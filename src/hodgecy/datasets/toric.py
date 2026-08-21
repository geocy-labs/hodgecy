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
IP_WEIGHT_SOURCE_REVISION = "tu-wien-4d-ip-weights-local"
KS_PARQUET_SOURCE_REVISION = "60c0e119a03608418df538191f65da3f43b5b819"


@dataclass(frozen=True, slots=True)
class IPWeightSchema:
    dataset_id: str = "ip_weight_systems_4d"
    dimension: int = 3

    def to_dict(self) -> dict[str, Any]:
        return {"dataset_id": self.dataset_id, "dimension": self.dimension}


IP_WEIGHT_SCHEMA = IPWeightSchema()


class IPWeightJsonlParser:
    parser_name = "ip_weight_jsonl"
    parser_version = ADAPTER_VERSION
    payload_type = "ip_weight_system"

    def __init__(self) -> None:
        self._jsonl = JsonlParser()

    def parse(self, source: SourceChunk) -> ParseResult:
        result = self._jsonl.parse(source)
        provenance = parser_provenance(self.parser_name, self.parser_version)
        records: list[ParsedRecord] = []
        rejected = list(result.rejected)
        for record in result.records:
            errors = validate_ip_weight_payload(record.payload)
            if errors:
                rejected.append(reject(
                    source,
                    parser_name=self.parser_name,
                    parser_version=self.parser_version,
                    error_code="invalid_ip_weight_payload",
                    error_message="; ".join(errors),
                    payload_excerpt=str(record.payload),
                    source_line=record.source_locator.source_line,
                ))
                continue
            payload = normalize_ip_weight_payload(record.payload)
            records.append(ParsedRecord(
                native_id=payload["source_record_id"],
                payload=payload,
                payload_type=self.payload_type,
                source_locator=record.source_locator,
                source_provenance=record.source_provenance,
                parser_provenance=provenance,
                validation_events=record.validation_events + (_event("ip_weight_payload_shape"),),
            ))
        return ParseResult(provenance, tuple(records), tuple(rejected), result.validation_events)


def ip_weight_descriptor() -> DatasetDescriptor:
    return DatasetDescriptor(
        dataset_id=HodgeCYID.dataset(IP_WEIGHT_SCHEMA.dataset_id),
        name="4D IP weight systems with Hodge/K3 data",
        construction_family=ConstructionFamily.known("ip_weight_system"),
        acquisition_status=AcquisitionStatus.COMPLETE_LOCAL,
        redistribution_status=RedistributionStatus.ACQUIRED_LOCALLY_BY_USER,
        source_version=IP_WEIGHT_SOURCE_REVISION,
        record_semantics="IP weight-system source record",
        identifier_definition="source line or ordered weight system",
        expected_count=184026,
        adapter_capabilities=(AdapterCapability.STREAMING.value, AdapterCapability.NATIVE_PAYLOAD.value),
        metadata={"schema": IP_WEIGHT_SCHEMA.to_dict(), "ks_join_policy": "presentation/canonical computation only; no fake geometry id"},
    )


def kreuzer_skarke_descriptor() -> DatasetDescriptor:
    return DatasetDescriptor(
        dataset_id=HodgeCYID.dataset("kreuzer_skarke"),
        name="Kreuzer-Skarke reflexive 4-polytopes",
        construction_family=ConstructionFamily.known("toric_hypersurface"),
        acquisition_status=AcquisitionStatus.COMPLETE_COLUMNAR,
        redistribution_status=RedistributionStatus.ACQUIRED_LOCALLY_BY_USER,
        source_version=KS_PARQUET_SOURCE_REVISION,
        record_semantics="columnar polytope source presentation",
        identifier_definition="distribution locator; not a stable geometry identity",
        expected_count=473800776,
        adapter_capabilities=(AdapterCapability.COLUMNAR.value, AdapterCapability.STREAMING.value),
        metadata={"row_count": 473800776, "parquet_files": 30, "bytes": 15773290651},
    )


def ip_weight_adapter(sources: Iterable[SourceChunk]) -> FixtureDatasetAdapter:
    return FixtureDatasetAdapter(
        descriptor=DatasetAdapterDescriptor(
            dataset_id=HodgeCYID.dataset(IP_WEIGHT_SCHEMA.dataset_id),
            adapter_name="ip_weight_adapter",
            adapter_version=ADAPTER_VERSION,
            capabilities=(AdapterCapability.STREAMING, AdapterCapability.NATIVE_PAYLOAD),
        ),
        parser=IPWeightJsonlParser(),
        sources=sources,
        identifier_definition="source line or ordered weight system",
    )


def validate_ip_weight_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    weights = payload.get("weights")
    if not isinstance(weights, list) or not weights or not all(isinstance(item, int) and item > 0 for item in weights):
        errors.append("weights must be positive integers")
    for key in ("h11", "h21", "point_count", "vertex_count", "dual_point_count"):
        if key in payload and not isinstance(payload[key], int):
            errors.append(f"{key} must be an integer when present")
    return errors


def normalize_ip_weight_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    normalized["dimension"] = 3
    normalized["construction_family"] = "ip_weight_system"
    normalized["source_record_id"] = str(payload.get("id") or "ip-" + "-".join(str(item) for item in payload["weights"]))
    normalized["presentation_kind"] = "ip_weight_vector"
    return normalized


def ip_weight_query_rows(run: AdapterRun) -> list[dict[str, Any]]:
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
                "point_count": record.payload.get("point_count"),
                "vertex_count": record.payload.get("vertex_count"),
                "dual_point_count": record.payload.get("dual_point_count"),
                "weights": record.payload.get("weights"),
                "source_locator": record.source_locator.to_dict(),
            })
    return rows


def _event(method: str) -> ValidationEvent:
    return ValidationEvent(
        dimension=ValidationDimension.PRESENTATION,
        status=ValidationStatus.SYNTACTICALLY_VALIDATED,
        method=method,
        evidence={"schema": IP_WEIGHT_SCHEMA.to_dict()},
        validator="hodgecy.datasets.toric",
        validator_version=ADAPTER_VERSION,
    )
