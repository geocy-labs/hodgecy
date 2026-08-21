from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .errors import MissingCapabilityError


@dataclass(frozen=True, slots=True)
class ParquetInspection:
    paths: tuple[Path, ...]
    schema: dict[str, str]
    row_count: int
    byte_size: int

    def to_dict(self) -> dict[str, object]:
        return {
            "paths": [path.as_posix() for path in self.paths],
            "schema": self.schema,
            "row_count": self.row_count,
            "byte_size": self.byte_size,
        }


def inspect_parquet_source(paths: Iterable[str | Path]) -> ParquetInspection:
    try:
        import pyarrow.parquet as pq  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise MissingCapabilityError("PyArrow is required for Parquet registration/query; install hodgecy[storage]") from exc
    resolved = tuple(Path(path).expanduser().resolve() for path in paths)
    if not resolved:
        raise MissingCapabilityError("At least one Parquet path is required")
    schema: dict[str, str] | None = None
    row_count = 0
    byte_size = 0
    for path in resolved:
        metadata = pq.read_metadata(path)
        row_count += int(metadata.num_rows)
        byte_size += path.stat().st_size
        current_schema = {field.name: str(field.type) for field in metadata.schema.to_arrow_schema()}
        if schema is None:
            schema = current_schema
        elif schema != current_schema:
            raise MissingCapabilityError("Mixed Parquet schemas are not supported by this Blob 4 registration helper")
    return ParquetInspection(resolved, schema or {}, row_count, byte_size)
