"""Permutation-character helpers for equivariant HodgeCY spectra."""

from __future__ import annotations

from collections import Counter
from typing import Callable, TypeVar

from .automorphisms import Permutation

Item = TypeVar("Item")


def fixed_count_character(items: list[Item], permutations: list[Permutation], action: Callable[[Item, Permutation], Item]) -> list[dict]:
    """Return fixed-count character values for a permutation action."""
    values = []
    for permutation in permutations:
        fixed = sum(1 for item in items if action(item, permutation) == item)
        values.append({"permutation": list(permutation), "fixed_count": fixed})
    return values


def _line_action(line: tuple[int, ...], permutation: Permutation) -> tuple[int, ...]:
    return tuple(sorted(permutation[index] for index in line))


def _point_action(point: tuple[int, ...], permutation: Permutation) -> tuple[int, ...]:
    return tuple(sorted(permutation[index] for index in point))


def character_C1(double_lines: list[dict], permutations: list[Permutation]) -> dict:
    items = [tuple(line["planes"]) for line in double_lines]
    values = fixed_count_character(items, permutations, _line_action)
    return {"values": values, "value_distribution": dict(sorted(Counter(row["fixed_count"] for row in values).items()))}


def character_C0(multiple_points: list[dict], permutations: list[Permutation]) -> dict:
    items = [tuple(point["planes"]) for point in multiple_points]
    values = fixed_count_character(items, permutations, _point_action)
    return {"values": values, "value_distribution": dict(sorted(Counter(row["fixed_count"] for row in values).items()))}


def character_kernel_cokernel_placeholder(matrix, permutations: list[Permutation]) -> dict:
    """Placeholder for future invariant-subspace character calculations."""
    return {
        "status": "not_computed",
        "permutation_count": len(permutations),
        "matrix_shape": [int(matrix.rows), int(matrix.cols)],
        "todo": "Compute induced actions on kernel and cokernel, then decompose characters into irreducibles.",
    }
