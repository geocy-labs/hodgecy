"""Subset-rank fingerprinting and incidence-isomorphism checks."""

from __future__ import annotations

from itertools import combinations, permutations

from .incidence import subset_rank_signature
from .planes import PlaneArrangement


def _subset_rank_lookup(arrangement: PlaneArrangement) -> dict[tuple[int, ...], int]:
    lookup: dict[tuple[int, ...], int] = {}
    indices = range(len(arrangement.planes))
    coefficient_rows = [tuple(plane.coefficients) for plane in arrangement.planes]
    from sympy import Matrix

    for subset_size in range(1, len(arrangement.planes) + 1):
        for subset in combinations(indices, subset_size):
            lookup[subset] = Matrix([coefficient_rows[index] for index in subset]).rank()
    return lookup


def canonical_subset_rank_fingerprint(arrangement: PlaneArrangement) -> dict:
    """Return a canonical subset-rank fingerprint suitable for equality testing."""
    signature = subset_rank_signature(arrangement)
    return {
        "arrangement_id": arrangement.arrangement_id,
        "plane_count": len(arrangement.planes),
        "subset_rank_signature": signature,
    }


def are_rank_fingerprints_equal(arr1: PlaneArrangement, arr2: PlaneArrangement) -> bool:
    """Return whether two arrangements share the same subset-rank fingerprint."""
    return subset_rank_signature(arr1) == subset_rank_signature(arr2)


def find_incidence_isomorphisms(
    arr1: PlaneArrangement,
    arr2: PlaneArrangement,
    max_results: int = 10,
) -> list[dict]:
    """Search for plane permutations preserving the full subset-rank function."""
    if len(arr1.planes) != len(arr2.planes):
        return []

    lookup1 = _subset_rank_lookup(arr1)
    lookup2 = _subset_rank_lookup(arr2)
    all_subsets = sorted(lookup1.keys(), key=lambda subset: (len(subset), subset))

    results: list[dict] = []
    for permutation in permutations(range(len(arr1.planes))):
        preserves_all = True
        for subset in all_subsets:
            mapped_subset = tuple(sorted(permutation[index] for index in subset))
            if lookup1[subset] != lookup2[mapped_subset]:
                preserves_all = False
                break
        if preserves_all:
            results.append(
                {
                    "permutation_zero_based": list(permutation),
                    "plane_label_map": {
                        arr1.planes[index].label: arr2.planes[permutation[index]].label
                        for index in range(len(permutation))
                    },
                }
            )
            if len(results) >= max_results:
                break
    return results


def incidence_isomorphic(arr1: PlaneArrangement, arr2: PlaneArrangement) -> bool:
    """Return whether an incidence-preserving plane permutation exists."""
    return bool(find_incidence_isomorphisms(arr1, arr2, max_results=1))
