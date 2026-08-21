from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from hodgecy.core.serialization import canonical_json, stable_sha256

from .errors import MissingCapabilityError, StorageError

PARQUET_METADATA_CACHE_SCHEMA = "parquet_metadata_cache.v1"


@dataclass(frozen=True, slots=True)
class ParquetRowGroupInspection:
    file_index: int
    row_group_index: int
    row_count: int
    total_byte_size: int | None = None
    column_statistics: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_index": self.file_index,
            "row_group_index": self.row_group_index,
            "row_count": self.row_count,
            "total_byte_size": self.total_byte_size,
            "column_statistics": self.column_statistics,
        }


@dataclass(frozen=True, slots=True)
class ParquetFileInspection:
    path: Path
    row_count: int
    row_group_count: int
    byte_size: int
    schema: dict[str, str]
    relative_path: str | None = None
    row_groups: tuple[ParquetRowGroupInspection, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path.as_posix(),
            "relative_path": self.relative_path,
            "row_count": self.row_count,
            "row_group_count": self.row_group_count,
            "byte_size": self.byte_size,
            "schema": self.schema,
            "row_groups": [row_group.to_dict() for row_group in self.row_groups],
        }


@dataclass(frozen=True, slots=True)
class ParquetInspection:
    paths: tuple[Path, ...]
    schema: dict[str, str]
    row_count: int
    byte_size: int
    files: tuple[ParquetFileInspection, ...] = ()
    source_revision: str | None = None

    @property
    def row_group_count(self) -> int:
        return sum(item.row_group_count for item in self.files)

    def to_dict(self) -> dict[str, object]:
        return {
            "paths": [path.as_posix() for path in self.paths],
            "schema": self.schema,
            "row_count": self.row_count,
            "byte_size": self.byte_size,
            "file_count": len(self.paths),
            "row_group_count": self.row_group_count,
            "source_revision": self.source_revision,
            "files": [item.to_dict() for item in self.files],
        }


def inspect_parquet_source(
    paths: Iterable[str | Path],
    *,
    data_root: str | Path | None = None,
    source_revision: str | None = None,
    include_column_statistics: bool = True,
) -> ParquetInspection:
    try:
        import pyarrow.parquet as pq  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise MissingCapabilityError("PyArrow is required for Parquet registration/query; install hodgecy[storage]") from exc
    root = None if data_root is None else Path(data_root).expanduser().resolve()
    resolved = tuple(Path(path).expanduser().resolve() for path in paths)
    if not resolved:
        raise MissingCapabilityError("At least one Parquet path is required")
    schema: dict[str, str] | None = None
    row_count = 0
    byte_size = 0
    files: list[ParquetFileInspection] = []
    for file_index, path in enumerate(resolved):
        metadata = pq.read_metadata(path)
        current_schema = {field.name: str(field.type) for field in metadata.schema.to_arrow_schema()}
        if schema is None:
            schema = current_schema
        elif schema != current_schema:
            raise MissingCapabilityError("Mixed Parquet schemas are not supported by this registration helper")
        stat = path.stat()
        file_rows = int(metadata.num_rows)
        file_bytes = int(stat.st_size)
        row_count += file_rows
        byte_size += file_bytes
        row_groups = tuple(
            _row_group_inspection(metadata.row_group(index), file_index=file_index, row_group_index=index, include_column_statistics=include_column_statistics)
            for index in range(metadata.num_row_groups)
        )
        files.append(ParquetFileInspection(
            path=path,
            relative_path=_relative_to_root(path, root),
            row_count=file_rows,
            row_group_count=int(metadata.num_row_groups),
            byte_size=file_bytes,
            schema=current_schema,
            row_groups=row_groups,
        ))
    return ParquetInspection(resolved, schema or {}, row_count, byte_size, tuple(files), source_revision=source_revision)


def build_parquet_metadata_cache(
    paths: Iterable[str | Path],
    cache_path: str | Path,
    *,
    data_root: str | Path | None = None,
    source_revision: str | None = None,
    source_checksum: str | None = None,
) -> dict[str, Any]:
    inspection = inspect_parquet_source(paths, data_root=data_root, source_revision=source_revision)
    path_tuple = tuple(Path(path).expanduser().resolve() for path in paths)
    payload = {
        "schema_version": PARQUET_METADATA_CACHE_SCHEMA,
        "builder_version": "blob11",
        "source_revision": source_revision,
        "source_checksum": source_checksum,
        "source_fingerprint": _source_fingerprint(path_tuple, source_revision=source_revision, source_checksum=source_checksum),
        "inspection": inspection.to_dict(),
    }
    target = Path(cache_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(canonical_json(payload) + "\n", encoding="utf-8")
    temporary.replace(target)
    return payload


def read_parquet_metadata_cache(
    cache_path: str | Path,
    paths: Iterable[str | Path],
    *,
    source_revision: str | None = None,
    source_checksum: str | None = None,
) -> dict[str, Any]:
    target = Path(cache_path)
    payload = json.loads(target.read_text(encoding="utf-8"))
    if payload.get("schema_version") != PARQUET_METADATA_CACHE_SCHEMA:
        raise StorageError("Unsupported Parquet metadata cache schema")
    path_tuple = tuple(Path(path).expanduser().resolve() for path in paths)
    expected = _source_fingerprint(path_tuple, source_revision=source_revision, source_checksum=source_checksum)
    if payload.get("source_revision") != source_revision or payload.get("source_checksum") != source_checksum or payload.get("source_fingerprint") != expected:
        raise StorageError("Parquet metadata cache is stale for this source instance")
    return payload


def _row_group_inspection(row_group: Any, *, file_index: int, row_group_index: int, include_column_statistics: bool) -> ParquetRowGroupInspection:
    stats: dict[str, dict[str, Any]] = {}
    if include_column_statistics:
        for column_index in range(row_group.num_columns):
            column = row_group.column(column_index)
            column_stats = column.statistics
            if column_stats is None:
                continue
            stats[column.path_in_schema] = {
                "min": _json_safe_stat(column_stats.min),
                "max": _json_safe_stat(column_stats.max),
                "null_count": column_stats.null_count,
                "has_min_max": column_stats.has_min_max,
            }
    return ParquetRowGroupInspection(
        file_index=file_index,
        row_group_index=row_group_index,
        row_count=int(row_group.num_rows),
        total_byte_size=getattr(row_group, "total_byte_size", None),
        column_statistics=stats,
    )


def _relative_to_root(path: Path, root: Path | None) -> str | None:
    if root is None:
        return None
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return None


def _json_safe_stat(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.hex()
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def _source_fingerprint(paths: tuple[Path, ...], *, source_revision: str | None, source_checksum: str | None) -> str:
    files = []
    for path in paths:
        stat = path.stat()
        files.append({"path": path.name, "size": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    return stable_sha256({"files": files, "source_revision": source_revision, "source_checksum": source_checksum})
