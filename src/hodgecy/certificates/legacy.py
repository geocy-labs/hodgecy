from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import CertificatePurpose
from .verify import CertificateVerificationIssue, sha256_file


@dataclass(frozen=True, slots=True)
class LegacyReleaseCertificateSummary:
    release_version: str
    release_tag: str
    package_version: str
    generation_source_commit: str
    theorem_arrangements: tuple[str, ...]
    file_count: int
    manifest_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "release_version": self.release_version,
            "release_tag": self.release_tag,
            "package_version": self.package_version,
            "generation_source_commit": self.generation_source_commit,
            "theorem_arrangements": list(self.theorem_arrangements),
            "file_count": self.file_count,
            "manifest_path": self.manifest_path,
            "purpose": CertificatePurpose.LEGACY_THEOREM_RESULT.value,
        }


def read_v0_2_0_release_manifest(release_dir: str | Path) -> dict[str, Any]:
    return json.loads((Path(release_dir) / "MANIFEST.json").read_text(encoding="utf-8"))


def legacy_release_summary(release_dir: str | Path) -> LegacyReleaseCertificateSummary:
    root = Path(release_dir)
    payload = read_v0_2_0_release_manifest(root)
    return LegacyReleaseCertificateSummary(
        release_version=str(payload.get("release_version") or ""),
        release_tag=str(payload.get("release_tag") or ""),
        package_version=str(payload.get("package_version") or ""),
        generation_source_commit=str(payload.get("generation_source_commit") or ""),
        theorem_arrangements=tuple(str(item) for item in payload.get("theorem_arrangements") or ()),
        file_count=len(payload.get("files") or ()),
        manifest_path="MANIFEST.json",
    )


def verify_legacy_release_checksums(release_dir: str | Path) -> tuple[CertificateVerificationIssue, ...]:
    root = Path(release_dir)
    payload = read_v0_2_0_release_manifest(root)
    issues: list[CertificateVerificationIssue] = []
    for row in payload.get("files") or ():
        rel = str(row["path"])
        path = root / rel
        if not path.exists():
            issues.append(CertificateVerificationIssue("missing_legacy_payload", "historical release payload is missing", rel))
            continue
        actual = sha256_file(path)
        if actual != row.get("sha256"):
            issues.append(CertificateVerificationIssue("legacy_checksum_mismatch", "historical release checksum mismatch", rel))
    return tuple(issues)
