"""Incidence-table utilities for eight-plane double-octic arrangements."""

from __future__ import annotations

from itertools import combinations
from typing import Any

import sympy as sp
from sympy.polys.polyerrors import PolynomialError

from .linear_forms import linear_forms_from_factor_texts

LinearForm = dict[str, Any]
Quadruple = tuple[int, int, int, int]


def _rank(linear_forms: list[LinearForm], indices: tuple[int, ...]) -> int:
    rows = [[sp.sympify(value) for value in linear_forms[index]["coefficients"]] for index in indices]
    return generic_matrix_rank(sp.Matrix(rows)) if rows else 0


def generic_matrix_rank(matrix: sp.Matrix) -> int:
    """Return the exact generic rank by symbolic minor nonvanishing.

    Entries may live in Q, a rational function field over parameters, an
    algebraic number field represented by SymPy radicals, or a mixture of
    algebraic constants and parameters.  No floating-point evaluation is used.
    """

    max_rank = min(int(matrix.rows), int(matrix.cols))
    if max_rank == 0:
        return 0
    for rank in range(max_rank, 0, -1):
        for row_indices in combinations(range(matrix.rows), rank):
            for col_indices in combinations(range(matrix.cols), rank):
                minor = matrix.extract(row_indices, col_indices).det()
                if not is_identically_zero(minor):
                    return rank
    return 0


def is_identically_zero(value: Any) -> bool:
    """Return whether an exact expression is identically zero."""

    expr = sp.cancel(sp.factor(sp.together(sp.sympify(value))))
    if expr == 0:
        return True
    if expr.is_zero is True:
        return True
    if expr.is_number:
        return sp.simplify(expr) == 0
    try:
        numerator, denominator = sp.fraction(expr)
        return sp.Poly(numerator, *sorted(numerator.free_symbols, key=lambda symbol: symbol.name)).is_zero
    except (PolynomialError, ValueError):
        return sp.simplify(expr) == 0


def parse_linear_forms_from_record(record: dict) -> list[LinearForm]:
    """Return normalized linear-form records with zero-based plane indices."""
    forms = []
    for index, form in enumerate(record.get("linear_forms", [])):
        coefficients = [sp.Rational(value) for value in form["coefficients"]]
        forms.append(
            {
                "index": index,
                "label": form.get("label", f"p{index + 1}"),
                "coefficients": coefficients,
                "equation": form.get("equation"),
            }
        )
    if len(forms) != 8:
        if record.get("linear_factor_texts"):
            return linear_forms_from_factor_texts(record)
        raise ValueError(f"Expected 8 linear forms, found {len(forms)}.")
    return forms


def incidence_table_from_linear_forms(linear_forms: list[LinearForm]) -> list[Quadruple]:
    """Return sorted quadruples of planes with nonempty projective intersection."""
    table = []
    for quadruple in combinations(range(len(linear_forms)), 4):
        if _rank(linear_forms, quadruple) <= 3:
            table.append(tuple(quadruple))
    return sorted(table)


def minimal_incidence_table(incidence_table: list[Quadruple]) -> list[Quadruple]:
    """Return a canonical sorted incidence table without duplicate quadruples."""
    return sorted({tuple(sorted(quadruple)) for quadruple in incidence_table})


def _planes_containing_flat(linear_forms: list[LinearForm], seed: tuple[int, ...], rank: int, rank_func=None) -> tuple[int, ...]:
    rank_func = rank_func or (lambda indices: _rank(linear_forms, indices))
    containing = set(seed)
    for index in range(len(linear_forms)):
        candidate = tuple(sorted(containing | {index}))
        if rank_func(candidate) == rank:
            containing.add(index)
    return tuple(sorted(containing))


def _rref_key(linear_forms: list[LinearForm], indices: tuple[int, ...]) -> str:
    matrix = sp.Matrix([[sp.sympify(value) for value in linear_forms[index]["coefficients"]] for index in indices])
    reduced, _ = matrix.rref()
    rows = []
    for row_index in range(reduced.rows):
        row = tuple(reduced[row_index, col_index] for col_index in range(reduced.cols))
        if any(value != 0 for value in row):
            rows.append(row)
    return "|".join(",".join(str(value) for value in row) for row in rows)


def singular_strata_from_incidence_table(incidence_table: list[Quadruple], linear_forms: list[LinearForm] | None = None) -> dict:
    """Recover singular strata from exact ranks when linear forms are provided."""
    if linear_forms is None:
        points = sorted({tuple(sorted(quadruple)) for quadruple in incidence_table})
        return {
            "double_lines": [],
            "triple_lines": [],
            "multiple_points": [{"point_id": f"q{index + 1:02d}", "planes": list(point), "multiplicity": len(point)} for index, point in enumerate(points)],
            "inventory": {"p3": 0, "p4_0": len(points), "p4_1": 0, "p5_0": 0, "p5_1": 0, "p5_2": 0, "double_lines": 0, "triple_lines": 0},
        }

    rank_cache: dict[tuple[int, ...], int] = {}

    def rank_indices(indices: tuple[int, ...]) -> int:
        key = tuple(sorted(indices))
        if key not in rank_cache:
            rank_cache[key] = _rank(linear_forms, key)
        return rank_cache[key]

    line_by_key: dict[str, tuple[int, ...]] = {}
    for pair in combinations(range(len(linear_forms)), 2):
        if rank_indices(pair) != 2:
            continue
        planes = _planes_containing_flat(linear_forms, pair, rank=2, rank_func=rank_indices)
        line_by_key[_rref_key(linear_forms, planes)] = planes

    point_by_key: dict[str, tuple[int, ...]] = {}
    for triple in combinations(range(len(linear_forms)), 3):
        if rank_indices(triple) != 3:
            continue
        planes = _planes_containing_flat(linear_forms, triple, rank=3, rank_func=rank_indices)
        if len(planes) >= 3:
            point_by_key[_rref_key(linear_forms, planes)] = planes

    double_lines = []
    triple_lines = []
    for line_index, planes in enumerate(sorted(line_by_key.values()), start=1):
        record = {"line_id": f"L{line_index:02d}", "planes": list(planes), "multiplicity": len(planes)}
        if len(planes) == 3:
            triple_lines.append(record)
        else:
            double_lines.append(record)

    all_lines = [*double_lines, *triple_lines]
    multiple_points = []
    for point_index, planes in enumerate(sorted(point_by_key.values()), start=1):
        incident_lines = [line["line_id"] for line in all_lines if set(line["planes"]).issubset(planes)]
        multiple_points.append(
            {
                "point_id": f"q{point_index:02d}",
                "planes": list(planes),
                "multiplicity": len(planes),
                "incident_double_lines": sorted(incident_lines),
            }
        )

    inventory = {
        "p3": sum(1 for point in multiple_points if point["multiplicity"] == 3),
        "p4_0": sum(1 for point in multiple_points if point["multiplicity"] == 4),
        "p4_1": 0,
        "p5_0": sum(1 for point in multiple_points if point["multiplicity"] == 5),
        "p5_1": 0,
        "p5_2": 0,
        "double_lines": len(double_lines),
        "triple_lines": len(triple_lines),
    }
    return {"double_lines": double_lines, "triple_lines": triple_lines, "multiple_points": multiple_points, "inventory": inventory}
