from __future__ import annotations

import pytest

from hodgecy.core import ComparisonState, EvidenceStatus, ResultKind
from hodgecy.geometry import (
    ExactSchemeIdealUnavailableError,
    IdealSource,
    ProjectiveSchemeIdeal,
    ProjectiveHypersurface,
    ProjectivePoint,
    SchemeSupportStatus,
    SingularSchemeResult,
    analyze_projective_singular_scheme,
    begin_hilbert_run,
    compare_hilbert_functions,
    compare_ideals,
    count_standard_monomials,
    groebner_basis_data,
    hilbert_function,
    hilbert_function_range,
    hilbert_polynomial,
    ideal_of_points,
    point_ideal,
    persist_hilbert_table,
)
from hodgecy.storage import ResultStore


VARS = ("x0", "x1", "x2")


def _store(tmp_path) -> ResultStore:
    store = ResultStore(tmp_path / "results.sqlite")
    store.initialize()
    store.add_geometry(geometry_id="fixture", display_name="Fixture", geometry_type="synthetic")
    return store


def test_homogeneous_ideal_validation_rejects_nonhomogeneous_input() -> None:
    with pytest.raises(ValueError, match="not homogeneous"):
        ProjectiveSchemeIdeal(VARS, ("x0 + x1**2",), ideal_source=IdealSource.EXPLICIT)


def test_exact_projective_point_ideal_and_coordinate_normalization() -> None:
    first = point_ideal((1, 2, 3), VARS)
    second = point_ideal((2, 4, 6), VARS)

    assert first.homogeneous_generators == second.homogeneous_generators
    assert first.homogeneous_generators == ("-2*x0 + x1", "-3*x0 + x2")
    assert ProjectivePoint.from_iterable((2, 4, 6)).point_id == "1:2:3"


def test_point_set_ideal_intersection_for_two_points() -> None:
    ideal = ideal_of_points([(1, 0, 0), (0, 1, 0)], VARS)

    assert ideal.ideal_source is IdealSource.POINT_INTERSECTION
    assert ideal.support_status is SchemeSupportStatus.CANDIDATE
    assert ideal.homogeneous_generators == ("x0*x1", "x2")
    assert [hilbert_function(ideal, degree).dim_quotient_d for degree in range(4)] == [1, 2, 2, 2]


def test_groebner_basis_and_standard_monomial_count() -> None:
    ideal = ideal_of_points([(1, 0, 0), (0, 1, 0)], VARS)
    gb = groebner_basis_data(ideal)

    assert gb.backend == "sympy.groebner"
    assert (1, 1, 0) in gb.leading_monomials
    assert count_standard_monomials(3, 2, gb.leading_monomials) == 2


def test_hilbert_function_single_degree_and_range() -> None:
    ideal = ideal_of_points([(1, 0, 0), (0, 1, 0)], VARS)
    value = hilbert_function(ideal, 2)
    table = hilbert_function_range(ideal, start=0, stop=4)

    assert value.dim_S_d == 6
    assert value.dim_I_d == 4
    assert value.dim_quotient_d == 2
    assert table.value_at(4) == 2
    assert table.observed_constant_tail == {"start_degree": 1, "stop_degree": 4, "value": 2, "matches_scheme_degree": True, "certified": False}
    assert table.certified_stabilization_degree is None


def test_one_projective_point_hilbert_function_is_one() -> None:
    ideal = point_ideal((1, 0, 0), VARS)
    assert [hilbert_function(ideal, degree).dim_quotient_d for degree in range(5)] == [1, 1, 1, 1, 1]


def test_three_noncollinear_and_collinear_points_have_different_low_degree_hilbert_functions() -> None:
    noncollinear = ideal_of_points([(1, 0, 0), (0, 1, 0), (0, 0, 1)], VARS)
    collinear = ideal_of_points([(1, 0, 0), (0, 1, 0), (1, 1, 0)], VARS)

    noncollinear_table = hilbert_function_range(noncollinear, stop=3)
    collinear_table = hilbert_function_range(collinear, stop=3)
    comparison = compare_hilbert_functions(noncollinear_table, collinear_table)

    assert [value.dim_quotient_d for value in noncollinear_table.values] == [1, 3, 3, 3]
    assert [value.dim_quotient_d for value in collinear_table.values] == [1, 2, 3, 3]
    assert noncollinear.scheme_degree == collinear.scheme_degree == 3
    assert comparison.state is ComparisonState.DIFFERENT
    assert comparison.first_differing_degree == 1


def test_nonreduced_scheme_degree_exceeds_support_cardinality_without_reducedness_claim() -> None:
    ideal = ProjectiveSchemeIdeal(
        VARS,
        ("x1**2", "x2"),
        ideal_source=IdealSource.EXPLICIT,
        scheme_dimension=0,
        scheme_degree=2,
        support_cardinality=1,
        is_saturated=None,
        evidence_status=EvidenceStatus.VERIFIED,
    )
    table = hilbert_function_range(ideal, stop=4)

    assert [value.dim_quotient_d for value in table.values] == [1, 2, 2, 2, 2]
    assert ideal.scheme_degree == 2
    assert ideal.support_cardinality == 1
    assert hilbert_polynomial(ideal) == "2"
    assert ideal.is_saturated is None


def test_complete_intersection_zero_dimensional_hilbert_values() -> None:
    ideal = ProjectiveSchemeIdeal(
        VARS,
        ("x1**2 - x0*x1", "x2"),
        ideal_source=IdealSource.EXPLICIT,
        scheme_dimension=0,
        scheme_degree=2,
    )
    assert [hilbert_function(ideal, degree).dim_quotient_d for degree in range(4)] == [1, 2, 2, 2]


def test_ideal_equality_and_difference_via_groebner_bases() -> None:
    left = ideal_of_points([(1, 0, 0), (0, 1, 0)], VARS)
    equivalent = ProjectiveSchemeIdeal(VARS, ("x2", "x0*x1"), ideal_source=IdealSource.EXPLICIT)
    different = point_ideal((1, 0, 0), VARS)

    assert compare_ideals(left, equivalent)["state"] == "equal"
    assert compare_ideals(left, different)["state"] == "different"


def test_blob5_conversion_with_exact_ideal_and_failure_without_ideal() -> None:
    exact = analyze_projective_singular_scheme(ProjectiveHypersurface(("x0", "x1", "x2"), "x0*x1"))
    converted = ProjectiveSchemeIdeal.from_singular_scheme(exact, variables=VARS)
    assert converted.ideal_source is IdealSource.JACOBIAN

    missing = SingularSchemeResult(
        geometry_id="missing",
        singular_ideal_generators=(),
        dimension=0,
        degree=112,
        support=(),
        is_zero_dimensional=True,
        is_reduced=None,
        is_complete=None,
        candidate_support_complete=None,
        backend="imported",
        evidence_status=EvidenceStatus.IMPORTED,
    )
    with pytest.raises(ExactSchemeIdealUnavailableError):
        ProjectiveSchemeIdeal.from_singular_scheme(missing, variables=("x", "y", "z", "t"))


def test_hilbert_table_persistence_artifact_round_trip_and_firewall(tmp_path) -> None:
    store = _store(tmp_path)
    ideal = ideal_of_points([(1, 0, 0), (0, 1, 0)], VARS, support_status=SchemeSupportStatus.CERTIFIED_SUPPORT, geometry_id="fixture")
    table = hilbert_function_range(ideal, stop=3)
    run = begin_hilbert_run(store, "fixture", input_metadata=ideal.to_dict(), parameters={"stop": 3})
    certificate, artifact, invariants = persist_hilbert_table(store, run_id=run.run_id, ideal=ideal, table=table)
    store.complete_run(run.run_id)

    restored = store.get_certificate(certificate.certificate_id)
    by_name = {item.invariant_name: item for item in store.get_invariants(geometry_id="fixture")}
    assert store.get_artifact(artifact.artifact_id, validate_integrity=True).role == "hilbert_function_table"
    assert restored.evidence["firewall"]["no_classical_defect_asserted"] is True
    assert by_name["scheme_ideal_hash"].result_kind is ResultKind.NODE_GEOMETRY
    assert by_name["hilbert_function_table"].value["values"][2]["dim_quotient_d"] == 2
    assert by_name["hilbert_polynomial"].value == "2"
    assert {item.result_kind for item in invariants} == {ResultKind.NODE_GEOMETRY}
    assert not store.get_invariants(geometry_id="fixture", result_kind=ResultKind.NODE_RELATION)
