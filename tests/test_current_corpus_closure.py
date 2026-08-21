from __future__ import annotations

import csv
import json

import pytest

pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")

import hodgecy.bootstrap.closure as closure_module
from hodgecy.bootstrap import CorpusBootstrapConfig, CorpusClosureConfig, bootstrap_current_corpus, close_current_corpus
from hodgecy.storage import open_catalog
from test_current_corpus_bootstrap import _fixture_root


def _append_final_states(root, rows: list[tuple[str, str, str]]) -> None:
    path = root / "reports" / "final_completion_states.tsv"
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        for dataset, state, count in rows:
            writer.writerow([dataset, state, count, "closure fixture"])


def _add_ks_fixture(root) -> None:
    ks_dir = root / "raw" / "kreuzer_skarke" / "parquet"
    ks_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = ks_dir / "ks_fixture.parquet"
    pq.write_table(
        pa.Table.from_pylist([
            {
                "vertex_count": 4,
                "facet_count": 4,
                "point_count": 5,
                "dual_point_count": 5,
                "h11": 1,
                "h12": 101,
                "euler_characteristic": -200,
                "vertices": "heavy-payload",
            }
        ]),
        parquet_path,
    )
    manifest = root / "manifests" / "kreuzer_skarke" / "parquet_files.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            [
                {
                    "filename": parquet_path.name,
                    "size_bytes": parquet_path.stat().st_size,
                    "local_sha256": "fixture-ks-sha256",
                    "source_url": "https://example.invalid/ks_fixture.parquet",
                    "revision": "fixture-revision",
                    "download_status": "fixture-present",
                }
            ],
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def test_current_corpus_closure_reports_ready_final_classes_and_ks_provenance(tmp_path, monkeypatch) -> None:
    root = _fixture_root(tmp_path)
    _append_final_states(
        root,
        [
            ("kreuzer_skarke", "COMPLETE_COLUMNAR", "1"),
            ("genuine_gcicy", "SOURCE_REGISTRY_ONLY", "0"),
            ("picard_fuchs_cyo", "COMPLETE_REMOTE", "0"),
            ("cicy3_divisors_springer", "MANUAL_SOURCE_REQUIRED", "0"),
            ("toric_ci_nef_partitions", "COMPUTABLE_NOT_PREENUMERATED", "0"),
            ("double_octics", "PARTIAL_PUBLIC_CORPUS", "0"),
        ],
    )
    _add_ks_fixture(root)
    monkeypatch.setattr(closure_module, "_smoke", lambda catalog, integrity: [{"name": "fixture_smoke", "passed": True, "detail": "ok"}])

    bootstrap_current_corpus(CorpusBootstrapConfig(root, batch_size=2, hodgecy_commit="fixture-sha"))
    result = close_current_corpus(CorpusClosureConfig(root, hodgecy_commit="fixture-sha"))

    assert result.corpus_fully_integrated is True
    assert result.second_acquisition_pass_ready is True
    assert result.remaining_blockers == []
    assert all(row["final_completion_class"] != "UNRESOLVED" for row in result.final_states)
    assert all(row["required_action"] != "EXPLAIN_OR_INTEGRATE" for row in result.stranded_sources)

    classes = {row["dataset_id"]: row["final_completion_class"] for row in result.final_states}
    assert classes["cicy3_standard"] == "COMPLETE_NORMALIZED"
    assert classes["current_corpus_relationships"] == "COMPLETE_RELATIONSHIP"
    assert classes["kreuzer_skarke"] == "COMPLETE_NATIVE_LAZY"
    assert classes["genuine_gcicy"] == "SOURCE_REGISTRY_ONLY"
    assert classes["picard_fuchs_cyo"] == "COMPLETE_REMOTE"
    assert classes["cicy3_divisors_springer"] == "MANUAL_SOURCE_REQUIRED"
    assert classes["toric_ci_nef_partitions"] == "COMPUTABLE_NOT_PREENUMERATED"
    assert classes["double_octics"] == "PARTIAL_PUBLIC_CORPUS"

    for path in result.reports.values():
        assert path.exists()

    status = json.loads((root / "reports" / "current_catalog_final_status.json").read_text(encoding="utf-8"))
    assert status["corpus_fully_integrated"] is True
    assert status["second_acquisition_pass_ready"] is True
    assert status["architecture_impacting_unresolved_count"] == 0
    assert status["KS_partition_checksum_reference_coverage"] == {"covered": 1, "state": "REFERENCED_VERIFIED", "total": 1}

    catalog = open_catalog(root, name="current_corpus", read_only=True)
    source = catalog.payload["physical_sources"]["ks_parquet_000"]
    assert source["sha256"] == "fixture-ks-sha256"
    assert source["metadata"]["checksum_verification_state"] == "REFERENCED_VERIFIED"
    assert source["metadata"]["checksum_source"] == "manifests/kreuzer_skarke/parquet_files.json"

    snapshot = json.loads((root / "manifests" / "current_hodgecy_corpus_snapshot.json").read_text(encoding="utf-8"))
    assert snapshot["source_checksums"]["ks_parquet_000"] == "fixture-ks-sha256"
    assert snapshot["metadata"]["final_completion_classes"]["kreuzer_skarke"] == "COMPLETE_NATIVE_LAZY"
