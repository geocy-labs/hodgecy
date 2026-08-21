from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from hodgecy.core.serialization import canonical_json, stable_sha256

from .models import CERTIFICATE_SCHEMA_VERSION, CertificateFileRef, CertificateManifest


@dataclass(frozen=True, slots=True)
class CertificateVerificationIssue:
    code: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {"code": self.code, "message": self.message, "path": self.path}


@dataclass(frozen=True, slots=True)
class CertificateVerificationResult:
    manifest: CertificateManifest | None
    issues: tuple[CertificateVerificationIssue, ...]

    @property
    def ok(self) -> bool:
        return not self.issues

    def require_ok(self) -> CertificateManifest:
        if self.issues:
            first = self.issues[0]
            raise CertificateVerificationError(f"{first.code}: {first.message}")
        assert self.manifest is not None
        return self.manifest

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "certificate_id": None if self.manifest is None else self.manifest.certificate_id.serialize(),
            "issues": [issue.to_dict() for issue in self.issues],
        }


class CertificateVerificationError(Exception):
    pass


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_payload_checksum(manifest: CertificateManifest) -> str:
    return stable_sha256(manifest.to_dict())


def write_manifest(path: Path, manifest: CertificateManifest) -> None:
    path.write_text(canonical_json(manifest.to_dict()) + "\n", encoding="utf-8")


def read_manifest(path: Path) -> CertificateManifest:
    import json

    return CertificateManifest.from_dict(json.loads(path.read_text(encoding="utf-8")))


def verify_certificate(certificate_dir: str | Path) -> CertificateVerificationResult:
    root = Path(certificate_dir)
    manifest_path = root / "certificate.json"
    issues: list[CertificateVerificationIssue] = []
    if not manifest_path.exists():
        return CertificateVerificationResult(None, (CertificateVerificationIssue("missing_manifest", "certificate.json is missing", "certificate.json"),))
    try:
        manifest = read_manifest(manifest_path)
    except Exception as exc:
        return CertificateVerificationResult(None, (CertificateVerificationIssue("malformed_manifest", f"manifest could not be parsed: {type(exc).__name__}", "certificate.json"),))
    if manifest.schema_version.value != CERTIFICATE_SCHEMA_VERSION:
        issues.append(CertificateVerificationIssue("unsupported_schema", f"unsupported schema {manifest.schema_version.value}", "certificate.json"))
    if manifest.derive_certificate_id() != manifest.certificate_id:
        issues.append(CertificateVerificationIssue("certificate_id_mismatch", "certificate_id does not match manifest identity payload", "certificate.json"))
    seen: set[str] = set()
    for file_ref in manifest.files:
        issues.extend(_verify_file(root, file_ref, seen))
    return CertificateVerificationResult(manifest, tuple(issues))


def _verify_file(root: Path, file_ref: CertificateFileRef, seen: set[str]) -> Iterable[CertificateVerificationIssue]:
    path = Path(file_ref.path)
    if path.is_absolute() or ".." in path.parts or str(path) in {"", "."}:
        yield CertificateVerificationIssue("unsafe_payload_path", "payload path must be certificate-root-relative", file_ref.path)
        return
    if file_ref.path in seen:
        yield CertificateVerificationIssue("duplicate_payload", "payload path appears more than once", file_ref.path)
    seen.add(file_ref.path)
    full_path = root / path
    if not full_path.exists():
        yield CertificateVerificationIssue("missing_payload", "payload file is missing", file_ref.path)
        return
    byte_size = full_path.stat().st_size
    if byte_size != file_ref.byte_size:
        yield CertificateVerificationIssue("payload_size_mismatch", f"expected {file_ref.byte_size} bytes, found {byte_size}", file_ref.path)
    actual = sha256_file(full_path)
    if actual != file_ref.sha256:
        yield CertificateVerificationIssue("payload_checksum_mismatch", "payload sha256 does not match manifest", file_ref.path)
