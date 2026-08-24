from __future__ import annotations

import json
import sqlite3

import pytest

from hodgecy.core import (
    ConifoldAtomSpectrum,
    EvidenceStatus,
    ResultKind,
    ResultMetadata,
    SmoothHodgeAtomSpectrum,
    SourceAssemblySpectrum,
    ValidationError,
)
from hodgecy.storage import (
    ArtifactIntegrityError,
    ImmutableRecordError,
    RecordNotFoundError,
    RecordType,
    ResultStore,
    ResultStoreSchemaVersionError,
    RunStatus,
    normalized_content_hash,
)


def store(tmp_path) -> ResultStore:
    result = ResultStore(tmp_path / "results" / "hodgecy-results.sqlite")
    result.initialize()
    return result


def add_geometry(result: ResultStore, geometry_id: str = "synthetic-A"):
    return result.add_geometry(
        geometry_id=geometry_id,
        display_name=f"Synthetic geometry {geometry_id}",
        geometry_type="synthetic_fixture",
        source_dataset="unit-test",
        source_dataset_version="v1",
        source_entry_id=geometry_id,
        metadata={"dimension": "synthetic"},
        provenance="unit-test",
    )


def begin_run(result: ResultStore, geometry_id: str = "synthetic-A"):
    add_geometry(result, geometry_id)
    return result.begin_run(
        geometry_id=geometry_id,
        calculation_type="source_assembly",
        input_metadata={"geometry": geometry_id},
        parameters={"field": "Q"},
        backend="python",
        coefficient_ring="Q",
        environment_metadata={"test": True},
        git_commit="abc123",
    )


def test_database_creation_schema_version_tables_and_foreign_keys(tmp_path) -> None:
    result = store(tmp_path)
    assert result.schema_version() == 1
    with result._connect() as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {
        "geometries",
        "calculation_runs",
        "invariants",
        "certificates",
        "artifacts",
        "spectra",
        "comparison_sets",
        "comparison_set_members",
    } <= tables


def test_future_schema_version_fails_clearly(tmp_path) -> None:
    path = tmp_path / "future.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA user_version = 999")
    conn.close()
    with pytest.raises(ResultStoreSchemaVersionError):
        ResultStore(path).initialize()


def test_geometry_lifecycle_duplicate_and_type_query(tmp_path) -> None:
    result = store(tmp_path)
    geom = add_geometry(result)
    assert result.get_geometry("synthetic-A") == geom
    assert result.add_geometry(**{key: value for key, value in geom.to_dict().items() if key != "created_at"}) == geom
    with pytest.raises(ImmutableRecordError):
        result.add_geometry(geometry_id="synthetic-A", display_name="Different", geometry_type="synthetic_fixture")
    assert result.list_geometries(geometry_type="synthetic_fixture") == (geom,)


def test_calculation_runs_complete_fail_and_supersede_without_overwrite(tmp_path) -> None:
    result = store(tmp_path)
    run_a = begin_run(result)
    completed = result.complete_run(run_a.run_id)
    assert completed.status is RunStatus.COMPLETED
    with pytest.raises(ImmutableRecordError):
        result.complete_run(run_a.run_id)

    run_b = result.begin_run(geometry_id="synthetic-A", calculation_type="source_assembly")
    failed = result.fail_run(run_b.run_id, notes="synthetic failure")
    assert failed.status is RunStatus.FAILED

    run_c = result.begin_run(geometry_id="synthetic-A", calculation_type="source_assembly")
    superseded = result.supersede_run(run_a.run_id, superseded_by_run_id=run_c.run_id, reason="corrected fixture")
    assert superseded.status is RunStatus.SUPERSEDED
    assert superseded.superseded_by_run_id == run_c.run_id
    assert result.get_run(run_a.run_id).run_id == run_a.run_id
    assert len(result.get_runs(geometry_id="synthetic-A", calculation_type="source_assembly")) == 3


def test_invariants_preserve_value_types_status_unknown_and_certificate_link(tmp_path) -> None:
    result = store(tmp_path)
    run = begin_run(result)
    cert = result.record_certificate(
        certificate_type="matrix_rank",
        subject_type="invariant",
        subject_id="source_rank",
        method="synthetic verifier",
        evidence={"rank": 8},
        generated_by_run_id=run.run_id,
    )
    result.record_invariant(run_id=run.run_id, name="source_rank", value=8, result_kind=ResultKind.SOURCE_ASSEMBLY, evidence_status=EvidenceStatus.COMPUTED)
    result.record_invariant(run_id=run.run_id, name="label", value="alpha", result_kind=ResultKind.SOURCE_ASSEMBLY, evidence_status=EvidenceStatus.IMPORTED)
    result.record_invariant(run_id=run.run_id, name="rational", value={"num": 1, "den": 3}, result_kind=ResultKind.SOURCE_ASSEMBLY, evidence_status=EvidenceStatus.ASSUMED)
    result.record_invariant(
        run_id=run.run_id,
        name="node_relation_snf",
        value=None,
        result_kind=ResultKind.NODE_RELATION,
        evidence_status=EvidenceStatus.UNKNOWN,
        certificate_id=cert.certificate_id,
        notes="not computed",
    )

    by_name = {item.invariant_name: item for item in result.get_invariants(geometry_id="synthetic-A")}
    assert by_name["source_rank"].value == 8
    assert by_name["label"].value == "alpha"
    assert by_name["rational"].value == {"num": 1, "den": 3}
    assert by_name["node_relation_snf"].value is None
    assert by_name["node_relation_snf"].evidence_status is EvidenceStatus.UNKNOWN
    assert by_name["node_relation_snf"].certificate_id == cert.certificate_id


def test_certificate_round_trip(tmp_path) -> None:
    result = store(tmp_path)
    run = begin_run(result)
    cert = result.record_certificate(
        certificate_type="ordinary_double_point",
        subject_type="geometry",
        subject_id="synthetic-A",
        method="external fixture",
        evidence={"verified": True},
        generated_by_run_id=run.run_id,
        notes="certificate metadata only",
    )
    restored = result.get_certificate(cert.certificate_id)
    assert restored == cert
    assert restored.content_hash == normalized_content_hash({
        "certificate_type": "ordinary_double_point",
        "subject_type": "geometry",
        "subject_id": "synthetic-A",
        "method": "external fixture",
        "evidence": {"verified": True},
        "generated_by_run_id": run.run_id,
        "notes": "certificate metadata only",
    })


def test_artifact_attach_hash_metadata_and_integrity(tmp_path) -> None:
    result = store(tmp_path)
    run = begin_run(result)
    source = tmp_path / "matrix.json"
    source.write_text(json.dumps({"rows": [[1, 0], [0, 1]]}), encoding="utf-8")
    artifact = result.attach_artifact(
        run_id=run.run_id,
        role="source_assembly_matrix",
        artifact_type="matrix",
        source_path=source,
        storage_format="json",
        shape=(2, 2),
        coefficient_ring="Z",
        metadata={"basis": "synthetic"},
    )
    restored = result.get_artifact(artifact.artifact_id, validate_integrity=True)
    assert restored.shape == (2, 2)
    assert restored.metadata["basis"] == "synthetic"
    stored_path = result.artifact_dir / restored.relative_path
    stored_path.write_text("tampered", encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError):
        result.get_artifact(artifact.artifact_id, validate_integrity=True)


def spectrum(kind: ResultKind):
    metadata = ResultMetadata("synthetic-A", kind, evidence_status=EvidenceStatus.COMPUTED)
    if kind is ResultKind.SOURCE_ASSEMBLY:
        return SourceAssemblySpectrum(metadata, payload={"terms": ["source"]})
    if kind is ResultKind.CONIFOLD_ATOM:
        return ConifoldAtomSpectrum(metadata, payload={"terms": ["conifold"]})
    return SmoothHodgeAtomSpectrum(metadata, payload={"terms": ["smooth"]})


def test_spectrum_round_trips_preserve_concrete_types_and_status(tmp_path) -> None:
    result = store(tmp_path)
    run = begin_run(result)
    records = [
        result.record_spectrum(run_id=run.run_id, spectrum=spectrum(ResultKind.SOURCE_ASSEMBLY)),
        result.record_spectrum(run_id=run.run_id, spectrum=spectrum(ResultKind.CONIFOLD_ATOM)),
        result.record_spectrum(run_id=run.run_id, spectrum=spectrum(ResultKind.SMOOTH_HODGE_ATOM)),
    ]

    restored = [result.get_spectrum(record.spectrum_id) for record in records]
    assert type(restored[0]) is SourceAssemblySpectrum
    assert type(restored[1]) is ConifoldAtomSpectrum
    assert type(restored[2]) is SmoothHodgeAtomSpectrum
    assert restored[0].kind is ResultKind.SOURCE_ASSEMBLY
    assert restored[1].kind is ResultKind.CONIFOLD_ATOM
    assert restored[2].metadata.evidence_status is EvidenceStatus.COMPUTED
    assert len(result.get_spectra(result_kind=ResultKind.SOURCE_ASSEMBLY)) == 1


def test_mathematical_firewall_survives_persistence_invalid_discriminators_fail(tmp_path) -> None:
    result = store(tmp_path)
    run = begin_run(result)
    record = result.record_spectrum(run_id=run.run_id, spectrum=spectrum(ResultKind.SOURCE_ASSEMBLY))

    with pytest.raises(ValidationError):
        ConifoldAtomSpectrum.from_dict(result.get_spectrum(record.spectrum_id).to_dict())
    with pytest.raises(ValidationError):
        SmoothHodgeAtomSpectrum.from_dict(result.get_spectrum(record.spectrum_id).to_dict())

    with result._connect() as conn:
        conn.execute("UPDATE spectra SET concrete_type = ? WHERE spectrum_id = ?", ("ConifoldAtomSpectrum", record.spectrum_id))
    with pytest.raises(ValidationError, match="invalid type/kind"):
        result.get_spectrum(record.spectrum_id)


def test_comparison_sets_two_three_and_missing_reference(tmp_path) -> None:
    result = store(tmp_path)
    add_geometry(result, "synthetic-A")
    add_geometry(result, "synthetic-B")
    add_geometry(result, "synthetic-C")
    pair = result.create_comparison_set(display_name="pair", member_geometry_ids=["synthetic-A", "synthetic-B"])
    triple = result.create_comparison_set(display_name="triple", member_geometry_ids=["synthetic-A", "synthetic-B", "synthetic-C"])
    assert result.get_comparison_set(pair.comparison_set_id).member_geometry_ids == ("synthetic-A", "synthetic-B")
    assert result.get_comparison_set(triple.comparison_set_id).member_geometry_ids == ("synthetic-A", "synthetic-B", "synthetic-C")
    with pytest.raises(RecordNotFoundError):
        result.create_comparison_set(display_name="bad", member_geometry_ids=["synthetic-A", "missing"])


def test_json_export_import_envelope_and_determinism(tmp_path) -> None:
    result = store(tmp_path)
    geom = add_geometry(result)
    exported = result.export_record_json(RecordType.GEOMETRY, geom)
    assert exported == result.export_record_json(RecordType.GEOMETRY, geom)
    imported = result.import_record(exported)
    assert imported == geom
    payload = json.loads(exported)
    assert payload["schema_version"] == "result_store.v1"
    assert payload["record_type"] == "geometry"


def test_hashing_normalizes_json_content(tmp_path) -> None:
    assert normalized_content_hash({"b": [2, 3], "a": 1}) == normalized_content_hash({"a": 1, "b": [2, 3]})
    assert normalized_content_hash({"a": 1}) != normalized_content_hash({"a": 2})
