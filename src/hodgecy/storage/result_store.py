from __future__ import annotations

import json
import sqlite3
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable

from hodgecy import __version__ as HODGECY_VERSION
from hodgecy.core.results import (
    ConifoldAtomSpectrum,
    EvidenceStatus,
    ResultKind,
    ResultMetadata,
    SmoothHodgeAtomSpectrum,
    SourceAssemblySpectrum,
)
from hodgecy.core.serialization import canonical_json, stable_sha256
from hodgecy.core.versions import SchemaVersion
from hodgecy.storage.errors import (
    ArtifactIntegrityError,
    ImmutableRecordError,
    RecordNotFoundError,
    ResultStoreError,
    ResultStoreSchemaVersionError,
    ValidationError,
)
from hodgecy.storage.models import normalize_relative_path, utc_now_iso

RESULT_STORE_SCHEMA_VERSION = 1
RESULT_STORE_SCHEMA_LABEL = "result_store.v1"


class RunStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SUPERSEDED = "SUPERSEDED"


class RecordType(str, Enum):
    GEOMETRY = "geometry"
    CALCULATION_RUN = "calculation_run"
    INVARIANT = "invariant"
    CERTIFICATE = "certificate"
    ARTIFACT = "artifact"
    SPECTRUM = "spectrum"
    COMPARISON_SET = "comparison_set"


def normalized_content_hash(payload: Any) -> str:
    return stable_sha256(payload)


def file_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _loads(value: str | None, default: Any) -> Any:
    return default if value in (None, "") else json.loads(value)


def _dumps(value: Any) -> str:
    return canonical_json(value)


def _id(prefix: str, payload: Any | None = None) -> str:
    if payload is None:
        return f"{prefix}_{uuid.uuid4().hex}"
    return f"{prefix}_{stable_sha256(payload)[:24]}"


def _detect_git_commit(start: Path | None = None) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=start,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None
    return completed.stdout.strip() or None


@dataclass(frozen=True, slots=True)
class GeometryRecord:
    geometry_id: str
    display_name: str
    geometry_type: str
    source_dataset: str | None = None
    source_dataset_version: str | None = None
    source_entry_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    provenance: str | None = None
    created_at: str = field(default_factory=utc_now_iso)

    @classmethod
    def deterministic_id(cls, *, geometry_type: str, source_dataset: str | None, source_entry_id: str | None, metadata: dict[str, Any] | None = None) -> str:
        return _id("geom", {"geometry_type": geometry_type, "source_dataset": source_dataset, "source_entry_id": source_entry_id, "metadata": metadata or {}})

    def to_dict(self) -> dict[str, Any]:
        return {
            "geometry_id": self.geometry_id,
            "display_name": self.display_name,
            "geometry_type": self.geometry_type,
            "source_dataset": self.source_dataset,
            "source_dataset_version": self.source_dataset_version,
            "source_entry_id": self.source_entry_id,
            "metadata": self.metadata,
            "provenance": self.provenance,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GeometryRecord":
        return cls(
            geometry_id=str(payload["geometry_id"]),
            display_name=str(payload["display_name"]),
            geometry_type=str(payload["geometry_type"]),
            source_dataset=payload.get("source_dataset"),
            source_dataset_version=payload.get("source_dataset_version"),
            source_entry_id=payload.get("source_entry_id"),
            metadata=dict(payload.get("metadata") or {}),
            provenance=payload.get("provenance"),
            created_at=str(payload.get("created_at") or utc_now_iso()),
        )


@dataclass(frozen=True, slots=True)
class CalculationRun:
    run_id: str
    geometry_id: str
    calculation_type: str
    started_at: str
    completed_at: str | None = None
    status: RunStatus = RunStatus.RUNNING
    hodgecy_version: str | None = HODGECY_VERSION
    git_commit: str | None = None
    schema_version: SchemaVersion = SchemaVersion(RESULT_STORE_SCHEMA_LABEL)
    input_hash: str | None = None
    parameter_hash: str | None = None
    backend: str | None = None
    coefficient_ring: str | None = None
    environment_metadata: dict[str, Any] = field(default_factory=dict)
    notes: str | None = None
    superseded_by_run_id: str | None = None
    supersession_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "geometry_id": self.geometry_id,
            "calculation_type": self.calculation_type,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status.value,
            "hodgecy_version": self.hodgecy_version,
            "git_commit": self.git_commit,
            "schema_version": self.schema_version.to_dict(),
            "input_hash": self.input_hash,
            "parameter_hash": self.parameter_hash,
            "backend": self.backend,
            "coefficient_ring": self.coefficient_ring,
            "environment_metadata": self.environment_metadata,
            "notes": self.notes,
            "superseded_by_run_id": self.superseded_by_run_id,
            "supersession_reason": self.supersession_reason,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CalculationRun":
        return cls(
            run_id=str(payload["run_id"]),
            geometry_id=str(payload["geometry_id"]),
            calculation_type=str(payload["calculation_type"]),
            started_at=str(payload["started_at"]),
            completed_at=payload.get("completed_at"),
            status=RunStatus(payload.get("status") or RunStatus.RUNNING.value),
            hodgecy_version=payload.get("hodgecy_version"),
            git_commit=payload.get("git_commit"),
            schema_version=SchemaVersion.from_dict(payload.get("schema_version", {"value": RESULT_STORE_SCHEMA_LABEL})),
            input_hash=payload.get("input_hash"),
            parameter_hash=payload.get("parameter_hash"),
            backend=payload.get("backend"),
            coefficient_ring=payload.get("coefficient_ring"),
            environment_metadata=dict(payload.get("environment_metadata") or {}),
            notes=payload.get("notes"),
            superseded_by_run_id=payload.get("superseded_by_run_id"),
            supersession_reason=payload.get("supersession_reason"),
        )


@dataclass(frozen=True, slots=True)
class InvariantRecord:
    invariant_id: str
    run_id: str
    geometry_id: str
    result_kind: ResultKind
    invariant_name: str
    value: Any
    value_type: str
    evidence_status: EvidenceStatus
    method: str | None = None
    provenance: str | None = None
    certificate_id: str | None = None
    notes: str | None = None
    content_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "invariant_id": self.invariant_id,
            "run_id": self.run_id,
            "geometry_id": self.geometry_id,
            "result_kind": self.result_kind.value,
            "invariant_name": self.invariant_name,
            "value": self.value,
            "value_type": self.value_type,
            "evidence_status": self.evidence_status.value,
            "method": self.method,
            "provenance": self.provenance,
            "certificate_id": self.certificate_id,
            "notes": self.notes,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "InvariantRecord":
        return cls(
            invariant_id=str(payload["invariant_id"]),
            run_id=str(payload["run_id"]),
            geometry_id=str(payload["geometry_id"]),
            result_kind=ResultKind(payload["result_kind"]),
            invariant_name=str(payload["invariant_name"]),
            value=payload.get("value"),
            value_type=str(payload.get("value_type") or "json"),
            evidence_status=EvidenceStatus(payload["evidence_status"]),
            method=payload.get("method"),
            provenance=payload.get("provenance"),
            certificate_id=payload.get("certificate_id"),
            notes=payload.get("notes"),
            content_hash=payload.get("content_hash"),
        )


@dataclass(frozen=True, slots=True)
class CertificateRecord:
    certificate_id: str
    certificate_type: str
    subject_type: str
    subject_id: str
    method: str
    evidence: dict[str, Any]
    generated_by_run_id: str | None = None
    content_hash: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "certificate_id": self.certificate_id,
            "certificate_type": self.certificate_type,
            "subject_type": self.subject_type,
            "subject_id": self.subject_id,
            "method": self.method,
            "evidence": self.evidence,
            "generated_by_run_id": self.generated_by_run_id,
            "content_hash": self.content_hash,
            "created_at": self.created_at,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CertificateRecord":
        return cls(
            certificate_id=str(payload["certificate_id"]),
            certificate_type=str(payload["certificate_type"]),
            subject_type=str(payload["subject_type"]),
            subject_id=str(payload["subject_id"]),
            method=str(payload["method"]),
            evidence=dict(payload.get("evidence") or {}),
            generated_by_run_id=payload.get("generated_by_run_id"),
            content_hash=payload.get("content_hash"),
            created_at=str(payload.get("created_at") or utc_now_iso()),
            notes=payload.get("notes"),
        )


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    artifact_id: str
    run_id: str
    geometry_id: str
    role: str
    artifact_type: str
    relative_path: str
    storage_format: str
    shape: tuple[int, ...] | None = None
    coefficient_ring: str | None = None
    content_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "run_id": self.run_id,
            "geometry_id": self.geometry_id,
            "role": self.role,
            "artifact_type": self.artifact_type,
            "relative_path": self.relative_path,
            "storage_format": self.storage_format,
            "shape": None if self.shape is None else list(self.shape),
            "coefficient_ring": self.coefficient_ring,
            "content_hash": self.content_hash,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ArtifactRecord":
        return cls(
            artifact_id=str(payload["artifact_id"]),
            run_id=str(payload["run_id"]),
            geometry_id=str(payload["geometry_id"]),
            role=str(payload["role"]),
            artifact_type=str(payload["artifact_type"]),
            relative_path=normalize_relative_path(str(payload["relative_path"])),
            storage_format=str(payload["storage_format"]),
            shape=None if payload.get("shape") is None else tuple(int(item) for item in payload["shape"]),
            coefficient_ring=payload.get("coefficient_ring"),
            content_hash=payload.get("content_hash"),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class SpectrumRecord:
    spectrum_id: str
    run_id: str
    geometry_id: str
    result_kind: ResultKind
    concrete_type: str
    schema_version: SchemaVersion
    evidence_status: EvidenceStatus
    payload: dict[str, Any]
    certificate_id: str | None = None
    content_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "spectrum_id": self.spectrum_id,
            "run_id": self.run_id,
            "geometry_id": self.geometry_id,
            "result_kind": self.result_kind.value,
            "concrete_type": self.concrete_type,
            "schema_version": self.schema_version.to_dict(),
            "evidence_status": self.evidence_status.value,
            "payload": self.payload,
            "certificate_id": self.certificate_id,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SpectrumRecord":
        return cls(
            spectrum_id=str(payload["spectrum_id"]),
            run_id=str(payload["run_id"]),
            geometry_id=str(payload["geometry_id"]),
            result_kind=ResultKind(payload["result_kind"]),
            concrete_type=str(payload["concrete_type"]),
            schema_version=SchemaVersion.from_dict(payload.get("schema_version", {"value": "v1"})),
            evidence_status=EvidenceStatus(payload["evidence_status"]),
            payload=dict(payload.get("payload") or {}),
            certificate_id=payload.get("certificate_id"),
            content_hash=payload.get("content_hash"),
        )


@dataclass(frozen=True, slots=True)
class ComparisonSetRecord:
    comparison_set_id: str
    display_name: str
    member_geometry_ids: tuple[str, ...]
    selection_criterion: str | None = None
    notes: str | None = None
    created_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        if len(self.member_geometry_ids) < 2:
            raise ValidationError("ComparisonSetRecord requires at least two geometries")

    def to_dict(self) -> dict[str, Any]:
        return {
            "comparison_set_id": self.comparison_set_id,
            "display_name": self.display_name,
            "member_geometry_ids": list(self.member_geometry_ids),
            "selection_criterion": self.selection_criterion,
            "notes": self.notes,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ComparisonSetRecord":
        return cls(
            comparison_set_id=str(payload["comparison_set_id"]),
            display_name=str(payload["display_name"]),
            member_geometry_ids=tuple(str(item) for item in payload.get("member_geometry_ids") or ()),
            selection_criterion=payload.get("selection_criterion"),
            notes=payload.get("notes"),
            created_at=str(payload.get("created_at") or utc_now_iso()),
        )


_SPECTRUM_TYPES = {
    "SourceAssemblySpectrum": (SourceAssemblySpectrum, ResultKind.SOURCE_ASSEMBLY),
    "ConifoldAtomSpectrum": (ConifoldAtomSpectrum, ResultKind.CONIFOLD_ATOM),
    "SmoothHodgeAtomSpectrum": (SmoothHodgeAtomSpectrum, ResultKind.SMOOTH_HODGE_ATOM),
}


class ResultStore:
    def __init__(self, path: str | Path, *, artifact_dir: str | Path | None = None) -> None:
        self.path = Path(path)
        self.artifact_dir = Path(artifact_dir) if artifact_dir is not None else self.path.parent / "artifacts"

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        with self._connect(require_initialized=False) as conn:
            current = self._schema_version(conn)
            if current > RESULT_STORE_SCHEMA_VERSION:
                raise ResultStoreSchemaVersionError(f"Unsupported future result-store schema version: {current}")
            if current == 0:
                self._create_schema(conn)
                conn.execute(f"PRAGMA user_version = {RESULT_STORE_SCHEMA_VERSION}")

    def schema_version(self) -> int:
        with self._connect() as conn:
            return self._schema_version(conn)

    def _connect(self, *, require_initialized: bool = True) -> sqlite3.Connection:
        if require_initialized and not self.path.exists():
            raise ResultStoreError(f"Result store does not exist: {self.path}")
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        version = self._schema_version(conn)
        if require_initialized:
            if version == 0:
                conn.close()
                raise ResultStoreSchemaVersionError("Result store has not been initialized")
            if version > RESULT_STORE_SCHEMA_VERSION:
                conn.close()
                raise ResultStoreSchemaVersionError(f"Unsupported future result-store schema version: {version}")
        return conn

    @staticmethod
    def _schema_version(conn: sqlite3.Connection) -> int:
        return int(conn.execute("PRAGMA user_version").fetchone()[0])

    @staticmethod
    def _create_schema(conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE geometries (
                geometry_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                geometry_type TEXT NOT NULL,
                source_dataset TEXT,
                source_dataset_version TEXT,
                source_entry_id TEXT,
                metadata_json TEXT NOT NULL,
                provenance TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX idx_geometries_type ON geometries(geometry_type);

            CREATE TABLE calculation_runs (
                run_id TEXT PRIMARY KEY,
                geometry_id TEXT NOT NULL REFERENCES geometries(geometry_id),
                calculation_type TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT NOT NULL,
                hodgecy_version TEXT,
                git_commit TEXT,
                schema_version_json TEXT NOT NULL,
                input_hash TEXT,
                parameter_hash TEXT,
                backend TEXT,
                coefficient_ring TEXT,
                environment_metadata_json TEXT NOT NULL,
                notes TEXT,
                superseded_by_run_id TEXT REFERENCES calculation_runs(run_id),
                supersession_reason TEXT
            );
            CREATE INDEX idx_runs_geometry ON calculation_runs(geometry_id);
            CREATE INDEX idx_runs_type ON calculation_runs(calculation_type);
            CREATE INDEX idx_runs_status ON calculation_runs(status);

            CREATE TABLE certificates (
                certificate_id TEXT PRIMARY KEY,
                certificate_type TEXT NOT NULL,
                subject_type TEXT NOT NULL,
                subject_id TEXT NOT NULL,
                method TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                generated_by_run_id TEXT REFERENCES calculation_runs(run_id),
                content_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                notes TEXT
            );
            CREATE INDEX idx_certificates_subject ON certificates(subject_type, subject_id);

            CREATE TABLE invariants (
                invariant_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES calculation_runs(run_id),
                geometry_id TEXT NOT NULL REFERENCES geometries(geometry_id),
                result_kind TEXT NOT NULL,
                invariant_name TEXT NOT NULL,
                value_json TEXT NOT NULL,
                value_type TEXT NOT NULL,
                evidence_status TEXT NOT NULL,
                method TEXT,
                provenance TEXT,
                certificate_id TEXT REFERENCES certificates(certificate_id),
                notes TEXT,
                content_hash TEXT NOT NULL
            );
            CREATE INDEX idx_invariants_geometry ON invariants(geometry_id);
            CREATE INDEX idx_invariants_name ON invariants(invariant_name);
            CREATE INDEX idx_invariants_kind ON invariants(result_kind);

            CREATE TABLE artifacts (
                artifact_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES calculation_runs(run_id),
                geometry_id TEXT NOT NULL REFERENCES geometries(geometry_id),
                role TEXT NOT NULL,
                artifact_type TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                storage_format TEXT NOT NULL,
                shape_json TEXT,
                coefficient_ring TEXT,
                content_hash TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            );
            CREATE INDEX idx_artifacts_geometry ON artifacts(geometry_id);
            CREATE INDEX idx_artifacts_role ON artifacts(role);

            CREATE TABLE spectra (
                spectrum_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES calculation_runs(run_id),
                geometry_id TEXT NOT NULL REFERENCES geometries(geometry_id),
                result_kind TEXT NOT NULL,
                concrete_type TEXT NOT NULL,
                schema_version_json TEXT NOT NULL,
                evidence_status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                certificate_id TEXT REFERENCES certificates(certificate_id),
                content_hash TEXT NOT NULL
            );
            CREATE INDEX idx_spectra_geometry ON spectra(geometry_id);
            CREATE INDEX idx_spectra_kind ON spectra(result_kind);

            CREATE TABLE comparison_sets (
                comparison_set_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                selection_criterion TEXT,
                notes TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE comparison_set_members (
                comparison_set_id TEXT NOT NULL REFERENCES comparison_sets(comparison_set_id),
                geometry_id TEXT NOT NULL REFERENCES geometries(geometry_id),
                member_order INTEGER NOT NULL,
                PRIMARY KEY (comparison_set_id, geometry_id)
            );
            CREATE INDEX idx_comparison_members_geometry ON comparison_set_members(geometry_id);
            """
        )

    def add_geometry(
        self,
        *,
        geometry_id: str | None = None,
        display_name: str,
        geometry_type: str,
        source_dataset: str | None = None,
        source_dataset_version: str | None = None,
        source_entry_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        provenance: str | None = None,
    ) -> GeometryRecord:
        geometry_id = geometry_id or GeometryRecord.deterministic_id(
            geometry_type=geometry_type,
            source_dataset=source_dataset,
            source_entry_id=source_entry_id,
            metadata=metadata,
        )
        record = GeometryRecord(geometry_id, display_name, geometry_type, source_dataset, source_dataset_version, source_entry_id, metadata or {}, provenance)
        with self._connect() as conn:
            existing = conn.execute("SELECT * FROM geometries WHERE geometry_id = ?", (geometry_id,)).fetchone()
            if existing is not None:
                existing_record = self._geometry_from_row(existing)
                existing_payload = existing_record.to_dict()
                record_payload = record.to_dict()
                existing_payload.pop("created_at", None)
                record_payload.pop("created_at", None)
                if existing_payload == record_payload:
                    return existing_record
                raise ImmutableRecordError(f"Geometry {geometry_id!r} already exists with different content")
            conn.execute(
                "INSERT INTO geometries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record.geometry_id,
                    record.display_name,
                    record.geometry_type,
                    record.source_dataset,
                    record.source_dataset_version,
                    record.source_entry_id,
                    _dumps(record.metadata),
                    record.provenance,
                    record.created_at,
                ),
            )
        return record

    def get_geometry(self, geometry_id: str) -> GeometryRecord:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM geometries WHERE geometry_id = ?", (geometry_id,)).fetchone()
        if row is None:
            raise RecordNotFoundError(geometry_id)
        return self._geometry_from_row(row)

    def list_geometries(self, *, geometry_type: str | None = None) -> tuple[GeometryRecord, ...]:
        with self._connect() as conn:
            if geometry_type is None:
                rows = conn.execute("SELECT * FROM geometries ORDER BY geometry_id").fetchall()
            else:
                rows = conn.execute("SELECT * FROM geometries WHERE geometry_type = ? ORDER BY geometry_id", (geometry_type,)).fetchall()
        return tuple(self._geometry_from_row(row) for row in rows)

    def begin_run(
        self,
        *,
        geometry_id: str,
        calculation_type: str,
        input_metadata: Any | None = None,
        parameters: Any | None = None,
        backend: str | None = None,
        coefficient_ring: str | None = None,
        environment_metadata: dict[str, Any] | None = None,
        git_commit: str | None = None,
        notes: str | None = None,
    ) -> CalculationRun:
        self.get_geometry(geometry_id)
        run = CalculationRun(
            run_id=_id("run"),
            geometry_id=geometry_id,
            calculation_type=calculation_type,
            started_at=utc_now_iso(),
            git_commit=git_commit if git_commit is not None else _detect_git_commit(self.path.parent),
            input_hash=None if input_metadata is None else normalized_content_hash(input_metadata),
            parameter_hash=None if parameters is None else normalized_content_hash(parameters),
            backend=backend,
            coefficient_ring=coefficient_ring,
            environment_metadata=environment_metadata or {},
            notes=notes,
        )
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO calculation_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                self._run_params(run),
            )
        return run

    def complete_run(self, run_id: str, *, notes: str | None = None) -> CalculationRun:
        return self._finish_run(run_id, RunStatus.COMPLETED, notes=notes)

    def fail_run(self, run_id: str, *, notes: str | None = None) -> CalculationRun:
        return self._finish_run(run_id, RunStatus.FAILED, notes=notes)

    def supersede_run(self, run_id: str, *, superseded_by_run_id: str, reason: str) -> CalculationRun:
        self.get_run(superseded_by_run_id)
        run = self.get_run(run_id)
        if run.status is RunStatus.SUPERSEDED:
            raise ImmutableRecordError(f"Run {run_id!r} is already superseded")
        with self._connect() as conn:
            conn.execute(
                "UPDATE calculation_runs SET status = ?, superseded_by_run_id = ?, supersession_reason = ? WHERE run_id = ?",
                (RunStatus.SUPERSEDED.value, superseded_by_run_id, reason, run_id),
            )
        return self.get_run(run_id)

    def _finish_run(self, run_id: str, status: RunStatus, *, notes: str | None) -> CalculationRun:
        run = self.get_run(run_id)
        if run.status is not RunStatus.RUNNING:
            raise ImmutableRecordError(f"Run {run_id!r} is already {run.status.value}")
        with self._connect() as conn:
            conn.execute(
                "UPDATE calculation_runs SET status = ?, completed_at = ?, notes = COALESCE(?, notes) WHERE run_id = ?",
                (status.value, utc_now_iso(), notes, run_id),
            )
        return self.get_run(run_id)

    def get_run(self, run_id: str) -> CalculationRun:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM calculation_runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise RecordNotFoundError(run_id)
        return self._run_from_row(row)

    def get_runs(self, *, geometry_id: str | None = None, calculation_type: str | None = None) -> tuple[CalculationRun, ...]:
        clauses = []
        params: list[Any] = []
        if geometry_id is not None:
            clauses.append("geometry_id = ?")
            params.append(geometry_id)
        if calculation_type is not None:
            clauses.append("calculation_type = ?")
            params.append(calculation_type)
        sql = "SELECT * FROM calculation_runs"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY started_at, run_id"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return tuple(self._run_from_row(row) for row in rows)

    def record_invariant(
        self,
        *,
        run_id: str,
        name: str,
        value: Any,
        result_kind: ResultKind,
        evidence_status: EvidenceStatus,
        value_type: str | None = None,
        method: str | None = None,
        provenance: str | None = None,
        certificate_id: str | None = None,
        notes: str | None = None,
    ) -> InvariantRecord:
        run = self.get_run(run_id)
        if certificate_id is not None:
            self.get_certificate(certificate_id)
        value_type = value_type or ("unknown" if value is None else type(value).__name__)
        payload = {
            "run_id": run_id,
            "geometry_id": run.geometry_id,
            "result_kind": result_kind.value,
            "invariant_name": name,
            "value": value,
            "value_type": value_type,
            "evidence_status": evidence_status.value,
            "method": method,
            "provenance": provenance,
            "certificate_id": certificate_id,
            "notes": notes,
        }
        content_hash = normalized_content_hash(payload)
        record = InvariantRecord(_id("inv"), run_id, run.geometry_id, result_kind, name, value, value_type, evidence_status, method, provenance, certificate_id, notes, content_hash)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO invariants VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record.invariant_id,
                    record.run_id,
                    record.geometry_id,
                    record.result_kind.value,
                    record.invariant_name,
                    _dumps(record.value),
                    record.value_type,
                    record.evidence_status.value,
                    record.method,
                    record.provenance,
                    record.certificate_id,
                    record.notes,
                    record.content_hash,
                ),
            )
        return record

    def get_invariants(
        self,
        *,
        geometry_id: str | None = None,
        name: str | None = None,
        result_kind: ResultKind | None = None,
    ) -> tuple[InvariantRecord, ...]:
        clauses = []
        params: list[Any] = []
        if geometry_id is not None:
            clauses.append("geometry_id = ?")
            params.append(geometry_id)
        if name is not None:
            clauses.append("invariant_name = ?")
            params.append(name)
        if result_kind is not None:
            clauses.append("result_kind = ?")
            params.append(result_kind.value)
        sql = "SELECT * FROM invariants"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY invariant_name, invariant_id"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return tuple(self._invariant_from_row(row) for row in rows)

    def record_certificate(
        self,
        *,
        certificate_type: str,
        subject_type: str,
        subject_id: str,
        method: str,
        evidence: dict[str, Any],
        generated_by_run_id: str | None = None,
        notes: str | None = None,
    ) -> CertificateRecord:
        if generated_by_run_id is not None:
            self.get_run(generated_by_run_id)
        payload = {
            "certificate_type": certificate_type,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "method": method,
            "evidence": evidence,
            "generated_by_run_id": generated_by_run_id,
            "notes": notes,
        }
        content_hash = normalized_content_hash(payload)
        record = CertificateRecord(_id("cert", payload), certificate_type, subject_type, subject_id, method, evidence, generated_by_run_id, content_hash, notes=notes)
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO certificates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record.certificate_id,
                    record.certificate_type,
                    record.subject_type,
                    record.subject_id,
                    record.method,
                    _dumps(record.evidence),
                    record.generated_by_run_id,
                    record.content_hash,
                    record.created_at,
                    record.notes,
                ),
            )
        return self.get_certificate(record.certificate_id)

    def get_certificate(self, certificate_id: str) -> CertificateRecord:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM certificates WHERE certificate_id = ?", (certificate_id,)).fetchone()
        if row is None:
            raise RecordNotFoundError(certificate_id)
        return self._certificate_from_row(row)

    def attach_artifact(
        self,
        *,
        run_id: str,
        role: str,
        artifact_type: str,
        source_path: str | Path,
        storage_format: str,
        shape: Iterable[int] | None = None,
        coefficient_ring: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRecord:
        run = self.get_run(run_id)
        source = Path(source_path)
        content_hash = file_sha256(source)
        suffix = source.suffix
        stored_name = f"{content_hash}{suffix}"
        relative_path = normalize_relative_path(stored_name)
        target = self.artifact_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(source.read_bytes())
        record = ArtifactRecord(
            artifact_id=_id("art", {"run_id": run_id, "role": role, "content_hash": content_hash}),
            run_id=run_id,
            geometry_id=run.geometry_id,
            role=role,
            artifact_type=artifact_type,
            relative_path=relative_path,
            storage_format=storage_format,
            shape=None if shape is None else tuple(int(item) for item in shape),
            coefficient_ring=coefficient_ring,
            content_hash=content_hash,
            metadata=metadata or {},
        )
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO artifacts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record.artifact_id,
                    record.run_id,
                    record.geometry_id,
                    record.role,
                    record.artifact_type,
                    record.relative_path,
                    record.storage_format,
                    None if record.shape is None else _dumps(list(record.shape)),
                    record.coefficient_ring,
                    record.content_hash,
                    _dumps(record.metadata),
                ),
            )
        return record

    def get_artifact(self, artifact_id: str, *, validate_integrity: bool = False) -> ArtifactRecord:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM artifacts WHERE artifact_id = ?", (artifact_id,)).fetchone()
        if row is None:
            raise RecordNotFoundError(artifact_id)
        record = self._artifact_from_row(row)
        if validate_integrity:
            path = self.artifact_dir / record.relative_path
            actual = file_sha256(path)
            if actual != record.content_hash:
                raise ArtifactIntegrityError(f"Artifact {artifact_id!r} hash mismatch: expected {record.content_hash}, got {actual}")
        return record

    def record_spectrum(self, *, run_id: str, spectrum: SourceAssemblySpectrum | ConifoldAtomSpectrum | SmoothHodgeAtomSpectrum, certificate_id: str | None = None) -> SpectrumRecord:
        run = self.get_run(run_id)
        if certificate_id is not None:
            self.get_certificate(certificate_id)
        concrete_type = type(spectrum).__name__
        if concrete_type not in _SPECTRUM_TYPES:
            raise ValidationError(f"Unsupported spectrum type: {concrete_type}")
        _, expected_kind = _SPECTRUM_TYPES[concrete_type]
        if spectrum.kind is not expected_kind:
            raise ValidationError(f"Invalid spectrum discriminator: {concrete_type} cannot carry {spectrum.kind.value}")
        payload = spectrum.to_dict()
        content_hash = normalized_content_hash({"type": concrete_type, "kind": spectrum.kind.value, "payload": payload, "certificate_id": certificate_id})
        record = SpectrumRecord(
            spectrum_id=_id("spec"),
            run_id=run_id,
            geometry_id=run.geometry_id,
            result_kind=spectrum.kind,
            concrete_type=concrete_type,
            schema_version=spectrum.metadata.schema_version,
            evidence_status=spectrum.metadata.evidence_status,
            payload=payload,
            certificate_id=certificate_id,
            content_hash=content_hash,
        )
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO spectra VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record.spectrum_id,
                    record.run_id,
                    record.geometry_id,
                    record.result_kind.value,
                    record.concrete_type,
                    _dumps(record.schema_version.to_dict()),
                    record.evidence_status.value,
                    _dumps(record.payload),
                    record.certificate_id,
                    record.content_hash,
                ),
            )
        return record

    def get_spectrum_record(self, spectrum_id: str) -> SpectrumRecord:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM spectra WHERE spectrum_id = ?", (spectrum_id,)).fetchone()
        if row is None:
            raise RecordNotFoundError(spectrum_id)
        return self._spectrum_from_row(row)

    def get_spectrum(self, spectrum_id: str) -> SourceAssemblySpectrum | ConifoldAtomSpectrum | SmoothHodgeAtomSpectrum:
        record = self.get_spectrum_record(spectrum_id)
        return self._spectrum_object(record)

    def get_spectra(self, *, result_kind: ResultKind | None = None, geometry_id: str | None = None) -> tuple[SpectrumRecord, ...]:
        clauses = []
        params: list[Any] = []
        if result_kind is not None:
            clauses.append("result_kind = ?")
            params.append(result_kind.value)
        if geometry_id is not None:
            clauses.append("geometry_id = ?")
            params.append(geometry_id)
        sql = "SELECT * FROM spectra"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY spectrum_id"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return tuple(self._spectrum_from_row(row) for row in rows)

    def create_comparison_set(
        self,
        *,
        display_name: str,
        member_geometry_ids: Iterable[str],
        comparison_set_id: str | None = None,
        selection_criterion: str | None = None,
        notes: str | None = None,
    ) -> ComparisonSetRecord:
        members = tuple(str(item) for item in member_geometry_ids)
        if len(members) < 2:
            raise ValidationError("comparison sets require at least two geometries")
        for geometry_id in members:
            self.get_geometry(geometry_id)
        comparison_set_id = comparison_set_id or _id("cmp", {"display_name": display_name, "members": members, "selection_criterion": selection_criterion})
        record = ComparisonSetRecord(comparison_set_id, display_name, members, selection_criterion, notes)
        with self._connect() as conn:
            conn.execute("INSERT INTO comparison_sets VALUES (?, ?, ?, ?, ?)", (record.comparison_set_id, record.display_name, record.selection_criterion, record.notes, record.created_at))
            conn.executemany(
                "INSERT INTO comparison_set_members VALUES (?, ?, ?)",
                [(record.comparison_set_id, geometry_id, index) for index, geometry_id in enumerate(members)],
            )
        return record

    def get_comparison_set(self, comparison_set_id: str) -> ComparisonSetRecord:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM comparison_sets WHERE comparison_set_id = ?", (comparison_set_id,)).fetchone()
            members = conn.execute(
                "SELECT geometry_id FROM comparison_set_members WHERE comparison_set_id = ? ORDER BY member_order",
                (comparison_set_id,),
            ).fetchall()
        if row is None:
            raise RecordNotFoundError(comparison_set_id)
        return ComparisonSetRecord(
            comparison_set_id=str(row["comparison_set_id"]),
            display_name=str(row["display_name"]),
            member_geometry_ids=tuple(str(member["geometry_id"]) for member in members),
            selection_criterion=row["selection_criterion"],
            notes=row["notes"],
            created_at=str(row["created_at"]),
        )

    def export_record(self, record_type: RecordType | str, record: Any) -> dict[str, Any]:
        record_type = RecordType(record_type)
        return {"schema_version": RESULT_STORE_SCHEMA_LABEL, "record_type": record_type.value, "payload": record.to_dict()}

    def export_record_json(self, record_type: RecordType | str, record: Any) -> str:
        return canonical_json(self.export_record(record_type, record))

    def import_record(self, envelope: dict[str, Any] | str) -> Any:
        if isinstance(envelope, str):
            envelope = json.loads(envelope)
        if envelope.get("schema_version") != RESULT_STORE_SCHEMA_LABEL:
            raise ResultStoreSchemaVersionError(f"Unsupported record envelope schema: {envelope.get('schema_version')!r}")
        record_type = RecordType(envelope["record_type"])
        payload = dict(envelope.get("payload") or {})
        if record_type is RecordType.GEOMETRY:
            record = GeometryRecord.from_dict(payload)
            return self.add_geometry(**{key: value for key, value in record.to_dict().items() if key != "created_at"})
        if record_type is RecordType.CALCULATION_RUN:
            return CalculationRun.from_dict(payload)
        if record_type is RecordType.INVARIANT:
            return InvariantRecord.from_dict(payload)
        if record_type is RecordType.CERTIFICATE:
            return CertificateRecord.from_dict(payload)
        if record_type is RecordType.ARTIFACT:
            return ArtifactRecord.from_dict(payload)
        if record_type is RecordType.SPECTRUM:
            return SpectrumRecord.from_dict(payload)
        if record_type is RecordType.COMPARISON_SET:
            return ComparisonSetRecord.from_dict(payload)
        raise ResultStoreError(f"Unsupported record type: {record_type}")

    @staticmethod
    def _spectrum_object(record: SpectrumRecord) -> SourceAssemblySpectrum | ConifoldAtomSpectrum | SmoothHodgeAtomSpectrum:
        if record.concrete_type not in _SPECTRUM_TYPES:
            raise ValidationError(f"Unknown spectrum concrete type: {record.concrete_type}")
        cls, expected_kind = _SPECTRUM_TYPES[record.concrete_type]
        if record.result_kind is not expected_kind:
            raise ValidationError(f"Spectrum row has invalid type/kind pair: {record.concrete_type} with {record.result_kind.value}")
        metadata = ResultMetadata.from_dict(record.payload["metadata"])
        if metadata.result_kind is not expected_kind:
            raise ValidationError(f"Spectrum payload has invalid result kind: {metadata.result_kind.value}")
        return cls.from_dict(record.payload)  # type: ignore[return-value]

    @staticmethod
    def _geometry_from_row(row: sqlite3.Row) -> GeometryRecord:
        return GeometryRecord(
            geometry_id=str(row["geometry_id"]),
            display_name=str(row["display_name"]),
            geometry_type=str(row["geometry_type"]),
            source_dataset=row["source_dataset"],
            source_dataset_version=row["source_dataset_version"],
            source_entry_id=row["source_entry_id"],
            metadata=dict(_loads(row["metadata_json"], {})),
            provenance=row["provenance"],
            created_at=str(row["created_at"]),
        )

    @staticmethod
    def _run_params(run: CalculationRun) -> tuple[Any, ...]:
        return (
            run.run_id,
            run.geometry_id,
            run.calculation_type,
            run.started_at,
            run.completed_at,
            run.status.value,
            run.hodgecy_version,
            run.git_commit,
            _dumps(run.schema_version.to_dict()),
            run.input_hash,
            run.parameter_hash,
            run.backend,
            run.coefficient_ring,
            _dumps(run.environment_metadata),
            run.notes,
            run.superseded_by_run_id,
            run.supersession_reason,
        )

    @staticmethod
    def _run_from_row(row: sqlite3.Row) -> CalculationRun:
        return CalculationRun(
            run_id=str(row["run_id"]),
            geometry_id=str(row["geometry_id"]),
            calculation_type=str(row["calculation_type"]),
            started_at=str(row["started_at"]),
            completed_at=row["completed_at"],
            status=RunStatus(row["status"]),
            hodgecy_version=row["hodgecy_version"],
            git_commit=row["git_commit"],
            schema_version=SchemaVersion.from_dict(_loads(row["schema_version_json"], {"value": RESULT_STORE_SCHEMA_LABEL})),
            input_hash=row["input_hash"],
            parameter_hash=row["parameter_hash"],
            backend=row["backend"],
            coefficient_ring=row["coefficient_ring"],
            environment_metadata=dict(_loads(row["environment_metadata_json"], {})),
            notes=row["notes"],
            superseded_by_run_id=row["superseded_by_run_id"],
            supersession_reason=row["supersession_reason"],
        )

    @staticmethod
    def _invariant_from_row(row: sqlite3.Row) -> InvariantRecord:
        return InvariantRecord(
            invariant_id=str(row["invariant_id"]),
            run_id=str(row["run_id"]),
            geometry_id=str(row["geometry_id"]),
            result_kind=ResultKind(row["result_kind"]),
            invariant_name=str(row["invariant_name"]),
            value=_loads(row["value_json"], None),
            value_type=str(row["value_type"]),
            evidence_status=EvidenceStatus(row["evidence_status"]),
            method=row["method"],
            provenance=row["provenance"],
            certificate_id=row["certificate_id"],
            notes=row["notes"],
            content_hash=row["content_hash"],
        )

    @staticmethod
    def _certificate_from_row(row: sqlite3.Row) -> CertificateRecord:
        return CertificateRecord(
            certificate_id=str(row["certificate_id"]),
            certificate_type=str(row["certificate_type"]),
            subject_type=str(row["subject_type"]),
            subject_id=str(row["subject_id"]),
            method=str(row["method"]),
            evidence=dict(_loads(row["evidence_json"], {})),
            generated_by_run_id=row["generated_by_run_id"],
            content_hash=row["content_hash"],
            created_at=str(row["created_at"]),
            notes=row["notes"],
        )

    @staticmethod
    def _artifact_from_row(row: sqlite3.Row) -> ArtifactRecord:
        shape = _loads(row["shape_json"], None)
        return ArtifactRecord(
            artifact_id=str(row["artifact_id"]),
            run_id=str(row["run_id"]),
            geometry_id=str(row["geometry_id"]),
            role=str(row["role"]),
            artifact_type=str(row["artifact_type"]),
            relative_path=str(row["relative_path"]),
            storage_format=str(row["storage_format"]),
            shape=None if shape is None else tuple(int(item) for item in shape),
            coefficient_ring=row["coefficient_ring"],
            content_hash=row["content_hash"],
            metadata=dict(_loads(row["metadata_json"], {})),
        )

    @staticmethod
    def _spectrum_from_row(row: sqlite3.Row) -> SpectrumRecord:
        return SpectrumRecord(
            spectrum_id=str(row["spectrum_id"]),
            run_id=str(row["run_id"]),
            geometry_id=str(row["geometry_id"]),
            result_kind=ResultKind(row["result_kind"]),
            concrete_type=str(row["concrete_type"]),
            schema_version=SchemaVersion.from_dict(_loads(row["schema_version_json"], {"value": "v1"})),
            evidence_status=EvidenceStatus(row["evidence_status"]),
            payload=dict(_loads(row["payload_json"], {})),
            certificate_id=row["certificate_id"],
            content_hash=row["content_hash"],
        )
