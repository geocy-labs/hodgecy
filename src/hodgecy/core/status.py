from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

class AcquisitionStatus(str, Enum):
    COMPLETE_LOCAL = "COMPLETE_LOCAL"
    COMPLETE_COLUMNAR = "COMPLETE_COLUMNAR"
    COMPLETE_NATIVE = "COMPLETE_NATIVE"
    COMPLETE_REMOTE = "COMPLETE_REMOTE"
    MANUAL_SOURCE_REQUIRED = "MANUAL_SOURCE_REQUIRED"
    SOURCE_REGISTRY_ONLY = "SOURCE_REGISTRY_ONLY"
    COMPUTABLE_NOT_PREENUMERATED = "COMPUTABLE_NOT_PREENUMERATED"
    PARTIAL_PUBLIC_CORPUS = "PARTIAL_PUBLIC_CORPUS"
    UNRESOLVED = "UNRESOLVED"

class ParseStatus(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    NOT_PARSED = "not_parsed"
    PARSED = "parsed"
    PARTIAL = "partial"
    REJECTED = "rejected"
    FAILED = "failed"

class SourceIntegrityStatus(str, Enum):
    SOURCE_VALID = "source_valid"
    SOURCE_CORRUPT = "source_corrupt"
    SOURCE_UNREADABLE = "source_unreadable"
    SOURCE_INCOMPLETE = "source_incomplete"
    SOURCE_ACCESS_BLOCKED = "source_access_blocked"
    SOURCE_REMOTE_INDEXED = "source_remote_indexed"

class RedistributionStatus(str, Enum):
    REDISTRIBUTABLE = "redistributable"
    ACQUIRED_LOCALLY_BY_USER = "acquired_locally_by_user"
    REMOTE_OR_MANUAL_ONLY = "remote_or_manual_only"
    UNSPECIFIED = "unspecified"

class ValidationDimension(str, Enum):
    SOURCE_INTEGRITY = "source_integrity"
    PARSE = "parse_validation"
    PRESENTATION = "presentation_validation"
    GEOMETRY = "geometry_validation"
    HODGE = "hodge_validation"
    TOPOLOGY = "topology_validation"
    RELATIONSHIP = "relationship_validation"
    SYMMETRY = "symmetry_validation"
    ASSEMBLY = "assembly_validation"
    DEGENERATION = "degeneration_validation"
    NODE = "node_validation"
    DEFECT = "defect_validation"
    OPERATOR = "operator_validation"
    EXACT_ALGEBRA = "exact_algebra_validation"
    EQUIVARIANT = "equivariant_validation"
    HODGE_ATOM = "hodge_atom_validation"

class ValidationStatus(str, Enum):
    SOURCE_REPORTED = "source_reported"
    SYNTACTICALLY_VALIDATED = "syntactically_validated"
    MATHEMATICALLY_VALIDATED = "mathematically_validated"
    INDEPENDENTLY_RECOMPUTED = "independently_recomputed"
    CERTIFIED = "certified"
    CONTRADICTED = "contradicted"
    DEFERRED = "deferred"
    NOT_APPLICABLE = "not_applicable"

class ClaimLevel(str, Enum):
    SOURCE_REPORTED = "source_reported"
    PARSED = "parsed"
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    RECOMPUTED = "recomputed"
    COMPUTATIONALLY_CERTIFIED = "computationally_certified"
    THEOREM_CERTIFIED = "theorem_certified"

class Exactness(str, Enum):
    EXACT = "exact"
    HEURISTIC = "heuristic"
    PROBABILISTIC = "probabilistic"
    PLACEHOLDER = "placeholder"
    FAILED = "failed"

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

@dataclass(frozen=True, slots=True)
class ValidationEvent:
    dimension: ValidationDimension
    status: ValidationStatus
    method: str
    evidence: dict[str, Any] = field(default_factory=dict)
    validator: str | None = None
    validator_version: str | None = None
    timestamp: datetime = field(default_factory=utc_now)
    provenance_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"dimension": self.dimension.value, "status": self.status.value, "method": self.method, "evidence": self.evidence, "validator": self.validator, "validator_version": self.validator_version, "timestamp": self.timestamp.isoformat(), "provenance_id": self.provenance_id}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ValidationEvent":
        return cls(ValidationDimension(payload["dimension"]), ValidationStatus(payload["status"]), str(payload["method"]), dict(payload.get("evidence") or {}), payload.get("validator"), payload.get("validator_version"), datetime.fromisoformat(str(payload["timestamp"])), payload.get("provenance_id"))
