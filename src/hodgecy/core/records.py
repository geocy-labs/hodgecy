from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from .ids import DistributionLocator, HodgeCYID, IdentityKind
from .provenance import ParserProvenance, SourceProvenance
from .status import ClaimLevel, ParseStatus, ValidationEvent
from .versions import SchemaVersion

@dataclass(frozen=True, slots=True)
class PresentationRef:
    presentation_id: HodgeCYID
    family: str
    payload_type: str
    claim_level: ClaimLevel = ClaimLevel.PARSED

    def __post_init__(self) -> None:
        self.presentation_id.require_kind(IdentityKind.PRESENTATION)

@dataclass(frozen=True, slots=True)
class GeometryRef:
    geometry_id: HodgeCYID | None
    claim_level: ClaimLevel
    certification: str | None = None

    def __post_init__(self) -> None:
        if self.geometry_id is not None:
            self.geometry_id.require_kind(IdentityKind.GEOMETRY)

@dataclass(frozen=True, slots=True)
class DerivedObjectRef:
    derived_id: HodgeCYID
    object_type: str
    parent_ids: tuple[HodgeCYID, ...]
    result_locator: str | None = None
    claim_level: ClaimLevel = ClaimLevel.CANDIDATE

    def __post_init__(self) -> None:
        self.derived_id.require_kind(IdentityKind.DERIVED_OBJECT)

@dataclass(frozen=True, slots=True)
class SourceRecordEnvelope:
    hodgecy_record_id: HodgeCYID
    dataset_id: HodgeCYID
    source_record_id: HodgeCYID
    source_version: str | None
    source_locator: DistributionLocator | None
    source_provenance: SourceProvenance
    parser_provenance: ParserProvenance | None
    parse_status: ParseStatus
    schema_version: SchemaVersion
    payload_type: str
    payload_ref: str | None = None
    validation_events: tuple[ValidationEvent, ...] = ()
    payload_summary: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.hodgecy_record_id.require_kind(IdentityKind.HODGECY_RECORD)
        self.dataset_id.require_kind(IdentityKind.DATASET)
        self.source_record_id.require_kind(IdentityKind.SOURCE_RECORD)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hodgecy_record_id": self.hodgecy_record_id.to_dict(), "dataset_id": self.dataset_id.to_dict(),
            "source_record_id": self.source_record_id.to_dict(), "source_version": self.source_version,
            "source_locator": None if self.source_locator is None else self.source_locator.to_dict(),
            "source_provenance": self.source_provenance.to_dict(),
            "parser_provenance": None if self.parser_provenance is None else self.parser_provenance.to_dict(),
            "parse_status": self.parse_status.value, "schema_version": self.schema_version.to_dict(),
            "payload_type": self.payload_type, "payload_ref": self.payload_ref,
            "validation_events": [event.to_dict() for event in self.validation_events], "payload_summary": self.payload_summary,
        }
