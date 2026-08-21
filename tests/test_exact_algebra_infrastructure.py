from __future__ import annotations

import pytest
import sympy as sp

from hodgecy.algebra import ExactMatrixRef, kernel_cokernel_result_q, rank_mod_p_result, rank_over_q_result, smith_normal_form_result
from hodgecy.assemblies import summarize_gluing_matrix, summarize_single_boundary
from hodgecy.core import HodgeCYID, IdentityKind, ValidationError, stable_sha256
from hodgecy.equivariant.gluing_complex import cokernel_dimension_Q, kernel_dimension_Q, rank_mod_p, rank_over_Q, smith_normal_form_invariants
from hodgecy.math import Basis, BasisArray, BasisMatrix, CoefficientDomain


def _basis(label: str, *, dimension: int = 2) -> Basis:
    return Basis(
        HodgeCYID.derived_from_components(IdentityKind.DERIVED_OBJECT, "test_basis", {"label": label}),
        "H2",
        CoefficientDomain.integers(),
        tuple(f"e{i}" for i in range(dimension)),
        source="blob8-fixture",
    )


def test_basis_array_preserves_axes_and_refuses_cross_basis_comparison() -> None:
    left = _basis("left")
    right = _basis("right")
    matrix = BasisMatrix(left, left, ((1, 2), (3, 4)))
    same = BasisArray.from_matrix("intersection_fixture", matrix)
    same_again = BasisArray.from_matrix("intersection_fixture", matrix)
    different = BasisArray.from_matrix("intersection_fixture", BasisMatrix(right, right, ((1, 2), (3, 4))))

    assert same.shape == (2, 2)
    assert same.entry_count == 4
    assert same.equal_entries_in_same_axes(same_again) is True
    assert same.to_dict(include_entries=False)["entries"] is None
    assert same.to_dict()["entries_hash"] == stable_sha256((1, 2, 3, 4))
    with pytest.raises(ValidationError):
        same.equal_entries_in_same_axes(different)


def test_exact_algebra_results_match_legacy_equivariant_helpers() -> None:
    matrix = sp.Matrix([[2, 4, 6], [0, 6, 12]])
    matrix_ref = ExactMatrixRef.from_sympy_matrix(matrix, label="fixture-boundary")

    assert rank_over_q_result(matrix, matrix_ref=matrix_ref).rank == rank_over_Q(matrix) == 2
    assert rank_mod_p_result(matrix, p=2, matrix_ref=matrix_ref).rank == rank_mod_p(matrix, p=2) == 0
    assert rank_mod_p_result(matrix, p=3, matrix_ref=matrix_ref).rank == rank_mod_p(matrix, p=3) == 1
    assert kernel_cokernel_result_q(matrix, matrix_ref=matrix_ref).kernel_dimension == kernel_dimension_Q(matrix) == 1
    assert kernel_cokernel_result_q(matrix, matrix_ref=matrix_ref).cokernel_dimension == cokernel_dimension_Q(matrix) == 0
    assert smith_normal_form_result(matrix, matrix_ref=matrix_ref).invariants == smith_normal_form_invariants(matrix) == [2, 6]

    payload = rank_over_q_result(matrix, matrix_ref=matrix_ref).to_dict()
    assert payload["schema_version"]["value"] == "exact_algebra_result.v1"
    assert payload["matrix_ref"]["label"] == "fixture-boundary"


def test_modular_rank_requires_prime_modulus() -> None:
    with pytest.raises(ValueError):
        rank_mod_p_result(sp.Matrix([[2]]), p=4)


def test_chain_and_gluing_assembly_summaries_are_queryable_payloads() -> None:
    matrix = sp.Matrix([[1, 0, 1], [0, 1, 1]])
    summary = summarize_single_boundary("fixture_gluing", matrix, rank_primes=(2, 3))
    operations = [result.operation.value for result in summary.exact_results]

    assert summary.schema_version.value == "assembly_summary.v1"
    assert operations == ["rank_Q", "rank_mod_p", "rank_mod_p", "kernel_cokernel_Q", "smith_normal_form"]
    assert summary.to_dict()["metadata"]["boundary_count"] == 1

    gluing = summarize_gluing_matrix(matrix, label="fixture_gluing")
    assert gluing.rank_Q == 2
    assert gluing.rank_F2 == 2
    assert gluing.kernel_dim_Q == 1
    assert gluing.cokernel_dim_Q == 0
    assert gluing.smith_normal_form == [1, 1]


def test_basis_matrix_ref_carries_basis_identity() -> None:
    row_basis = _basis("rows", dimension=2)
    column_basis = _basis("cols", dimension=3)
    matrix = BasisMatrix(row_basis, column_basis, ((1, 0, 1), (0, 1, 1)))
    ref = ExactMatrixRef.from_basis_matrix(matrix, label="basis-aware-boundary")

    assert ref.shape == (2, 3)
    assert ref.row_basis_id == row_basis.basis_id
    assert ref.column_basis_id == column_basis.basis_id
    assert ref.to_dict()["coefficient_domain"] == "Z"
