"""JSON-serializable equivariant HodgeCY spectrum records."""

from __future__ import annotations

from dataclasses import asdict, dataclass
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
from .incidence_tables import incidence_table_from_linear_forms, parse_linear_forms_from_record, singular_strata_from_incidence_table


@dataclass(slots=True)
class EquivariantHodgeCYSpectrum:
    arrangement_id: str
    source: str
    representative_status: str
    parameter_choice: dict[str, Any] | None
    source_equation: str | None
    source_reference: str | None
    linear_forms: list[dict[str, Any]]
    incidence_table: list[list[int]]
    singularity_inventory: dict[str, int]
    expected_cynk_inventory: dict[str, int] | None
    computed_inventory: dict[str, int]
    inventory_matches_expected: bool | None
    hodge_data_if_known: dict[str, Any] | None
    arithmetic_label_if_known: str | None
    automorphism_group_order: int
    invariant_permutations: list[list[int]]
    plane_orbits: list[list[int]]
    double_line_orbits: list[list[list[int]]]
    multiple_point_orbits: list[list[list[int]]]
    gluing_matrix_shape: list[int]
    rank_Q: int
    rank_F2: int
    kernel_dim_Q: int
    cokernel_dim_Q: int
    smith_normal_form: list[int] | None
    row_degree_distribution: dict[int, int]
    column_degree_distribution: dict[int, int]
    character_C1: dict
    character_C0: dict
    character_kernel_cokernel: dict
    p4_graph_summary_if_available: dict | None
    perturbation_status_if_available: str | None
    notes: str


def _line_action(line: tuple[int, ...], permutation: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(sorted(permutation[index] for index in line))


def _point_action(point: tuple[int, ...], permutation: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(sorted(permutation[index] for index in point))


def _computed_inventory(inventory: dict[str, int]) -> dict[str, int]:
    return {
        "p3": int(inventory.get("p3", 0)),
        "p4_0": int(inventory.get("p4_0", 0)),
        "p4_1": int(inventory.get("p4_1", 0)),
        "p5_0": int(inventory.get("p5_0", 0)),
        "p5_1": int(inventory.get("p5_1", 0)),
        "p5_2": int(inventory.get("p5_2", 0)),
        "l3": int(inventory.get("triple_lines", 0)),
    }


def _inventory_matches(expected: dict[str, int] | None, computed: dict[str, int]) -> bool | None:
    if expected is None:
        return None
    return all(int(expected.get(key, -1)) == computed.get(key) for key in computed)


def build_equivariant_spectrum(record: dict, p4_graph_summary_if_available: dict | None = None, perturbation_status_if_available: str | None = None) -> EquivariantHodgeCYSpectrum:
    linear_forms = parse_linear_forms_from_record(record)
    incidence_table = incidence_table_from_linear_forms(linear_forms)
    strata = singular_strata_from_incidence_table(incidence_table, linear_forms)
    permutations = invariant_permutations(incidence_table)
    group_summary = permutation_group_summary(permutations)
    matrix = build_gluing_matrix(strata["double_lines"], strata["multiple_points"])
    double_line_items = [tuple(line["planes"]) for line in strata["double_lines"]]
    multiple_point_items = [tuple(point["planes"]) for point in strata["multiple_points"]]
    expected_inventory = record.get("expected_cynk_inventory")
    computed_inventory = _computed_inventory(strata["inventory"])
    inventory_matches = _inventory_matches(expected_inventory, computed_inventory)
    representative_status = str(record.get("representative_status", "provisional"))
    if inventory_matches is False:
        representative_status = "provisional"

    return EquivariantHodgeCYSpectrum(
        arrangement_id=str(record["arrangement_id"]),
        source=str(record.get("source", "")),
        representative_status=representative_status,
        parameter_choice=record.get("parameter_choice") or record.get("parameters"),
        source_equation=record.get("source_equation"),
        source_reference=record.get("source_reference"),
        linear_forms=[
            {"label": form["label"], "coefficients": [str(value) for value in form["coefficients"]], "equation": form.get("equation")}
            for form in linear_forms
        ],
        incidence_table=[list(quadruple) for quadruple in incidence_table],
        singularity_inventory=strata["inventory"],
        expected_cynk_inventory=expected_inventory,
        computed_inventory=computed_inventory,
        inventory_matches_expected=inventory_matches,
        hodge_data_if_known=record.get("hodge_data_if_known"),
        arithmetic_label_if_known=record.get("arithmetic_label_if_known"),
        automorphism_group_order=group_summary["order"],
        invariant_permutations=group_summary["all_permutations"],
        plane_orbits=orbit_decomposition(list(range(8)), permutations),
        double_line_orbits=[[list(item) for item in orbit] for orbit in orbit_decomposition(double_line_items, permutations, _line_action)],
        multiple_point_orbits=[[list(item) for item in orbit] for orbit in orbit_decomposition(multiple_point_items, permutations, _point_action)],
        gluing_matrix_shape=[int(matrix.rows), int(matrix.cols)],
        rank_Q=rank_over_Q(matrix),
        rank_F2=rank_mod_p(matrix, p=2),
        kernel_dim_Q=kernel_dimension_Q(matrix),
        cokernel_dim_Q=cokernel_dimension_Q(matrix),
        smith_normal_form=smith_normal_form_invariants(matrix),
        row_degree_distribution=row_degree_distribution(matrix),
        column_degree_distribution=column_degree_distribution(matrix),
        character_C1=character_C1(strata["double_lines"], permutations),
        character_C0=character_C0(strata["multiple_points"], permutations),
        character_kernel_cokernel=character_kernel_cokernel_placeholder(matrix, permutations),
        p4_graph_summary_if_available=p4_graph_summary_if_available,
        perturbation_status_if_available=perturbation_status_if_available,
        notes=str(record.get("notes", "Experimental additive equivariant spectrum record.")),
    )


def spectrum_to_dict(spectrum: EquivariantHodgeCYSpectrum) -> dict:
    return asdict(spectrum)
