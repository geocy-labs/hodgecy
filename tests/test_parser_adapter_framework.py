from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

import pytest

from hodgecy.core.adapters import AdapterCapability
from hodgecy.core.ids import HodgeCYID
from hodgecy.core.records import SourceRecordEnvelope
from hodgecy.core.status import ParseStatus, ValidationEvent
from hodgecy.datasets import AdapterRegistry, FixtureDatasetAdapter
from hodgecy.parsers import (
    BlockTextParser,
    JsonlParser,
    MathematicaRuleParser,
    ParquetRowParser,
    SourceChunk,
    ZipArchiveParser,
    write_rejected_jsonl,
)


def source(payload: str | bytes, dataset_id: str = "fixture_dataset", distribution_id: str = "fixture") -> SourceChunk:
    return SourceChunk(
        dataset_id=HodgeCYID.dataset(dataset_id),
        distribution_id=distribution_id,
        payload=payload,
        relative_path=f"fixtures/{distribution_id}",
        source_version="fixture-v1",
    )


def test_jsonl_parser_emits_records_and_rejections() -> None:
    parser = JsonlParser()
    result = parser.parse(source('{"id":"a1","h11":1}\nnot-json\n[1,2]\n{"id":"a2"}\n'))

    assert result.parsed_count == 2
    assert result.rejected_count == 2
    assert result.records[0].native_id == "a1"
    assert result.records[0].source_locator.source_line == 1
    assert result.rejected[0].error_code == "invalid_json"
    assert result.rejected[1].error_code == "jsonl_record_not_object"


def test_block_text_parser_reads_key_value_blocks() -> None:
    parser = BlockTextParser()
    payload = "id: block-a\nh11: 2\n---\nname: block b\nh12: 4\n"
    result = parser.parse(source(payload))

    assert result.parsed_count == 2
    assert result.rejected_count == 0
    assert result.records[1].native_id == "block_b"
    assert result.records[0].payload == {"id": "block-a", "h11": "2"}


def test_block_text_parser_rejects_bad_blocks() -> None:
    parser = BlockTextParser()
    result = parser.parse(source("id: ok\n\nmissing colon\n"))

    assert result.parsed_count == 1
    assert result.rejected_count == 1
    assert result.rejected[0].source_locator.source_block == "2"


def test_mathematica_rule_parser_handles_safe_rules_and_lists() -> None:
    parser = MathematicaRuleParser()
    result = parser.parse(source('{id -> "m1", h11 -> 2, c2 -> {1, 2, 3}}'))

    assert result.parsed_count == 1
    assert result.rejected_count == 0
    assert result.records[0].native_id == "m1"
    assert result.records[0].payload == {"id": "m1", "h11": 2, "c2": [1, 2, 3]}


def test_mathematica_rule_parser_rejects_malformed_input() -> None:
    parser = MathematicaRuleParser()
    result = parser.parse(source("{id -> one, broken}"))

    assert result.parsed_count == 0
    assert result.rejected_count == 1
    assert result.rejected[0].error_code == "invalid_mathematica_rule_syntax"


def test_zip_archive_parser_delegates_members_and_rejects_unsafe_paths() -> None:
    archive_bytes = BytesIO()
    with ZipFile(archive_bytes, "w") as archive:
        archive.writestr("records.jsonl", '{"id":"z1"}\nnot-json\n')
        archive.writestr("../escape.jsonl", '{"id":"bad"}\n')
        archive.writestr("unsupported.bin", "x")

    result = ZipArchiveParser().parse(source(archive_bytes.getvalue(), distribution_id="fixture_zip"))

    assert result.parsed_count == 1
    assert {item.error_code for item in result.rejected} == {
        "invalid_json",
        "unsafe_zip_member_path",
        "unsupported_zip_member_type",
    }
    assert result.records[0].source_locator.archive_member == "records.jsonl"


def test_parquet_row_parser_reads_tiny_fixture(tmp_path) -> None:
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    path = tmp_path / "fixture.parquet"
    table = pa.table({"id": ["p1", "p2"], "h11": [1, 2], "h12": [3, 4]})
    pq.write_table(table, path)

    chunk = SourceChunk(
        dataset_id=HodgeCYID.dataset("fixture_parquet"),
        distribution_id="parquet_fixture",
        payload=b"",
        relative_path=str(path),
    )
    result = ParquetRowParser(max_rows=1, columns=["id", "h11"]).parse(chunk)

    assert result.parsed_count == 1
    assert result.records[0].native_id == "p1"
    assert result.records[0].payload == {"id": "p1", "h11": 1}
    assert result.records[0].source_locator.row_group == 0


def test_fixture_dataset_adapter_emits_source_envelopes_and_validation_events() -> None:
    chunk = source('{"id":"native 1","h11":1}\nnot-json\n')
    adapter = FixtureDatasetAdapter.build(
        dataset_id="fixture_dataset",
        parser=JsonlParser(),
        sources=[chunk],
        capabilities=(AdapterCapability.STREAMING, AdapterCapability.NATIVE_PAYLOAD),
    )

    run = adapter.run()
    manifest = adapter.normalization_manifest(run, output_refs=("memory://fixture",))

    assert run.summary.source_count == 1
    assert run.summary.parsed_count == 1
    assert run.summary.rejected_count == 1
    assert isinstance(run.envelopes[0], SourceRecordEnvelope)
    assert run.envelopes[0].parse_status is ParseStatus.PARSED
    assert run.envelopes[0].source_record_id.local_id == "native_1"
    assert all(isinstance(event, ValidationEvent) for event in run.envelopes[0].validation_events)
    assert manifest.to_dict()["output_record_count"] == 1
    assert manifest.to_dict()["manifest_id"] == manifest.manifest_id


def test_adapter_registry_rejects_duplicate_dataset() -> None:
    adapter = FixtureDatasetAdapter.build(
        dataset_id="fixture_dataset",
        parser=JsonlParser(),
        sources=[source('{"id":"a"}\n')],
    )
    registry = AdapterRegistry()
    registry.register(adapter)

    assert registry.get("fixture_dataset") is adapter
    with pytest.raises(ValueError):
        registry.register(adapter)
    registry.register(adapter, replace=True)
    assert registry.list_dataset_ids() == (HodgeCYID.dataset("fixture_dataset"),)


def test_rejected_record_jsonl_writer_is_deterministic(tmp_path) -> None:
    result = JsonlParser().parse(source("not-json\n"))
    path = tmp_path / "rejected.jsonl"

    count = write_rejected_jsonl(path, result.rejected)
    first = path.read_text(encoding="utf-8")
    count_again = write_rejected_jsonl(path, result.rejected)

    assert count == 1
    assert count_again == 1
    assert first == path.read_text(encoding="utf-8")
    assert "invalid_json" in first
