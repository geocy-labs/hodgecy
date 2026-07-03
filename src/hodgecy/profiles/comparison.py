"""Comparison schema for HodgeCY atom profiles."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .atom_profile import HodgeCYAtomProfile


@dataclass(slots=True)
class AtomProfileComparison:
    comparison_id: str
    example_a: str
    example_b: str
    same_node_count: bool | None
    same_classical_defect: bool | None
    same_block_profile: bool | None
    same_gluing_deficit: bool | None
    same_hodge_numbers: bool | None
    same_singularity_profile: bool | None
    same_modular_form: bool | None
    conclusion: str
    status: str
    notes: str | None = None


def _same_hodge_numbers(row_a: dict | None, row_b: dict | None) -> bool | None:
    if row_a is None or row_b is None:
        return None
    return (row_a.get("h12"), row_a.get("h11"), row_a.get("euler")) == (
        row_b.get("h12"),
        row_b.get("h11"),
        row_b.get("euler"),
    )


def _same_singularity_profile(row_a: dict | None, row_b: dict | None) -> bool | None:
    if row_a is None or row_b is None:
        return None
    keys = ["p3", "p4_0", "p4_1", "p5_0", "p5_1", "p5_2", "l3"]
    return tuple(row_a.get(key) for key in keys) == tuple(row_b.get(key) for key in keys)


def compare_atom_profiles(
    profile_a: HodgeCYAtomProfile,
    profile_b: HodgeCYAtomProfile,
    table1_row_a: dict | None = None,
    table1_row_b: dict | None = None,
) -> AtomProfileComparison:
    """Compare two candidate atom profiles conservatively."""
    same_node_count = (
        profile_a.node_count == profile_b.node_count
        if profile_a.node_count is not None and profile_b.node_count is not None
        else None
    )
    same_classical_defect = (
        profile_a.classical_defect == profile_b.classical_defect
        if profile_a.classical_defect is not None and profile_b.classical_defect is not None
        else None
    )
    same_block_profile = (
        sorted(profile_a.block_profile) == sorted(profile_b.block_profile)
        if profile_a.block_profile is not None and profile_b.block_profile is not None
        else None
    )
    same_gluing_deficit = (
        profile_a.gluing_deficit == profile_b.gluing_deficit
        if profile_a.gluing_deficit is not None and profile_b.gluing_deficit is not None
        else None
    )
    same_hodge_numbers = _same_hodge_numbers(table1_row_a, table1_row_b)
    same_singularity_profile = _same_singularity_profile(table1_row_a, table1_row_b)
    same_modular_form = (
        table1_row_a.get("modular_form") == table1_row_b.get("modular_form")
        if table1_row_a is not None and table1_row_b is not None
        else None
    )

    conclusion = "inconclusive"
    if same_node_count and same_block_profile is False:
        conclusion = "candidate_atom_profile_separates"
    elif same_node_count and same_block_profile is True and same_classical_defect is None:
        conclusion = "pending_defect_computation"
    elif same_node_count and same_classical_defect is True and same_block_profile is False:
        conclusion = "candidate_strict_refinement_of_defect"

    return AtomProfileComparison(
        comparison_id=f"{profile_a.example_id}_vs_{profile_b.example_id}",
        example_a=profile_a.example_id,
        example_b=profile_b.example_id,
        same_node_count=same_node_count,
        same_classical_defect=same_classical_defect,
        same_block_profile=same_block_profile,
        same_gluing_deficit=same_gluing_deficit,
        same_hodge_numbers=same_hodge_numbers,
        same_singularity_profile=same_singularity_profile,
        same_modular_form=same_modular_form,
        conclusion=conclusion,
        status="candidate",
        notes=(
            "Comparison remains candidate-level until smoothing-bridge node verification and "
            "classical defect computations are available."
        ),
    )


def comparison_to_dict(comparison: AtomProfileComparison) -> dict:
    """Serialize a profile comparison to a plain dictionary."""
    return asdict(comparison)
