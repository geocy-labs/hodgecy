from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from .ids import HodgeCYID, IdentityKind
from .serialization import stable_sha256

@dataclass(frozen=True, slots=True)
class AlgorithmDescriptor:
    algorithm_id: HodgeCYID
    name: str
    version: str
    parameters: dict[str, Any] = field(default_factory=dict)
    implementation: str | None = None

    def __post_init__(self) -> None:
        self.algorithm_id.require_kind(IdentityKind.ALGORITHM)

    @property
    def parameter_hash(self) -> str:
        return stable_sha256(self.parameters)
