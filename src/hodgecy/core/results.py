from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from collections.abc import Mapping
from typing import Any, ClassVar, Generic, TypeVar

from .errors import MathematicalPromotionError, ValidationError
from .ids import HodgeCYID
from .versions import SchemaVersion

RESULT_SCHEMA_VERSION = "mathematical_result.v1"

T = TypeVar("T")


class EvidenceStatus(str, Enum):
    COMPUTED = "computed"
    VERIFIED = "verified"
    IMPORTED = "imported"
    ASSUMED = "assumed"
    CONJECTURAL = "conjectural"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class ResultKind(str, Enum):
    SOURCE_ASSEMBLY = "source_assembly"
    NODE_GEOMETRY = "node_geometry"
    NODE_RELATION = "node_relation"
    CONIFOLD_ATOM = "conifold_atom"
    SMOOTH_HODGE_ATOM = "smooth_hodge_atom"


class ComparisonState(str, Enum):
    EQUAL = "equal"
    DIFFERENT = "different"
    UNKNOWN = "unknown"
    INCOMPARABLE = "incomparable"


def _geometry_id_to_dict(value: HodgeCYID | str | None) -> dict[str, str] | str | None:
    return value.to_dict() if isinstance(value, HodgeCYID) else value


def _geometry_id_from_dict(value: dict[str, str] | str | None) -> HodgeCYID | str | None:
    return HodgeCYID.from_dict(value) if isinstance(value, dict) else value


def _json_ready(value: Any) -> Any:
    if isinstance(value, HodgeCYID):
        return value.to_dict()
    if isinstance(value, SchemaVersion):
        return value.to_dict()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, ResultValue):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_ready(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class ResultValue(Generic[T]):
    value: T | None
    status: EvidenceStatus
    method: str | None = None
    provenance: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": _json_ready(self.value),
            "status": self.status.value,
            "method": self.method,
            "provenance": self.provenance,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResultValue[Any]":
        return cls(
            value=payload.get("value"),
            status=EvidenceStatus(payload["status"]),
            method=payload.get("method"),
            provenance=payload.get("provenance"),
            notes=payload.get("notes"),
        )


@dataclass(frozen=True, slots=True)
class ResultMetadata:
    geometry_id: HodgeCYID | str | None
    result_kind: ResultKind
    schema_version: SchemaVersion = SchemaVersion(RESULT_SCHEMA_VERSION)
    evidence_status: EvidenceStatus = EvidenceStatus.UNKNOWN
    method: str | None = None
    provenance: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "geometry_id": _geometry_id_to_dict(self.geometry_id),
            "result_kind": self.result_kind.value,
            "schema_version": self.schema_version.to_dict(),
            "evidence_status": self.evidence_status.value,
            "method": self.method,
            "provenance": self.provenance,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResultMetadata":
        return cls(
            geometry_id=_geometry_id_from_dict(payload.get("geometry_id")),
            result_kind=ResultKind(payload["result_kind"]),
            schema_version=SchemaVersion.from_dict(payload.get("schema_version", {"value": RESULT_SCHEMA_VERSION})),
            evidence_status=EvidenceStatus(payload.get("evidence_status", EvidenceStatus.UNKNOWN.value)),
            method=payload.get("method"),
            provenance=payload.get("provenance"),
            notes=payload.get("notes"),
        )


@dataclass(frozen=True, slots=True)
class MathematicalResult:
    metadata: ResultMetadata
    values: Mapping[str, ResultValue[Any]] = field(default_factory=dict)
    payload: Mapping[str, Any] = field(default_factory=dict)

    EXPECTED_KIND: ClassVar[ResultKind | None] = None

    def __post_init__(self) -> None:
        if self.EXPECTED_KIND is not None and self.metadata.result_kind is not self.EXPECTED_KIND:
            raise ValidationError(f"{type(self).__name__} requires result kind {self.EXPECTED_KIND.value}; got {self.metadata.result_kind.value}")

    @property
    def kind(self) -> ResultKind:
        return self.metadata.result_kind

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "values": {key: value.to_dict() for key, value in self.values.items()},
            "payload": _json_ready(self.payload),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MathematicalResult":
        return cls(
            metadata=ResultMetadata.from_dict(payload["metadata"]),
            values={str(key): ResultValue.from_dict(value) for key, value in (payload.get("values") or {}).items()},
            payload=dict(payload.get("payload") or {}),
        )


@dataclass(frozen=True, slots=True)
class BaseSpectrum(MathematicalResult):
    """Abstract base for typed spectrum-like result objects."""


@dataclass(frozen=True, slots=True)
class SourceAssemblyResult(MathematicalResult):
    EXPECTED_KIND: ClassVar[ResultKind | None] = ResultKind.SOURCE_ASSEMBLY


@dataclass(frozen=True, slots=True)
class SourceAssemblySpectrum(BaseSpectrum):
    EXPECTED_KIND: ClassVar[ResultKind | None] = ResultKind.SOURCE_ASSEMBLY


@dataclass(frozen=True, slots=True)
class NodeGeometryResult(MathematicalResult):
    EXPECTED_KIND: ClassVar[ResultKind | None] = ResultKind.NODE_GEOMETRY


@dataclass(frozen=True, slots=True)
class NodeRelationResult(MathematicalResult):
    EXPECTED_KIND: ClassVar[ResultKind | None] = ResultKind.NODE_RELATION


@dataclass(frozen=True, slots=True)
class ConifoldAtomSpectrum(BaseSpectrum):
    EXPECTED_KIND: ClassVar[ResultKind | None] = ResultKind.CONIFOLD_ATOM


@dataclass(frozen=True, slots=True)
class SmoothHodgeAtomSpectrum(BaseSpectrum):
    EXPECTED_KIND: ClassVar[ResultKind | None] = ResultKind.SMOOTH_HODGE_ATOM


def require_certified_promotion(source: MathematicalResult, target_kind: ResultKind, *, certification: ResultValue[Any] | None = None) -> None:
    if certification is None or certification.status is not EvidenceStatus.VERIFIED:
        raise MathematicalPromotionError(
            f"Cannot promote {source.kind.value} data to a {target_kind.value} result: "
            "no verified mathematical comparison/certification was supplied."
        )


def promote_source_to_node_relation(source: SourceAssemblyResult | SourceAssemblySpectrum, *, certification: ResultValue[Any] | None = None) -> NodeRelationResult:
    require_certified_promotion(source, ResultKind.NODE_RELATION, certification=certification)
    return NodeRelationResult(
        metadata=ResultMetadata(
            geometry_id=source.metadata.geometry_id,
            result_kind=ResultKind.NODE_RELATION,
            evidence_status=EvidenceStatus.VERIFIED,
            method=certification.method,
            provenance=certification.provenance,
            notes=certification.notes,
        ),
        values={},
        payload={"certified_source_result": source.to_dict(), "certification": certification.to_dict()},
    )


def promote_source_to_conifold_atom(source: SourceAssemblyResult | SourceAssemblySpectrum, *, certification: ResultValue[Any] | None = None) -> ConifoldAtomSpectrum:
    require_certified_promotion(source, ResultKind.CONIFOLD_ATOM, certification=certification)
    return ConifoldAtomSpectrum(
        metadata=ResultMetadata(
            geometry_id=source.metadata.geometry_id,
            result_kind=ResultKind.CONIFOLD_ATOM,
            evidence_status=EvidenceStatus.VERIFIED,
            method=certification.method,
            provenance=certification.provenance,
            notes=certification.notes,
        ),
        values={},
        payload={"certified_source_result": source.to_dict(), "certification": certification.to_dict()},
    )


def promote_source_to_smooth_hodge_atom(source: SourceAssemblyResult | SourceAssemblySpectrum, *, certification: ResultValue[Any] | None = None) -> SmoothHodgeAtomSpectrum:
    require_certified_promotion(source, ResultKind.SMOOTH_HODGE_ATOM, certification=certification)
    return SmoothHodgeAtomSpectrum(
        metadata=ResultMetadata(
            geometry_id=source.metadata.geometry_id,
            result_kind=ResultKind.SMOOTH_HODGE_ATOM,
            evidence_status=EvidenceStatus.VERIFIED,
            method=certification.method,
            provenance=certification.provenance,
            notes=certification.notes,
        ),
        values={},
        payload={"certified_source_result": source.to_dict(), "certification": certification.to_dict()},
    )
