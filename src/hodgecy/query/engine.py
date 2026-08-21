from __future__ import annotations

from pathlib import Path
from typing import Any

from hodgecy.core.errors import ValidationError
from hodgecy.storage.errors import MissingCapabilityError, StorageError
from hodgecy.storage.models import ColumnarSourceRef

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
        paths = tuple((self.catalog.data_root.root / row["relative_path"]).as_posix() for row in physical_sources if row.get("relative_path"))
        if not paths:
            raise StorageError("Columnar query source has no local relative paths")
        registry = FieldRegistry.from_schema(source.schema.keys(), semantic_mapping=source.common_field_mapping, heavy_fields=source.heavy_columns)
        requested = list(spec.fields or tuple(field for field in source.query_safe_columns if field not in source.heavy_columns) or tuple(source.schema.keys()))
        requested.extend(order.field for order in spec.order_by_fields)
        requested.extend(spec.group_by_fields)
        requested.extend(aggregation.field for aggregation in spec.aggregations if aggregation.field is not None)
        projected = tuple(registry.projection(requested, include_heavy=spec.include_heavy))
        predicate = None if spec.predicate is None else spec.predicate.compile_arrow(registry)
        return LazyResultSet(
            query_spec=spec,
            registry=registry,
            dataset_factory=lambda: _open_dataset(paths),
            paths=paths,
            projected_fields=projected,
            predicate=predicate,
            estimated_rows=source.row_count,
            row_limit=spec.materialization_policy.row_limit,
            provenance={"query_id": spec.stable_id(), "columnar_id": source.columnar_id, "paths": list(paths), "backend": "pyarrow.dataset"},
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
