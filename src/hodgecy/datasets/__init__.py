"""Dataset loaders and adapter foundations for HodgeCY."""

from .base import AdapterRun, AdapterRunSummary, DatasetAdapter, FixtureDatasetAdapter, NormalizationManifest
from .cicy import cicy3_adapter, cicy3_descriptor, cicy4_adapter, cicy4_descriptor
from .cynk_meyer import (
    load_family_equations,
    load_rigid_equations,
    load_table1,
    validate_table1,
)
from .double_octics import double_octic_adapter, double_octic_descriptor
from .operators import picard_fuchs_adapter, picard_fuchs_descriptor
from .registry import AdapterRegistry
from .toric import ip_weight_adapter, ip_weight_descriptor, kreuzer_skarke_descriptor
from .weighted import weighted_p4_adapter, weighted_p4_descriptor

__all__ = [
    "AdapterRegistry",
    "AdapterRun",
    "AdapterRunSummary",
    "DatasetAdapter",
    "FixtureDatasetAdapter",
    "NormalizationManifest",
    "cicy3_adapter",
    "cicy3_descriptor",
    "cicy4_adapter",
    "cicy4_descriptor",
    "double_octic_adapter",
    "double_octic_descriptor",
    "ip_weight_adapter",
    "ip_weight_descriptor",
    "kreuzer_skarke_descriptor",
    "load_family_equations",
    "load_rigid_equations",
    "load_table1",
    "picard_fuchs_adapter",
    "picard_fuchs_descriptor",
    "validate_table1",
    "weighted_p4_adapter",
    "weighted_p4_descriptor",
]
