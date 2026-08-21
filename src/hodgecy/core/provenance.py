from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from .status import Exactness, utc_now

@dataclass(frozen=True, slots=True)
class SourceProvenance:
    source_dataset: str
    source_version: str | None = None
    source_url: str | None = None
    citation: str | None = None
    doi: str | None = None
    distribution_revision: str | None = None
    physical_file: str | None = None
    file_sha256: str | None = None
    archive_member: str | None = None
    source_locator: str | None = None
    acquisition_timestamp: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {"source_dataset": self.source_dataset, "source_version": self.source_version, "source_url": self.source_url, "citation": self.citation, "doi": self.doi, "distribution_revision": self.distribution_revision, "physical_file": self.physical_file, "file_sha256": self.file_sha256, "archive_member": self.archive_member, "source_locator": self.source_locator, "acquisition_timestamp": self.acquisition_timestamp.isoformat()}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SourceProvenance":
        return cls(str(payload["source_dataset"]), payload.get("source_version"), payload.get("source_url"), payload.get("citation"), payload.get("doi"), payload.get("distribution_revision"), payload.get("physical_file"), payload.get("file_sha256"), payload.get("archive_member"), payload.get("source_locator"), datetime.fromisoformat(str(payload["acquisition_timestamp"])))

@dataclass(frozen=True, slots=True)
class ParserProvenance:
    parser_name: str
    parser_version: str
    parser_schema_version: str
    hodgecy_version: str | None = None
    hodgecy_commit: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {"parser_name": self.parser_name, "parser_version": self.parser_version, "parser_schema_version": self.parser_schema_version, "hodgecy_version": self.hodgecy_version, "hodgecy_commit": self.hodgecy_commit}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ParserProvenance":
        return cls(str(payload["parser_name"]), str(payload["parser_version"]), str(payload["parser_schema_version"]), payload.get("hodgecy_version"), payload.get("hodgecy_commit"))

@dataclass(frozen=True, slots=True)
class ComputationProvenance:
    algorithm: str
    algorithm_version: str
    parameters: dict[str, Any] = field(default_factory=dict)
    dependencies: dict[str, str] = field(default_factory=dict)
    hodgecy_commit: str | None = None
    timestamp: datetime = field(default_factory=utc_now)
    exactness: Exactness = Exactness.EXACT

    def to_dict(self) -> dict[str, Any]:
        return {"algorithm": self.algorithm, "algorithm_version": self.algorithm_version, "parameters": self.parameters, "dependencies": self.dependencies, "hodgecy_commit": self.hodgecy_commit, "timestamp": self.timestamp.isoformat(), "exactness": self.exactness.value}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ComputationProvenance":
        return cls(str(payload["algorithm"]), str(payload["algorithm_version"]), dict(payload.get("parameters") or {}), dict(payload.get("dependencies") or {}), payload.get("hodgecy_commit"), datetime.fromisoformat(str(payload["timestamp"])), Exactness(payload.get("exactness", Exactness.EXACT.value)))
