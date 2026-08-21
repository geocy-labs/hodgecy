from __future__ import annotations

from io import BytesIO
from typing import Any

from hodgecy.storage.errors import MissingCapabilityError
from hodgecy.core.status import ValidationDimension, ValidationEvent, ValidationStatus

from .base import ParseResult, ParsedRecord, SourceChunk, parser_provenance


class ParquetRowParser:
    parser_name = "parquet_rows"
    parser_version = "1.0.0"
    payload_type = "parquet_row"

    def __init__(self, *, max_rows: int | None = None, columns: list[str] | None = None) -> None:
        self.max_rows = max_rows
        self.columns = columns

    def parse(self, source: SourceChunk) -> ParseResult:
        try:
            import pyarrow.parquet as pq
        except ImportError as exc:
            raise MissingCapabilityError("Parquet parsing requires optional dependency 'pyarrow'.") from exc

        provenance = parser_provenance(self.parser_name, self.parser_version)
        records: list[ParsedRecord] = []
        reader = pq.ParquetFile(source.relative_path) if source.relative_path else pq.ParquetFile(BytesIO(source.bytes()))
        remaining = self.max_rows
        for row_group_index in range(reader.num_row_groups):
            if remaining is not None and remaining <= 0:
                break
            table = reader.read_row_group(row_group_index, columns=self.columns)
            rows = table.to_pylist()
            if remaining is not None:
                rows = rows[:remaining]
            for row_offset, payload in enumerate(rows):
                native_id = _native_id(payload, row_group_index, row_offset)
                records.append(ParsedRecord(
                    native_id=native_id,
                    payload=dict(payload),
                    payload_type=self.payload_type,
                    source_locator=source.locator(row_group=row_group_index, row_offset=row_offset),
                    source_provenance=source.source_provenance(source_locator=f"row_group:{row_group_index}:row:{row_offset}"),
                    parser_provenance=provenance,
                    validation_events=(_event(row_group_index, row_offset),),
                ))
            if remaining is not None:
                remaining -= len(rows)
        return ParseResult(provenance, tuple(records), ())


def _native_id(payload: dict[str, Any], row_group: int, row_offset: int) -> str:
    for key in ("id", "record_id", "name"):
        value = payload.get(key)
        if isinstance(value, (str, int)):
            normalized = str(value).replace(" ", "_")
            if normalized and normalized[0].isalnum():
                return normalized
    return f"row-{row_group}-{row_offset}"


def _event(row_group: int, row_offset: int) -> ValidationEvent:
    return ValidationEvent(
        dimension=ValidationDimension.PARSE,
        status=ValidationStatus.SYNTACTICALLY_VALIDATED,
        method="pyarrow_parquet_row",
        evidence={"row_group": row_group, "row_offset": row_offset},
        validator="hodgecy.parsers.parquet",
        validator_version=ParquetRowParser.parser_version,
    )
