from __future__ import annotations

import json

import pytest

from hodgecy.core.dataset import ConstructionFamily, DatasetDescriptor
from hodgecy.core.ids import HodgeCYID
from hodgecy.core.status import AcquisitionStatus, RedistributionStatus
from hodgecy.storage import DatasetInstance, PhysicalSourceRef, SourceFormat, open_catalog
from hodgecy.storage.errors import CatalogVersionError, MissingCapabilityError, StorageError


def _descriptor() -> DatasetDescriptor:
    return DatasetDescriptor(
        dataset_id=HodgeCYID.dataset("ks_fixture"),
        name="KS fixture",
        construction_family=ConstructionFamily.known("toric_hypersurface"),
        acquisition_status=AcquisitionStatus.COMPLETE_COLUMNAR,
        redistribution_status=RedistributionStatus.REDISTRIBUTABLE,
        expected_count=3,
        verified_count=3,
    )


def test_catalog_create_register_and_reopen(tmp_path) -> None:
    catalog = open_catalog(tmp_path, create=True)
    descriptor = catalog.register_dataset(_descriptor())
    instance = catalog.register_instance(DatasetInstance(
        instance_id="ks_fixture_v1",
        dataset_id=descriptor.dataset_id,
        source_version="fixture-v1",
        acquisition_status=AcquisitionStatus.COMPLETE_COLUMNAR,
        redistribution_status=RedistributionStatus.REDISTRIBUTABLE,
        record_count=3,
    ))
    source = catalog.register_physical_source(PhysicalSourceRef(
        source_id="ks_fixture_parquet",
        instance_id=instance.instance_id,
        relative_path="raw/ks_fixture/polytopes.parquet",
        source_format=SourceFormat.PARQUET,
        byte_size=123,
    ))
    snapshot = catalog.create_snapshot("snapshot_v1", hodgecy_version="1.0.0")

    reopened = open_catalog(tmp_path, read_only=True)
    assert reopened.metadata.catalog_schema_version.value == "v1"
    assert reopened.dataset_status("ks_fixture")["installed"] is True
    assert reopened.list_physical_sources(instance.instance_id)[0].relative_path == source.relative_path
    assert reopened.payload["snapshots"][snapshot.snapshot_id]["dataset_instances"] == ["ks_fixture_v1"]


def test_catalog_idempotent_and_conflict_registration(tmp_path) -> None:
    catalog = open_catalog(tmp_path, create=True)
    descriptor = _descriptor()
    catalog.register_dataset(descriptor)
    catalog.register_dataset(descriptor)
    conflicting = DatasetDescriptor(
        dataset_id=descriptor.dataset_id,
        name="different",
        construction_family=descriptor.construction_family,
        acquisition_status=descriptor.acquisition_status,
        redistribution_status=descriptor.redistribution_status,
    )
    with pytest.raises(StorageError):
        catalog.register_dataset(conflicting)


def test_catalog_schema_future_version_refuses_open(tmp_path) -> None:
    catalog = open_catalog(tmp_path, create=True)
    payload = json.loads(catalog.path.read_text(encoding="utf-8"))
    payload["metadata"]["catalog_schema_version"] = {"value": "v999"}
    catalog.path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CatalogVersionError):
        open_catalog(tmp_path, read_only=True)


def test_manifest_bootstrap_and_relative_path_validation(tmp_path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"datasets": [{
        "dataset_id": "gcicy_registry",
        "name": "gCICY registry fixture",
        "family": "generalized_cicy",
        "acquisition_status": "SOURCE_REGISTRY_ONLY",
        "redistribution_status": "REMOTE_OR_MANUAL_ONLY",
        "instance_id": "gcicy_registry_v1",
        "source_version": "fixture",
        "relative_path": "manifests/gcicy.tsv",
        "source_format": "tsv",
        "source_revision": "fixture-rev",
        "unknown_source_note": "preserved",
    }]}), encoding="utf-8")
    catalog = open_catalog(tmp_path, create=True)
    descriptors = catalog.bootstrap_manifest(manifest)
    assert descriptors[0].metadata["unknown_source_note"] == "preserved"
    assert catalog.dataset_status("gcicy_registry")["logical_acquisition_status"] == "SOURCE_REGISTRY_ONLY"
    with pytest.raises(Exception):
        PhysicalSourceRef(source_id="bad", instance_id="gcicy_registry_v1", relative_path="../escape.parquet")


def test_optional_duckdb_backend_missing_or_opens(tmp_path) -> None:
    try:
        open_catalog(tmp_path, create=True, backend="duckdb")
    except MissingCapabilityError as exc:
        assert "duckdb" in str(exc).lower()
