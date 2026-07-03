"""Atom-profile schema for HodgeCY."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class HodgeCYAtomProfile:
    example_id: str
    source_dataset: str | None
    construction: str | None
    source_arrangement: str | None
    node_count: int | None
    classical_defect: int | None
    flexible_formal_rank: int | None
    flexible_realized_rank: int | None
    relation_rank: int | None
    block_count: int | None
    block_profile: list[int] | None
    block_profile_source: str | None
    gluing_deficit: int | None
    defect_status: str = "not_computed"
    operator_route_available: bool = False
    operator_conifold_count: int | None = None
    geometric_operator_match_status: str = "not_tested"
    status: str = "partial"
    notes: str | None = None


def profile_from_defect(
    example_id: str,
    node_count: int | None,
    classical_defect: int | None,
    block_profile: list[int] | None = None,
    source_dataset: str | None = None,
    notes: str | None = None,
) -> HodgeCYAtomProfile:
    """Lift a coarse classical defect count into the first HodgeCY atom-profile schema."""
    flexible_formal_rank = node_count
    relation_rank = classical_defect
    flexible_realized_rank = None
    if node_count is not None and classical_defect is not None:
        candidate_rank = node_count - classical_defect
        if candidate_rank >= 0:
            flexible_realized_rank = candidate_rank

    block_count = len(block_profile) if block_profile is not None else None
    schema_note = (
        "Schema-level atom profile only: classical defect is treated as a coarse numerical "
        "shadow of flexible-sector compression until geometric/operator data are computed."
    )
    if notes:
        schema_note = f"{notes} {schema_note}"

    return HodgeCYAtomProfile(
        example_id=example_id,
        source_dataset=source_dataset,
        construction=None,
        source_arrangement=None,
        node_count=node_count,
        classical_defect=classical_defect,
        defect_status="not_computed" if classical_defect is None else "computed",
        flexible_formal_rank=flexible_formal_rank,
        flexible_realized_rank=flexible_realized_rank,
        relation_rank=relation_rank,
        block_count=block_count,
        block_profile=block_profile,
        block_profile_source=None,
        gluing_deficit=None,
        notes=schema_note,
    )


def profile_from_smoothing_bridge(
    arrangement_id: str,
    expected_node_count: int | None,
    double_line_count: int | None,
    nodes_per_line: int | None = 4,
    classical_defect: int | None = None,
    defect_status: str = "not_computed",
    notes: str | None = None,
) -> HodgeCYAtomProfile:
    """Build a candidate atom profile from the Gate 2 smoothing-bridge labeling."""
    block_profile = None
    if double_line_count is not None and nodes_per_line is not None:
        block_profile = [nodes_per_line] * double_line_count

    flexible_realized_rank = None
    relation_rank = classical_defect
    if expected_node_count is not None and classical_defect is not None:
        candidate_rank = expected_node_count - classical_defect
        if candidate_rank >= 0:
            flexible_realized_rank = candidate_rank

    gluing_deficit = None
    if expected_node_count is not None and double_line_count is not None:
        gluing_deficit = expected_node_count - double_line_count

    schema_note = (
        "Candidate atom-block profile induced by smoothing-bridge double-line labeling; "
        "local node verification and defect computation remain mathematically required."
    )
    if notes:
        schema_note = f"{notes} {schema_note}"

    return HodgeCYAtomProfile(
        example_id=f"smoothing_bridge_{arrangement_id}",
        source_dataset="cynk_meyer",
        construction="smoothing_bridge",
        source_arrangement=arrangement_id,
        node_count=expected_node_count,
        classical_defect=classical_defect,
        defect_status=defect_status,
        flexible_formal_rank=expected_node_count,
        flexible_realized_rank=flexible_realized_rank,
        relation_rank=relation_rank,
        block_count=double_line_count,
        block_profile=block_profile,
        block_profile_source="double_line_labeling_from_arrangement",
        gluing_deficit=gluing_deficit,
        status="expected_not_verified" if expected_node_count is not None else "partial",
        notes=schema_note,
    )


def to_dict(profile: HodgeCYAtomProfile) -> dict:
    """Serialize a HodgeCY atom profile to a plain dictionary."""
    return asdict(profile)
