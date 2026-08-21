from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from .ids import HodgeCYID, IdentityKind
from .status import ClaimLevel, ValidationEvent

@dataclass(frozen=True, slots=True)
class RelationshipEndpoint:
    object_id: HodgeCYID
    role: str

@dataclass(frozen=True, slots=True)
class RelationshipAssertion:
    relationship_id: HodgeCYID
    relation_type: str
    endpoints: tuple[RelationshipEndpoint, ...]
    claim_level: ClaimLevel
    directed: bool = True
    provenance_id: str | None = None
    validation_events: tuple[ValidationEvent, ...] = ()
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.relationship_id.require_kind(IdentityKind.DERIVED_OBJECT)
        if len(self.endpoints) < 1:
            raise ValueError("RelationshipAssertion requires at least one endpoint")
