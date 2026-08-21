"""Dataset loaders and adapter foundations for HodgeCY."""

from .base import AdapterRun, AdapterRunSummary, DatasetAdapter, FixtureDatasetAdapter, NormalizationManifest
from .cicy import cicy3_adapter, cicy3_descriptor, cicy4_adapter, cicy4_descriptor
from .cicy4_fibrations import (
    CICY4FibrationArchiveIndex,
    CICY4FibrationMemberIndex,
    ArchiveMemberLocator,
    build_cicy4_fibration_archive_index,
    iter_member_lines,
    open_archive_member,
    read_cicy4_fibration_archive_index,
)
from .cynk_meyer import (
    load_family_equations,
    load_rigid_equations,
    load_table1,
    validate_table1,
)
from .double_octics import double_octic_adapter, double_octic_descriptor
from .kreuzer_skarke import (
    KreuzerSkarkeRowReference,
    default_ks_projection,
    hodge_pair_filter,
    kreuzer_skarke_descriptor,
    ks_field_metadata,
    ks_query,
    register_kreuzer_skarke_parquet_source,
)
from .operators import picard_fuchs_adapter, picard_fuchs_descriptor
from .registry import AdapterRegistry
from .toric import ip_weight_adapter, ip_weight_descriptor
from .weighted import weighted_p4_adapter, weighted_p4_descriptor

__all__ = [
    "AdapterRegistry",
    "AdapterRun",
    "AdapterRunSummary",
    "ArchiveMemberLocator",
    "CICY4FibrationArchiveIndex",
    "CICY4FibrationMemberIndex",
    "DatasetAdapter",
    "FixtureDatasetAdapter",
    "KreuzerSkarkeRowReference",
    "NormalizationManifest",
    "build_cicy4_fibration_archive_index",
    "cicy3_adapter",
    "cicy3_descriptor",
    "cicy4_adapter",
    "cicy4_descriptor",
    "default_ks_projection",
    "double_octic_adapter",
    "double_octic_descriptor",
    "hodge_pair_filter",
    "ip_weight_adapter",
    "ip_weight_descriptor",
    "iter_member_lines",
    "kreuzer_skarke_descriptor",
    "ks_field_metadata",
    "ks_query",
    "load_family_equations",
    "load_rigid_equations",
    "load_table1",
    "open_archive_member",
    "picard_fuchs_descriptor",
    "picard_fuchs_adapter",
    "read_cicy4_fibration_archive_index",
    "register_kreuzer_skarke_parquet_source",
    "validate_table1",
    "weighted_p4_adapter",
    "weighted_p4_descriptor",
]
