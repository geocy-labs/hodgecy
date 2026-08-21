from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from hodgecy.core.adapters import AdapterCapability, DatasetAdapterDescriptor
from hodgecy.core.dataset import ConstructionFamily, DatasetDescriptor
from hodgecy.core.ids import HodgeCYID
from hodgecy.core.status import AcquisitionStatus, RedistributionStatus, ValidationDimension, ValidationEvent, ValidationStatus
from hodgecy.datasets.base import AdapterRun, FixtureDatasetAdapter
from hodgecy.parsers import JsonlParser, SourceChunk
from hodgecy.parsers.base import ParseResult, ParsedRecord, parser_provenance, reject

ADAPTER_VERSION = "1.0.0"
WEIGHTED_P4_SOURCE_REVISION = "tu-wien-weighted-p4-local"


@dataclass(frozen=True, slots=True)
class WeightedP4Schema:
    dataset_id: str = "weighted_p4"
    source_key: str = "weights"
    dimension: int = 3

    def to_dict(self) -> dict[str, Any]:
        return {"dataset_id": self.dataset_id, "source_key": self.source_key, "dimension": self.dimension}


WEIGHTED_P4_SCHEMA = WeightedP4Schema()


class WeightedP4JsonlParser:
    parser_name = "weighted_p4_jsonl"
    parser_version = ADAPTER_VERSION
    payload_type = "weighted_p4_hypersurface"

    def __init__(self, schema: WeightedP4Schema = WEIGHTED_P4_SCHEMA) -> None:
        self.schema = schema
        self._jsonl = JsonlParser()

    def parse(self, source: SourceChunk) -> ParseResult:
        result = self._jsonl.parse(source)
        provenance = parser_provenance(self.parser_name, self.parser_version)
        records: list[ParsedRecord] = []
        rejected = list(result.rejected)
        for record in result.records:
            errors = validate_weighted_p4_payload(record.payload)
            if errors:
                rejected.append(reject(
                    source,
                    parser_name=self.parser_name,
                    parser_version=self.parser_version,
                    error_code="invalid_weighted_p4_payload",
                    error_message="; ".join(errors),
                    payload_excerpt=str(record.payload),
                    source_line=record.source_locator.source_line,
                ))
                continue
            payload = normalize_weighted_p4_payload(record.payload)
            records.append(ParsedRecord(
                native_id="w-" + "-".join(str(item) for item in payload["weights"]),
                payload=payload,
                payload_type=self.payload_type,
                source_locator=record.source_locator,
                source_provenance=record.source_provenance,
                parser_provenance=provenance,
                validation_events=record.validation_events + (_event("weighted_p4_payload_shape"),),
            ))
        return ParseResult(provenance, tuple(records), tuple(rejected), result.validation_events)


def weighted_p4_descriptor() -> DatasetDescriptor:
    return DatasetDescriptor(
        dataset_id=HodgeCYID.dataset(WEIGHTED_P4_SCHEMA.dataset_id),
        name="Weighted-P4 Calabi-Yau hypersurfaces",
        construction_family=ConstructionFamily.known("weighted_hypersurface"),
        acquisition_status=AcquisitionStatus.COMPLETE_LOCAL,
        redistribution_status=RedistributionStatus.ACQUIRED_LOCALLY_BY_USER,
        source_version=WEIGHTED_P4_SOURCE_REVISION,
        record_semantics="weight-system hypersurface source record",
        identifier_definition="ordered weight vector source identifier",
        expected_count=7555,
        adapter_capabilities=(AdapterCapability.STREAMING.value, AdapterCapability.NATIVE_PAYLOAD.value),
        metadata={"schema": WEIGHTED_P4_SCHEMA.to_dict(), "identity_boundary": "weight vector is a presentation/source identifier"},
    )


def weighted_p4_adapter(sources: Iterable[SourceChunk]) -> FixtureDatasetAdapter:
    return FixtureDatasetAdapter(
        descriptor=DatasetAdapterDescriptor(
            dataset_id=HodgeCYID.dataset(WEIGHTED_P4_SCHEMA.dataset_id),
            adapter_name="weighted_p4_adapter",
            adapter_version=ADAPTER_VERSION,
            capabilities=(AdapterCapability.STREAMING, AdapterCapability.NATIVE_PAYLOAD),
        ),
        parser=WeightedP4JsonlParser(),
        sources=sources,
        identifier_definition="ordered weight vector",
    )


def validate_weighted_p4_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    weights = payload.get("weights")
    if not isinstance(weights, list) or len(weights) != 5 or not all(isinstance(item, int) and item > 0 for item in weights):
        errors.append("weights must be five positive integers")
    degree = payload.get("degree")
    if degree is not None and not isinstance(degree, int):
        errors.append("degree must be an integer when present")
    for key in ("h11", "h21", "euler"):
        if key in payload and not isinstance(payload[key], int):
            errors.append(f"{key} must be an integer when present")
    return errors


def normalize_weighted_p4_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    normalized["dimension"] = 3
    normalized["construction_family"] = "weighted_hypersurface"
    normalized["source_record_id"] = "w-" + "-".join(str(item) for item in payload["weights"])
    normalized["presentation_kind"] = "weight_vector"
    return normalized


def weighted_query_rows(run: AdapterRun) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in run.parse_results:
        for record in result.records:
            rows.append({
                "dataset_id": record.source_provenance.source_dataset,
                "source_record_id": record.payload["source_record_id"],
                "construction_family": record.payload["construction_family"],
                "dimension": record.payload["dimension"],
                "h11": record.payload.get("h11"),
                "h21": record.payload.get("h21"),
                "euler": record.payload.get("euler"),
                "degree": record.payload.get("degree"),
                "weights": record.payload.get("weights"),
                "source_locator": record.source_locator.to_dict(),
            })
    return rows


def _event(method: str) -> ValidationEvent:
    return ValidationEvent(
        dimension=ValidationDimension.PRESENTATION,
        status=ValidationStatus.SYNTACTICALLY_VALIDATED,
        method=method,
        evidence={"schema": WEIGHTED_P4_SCHEMA.to_dict()},
        validator="hodgecy.datasets.weighted",
        validator_version=ADAPTER_VERSION,
    )
