from __future__ import annotations

import json

from hodgecy.cohorts import (
    baseline_hodgecy_ii_comparison,
    hodgecy_ii_defect_blob7,
    hodgecy_ii_integral_lattice_blob8,
    hodgecy_ii_node_geometry_blob5,
    hodgecy_ii_node_ideal_hilbert_blob6,
    hodgecy_ii_node_relation_blob9,
    ingest_hodgecy_ii_cohort,
    load_hodgecy_ii_manifest,
)
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


def test_blob6_node_ideal_hilbert_keeps_84_ideal_and_hilbert_unknown(tmp_path) -> None:
    store = make_store(tmp_path)
    result = hodgecy_ii_node_ideal_hilbert_blob6(store)
    by_name = {item.invariant_name: item for item in store.get_invariants(geometry_id="hodgecy-ii-84", result_kind=ResultKind.NODE_GEOMETRY)}

    assert result.summaries["84"]["imported_singular_scheme_degree"] == 112
    assert by_name["exact_node_ideal_available"].value is False
    assert by_name["exact_node_ideal_available"].evidence_status is EvidenceStatus.COMPUTED
    assert by_name["scheme_ideal_hash"].value is None
    assert by_name["scheme_ideal_hash"].evidence_status is EvidenceStatus.UNKNOWN
    assert by_name["hilbert_function_table"].value is None
    assert by_name["hilbert_function_table"].evidence_status is EvidenceStatus.UNKNOWN
    assert "degree 112 is not enough" in (by_name["hilbert_computation_status"].notes or "")


def test_blob6_does_not_analyze_239_240_241_without_node_ideals(tmp_path) -> None:
    store = make_store(tmp_path)
    hodgecy_ii_node_ideal_hilbert_blob6(store)
    by_name = {item.invariant_name: item for item in store.get_invariants(geometry_id="hodgecy-ii-240", result_kind=ResultKind.NODE_GEOMETRY)}

    assert by_name["scheme_ideal_hash"].value is None
    assert by_name["hilbert_function_table"].evidence_status is EvidenceStatus.UNKNOWN
    assert "No exact supported node/singular-scheme ideal" in (by_name["hilbert_computation_status"].notes or "")


def test_blob6_reports_unknown_84_84a_hilbert_comparison(tmp_path) -> None:
    store = make_store(tmp_path)
    report_dir = tmp_path / "hilbert_reports"
    result = hodgecy_ii_node_ideal_hilbert_blob6(store, report_dir=report_dir)

    pair_states = {item.comparison_key: item.state for item in result.pair_84_hilbert_report.invariant_results}
    assert pair_states["exact_node_ideal_available"] is ComparisonState.EQUAL
    assert pair_states["scheme_ideal_hash"] is ComparisonState.UNKNOWN
    assert result.pair_84_hilbert_first_difference.state is ComparisonState.UNKNOWN
    paths = {path.name for path in result.report_paths}
    assert "hodgecy_ii_node_ideal_hilbert_blob6.json" in paths
    assert "hodgecy_ii_84_84a_hilbert_comparison.md" in paths
    payload = json.loads((report_dir / "hodgecy_ii_node_ideal_hilbert_blob6.json").read_text(encoding="utf-8"))
    assert payload["summaries"]["84"]["exact_node_or_singular_ideal_available"] is False
    assert "comparison_time" not in json.dumps(payload)


def test_blob7_resolves_84_84a_critical_degree_but_keeps_defect_unknown(tmp_path) -> None:
    store = make_store(tmp_path)
    result = hodgecy_ii_defect_blob7(store)
    blob7_run_ids = {run.run_id for run in store.get_runs(geometry_id="hodgecy-ii-84", calculation_type="hodgecy_ii_defect_blob7")}
    by_name = {
        item.invariant_name: item
        for item in store.get_invariants(geometry_id="hodgecy-ii-84", result_kind=ResultKind.NODE_GEOMETRY)
        if item.run_id in blob7_run_ids
    }

    assert result.summaries["84"]["branch_degree"] == 8
    assert result.summaries["84"]["critical_degree"] == 8
    assert result.summaries["84"]["N_k"] == 165
    assert by_name["critical_degree"].value == 8
    assert by_name["critical_degree"].evidence_status is EvidenceStatus.VERIFIED
    assert by_name["evaluation_source_dimension"].value == 165
    assert by_name["evaluation_rank"].value is None
    assert by_name["evaluation_rank"].evidence_status is EvidenceStatus.UNKNOWN
    assert by_name["classical_defect"].value is None
    assert by_name["classical_defect"].evidence_status is EvidenceStatus.UNKNOWN
    assert "exact node ideal" in (by_name["classical_defect"].notes or "")


def test_blob7_does_not_assign_double_solid_defect_to_239_240_241(tmp_path) -> None:
    store = make_store(tmp_path)
    result = hodgecy_ii_defect_blob7(store)
    blob7_run_ids = {run.run_id for run in store.get_runs(geometry_id="hodgecy-ii-239", calculation_type="hodgecy_ii_defect_blob7")}
    by_name = {
        item.invariant_name: item
        for item in store.get_invariants(geometry_id="hodgecy-ii-239", result_kind=ResultKind.NODE_GEOMETRY)
        if item.run_id in blob7_run_ids
    }

    assert result.summaries["239"]["critical_degree"] is None
    assert by_name["critical_degree"].value is None
    assert by_name["critical_degree"].evidence_status is EvidenceStatus.UNKNOWN
    assert by_name["classical_defect"].value is None
    assert "No applicable exact double-solid defect model" in result.summaries["239"]["reason"]


def test_blob7_reports_84_84a_defect_comparison(tmp_path) -> None:
    store = make_store(tmp_path)
    report_dir = tmp_path / "defect_reports"
    result = hodgecy_ii_defect_blob7(store, report_dir=report_dir)

    pair_states = {item.comparison_key: item.state for item in result.pair_84_defect_report.invariant_results}
    assert pair_states["critical_degree"] is ComparisonState.EQUAL
    assert pair_states["evaluation_rank"] is ComparisonState.UNKNOWN
    assert pair_states["classical_defect"] is ComparisonState.UNKNOWN
    assert result.pair_84_defect_first_difference.state is ComparisonState.UNKNOWN
    paths = {path.name for path in result.report_paths}
    assert "hodgecy_ii_defect_blob7.json" in paths
    assert "hodgecy_ii_84_84a_defect_comparison.md" in paths
    payload = json.loads((report_dir / "hodgecy_ii_defect_blob7.json").read_text(encoding="utf-8"))
    assert payload["summaries"]["84a"]["critical_degree"] == 8
    assert "comparison_time" not in json.dumps(payload)


def test_blob8_source_lattice_reproduces_84_84a_mod2_distinction(tmp_path) -> None:
    store = make_store(tmp_path)
    result = hodgecy_ii_integral_lattice_blob8(store)

    assert result.summaries["84"]["matrix_shape"] == [26, 28]
    assert result.summaries["84a"]["matrix_shape"] == [26, 28]
    assert result.summaries["84"]["rank_Q"] == 26
    assert result.summaries["84a"]["rank_Q"] == 26
    assert result.summaries["84"]["rank_mod_2"] == 23
    assert result.summaries["84a"]["rank_mod_2"] == 21
    assert result.pair_84_source_lattice_first_difference.first_difference == "rank_mod_2"

    pair_states = {item.comparison_key: item.state for item in result.pair_84_source_lattice_report.invariant_results}
    assert pair_states["rank_Q"] is ComparisonState.EQUAL
    assert pair_states["rank_mod_2"] is ComparisonState.DIFFERENT
    assert result.summaries["84"]["legacy_cross_check"]["rank_mod_2_matches_source_record"] is True


def test_blob8_source_lattice_reproduces_239_240_241_rational_split(tmp_path) -> None:
    store = make_store(tmp_path)
    result = hodgecy_ii_integral_lattice_blob8(store)

    assert result.summaries["239"]["rank_Q"] == 26
    assert result.summaries["240"]["rank_Q"] == 26
    assert result.summaries["241"]["rank_Q"] == 24
    assert result.summaries["239"]["rank_mod_2"] == 21
    assert result.summaries["240"]["rank_mod_2"] == 23
    assert result.summaries["241"]["rank_mod_2"] == 24
    assert result.set_239_241_source_lattice_first_difference.first_difference == "rank_Q"
    assert result.summaries["241"]["legacy_cross_check"]["rank_Q_matches_source_record"] is True


def test_blob8_source_lattice_reports_are_written(tmp_path) -> None:
    store = make_store(tmp_path)
    report_dir = tmp_path / "blob8_reports"
    result = hodgecy_ii_integral_lattice_blob8(store, report_dir=report_dir)

    paths = {path.name for path in result.report_paths}
    assert "hodgecy_ii_integral_lattice_blob8.json" in paths
    assert "hodgecy_ii_84_84a_source_lattice_comparison.md" in paths
    payload = json.loads((report_dir / "hodgecy_ii_integral_lattice_blob8.json").read_text(encoding="utf-8"))
    assert payload["summaries"]["84"]["matrix_role"] == "source_assembly"
    assert payload["summaries"]["84a"]["rank_mod_2"] == 21
    assert "comparison_time" not in json.dumps(payload)


def test_blob9_records_expected_84_shapes_but_keeps_node_relations_unknown(tmp_path) -> None:
    store = make_store(tmp_path)
    result = hodgecy_ii_node_relation_blob9(store)
    blob9_run_ids = {run.run_id for run in store.get_runs(geometry_id="hodgecy-ii-84", calculation_type="hodgecy_ii_node_relation_blob9")}
    by_name = {
        item.invariant_name: item
        for item in store.get_invariants(geometry_id="hodgecy-ii-84", result_kind=ResultKind.NODE_RELATION)
        if item.run_id in blob9_run_ids
    }

    assert result.summaries["84"]["expected_node_count"] == 112
    assert result.summaries["84"]["critical_degree"] == 8
    assert result.summaries["84"]["expected_evaluation_matrix_shape"] == [112, 165]
    assert result.summaries["84"]["expected_relation_map_shape"] == [165, 112]
    assert by_name["expected_relation_realization_kind"].value == "evaluation_condition"
    assert by_name["node_generator_rank"].value is None
    assert by_name["node_generator_rank"].evidence_status is EvidenceStatus.UNKNOWN
    assert by_name["rational_evaluation_relation_rank"].value is None
    assert by_name["integral_evaluation_relation_snf"].evidence_status is EvidenceStatus.UNKNOWN
    assert "without verified node support" in (by_name["node_generator_module_status"].notes or "")


def test_blob9_does_not_assign_relation_model_to_239_240_241(tmp_path) -> None:
    store = make_store(tmp_path)
    result = hodgecy_ii_node_relation_blob9(store)
    blob9_run_ids = {run.run_id for run in store.get_runs(geometry_id="hodgecy-ii-239", calculation_type="hodgecy_ii_node_relation_blob9")}
    by_name = {
        item.invariant_name: item
        for item in store.get_invariants(geometry_id="hodgecy-ii-239", result_kind=ResultKind.NODE_RELATION)
        if item.run_id in blob9_run_ids
    }

    assert result.summaries["239"]["expected_node_count"] is None
    assert result.summaries["239"]["expected_evaluation_matrix_shape"] is None
    assert by_name["expected_relation_realization_kind"].value is None
    assert by_name["rational_evaluation_relation_complex"].evidence_status is EvidenceStatus.UNKNOWN
    assert by_name["source_to_node_map_status"].value == "NOT_CONSTRUCTED"


def test_blob9_reports_84_84a_relation_status(tmp_path) -> None:
    store = make_store(tmp_path)
    report_dir = tmp_path / "node_relation_reports"
    result = hodgecy_ii_node_relation_blob9(store, report_dir=report_dir)

    pair_states = {item.comparison_key: item.state for item in result.pair_84_node_relation_report.invariant_results}
    assert pair_states["expected_evaluation_matrix_shape"] is ComparisonState.EQUAL
    assert pair_states["node_generator_rank"] is ComparisonState.UNKNOWN
    assert pair_states["rational_evaluation_relation_rank"] is ComparisonState.UNKNOWN
    assert result.pair_84_node_relation_first_difference.state is ComparisonState.UNKNOWN
    paths = {path.name for path in result.report_paths}
    assert "hodgecy_ii_node_relation_blob9.json" in paths
    assert "hodgecy_ii_84_84a_relation_status.md" in paths
    payload = json.loads((report_dir / "hodgecy_ii_node_relation_blob9.json").read_text(encoding="utf-8"))
    assert payload["summaries"]["84a"]["expected_relation_map_shape"] == [165, 112]
    assert "comparison_time" not in json.dumps(payload)
