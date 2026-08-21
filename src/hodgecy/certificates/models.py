from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from hodgecy.core.ids import HodgeCYID, IdentityKind
from hodgecy.core.provenance import ComputationProvenance
from hodgecy.core.serialization import stable_sha256
from hodgecy.core.status import ClaimLevel, ValidationEvent
from hodgecy.core.versions import SchemaVersion

CERTIFICATE_SCHEMA_NAME = "hodgecy.certificate"
CERTIFICATE_SCHEMA_VERSION = "certificate.v1"


class CertificatePurpose(str, Enum):
    SOURCE_INGEST = "source_ingest"
    NORMALIZATION = "normalization"
    RELATIONSHIP_IMPORT = "relationship_import"
    DATA_SNAPSHOT = "data_snapshot"
    LEGACY_THEOREM_RESULT = "legacy_theorem_result"
    REPORT_ARTIFACT = "report_artifact"


class ArtifactClass(str, Enum):
    CACHE = "cache"
    DERIVED = "derived"
    CERTIFIED = "certified"


@dataclass(frozen=True, slots=True)
class CertificateFileRef:
    path: str
    sha256: str
    byte_size: int
    role: str = "payload"

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "sha256": self.sha256, "byte_size": self.byte_size, "role": self.role}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CertificateFileRef":
        return cls(str(payload["path"]), str(payload["sha256"]), int(payload["byte_size"]), str(payload.get("role") or "payload"))


@dataclass(frozen=True, slots=True)
class CertificateSubject:
    subject_type: str
    object_id: HodgeCYID | None = None
    dataset_id: HodgeCYID | None = None
    source_instance_id: str | None = None
    source_revision: str | None = None
    source_checksum: str | None = None
    payload_ref: str | None = None
    basis_labels: tuple[str, ...] = ()
    relationship_evidence: tuple[str, ...] = ()
    claim_level: ClaimLevel = ClaimLevel.SOURCE_REPORTED
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.dataset_id is not None:
            self.dataset_id.require_kind(IdentityKind.DATASET)

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject_type": self.subject_type,
            "object_id": None if self.object_id is None else self.object_id.to_dict(),
            "dataset_id": None if self.dataset_id is None else self.dataset_id.to_dict(),
            "source_instance_id": self.source_instance_id,
            "source_revision": self.source_revision,
            "source_checksum": self.source_checksum,
            "payload_ref": self.payload_ref,
            "basis_labels": list(self.basis_labels),
            "relationship_evidence": list(self.relationship_evidence),
            "claim_level": self.claim_level.value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CertificateSubject":
        object_payload = payload.get("object_id")
        dataset_payload = payload.get("dataset_id")
        return cls(
            subject_type=str(payload["subject_type"]),
            object_id=None if object_payload is None else HodgeCYID.from_dict(object_payload),
            dataset_id=None if dataset_payload is None else HodgeCYID.from_dict(dataset_payload),
            source_instance_id=payload.get("source_instance_id"),
            source_revision=payload.get("source_revision"),
            source_checksum=payload.get("source_checksum"),
            payload_ref=payload.get("payload_ref"),
            basis_labels=tuple(payload.get("basis_labels") or ()),
            relationship_evidence=tuple(payload.get("relationship_evidence") or ()),
            claim_level=ClaimLevel(payload.get("claim_level", ClaimLevel.SOURCE_REPORTED.value)),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class EnvironmentCapture:
    python_version: str
    platform: str
    hodgecy_version: str | None = None
    hodgecy_commit: str | None = None
    git_dirty: bool | None = None
    dependencies: dict[str, str | None] = field(default_factory=dict)
    backends: dict[str, str | None] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "python_version": self.python_version,
            "platform": self.platform,
            "hodgecy_version": self.hodgecy_version,
            "hodgecy_commit": self.hodgecy_commit,
            "git_dirty": self.git_dirty,
            "dependencies": self.dependencies,
            "backends": self.backends,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EnvironmentCapture":
        return cls(
            python_version=str(payload["python_version"]),
            platform=str(payload["platform"]),
            hodgecy_version=payload.get("hodgecy_version"),
            hodgecy_commit=payload.get("hodgecy_commit"),
            git_dirty=payload.get("git_dirty"),
            dependencies=dict(payload.get("dependencies") or {}),
            backends=dict(payload.get("backends") or {}),
        )


@dataclass(frozen=True, slots=True)
class CertificateManifest:
    purpose: CertificatePurpose
    artifact_class: ArtifactClass
    subjects: tuple[CertificateSubject, ...]
    files: tuple[CertificateFileRef, ...]
    created_utc: str
    environment: EnvironmentCapture
    validation_results: tuple[ValidationEvent, ...] = ()
    algorithm_provenance: tuple[ComputationProvenance, ...] = ()
    generated_summaries: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    certificate_id: HodgeCYID | None = None
    schema_name: str = CERTIFICATE_SCHEMA_NAME
    schema_version: SchemaVersion = SchemaVersion(CERTIFICATE_SCHEMA_VERSION)

    def __post_init__(self) -> None:
        if self.artifact_class is not ArtifactClass.CERTIFIED:
            raise ValueError("CertificateManifest artifact_class must be certified")
        if self.certificate_id is None:
            object.__setattr__(self, "certificate_id", self.derive_certificate_id())
        assert self.certificate_id is not None
        self.certificate_id.require_kind(IdentityKind.CERTIFICATE)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "purpose": self.purpose.value,
            "artifact_class": self.artifact_class.value,
            "subjects": [subject.to_dict() for subject in self.subjects],
            "files": [file_ref.to_dict() for file_ref in self.files],
            "validation_results": [event.to_dict() for event in self.validation_results],
            "algorithm_provenance": [item.to_dict() for item in self.algorithm_provenance],
            "generated_summaries": self.generated_summaries,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version.to_dict(),
        }

    def derive_certificate_id(self) -> HodgeCYID:
        return HodgeCYID(IdentityKind.CERTIFICATE, "certificate", stable_sha256(self.identity_payload()))

    @property
    def local_id(self) -> str:
        assert self.certificate_id is not None
        return self.certificate_id.local_id

    def to_dict(self) -> dict[str, Any]:
        assert self.certificate_id is not None
        return {
            "certificate_id": self.certificate_id.to_dict(),
            "purpose": self.purpose.value,
            "artifact_class": self.artifact_class.value,
            "subjects": [subject.to_dict() for subject in self.subjects],
            "files": [file_ref.to_dict() for file_ref in self.files],
            "created_utc": self.created_utc,
            "environment": self.environment.to_dict(),
            "validation_results": [event.to_dict() for event in self.validation_results],
            "algorithm_provenance": [item.to_dict() for item in self.algorithm_provenance],
            "generated_summaries": self.generated_summaries,
            "metadata": self.metadata,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CertificateManifest":
        return cls(
            certificate_id=HodgeCYID.from_dict(payload["certificate_id"]),
            purpose=CertificatePurpose(payload["purpose"]),
            artifact_class=ArtifactClass(payload.get("artifact_class", ArtifactClass.CERTIFIED.value)),
            subjects=tuple(CertificateSubject.from_dict(row) for row in payload.get("subjects") or ()),
            files=tuple(CertificateFileRef.from_dict(row) for row in payload.get("files") or ()),
            created_utc=str(payload["created_utc"]),
            environment=EnvironmentCapture.from_dict(payload["environment"]),
            validation_results=tuple(ValidationEvent.from_dict(row) for row in payload.get("validation_results") or ()),
            algorithm_provenance=tuple(ComputationProvenance.from_dict(row) for row in payload.get("algorithm_provenance") or ()),
            generated_summaries=dict(payload.get("generated_summaries") or {}),
            metadata=dict(payload.get("metadata") or {}),
            schema_name=str(payload.get("schema_name") or CERTIFICATE_SCHEMA_NAME),
            schema_version=SchemaVersion.from_dict(payload.get("schema_version", {"value": CERTIFICATE_SCHEMA_VERSION})),
        )
