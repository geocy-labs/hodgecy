from __future__ import annotations

from dataclasses import asdict
from typing import Any, Iterable

from hodgecy.core.adapters import AdapterCapability, DatasetAdapterDescriptor
from hodgecy.core.dataset import ConstructionFamily, DatasetDescriptor
from hodgecy.core.ids import HodgeCYID
from hodgecy.core.status import AcquisitionStatus, RedistributionStatus, ValidationDimension, ValidationEvent, ValidationStatus
from hodgecy.datasets.base import AdapterRun, FixtureDatasetAdapter
from hodgecy.operators.picard_fuchs import PicardFuchsOperator
from hodgecy.parsers import JsonlParser, SourceChunk
from hodgecy.parsers.base import ParseResult, ParsedRecord, parser_provenance, reject

ADAPTER_VERSION = "1.0.0"
PF_SOURCE_REVISION = "cyo-picard-fuchs-local"


class PicardFuchsJsonlParser:
    parser_name = "picard_fuchs_jsonl"
    parser_version = ADAPTER_VERSION
    payload_type = "picard_fuchs_operator_source"

    def __init__(self) -> None:
        self._jsonl = JsonlParser()

    def parse(self, source: SourceChunk) -> ParseResult:
        result = self._jsonl.parse(source)
        provenance = parser_provenance(self.parser_name, self.parser_version)
        records: list[ParsedRecord] = []
        rejected = list(result.rejected)
        for record in result.records:
            errors = validate_operator_payload(record.payload)
            if errors:
                rejected.append(reject(
                    source,
                    parser_name=self.parser_name,
                    parser_version=self.parser_version,
                    error_code="invalid_picard_fuchs_payload",
                    error_message="; ".join(errors),
                    payload_excerpt=str(record.payload),
                    source_line=record.source_locator.source_line,
                ))
                continue
            payload = normalize_operator_payload(record.payload)
            records.append(ParsedRecord(
                native_id=payload["source_record_id"],
                payload=payload,
                payload_type=self.payload_type,
                source_locator=record.source_locator,
                source_provenance=record.source_provenance,
                parser_provenance=provenance,
                validation_events=record.validation_events + (_event("operator_source_shape"),),
            ))
        return ParseResult(provenance, tuple(records), tuple(rejected), result.validation_events)


def picard_fuchs_descriptor() -> DatasetDescriptor:
    return DatasetDescriptor(
        dataset_id=HodgeCYID.dataset("picard_fuchs_cyo_topological"),
        name="Calabi-Yau operator topological data",
        construction_family=ConstructionFamily.known("operator_family"),
        acquisition_status=AcquisitionStatus.COMPLETE_LOCAL,
        redistribution_status=RedistributionStatus.ACQUIRED_LOCALLY_BY_USER,
        source_version=PF_SOURCE_REVISION,
        record_semantics="operator/topology source lines; not geometry records",
        identifier_definition="operator source id",
        expected_count=1197,
        adapter_capabilities=(AdapterCapability.STREAMING.value, AdapterCapability.NATIVE_PAYLOAD.value),
        metadata={"operator_rows": 613, "topological_rows": 584, "geometry_identity_inference": False},
    )


def picard_fuchs_adapter(sources: Iterable[SourceChunk]) -> FixtureDatasetAdapter:
    return FixtureDatasetAdapter(
        descriptor=DatasetAdapterDescriptor(
            dataset_id=HodgeCYID.dataset("picard_fuchs_cyo_topological"),
            adapter_name="picard_fuchs_adapter",
            adapter_version=ADAPTER_VERSION,
            capabilities=(AdapterCapability.STREAMING, AdapterCapability.NATIVE_PAYLOAD),
        ),
        parser=PicardFuchsJsonlParser(),
        sources=sources,
        identifier_definition="operator source id",
    )


def to_picard_fuchs_operator(payload: dict[str, Any]) -> PicardFuchsOperator:
    return PicardFuchsOperator(
        example_id=str(payload["source_record_id"]),
        operator_label=payload.get("operator_label"),
        order=payload.get("order"),
        coefficients=payload.get("coefficients"),
        source=payload.get("source"),
        status="source_reported",
        notes=payload.get("notes"),
    )


def validate_operator_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if "operator_id" not in payload and "id" not in payload:
        errors.append("operator_id or id is required")
    if "order" in payload and payload["order"] is not None and not isinstance(payload["order"], int):
        errors.append("order must be an integer when present")
    if "coefficients" in payload and payload["coefficients"] is not None:
        coefficients = payload["coefficients"]
        if not isinstance(coefficients, list) or not all(isinstance(item, str) for item in coefficients):
            errors.append("coefficients must be a list of strings when present")
    return errors


def normalize_operator_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    normalized["source_record_id"] = str(payload.get("operator_id") or payload.get("id"))
    normalized["construction_family"] = "operator_family"
    normalized["presentation_kind"] = "picard_fuchs_operator"
    normalized["is_geometry_record"] = False
    return normalized


def operator_query_rows(run: AdapterRun) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in run.parse_results:
        for record in result.records:
            operator = to_picard_fuchs_operator(record.payload)
            rows.append({
                "dataset_id": record.source_provenance.source_dataset,
                "source_record_id": record.payload["source_record_id"],
                "construction_family": "operator_family",
                "operator_label": operator.operator_label,
                "operator_order": operator.order,
                "is_geometry_record": False,
                "source_locator": record.source_locator.to_dict(),
            })
    return rows


def _event(method: str) -> ValidationEvent:
    return ValidationEvent(
        dimension=ValidationDimension.OPERATOR,
        status=ValidationStatus.SOURCE_REPORTED,
        method=method,
        evidence={"safe_evaluation": False, "source_semantics": "operator_not_geometry"},
        validator="hodgecy.datasets.operators",
        validator_version=ADAPTER_VERSION,
    )
