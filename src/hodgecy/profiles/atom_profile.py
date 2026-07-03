"""Atom-profile schema for HodgeCY."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class HodgeCYAtomProfile:
    example_id: str
    source_dataset: str | None
    node_count: int | None
    classical_defect: int | None
    flexible_formal_rank: int | None
    flexible_realized_rank: int | None
    relation_rank: int | None
    block_count: int | None
    block_profile: list[int] | None
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
        node_count=node_count,
        classical_defect=classical_defect,
        flexible_formal_rank=flexible_formal_rank,
        flexible_realized_rank=flexible_realized_rank,
        relation_rank=relation_rank,
        block_count=block_count,
        block_profile=block_profile,
        notes=schema_note,
    )


def to_dict(profile: HodgeCYAtomProfile) -> dict:
    """Serialize a HodgeCY atom profile to a plain dictionary."""
    return asdict(profile)
