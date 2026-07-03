"""Monodromy and nilpotent-profile schemas for HodgeCY."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MonodromyData:
    example_id: str
    conifold_point: str | None
    monodromy_matrix: list[list[str]] | None
    nilpotent_matrix: list[list[str]] | None
    rank_nilpotent: int | None
    source: str | None
    status: str = "not_computed"
    notes: str | None = None


@dataclass(slots=True)
class NilpotentProfile:
    example_id: str
    nilpotent_rank: int | None
    nilpotent_index: int | None
    is_conifold_type: bool | None
    status: str = "not_computed"
    notes: str | None = None


@dataclass(slots=True)
class OperatorAtomProfile:
    example_id: str
    operator_route_available: bool
    conifold_point_count: int | None
    nilpotent_profiles: list[NilpotentProfile] | None
    status: str = "not_computed"
    notes: str | None = None


def operator_profile_placeholder(example_id: str, notes: str | None = None) -> OperatorAtomProfile:
    """Return a clearly marked operator-route placeholder profile."""
    base_note = "Picard--Fuchs and conifold monodromy data are not yet loaded in this repository."
    if notes:
        base_note = f"{notes} {base_note}"
    return OperatorAtomProfile(
        example_id=example_id,
        operator_route_available=False,
        conifold_point_count=None,
        nilpotent_profiles=None,
        status="not_computed",
        notes=base_note,
    )
