"""Incidence-first source-complex construction for double octics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .automorphisms import invariant_permutations, orbit_decomposition, permutation_group_summary
from .characters import character_C0, character_C1, character_kernel_cokernel_placeholder
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
from .incidence_tables import Quadruple, singular_strata_from_incidence_table


@dataclass(frozen=True, slots=True)
class SourceComplexFromIncidence:
    arrangement_id: str
    incidence_table: list[Quadruple]
    source_provenance: dict[str, Any]
    strata: dict[str, Any]
    matrix_entries: list[list[int]]
    automorphism_group: dict[str, Any]
    plane_orbits: list[list[int]]
    double_line_orbits: list[list[list[int]]]
    triple_line_orbits: list[list[list[int]]]
    multiple_point_orbits: list[list[list[int]]]
    algebra: dict[str, Any]
    characters: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "arrangement_id": self.arrangement_id,
            "incidence_table": [list(item) for item in self.incidence_table],
            "source_provenance": self.source_provenance,
            "strata": self.strata,
            "matrix_entries": self.matrix_entries,
            "automorphism_group": self.automorphism_group,
            "plane_orbits": self.plane_orbits,
            "double_line_orbits": self.double_line_orbits,
            "triple_line_orbits": self.triple_line_orbits,
            "multiple_point_orbits": self.multiple_point_orbits,
            "algebra": self.algebra,
            "characters": self.characters,
        }


def source_complex_from_incidence(
    incidence_table: list[Quadruple],
    *,
    arrangement_id: str,
    linear_forms: list[dict[str, Any]] | None = None,
    source_provenance: dict[str, Any] | None = None,
    rank_primes: tuple[int, ...] = (2, 3, 5, 7, 11),
) -> SourceComplexFromIncidence:
    """Build the HodgeCY I two-stratum source complex from incidence data."""

    canonical = sorted(tuple(sorted(int(value) for value in item)) for item in incidence_table)
    strata = singular_strata_from_incidence_table(canonical, linear_forms)
    matrix = build_gluing_matrix(strata["double_lines"], strata["multiple_points"])
    permutations = invariant_permutations(canonical)
    group_summary = permutation_group_summary(permutations)
    double_line_items = [tuple(line["planes"]) for line in strata["double_lines"]]
    triple_line_items = [tuple(line["planes"]) for line in strata["triple_lines"]]
    point_items = [tuple(point["planes"]) for point in strata["multiple_points"]]
    algebra = {
        "gluing_matrix_shape": [int(matrix.rows), int(matrix.cols)],
        "rank_Q": rank_over_Q(matrix),
        "rank_mod_p": {str(prime): rank_mod_p(matrix, p=prime) for prime in rank_primes},
        "kernel_dim_Q": kernel_dimension_Q(matrix),
        "cokernel_dim_Q": cokernel_dimension_Q(matrix),
        "smith_normal_form": smith_normal_form_invariants(matrix),
        "row_degree_distribution": row_degree_distribution(matrix),
        "column_degree_distribution": column_degree_distribution(matrix),
    }
    return SourceComplexFromIncidence(
        arrangement_id=str(arrangement_id),
        incidence_table=canonical,
        source_provenance=source_provenance or {},
        strata=strata,
        matrix_entries=[[int(matrix[row, col]) for col in range(matrix.cols)] for row in range(matrix.rows)],
        automorphism_group=group_summary,
        plane_orbits=orbit_decomposition(list(range(8)), permutations),
        double_line_orbits=[[list(item) for item in orbit] for orbit in orbit_decomposition(double_line_items, permutations, _line_action)],
        triple_line_orbits=[[list(item) for item in orbit] for orbit in orbit_decomposition(triple_line_items, permutations, _line_action)],
        multiple_point_orbits=[[list(item) for item in orbit] for orbit in orbit_decomposition(point_items, permutations, _point_action)],
        algebra=algebra,
        characters={
            "C1": character_C1(strata["double_lines"], permutations),
            "C0": character_C0(strata["multiple_points"], permutations),
            "kernel_cokernel": character_kernel_cokernel_placeholder(matrix, permutations),
        },
    )


def _line_action(line: tuple[int, ...], permutation: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(sorted(permutation[index] for index in line))


def _point_action(point: tuple[int, ...], permutation: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(sorted(permutation[index] for index in point))
