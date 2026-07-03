"""Arrangement and incidence helpers for HodgeCY."""

from .incidence import (
    incidence_hypergraph,
    intersection_codimension,
    intersection_rank,
    maximal_incidence_strata,
    plane_matrix,
    rank_of_planes,
    subset_rank_signature,
    subset_rank_table,
)
from .isomorphism import (
    are_rank_fingerprints_equal,
    canonical_subset_rank_fingerprint,
    find_incidence_isomorphisms,
    incidence_isomorphic,
)
from .planes import Plane, PlaneArrangement, arrangement_83_family_symbolic, arrangement_84, arrangement_84a

__all__ = [
    "Plane",
    "PlaneArrangement",
    "are_rank_fingerprints_equal",
    "arrangement_83_family_symbolic",
    "arrangement_84",
    "arrangement_84a",
    "canonical_subset_rank_fingerprint",
    "find_incidence_isomorphisms",
    "incidence_hypergraph",
    "incidence_isomorphic",
    "intersection_codimension",
    "intersection_rank",
    "maximal_incidence_strata",
    "plane_matrix",
    "rank_of_planes",
    "subset_rank_signature",
    "subset_rank_table",
]
