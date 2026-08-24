from __future__ import annotations

import pytest
import sympy as sp

from hodgecy.algebra import (
    InfiniteIndexError,
    IntegerLinearMap,
    IntegerMatrixError,
    LatticeComparisonState,
    LatticeContainmentError,
    MatrixSemanticRole,
    UnsupportedExactDomainError,
    begin_integer_lattice_run,
    compare_lattices,
    image_lattice,
    integer_kernel,
    lattice_index,
    modular_rank,
    modular_rank_profile,
    persist_integer_linear_map_analysis,
    rational_rank,
    same_rational_span,
    saturation_of_image,
    smith_normal_form_data,
)
from hodgecy.core import EvidenceStatus, ResultKind
from hodgecy.storage import ResultStore


def _store(tmp_path) -> ResultStore:
    store = ResultStore(tmp_path / "results.sqlite")
    store.initialize()
    store.add_geometry(geometry_id="fixture", display_name="Fixture", geometry_type="synthetic")
    return store


def test_integer_entry_validation_rejects_approximate_and_symbolic_values() -> None:
    assert IntegerLinearMap([[sp.Integer(2), -3]]).matrix == ((2, -3),)
    with pytest.raises(UnsupportedExactDomainError):
        IntegerLinearMap([[1.2]])
    with pytest.raises(UnsupportedExactDomainError):
        IntegerLinearMap([[sp.Rational(1, 2)]])
    with pytest.raises(UnsupportedExactDomainError):
        IntegerLinearMap([[sp.Symbol("x")]])
    with pytest.raises(UnsupportedExactDomainError):
        IntegerLinearMap([[True]])


def test_row_column_convention_and_primitive_surjection() -> None:
    linear_map = IntegerLinearMap([[1, 1, -1]], semantic_role=MatrixSemanticRole.USER_SUPPLIED)
    rank = rational_rank(linear_map)
    kernel = integer_kernel(linear_map)
    snf = smith_normal_form_data(linear_map)
    image = image_lattice(linear_map)

    assert linear_map.domain_rank == 3
    assert linear_map.codomain_rank == 1
    assert rank.rank == 1
    assert rank.nullity == 2
    assert kernel.rank == 2
    assert sp.Matrix(linear_map.matrix) * sp.Matrix(kernel.basis) == sp.zeros(1, 2)
    assert snf.cokernel.free_rank == 0
    assert snf.cokernel.torsion_invariant_factors == ()
    assert image.saturation.index == 1
    assert image.saturation.is_saturated is True


def test_pure_torsion_snf_cokernel_and_saturation() -> None:
    linear_map = IntegerLinearMap([[2, 0], [0, 4]])
    snf = smith_normal_form_data(linear_map)
    image = image_lattice(linear_map)

    assert snf.diagonal_invariant_factors == (2, 4)
    assert snf.torsion_invariant_factors == (2, 4)
    assert snf.cokernel.free_rank == 0
    assert snf.cokernel.torsion_order == 8
    assert snf.cokernel.torsion_primes == (2,)
    assert image.saturation.basis == ((1, 0), (0, 1))
    assert image.saturation.index == 8
    assert image.saturation.is_saturated is False


def test_free_plus_torsion_cokernel() -> None:
    linear_map = IntegerLinearMap([[2, 0], [0, 0]])
    snf = smith_normal_form_data(linear_map)

    assert snf.rank == 1
    assert snf.cokernel.free_rank == 1
    assert snf.cokernel.torsion_invariant_factors == (2,)
    assert snf.cokernel.to_dict()["structure"] == "Z + Z/2Z"


def test_primitive_rank_one_image_is_saturated_in_rational_span() -> None:
    linear_map = IntegerLinearMap([[2, 4], [1, 2]])
    snf = smith_normal_form_data(linear_map)
    image = image_lattice(linear_map)

    assert rational_rank(linear_map).rank == 1
    assert snf.diagonal_invariant_factors == (1,)
    assert snf.cokernel.free_rank == 1
    assert snf.cokernel.is_torsion_free is True
    assert image.basis == ((2,), (1,))
    assert image.saturation.index == 1


def test_zero_and_rectangular_matrices() -> None:
    zero = IntegerLinearMap(sp.zeros(2, 3))
    tall = IntegerLinearMap([[1, 0], [0, 1], [0, 0]])
    wide = IntegerLinearMap([[1, 0, 0], [0, 1, 0]])

    assert rational_rank(zero).rank == 0
    assert integer_kernel(zero).rank == 3
    assert smith_normal_form_data(zero).cokernel.free_rank == 2
    assert rational_rank(tall).rank == 2
    assert smith_normal_form_data(tall).cokernel.free_rank == 1
    assert rational_rank(wide).rank == 2
    assert integer_kernel(wide).rank == 1


def test_modular_rank_prime_validation_and_rank_drop() -> None:
    linear_map = IntegerLinearMap([[2, 0], [0, 1]])

    assert rational_rank(linear_map).rank == 2
    assert modular_rank(linear_map, 2).rank == 1
    assert modular_rank(linear_map, 3).rank == 2
    profile = modular_rank_profile(linear_map, primes=(2, 3, 5))
    assert {p: result.rank for p, result in profile.items()} == {2: 1, 3: 2, 5: 2}
    with pytest.raises(IntegerMatrixError):
        modular_rank(linear_map, 4)


def test_same_rational_span_different_integral_lattice_and_index() -> None:
    l1 = IntegerLinearMap([[1, 0], [0, 1]])
    l2 = IntegerLinearMap([[2, 0], [0, 1]])

    assert same_rational_span(l1, l2) is True
    comparison = compare_lattices(l1, l2)
    assert comparison.state is LatticeComparisonState.DIFFERENT
    assert comparison.same_rational_span is True
    assert lattice_index(l2, l1) == 2
    with pytest.raises(LatticeContainmentError):
        lattice_index(l1, l2)


def test_unimodularly_related_bases_define_same_embedded_lattice() -> None:
    left = IntegerLinearMap([[1, 0], [0, 1]])
    right = IntegerLinearMap([[1, 1], [0, 1]])

    comparison = compare_lattices(left, right)
    assert comparison.state is LatticeComparisonState.EQUAL
    assert comparison.index == 1
    assert lattice_index(left, right) == 1


def test_incomparable_or_infinite_index_cases_fail_clearly() -> None:
    rank_one = IntegerLinearMap([[1], [0]])
    rank_two = IntegerLinearMap([[1, 0], [0, 1]])
    ambient_three = IntegerLinearMap([[1], [0], [0]])

    assert compare_lattices(rank_one, ambient_three).state is LatticeComparisonState.INCOMPARABLE
    with pytest.raises(InfiniteIndexError):
        lattice_index(rank_one, rank_two)


def test_snf_transform_verification_and_deterministic_hashing() -> None:
    first = IntegerLinearMap([[2, 4, 6], [0, 6, 12]], semantic_role="source_assembly")
    second = IntegerLinearMap([[2, 4, 6], [0, 6, 12]], semantic_role="node_relation")
    snf = smith_normal_form_data(first)

    assert first.matrix_hash == second.matrix_hash
    assert first.semantic_role != second.semantic_role
    assert snf.diagonal_invariant_factors == (2, 6)
    assert snf.transform_verification["U_A_V_equals_D"] is True
    assert snf.transform_verification["left_unimodular"] is True
    assert snf.transform_verification["right_unimodular"] is True


def test_persistence_round_trip_and_caller_supplied_result_kind(tmp_path) -> None:
    store = _store(tmp_path)
    linear_map = IntegerLinearMap([[2, 0], [0, 4]], semantic_role=MatrixSemanticRole.SOURCE_ASSEMBLY, provenance="synthetic fixture")
    run = begin_integer_lattice_run(store, "fixture", input_metadata=linear_map.to_dict(), parameters={"primes": [2, 3]})
    certificate, artifacts, invariants = persist_integer_linear_map_analysis(
        store,
        run_id=run.run_id,
        linear_map=linear_map,
        result_kind=ResultKind.SOURCE_ASSEMBLY,
        modular_primes=(2, 3),
    )
    store.complete_run(run.run_id)

    by_name = {item.invariant_name: item for item in store.get_invariants(geometry_id="fixture")}
    assert store.get_certificate(certificate.certificate_id).certificate_type == "exact_integer_matrix"
    assert {artifact.role for artifact in artifacts} == {"raw_integer_matrix", "integer_kernel_basis", "image_lattice_basis"}
    assert by_name["rank_Q"].value == 2
    assert by_name["smith_normal_form"].value == [2, 4]
    assert by_name["cokernel_structure"].value["torsion_order"] == 8
    assert by_name["saturation_index"].value == 8
    assert {item.result_kind for item in invariants} == {ResultKind.SOURCE_ASSEMBLY}


def test_source_vs_node_firewall_is_caller_level_not_matrix_level(tmp_path) -> None:
    store = _store(tmp_path)
    linear_map = IntegerLinearMap([[1, 0]], semantic_role=MatrixSemanticRole.SOURCE_ASSEMBLY)
    run = begin_integer_lattice_run(store, "fixture", input_metadata=linear_map.to_dict())
    _, _, invariants = persist_integer_linear_map_analysis(store, run_id=run.run_id, linear_map=linear_map, result_kind=ResultKind.NODE_GEOMETRY)
    store.complete_run(run.run_id)

    assert {item.result_kind for item in invariants} == {ResultKind.NODE_GEOMETRY}
    assert {item.notes for item in invariants if item.invariant_name == "rank_Q"}.pop().endswith("semantic_role=source_assembly")
