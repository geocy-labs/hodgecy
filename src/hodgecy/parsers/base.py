from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from hodgecy.core.ids import DistributionLocator, HodgeCYID
from hodgecy.core.provenance import ParserProvenance, SourceProvenance
from hodgecy.core.serialization import stable_sha256
from hodgecy.core.status import ValidationEvent
from hodgecy.core.versions import SchemaVersion

PARSER_SCHEMA_VERSION = "parser.v1"


@dataclass(frozen=True, slots=True)
class SourceChunk:
    dataset_id: HodgeCYID
    distribution_id: str
    payload: str | bytes
    relative_path: str | None = None
    archive_member: str | None = None
    source_version: str | None = None
    source_url: str | None = None
    citation: str | None = None
    doi: str | None = None
    file_sha256: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_path(
        cls,
        path: str | Path,
        *,
        dataset_id: HodgeCYID,
        distribution_id: str,
        text: bool = True,
        encoding: str = "utf-8",
        **metadata: Any,
    ) -> "SourceChunk":
        source_path = Path(path)
        payload: str | bytes
        if text:
            payload = source_path.read_text(encoding=encoding)
        else:
            payload = source_path.read_bytes()
        return cls(
            dataset_id=dataset_id,
            distribution_id=distribution_id,
            payload=payload,
            relative_path=source_path.as_posix(),
            file_sha256=stable_sha256(payload.decode(encoding, errors="replace") if isinstance(payload, bytes) else payload),
            metadata=metadata,
        )

    def text(self, encoding: str = "utf-8") -> str:
        if isinstance(self.payload, bytes):
            return self.payload.decode(encoding)
        return self.payload

    def bytes(self, encoding: str = "utf-8") -> bytes:
        if isinstance(self.payload, bytes):
            return self.payload
        return self.payload.encode(encoding)

    def fingerprint(self) -> str:
        return stable_sha256({
            "payload": self.text(errors_encoding()) if isinstance(self.payload, bytes) else self.payload,
            "relative_path": self.relative_path,
            "archive_member": self.archive_member,
        })

    def locator(
        self,
        *,
        source_line: int | None = None,
        source_block: str | None = None,
        row_group: int | None = None,
        row_offset: int | None = None,
        archive_member: str | None = None,
    ) -> DistributionLocator:
        return DistributionLocator(
            dataset_id=self.dataset_id,
            distribution_id=self.distribution_id,
            relative_path=self.relative_path,
            archive_member=archive_member if archive_member is not None else self.archive_member,
            row_group=row_group,
            row_offset=row_offset,
            source_line=source_line,
            source_block=source_block,
        )

    def source_provenance(self, *, archive_member: str | None = None, source_locator: str | None = None) -> SourceProvenance:
        return SourceProvenance(
            source_dataset=self.dataset_id.local_id,
            source_version=self.source_version,
            source_url=self.source_url,
            citation=self.citation,
            doi=self.doi,
            physical_file=self.relative_path,
            file_sha256=self.file_sha256,
            archive_member=archive_member if archive_member is not None else self.archive_member,
            source_locator=source_locator,
        )


def errors_encoding() -> str:
    return "utf-8"


@dataclass(frozen=True, slots=True)
class ParsedRecord:
    native_id: str
    payload: dict[str, Any]
    payload_type: str
    source_locator: DistributionLocator
    source_provenance: SourceProvenance
    parser_provenance: ParserProvenance
    validation_events: tuple[ValidationEvent, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "native_id": self.native_id,
            "payload": self.payload,
            "payload_type": self.payload_type,
            "source_locator": self.source_locator.to_dict(),
            "source_provenance": self.source_provenance.to_dict(),
            "parser_provenance": self.parser_provenance.to_dict(),
            "validation_events": [event.to_dict() for event in self.validation_events],
        }


@dataclass(frozen=True, slots=True)
class RejectedRecord:
    dataset_id: HodgeCYID
    source_locator: DistributionLocator
    parser_name: str
    parser_version: str
    error_code: str
    error_message: str
    payload_excerpt: str
    raw_fingerprint: str
    validation_events: tuple[ValidationEvent, ...] = ()
    schema_version: SchemaVersion = SchemaVersion("rejected.v1")

    @property
    def rejected_id(self) -> str:
        return stable_sha256({
            "dataset_id": self.dataset_id.serialize(),
            "source_locator": self.source_locator.to_dict(),
            "parser_name": self.parser_name,
            "parser_version": self.parser_version,
            "error_code": self.error_code,
            "raw_fingerprint": self.raw_fingerprint,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "rejected_id": self.rejected_id,
            "dataset_id": self.dataset_id.to_dict(),
            "source_locator": self.source_locator.to_dict(),
            "parser_name": self.parser_name,
            "parser_version": self.parser_version,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "payload_excerpt": self.payload_excerpt,
            "raw_fingerprint": self.raw_fingerprint,
            "schema_version": self.schema_version.to_dict(),
            "validation_events": [event.to_dict() for event in self.validation_events],
        }


@dataclass(frozen=True, slots=True)
class ParseResult:
    parser_provenance: ParserProvenance
    records: tuple[ParsedRecord, ...] = ()
    rejected: tuple[RejectedRecord, ...] = ()
    validation_events: tuple[ValidationEvent, ...] = ()

    @property
    def parsed_count(self) -> int:
        return len(self.records)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected)

    @property
    def has_rejections(self) -> bool:
        return bool(self.rejected)


class Parser(Protocol):
    parser_name: str
    parser_version: str
    payload_type: str

    def parse(self, source: SourceChunk) -> ParseResult:
        ...


def parser_provenance(parser_name: str, parser_version: str) -> ParserProvenance:
    return ParserProvenance(
        parser_name=parser_name,
        parser_version=parser_version,
        parser_schema_version=PARSER_SCHEMA_VERSION,
    )


def reject(
    source: SourceChunk,
    *,
    parser_name: str,
    parser_version: str,
    error_code: str,
    error_message: str,
    payload_excerpt: str,
    source_line: int | None = None,
    source_block: str | None = None,
    archive_member: str | None = None,
) -> RejectedRecord:
    return RejectedRecord(
        dataset_id=source.dataset_id,
        source_locator=source.locator(source_line=source_line, source_block=source_block, archive_member=archive_member),
        parser_name=parser_name,
        parser_version=parser_version,
        error_code=error_code,
        error_message=error_message,
        payload_excerpt=payload_excerpt[:500],
        raw_fingerprint=stable_sha256(payload_excerpt),
    )


def write_rejected_jsonl(path: str | Path, rejected: list[RejectedRecord] | tuple[RejectedRecord, ...]) -> int:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for item in rejected:
            handle.write(json.dumps(item.to_dict(), sort_keys=True) + "\n")
    return len(rejected)
