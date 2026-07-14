"""Automorphism utilities for incidence tables."""

from __future__ import annotations

from itertools import permutations
from typing import Callable, Iterable, TypeVar

Item = TypeVar("Item")
Permutation = tuple[int, ...]
Quadruple = tuple[int, int, int, int]


def apply_permutation_to_quadruple(quadruple: Quadruple, permutation: Permutation) -> Quadruple:
    """Apply a zero-based plane permutation to a quadruple."""
    return tuple(sorted(permutation[index] for index in quadruple))  # type: ignore[return-value]


def apply_permutation_to_incidence_table(incidence_table: list[Quadruple], permutation: Permutation) -> list[Quadruple]:
    """Apply a permutation and return the canonical incidence table."""
    return sorted(apply_permutation_to_quadruple(quadruple, permutation) for quadruple in incidence_table)


def invariant_permutations(incidence_table: list[Quadruple]) -> list[Permutation]:
    """Brute-force all S_8 permutations preserving the incidence table."""
    canonical = sorted(tuple(sorted(quadruple)) for quadruple in incidence_table)
    invariant = []
    for permutation in permutations(range(8)):
        if apply_permutation_to_incidence_table(canonical, permutation) == canonical:
            invariant.append(tuple(permutation))
    return invariant


def permutation_group_summary(permutations_: list[Permutation]) -> dict:
    """Return a lightweight group summary."""
    identity = tuple(range(8))
    non_identity = [perm for perm in permutations_ if perm != identity]
    return {
        "order": len(permutations_),
        "identity_present": identity in permutations_,
        "sample_generators": [list(perm) for perm in non_identity[: min(4, len(non_identity))]],
        "all_permutations": [list(perm) for perm in permutations_],
    }


def orbit_decomposition(items: Iterable[Item], permutations_: list[Permutation], action: Callable[[Item, Permutation], Item] | None = None) -> list[list[Item]]:
    """Compute orbits for a finite permutation action."""
    remaining = set(items)
    orbits = []
    while remaining:
        start = next(iter(remaining))
        orbit = {start}
        changed = True
        while changed:
            changed = False
            for item in list(orbit):
                for permutation in permutations_:
                    image = action(item, permutation) if action else permutation[item]  # type: ignore[index]
                    if image not in orbit:
                        orbit.add(image)
                        changed = True
        orbits.append(sorted(orbit))
        remaining -= orbit
    return sorted(orbits, key=lambda values: (len(values), values))
