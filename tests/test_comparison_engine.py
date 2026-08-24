from __future__ import annotations

import pytest

from hodgecy.comparison import AmbiguousResultError, ComparisonEngine, ComparisonPolicy, RunSelectionPolicy, canonical_value
from hodgecy.core import (
    ComparisonState,
    ConifoldAtomSpectrum,
    EvidenceStatus,
    ResultKind,
    ResultMetadata,
    SmoothHodgeAtomSpectrum,
    SourceAssemblySpectrum,
)
from hodgecy.storage import ResultStore


def make_store(tmp_path) -> ResultStore:
    store = ResultStore(tmp_path / "results.sqlite")
    store.initialize()
    return store


def add_geometry(store: ResultStore, geometry_id: str) -> None:
    store.add_geometry(geometry_id=geometry_id, display_name=f"Synthetic {geometry_id}", geometry_type="synthetic")


def add_run_with_invariants(
    store: ResultStore,
    geometry_id: str,
    values: dict[str, object],
    *,
    statuses: dict[str, EvidenceStatus] | None = None,
    calculation_type: str = "source_assembly",
):
    try:
        store.get_geometry(geometry_id)
    except Exception:
        add_geometry(store, geometry_id)
    run = store.begin_run(geometry_id=geometry_id, calculation_type=calculation_type, git_commit="test")
    for name, value in values.items():
        store.record_invariant(
            run_id=run.run_id,
            name=name,
            value=value,
            result_kind=ResultKind.SOURCE_ASSEMBLY,
            evidence_status=(statuses or {}).get(name, EvidenceStatus.COMPUTED),
        )
    return store.complete_run(run.run_id)


def test_pair_equality_difference_unknown_and_evidence_preservation(tmp_path) -> None:
    store = make_store(tmp_path)
    add_run_with_invariants(store, "A", {"source_rank": 8, "source_snf": [1, 2]}, statuses={"source_rank": EvidenceStatus.VERIFIED})
    add_run_with_invariants(store, "B", {"source_rank": 8, "source_snf": [1, 3]}, statuses={"source_rank": EvidenceStatus.COMPUTED})
    add_run_with_invariants(store, "C", {"source_rank": None}, statuses={"source_rank": EvidenceStatus.UNKNOWN})
    engine = ComparisonEngine(store)

    equal = engine.compare_invariant(("A", "B"), "source_rank")
    different = engine.compare_invariant(("A", "B"), "source_snf")
    unknown = engine.compare_invariant(("A", "C"), "source_rank")

    assert equal.state is ComparisonState.EQUAL
    assert equal.left_status is EvidenceStatus.VERIFIED
    assert equal.right_status is EvidenceStatus.COMPUTED
    assert different.state is ComparisonState.DIFFERENT
    assert unknown.state is ComparisonState.UNKNOWN


def test_pair_report_and_first_difference(tmp_path) -> None:
    store = make_store(tmp_path)
    add_run_with_invariants(store, "A", {"h11": 1, "h21": 2, "source_rank": 8, "source_snf": [1, 1]})
    add_run_with_invariants(store, "B", {"h11": 1, "h21": 2, "source_rank": 8, "source_snf": [1, 2]})
    engine = ComparisonEngine(store)

    report = engine.compare_pair("A", "B", invariants=["h11", "h21", "source_rank", "source_snf"])
    first = engine.first_difference(("A", "B"), ["h11", "h21", "source_rank", "source_snf"])

    assert report.first_difference == "source_snf"
    assert "| source_snf | different |" in report.to_markdown()
    assert first.first_difference == "source_snf"
    assert first.state is ComparisonState.DIFFERENT


def test_multi_member_set_comparison_equivalence_groups(tmp_path) -> None:
    store = make_store(tmp_path)
    add_run_with_invariants(store, "X1", {"source_rank": 8})
    add_run_with_invariants(store, "X2", {"source_rank": 8})
    add_run_with_invariants(store, "X3", {"source_rank": 9})
    add_run_with_invariants(store, "X4", {"source_rank": None}, statuses={"source_rank": EvidenceStatus.UNKNOWN})
    comparison_set = store.create_comparison_set(display_name="four synthetic", member_geometry_ids=["X1", "X2", "X3", "X4"])
    engine = ComparisonEngine(store)

    result = engine.compare_set(comparison_set.comparison_set_id, invariants=["source_rank"])[0]

    assert result.state is ComparisonState.DIFFERENT
    assert result.equivalence_groups[canonical_value(8)] == ("X1", "X2")
    assert result.equivalence_groups[canonical_value(9)] == ("X3",)
    assert result.unknown_members == ("X4",)


def test_equivalence_classes_and_progressive_refinement(tmp_path) -> None:
    store = make_store(tmp_path)
    add_run_with_invariants(store, "A", {"h11": 1, "h21": 2, "source_rank": 8, "source_snf": [1, 1]})
    add_run_with_invariants(store, "B", {"h11": 1, "h21": 2, "source_rank": 8, "source_snf": [1, 1]})
    add_run_with_invariants(store, "C", {"h11": 1, "h21": 2, "source_rank": 9, "source_snf": [1, 2]})
    add_run_with_invariants(store, "D", {"h11": 2, "h21": 2, "source_rank": 9, "source_snf": [1, 2]})
    engine = ComparisonEngine(store)

    coarse = engine.group_by_invariants(["A", "B", "C", "D"], ["h11", "h21"])
    refined = engine.classify(["A", "B", "C", "D"], levels=[["h11", "h21"], ["source_rank"], ["source_snf"]])

    assert sorted(len(item.member_geometry_ids) for item in coarse.classes) == [1, 3]
    assert [sorted(len(item.member_geometry_ids) for item in level.classes) for level in refined.levels] == [[1, 3], [1, 1, 2], [1, 1, 2]]


def test_superseded_runs_and_explicit_historical_run(tmp_path) -> None:
    store = make_store(tmp_path)
    old_run = add_run_with_invariants(store, "A", {"source_rank": 7})
    new_run = add_run_with_invariants(store, "A", {"source_rank": 8})
    store.supersede_run(old_run.run_id, superseded_by_run_id=new_run.run_id, reason="corrected synthetic value")
    peer_run = add_run_with_invariants(store, "B", {"source_rank": 8})
    engine = ComparisonEngine(store)

    current = engine.compare_invariant(("A", "B"), "source_rank")
    historical = engine.compare_invariant(("A", "B"), "source_rank", run_ids={"A": old_run.run_id, "B": peer_run.run_id})

    assert current.state is ComparisonState.EQUAL
    assert current.left_value == 8
    assert historical.state is ComparisonState.DIFFERENT
    assert historical.left_value == 7


def test_ambiguous_current_results_do_not_choose_arbitrarily(tmp_path) -> None:
    store = make_store(tmp_path)
    add_run_with_invariants(store, "A", {"source_rank": 8})
    add_run_with_invariants(store, "A", {"source_rank": 9})
    add_run_with_invariants(store, "B", {"source_rank": 8})
    policy = ComparisonPolicy(run_selection=RunSelectionPolicy.ALL_CURRENT_STRICT)
    engine = ComparisonEngine(store, policy)

    with pytest.raises(AmbiguousResultError):
        engine.compare_invariant(("A", "B"), "source_rank")


def source_spectrum(geometry_id: str, value: object) -> SourceAssemblySpectrum:
    return SourceAssemblySpectrum(ResultMetadata(geometry_id, ResultKind.SOURCE_ASSEMBLY, evidence_status=EvidenceStatus.COMPUTED), payload={"terms": value})


def test_spectrum_equality_inequality_and_cross_kind_firewall(tmp_path) -> None:
    store = make_store(tmp_path)
    add_geometry(store, "A")
    add_geometry(store, "B")
    run_a = store.complete_run(store.begin_run(geometry_id="A", calculation_type="spectrum", git_commit="test").run_id)
    run_b = store.complete_run(store.begin_run(geometry_id="B", calculation_type="spectrum", git_commit="test").run_id)
    spec_a = store.record_spectrum(run_id=run_a.run_id, spectrum=source_spectrum("A", [1, 2]))
    spec_b_same = store.record_spectrum(run_id=run_b.run_id, spectrum=source_spectrum("B", [1, 2]))
    spec_b_diff = store.record_spectrum(run_id=run_b.run_id, spectrum=source_spectrum("B", [1, 3]))
    conifold = store.record_spectrum(
        run_id=run_b.run_id,
        spectrum=ConifoldAtomSpectrum(ResultMetadata("B", ResultKind.CONIFOLD_ATOM, evidence_status=EvidenceStatus.COMPUTED), payload={"terms": [1, 2]}),
    )
    smooth = store.record_spectrum(
        run_id=run_b.run_id,
        spectrum=SmoothHodgeAtomSpectrum(ResultMetadata("B", ResultKind.SMOOTH_HODGE_ATOM, evidence_status=EvidenceStatus.COMPUTED), payload={"terms": [1, 2]}),
    )
    engine = ComparisonEngine(store)

    equal = engine.compare_spectra(spec_a.spectrum_id, spec_b_same.spectrum_id)
    different = engine.compare_spectra(spec_a.spectrum_id, spec_b_diff.spectrum_id)
    cross_conifold = engine.compare_spectra(spec_a.spectrum_id, conifold.spectrum_id)
    cross_smooth = engine.compare_spectra(spec_a.spectrum_id, smooth.spectrum_id)

    assert equal.state is ComparisonState.EQUAL
    assert different.state is ComparisonState.DIFFERENT
    assert different.evidence["field_differences"]
    assert cross_conifold.state is ComparisonState.INCOMPARABLE
    assert cross_smooth.state is ComparisonState.INCOMPARABLE


def test_result_kind_firewall_for_numerically_equal_different_invariants(tmp_path) -> None:
    store = make_store(tmp_path)
    add_geometry(store, "A")
    run = store.complete_run(store.begin_run(geometry_id="A", calculation_type="mixed", git_commit="test").run_id)
    store.record_invariant(run_id=run.run_id, name="source_rank", value=8, result_kind=ResultKind.SOURCE_ASSEMBLY, evidence_status=EvidenceStatus.COMPUTED)
    store.record_invariant(run_id=run.run_id, name="node_relation_rank", value=8, result_kind=ResultKind.NODE_RELATION, evidence_status=EvidenceStatus.COMPUTED)
    engine = ComparisonEngine(store)

    result = engine.compare_invariant(("A", "A"), "source_rank", result_kind=ResultKind.SOURCE_ASSEMBLY)
    node = engine.compare_invariant(("A", "A"), "node_relation_rank", result_kind=ResultKind.NODE_RELATION)

    assert result.state is ComparisonState.EQUAL
    assert node.state is ComparisonState.EQUAL
    assert result.result_kind is not node.result_kind
