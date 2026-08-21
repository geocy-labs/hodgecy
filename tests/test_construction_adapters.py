from __future__ import annotations

import json

import pytest

pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")

from hodgecy.core.ids import HodgeCYID
from hodgecy.core.records import SourceRecordEnvelope
from hodgecy.core.status import AcquisitionStatus
from hodgecy.datasets import (
    cicy3_adapter,
    cicy3_descriptor,
    cicy4_adapter,
    cicy4_descriptor,
    double_octic_adapter,
    double_octic_descriptor,
    ip_weight_adapter,
    ip_weight_descriptor,
    kreuzer_skarke_descriptor,
    picard_fuchs_adapter,
    picard_fuchs_descriptor,
    weighted_p4_adapter,
    weighted_p4_descriptor,
)
from hodgecy.datasets.cicy import cicy_query_rows
from hodgecy.datasets.double_octics import double_octic_query_rows, load_table1_source_records
from hodgecy.datasets.operators import operator_query_rows, to_picard_fuchs_operator
from hodgecy.datasets.toric import ip_weight_query_rows
from hodgecy.datasets.weighted import weighted_query_rows
from hodgecy.parsers import SourceChunk
from hodgecy.query import Q
from hodgecy.storage import DatasetInstance, open_catalog


def chunk(dataset_id: str, payload: str, *, distribution_id: str = "fixture") -> SourceChunk:
    return SourceChunk(
        dataset_id=HodgeCYID.dataset(dataset_id),
        distribution_id=distribution_id,
        payload=payload,
        relative_path=f"raw/{dataset_id}/{distribution_id}.jsonl",
        source_version="fixture-v1",
        file_sha256="0" * 64,
    )


def test_construction_descriptors_preserve_scope_and_counts() -> None:
    descriptors = [
        cicy3_descriptor(),
        cicy4_descriptor(),
        weighted_p4_descriptor(),
        ip_weight_descriptor(),
        picard_fuchs_descriptor(),
        double_octic_descriptor(),
        kreuzer_skarke_descriptor(),
    ]

    by_id = {descriptor.dataset_id.local_id: descriptor for descriptor in descriptors}
    assert by_id["cicy3_standard"].expected_count == 7890
    assert by_id["cicy4_core"].expected_count == 921497
    assert by_id["weighted_p4"].expected_count == 7555
    assert by_id["ip_weight_systems_4d"].expected_count == 184026
    assert by_id["kreuzer_skarke"].acquisition_status is AcquisitionStatus.COMPLETE_COLUMNAR
    assert by_id["kreuzer_skarke"].metadata["row_count"] == 473800776
    assert by_id["picard_fuchs_cyo_topological"].metadata["geometry_identity_inference"] is False


def test_cicy_adapters_emit_envelopes_and_preserve_c2_and_cy4_hodge_payloads() -> None:
    cicy3_source = chunk(
        "cicy3_standard",
        json.dumps({"Num": 1, "configuration_matrix": [[4], [2]], "h11": 1, "h21": 65, "euler": -128, "c2": [24, 36]}) + "\n",
    )
    cicy4_source = chunk(
        "cicy4_core",
        json.dumps({"matrix_number": 7, "dimension": 4, "configuration_matrix": [[1, 1], [2, 3]], "h11": 2, "h12": 0, "h13": 12, "h22": 44, "h31": 12, "euler": 72}) + "\n",
    )

    cicy3_run = cicy3_adapter([cicy3_source]).run()
    cicy4_run = cicy4_adapter([cicy4_source]).run()

    assert cicy3_run.summary.envelope_count == 1
    assert cicy4_run.summary.envelope_count == 1
    assert isinstance(cicy3_run.envelopes[0], SourceRecordEnvelope)
    assert cicy3_run.parse_results[0].records[0].payload["c2"] == [24, 36]
    assert cicy3_run.parse_results[0].records[0].payload["hodge_numbers"] == {"h11": 1, "h21": 65}
    assert cicy4_run.parse_results[0].records[0].payload["hodge_numbers"]["h22"] == 44
    assert cicy4_run.envelopes[0].source_provenance.file_sha256 == "0" * 64


def test_construction_adapters_reject_invalid_payloads() -> None:
    bad_cicy = cicy3_adapter([chunk("cicy3_standard", '{"Num":1,"configuration_matrix":[[1],[1,2]]}\n')]).run()
    bad_weighted = weighted_p4_adapter([chunk("weighted_p4", '{"weights":[1,2,3]}\n')]).run()
    bad_pf = picard_fuchs_adapter([chunk("picard_fuchs_cyo_topological", '{"order":"four"}\n')]).run()

    assert bad_cicy.summary.rejected_count == 1
    assert bad_weighted.summary.rejected_count == 1
    assert bad_pf.summary.rejected_count == 1


def test_weighted_ip_operator_and_double_octic_wrappers() -> None:
    weighted_run = weighted_p4_adapter([chunk("weighted_p4", '{"weights":[1,1,1,1,1],"degree":5,"h11":1,"h21":101,"euler":-200}\n')]).run()
    ip_run = ip_weight_adapter([chunk("ip_weight_systems_4d", '{"id":"ip-1","weights":[1,1,1,1,2],"h11":2,"h21":86,"point_count":100,"vertex_count":5,"dual_point_count":90}\n')]).run()
    pf_run = picard_fuchs_adapter([chunk("picard_fuchs_cyo_topological", '{"operator_id":"op-1","operator_label":"L1","order":4,"coefficients":["theta^4","z"]}\n')]).run()
    double_run = double_octic_adapter([chunk("double_octic_cynk_meyer", '{"arrangement":"84","h11":35,"h12":1,"euler":68}\n')]).run()

    assert weighted_run.parse_results[0].parser_provenance.parser_name == "weighted_p4_jsonl"
    assert weighted_query_rows(weighted_run)[0]["source_record_id"] == "w-1-1-1-1-1"
    assert ip_weight_query_rows(ip_run)[0]["point_count"] == 100
    operator = to_picard_fuchs_operator(pf_run.parse_results[0].records[0].payload)
    assert operator.example_id == "op-1"
    assert operator.status == "source_reported"
    assert operator_query_rows(pf_run)[0]["is_geometry_record"] is False
    assert double_octic_query_rows(double_run)[0]["is_hodgecy_i_control"] is True


def test_double_octic_real_table1_wrapper_keeps_hodgecy_i_examples_available() -> None:
    records = load_table1_source_records()
    ids = {record["source_record_id"] for record in records}

    assert {"84", "84a"}.issubset(ids)
    row84 = next(record for record in records if record["source_record_id"] == "84")
    assert row84["construction_family"] == "double_octic"
    assert row84["derived_hodgecy_i_outputs_separate"] is True


def test_catalog_can_load_and_query_major_construction_fixtures(tmp_path) -> None:
    catalog = open_catalog(tmp_path, create=True)
    fixtures = [
        (cicy3_descriptor(), cicy3_adapter([chunk("cicy3_standard", '{"Num":1,"configuration_matrix":[[4],[2]],"h11":1,"h21":65,"euler":-128}\n')]).run(), cicy_query_rows, "cicy3_fixture"),
        (cicy4_descriptor(), cicy4_adapter([chunk("cicy4_core", '{"matrix_number":7,"dimension":4,"configuration_matrix":[[1,1],[2,3]],"h11":2,"h12":0,"h13":12,"h22":44,"h31":12,"euler":72}\n')]).run(), cicy_query_rows, "cicy4_fixture"),
        (weighted_p4_descriptor(), weighted_p4_adapter([chunk("weighted_p4", '{"weights":[1,1,1,1,1],"degree":5,"h11":1,"h21":101,"euler":-200}\n')]).run(), weighted_query_rows, "weighted_fixture"),
        (ip_weight_descriptor(), ip_weight_adapter([chunk("ip_weight_systems_4d", '{"id":"ip-1","weights":[1,1,1,1,2],"h11":2,"h21":86,"point_count":100,"vertex_count":5,"dual_point_count":90}\n')]).run(), ip_weight_query_rows, "ip_fixture"),
        (picard_fuchs_descriptor(), picard_fuchs_adapter([chunk("picard_fuchs_cyo_topological", '{"operator_id":"op-1","operator_label":"L1","order":4,"coefficients":["theta^4","z"]}\n')]).run(), operator_query_rows, "pf_fixture"),
        (double_octic_descriptor(), double_octic_adapter([chunk("double_octic_cynk_meyer", '{"arrangement":"84","h11":35,"h12":1,"euler":68}\n')]).run(), double_octic_query_rows, "double_octic_fixture"),
    ]

    for descriptor, run, row_builder, table_name in fixtures:
        catalog.register_dataset(descriptor)
        instance_id = f"{descriptor.dataset_id.local_id}_fixture_v1"
        catalog.register_instance(DatasetInstance(
            instance_id=instance_id,
            dataset_id=descriptor.dataset_id,
            source_version="fixture-v1",
            acquisition_status=descriptor.acquisition_status,
            redistribution_status=descriptor.redistribution_status,
            record_count=run.summary.envelope_count,
            adapter_name=run.summary.adapter_descriptor.adapter_name,
            source_revision=descriptor.source_version,
        ))
        raw_dir = tmp_path / "raw" / descriptor.dataset_id.local_id
        raw_dir.mkdir(parents=True, exist_ok=True)
        parquet_path = raw_dir / f"{table_name}.parquet"
        rows = [_scalar_row(row) for row in row_builder(run)]
        pq.write_table(pa.Table.from_pylist(rows), parquet_path)
        catalog.register_parquet_source(
            columnar_id=f"{table_name}_columnar",
            instance_id=instance_id,
            source_id=f"{table_name}_source",
            relative_path=f"raw/{descriptor.dataset_id.local_id}/{table_name}.parquet",
            table_name=table_name,
            common_field_mapping={"h^(1,1)": "h11", "h^(2,1)": "h21"},
            query_safe_columns=tuple(rows[0].keys()),
        )

    cicy3 = catalog.query(Q.dataset("cicy3_standard").where_hodge(h11=1).select("source_record_id", "h11", "euler"))
    pf = catalog.query(Q.dataset("picard_fuchs_cyo_topological").select("source_record_id", "operator_order", "is_geometry_record"))
    double = catalog.describe_dataset("double_octic_cynk_meyer")

    assert cicy3.count() == 1
    assert cicy3.head(1).column("source_record_id").to_pylist() == ["1"]
    assert pf.head(1).column("is_geometry_record").to_pylist() == [False]
    assert double["instances"][0]["adapter_name"] == "double_octic_adapter"
    assert double["physical_sources"][0]["relative_path"].startswith("raw/double_octic_cynk_meyer/")


def _scalar_row(row: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in row.items() if key != "source_locator" and not isinstance(value, (list, dict))}
