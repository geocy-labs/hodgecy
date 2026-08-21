"""Stratified gluing complex for arrangement incidence data."""

from __future__ import annotations

import sympy as sp

from hodgecy.algebra.results import kernel_cokernel_result_q, rank_mod_p_result, rank_over_q_result, smith_normal_form_result


def build_gluing_matrix(double_lines: list[dict], multiple_points: list[dict]) -> sp.Matrix:
    """Build the multiple-point by double-line incidence matrix."""
    entries = []
    for point in multiple_points:
        point_planes = set(point["planes"])
        entries.append([1 if set(line["planes"]).issubset(point_planes) else 0 for line in double_lines])
    return sp.Matrix(entries)


def rank_over_Q(matrix: sp.Matrix) -> int:
    return rank_over_q_result(matrix).rank


def rank_mod_p(matrix: sp.Matrix, p: int = 2) -> int:
    return rank_mod_p_result(matrix, p=p).rank


def kernel_dimension_Q(matrix: sp.Matrix) -> int:
    return kernel_cokernel_result_q(matrix).kernel_dimension


def cokernel_dimension_Q(matrix: sp.Matrix) -> int:
    return kernel_cokernel_result_q(matrix).cokernel_dimension


def smith_normal_form_invariants(matrix: sp.Matrix) -> list[int] | None:
    return smith_normal_form_result(matrix).invariants


def row_degree_distribution(matrix: sp.Matrix) -> dict[int, int]:
    distribution: dict[int, int] = {}
    for row in range(matrix.rows):
        degree = int(sum(matrix[row, col] for col in range(matrix.cols)))
        distribution[degree] = distribution.get(degree, 0) + 1
    return dict(sorted(distribution.items()))


def column_degree_distribution(matrix: sp.Matrix) -> dict[int, int]:
    distribution: dict[int, int] = {}
    for col in range(matrix.cols):
        degree = int(sum(matrix[row, col] for row in range(matrix.rows)))
        distribution[degree] = distribution.get(degree, 0) + 1
    return dict(sorted(distribution.items()))
