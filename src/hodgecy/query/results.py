from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from hodgecy.storage.errors import MaterializationLimitError, MissingCapabilityError


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

    def schema(self) -> dict[str, str]:
        return {field: field for field in self.projected_fields}

    def estimated_count(self) -> int | None:
        return self.estimated_rows

    def count(self) -> int:
        dataset = self.dataset_factory()
        return int(dataset.count_rows(filter=self.predicate))

    def iter_batches(self, *, batch_size: int = 65_536) -> Iterable[Any]:
        dataset = self.dataset_factory()
        scanner = dataset.scanner(columns=list(self.projected_fields), filter=self.predicate, batch_size=batch_size)
        yield from scanner.to_batches()

    def take(self, n: int) -> Any:
        if n < 0:
            raise MaterializationLimitError("take(n) requires n >= 0")
        if n > self.row_limit:
            raise MaterializationLimitError(f"Requested {n} rows exceeds materialization limit {self.row_limit}")
        scanner = self.dataset_factory().scanner(columns=list(self.projected_fields), filter=self.predicate, batch_size=max(1, min(n or 1, 65_536)))
        return scanner.head(n)

    def head(self, n: int = 5) -> Any:
        return self.take(n)

    def to_arrow(self, *, allow_over_limit: bool = False) -> Any:
        count = self.count()
        requested = self.query_spec.limit_value if self.query_spec.limit_value is not None else count
        if requested > self.row_limit and not allow_over_limit:
            raise MaterializationLimitError(f"Query would materialize {requested} rows; limit is {self.row_limit}")
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

    def __iter__(self) -> Iterable[Any]:
        raise MaterializationLimitError("Iterating a LazyResultSet directly is disabled; use iter_batches(), head(), or take(n)")
