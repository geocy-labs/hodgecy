from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from hodgecy.core.errors import ValidationError

_FIELD_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$|^h\^\([0-9]+,[0-9]+\)$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_field_name(field: str) -> None:
    if not _FIELD_RE.fullmatch(field):
        raise ValidationError(f"Unsafe or invalid query field: {field!r}")


def validate_identifier(identifier: str) -> None:
    if not _IDENTIFIER_RE.fullmatch(identifier):
        raise ValidationError(f"Unsafe physical field identifier: {identifier!r}")


def hodge_field(p: int, q: int) -> str:
    if p < 0 or q < 0:
        raise ValidationError("Hodge indices must be non-negative")
    return f"h^({p},{q})"


@dataclass(frozen=True, slots=True)
class FieldRegistry:
    physical_fields: tuple[str, ...]
    semantic_mapping: dict[str, str] = field(default_factory=dict)
    heavy_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for physical in self.physical_fields:
            validate_identifier(physical)
        for semantic, physical in self.semantic_mapping.items():
            validate_field_name(semantic)
            validate_identifier(physical)

    @classmethod
    def from_schema(cls, fields: Iterable[str], *, semantic_mapping: dict[str, str] | None = None, heavy_fields: Iterable[str] = ()) -> "FieldRegistry":
        field_tuple = tuple(fields)
        mapping = dict(semantic_mapping or {})
        if "h11" in field_tuple:
            mapping.setdefault(hodge_field(1, 1), "h11")
        if "h12" in field_tuple:
            mapping.setdefault(hodge_field(1, 2), "h12")
            mapping.setdefault(hodge_field(2, 1), "h12")
        if "h21" in field_tuple:
            mapping.setdefault(hodge_field(2, 1), "h21")
        if "h31" in field_tuple:
            mapping.setdefault(hodge_field(3, 1), "h31")
        if "h22" in field_tuple:
            mapping.setdefault(hodge_field(2, 2), "h22")
        return cls(field_tuple, mapping, tuple(heavy_fields))

    def resolve(self, field: str) -> str:
        validate_field_name(field)
        physical = self.semantic_mapping.get(field, field)
        validate_identifier(physical)
        if physical not in self.physical_fields:
            raise ValidationError(f"Field is not available in this query source: {field!r}")
        return physical

    def projection(self, fields: Iterable[str], *, include_heavy: bool = False) -> list[str]:
        resolved: list[str] = []
        for field in fields:
            physical = self.resolve(field)
            if not include_heavy and physical in self.heavy_fields:
                raise ValidationError(f"Field requires explicit heavy-column opt-in: {field!r}")
            if physical not in resolved:
                resolved.append(physical)
        return resolved
