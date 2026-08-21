from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from hodgecy.storage import HodgeCYCatalog, TableKind

from .models import CertificateManifest
from .verify import manifest_payload_checksum, read_manifest


@dataclass(frozen=True, slots=True)
class CertificateRegistryRecord:
    certificate_id: str
    purpose: str
    artifact_class: str
    schema_version: str
    status: str
    relative_path: str
    manifest_sha256: str
    subject_count: int
    payload_count: int
    source_instances: tuple[str, ...] = ()
    datasets: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "certificate_id": self.certificate_id,
            "purpose": self.purpose,
            "artifact_class": self.artifact_class,
            "schema_version": self.schema_version,
            "status": self.status,
            "relative_path": self.relative_path,
            "manifest_sha256": self.manifest_sha256,
            "subject_count": self.subject_count,
            "payload_count": self.payload_count,
            "source_instances": list(self.source_instances),
            "datasets": list(self.datasets),
            "metadata": self.metadata,
        }


def registry_record(manifest: CertificateManifest, *, relative_path: str, status: str = "verified") -> CertificateRegistryRecord:
    datasets = []
    instances = []
    for subject in manifest.subjects:
        if subject.dataset_id is not None:
            datasets.append(subject.dataset_id.local_id)
        if subject.source_instance_id is not None:
            instances.append(subject.source_instance_id)
    return CertificateRegistryRecord(
        certificate_id=manifest.certificate_id.serialize(),
        purpose=manifest.purpose.value,
        artifact_class=manifest.artifact_class.value,
        schema_version=manifest.schema_version.value,
        status=status,
        relative_path=relative_path.replace("\\", "/"),
        manifest_sha256=manifest_payload_checksum(manifest),
        subject_count=len(manifest.subjects),
        payload_count=len(manifest.files),
        source_instances=tuple(sorted(set(instances))),
        datasets=tuple(sorted(set(datasets))),
        metadata=manifest.metadata,
    )


def certificate_summary_rows(records: Iterable[CertificateRegistryRecord]) -> list[dict[str, Any]]:
    return [record.to_dict() for record in records]


def records_from_certificate_dirs(root: str | Path) -> list[CertificateRegistryRecord]:
    base = Path(root)
    records: list[CertificateRegistryRecord] = []
    for manifest_path in sorted(base.glob("*/certificate.json")):
        manifest = read_manifest(manifest_path)
        records.append(registry_record(manifest, relative_path=manifest_path.parent.relative_to(base).as_posix()))
    return records


def register_certificate_summary_parquet_source(
    catalog: HodgeCYCatalog,
    *,
    columnar_id: str,
    instance_id: str,
    source_id: str,
    relative_path: str,
    table_name: str = "certificate_registry",
):
    return catalog.register_parquet_source(
        columnar_id=columnar_id,
        instance_id=instance_id,
        source_id=source_id,
        relative_path=relative_path,
        table_name=table_name,
        table_kind=TableKind.DERIVED,
        query_safe_columns=("certificate_id", "purpose", "artifact_class", "schema_version", "status", "relative_path", "manifest_sha256", "subject_count", "payload_count"),
        metadata={"artifact_kind": "certificate_registry", "schema_version": "certificate_registry.v1"},
    )
