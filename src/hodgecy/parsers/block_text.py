from __future__ import annotations

from hodgecy.core.status import ValidationDimension, ValidationEvent, ValidationStatus

from .base import ParseResult, ParsedRecord, SourceChunk, parser_provenance, reject


class BlockTextParser:
    parser_name = "block_text"
    parser_version = "1.0.0"
    payload_type = "key_value_block"

    def parse(self, source: SourceChunk) -> ParseResult:
        provenance = parser_provenance(self.parser_name, self.parser_version)
        records: list[ParsedRecord] = []
        rejected = []
        for index, block in enumerate(_blocks(source.text()), start=1):
            payload: dict[str, str] = {}
            bad_lines: list[str] = []
            first_line = block[0][0]
            for _, line in block:
                if ":" not in line:
                    bad_lines.append(line)
                    continue
                key, value = line.split(":", 1)
                key = key.strip()
                if not key:
                    bad_lines.append(line)
                    continue
                payload[key] = value.strip()
            if bad_lines or not payload:
                rejected.append(reject(
                    source,
                    parser_name=self.parser_name,
                    parser_version=self.parser_version,
                    error_code="invalid_key_value_block",
                    error_message="Every non-empty block line must contain a non-empty 'key: value' pair.",
                    payload_excerpt="\n".join(line for _, line in block),
                    source_line=first_line,
                    source_block=str(index),
                ))
                continue
            native_id = payload.get("id") or payload.get("name") or f"block-{index}"
            records.append(ParsedRecord(
                native_id=native_id.replace(" ", "_"),
                payload=payload,
                payload_type=self.payload_type,
                source_locator=source.locator(source_line=first_line, source_block=str(index)),
                source_provenance=source.source_provenance(source_locator=f"block:{index}"),
                parser_provenance=provenance,
                validation_events=(_event(index),),
            ))
        return ParseResult(provenance, tuple(records), tuple(rejected))


def _blocks(text: str) -> list[list[tuple[int, str]]]:
    blocks: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    for line_number, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped == "---":
            if current:
                blocks.append(current)
                current = []
            continue
        current.append((line_number, stripped))
    if current:
        blocks.append(current)
    return blocks


def _event(index: int) -> ValidationEvent:
    return ValidationEvent(
        dimension=ValidationDimension.PARSE,
        status=ValidationStatus.SYNTACTICALLY_VALIDATED,
        method="colon_delimited_block",
        evidence={"block": index},
        validator="hodgecy.parsers.block_text",
        validator_version=BlockTextParser.parser_version,
    )
