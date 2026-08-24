from __future__ import annotations

import json

from hodgecy.cohorts import baseline_hodgecy_ii_comparison, hodgecy_ii_node_geometry_blob5, ingest_hodgecy_ii_cohort, load_hodgecy_ii_manifest
from hodgecy.core import ComparisonState, EvidenceStatus, ResultKind
from hodgecy.storage import ResultStore


def make_store(tmp_path) -> ResultStore:
    store = ResultStore(tmp_path / "registry" / "hodgecy-results.sqlite")
    store.initialize()
    return store


def test_manifest_loads_current_documented_cohort() -> None:
    manifest = load_hodgecy_ii_manifest()
    assert manifest["cohort_id"] == "hodgecy-ii"
    assert [member["arrangement_id"] for member in manifest["members"]] == ["84", "84a", "239", "240", "241"]
    assert manifest["excluded_explicit_records"][0]["arrangement_id"] == "83"


def test_ingest_registers_stable_distinct_geometries_and_sets(tmp_path) -> None:
    store = make_store(tmp_path)
    result = ingest_hodgecy_ii_cohort(store)
    geometry_ids = [geometry.geometry_id for geometry in result.geometries]

    assert geometry_ids == ["hodgecy-ii-84", "hodgecy-ii-84a", "hodgecy-ii-239", "hodgecy-ii-240", "hodgecy-ii-241"]
    assert "hodgecy-ii-84" != "hodgecy-ii-84a"
    sets = {comparison_set.comparison_set_id: comparison_set.member_geometry_ids for comparison_set in result.comparison_sets}
    assert sets["hodgecy-ii-84-pair"] == ("hodgecy-ii-84", "hodgecy-ii-84a")
    assert sets["hodgecy-ii-239-241"] == ("hodgecy-ii-239", "hodgecy-ii-240", "hodgecy-ii-241")
    assert sets["hodgecy-ii-source-cohort"] == ("hodgecy-ii-84", "hodgecy-ii-84a", "hodgecy-ii-239", "hodgecy-ii-240", "hodgecy-ii-241")


def test_ingest_is_idempotent_for_geometries_and_comparison_sets(tmp_path) -> None:
    store = make_store(tmp_path)
    ingest_hodgecy_ii_cohort(store)
    ingest_hodgecy_ii_cohort(store)

    assert len(store.list_geometries(geometry_type="eight_plane_arrangement_source_profile")) == 5
    assert store.get_comparison_set("hodgecy-ii-84-pair").member_geometry_ids == ("hodgecy-ii-84", "hodgecy-ii-84a")
    assert store.get_comparison_set("hodgecy-ii-source-cohort").member_geometry_ids[-1] == "hodgecy-ii-241"


def test_ingested_invariants_preserve_provenance_and_firewall_levels(tmp_path) -> None:
    store = make_store(tmp_path)
    ingest_hodgecy_ii_cohort(store)
    invariants = {item.invariant_name: item for item in store.get_invariants(geometry_id="hodgecy-ii-84a")}

    assert invariants["local_inventory"].result_kind is ResultKind.SOURCE_ASSEMBLY
    assert invariants["local_inventory"].value == {"p3": 16, "p4_0": 10, "p4_1": 0, "p5_0": 0, "p5_1": 0, "p5_2": 0, "l3": 0}
    assert invariants["local_inventory"].evidence_status is EvidenceStatus.IMPORTED
    assert "theorem_summary.json" in str(invariants["local_inventory"].provenance)
    assert invariants["node_relation_rank"].result_kind is ResultKind.NODE_RELATION
    assert invariants["node_relation_rank"].evidence_status is EvidenceStatus.UNKNOWN
    assert invariants["classical_defect"].result_kind is ResultKind.NODE_GEOMETRY
    assert invariants["conifold_atom_spectrum"].result_kind is ResultKind.CONIFOLD_ATOM


def test_unknown_hodge_data_for_239_240_241_remain_unknown(tmp_path) -> None:
    store = make_store(tmp_path)
    ingest_hodgecy_ii_cohort(store)
    h11_239 = store.get_invariants(geometry_id="hodgecy-ii-239", name="h11")[0]
    h11_84 = store.get_invariants(geometry_id="hodgecy-ii-84", name="h11")[0]

    assert h11_239.result_kind is ResultKind.HODGE_DATA
    assert h11_239.value is None
    assert h11_239.evidence_status is EvidenceStatus.UNKNOWN
    assert h11_84.value == 40
    assert h11_84.evidence_status is EvidenceStatus.IMPORTED


def test_baseline_pair_set_refinement_and_reports(tmp_path) -> None:
    store = make_store(tmp_path)
    report_dir = tmp_path / "reports"
    baseline = baseline_hodgecy_ii_comparison(store, report_dir=report_dir)

    pair_states = {result.comparison_key: result.state for result in baseline.pair_84_report.invariant_results}
    assert pair_states["local_inventory"] is ComparisonState.EQUAL
    assert pair_states["rank_mod_2"] is ComparisonState.DIFFERENT
    assert pair_states["node_relation_rank"] is ComparisonState.UNKNOWN
    assert baseline.pair_84_first_available_difference.first_difference == "rank_mod_2"

    set_states = {result.comparison_key: result.state for result in baseline.set_239_241_results}
    assert set_states["local_inventory"] is ComparisonState.EQUAL
    assert set_states["rank_Q"] is ComparisonState.DIFFERENT
    assert baseline.set_239_241_first_split.first_difference == "rank_Q"
    assert baseline.source_cohort_first_split.first_difference == "rank_Q"

    paths = {path.name for path in baseline.report_paths}
    assert "hodgecy_ii_84_pair_baseline.json" in paths
    assert "hodgecy_ii_239_241_baseline.md" in paths
    payload = json.loads((report_dir / "hodgecy_ii_84_pair_baseline.json").read_text(encoding="utf-8"))
    assert payload["first_current_available_distinction"]["first_difference"] == "rank_mod_2"
    assert "comparison_time" not in json.dumps(payload)


def test_reopen_persistence_keeps_cohort_records_available(tmp_path) -> None:
    path = tmp_path / "registry" / "hodgecy-results.sqlite"
    store = ResultStore(path)
    store.initialize()
    ingest_hodgecy_ii_cohort(store)

    reopened = ResultStore(path)
    assert reopened.get_geometry("hodgecy-ii-84a").source_entry_id == "84a"
    assert reopened.get_comparison_set("hodgecy-ii-239-241").member_geometry_ids == ("hodgecy-ii-239", "hodgecy-ii-240", "hodgecy-ii-241")
    assert reopened.get_invariants(geometry_id="hodgecy-ii-241", name="rank_Q")[0].value == 24


def test_blob5_node_geometry_persists_imported_84_degree_but_keeps_odp_unknown(tmp_path) -> None:
    store = make_store(tmp_path)
    result = hodgecy_ii_node_geometry_blob5(store)
    by_name = {item.invariant_name: item for item in store.get_invariants(geometry_id="hodgecy-ii-84", result_kind=ResultKind.NODE_GEOMETRY)}

    assert result.node_summaries["84"]["singular_scheme_degree"] == 112
    assert by_name["singular_scheme_dimension"].value == 0
    assert by_name["singular_scheme_dimension"].evidence_status is EvidenceStatus.IMPORTED
    assert by_name["singular_scheme_degree"].value == 112
    assert by_name["singular_support_cardinality"].value is None
    assert by_name["singular_support_cardinality"].evidence_status is EvidenceStatus.UNKNOWN
    assert by_name["singular_scheme_reduced"].evidence_status is EvidenceStatus.UNKNOWN
    assert by_name["pointwise_odp_verified_count"].evidence_status is EvidenceStatus.UNKNOWN
    assert by_name["finite_reduced_odp_scheme"].evidence_status is EvidenceStatus.UNKNOWN
    assert by_name["generic_parameter_verified"].evidence_status is EvidenceStatus.UNKNOWN


def test_blob5_node_geometry_does_not_analyze_239_240_241_without_models(tmp_path) -> None:
    store = make_store(tmp_path)
    hodgecy_ii_node_geometry_blob5(store)
    by_name = {item.invariant_name: item for item in store.get_invariants(geometry_id="hodgecy-ii-239", result_kind=ResultKind.NODE_GEOMETRY)}

    assert by_name["singular_scheme_degree"].value is None
    assert by_name["singular_scheme_degree"].evidence_status is EvidenceStatus.UNKNOWN
    assert "no exact supported singular-fiber model" in (by_name["singular_scheme_degree"].notes or "")


def test_blob5_node_geometry_reports_and_pair_comparison(tmp_path) -> None:
    store = make_store(tmp_path)
    report_dir = tmp_path / "node_reports"
    result = hodgecy_ii_node_geometry_blob5(store, report_dir=report_dir)

    pair_states = {item.comparison_key: item.state for item in result.pair_84_node_report.invariant_results}
    assert pair_states["singular_scheme_degree"] is ComparisonState.EQUAL
    assert pair_states["singular_support_cardinality"] is ComparisonState.UNKNOWN
    assert result.pair_84_node_first_difference.state is ComparisonState.UNKNOWN
    paths = {path.name for path in result.report_paths}
    assert "hodgecy_ii_node_geometry_blob5.json" in paths
    assert "hodgecy_ii_84_84a_node_geometry_comparison.md" in paths
    payload = json.loads((report_dir / "hodgecy_ii_node_geometry_blob5.json").read_text(encoding="utf-8"))
    assert payload["node_summaries"]["84a"]["singular_scheme_degree"] == 112
    assert "comparison_time" not in json.dumps(payload)
