from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from hodgecy.storage.errors import MaterializationLimitError, MissingCapabilityError
from hodgecy.storage.planning import EstimateKind, QueryEstimate, QueryPlanSummary


@dataclass(slots=True)
class LazyResultSet:
    query_spec: Any
    registry: Any
    dataset_factory: Any
    paths: tuple[str, ...]
    projected_fields: tuple[str, ...]
    predicate: Any = None
    estimated_rows: int | None = None
    row_limit: int = 100_000
    provenance: dict[str, Any] = field(default_factory=dict)
    plan: QueryPlanSummary | None = None

    def schema(self) -> dict[str, str]:
        return {field: field for field in self.projected_fields}

    def estimated_count(self) -> int | None:
        return self.estimated_rows

    @property
    def heavy_projected_fields(self) -> tuple[str, ...]:
        heavy = set(getattr(self.registry, "heavy_fields", ()))
        return tuple(field for field in self.projected_fields if field in heavy)

    def explain(self) -> dict[str, Any]:
        if self.plan is not None:
            return self.plan.to_dict()
        return {
            "backend": self.provenance.get("backend", "unknown"),
            "projected_columns": list(self.projected_fields),
            "heavy_columns": list(self.heavy_projected_fields),
            "heavy_columns_requested": bool(self.heavy_projected_fields),
            "predicate_pushdown": self.predicate is not None,
            "estimated_rows": {"kind": "known" if self.estimated_rows is not None else "unknown", "rows": self.estimated_rows},
        }

    def count(self) -> int:
        dataset = self.dataset_factory()
        return int(dataset.count_rows(filter=self.predicate))

    def iter_batches(self, *, batch_size: int = 65_536) -> Iterable[Any]:
        if batch_size <= 0:
            raise MaterializationLimitError("iter_batches(batch_size=...) requires a positive batch size")
        dataset = self.dataset_factory()
        scanner = dataset.scanner(columns=list(self.projected_fields), filter=self.predicate, batch_size=batch_size)
        yield from scanner.to_batches()

    def take(self, n: int, *, allow_over_limit: bool = False) -> Any:
        if n < 0:
            raise MaterializationLimitError("take(n) requires n >= 0")
        self._check_materialization_limits(n, allow_over_limit=allow_over_limit)
        scanner = self.dataset_factory().scanner(columns=list(self.projected_fields), filter=self.predicate, batch_size=max(1, min(n or 1, 65_536)))
        return scanner.head(n)

    def head(self, n: int = 5) -> Any:
        return self.take(n)

    def to_arrow(self, *, allow_over_limit: bool = False) -> Any:
        requested = self._requested_rows_for_collect()
        self._check_materialization_limits(requested, allow_over_limit=allow_over_limit)
        table = self.dataset_factory().to_table(columns=list(self.projected_fields), filter=self.predicate)
        if self.query_spec.order_by_fields:
            order = []
            for item in self.query_spec.order_by_fields:
                physical = self.registry.resolve(item.field)
                order.append((physical, "descending" if item.descending else "ascending"))
            table = table.sort_by(order)
        if self.query_spec.offset:
            table = table.slice(self.query_spec.offset)
        if self.query_spec.limit_value is not None:
            table = table.slice(0, self.query_spec.limit_value)
        return table

    def aggregate(self, *, allow_over_limit: bool = False) -> Any:
        try:
            import pyarrow as pa  # type: ignore[import-not-found]
        except ModuleNotFoundError as exc:
            raise MissingCapabilityError("PyArrow is required for aggregation") from exc
        if not self.query_spec.group_by_fields and all(item.function == "count" and item.field is None for item in self.query_spec.aggregations):
            return pa.table({"count": [self.count()]})
        columns = list(self.projected_fields)
        for field in self.query_spec.group_by_fields:
            physical = self.registry.resolve(field)
            if physical not in columns:
                columns.append(physical)
        for item in self.query_spec.aggregations:
            if item.field is not None:
                physical = self.registry.resolve(item.field)
                if physical not in columns:
                    columns.append(physical)
        self._check_materialization_limits(self._requested_rows_for_collect(), allow_over_limit=allow_over_limit)
        table = self.dataset_factory().to_table(columns=columns, filter=self.predicate)
        groups = [self.registry.resolve(field) for field in self.query_spec.group_by_fields]
        aggregations = []
        for item in self.query_spec.aggregations:
            if item.function != "count":
                raise MaterializationLimitError(f"Unsupported Blob 4 aggregation: {item.function}")
            count_field = self.registry.resolve(item.field) if item.field is not None else (groups[0] if groups else columns[0])
            aggregations.append((count_field, "count"))
        if groups:
            return table.group_by(groups).aggregate(aggregations)
        return pa.table({"count": [self.count()]})

    def to_pandas(self, *, allow_over_limit: bool = False) -> Any:
        return self.to_arrow(allow_over_limit=allow_over_limit).to_pandas()

    def materialize(self, path: str, *, allow_over_limit: bool = False) -> str:
        try:
            import pyarrow.parquet as pq  # type: ignore[import-not-found]
        except ModuleNotFoundError as exc:
            raise MissingCapabilityError("PyArrow is required for result materialization") from exc
        pq.write_table(self.to_arrow(allow_over_limit=allow_over_limit), path)
        return path

    def _requested_rows_for_collect(self) -> int:
        if self.query_spec.limit_value is not None:
            return int(self.query_spec.limit_value)
        if self.estimated_rows is not None:
            return int(self.estimated_rows)
        return self.count()

    def _estimated_projected_bytes(self) -> int | None:
        if self.plan is None:
            return None
        estimate = self.plan.estimated_bytes
        if estimate.kind is EstimateKind.UNKNOWN:
            return None
        return estimate.bytes

    def _check_materialization_limits(self, requested_rows: int, *, allow_over_limit: bool = False) -> None:
        policy = self.query_spec.materialization_policy
        override = allow_over_limit or policy.allow_over_limit
        if requested_rows > self.row_limit and not override:
            raise MaterializationLimitError(f"Query would materialize {requested_rows} rows; limit is {self.row_limit}")
        heavy_rows = requested_rows if self.heavy_projected_fields else 0
        heavy_override = override or policy.allow_heavy_over_limit
        if heavy_rows > policy.heavy_row_limit and not heavy_override:
            raise MaterializationLimitError(
                f"Query would materialize {heavy_rows} rows with heavy columns {self.heavy_projected_fields}; "
                f"heavy-row limit is {policy.heavy_row_limit}"
            )
        estimated_bytes = self._estimated_projected_bytes()
        if policy.estimated_byte_limit is not None and estimated_bytes is not None and estimated_bytes > policy.estimated_byte_limit and not override:
            raise MaterializationLimitError(
                f"Query would materialize an estimated {estimated_bytes} bytes; limit is {policy.estimated_byte_limit}"
            )

    def __iter__(self) -> Iterable[Any]:
        raise MaterializationLimitError("Iterating a LazyResultSet directly is disabled; use iter_batches(), head(), or take(n)")
