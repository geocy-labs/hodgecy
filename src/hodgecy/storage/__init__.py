"""Storage and catalog primitives for HodgeCY."""
from .catalog import HodgeCYCatalog, open_catalog
from .errors import CatalogVersionError, MaterializationLimitError, MissingCapabilityError, StorageError
from .models import CatalogMetadata, ColumnarSourceRef, CorpusSnapshot, DatasetInstance, PhysicalSourceRef, RegisteredTable, SourceFormat, TableKind
from .parquet import inspect_parquet_source

__all__ = [
    "CatalogMetadata", "CatalogVersionError", "ColumnarSourceRef", "CorpusSnapshot", "DatasetInstance",
    "HodgeCYCatalog", "MaterializationLimitError", "MissingCapabilityError", "PhysicalSourceRef",
    "RegisteredTable", "SourceFormat", "StorageError", "TableKind", "inspect_parquet_source", "open_catalog",
]
