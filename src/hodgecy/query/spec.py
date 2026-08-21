from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from hodgecy.core.serialization import stable_sha256

from .predicates import Predicate


@dataclass(frozen=True, slots=True)
class MaterializationPolicy:
    row_limit: int = 100_000
    allow_over_limit: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"row_limit": self.row_limit, "allow_over_limit": self.allow_over_limit}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MaterializationPolicy":
        return cls(int(payload.get("row_limit", 100_000)), bool(payload.get("allow_over_limit", False)))


@dataclass(frozen=True, slots=True)
class OrderBy:
    field: str
    descending: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"field": self.field, "descending": self.descending}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "OrderBy":
        return cls(str(payload["field"]), bool(payload.get("descending", False)))


@dataclass(frozen=True, slots=True)
class Aggregation:
    function: str
    field: str | None = None
    alias: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"function": self.function, "field": self.field, "alias": self.alias}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Aggregation":
        return cls(str(payload["function"]), payload.get("field"), payload.get("alias"))


@dataclass(frozen=True, slots=True)
class QuerySpec:
    datasets: tuple[str, ...] = ()
    table: str | None = None
    predicate: Predicate | None = None
    fields: tuple[str, ...] = ()
    limit_value: int | None = None
    offset: int | None = None
    order_by_fields: tuple[OrderBy, ...] = ()
    group_by_fields: tuple[str, ...] = ()
    aggregations: tuple[Aggregation, ...] = ()
    materialization_policy: MaterializationPolicy = field(default_factory=MaterializationPolicy)
    include_heavy: bool = False
    sample_fraction: float | None = None

    def where(self, predicate: Predicate) -> "QuerySpec":
        combined = predicate if self.predicate is None else self.predicate & predicate
        return replace(self, predicate=combined)

    def where_hodge(self, **values: int) -> "QuerySpec":
        from .predicates import Q
        mapping = {"h11": (1, 1), "h12": (1, 2), "h21": (2, 1), "h31": (3, 1), "h22": (2, 2)}
        spec = self
        for key, value in values.items():
            p, q = mapping[key]
            spec = spec.where(Q.hodge(p, q) == value)
        return spec

    def select(self, *fields: str) -> "QuerySpec":
        return replace(self, fields=tuple(fields))

    def limit(self, n: int) -> "QuerySpec":
        return replace(self, limit_value=n)

    def order_by(self, field: str, *, descending: bool = False) -> "QuerySpec":
        return replace(self, order_by_fields=self.order_by_fields + (OrderBy(field, descending),))

    def group_by(self, *fields: str) -> "QuerySpec":
        return replace(self, group_by_fields=tuple(fields))

    def aggregate(self, *aggregations: Aggregation) -> "QuerySpec":
        return replace(self, aggregations=tuple(aggregations))

    def to_dict(self) -> dict[str, Any]:
        return {
            "datasets": list(self.datasets),
            "table": self.table,
            "predicate": None if self.predicate is None else self.predicate.to_dict(),
            "fields": list(self.fields),
            "limit": self.limit_value,
            "offset": self.offset,
            "order_by": [order.to_dict() for order in self.order_by_fields],
            "group_by": list(self.group_by_fields),
            "aggregations": [aggregation.to_dict() for aggregation in self.aggregations],
            "materialization_policy": self.materialization_policy.to_dict(),
            "include_heavy": self.include_heavy,
            "sample_fraction": self.sample_fraction,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "QuerySpec":
        return cls(
            datasets=tuple(payload.get("datasets") or ()),
            table=payload.get("table"),
            predicate=Predicate.from_dict(payload["predicate"]) if payload.get("predicate") else None,
            fields=tuple(payload.get("fields") or ()),
            limit_value=payload.get("limit"),
            offset=payload.get("offset"),
            order_by_fields=tuple(OrderBy.from_dict(row) for row in payload.get("order_by") or ()),
            group_by_fields=tuple(payload.get("group_by") or ()),
            aggregations=tuple(Aggregation.from_dict(row) for row in payload.get("aggregations") or ()),
            materialization_policy=MaterializationPolicy.from_dict(payload.get("materialization_policy") or {}),
            include_heavy=bool(payload.get("include_heavy", False)),
            sample_fraction=payload.get("sample_fraction"),
        )

    def stable_id(self) -> str:
        return stable_sha256(self.to_dict())
