from __future__ import annotations

import importlib.metadata
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from hodgecy import __version__
from hodgecy.core.serialization import canonical_json

from .models import ArtifactClass, CertificateFileRef, CertificateManifest, CertificatePurpose, CertificateSubject, EnvironmentCapture
from .verify import CertificateVerificationError, sha256_file, verify_certificate, write_manifest


def capture_environment(*, repo_root: str | Path | None = None, dependencies: Iterable[str] = ("sympy", "pandas", "pyarrow", "duckdb")) -> EnvironmentCapture:
    commit = None
    dirty = None
    if repo_root is not None:
        root = Path(repo_root)
        commit = _git(root, "rev-parse", "HEAD")
        dirty = bool(_git(root, "status", "--porcelain=v1"))
    versions: dict[str, str | None] = {}
    for dependency in dependencies:
        try:
            versions[dependency] = importlib.metadata.version(dependency)
        except importlib.metadata.PackageNotFoundError:
            versions[dependency] = None
    return EnvironmentCapture(
        python_version=sys.version,
        platform=platform.platform(),
        hodgecy_version=__version__,
        hodgecy_commit=commit,
        git_dirty=dirty,
        dependencies=versions,
        backends={"python": platform.python_implementation()},
    )


def build_certificate(
    output_root: str | Path,
    *,
    purpose: CertificatePurpose,
    subjects: tuple[CertificateSubject, ...],
    payloads: dict[str, bytes | str],
    environment: EnvironmentCapture,
    validation_results: tuple[Any, ...] = (),
    algorithm_provenance: tuple[Any, ...] = (),
    generated_summaries: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    created_utc: str | None = None,
) -> CertificateManifest:
    output = Path(output_root)
    output.mkdir(parents=True, exist_ok=True)
    created = created_utc or datetime.now(timezone.utc).isoformat()
    temp_dir = Path(tempfile.mkdtemp(prefix=".hodgecy-cert-", dir=output))
    try:
        file_refs: list[CertificateFileRef] = []
        for relative_path, payload in sorted(payloads.items()):
            target = _safe_payload_path(temp_dir, relative_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(payload, bytes):
                target.write_bytes(payload)
            else:
                target.write_text(payload, encoding="utf-8")
            file_refs.append(CertificateFileRef(relative_path.replace("\\", "/"), sha256_file(target), target.stat().st_size))
        manifest = CertificateManifest(
            purpose=purpose,
            artifact_class=ArtifactClass.CERTIFIED,
            subjects=subjects,
            files=tuple(file_refs),
            created_utc=created,
            environment=environment,
            validation_results=validation_results,
            algorithm_provenance=algorithm_provenance,
            generated_summaries=generated_summaries or {},
            metadata=metadata or {},
        )
        write_manifest(temp_dir / "certificate.json", manifest)
        verification = verify_certificate(temp_dir)
        if not verification.ok:
            raise CertificateVerificationError(str(verification.to_dict()))
        final_dir = output / manifest.local_id
        if final_dir.exists():
            existing = verify_certificate(final_dir).require_ok()
            if existing.to_dict() != manifest.to_dict():
                raise FileExistsError(f"conflicting certificate already exists: {final_dir}")
            shutil.rmtree(temp_dir)
            return existing
        temp_dir.replace(final_dir)
        return manifest
    except Exception:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        raise


def _safe_payload_path(root: Path, relative_path: str) -> Path:
    path = Path(relative_path.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or str(path) in {"", ".", "certificate.json"}:
        raise ValueError(f"unsafe certificate payload path: {relative_path!r}")
    return root / path


def _git(root: Path, *args: str) -> str | None:
    try:
        return subprocess.run(["git", *args], cwd=root, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()
    except Exception:
        return None


def json_payload(value: Any) -> str:
    return canonical_json(value) + "\n"
