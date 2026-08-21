from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from hodgecy.core.dataset import ConstructionFamily, DatasetDescriptor
from hodgecy.core.ids import HodgeCYID
from hodgecy.core.status import AcquisitionStatus, RedistributionStatus
from hodgecy.core.versions import SchemaVersion

from .errors import StorageError
from .models import DatasetInstance, PhysicalSourceRef, SourceFormat


def _enum_value(enum_cls, value):
    raw = str(value)
    try:
        return enum_cls(raw)
    except ValueError:
        try:
            return enum_cls[raw].value
        except KeyError:
            raise

_DESCRIPTOR_KEYS = {
    "dataset_id", "id", "id_schema_version", "name", "construction_family", "family", "acquisition_status",
    "redistribution_status", "schema_version", "source_version", "record_semantics", "identifier_definition",
    "source_citations", "source_urls", "doi", "expected_count", "verified_count", "adapter_capabilities",
}


def read_dataset_manifest(path: str | Path) -> list[dict[str, Any]]:
    manifest_path = Path(path)
    suffix = manifest_path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        records = payload.get("datasets") or payload.get("records") if isinstance(payload, dict) else payload
        if not isinstance(records, list):
            raise StorageError("Dataset JSON manifest must contain a list or a 'datasets' list")
        return [dict(record) for record in records]
    if suffix == ".tsv":
        with manifest_path.open("r", encoding="utf-8", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle, delimiter="\t")]
    raise StorageError(f"Unsupported dataset manifest format: {manifest_path.suffix}")


def descriptor_from_manifest_record(record: dict[str, Any]) -> DatasetDescriptor:
    dataset_key = str(record.get("dataset_id") or record.get("id") or "")
    if not dataset_key:
        raise StorageError("Manifest record is missing dataset_id")
    return DatasetDescriptor(
        dataset_id=HodgeCYID.dataset(dataset_key, str(record.get("id_schema_version") or "v1")),
        name=str(record.get("name") or dataset_key),
        construction_family=ConstructionFamily.known(str(record.get("construction_family") or record.get("family") or "source_registry")),
        acquisition_status=AcquisitionStatus(_enum_value(AcquisitionStatus, record.get("acquisition_status") or AcquisitionStatus.SOURCE_REGISTRY_ONLY.value)),
        redistribution_status=RedistributionStatus(_enum_value(RedistributionStatus, record.get("redistribution_status") or RedistributionStatus.UNSPECIFIED.value)),
        schema_version=SchemaVersion(str(record.get("schema_version") or "v1")),
        source_version=record.get("source_version"),
        record_semantics=record.get("record_semantics"),
        identifier_definition=record.get("identifier_definition"),
        source_citations=tuple(filter(None, str(record.get("source_citations") or "").split(";"))),
        source_urls=tuple(filter(None, str(record.get("source_urls") or "").split(";"))),
        doi=record.get("doi"),
        expected_count=int(record["expected_count"]) if record.get("expected_count") not in (None, "") else None,
        verified_count=int(record["verified_count"]) if record.get("verified_count") not in (None, "") else None,
        adapter_capabilities=tuple(filter(None, str(record.get("adapter_capabilities") or "").split(";"))),
        metadata={k: v for k, v in record.items() if k not in _DESCRIPTOR_KEYS},
    )


def instance_from_manifest_record(record: dict[str, Any], descriptor: DatasetDescriptor) -> DatasetInstance:
    instance_id = str(record.get("instance_id") or f"{descriptor.dataset_id.local_id}_{descriptor.source_version or 'registry'}")
    return DatasetInstance(
        instance_id=instance_id,
        dataset_id=descriptor.dataset_id,
        source_version=descriptor.source_version,
        acquisition_status=descriptor.acquisition_status,
        redistribution_status=descriptor.redistribution_status,
        record_count=descriptor.verified_count or descriptor.expected_count,
        schema_version=descriptor.schema_version,
        source_revision=record.get("source_revision"),
        adapter_name=record.get("adapter_name"),
        metadata={"manifest_record": record},
    )


def source_refs_from_manifest_record(record: dict[str, Any], instance: DatasetInstance) -> Iterable[PhysicalSourceRef]:
    source_path = record.get("relative_path") or record.get("path")
    source_uri = record.get("uri")
    if not source_path and not source_uri:
        return ()
    source_id = str(record.get("source_id") or f"{instance.instance_id}_source")
    return (
        PhysicalSourceRef(
            source_id=source_id,
            instance_id=instance.instance_id,
            relative_path=source_path,
            uri=source_uri,
            sha256=record.get("sha256"),
            byte_size=int(record["byte_size"]) if record.get("byte_size") not in (None, "") else None,
            source_format=SourceFormat(_enum_value(SourceFormat, record.get("source_format") or SourceFormat.NATIVE.value)),
            partition=record.get("partition"),
            archive_member=record.get("archive_member"),
            metadata={"source_revision": record.get("source_revision")},
        ),
    )
