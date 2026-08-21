from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from .errors import ValidationError
from .ids import HodgeCYID
from .status import ClaimLevel, ValidationEvent

class FactOrigin(str, Enum):
    SOURCE_REPORTED = "source_reported"
    HODGECY_DERIVED = "hodgecy_derived"
    INDEPENDENTLY_RECOMPUTED = "independently_recomputed"

@dataclass(frozen=True, slots=True)
class HodgeDiamondFact:
    subject_id: HodgeCYID
    dimension: int
    p: int
    q: int
    value: int
    origin: FactOrigin
    claim_level: ClaimLevel
    provenance_id: str | None = None
    validation_events: tuple[ValidationEvent, ...] = ()

    def __post_init__(self) -> None:
        if self.dimension < 0 or self.p < 0 or self.q < 0:
            raise ValidationError("Hodge indices and dimension must be non-negative")
        if self.p > self.dimension or self.q > self.dimension:
            raise ValidationError("Hodge indices exceed dimension")
        if self.value < 0:
            raise ValidationError("Hodge numbers must be non-negative")

@dataclass(frozen=True, slots=True)
class HodgeDiamond:
    dimension: int
    facts: tuple[HodgeDiamondFact, ...]

    def __post_init__(self) -> None:
        keys = set()
        for fact in self.facts:
            if fact.dimension != self.dimension:
                raise ValidationError("All Hodge facts must share the diamond dimension")
            key = (fact.p, fact.q)
            if key in keys:
                raise ValidationError(f"Duplicate Hodge fact for {key}")
            keys.add(key)

    def get(self, p: int, q: int) -> int | None:
        for fact in self.facts:
            if fact.p == p and fact.q == q:
                return fact.value
        return None

    @property
    def h11(self) -> int | None:
        return self.get(1, 1)

    @property
    def h21(self) -> int | None:
        return self.get(2, 1)

    @property
    def h31(self) -> int | None:
        return self.get(3, 1)

    @property
    def h22(self) -> int | None:
        return self.get(2, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "facts": [
                {
                    "subject_id": fact.subject_id.to_dict(),
                    "dimension": fact.dimension,
                    "p": fact.p,
                    "q": fact.q,
                    "value": fact.value,
                    "origin": fact.origin.value,
                    "claim_level": fact.claim_level.value,
                    "provenance_id": fact.provenance_id,
                    "validation_events": [event.to_dict() for event in fact.validation_events],
                }
                for fact in self.facts
            ],
        }

@dataclass(frozen=True, slots=True)
class EulerCharacteristicFact:
    subject_id: HodgeCYID
    value: int
    origin: FactOrigin
    claim_level: ClaimLevel
    computed_from: str | None = None
    provenance_id: str | None = None

@dataclass(frozen=True, slots=True)
class FactAssertion:
    subject_id: HodgeCYID
    predicate: str
    value: Any
    origin: FactOrigin
    claim_level: ClaimLevel
    basis_id: HodgeCYID | None = None
    convention: str | None = None
    validation_events: tuple[ValidationEvent, ...] = ()
