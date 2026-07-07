"""Arrangement and incidence helpers for HodgeCY."""

from .concurrency import (
    ArrangementConcurrencyProfile,
    DoubleLine,
    MultiplePoint,
    build_concurrency_profile,
    concurrency_profile_to_dict,
    fraction_to_str,
    rref_key_to_str,
    vector_to_projective_str,
)
from .graphs import (
    build_concurrency_graph,
    build_p4_collinearity_graph,
    colored_graph_isomorphic,
    p4_collinearity_certificate_rows,
)
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
    "ArrangementConcurrencyProfile",
    "DoubleLine",
    "MultiplePoint",
    "Plane",
    "PlaneArrangement",
    "are_rank_fingerprints_equal",
    "arrangement_83_family_symbolic",
    "arrangement_84",
    "arrangement_84a",
    "canonical_subset_rank_fingerprint",
    "build_concurrency_graph",
    "build_p4_collinearity_graph",
    "build_concurrency_profile",
    "colored_graph_isomorphic",
    "concurrency_profile_to_dict",
    "fraction_to_str",
    "find_incidence_isomorphisms",
    "incidence_hypergraph",
    "incidence_isomorphic",
    "intersection_codimension",
    "intersection_rank",
    "maximal_incidence_strata",
    "plane_matrix",
    "p4_collinearity_certificate_rows",
    "rank_of_planes",
    "rref_key_to_str",
    "subset_rank_signature",
    "subset_rank_table",
    "vector_to_projective_str",
]
