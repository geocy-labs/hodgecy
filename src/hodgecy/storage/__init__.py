"""Storage and catalog primitives for HodgeCY."""
from .catalog import HodgeCYCatalog, open_catalog
from .errors import CatalogVersionError, MaterializationLimitError, MissingCapabilityError, StorageError
from .models import CatalogMetadata, ColumnarSourceRef, CorpusSnapshot, DatasetInstance, PhysicalSourceRef, RegisteredTable, SourceFormat, TableKind
from .parquet import build_parquet_metadata_cache, inspect_parquet_source, read_parquet_metadata_cache
from .planning import EstimateKind, QueryEstimate, QueryPlanSummary

__all__ = [
    "CatalogMetadata", "CatalogVersionError", "ColumnarSourceRef", "CorpusSnapshot", "DatasetInstance",
    "EstimateKind", "HodgeCYCatalog", "MaterializationLimitError", "MissingCapabilityError", "PhysicalSourceRef",
    "QueryEstimate", "QueryPlanSummary", "RegisteredTable", "SourceFormat", "StorageError", "TableKind",
    "build_parquet_metadata_cache", "inspect_parquet_source", "open_catalog", "read_parquet_metadata_cache",
]
