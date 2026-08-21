from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from .ids import HodgeCYID, IdentityKind
from .status import AcquisitionStatus, RedistributionStatus
from .versions import SchemaVersion
from .errors import ValidationError

_FAMILY_RE = re.compile(r"^[a-z][a-z0-9_]*$")

@dataclass(frozen=True, slots=True)
class ConstructionFamily:
    name: str

    def __post_init__(self) -> None:
        if not _FAMILY_RE.fullmatch(self.name):
            raise ValidationError(f"Invalid construction family: {self.name!r}")

    @classmethod
    def known(cls, name: str) -> "ConstructionFamily":
        return cls(name)

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name}

@dataclass(frozen=True, slots=True)
class DatasetDescriptor:
    dataset_id: HodgeCYID
    name: str
    construction_family: ConstructionFamily
    acquisition_status: AcquisitionStatus
    redistribution_status: RedistributionStatus
    schema_version: SchemaVersion = SchemaVersion()
    source_version: str | None = None
    record_semantics: str | None = None
    identifier_definition: str | None = None
    source_citations: tuple[str, ...] = ()
    source_urls: tuple[str, ...] = ()
    doi: str | None = None
    expected_count: int | None = None
    verified_count: int | None = None
    adapter_capabilities: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.dataset_id.require_kind(IdentityKind.DATASET)
        if self.expected_count is not None and self.expected_count < 0:
            raise ValidationError("expected_count must be non-negative")
        if self.verified_count is not None and self.verified_count < 0:
            raise ValidationError("verified_count must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id.to_dict(), "name": self.name, "construction_family": self.construction_family.to_dict(),
            "acquisition_status": self.acquisition_status.value, "redistribution_status": self.redistribution_status.value,
            "schema_version": self.schema_version.to_dict(), "source_version": self.source_version,
            "record_semantics": self.record_semantics, "identifier_definition": self.identifier_definition,
            "source_citations": list(self.source_citations), "source_urls": list(self.source_urls), "doi": self.doi,
            "expected_count": self.expected_count, "verified_count": self.verified_count,
            "adapter_capabilities": list(self.adapter_capabilities), "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DatasetDescriptor":
        return cls(
            dataset_id=HodgeCYID.from_dict(payload["dataset_id"]), construction_family=ConstructionFamily(str(payload["construction_family"]["name"])),
            name=str(payload["name"]), acquisition_status=AcquisitionStatus(payload["acquisition_status"]),
            redistribution_status=RedistributionStatus(payload["redistribution_status"]), schema_version=SchemaVersion.from_dict(payload["schema_version"]),
            source_version=payload.get("source_version"), record_semantics=payload.get("record_semantics"),
            identifier_definition=payload.get("identifier_definition"), source_citations=tuple(payload.get("source_citations") or ()),
            source_urls=tuple(payload.get("source_urls") or ()), doi=payload.get("doi"), expected_count=payload.get("expected_count"),
            verified_count=payload.get("verified_count"), adapter_capabilities=tuple(payload.get("adapter_capabilities") or ()),
            metadata=dict(payload.get("metadata") or {}),
        )
