"""Incidence computations for plane arrangements in projective three-space."""

from __future__ import annotations

from itertools import combinations

import pandas as pd
import sympy as sp

from .planes import Plane, PlaneArrangement


def plane_matrix(arrangement: PlaneArrangement) -> sp.Matrix:
    """Return the coefficient matrix for the arrangement planes."""
    return sp.Matrix([list(plane.coefficients) for plane in arrangement.planes])


def rank_of_planes(planes: list[Plane]) -> int:
    """Return the rank of the linear forms defining the selected planes."""
    if not planes:
        return 0
    return sp.Matrix([list(plane.coefficients) for plane in planes]).rank()


def intersection_rank(arrangement: PlaneArrangement, plane_indices: tuple[int, ...]) -> int:
    """Return the rank of the selected subset of planes."""
    selected = [arrangement.planes[index] for index in plane_indices]
    return rank_of_planes(selected)


def intersection_codimension(arrangement: PlaneArrangement, plane_indices: tuple[int, ...]) -> int:
    """Return the codimension estimate of the projective intersection."""
    return intersection_rank(arrangement, plane_indices)


def _projective_dimension_from_rank(rank: int) -> int:
    return 3 - rank


def _geometry_label(rank: int) -> str:
    projective_dimension = _projective_dimension_from_rank(rank)
    if projective_dimension >= 2:
        return "plane-like"
    if projective_dimension == 1:
        return "line-like"
    if projective_dimension == 0:
        return "point-like"
    return "empty/overdetermined"


def subset_rank_signature(arrangement: PlaneArrangement) -> dict[int, list[int]]:
    """Return the multiset of subset ranks grouped by subset size."""
    signature: dict[int, list[int]] = {}
    indices = range(len(arrangement.planes))
    for subset_size in range(1, len(arrangement.planes) + 1):
        signature[subset_size] = sorted(
            intersection_rank(arrangement, subset)
            for subset in combinations(indices, subset_size)
        )
    return signature


def subset_rank_table(arrangement: PlaneArrangement) -> pd.DataFrame:
    """Return a row for every nonempty subset of planes."""
    rows: list[dict[str, object]] = []
    indices = range(len(arrangement.planes))
    for subset_size in range(1, len(arrangement.planes) + 1):
        for subset in combinations(indices, subset_size):
            rank = intersection_rank(arrangement, subset)
            rows.append(
                {
                    "arrangement_id": arrangement.arrangement_id,
                    "subset": ",".join(str(index) for index in subset),
                    "subset_size": subset_size,
                    "rank": rank,
                    "projective_dimension_estimate": _projective_dimension_from_rank(rank),
                    "labels": ",".join(arrangement.planes[index].label for index in subset),
                }
            )
    return pd.DataFrame(rows)


def incidence_hypergraph(arrangement: PlaneArrangement, min_subset_size: int = 2) -> dict:
    """Record subset-level incidence data for all subsets above the requested size."""
    hyperedges: list[dict[str, object]] = []
    indices = range(len(arrangement.planes))
    for subset_size in range(min_subset_size, len(arrangement.planes) + 1):
        for subset in combinations(indices, subset_size):
            rank = intersection_rank(arrangement, subset)
            hyperedges.append(
                {
                    "subset": subset,
                    "subset_labels": tuple(arrangement.planes[index].label for index in subset),
                    "subset_size": subset_size,
                    "rank": rank,
                    "projective_dimension": _projective_dimension_from_rank(rank),
                    "geometry": _geometry_label(rank),
                }
            )
    return {
        "arrangement_id": arrangement.arrangement_id,
        "hyperedges": hyperedges,
    }


def maximal_incidence_strata(arrangement: PlaneArrangement) -> pd.DataFrame:
    """Identify maximal subsets whose projective intersections remain nonempty."""
    candidates: list[tuple[int, ...]] = []
    indices = range(len(arrangement.planes))
    for subset_size in range(2, len(arrangement.planes) + 1):
        for subset in combinations(indices, subset_size):
            if intersection_rank(arrangement, subset) <= 3:
                candidates.append(subset)

    maximal_subsets: list[tuple[int, ...]] = []
    for subset in candidates:
        is_maximal = True
        subset_set = set(subset)
        for other in candidates:
            if len(other) <= len(subset):
                continue
            if subset_set.issubset(other):
                is_maximal = False
                break
        if is_maximal:
            maximal_subsets.append(subset)

    rows = []
    for subset in maximal_subsets:
        rank = intersection_rank(arrangement, subset)
        rows.append(
            {
                "arrangement_id": arrangement.arrangement_id,
                "subset": ",".join(str(index) for index in subset),
                "subset_labels": ",".join(arrangement.planes[index].label for index in subset),
                "subset_size": len(subset),
                "rank": rank,
                "projective_dimension": _projective_dimension_from_rank(rank),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["subset_size", "subset_labels"], ascending=[False, True]
    ).reset_index(drop=True)
