from __future__ import annotations

from hodgecy.core.errors import ConfigurationError, HodgeCYError, ValidationError


class StorageError(HodgeCYError):
    """Base class for storage and catalog failures."""


class CatalogVersionError(StorageError):
    """Raised when a catalog schema version cannot be opened safely."""


class MissingCapabilityError(StorageError):
    """Raised when an optional backend is requested but unavailable."""


class MaterializationLimitError(StorageError):
    """Raised when a query result would exceed configured materialization limits."""


class ResultStoreError(StorageError):
    """Base class for persistent mathematical result registry failures."""


class ResultStoreSchemaVersionError(ResultStoreError):
    """Raised when a result-store schema version cannot be opened safely."""


class RecordNotFoundError(ResultStoreError, KeyError):
    """Raised when a requested persistent result record does not exist."""


class ImmutableRecordError(ResultStoreError):
    """Raised when code attempts to destructively overwrite historical records."""


class ArtifactIntegrityError(ResultStoreError):
    """Raised when an artifact's bytes no longer match its stored content hash."""


__all__ = [
    "ArtifactIntegrityError", "CatalogVersionError", "ConfigurationError", "ImmutableRecordError", "MaterializationLimitError",
    "MissingCapabilityError", "RecordNotFoundError", "ResultStoreError", "ResultStoreSchemaVersionError",
    "StorageError", "ValidationError",
]
