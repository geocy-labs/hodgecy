from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from typing import Any

from hodgecy.core.errors import ValidationError

from .fields import FieldRegistry, validate_field_name, validate_identifier


@dataclass(frozen=True, slots=True)
class Predicate:
    op: str
    field: str | None = None
    value: Any = None
    children: tuple["Predicate", ...] = dataclass_field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.field is not None:
            validate_field_name(self.field)
        if self.op in {"and", "or"} and not self.children:
            raise ValidationError(f"{self.op} predicate requires children")
        if self.op == "not" and len(self.children) != 1:
            raise ValidationError("not predicate requires exactly one child")

    def __and__(self, other: "Predicate") -> "Predicate":
        return Predicate("and", children=(self, other))

    def __or__(self, other: "Predicate") -> "Predicate":
        return Predicate("or", children=(self, other))

    def __invert__(self) -> "Predicate":
        return Predicate("not", children=(self,))

    def to_dict(self) -> dict[str, Any]:
        return {"op": self.op, "field": self.field, "value": self.value, "children": [child.to_dict() for child in self.children]}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Predicate":
        return cls(str(payload["op"]), payload.get("field"), payload.get("value"), tuple(cls.from_dict(child) for child in payload.get("children") or ()))

    def compile_sql(self, registry: FieldRegistry) -> tuple[str, list[Any]]:
        if self.op in {"and", "or"}:
            parts: list[str] = []
            params: list[Any] = []
            for child in self.children:
                sql, child_params = child.compile_sql(registry)
                parts.append(f"({sql})")
                params.extend(child_params)
            return f" {self.op.upper()} ".join(parts), params
        if self.op == "not":
            sql, params = self.children[0].compile_sql(registry)
            return f"NOT ({sql})", params
        if self.field is None:
            raise ValidationError("Scalar predicate requires a field")
        physical = registry.resolve(self.field)
        validate_identifier(physical)
        if self.op in {"eq", "ne", "lt", "le", "gt", "ge"}:
            symbol = {"eq": "=", "ne": "!=", "lt": "<", "le": "<=", "gt": ">", "ge": ">="}[self.op]
            return f"{physical} {symbol} ?", [self.value]
        if self.op == "in":
            values = list(self.value)
            if not values:
                raise ValidationError("in predicate requires at least one value")
            return f"{physical} IN ({','.join('?' for _ in values)})", values
        if self.op == "between":
            low, high = self.value
            return f"{physical} BETWEEN ? AND ?", [low, high]
        if self.op == "is_null":
            return f"{physical} IS NULL", []
        if self.op == "is_not_null":
            return f"{physical} IS NOT NULL", []
        raise ValidationError(f"Unsupported predicate op: {self.op}")

    def compile_arrow(self, registry: FieldRegistry) -> Any:
        try:
            import pyarrow.dataset as ds  # type: ignore[import-not-found]
        except ModuleNotFoundError as exc:
            from hodgecy.storage.errors import MissingCapabilityError
            raise MissingCapabilityError("PyArrow is required for Arrow predicate compilation") from exc
        if self.op in {"and", "or"}:
            expr = self.children[0].compile_arrow(registry)
            for child in self.children[1:]:
                expr = (expr & child.compile_arrow(registry)) if self.op == "and" else (expr | child.compile_arrow(registry))
            return expr
        if self.op == "not":
            return ~self.children[0].compile_arrow(registry)
        if self.field is None:
            raise ValidationError("Scalar predicate requires a field")
        column = ds.field(registry.resolve(self.field))
        if self.op == "eq":
            return column == self.value
        if self.op == "ne":
            return column != self.value
        if self.op == "lt":
            return column < self.value
        if self.op == "le":
            return column <= self.value
        if self.op == "gt":
            return column > self.value
        if self.op == "ge":
            return column >= self.value
        if self.op == "in":
            return column.isin(list(self.value))
        if self.op == "between":
            low, high = self.value
            return (column >= low) & (column <= high)
        if self.op == "is_null":
            return column.is_null()
        if self.op == "is_not_null":
            return ~column.is_null()
        raise ValidationError(f"Unsupported predicate op: {self.op}")


@dataclass(frozen=True, slots=True)
class FieldExpression:
    name: str

    def __post_init__(self) -> None:
        validate_field_name(self.name)

    def __eq__(self, other: object) -> Predicate:  # type: ignore[override]
        return Predicate("eq", self.name, other)

    def __ne__(self, other: object) -> Predicate:  # type: ignore[override]
        return Predicate("ne", self.name, other)

    def __lt__(self, other: object) -> Predicate:
        return Predicate("lt", self.name, other)

    def __le__(self, other: object) -> Predicate:
        return Predicate("le", self.name, other)

    def __gt__(self, other: object) -> Predicate:
        return Predicate("gt", self.name, other)

    def __ge__(self, other: object) -> Predicate:
        return Predicate("ge", self.name, other)

    def in_(self, values: list[Any] | tuple[Any, ...]) -> Predicate:
        return Predicate("in", self.name, list(values))

    def between(self, low: Any, high: Any) -> Predicate:
        return Predicate("between", self.name, [low, high])

    def is_null(self) -> Predicate:
        return Predicate("is_null", self.name)

    def is_not_null(self) -> Predicate:
        return Predicate("is_not_null", self.name)


class Q:
    @staticmethod
    def col(name: str) -> FieldExpression:
        return FieldExpression(name)

    @staticmethod
    def hodge(p: int, q: int) -> FieldExpression:
        from .fields import hodge_field
        return FieldExpression(hodge_field(p, q))

    @staticmethod
    def dataset(dataset_id: str) -> "QuerySpec":
        from .spec import QuerySpec
        return QuerySpec(datasets=(dataset_id,))
