from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import PurePosixPath
from typing import Any

from hodgecy.core.ids import HodgeCYID, IdentityKind
from hodgecy.core.status import AcquisitionStatus, RedistributionStatus
from hodgecy.core.versions import SchemaVersion
from hodgecy.core.errors import ValidationError

CATALOG_SCHEMA_VERSION = "v1"
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._=-]*$")
_TABLE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_token(name: str, value: str) -> None:
    if not _TOKEN_RE.fullmatch(value):
        raise ValidationError(f"Invalid {name}: {value!r}")


def validate_table_name(value: str) -> None:
    if not _TABLE_RE.fullmatch(value):
        raise ValidationError(f"Invalid table name: {value!r}")


def normalize_relative_path(value: str) -> str:
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or str(path) in {"", "."}:
        raise ValidationError(f"Path must be a safe data-root-relative path: {value!r}")
    return path.as_posix()


class SourceFormat(str, Enum):
    PARQUET = "parquet"
    JSON = "json"
    JSONL = "jsonl"
    TSV = "tsv"
    CSV = "csv"
    ZIP = "zip"
    NATIVE = "native"
    REMOTE = "remote"


class TableKind(str, Enum):
    SOURCE = "source"
    NORMALIZED = "normalized"
    DERIVED = "derived"
    RELATIONSHIP = "relationship"
    FIBRATION = "fibration"


@dataclass(frozen=True, slots=True)
class CatalogMetadata:
    catalog_schema_version: SchemaVersion = SchemaVersion(CATALOG_SCHEMA_VERSION)
    created_at: str = field(default_factory=utc_now_iso)
    last_updated: str = field(default_factory=utc_now_iso)
    hodgecy_version: str | None = None
    hodgecy_commit: str | None = None
    data_root: str | None = None
    backend: str = "json"
    backend_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "catalog_schema_version": self.catalog_schema_version.to_dict(),
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "hodgecy_version": self.hodgecy_version,
            "hodgecy_commit": self.hodgecy_commit,
            "data_root": self.data_root,
            "backend": self.backend,
            "backend_version": self.backend_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CatalogMetadata":
        return cls(
            catalog_schema_version=SchemaVersion.from_dict(payload.get("catalog_schema_version", {"value": CATALOG_SCHEMA_VERSION})),
            created_at=str(payload.get("created_at") or utc_now_iso()),
            last_updated=str(payload.get("last_updated") or utc_now_iso()),
            hodgecy_version=payload.get("hodgecy_version"),
            hodgecy_commit=payload.get("hodgecy_commit"),
            data_root=payload.get("data_root"),
            backend=str(payload.get("backend") or "json"),
            backend_version=payload.get("backend_version"),
        )


@dataclass(frozen=True, slots=True)
class DatasetInstance:
    instance_id: str
    dataset_id: HodgeCYID
    source_version: str | None
    acquisition_status: AcquisitionStatus
    redistribution_status: RedistributionStatus
    installed_at: str = field(default_factory=utc_now_iso)
    record_count: int | None = None
    schema_version: SchemaVersion = SchemaVersion()
    source_revision: str | None = None
    adapter_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_token("instance_id", self.instance_id)
        self.dataset_id.require_kind(IdentityKind.DATASET)
        if self.record_count is not None and self.record_count < 0:
            raise ValidationError("record_count must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "dataset_id": self.dataset_id.to_dict(),
            "source_version": self.source_version,
            "acquisition_status": self.acquisition_status.value,
            "redistribution_status": self.redistribution_status.value,
            "installed_at": self.installed_at,
            "record_count": self.record_count,
            "schema_version": self.schema_version.to_dict(),
            "source_revision": self.source_revision,
            "adapter_name": self.adapter_name,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DatasetInstance":
        return cls(
            instance_id=str(payload["instance_id"]),
            dataset_id=HodgeCYID.from_dict(payload["dataset_id"]),
            source_version=payload.get("source_version"),
            acquisition_status=AcquisitionStatus(payload["acquisition_status"]),
            redistribution_status=RedistributionStatus(payload["redistribution_status"]),
            installed_at=str(payload.get("installed_at") or utc_now_iso()),
            record_count=payload.get("record_count"),
            schema_version=SchemaVersion.from_dict(payload.get("schema_version", {"value": "v1"})),
            source_revision=payload.get("source_revision"),
            adapter_name=payload.get("adapter_name"),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class PhysicalSourceRef:
    source_id: str
    instance_id: str
    relative_path: str | None = None
    uri: str | None = None
    sha256: str | None = None
    byte_size: int | None = None
    source_format: SourceFormat = SourceFormat.NATIVE
    partition: str | None = None
    archive_member: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_token("source_id", self.source_id)
        _validate_token("instance_id", self.instance_id)
        if self.relative_path is not None:
            object.__setattr__(self, "relative_path", normalize_relative_path(self.relative_path))
        if self.byte_size is not None and self.byte_size < 0:
            raise ValidationError("byte_size must be non-negative")
        if self.relative_path is None and self.uri is None:
            raise ValidationError("PhysicalSourceRef requires a relative_path or uri")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "instance_id": self.instance_id,
            "relative_path": self.relative_path,
            "uri": self.uri,
            "sha256": self.sha256,
            "byte_size": self.byte_size,
            "source_format": self.source_format.value,
            "partition": self.partition,
            "archive_member": self.archive_member,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PhysicalSourceRef":
        return cls(
            source_id=str(payload["source_id"]),
            instance_id=str(payload["instance_id"]),
            relative_path=payload.get("relative_path"),
            uri=payload.get("uri"),
            sha256=payload.get("sha256"),
            byte_size=payload.get("byte_size"),
            source_format=SourceFormat(payload.get("source_format") or SourceFormat.NATIVE.value),
            partition=payload.get("partition"),
            archive_member=payload.get("archive_member"),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class ColumnarSourceRef:
    columnar_id: str
    instance_id: str
    source_ids: tuple[str, ...]
    table_name: str
    schema: dict[str, str]
    row_count: int | None = None
    partition_metadata: dict[str, Any] = field(default_factory=dict)
    common_field_mapping: dict[str, str] = field(default_factory=dict)
    heavy_columns: tuple[str, ...] = ()
    query_safe_columns: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_token("columnar_id", self.columnar_id)
        _validate_token("instance_id", self.instance_id)
        validate_table_name(self.table_name)
        for source_id in self.source_ids:
            _validate_token("source_id", source_id)
        if self.row_count is not None and self.row_count < 0:
            raise ValidationError("row_count must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "columnar_id": self.columnar_id,
            "instance_id": self.instance_id,
            "source_ids": list(self.source_ids),
            "table_name": self.table_name,
            "schema": self.schema,
            "row_count": self.row_count,
            "partition_metadata": self.partition_metadata,
            "common_field_mapping": self.common_field_mapping,
            "heavy_columns": list(self.heavy_columns),
            "query_safe_columns": list(self.query_safe_columns),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ColumnarSourceRef":
        return cls(
            columnar_id=str(payload["columnar_id"]),
            instance_id=str(payload["instance_id"]),
            source_ids=tuple(payload.get("source_ids") or ()),
            table_name=str(payload["table_name"]),
            schema=dict(payload.get("schema") or {}),
            row_count=payload.get("row_count"),
            partition_metadata=dict(payload.get("partition_metadata") or {}),
            common_field_mapping=dict(payload.get("common_field_mapping") or {}),
            heavy_columns=tuple(payload.get("heavy_columns") or ()),
            query_safe_columns=tuple(payload.get("query_safe_columns") or ()),
            metadata=dict(payload.get("metadata") or {}),
        )

@dataclass(frozen=True, slots=True)
class RegisteredTable:
    table_id: str
    table_name: str
    table_kind: TableKind
    instance_id: str | None = None
    columnar_id: str | None = None
    row_count: int | None = None
    columns: tuple[str, ...] = ()
    parent_key: str | None = None
    child_key: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_token("table_id", self.table_id)
        validate_table_name(self.table_name)
        if self.instance_id is not None:
            _validate_token("instance_id", self.instance_id)
        if self.columnar_id is not None:
            _validate_token("columnar_id", self.columnar_id)
        if self.row_count is not None and self.row_count < 0:
            raise ValidationError("row_count must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "table_id": self.table_id,
            "table_name": self.table_name,
            "table_kind": self.table_kind.value,
            "instance_id": self.instance_id,
            "columnar_id": self.columnar_id,
            "row_count": self.row_count,
            "columns": list(self.columns),
            "parent_key": self.parent_key,
            "child_key": self.child_key,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RegisteredTable":
        return cls(
            table_id=str(payload["table_id"]),
            table_name=str(payload["table_name"]),
            table_kind=TableKind(payload["table_kind"]),
            instance_id=payload.get("instance_id"),
            columnar_id=payload.get("columnar_id"),
            row_count=payload.get("row_count"),
            columns=tuple(payload.get("columns") or ()),
            parent_key=payload.get("parent_key"),
            child_key=payload.get("child_key"),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class CorpusSnapshot:
    snapshot_id: str
    created_at: str
    hodgecy_version: str | None
    hodgecy_commit: str | None
    catalog_schema_version: SchemaVersion
    dataset_instances: tuple[str, ...]
    source_checksums: dict[str, str | None]
    normalized_schema_versions: dict[str, str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_token("snapshot_id", self.snapshot_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "created_at": self.created_at,
            "hodgecy_version": self.hodgecy_version,
            "hodgecy_commit": self.hodgecy_commit,
            "catalog_schema_version": self.catalog_schema_version.to_dict(),
            "dataset_instances": list(self.dataset_instances),
            "source_checksums": self.source_checksums,
            "normalized_schema_versions": self.normalized_schema_versions,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CorpusSnapshot":
        return cls(
            snapshot_id=str(payload["snapshot_id"]),
            created_at=str(payload["created_at"]),
            hodgecy_version=payload.get("hodgecy_version"),
            hodgecy_commit=payload.get("hodgecy_commit"),
            catalog_schema_version=SchemaVersion.from_dict(payload["catalog_schema_version"]),
            dataset_instances=tuple(payload.get("dataset_instances") or ()),
            source_checksums=dict(payload.get("source_checksums") or {}),
            normalized_schema_versions=dict(payload.get("normalized_schema_versions") or {}),
            metadata=dict(payload.get("metadata") or {}),
        )


def empty_catalog_payload(metadata: CatalogMetadata) -> dict[str, Any]:
    return {
        "metadata": metadata.to_dict(),
        "datasets": {},
        "instances": {},
        "physical_sources": {},
        "columnar_sources": {},
        "tables": {},
        "snapshots": {},
    }


def payload_from_dict(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "metadata": CatalogMetadata.from_dict(payload.get("metadata") or {}).to_dict(),
        "datasets": dict(payload.get("datasets") or {}),
        "instances": dict(payload.get("instances") or {}),
        "physical_sources": dict(payload.get("physical_sources") or {}),
        "columnar_sources": dict(payload.get("columnar_sources") or {}),
        "tables": dict(payload.get("tables") or {}),
        "snapshots": dict(payload.get("snapshots") or {}),
    }
