from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from .errors import IdentityError
from .serialization import stable_sha256
from .versions import SchemaVersion

_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._=-]*$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

class IdentityKind(str, Enum):
    HODGECY_RECORD = "hodgecy_record"
    DATASET = "dataset"
    SOURCE_RECORD = "source_record"
    PRESENTATION = "presentation"
    GEOMETRY = "geometry"
    DERIVED_OBJECT = "derived_object"
    CERTIFICATE = "certificate"
    ALGORITHM = "algorithm"

class FingerprintKind(str, Enum):
    BYTE = "byte"
    NORMALIZED_PRESENTATION = "normalized_presentation"
    CANONICAL_PRESENTATION = "canonical_presentation"
    GEOMETRIC_EQUIVALENCE = "geometric_equivalence"


def _validate_token(name: str, value: str) -> None:
    if not _TOKEN_RE.fullmatch(value):
        raise IdentityError(f"Invalid {name}: {value!r}")

@dataclass(frozen=True, slots=True)
class HodgeCYID:
    kind: IdentityKind
    namespace: str
    local_id: str
    schema_version: SchemaVersion = SchemaVersion()

    def __post_init__(self) -> None:
        _validate_token("namespace", self.namespace)
        _validate_token("local_id", self.local_id)

    def serialize(self) -> str:
        return f"hcy:{self.schema_version}:{self.kind.value}:{self.namespace}:{self.local_id}"

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind.value, "namespace": self.namespace, "local_id": self.local_id, "schema_version": str(self.schema_version)}

    @classmethod
    def parse(cls, value: str) -> "HodgeCYID":
        parts = value.split(":")
        if len(parts) != 5 or parts[0] != "hcy":
            raise IdentityError(f"Invalid HodgeCY identity: {value!r}")
        _, version, kind, namespace, local_id = parts
        return cls(IdentityKind(kind), namespace, local_id, SchemaVersion(version))

    @classmethod
    def from_dict(cls, payload: dict[str, str]) -> "HodgeCYID":
        return cls(IdentityKind(payload["kind"]), str(payload["namespace"]), str(payload["local_id"]), SchemaVersion(str(payload.get("schema_version", "v1"))))

    @classmethod
    def dataset(cls, dataset_id: str, version: str = "v1") -> "HodgeCYID":
        return cls(IdentityKind.DATASET, "dataset", dataset_id, SchemaVersion(version))

    @classmethod
    def source_record(cls, dataset_id: str, native_id: str, version: str = "v1") -> "HodgeCYID":
        return cls(IdentityKind.SOURCE_RECORD, dataset_id, native_id, SchemaVersion(version))

    @classmethod
    def presentation(cls, family: str, fingerprint: str, version: str = "v1") -> "HodgeCYID":
        return cls(IdentityKind.PRESENTATION, family, fingerprint, SchemaVersion(version))

    @classmethod
    def derived_from_components(cls, kind: IdentityKind, namespace: str, components: object, version: str = "v1") -> "HodgeCYID":
        return cls(kind, namespace, stable_sha256(components), SchemaVersion(version))

    def require_kind(self, kind: IdentityKind) -> None:
        if self.kind is not kind:
            raise IdentityError(f"Expected {kind.value} identity, got {self.kind.value}")

    def __str__(self) -> str:
        return self.serialize()

@dataclass(frozen=True, slots=True)
class ContentFingerprint:
    algorithm: str
    value: str
    kind: FingerprintKind

    def __post_init__(self) -> None:
        if self.algorithm != "sha256":
            raise IdentityError("Only sha256 fingerprints are supported in the core foundation")
        if not _HEX64_RE.fullmatch(self.value):
            raise IdentityError(f"Invalid sha256 fingerprint: {self.value!r}")

    @classmethod
    def from_payload(cls, payload: object, kind: FingerprintKind) -> "ContentFingerprint":
        return cls("sha256", stable_sha256(payload), kind)

    def to_dict(self) -> dict[str, str]:
        return {"algorithm": self.algorithm, "value": self.value, "kind": self.kind.value}

    @classmethod
    def from_dict(cls, payload: dict[str, str]) -> "ContentFingerprint":
        return cls(str(payload["algorithm"]), str(payload["value"]), FingerprintKind(payload["kind"]))

@dataclass(frozen=True, slots=True)
class DistributionLocator:
    dataset_id: HodgeCYID
    distribution_id: str
    relative_path: str | None = None
    archive_member: str | None = None
    row_group: int | None = None
    row_offset: int | None = None
    source_line: int | None = None
    source_block: str | None = None

    def __post_init__(self) -> None:
        self.dataset_id.require_kind(IdentityKind.DATASET)
        _validate_token("distribution_id", self.distribution_id)
        for name in ("row_group", "row_offset", "source_line"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise IdentityError(f"{name} must be non-negative")

    def to_dict(self) -> dict[str, object]:
        return {"dataset_id": self.dataset_id.to_dict(), "distribution_id": self.distribution_id, "relative_path": self.relative_path, "archive_member": self.archive_member, "row_group": self.row_group, "row_offset": self.row_offset, "source_line": self.source_line, "source_block": self.source_block}

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "DistributionLocator":
        return cls(HodgeCYID.from_dict(payload["dataset_id"]), str(payload["distribution_id"]), payload.get("relative_path"), payload.get("archive_member"), payload.get("row_group"), payload.get("row_offset"), payload.get("source_line"), payload.get("source_block"))  # type: ignore[arg-type]
