from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable

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


class FieldWeight(str, Enum):
    LIGHT = "light"
    NESTED = "nested"
    HEAVY = "heavy"
    MATERIALIZATION_ONLY = "materialization_only"


@dataclass(frozen=True, slots=True)
class FieldMetadata:
    name: str
    weight: FieldWeight = FieldWeight.LIGHT
    indexable: bool = True
    projection_safe: bool = True
    materialization_only: bool = False
    description: str | None = None

    def __post_init__(self) -> None:
        validate_identifier(self.name)

    @property
    def is_heavy(self) -> bool:
        return self.weight in {FieldWeight.NESTED, FieldWeight.HEAVY, FieldWeight.MATERIALIZATION_ONLY} or self.materialization_only

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "weight": self.weight.value,
            "indexable": self.indexable,
            "projection_safe": self.projection_safe,
            "materialization_only": self.materialization_only,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "FieldMetadata":
        return cls(
            name=str(payload["name"]),
            weight=FieldWeight(payload.get("weight", FieldWeight.LIGHT.value)),
            indexable=bool(payload.get("indexable", True)),
            projection_safe=bool(payload.get("projection_safe", True)),
            materialization_only=bool(payload.get("materialization_only", False)),
            description=payload.get("description"),
        )


@dataclass(frozen=True, slots=True)
class FieldRegistry:
    physical_fields: tuple[str, ...]
    semantic_mapping: dict[str, str] = field(default_factory=dict)
    heavy_fields: tuple[str, ...] = ()
    field_metadata: dict[str, FieldMetadata] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for physical in self.physical_fields:
            validate_identifier(physical)
        for semantic, physical in self.semantic_mapping.items():
            validate_field_name(semantic)
            validate_identifier(physical)
        for name in self.field_metadata:
            validate_identifier(name)

    @classmethod
    def from_schema(
        cls,
        fields: Iterable[str],
        *,
        semantic_mapping: dict[str, str] | None = None,
        heavy_fields: Iterable[str] = (),
        field_metadata: dict[str, FieldMetadata | dict[str, Any]] | None = None,
    ) -> "FieldRegistry":
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
        metadata: dict[str, FieldMetadata] = {}
        supplied = field_metadata or {}
        heavy_tuple = tuple(heavy_fields)
        for field_name in field_tuple:
            payload = supplied.get(field_name)
            if isinstance(payload, FieldMetadata):
                metadata[field_name] = payload
            elif isinstance(payload, dict):
                metadata[field_name] = FieldMetadata.from_dict({"name": field_name, **payload})
            elif field_name in heavy_tuple:
                metadata[field_name] = FieldMetadata(field_name, FieldWeight.HEAVY, indexable=False, projection_safe=False)
            else:
                metadata[field_name] = FieldMetadata(field_name)
        heavy = tuple(name for name in field_tuple if name in heavy_tuple or metadata[name].is_heavy)
        return cls(field_tuple, mapping, heavy, metadata)

    def resolve(self, field: str) -> str:
        validate_field_name(field)
        physical = self.semantic_mapping.get(field, field)
        validate_identifier(physical)
        if physical not in self.physical_fields:
            raise ValidationError(f"Field is not available in this query source: {field!r}")
        return physical

    def metadata_for(self, field: str) -> FieldMetadata:
        physical = self.resolve(field)
        return self.field_metadata.get(physical, FieldMetadata(physical))

    def projection(self, fields: Iterable[str], *, include_heavy: bool = False) -> list[str]:
        resolved: list[str] = []
        for field in fields:
            physical = self.resolve(field)
            metadata = self.field_metadata.get(physical)
            if metadata is not None and (metadata.materialization_only or not metadata.projection_safe) and not include_heavy:
                raise ValidationError(f"Field requires explicit heavy-column opt-in: {field!r}")
            if not include_heavy and physical in self.heavy_fields:
                raise ValidationError(f"Field requires explicit heavy-column opt-in: {field!r}")
            if physical not in resolved:
                resolved.append(physical)
        return resolved
