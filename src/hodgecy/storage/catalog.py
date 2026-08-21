from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
from typing import Any, Iterable

from hodgecy.config import HodgeCYDataRoot, open_data_root
from hodgecy.core.dataset import DatasetDescriptor
from hodgecy.core.serialization import canonical_json

from .backends import DuckDBCatalogBackend, JsonCatalogBackend
from .errors import CatalogVersionError, StorageError
from .manifests import descriptor_from_manifest_record, instance_from_manifest_record, read_dataset_manifest, source_refs_from_manifest_record
from .models import (
    CATALOG_SCHEMA_VERSION,
    CatalogMetadata,
    ColumnarSourceRef,
    CorpusSnapshot,
    DatasetInstance,
    PhysicalSourceRef,
    RegisteredTable,
    SourceFormat,
    TableKind,
    empty_catalog_payload,
    payload_from_dict,
    utc_now_iso,
)
from .parquet import ParquetInspection, inspect_parquet_source


class HodgeCYCatalog:
    """Local metadata catalog backed by deterministic JSON state.

    DuckDB is exposed as an optional backend capability. The JSON catalog is the
    portable bootstrap state used by fixture tests and manifest rebuilds.
    """

    def __init__(self, path: Path, *, data_root: HodgeCYDataRoot | None = None, read_only: bool = False, backend: str = "json") -> None:
        self.path = path.expanduser().resolve()
        self.data_root = data_root
        self.read_only = read_only
        self.backend = backend
        self._payload: dict[str, Any] | None = None
        self._backend_context: JsonCatalogBackend | DuckDBCatalogBackend | None = None

    @classmethod
    def create(cls, *, data_root: str | Path | HodgeCYDataRoot, name: str = "hodgecy_catalog", hodgecy_version: str | None = None, hodgecy_commit: str | None = None, backend: str = "json") -> "HodgeCYCatalog":
        root = data_root if isinstance(data_root, HodgeCYDataRoot) else HodgeCYDataRoot(Path(data_root))
        catalog_dir = root.catalogs / name
        catalog_dir.mkdir(parents=True, exist_ok=True)
        path = catalog_dir / "catalog.json"
        metadata = CatalogMetadata(
            hodgecy_version=hodgecy_version,
            hodgecy_commit=hodgecy_commit,
            data_root=root.root.as_posix(),
            backend=backend,
            backend_version=_backend_version(backend),
        )
        catalog = cls(path, data_root=root, read_only=False, backend=backend)
        if not path.exists():
            catalog._payload = empty_catalog_payload(metadata)
            catalog._write()
        return catalog._open()

    @classmethod
    def from_path(cls, path: str | Path, *, data_root: str | Path | HodgeCYDataRoot | None = None, read_only: bool = False, backend: str = "json") -> "HodgeCYCatalog":
        root = None if data_root is None else (data_root if isinstance(data_root, HodgeCYDataRoot) else HodgeCYDataRoot(Path(data_root)))
        return cls(Path(path), data_root=root, read_only=read_only, backend=backend)._open()

    def _open(self) -> "HodgeCYCatalog":
        if self.backend == "duckdb":
            self._backend_context = DuckDBCatalogBackend(self.path.with_suffix(".duckdb"), read_only=self.read_only).__enter__()
        else:
            self._backend_context = JsonCatalogBackend(self.path, read_only=self.read_only).__enter__()
        if not self.path.exists():
            if self.read_only:
                raise StorageError(f"Catalog does not exist: {self.path}")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._payload = empty_catalog_payload(CatalogMetadata(data_root=None if self.data_root is None else self.data_root.root.as_posix(), backend=self.backend, backend_version=_backend_version(self.backend)))
            self._write()
        self._payload = payload_from_dict(json.loads(self.path.read_text(encoding="utf-8")))
        self._check_schema_version()
        return self

    def close(self) -> None:
        if self._backend_context is not None:
            self._backend_context.close()
            self._backend_context = None

    def __enter__(self) -> "HodgeCYCatalog":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    @property
    def payload(self) -> dict[str, Any]:
        if self._payload is None:
            raise StorageError("Catalog is not open")
        return self._payload

    @property
    def metadata(self) -> CatalogMetadata:
        return CatalogMetadata.from_dict(self.payload["metadata"])

    def _check_schema_version(self) -> None:
        current = self.metadata.catalog_schema_version.value
        if current != CATALOG_SCHEMA_VERSION:
            raise CatalogVersionError(f"Unsupported catalog schema version {current}; expected {CATALOG_SCHEMA_VERSION}")

    def _touch(self) -> None:
        metadata = self.metadata
        self.payload["metadata"] = CatalogMetadata(
            catalog_schema_version=metadata.catalog_schema_version,
            created_at=metadata.created_at,
            last_updated=utc_now_iso(),
            hodgecy_version=metadata.hodgecy_version,
            hodgecy_commit=metadata.hodgecy_commit,
            data_root=metadata.data_root,
            backend=metadata.backend,
            backend_version=metadata.backend_version,
        ).to_dict()

    def _write(self) -> None:
        if self.read_only:
            raise StorageError("Catalog is read-only")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(canonical_json(self.payload) + "\n", encoding="utf-8")

    def _upsert(self, section: str, key: str, value: dict[str, Any]) -> None:
        existing = self.payload[section].get(key)
        if existing == value:
            return
        if existing is not None and existing != value:
            raise StorageError(f"Conflicting registration for {section}.{key}")
        self.payload[section][key] = value
        self._touch()
        self._write()

    def register_dataset(self, descriptor: DatasetDescriptor) -> DatasetDescriptor:
        self._upsert("datasets", descriptor.dataset_id.serialize(), descriptor.to_dict())
        return descriptor

    def register_instance(self, instance: DatasetInstance) -> DatasetInstance:
        if instance.dataset_id.serialize() not in self.payload["datasets"]:
            raise StorageError(f"Dataset must be registered before instance: {instance.dataset_id}")
        self._upsert("instances", instance.instance_id, instance.to_dict())
        return instance

    def register_physical_source(self, source: PhysicalSourceRef) -> PhysicalSourceRef:
        if source.instance_id not in self.payload["instances"]:
            raise StorageError(f"Dataset instance must be registered before source: {source.instance_id}")
        self._upsert("physical_sources", source.source_id, source.to_dict())
        return source

    def register_columnar_source(self, source: ColumnarSourceRef) -> ColumnarSourceRef:
        if source.instance_id not in self.payload["instances"]:
            raise StorageError(f"Dataset instance must be registered before columnar source: {source.instance_id}")
        for source_id in source.source_ids:
            if source_id not in self.payload["physical_sources"]:
                raise StorageError(f"Physical source must be registered before columnar source: {source_id}")
        self._upsert("columnar_sources", source.columnar_id, source.to_dict())
        if source.table_name not in {row["table_name"] for row in self.payload["tables"].values()}:
            metadata = dict(source.metadata)
            table_kind = TableKind(metadata.pop("table_kind", TableKind.SOURCE.value))
            parent_key = metadata.pop("parent_key", None)
            child_key = metadata.pop("child_key", None)
            self.register_table(RegisteredTable(
                table_id=source.table_name,
                table_name=source.table_name,
                table_kind=table_kind,
                instance_id=source.instance_id,
                columnar_id=source.columnar_id,
                row_count=source.row_count,
                columns=tuple(source.schema.keys()),
                parent_key=parent_key,
                child_key=child_key,
                metadata=metadata,
            ))
        return source

    def register_parquet_source(self, *, columnar_id: str, instance_id: str, source_id: str, relative_path: str, table_name: str, common_field_mapping: dict[str, str] | None = None, heavy_columns: Iterable[str] = (), query_safe_columns: Iterable[str] = (), table_kind: TableKind = TableKind.SOURCE, metadata: dict[str, Any] | None = None, parent_key: str | None = None, child_key: str | None = None) -> ColumnarSourceRef:
        return self.register_parquet_sources(
            columnar_id=columnar_id,
            instance_id=instance_id,
            source_ids=(source_id,),
            relative_paths=(relative_path,),
            table_name=table_name,
            common_field_mapping=common_field_mapping,
            heavy_columns=heavy_columns,
            query_safe_columns=query_safe_columns,
            table_kind=table_kind,
            metadata=metadata,
            parent_key=parent_key,
            child_key=child_key,
        )

    def register_parquet_sources(self, *, columnar_id: str, instance_id: str, source_ids: Iterable[str], relative_paths: Iterable[str], table_name: str, common_field_mapping: dict[str, str] | None = None, heavy_columns: Iterable[str] = (), query_safe_columns: Iterable[str] = (), table_kind: TableKind = TableKind.SOURCE, metadata: dict[str, Any] | None = None, parent_key: str | None = None, child_key: str | None = None, source_revision: str | None = None, field_metadata: dict[str, Any] | None = None) -> ColumnarSourceRef:
        if self.data_root is None:
            raise StorageError("register_parquet_sources requires a configured data_root")
        relative_tuple = tuple(relative_paths)
        source_id_tuple = tuple(source_ids)
        if len(relative_tuple) != len(source_id_tuple):
            raise StorageError("source_ids and relative_paths must have the same length")
        inspection = inspect_parquet_source((self.data_root.root / path for path in relative_tuple), data_root=self.data_root.root, source_revision=source_revision)
        physical_ids: list[str] = []
        for index, (source_id, relative_path) in enumerate(zip(source_id_tuple, relative_tuple)):
            file_info = inspection.files[index]
            physical = self.register_physical_source(PhysicalSourceRef(
                source_id=source_id,
                instance_id=instance_id,
                relative_path=relative_path,
                byte_size=file_info.byte_size,
                source_format=SourceFormat.PARQUET,
                partition=str(index),
                metadata={
                    "parquet_row_count": file_info.row_count,
                    "parquet_row_group_count": file_info.row_group_count,
                    "source_revision": source_revision,
                },
            ))
            physical_ids.append(physical.source_id)
        heavy_tuple = tuple(heavy_columns)
        return self.register_columnar_source(ColumnarSourceRef(
            columnar_id=columnar_id,
            instance_id=instance_id,
            source_ids=tuple(physical_ids),
            table_name=table_name,
            schema=inspection.schema,
            row_count=inspection.row_count,
            partition_metadata=_partition_metadata_from_inspection(inspection),
            common_field_mapping=common_field_mapping or {},
            heavy_columns=heavy_tuple,
            query_safe_columns=tuple(query_safe_columns) or tuple(field for field in inspection.schema.keys() if field not in heavy_tuple),
            metadata={
                **(metadata or {}),
                "table_kind": table_kind.value,
                "parent_key": parent_key,
                "child_key": child_key,
                "field_metadata": field_metadata or {},
            },
        ))
    def register_table(self, table: RegisteredTable) -> RegisteredTable:
        self._upsert("tables", table.table_id, table.to_dict())
        return table

    def create_snapshot(self, snapshot_id: str, *, hodgecy_version: str | None = None, hodgecy_commit: str | None = None, metadata: dict[str, Any] | None = None) -> CorpusSnapshot:
        instances = tuple(sorted(self.payload["instances"].keys()))
        source_checksums = {key: value.get("sha256") for key, value in sorted(self.payload["physical_sources"].items())}
        schema_versions = {key: value.get("schema_version", {}).get("value", "v1") for key, value in sorted(self.payload["instances"].items())}
        snapshot = CorpusSnapshot(
            snapshot_id=snapshot_id,
            created_at=utc_now_iso(),
            hodgecy_version=hodgecy_version or self.metadata.hodgecy_version,
            hodgecy_commit=hodgecy_commit or self.metadata.hodgecy_commit,
            catalog_schema_version=self.metadata.catalog_schema_version,
            dataset_instances=instances,
            source_checksums=source_checksums,
            normalized_schema_versions=schema_versions,
            metadata=metadata or {},
        )
        self._upsert("snapshots", snapshot.snapshot_id, snapshot.to_dict())
        return snapshot

    def bootstrap_manifest(self, path: str | Path) -> list[DatasetDescriptor]:
        descriptors: list[DatasetDescriptor] = []
        for record in read_dataset_manifest(path):
            descriptor = self.register_dataset(descriptor_from_manifest_record(record))
            instance = self.register_instance(instance_from_manifest_record(record, descriptor))
            for source in source_refs_from_manifest_record(record, instance):
                self.register_physical_source(source)
            descriptors.append(descriptor)
        return descriptors

    def list_datasets(self) -> list[DatasetDescriptor]:
        return [DatasetDescriptor.from_dict(value) for value in self.payload["datasets"].values()]

    def list_instances(self, dataset_id: str | None = None) -> list[DatasetInstance]:
        instances = [DatasetInstance.from_dict(value) for value in self.payload["instances"].values()]
        if dataset_id is not None:
            instances = [instance for instance in instances if instance.dataset_id.local_id == dataset_id or instance.dataset_id.serialize() == dataset_id]
        return instances

    def list_physical_sources(self, instance_id: str | None = None) -> list[PhysicalSourceRef]:
        sources = [PhysicalSourceRef.from_dict(value) for value in self.payload["physical_sources"].values()]
        return [source for source in sources if instance_id is None or source.instance_id == instance_id]

    def list_columnar_sources(self, instance_id: str | None = None) -> list[ColumnarSourceRef]:
        sources = [ColumnarSourceRef.from_dict(value) for value in self.payload["columnar_sources"].values()]
        return [source for source in sources if instance_id is None or source.instance_id == instance_id]

    def list_tables(self, table_kind: TableKind | None = None) -> list[RegisteredTable]:
        tables = [RegisteredTable.from_dict(value) for value in self.payload["tables"].values()]
        return [table for table in tables if table_kind is None or table.table_kind is table_kind]

    def dataset_status(self, dataset_id: str) -> dict[str, Any]:
        descriptors = [descriptor for descriptor in self.list_datasets() if descriptor.dataset_id.local_id == dataset_id or descriptor.dataset_id.serialize() == dataset_id]
        if not descriptors:
            raise StorageError(f"Unknown dataset: {dataset_id}")
        instances = self.list_instances(descriptors[0].dataset_id.local_id)
        return {
            "dataset_id": descriptors[0].dataset_id.serialize(),
            "name": descriptors[0].name,
            "construction_family": descriptors[0].construction_family.name,
            "logical_acquisition_status": descriptors[0].acquisition_status.value,
            "installed": bool(instances),
            "instances": [instance.to_dict() for instance in instances],
        }

    def describe_dataset(self, dataset_id: str) -> dict[str, Any]:
        status = self.dataset_status(dataset_id)
        instance_ids = [instance["instance_id"] for instance in status["instances"]]
        return {
            **status,
            "physical_sources": [source.to_dict() for source in self.list_physical_sources() if source.instance_id in instance_ids],
            "columnar_sources": [source.to_dict() for source in self.list_columnar_sources() if source.instance_id in instance_ids],
            "tables": [table.to_dict() for table in self.list_tables() if table.instance_id in instance_ids],
        }

    def query(self, spec: object) -> object:
        from hodgecy.query.engine import CatalogQueryEngine
        return CatalogQueryEngine(self).execute(spec)


def open_catalog(root: str | Path | HodgeCYDataRoot | None = None, *, name: str = "hodgecy_catalog", create: bool = False, read_only: bool = False, backend: str = "json") -> HodgeCYCatalog:
    data_root = root if isinstance(root, HodgeCYDataRoot) else open_data_root(root)
    path = data_root.catalogs / name / "catalog.json"
    if create:
        return HodgeCYCatalog.create(data_root=data_root, name=name, backend=backend)
    return HodgeCYCatalog.from_path(path, data_root=data_root, read_only=read_only, backend=backend)


def _partition_metadata_from_inspection(inspection: ParquetInspection) -> dict[str, Any]:
    return {
        "schema_version": "partition_metadata.v1",
        "file_count": len(inspection.files),
        "row_group_count": inspection.row_group_count,
        "row_count": inspection.row_count,
        "byte_size": inspection.byte_size,
        "source_revision": inspection.source_revision,
        "files": [
            {
                "relative_path": item.relative_path,
                "row_count": item.row_count,
                "row_group_count": item.row_group_count,
                "byte_size": item.byte_size,
                "row_groups": [row_group.to_dict() for row_group in item.row_groups],
            }
            for item in inspection.files
        ],
    }
def _backend_version(backend: str) -> str | None:
    if backend == "json":
        return "1"
    try:
        return importlib.metadata.version(backend)
    except importlib.metadata.PackageNotFoundError:
        return None
