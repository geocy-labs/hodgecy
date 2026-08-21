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


__all__ = [
    "CatalogVersionError", "ConfigurationError", "MaterializationLimitError",
    "MissingCapabilityError", "StorageError", "ValidationError",
]
