from __future__ import annotations

import json
from typing import Any

from hodgecy.core.status import ValidationDimension, ValidationEvent, ValidationStatus

from .base import ParseResult, ParsedRecord, SourceChunk, parser_provenance, reject


class JsonlParser:
    parser_name = "jsonl"
    parser_version = "1.0.0"
    payload_type = "json_object"

    def parse(self, source: SourceChunk) -> ParseResult:
        provenance = parser_provenance(self.parser_name, self.parser_version)
        records: list[ParsedRecord] = []
        rejected = []
        for line_number, line in enumerate(source.text().splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                rejected.append(reject(
                    source,
                    parser_name=self.parser_name,
                    parser_version=self.parser_version,
                    error_code="invalid_json",
                    error_message=str(exc),
                    payload_excerpt=stripped,
                    source_line=line_number,
                ))
                continue
            if not isinstance(payload, dict):
                rejected.append(reject(
                    source,
                    parser_name=self.parser_name,
                    parser_version=self.parser_version,
                    error_code="jsonl_record_not_object",
                    error_message="JSONL records must be JSON objects.",
                    payload_excerpt=stripped,
                    source_line=line_number,
                ))
                continue
            native_id = _native_id(payload, line_number)
            records.append(ParsedRecord(
                native_id=native_id,
                payload=payload,
                payload_type=self.payload_type,
                source_locator=source.locator(source_line=line_number),
                source_provenance=source.source_provenance(source_locator=f"line:{line_number}"),
                parser_provenance=provenance,
                validation_events=(_event("json_line_object", {"line": line_number}),),
            ))
        return ParseResult(provenance, tuple(records), tuple(rejected))


def _native_id(payload: dict[str, Any], line_number: int) -> str:
    for key in ("id", "record_id", "name"):
        value = payload.get(key)
        if isinstance(value, (str, int)):
            normalized = str(value).replace(" ", "_")
            if normalized and normalized[0].isalnum():
                return normalized
    return f"line-{line_number}"


def _event(method: str, evidence: dict[str, Any]) -> ValidationEvent:
    return ValidationEvent(
        dimension=ValidationDimension.PARSE,
        status=ValidationStatus.SYNTACTICALLY_VALIDATED,
        method=method,
        evidence=evidence,
        validator="hodgecy.parsers.jsonl",
        validator_version=JsonlParser.parser_version,
    )
