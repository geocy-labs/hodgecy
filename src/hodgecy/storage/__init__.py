"""Storage and catalog primitives for HodgeCY."""
from .catalog import HodgeCYCatalog, open_catalog
from .errors import (
    ArtifactIntegrityError,
    CatalogVersionError,
    ImmutableRecordError,
    MaterializationLimitError,
    MissingCapabilityError,
    RecordNotFoundError,
    ResultStoreError,
    ResultStoreSchemaVersionError,
    StorageError,
)
from .models import CatalogMetadata, ColumnarSourceRef, CorpusSnapshot, DatasetInstance, PhysicalSourceRef, RegisteredTable, SourceFormat, TableKind
from .parquet import build_parquet_metadata_cache, inspect_parquet_source, read_parquet_metadata_cache
from .planning import EstimateKind, QueryEstimate, QueryPlanSummary
from .result_store import (
    ArtifactRecord,
    CalculationRun,
    CertificateRecord,
    ComparisonSetRecord,
    GeometryRecord,
    InvariantRecord,
    RecordType,
    ResultStore,
    RunStatus,
    SpectrumRecord,
    file_sha256,
    normalized_content_hash,
)

__all__ = [
    "ArtifactIntegrityError", "ArtifactRecord", "CalculationRun", "CatalogMetadata", "CatalogVersionError", "CertificateRecord",
    "ColumnarSourceRef", "ComparisonSetRecord", "CorpusSnapshot", "DatasetInstance", "EstimateKind", "GeometryRecord",
    "HodgeCYCatalog", "ImmutableRecordError", "InvariantRecord", "MaterializationLimitError", "MissingCapabilityError",
    "PhysicalSourceRef", "QueryEstimate", "QueryPlanSummary", "RecordNotFoundError", "RecordType", "RegisteredTable",
    "ResultStore", "ResultStoreError", "ResultStoreSchemaVersionError", "RunStatus", "SourceFormat", "SpectrumRecord",
    "StorageError", "TableKind", "build_parquet_metadata_cache", "file_sha256", "inspect_parquet_source",
    "normalized_content_hash", "open_catalog", "read_parquet_metadata_cache",
]
