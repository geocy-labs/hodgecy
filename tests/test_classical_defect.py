from __future__ import annotations

import pytest

from hodgecy.core import EvidenceStatus, ResultKind
from hodgecy.geometry import (
    DefectConvention,
    IdealSource,
    ProjectiveSchemeIdeal,
    SchemeSupportStatus,
    begin_defect_run,
    classical_defect_from_evaluation,
    cross_check_evaluation_methods,
    evaluation_from_hilbert,
    evaluation_from_points,
    ideal_of_points,
    persist_classical_defect_result,
    projective_source_dimension,
    resolve_critical_degree,
)
from hodgecy.storage import ResultStore


VARS4 = ("x0", "x1", "x2", "x3")


def _store(tmp_path) -> ResultStore:
    store = ResultStore(tmp_path / "results.sqlite")
    store.initialize()
    store.add_geometry(geometry_id="fixture", display_name="Fixture", geometry_type="synthetic")
    return store


def _verified_prerequisites() -> dict[str, bool]:
    return {
        "finite_singular_scheme": True,
        "complete_support": True,
        "reducedness": True,
        "ordinary_node_classification": True,
        "exact_node_ideal": True,
        "applicable_double_solid_model": True,
        "certified_critical_degree_rule": True,
        "exact_evaluation_or_hilbert_computation": True,
    }


def test_one_point_evaluation_rank_is_one_and_cokernel_zero() -> None:
    ideal = ideal_of_points([(1, 0, 0, 0)], VARS4, support_status=SchemeSupportStatus.CERTIFIED_SUPPORT)

    for degree in range(4):
        result = evaluation_from_hilbert(ideal, degree)
        assert result.rank == 1
        assert result.target_length == 1
        assert result.cokernel_dimension == 0
        assert result.rank_deficiency == 0


def test_two_points_low_degree_and_eventual_independent_conditions() -> None:
    ideal = ideal_of_points([(1, 0, 0, 0), (0, 1, 0, 0)], VARS4)

    assert [evaluation_from_hilbert(ideal, degree).rank for degree in range(4)] == [1, 2, 2, 2]
    degree_zero = evaluation_from_hilbert(ideal, 0)
    assert degree_zero.cokernel_dimension == 1
    assert degree_zero.rank_deficiency == 0


def test_collinear_and_noncollinear_points_have_different_linear_evaluation_rank() -> None:
    noncollinear = ideal_of_points([(1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0)], VARS4)
    collinear = ideal_of_points([(1, 0, 0, 0), (0, 1, 0, 0), (1, 1, 0, 0)], VARS4)

    assert evaluation_from_hilbert(noncollinear, 1).rank == 3
    assert evaluation_from_hilbert(collinear, 1).rank == 2
    assert evaluation_from_hilbert(collinear, 2).rank == 3


def test_nonreduced_evaluation_data_is_not_automatically_classical_defect() -> None:
    ideal = ProjectiveSchemeIdeal(
        VARS4,
        ("x1**2", "x2", "x3"),
        ideal_source=IdealSource.EXPLICIT,
        scheme_dimension=0,
        scheme_degree=2,
        support_cardinality=1,
        evidence_status=EvidenceStatus.VERIFIED,
    )
    critical = resolve_critical_degree(DefectConvention.NODAL_DOUBLE_SOLID_CLEMENS_CYNK, branch_degree=4)
    evaluation = evaluation_from_hilbert(ideal, critical.critical_degree)
    prerequisites = _verified_prerequisites() | {"reducedness": False, "ordinary_node_classification": False}
    defect = classical_defect_from_evaluation(evaluation, critical_degree=critical, prerequisites=prerequisites)

    assert evaluation.rank == 2
    assert evaluation.cokernel_dimension == 0
    assert defect.classical_defect is None
    assert defect.evidence_status is EvidenceStatus.UNKNOWN


def test_double_solid_critical_degree_rule_and_validation() -> None:
    assert resolve_critical_degree(DefectConvention.NODAL_DOUBLE_SOLID_CLEMENS_CYNK, branch_degree=4).critical_degree == 2
    assert resolve_critical_degree(DefectConvention.NODAL_DOUBLE_SOLID_CLEMENS_CYNK, branch_degree=6).critical_degree == 5
    double_octic = resolve_critical_degree(DefectConvention.NODAL_DOUBLE_SOLID_CLEMENS_CYNK, branch_degree=8)

    assert double_octic.d == 4
    assert double_octic.critical_degree == 8
    assert double_octic.source_dimension == 165
    assert projective_source_dimension(3, 8) == 165
    with pytest.raises(ValueError, match="positive and even"):
        resolve_critical_degree(DefectConvention.NODAL_DOUBLE_SOLID_CLEMENS_CYNK, branch_degree=7)
    with pytest.raises(ValueError, match="base P\\^3"):
        resolve_critical_degree(DefectConvention.NODAL_DOUBLE_SOLID_CLEMENS_CYNK, branch_degree=8, ambient_dimension=4, ambient_base="P^4")


def test_explicit_point_matrix_agrees_with_hilbert_route() -> None:
    points = [(1, 0, 0, 0), (0, 1, 0, 0)]
    ideal = ideal_of_points(points, VARS4, support_status=SchemeSupportStatus.CERTIFIED_SUPPORT)
    hilbert = evaluation_from_hilbert(ideal, 2)
    explicit = evaluation_from_points(points, VARS4, 2)
    cross_check = cross_check_evaluation_methods(hilbert, explicit)

    assert explicit.matrix_shape == (2, 10)
    assert explicit.rank == hilbert.rank == 2
    assert cross_check.agrees is True
    assert cross_check.evidence_status is EvidenceStatus.VERIFIED
    assert cross_check.certificate["certificate_type"] == "hilbert_evaluation_agreement"


def test_verified_classical_defect_requires_all_prerequisites() -> None:
    ideal = ideal_of_points([(1, 0, 0, 0), (0, 1, 0, 0)], VARS4, support_status=SchemeSupportStatus.CERTIFIED_SUPPORT)
    critical = resolve_critical_degree(DefectConvention.NODAL_DOUBLE_SOLID_CLEMENS_CYNK, branch_degree=4)
    evaluation = evaluation_from_hilbert(ideal, critical.critical_degree)

    verified = classical_defect_from_evaluation(evaluation, critical_degree=critical, prerequisites=_verified_prerequisites())
    blocked = classical_defect_from_evaluation(evaluation, critical_degree=critical, prerequisites=_verified_prerequisites() | {"exact_node_ideal": False})

    assert verified.classical_defect == 0
    assert verified.evidence_status is EvidenceStatus.VERIFIED
    assert blocked.classical_defect is None
    assert blocked.evidence_status is EvidenceStatus.UNKNOWN


def test_defect_result_persistence_records_node_geometry_invariants(tmp_path) -> None:
    store = _store(tmp_path)
    ideal = ideal_of_points([(1, 0, 0, 0), (0, 1, 0, 0)], VARS4, support_status=SchemeSupportStatus.CERTIFIED_SUPPORT, geometry_id="fixture")
    critical = resolve_critical_degree(DefectConvention.NODAL_DOUBLE_SOLID_CLEMENS_CYNK, branch_degree=4)
    evaluation = evaluation_from_hilbert(ideal, critical.critical_degree)
    defect = classical_defect_from_evaluation(evaluation, critical_degree=critical, prerequisites=_verified_prerequisites())
    run = begin_defect_run(store, "fixture", input_metadata={"fixture": "two points"}, parameters={"branch_degree": 4})
    certificate, artifact, invariants = persist_classical_defect_result(store, run_id=run.run_id, critical_degree=critical, defect_result=defect)
    store.complete_run(run.run_id)

    by_name = {item.invariant_name: item for item in store.get_invariants(geometry_id="fixture")}
    assert store.get_certificate(certificate.certificate_id).certificate_type == "classical_nodal_defect"
    assert store.get_artifact(artifact.artifact_id, validate_integrity=True).role == "classical_defect_result"
    assert by_name["critical_degree"].value == 2
    assert by_name["evaluation_rank"].value == 2
    assert by_name["classical_defect"].value == 0
    assert by_name["classical_defect"].result_kind is ResultKind.NODE_GEOMETRY
    assert {item.result_kind for item in invariants} == {ResultKind.NODE_GEOMETRY}
