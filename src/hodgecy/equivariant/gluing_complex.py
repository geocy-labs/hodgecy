"""Stratified gluing complex for arrangement incidence data."""

from __future__ import annotations

import sympy as sp


def build_gluing_matrix(double_lines: list[dict], multiple_points: list[dict]) -> sp.Matrix:
    """Build the multiple-point by double-line incidence matrix."""
    entries = []
    for point in multiple_points:
        point_planes = set(point["planes"])
        entries.append([1 if set(line["planes"]).issubset(point_planes) else 0 for line in double_lines])
    return sp.Matrix(entries)


def rank_over_Q(matrix: sp.Matrix) -> int:
    return int(matrix.rank())


def rank_mod_p(matrix: sp.Matrix, p: int = 2) -> int:
    rows = [[int(matrix[row, col]) % p for col in range(matrix.cols)] for row in range(matrix.rows)]
    if not rows:
        return 0
    rank = 0
    pivot_row = 0
    for col in range(matrix.cols):
        pivot = None
        for row in range(pivot_row, matrix.rows):
            if rows[row][col] % p != 0:
                pivot = row
                break
        if pivot is None:
            continue
        rows[pivot_row], rows[pivot] = rows[pivot], rows[pivot_row]
        inv = pow(rows[pivot_row][col], -1, p)
        rows[pivot_row] = [(value * inv) % p for value in rows[pivot_row]]
        for row in range(matrix.rows):
            if row == pivot_row or rows[row][col] % p == 0:
                continue
            factor = rows[row][col] % p
            rows[row] = [(left - factor * right) % p for left, right in zip(rows[row], rows[pivot_row])]
        rank += 1
        pivot_row += 1
    return rank


def kernel_dimension_Q(matrix: sp.Matrix) -> int:
    return int(matrix.cols - rank_over_Q(matrix))


def cokernel_dimension_Q(matrix: sp.Matrix) -> int:
    return int(matrix.rows - rank_over_Q(matrix))


def smith_normal_form_invariants(matrix: sp.Matrix) -> list[int] | None:
    try:
        from sympy.matrices.normalforms import smith_normal_form

        normal = smith_normal_form(matrix, domain=sp.ZZ)
    except Exception:
        return None
    invariants = []
    for index in range(min(normal.rows, normal.cols)):
        value = int(abs(normal[index, index]))
        if value:
            invariants.append(value)
    return invariants


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
