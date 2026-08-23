"""Experimental equivariant HodgeCY spectrum utilities."""

from .automorphisms import (
    apply_permutation_to_incidence_table,
    apply_permutation_to_quadruple,
    invariant_permutations,
    orbit_decomposition,
    permutation_group_summary,
)
from .characters import character_C0, character_C1, character_kernel_cokernel_placeholder, fixed_count_character
from .gluing_complex import (
    build_gluing_matrix,
    cokernel_dimension_Q,
    column_degree_distribution,
    kernel_dimension_Q,
    rank_mod_p,
    rank_over_Q,
    row_degree_distribution,
    smith_normal_form_invariants,
)
from .incidence_tables import (
    generic_matrix_rank,
    incidence_table_from_linear_forms,
    is_identically_zero,
    minimal_incidence_table,
    parse_linear_forms_from_record,
    singular_strata_from_incidence_table,
)
from .linear_forms import linear_forms_from_factor_texts, parse_linear_factor_text
from .spectrum import EquivariantHodgeCYSpectrum, build_equivariant_spectrum, spectrum_to_dict
from .source_complex import SourceComplexFromIncidence, source_complex_from_incidence

__all__ = [
    "EquivariantHodgeCYSpectrum",
    "apply_permutation_to_incidence_table",
    "apply_permutation_to_quadruple",
    "build_equivariant_spectrum",
    "build_gluing_matrix",
    "character_C0",
    "character_C1",
    "character_kernel_cokernel_placeholder",
    "cokernel_dimension_Q",
    "column_degree_distribution",
    "fixed_count_character",
    "generic_matrix_rank",
    "incidence_table_from_linear_forms",
    "invariant_permutations",
    "is_identically_zero",
    "kernel_dimension_Q",
    "linear_forms_from_factor_texts",
    "minimal_incidence_table",
    "orbit_decomposition",
    "parse_linear_factor_text",
    "parse_linear_forms_from_record",
    "permutation_group_summary",
    "rank_mod_p",
    "rank_over_Q",
    "row_degree_distribution",
    "singular_strata_from_incidence_table",
    "source_complex_from_incidence",
    "smith_normal_form_invariants",
    "SourceComplexFromIncidence",
    "spectrum_to_dict",
]
