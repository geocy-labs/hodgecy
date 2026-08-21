from __future__ import annotations

from typing import Any, Iterable

from hodgecy.core.adapters import AdapterCapability, DatasetAdapterDescriptor
from hodgecy.core.dataset import ConstructionFamily, DatasetDescriptor
from hodgecy.core.ids import HodgeCYID
from hodgecy.core.status import AcquisitionStatus, RedistributionStatus, ValidationDimension, ValidationEvent, ValidationStatus
from hodgecy.datasets.base import AdapterRun, FixtureDatasetAdapter
from hodgecy.datasets.cynk_meyer import load_family_equations, load_rigid_equations, load_table1, validate_table1
from hodgecy.parsers import JsonlParser, SourceChunk
from hodgecy.parsers.base import ParseResult, ParsedRecord, parser_provenance, reject

ADAPTER_VERSION = "1.0.0"
DOUBLE_OCTIC_SOURCE_REVISION = "hodgecy-i-cynk-meyer-local"


class DoubleOcticJsonlParser:
    parser_name = "double_octic_jsonl"
    parser_version = ADAPTER_VERSION
    payload_type = "double_octic_source_record"

    def __init__(self) -> None:
        self._jsonl = JsonlParser()

    def parse(self, source: SourceChunk) -> ParseResult:
        result = self._jsonl.parse(source)
        provenance = parser_provenance(self.parser_name, self.parser_version)
        records: list[ParsedRecord] = []
        rejected = list(result.rejected)
        for record in result.records:
            errors = validate_double_octic_payload(record.payload)
            if errors:
                rejected.append(reject(
                    source,
                    parser_name=self.parser_name,
                    parser_version=self.parser_version,
                    error_code="invalid_double_octic_payload",
                    error_message="; ".join(errors),
                    payload_excerpt=str(record.payload),
                    source_line=record.source_locator.source_line,
                ))
                continue
            payload = normalize_double_octic_payload(record.payload)
            records.append(ParsedRecord(
                native_id=payload["source_record_id"],
                payload=payload,
                payload_type=self.payload_type,
                source_locator=record.source_locator,
                source_provenance=record.source_provenance,
                parser_provenance=provenance,
                validation_events=record.validation_events + (_event("double_octic_source_shape"),),
            ))
        return ParseResult(provenance, tuple(records), tuple(rejected), result.validation_events)


def double_octic_descriptor() -> DatasetDescriptor:
    return DatasetDescriptor(
        dataset_id=HodgeCYID.dataset("double_octic_cynk_meyer"),
        name="Cynk-Meyer double-octic HodgeCY I source corpus",
        construction_family=ConstructionFamily.known("double_octic"),
        acquisition_status=AcquisitionStatus.COMPLETE_LOCAL,
        redistribution_status=RedistributionStatus.REDISTRIBUTABLE,
        source_version=DOUBLE_OCTIC_SOURCE_REVISION,
        record_semantics="HodgeCY I source/reproduction record, separate from derived theorem outputs",
        identifier_definition="arrangement label",
        adapter_capabilities=(AdapterCapability.STREAMING.value, AdapterCapability.NATIVE_PAYLOAD.value),
        metadata={"compatibility_wrapped_module": "hodgecy.datasets.cynk_meyer"},
    )


def double_octic_adapter(sources: Iterable[SourceChunk]) -> FixtureDatasetAdapter:
    return FixtureDatasetAdapter(
        descriptor=DatasetAdapterDescriptor(
            dataset_id=HodgeCYID.dataset("double_octic_cynk_meyer"),
            adapter_name="double_octic_adapter",
            adapter_version=ADAPTER_VERSION,
            capabilities=(AdapterCapability.STREAMING, AdapterCapability.NATIVE_PAYLOAD),
        ),
        parser=DoubleOcticJsonlParser(),
        sources=sources,
        identifier_definition="arrangement label",
    )


def load_table1_source_records() -> list[dict[str, Any]]:
    frame = load_table1()
    validate_table1(frame)
    return [normalize_double_octic_payload(dict(row)) for row in frame.to_dict(orient="records")]


def load_rigid_equation_source_records() -> list[dict[str, Any]]:
    return [dict(row) for row in load_rigid_equations()]


def load_family_equation_source_records() -> list[dict[str, Any]]:
    return [dict(row) for row in load_family_equations()]


def validate_double_octic_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if "arrangement" not in payload and "id" not in payload:
        errors.append("arrangement or id is required")
    for key in ("h11", "h12", "euler"):
        if key in payload and payload[key] is not None and not isinstance(payload[key], int):
            errors.append(f"{key} must be an integer when present")
    return errors


def normalize_double_octic_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    source_id = str(payload.get("arrangement") or payload.get("id"))
    normalized["source_record_id"] = source_id
    normalized["construction_family"] = "double_octic"
    normalized["dimension"] = 3
    normalized["presentation_kind"] = "plane_arrangement"
    normalized["derived_hodgecy_i_outputs_separate"] = True
    return normalized


def double_octic_query_rows(run: AdapterRun) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in run.parse_results:
        for record in result.records:
            rows.append({
                "dataset_id": record.source_provenance.source_dataset,
                "source_record_id": record.payload["source_record_id"],
                "construction_family": "double_octic",
                "dimension": 3,
                "h11": record.payload.get("h11"),
                "h21": record.payload.get("h12"),
                "h12": record.payload.get("h12"),
                "euler": record.payload.get("euler"),
                "is_hodgecy_i_control": record.payload.get("source_record_id") in {"84", "84a", "239", "240", "241"},
                "source_locator": record.source_locator.to_dict(),
            })
    return rows


def _event(method: str) -> ValidationEvent:
    return ValidationEvent(
        dimension=ValidationDimension.PRESENTATION,
        status=ValidationStatus.SOURCE_REPORTED,
        method=method,
        evidence={"wrapper": "hodgecy.datasets.cynk_meyer", "derived_outputs_separate": True},
        validator="hodgecy.datasets.double_octics",
        validator_version=ADAPTER_VERSION,
    )
