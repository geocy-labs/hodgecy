from __future__ import annotations

from pathlib import Path
from typing import Any

from hodgecy.core.errors import ValidationError
from hodgecy.storage.errors import MissingCapabilityError, StorageError
from hodgecy.storage.models import ColumnarSourceRef
from hodgecy.storage.planning import EstimateKind, QueryEstimate, QueryPlanSummary

from .fields import FieldRegistry
from .results import LazyResultSet
from .spec import QuerySpec


class CatalogQueryEngine:
    def __init__(self, catalog: Any) -> None:
        self.catalog = catalog

    def execute(self, spec: QuerySpec | object) -> LazyResultSet:
        if not isinstance(spec, QuerySpec):
            raise ValidationError("catalog.query expects a QuerySpec")
        source = self._resolve_source(spec)
        if self.catalog.data_root is None:
            raise StorageError("Query execution requires a catalog with data_root")
        physical_sources = [self.catalog.payload["physical_sources"][source_id] for source_id in source.source_ids]
        relative_paths = tuple(row["relative_path"] for row in physical_sources if row.get("relative_path"))
        paths = tuple((self.catalog.data_root.root / relative_path).as_posix() for relative_path in relative_paths)
        if not paths:
            raise StorageError("Columnar query source has no local relative paths")
        field_metadata = dict(source.metadata.get("field_metadata") or {})
        registry = FieldRegistry.from_schema(
            source.schema.keys(),
            semantic_mapping=source.common_field_mapping,
            heavy_fields=source.heavy_columns,
            field_metadata=field_metadata,
        )
        requested = list(spec.fields or tuple(field for field in source.query_safe_columns if field not in source.heavy_columns) or tuple(source.schema.keys()))
        requested.extend(order.field for order in spec.order_by_fields)
        requested.extend(spec.group_by_fields)
        requested.extend(aggregation.field for aggregation in spec.aggregations if aggregation.field is not None)
        projected = tuple(registry.projection(requested, include_heavy=spec.include_heavy))
        predicate = None if spec.predicate is None else spec.predicate.compile_arrow(registry)
        row_limit = spec.materialization_policy.row_limit
        plan = _plan_summary(
            source=source,
            projected=projected,
            heavy_fields=registry.heavy_fields,
            predicate_present=spec.predicate is not None,
            relative_paths=relative_paths,
        )
        return LazyResultSet(
            query_spec=spec,
            registry=registry,
            dataset_factory=lambda: _open_dataset(paths),
            paths=paths,
            projected_fields=projected,
            predicate=predicate,
            estimated_rows=source.row_count,
            row_limit=row_limit,
            provenance={
                "query_id": spec.stable_id(),
                "columnar_id": source.columnar_id,
                "source_relative_paths": list(relative_paths),
                "backend": "pyarrow.dataset",
            },
            plan=plan,
        )

    def _resolve_source(self, spec: QuerySpec) -> ColumnarSourceRef:
        sources = self.catalog.list_columnar_sources()
        if spec.table is not None:
            for source in sources:
                if source.table_name == spec.table or source.columnar_id == spec.table:
                    return source
            raise StorageError(f"Unknown query table: {spec.table}")
        if spec.datasets:
            instances = []
            for dataset_id in spec.datasets:
                instances.extend(self.catalog.list_instances(dataset_id))
            instance_ids = {instance.instance_id for instance in instances}
            matching = [source for source in sources if source.instance_id in instance_ids]
            if len(matching) == 1:
                return matching[0]
            if not matching:
                raise StorageError(f"No columnar source registered for datasets: {spec.datasets}")
            raise StorageError("Cross-dataset query planning is represented but requires an explicit table in Blob 4")
        if len(sources) == 1:
            return sources[0]
        raise StorageError("QuerySpec must name a dataset or table when multiple columnar sources are registered")


def _open_dataset(paths: tuple[str, ...]) -> Any:
    try:
        import pyarrow.dataset as ds  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise MissingCapabilityError("PyArrow is required for query execution; install hodgecy[storage]") from exc
    return ds.dataset([Path(path) for path in paths], format="parquet")


def _plan_summary(
    *,
    source: ColumnarSourceRef,
    projected: tuple[str, ...],
    heavy_fields: tuple[str, ...],
    predicate_present: bool,
    relative_paths: tuple[str, ...],
) -> QueryPlanSummary:
    partition = source.partition_metadata or {}
    file_count = partition.get("file_count")
    row_group_count = partition.get("row_group_count")
    projected_heavy = tuple(field for field in projected if field in heavy_fields)
    row_kind = EstimateKind.ESTIMATED if predicate_present and source.row_count is not None else (EstimateKind.KNOWN if source.row_count is not None else EstimateKind.UNKNOWN)
    estimated_rows = QueryEstimate(row_kind, rows=source.row_count, reason="source row count; predicates may reduce it" if predicate_present else "registered source row count")
    estimated_bytes = _estimate_projected_bytes(source, projected)
    notes = ["Arrow scanner receives projected columns and compiled predicate lazily"]
    if projected_heavy:
        notes.append("heavy columns requested explicitly")
    return QueryPlanSummary(
        backend="pyarrow.dataset",
        projected_columns=projected,
        heavy_columns=projected_heavy,
        predicate_pushdown=predicate_present,
        partition_count=file_count,
        row_group_count=row_group_count,
        estimated_rows=estimated_rows,
        estimated_bytes=estimated_bytes,
        full_scan_likely=not predicate_present,
        source_relative_paths=relative_paths,
        notes=tuple(notes),
    )


def _estimate_projected_bytes(source: ColumnarSourceRef, projected: tuple[str, ...]) -> QueryEstimate:
    total_bytes = source.partition_metadata.get("byte_size")
    if not total_bytes or not source.schema:
        return QueryEstimate(EstimateKind.UNKNOWN, reason="source byte size or schema unavailable")
    weight_map = source.metadata.get("column_weight_bytes") or {}
    if weight_map:
        projected_weight = sum(int(weight_map.get(field, 1)) for field in projected)
        total_weight = sum(int(weight_map.get(field, 1)) for field in source.schema)
    else:
        projected_weight = len(projected)
        total_weight = len(source.schema)
    if total_weight <= 0:
        return QueryEstimate(EstimateKind.UNKNOWN, reason="column weights unavailable")
    return QueryEstimate(
        EstimateKind.ESTIMATED,
        bytes=max(1, int(int(total_bytes) * projected_weight / total_weight)),
        reason="proportional projection estimate from registered Parquet byte size",
    )
