from __future__ import annotations

import json

import pytest

pytest.importorskip("pyarrow")

from hodgecy.bootstrap import CorpusBootstrapConfig, bootstrap_current_corpus
from hodgecy.query import QuerySpec
from hodgecy.storage import open_catalog


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _jsonl(path, rows):
    _write(path, "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def _fixture_root(tmp_path):
    root = tmp_path
    reports = root / "reports"
    _write(reports / "logical_datasets.tsv", "dataset_id\thuman_name\tconstruction_family\tcovered_dimensions\trecord_semantics\tsource_record_count\tstaged_record_count\tprimary_external_identifier\tparent_related_dataset\tacquisition_completeness\tsemantic_parse_completeness\tsource_provenance\tlicense_status\n" +
           "cicy3_standard\tCICY3\tcicy3\t3\tconfiguration\t2\t2\tNum\tnone\tCOMPLETE\tCOMPLETE\tfixture\tATTRIBUTION_REQUIRED\n" +
           "cicy3_favorable\tFavorable\tcicy3\t3\tpresentation\t2\t2\tNum\tcicy3_standard\tCOMPLETE\tCOMPLETE\tfixture\tATTRIBUTION_REQUIRED\n" +
           "cicy3_fibrations\tFibrations\tcicy3\t3\tfibration\t1\t1\tsource_cicy_id+fibration_id\tcicy3_favorable\tCOMPLETE\tCOMPLETE\tfixture\tATTRIBUTION_REQUIRED\n" +
           "weighted_p4\tWeighted\tweighted_p4\t3\tweights\t1\t1\tweights\tnone\tCOMPLETE\tCOMPLETE\tfixture\tATTRIBUTION_REQUIRED\n" +
           "ip_weight_systems_4d\tIP\ttoric_hypersurface\t3\tweights\t1\t1\tweights\tweighted_p4\tCOMPLETE\tCOMPLETE\tfixture\tATTRIBUTION_REQUIRED\n")
    _write(reports / "final_completion_states.tsv", "dataset\tstate\trecord_count\tarchitecture_impact\n" +
           "cicy3_standard\tCOMPLETE_LOCAL\t2\tfixture\n" +
           "cicy3_favorable\tCOMPLETE_LOCAL\t2\tfixture\n" +
           "cicy3_fibrations\tCOMPLETE_LOCAL\t1\tfixture\n" +
           "weighted_p4\tCOMPLETE_LOCAL\t1\tfixture\n" +
           "ip_weight_systems_4d\tCOMPLETE_LOCAL\t1\tfixture\n")
    _write(reports / "source_inventory.tsv", "dataset_id\tlogical_dataset_id\tsource_url\tsource_citation\tDOI\tsource_version_revision\tacquisition_timestamp\toriginal_filename\tlocal_path\tbyte_size\tSHA256\tarchive_format\tparse_status\tlicense_status\tredistribution_status\n" +
           "cicy3_standard\tcicy3_core\t\tfixture\t\tfixture\t\tcicylist\tstaged/cicy3/cicylist.neutral.jsonl\t10\tabcd\tjsonl\tSTAGED_OR_PROFILED\tATTRIBUTION_REQUIRED\tacquired_locally_by_user\n")
    _jsonl(root / "staged" / "cicy3" / "cicylist.neutral.jsonl", [
        {"cicy_id": 1, "configuration_degree_matrix": [[1]], "c2_vector_source_basis": [2], "hodge": {"h11": 1, "h21": 2}, "source_dataset": "fixture", "source_file": "raw/cicy3/cicylist.txt"},
        {"cicy_id": 2, "configuration_degree_matrix": [[2]], "c2_vector_source_basis": [4], "hodge": {"h11": 2, "h21": 3}, "source_dataset": "fixture", "source_file": "raw/cicy3/cicylist.txt"},
    ])
    _jsonl(root / "staged" / "cicy3_favorable" / "favourcicylist.neutral.jsonl", [
        {"source_record_id": 1, "source_fields": {"Num": 1, "Favour": True, "KahlerPos": False, "IsProduct": False, "H11": 1, "H21": 2, "C2": [2]}, "parse_status": "VALID"},
        {"source_record_id": 2, "source_fields": {"Num": 2, "Favour": False, "KahlerPos": True, "IsProduct": False, "H11": 2, "H21": 3, "C2": [4]}, "parse_status": "VALID"},
    ])
    _jsonl(root / "staged" / "cicy3_fibrations" / "fibrationslist-3.neutral.jsonl", [
        {"source_record_id": "1:1", "source_cicy_id": 1, "fibration_id": 1, "fiber_data": [[1]], "ambient_decomposition": [[1]], "parse_status": "VALID"}
    ])
    _jsonl(root / "staged" / "weighted_p4" / "weighted_p4.res4_res5.neutral.jsonl", [
        {"source_record_id": "w1", "source_fields": {"weights": [1, 1, 1, 1, 1], "degree": 5, "h11": 1, "h21": 101, "chi": -200}, "parse_status": "VALID"}
    ])
    _jsonl(root / "staged" / "ip_weight_systems" / "tuwien_4d_ip_weights_hodge_k3.neutral.jsonl", [
        {"source_record_id": 1, "source_fields": {"weights": [1, 1, 1, 1, 1], "degree": 5, "source_flag": "TS", "h11": 1, "h12": 101}, "parse_status": "VALID"}
    ])
    return root


def test_current_corpus_bootstrap_fixture_catalog_reports_and_idempotence(tmp_path) -> None:
    root = _fixture_root(tmp_path)
    result = bootstrap_current_corpus(CorpusBootstrapConfig(root, batch_size=2, hodgecy_commit="fixture-sha"))
    assert result.catalog_path.exists()
    assert result.snapshot_path.exists()
    assert (root / "reports" / "current_corpus_build.tsv").exists()
    assert any(row.dataset == "cicy3_standard" and row.normalized_count == 2 for row in result.build_rows)
    assert any(row["relationship_type"] == "source_crosswalk" for row in result.relationship_rows)

    snapshot = json.loads(result.snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["source_checksums"]["current_cicy3_standard_parquet"]
    assert snapshot["source_checksums"]["current_corpus_relationships_parquet"]

    catalog = open_catalog(root, name="current_corpus", read_only=True)
    table = catalog.query(QuerySpec(table="current_cicy3_standard", fields=("source_record_id", "h11"))).to_arrow()
    assert table.num_rows == 2

    second = bootstrap_current_corpus(CorpusBootstrapConfig(root, batch_size=2, hodgecy_commit="fixture-sha"))
    assert second.snapshot_path.exists()
    assert len(second.relationship_rows) == len(result.relationship_rows)
