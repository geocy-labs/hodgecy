from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from hodgecy.core.adapters import AdapterCapability, DatasetAdapterDescriptor
from hodgecy.core.dataset import ConstructionFamily, DatasetDescriptor
from hodgecy.core.ids import HodgeCYID
from hodgecy.core.status import AcquisitionStatus, RedistributionStatus, ValidationDimension, ValidationEvent, ValidationStatus
from hodgecy.datasets.base import AdapterRun, FixtureDatasetAdapter
from hodgecy.parsers import JsonlParser, SourceChunk
from hodgecy.parsers.base import ParseResult, ParsedRecord, parser_provenance

ADAPTER_VERSION = "1.0.0"
CICY3_SOURCE_REVISION = "oxford-cicy3-corrected-local"
CICY4_SOURCE_REVISION = "oxford-cicy4-local"


@dataclass(frozen=True, slots=True)
class CICYAdapterSchema:
    dataset_id: str
    dimension: int
    source_key: str
    matrix_key: str = "configuration_matrix"
    hodge_keys: tuple[str, ...] = ()
    topology_keys: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "dimension": self.dimension,
            "source_key": self.source_key,
            "matrix_key": self.matrix_key,
            "hodge_keys": list(self.hodge_keys),
            "topology_keys": list(self.topology_keys),
        }


CICY3_SCHEMA = CICYAdapterSchema(
    dataset_id="cicy3_standard",
    dimension=3,
    source_key="Num",
    hodge_keys=("h11", "h21"),
    topology_keys=("euler", "c2"),
)
CICY4_SCHEMA = CICYAdapterSchema(
    dataset_id="cicy4_core",
    dimension=4,
    source_key="matrix_number",
    hodge_keys=("h11", "h12", "h13", "h22", "h31"),
    topology_keys=("euler", "chern"),
)


class CICYJsonlParser:
    parser_name = "cicy_jsonl"
    parser_version = ADAPTER_VERSION
    payload_type = "cicy_configuration"

    def __init__(self, schema: CICYAdapterSchema) -> None:
        self.schema = schema
        self._jsonl = JsonlParser()

    def parse(self, source: SourceChunk) -> ParseResult:
        result = self._jsonl.parse(source)
        provenance = parser_provenance(self.parser_name, self.parser_version)
        records: list[ParsedRecord] = []
        rejected = list(result.rejected)
        for record in result.records:
            errors = validate_cicy_payload(record.payload, self.schema)
            if errors:
                from hodgecy.parsers.base import reject
                rejected.append(reject(
                    source,
                    parser_name=self.parser_name,
                    parser_version=self.parser_version,
                    error_code="invalid_cicy_payload",
                    error_message="; ".join(errors),
                    payload_excerpt=str(record.payload),
                    source_line=record.source_locator.source_line,
                ))
                continue
            payload = normalize_cicy_payload(record.payload, self.schema)
            records.append(ParsedRecord(
                native_id=str(payload[self.schema.source_key]),
                payload=payload,
                payload_type=self.payload_type,
                source_locator=record.source_locator,
                source_provenance=record.source_provenance,
                parser_provenance=provenance,
                validation_events=record.validation_events + (_event(self.schema, "cicy_payload_shape"),),
            ))
        return ParseResult(provenance, tuple(records), tuple(rejected), result.validation_events)


def cicy3_descriptor() -> DatasetDescriptor:
    return DatasetDescriptor(
        dataset_id=HodgeCYID.dataset(CICY3_SCHEMA.dataset_id),
        name="Complete CICY threefold configurations",
        construction_family=ConstructionFamily.known("cicy3"),
        acquisition_status=AcquisitionStatus.COMPLETE_LOCAL,
        redistribution_status=RedistributionStatus.ACQUIRED_LOCALLY_BY_USER,
        source_version=CICY3_SOURCE_REVISION,
        record_semantics="configuration-family source record",
        identifier_definition="Oxford CICY Num source identifier",
        expected_count=7890,
        adapter_capabilities=(AdapterCapability.STREAMING.value, AdapterCapability.NATIVE_PAYLOAD.value),
        metadata={"schema": CICY3_SCHEMA.to_dict(), "basis_sensitive_fields": ["c2"]},
    )


def cicy4_descriptor() -> DatasetDescriptor:
    return DatasetDescriptor(
        dataset_id=HodgeCYID.dataset(CICY4_SCHEMA.dataset_id),
        name="Complete CICY fourfold configurations/topology",
        construction_family=ConstructionFamily.known("cicy4"),
        acquisition_status=AcquisitionStatus.COMPLETE_LOCAL,
        redistribution_status=RedistributionStatus.ACQUIRED_LOCALLY_BY_USER,
        source_version=CICY4_SOURCE_REVISION,
        record_semantics="configuration/topology source record",
        identifier_definition="Oxford CICY4 matrix number source identifier",
        expected_count=921497,
        adapter_capabilities=(AdapterCapability.STREAMING.value, AdapterCapability.NATIVE_PAYLOAD.value),
        metadata={"schema": CICY4_SCHEMA.to_dict(), "dimension_independent_hodge": True},
    )


def cicy3_adapter(sources: Iterable[SourceChunk]) -> FixtureDatasetAdapter:
    return _adapter(CICY3_SCHEMA, sources, "cicy3_adapter")


def cicy4_adapter(sources: Iterable[SourceChunk]) -> FixtureDatasetAdapter:
    return _adapter(CICY4_SCHEMA, sources, "cicy4_adapter")


def normalize_cicy_payload(payload: dict[str, Any], schema: CICYAdapterSchema) -> dict[str, Any]:
    normalized = dict(payload)
    normalized["dimension"] = schema.dimension
    normalized["construction_family"] = "cicy3" if schema.dimension == 3 else "cicy4"
    normalized["source_record_id"] = str(payload[schema.source_key])
    normalized["presentation_kind"] = "configuration_matrix"
    normalized["hodge_numbers"] = {key: payload[key] for key in schema.hodge_keys if key in payload}
    return normalized


def validate_cicy_payload(payload: dict[str, Any], schema: CICYAdapterSchema) -> list[str]:
    errors: list[str] = []
    if schema.source_key not in payload:
        errors.append(f"missing source key {schema.source_key}")
    matrix = payload.get(schema.matrix_key)
    if not isinstance(matrix, list) or not matrix or not all(isinstance(row, list) and row for row in matrix):
        errors.append("configuration_matrix must be a non-empty rectangular list")
    elif len({len(row) for row in matrix}) != 1:
        errors.append("configuration_matrix rows must have equal length")
    if payload.get("dimension", schema.dimension) != schema.dimension:
        errors.append(f"dimension must be {schema.dimension}")
    for key in schema.hodge_keys:
        if key in payload and not isinstance(payload[key], int):
            errors.append(f"{key} must be an integer when present")
    if "euler" in payload and not isinstance(payload["euler"], int):
        errors.append("euler must be an integer when present")
    return errors


def cicy_query_rows(run: AdapterRun) -> list[dict[str, Any]]:
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
                "h31": record.payload.get("h31"),
                "h22": record.payload.get("h22"),
                "euler": record.payload.get("euler"),
                "source_locator": record.source_locator.to_dict(),
            })
    return rows


def _adapter(schema: CICYAdapterSchema, sources: Iterable[SourceChunk], adapter_name: str) -> FixtureDatasetAdapter:
    return FixtureDatasetAdapter(
        descriptor=DatasetAdapterDescriptor(
            dataset_id=HodgeCYID.dataset(schema.dataset_id),
            adapter_name=adapter_name,
            adapter_version=ADAPTER_VERSION,
            capabilities=(AdapterCapability.STREAMING, AdapterCapability.NATIVE_PAYLOAD),
        ),
        parser=CICYJsonlParser(schema),
        sources=sources,
        identifier_definition=f"{schema.source_key} source identifier",
    )


def _event(schema: CICYAdapterSchema, method: str) -> ValidationEvent:
    return ValidationEvent(
        dimension=ValidationDimension.PRESENTATION,
        status=ValidationStatus.SYNTACTICALLY_VALIDATED,
        method=method,
        evidence={"schema": schema.to_dict()},
        validator="hodgecy.datasets.cicy",
        validator_version=ADAPTER_VERSION,
    )
