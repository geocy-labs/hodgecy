from __future__ import annotations

import re
from typing import Any

from hodgecy.core.status import ValidationDimension, ValidationEvent, ValidationStatus

from .base import ParseResult, ParsedRecord, SourceChunk, parser_provenance, reject

_TOKEN_RE = re.compile(r'\s*(->|[{} ,]|"(?:[^"\\]|\\.)*"|-?\d+|[A-Za-z$][A-Za-z0-9_$`]*|.)')


class MathematicaRuleParser:
    parser_name = "mathematica_rules"
    parser_version = "1.0.0"
    payload_type = "mathematica_rule_payload"

    def parse(self, source: SourceChunk) -> ParseResult:
        provenance = parser_provenance(self.parser_name, self.parser_version)
        records: list[ParsedRecord] = []
        rejected = []
        for index, statement in enumerate(_statements(source.text()), start=1):
            try:
                payload = _Parser(statement).parse()
            except ValueError as exc:
                rejected.append(reject(
                    source,
                    parser_name=self.parser_name,
                    parser_version=self.parser_version,
                    error_code="invalid_mathematica_rule_syntax",
                    error_message=str(exc),
                    payload_excerpt=statement,
                    source_block=str(index),
                ))
                continue
            if not isinstance(payload, dict):
                payload = {"value": payload}
            native_id = str(payload.get("id") or payload.get("ID") or payload.get("Name") or f"rule-{index}").replace(" ", "_")
            records.append(ParsedRecord(
                native_id=native_id,
                payload=payload,
                payload_type=self.payload_type,
                source_locator=source.locator(source_block=str(index)),
                source_provenance=source.source_provenance(source_locator=f"statement:{index}"),
                parser_provenance=provenance,
                validation_events=(_event(index),),
            ))
        return ParseResult(provenance, tuple(records), tuple(rejected))


class _Parser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.tokens = [match.group(1) for match in _TOKEN_RE.finditer(self.text) if match.group(1).strip()]
        self.index = 0

    def parse(self) -> Any:
        value = self._expr()
        if self.index != len(self.tokens):
            raise ValueError(f"Unexpected token {self.tokens[self.index]!r}.")
        return value

    def _expr(self) -> Any:
        token = self._peek()
        if token == "{":
            return self._list_or_rules()
        if token is None:
            raise ValueError("Unexpected end of input.")
        self.index += 1
        if token.startswith('"'):
            return bytes(token[1:-1], "utf-8").decode("unicode_escape")
        if re.fullmatch(r"-?\d+", token):
            return int(token)
        if re.fullmatch(r"[A-Za-z$][A-Za-z0-9_$`]*", token):
            return token
        raise ValueError(f"Unsupported token {token!r}.")

    def _list_or_rules(self) -> Any:
        self._expect("{")
        items: list[Any] = []
        rules: list[tuple[str, Any]] = []
        saw_rule = False
        while self._peek() != "}":
            if self._peek() is None:
                raise ValueError("Unclosed list.")
            key_or_value = self._expr()
            if self._peek() == "->":
                if not isinstance(key_or_value, str):
                    raise ValueError("Mathematica rule keys must be symbols or strings.")
                self._expect("->")
                rules.append((key_or_value, self._expr()))
                saw_rule = True
            else:
                if saw_rule:
                    raise ValueError("Cannot mix rules and list values in one list.")
                items.append(key_or_value)
            if self._peek() == ",":
                self._expect(",")
            elif self._peek() != "}":
                raise ValueError(f"Expected ',' or '}}', got {self._peek()!r}.")
        self._expect("}")
        if saw_rule:
            return dict(rules)
        return items

    def _peek(self) -> str | None:
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index]

    def _expect(self, token: str) -> None:
        if self._peek() != token:
            raise ValueError(f"Expected {token!r}, got {self._peek()!r}.")
        self.index += 1


def _statements(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []
    statements = [part.strip() for part in stripped.split("\n\n") if part.strip()]
    if len(statements) == 1 and stripped.startswith("{") and stripped.endswith("}"):
        return statements
    return statements


def _event(index: int) -> ValidationEvent:
    return ValidationEvent(
        dimension=ValidationDimension.PARSE,
        status=ValidationStatus.SYNTACTICALLY_VALIDATED,
        method="safe_mathematica_rule_tokenizer",
        evidence={"statement": index},
        validator="hodgecy.parsers.mathematica",
        validator_version=MathematicaRuleParser.parser_version,
    )
