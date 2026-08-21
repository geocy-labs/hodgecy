from __future__ import annotations

import json
from pathlib import Path

import pytest

from hodgecy.certificates import (
    ArtifactClass,
    CertificatePurpose,
    CertificateSubject,
    EnvironmentCapture,
    build_certificate,
    certificate_summary_rows,
    json_payload,
    legacy_release_summary,
    records_from_certificate_dirs,
    register_certificate_summary_parquet_source,
    registry_record,
    verify_certificate,
    verify_legacy_release_checksums,
)
from hodgecy.core import AcquisitionStatus, ClaimLevel, ConstructionFamily, DatasetDescriptor, HodgeCYID, RedistributionStatus
from hodgecy.query import QuerySpec
from hodgecy.reporting import certificate_status_report, legacy_release_status_row
from hodgecy.storage import DatasetInstance, TableKind, open_catalog


REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = REPO_ROOT / "release" / "hodgecy-v0.2.0"


def _environment() -> EnvironmentCapture:
    return EnvironmentCapture(
        python_version="3.test",
        platform="pytest",
        hodgecy_version="0.2.0",
        hodgecy_commit="abc123",
        git_dirty=False,
        dependencies={"sympy": "fixture"},
        backends={"python": "CPython"},
    )


def _subject() -> CertificateSubject:
    return CertificateSubject(
        subject_type="source_ingest",
        object_id=HodgeCYID.source_record("fixture_dataset", "row-1"),
        dataset_id=HodgeCYID.dataset("fixture_dataset"),
        source_instance_id="fixture_dataset_v1",
        source_revision="fixture-rev",
        source_checksum="0" * 64,
        payload_ref="payload/source.json",
        basis_labels=("J1", "J2"),
        relationship_evidence=("SOURCE_EXPLICIT",),
        claim_level=ClaimLevel.SOURCE_REPORTED,
    )


def _build(root: Path):
    return build_certificate(
        root,
        purpose=CertificatePurpose.SOURCE_INGEST,
        subjects=(_subject(),),
        payloads={"payload/source.json": json_payload({"source_record_id": "row-1", "value": 7})},
        environment=_environment(),
        generated_summaries={"row_count": 1},
        metadata={"fixture": True},
        created_utc="2026-08-21T00:00:00+00:00",
    )


def test_certificate_build_verify_and_identity_are_deterministic(tmp_path) -> None:
    manifest = _build(tmp_path)
    second = _build(tmp_path)
    certificate_dir = tmp_path / manifest.local_id
    verification = verify_certificate(certificate_dir)

    assert manifest.certificate_id == second.certificate_id
    assert manifest.artifact_class is ArtifactClass.CERTIFIED
    assert manifest.schema_version.value == "certificate.v1"
    assert verification.ok is True
    assert verification.require_ok().certificate_id == manifest.certificate_id
    assert (certificate_dir / "certificate.json").exists()
    assert (certificate_dir / "payload" / "source.json").exists()


def test_certificate_verifier_reports_checksum_schema_and_missing_payload(tmp_path) -> None:
    manifest = _build(tmp_path)
    certificate_dir = tmp_path / manifest.local_id
    payload_path = certificate_dir / "payload" / "source.json"
    payload_path.write_text("tampered\n", encoding="utf-8")
    issues = verify_certificate(certificate_dir).issues
    assert any(issue.code == "payload_checksum_mismatch" for issue in issues)

    payload_path.unlink()
    issues = verify_certificate(certificate_dir).issues
    assert any(issue.code == "missing_payload" for issue in issues)

    manifest_path = certificate_dir / "certificate.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["schema_version"] = {"value": "certificate.v999"}
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    issues = verify_certificate(certificate_dir).issues
    assert any(issue.code == "unsupported_schema" for issue in issues)


def test_certificate_builder_detects_conflicting_existing_identity(tmp_path) -> None:
    manifest = _build(tmp_path)
    with pytest.raises(FileExistsError):
        build_certificate(
            tmp_path,
            purpose=CertificatePurpose.SOURCE_INGEST,
            subjects=(_subject(),),
            payloads={"payload/source.json": json_payload({"source_record_id": "row-1", "value": 7})},
            environment=_environment(),
            generated_summaries={"row_count": 1},
            metadata={"fixture": "changed metadata"},
            created_utc=manifest.created_utc,
        )


def test_certificate_registry_rows_reporting_and_catalog_registration(tmp_path) -> None:
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")

    manifest = _build(tmp_path / "certificates")
    records = records_from_certificate_dirs(tmp_path / "certificates")
    record = registry_record(manifest, relative_path=manifest.local_id)
    rows = certificate_summary_rows(records)
    report = certificate_status_report(records)

    assert records[0].certificate_id == record.certificate_id
    assert rows[0]["purpose"] == "source_ingest"
    assert rows[0]["datasets"] == ["fixture_dataset"]
    assert report["certificate_count"] == 1
    assert report["by_purpose"] == {"source_ingest": 1}

    raw = tmp_path / "raw" / "certificates"
    raw.mkdir(parents=True)
    pq.write_table(pa.Table.from_pylist(rows), raw / "registry.parquet")
    catalog = open_catalog(tmp_path, create=True)
    descriptor = catalog.register_dataset(DatasetDescriptor(
        dataset_id=HodgeCYID.dataset("certificate_registry_fixture"),
        name="Certificate registry fixture",
        construction_family=ConstructionFamily.known("certificate_registry"),
        acquisition_status=AcquisitionStatus.COMPLETE_COLUMNAR,
        redistribution_status=RedistributionStatus.REDISTRIBUTABLE,
    ))
    catalog.register_instance(DatasetInstance(
        instance_id="certificate_registry_fixture_v1",
        dataset_id=descriptor.dataset_id,
        source_version="fixture-v1",
        acquisition_status=AcquisitionStatus.COMPLETE_COLUMNAR,
        redistribution_status=RedistributionStatus.REDISTRIBUTABLE,
        record_count=1,
    ))
    register_certificate_summary_parquet_source(
        catalog,
        columnar_id="certificate_registry_columnar",
        instance_id="certificate_registry_fixture_v1",
        source_id="certificate_registry_parquet",
        relative_path="raw/certificates/registry.parquet",
    )
    table = catalog.list_tables(TableKind.DERIVED)[0]
    assert table.metadata["artifact_kind"] == "certificate_registry"
    result = catalog.query(QuerySpec(table="certificate_registry"))
    assert result.count() == 1


def test_legacy_v0_2_0_release_compatibility_reader_does_not_mutate_release() -> None:
    before = (RELEASE_DIR / "MANIFEST.json").read_bytes()
    summary = legacy_release_summary(RELEASE_DIR)
    issues = verify_legacy_release_checksums(RELEASE_DIR)
    row = legacy_release_status_row(summary)
    after = (RELEASE_DIR / "MANIFEST.json").read_bytes()

    assert all(issue.code in {"legacy_checksum_mismatch", "missing_legacy_payload"} for issue in issues)
    assert not any("theorem_summary.json" in (issue.path or "") for issue in issues)
    assert summary.theorem_arrangements == ("84", "84a", "239", "240", "241")
    assert summary.file_count > 0
    assert row["purpose"] == "legacy_theorem_result"
    assert before == after
