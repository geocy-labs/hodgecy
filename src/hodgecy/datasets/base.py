from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Protocol

from hodgecy.core.adapters import AdapterCapability, DatasetAdapterDescriptor
from hodgecy.core.ids import HodgeCYID, IdentityKind
from hodgecy.core.records import SourceRecordEnvelope
from hodgecy.core.serialization import stable_sha256
from hodgecy.core.status import ParseStatus, ValidationDimension, ValidationEvent, ValidationStatus
from hodgecy.core.versions import SchemaVersion
from hodgecy.parsers.base import ParseResult, ParsedRecord, RejectedRecord, SourceChunk

_TOKEN_RE = re.compile(r"[^A-Za-z0-9._=-]+")


@dataclass(frozen=True, slots=True)
class AdapterRunSummary:
    adapter_descriptor: DatasetAdapterDescriptor
    source_count: int
    parsed_count: int
    rejected_count: int
    envelope_count: int
    validation_events: tuple[ValidationEvent, ...] = ()

    @property
    def ok(self) -> bool:
        return self.rejected_count == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_descriptor": {
                "dataset_id": self.adapter_descriptor.dataset_id.to_dict(),
                "adapter_name": self.adapter_descriptor.adapter_name,
                "adapter_version": self.adapter_descriptor.adapter_version,
                "capabilities": [capability.value for capability in self.adapter_descriptor.capabilities],
            },
            "source_count": self.source_count,
            "parsed_count": self.parsed_count,
            "rejected_count": self.rejected_count,
            "envelope_count": self.envelope_count,
            "ok": self.ok,
            "validation_events": [event.to_dict() for event in self.validation_events],
        }


@dataclass(frozen=True, slots=True)
class AdapterRun:
    summary: AdapterRunSummary
    parse_results: tuple[ParseResult, ...]
    envelopes: tuple[SourceRecordEnvelope, ...]
    rejected: tuple[RejectedRecord, ...]


@dataclass(frozen=True, slots=True)
class NormalizationManifest:
    dataset_id: HodgeCYID
    adapter_name: str
    adapter_version: str
    source_count: int
    input_record_count: int
    output_record_count: int
    rejected_record_count: int
    parser_names: tuple[str, ...]
    schema_version: SchemaVersion = SchemaVersion("normalization_manifest.v1")
    identifier_definition: str | None = None
    output_refs: tuple[str, ...] = ()
    validation_events: tuple[ValidationEvent, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def manifest_id(self) -> str:
        return str(self.to_dict(include_events=False)["manifest_id"])

    def to_dict(self, *, include_events: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "manifest_id": None,
            "dataset_id": self.dataset_id.to_dict(),
            "adapter_name": self.adapter_name,
            "adapter_version": self.adapter_version,
            "source_count": self.source_count,
            "input_record_count": self.input_record_count,
            "output_record_count": self.output_record_count,
            "rejected_record_count": self.rejected_record_count,
            "parser_names": list(self.parser_names),
            "schema_version": self.schema_version.to_dict(),
            "identifier_definition": self.identifier_definition,
            "output_refs": list(self.output_refs),
            "metadata": self.metadata,
        }
        payload["manifest_id"] = stable_sha256(payload)
        if include_events:
            payload["validation_events"] = [event.to_dict() for event in self.validation_events]
        return payload


class DatasetAdapter(Protocol):
    descriptor: DatasetAdapterDescriptor

    def discover_sources(self) -> Iterable[SourceChunk]:
        ...

    def parse_source(self, source: SourceChunk) -> ParseResult:
        ...

    def run(self) -> AdapterRun:
        ...


class FixtureDatasetAdapter:
    def __init__(
        self,
        *,
        descriptor: DatasetAdapterDescriptor,
        parser: Any,
        sources: Iterable[SourceChunk],
        identifier_definition: str = "fixture parser native_id",
    ) -> None:
        self.descriptor = descriptor
        self.parser = parser
        self._sources = tuple(sources)
        self.identifier_definition = identifier_definition

    @classmethod
    def build(
        cls,
        *,
        dataset_id: str,
        parser: Any,
        sources: Iterable[SourceChunk],
        adapter_name: str = "fixture_dataset_adapter",
        adapter_version: str = "1.0.0",
        capabilities: tuple[AdapterCapability, ...] = (AdapterCapability.STREAMING, AdapterCapability.NATIVE_PAYLOAD),
    ) -> "FixtureDatasetAdapter":
        return cls(
            descriptor=DatasetAdapterDescriptor(
                dataset_id=HodgeCYID.dataset(dataset_id),
                adapter_name=adapter_name,
                adapter_version=adapter_version,
                capabilities=capabilities,
            ),
            parser=parser,
            sources=sources,
        )

    def discover_sources(self) -> Iterable[SourceChunk]:
        return self._sources

    def parse_source(self, source: SourceChunk) -> ParseResult:
        if source.dataset_id != self.descriptor.dataset_id:
            raise ValueError("Source dataset_id does not match adapter descriptor dataset_id.")
        return self.parser.parse(source)

    def normalize_record(self, parsed: ParsedRecord) -> SourceRecordEnvelope:
        source_record_id = HodgeCYID.source_record(
            self.descriptor.dataset_id.local_id,
            _tokenize(parsed.native_id),
        )
        record_id = HodgeCYID.derived_from_components(
            IdentityKind.HODGECY_RECORD,
            self.descriptor.dataset_id.local_id,
            {
                "dataset_id": self.descriptor.dataset_id.serialize(),
                "source_record_id": source_record_id.serialize(),
                "source_locator": parsed.source_locator.to_dict(),
                "payload": parsed.payload,
            },
        )
        events = parsed.validation_events + (_normalization_event(parsed.native_id),)
        return SourceRecordEnvelope(
            hodgecy_record_id=record_id,
            dataset_id=self.descriptor.dataset_id,
            source_record_id=source_record_id,
            source_version=parsed.source_provenance.source_version,
            source_locator=parsed.source_locator,
            source_provenance=parsed.source_provenance,
            parser_provenance=parsed.parser_provenance,
            parse_status=ParseStatus.PARSED,
            schema_version=SchemaVersion(),
            payload_type=parsed.payload_type,
            payload_ref=None,
            validation_events=events,
            payload_summary=_payload_summary(parsed.payload),
        )

    def run(self) -> AdapterRun:
        parse_results: list[ParseResult] = []
        envelopes: list[SourceRecordEnvelope] = []
        rejected: list[RejectedRecord] = []
        for source in self.discover_sources():
            result = self.parse_source(source)
            parse_results.append(result)
            rejected.extend(result.rejected)
            envelopes.extend(self.normalize_record(record) for record in result.records)
        validation_events = tuple(event for envelope in envelopes for event in envelope.validation_events)
        summary = AdapterRunSummary(
            adapter_descriptor=self.descriptor,
            source_count=len(self._sources),
            parsed_count=sum(result.parsed_count for result in parse_results),
            rejected_count=len(rejected),
            envelope_count=len(envelopes),
            validation_events=validation_events,
        )
        return AdapterRun(summary, tuple(parse_results), tuple(envelopes), tuple(rejected))

    def normalization_manifest(self, run: AdapterRun, *, output_refs: tuple[str, ...] = ()) -> NormalizationManifest:
        parser_names = tuple(sorted({result.parser_provenance.parser_name for result in run.parse_results}))
        return NormalizationManifest(
            dataset_id=self.descriptor.dataset_id,
            adapter_name=self.descriptor.adapter_name,
            adapter_version=self.descriptor.adapter_version,
            source_count=run.summary.source_count,
            input_record_count=run.summary.parsed_count + run.summary.rejected_count,
            output_record_count=run.summary.envelope_count,
            rejected_record_count=run.summary.rejected_count,
            parser_names=parser_names,
            identifier_definition=self.identifier_definition,
            output_refs=output_refs,
            validation_events=run.summary.validation_events,
        )


def _tokenize(value: str) -> str:
    token = _TOKEN_RE.sub("-", value.strip()).strip("-._=")
    if not token:
        token = "record"
    if not token[0].isalnum():
        token = f"record-{token}"
    return token


def _payload_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "field_count": len(payload),
        "fields": sorted(str(key) for key in payload.keys())[:20],
    }


def _normalization_event(native_id: str) -> ValidationEvent:
    return ValidationEvent(
        dimension=ValidationDimension.PRESENTATION,
        status=ValidationStatus.SOURCE_REPORTED,
        method="fixture_source_record_envelope",
        evidence={"native_id": native_id},
        validator="hodgecy.datasets.base",
        validator_version="1.0.0",
    )
