from __future__ import annotations

import importlib.metadata
from pathlib import Path
from typing import Any

from .errors import MissingCapabilityError


class CatalogBackend:
    """Small context-managed catalog backend contract."""

    backend_name = "abstract"

    def __enter__(self) -> "CatalogBackend":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def close(self) -> None:
        return None

    def backend_version(self) -> str | None:
        return None


class JsonCatalogBackend(CatalogBackend):
    backend_name = "json"

    def __init__(self, path: Path, *, read_only: bool = False) -> None:
        self.path = path
        self.read_only = read_only


class DuckDBCatalogBackend(CatalogBackend):
    """Optional DuckDB backend wrapper, imported only when opened."""

    backend_name = "duckdb"

    def __init__(self, path: Path, *, read_only: bool = False) -> None:
        self.path = path
        self.read_only = read_only
        self._connection: Any | None = None

    def __enter__(self) -> "DuckDBCatalogBackend":
        try:
            import duckdb  # type: ignore[import-not-found]
        except ModuleNotFoundError as exc:
            raise MissingCapabilityError("DuckDB backend requested but duckdb is not installed; install hodgecy[storage]") from exc
        self._connection = duckdb.connect(str(self.path), read_only=self.read_only)
        return self

    @property
    def connection(self) -> Any:
        if self._connection is None:
            raise MissingCapabilityError("DuckDB backend is not open")
        return self._connection

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def backend_version(self) -> str | None:
        try:
            return importlib.metadata.version("duckdb")
        except importlib.metadata.PackageNotFoundError:
            return None
