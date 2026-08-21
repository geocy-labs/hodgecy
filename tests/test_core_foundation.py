from __future__ import annotations

import json
from fractions import Fraction

import pytest

from hodgecy.config import HodgeCYConfig, HodgeCYDataRoot, open_data_root
from hodgecy.core import (
    AcquisitionStatus,
    AdapterCapability,
    ClaimLevel,
    ConstructionFamily,
    ContentFingerprint,
    DatasetAdapterDescriptor,
    DatasetDescriptor,
    DistributionLocator,
    FactOrigin,
    FingerprintKind,
    GeometryRef,
    HodgeCYID,
    HodgeDiamond,
    HodgeDiamondFact,
    IdentityError,
    IdentityKind,
    ParseStatus,
    ParserProvenance,
    PresentationRef,
    RedistributionStatus,
    RelationshipAssertion,
    RelationshipEndpoint,
    SchemaVersion,
    SourceProvenance,
    SourceRecordEnvelope,
    ValidationDimension,
    ValidationEvent,
    ValidationStatus,
    canonical_json,
    stable_sha256,
)
from hodgecy.core.algorithms import AlgorithmDescriptor
from hodgecy.core.errors import ConfigurationError, ValidationError
from hodgecy.math import Basis, BasisMatrix, BasisVector, CoefficientDomain


def dataset_id(name: str = "cicy3_oxford") -> HodgeCYID:
    return HodgeCYID.dataset(name)


def test_identity_layers_are_distinct_and_serializable() -> None:
    ds = dataset_id()
    source = HodgeCYID.source_record("cicy3_oxford", "Num-1")
    presentation = HodgeCYID.presentation("cicy3", stable_sha256({"matrix": [[1, 1]]}))
    assert HodgeCYID.parse(ds.serialize()) == ds
    assert ds.kind is IdentityKind.DATASET
    assert source.kind is IdentityKind.SOURCE_RECORD
    assert presentation.kind is IdentityKind.PRESENTATION
    assert ds != source
    with pytest.raises(IdentityError):
        source.require_kind(IdentityKind.DATASET)


def test_distribution_locator_is_not_identity() -> None:
    locator = DistributionLocator(dataset_id("kreuzer_skarke_4d"), "ks-rev", relative_path="raw/ks/shard.parquet", row_group=4, row_offset=10)
    assert locator.row_group == 4
    assert locator.dataset_id.kind is IdentityKind.DATASET


def test_content_fingerprint_claim_kind() -> None:
    fp = ContentFingerprint.from_payload({"vertices": [[0, 1], [1, 0]]}, FingerprintKind.NORMALIZED_PRESENTATION)
    assert fp.kind is FingerprintKind.NORMALIZED_PRESENTATION
    assert fp != ContentFingerprint.from_payload({"vertices": [[0, 1], [1, 0]]}, FingerprintKind.GEOMETRIC_EQUIVALENCE)


def test_dataset_descriptor_round_trip_and_status_independence() -> None:
    descriptor = DatasetDescriptor(dataset_id("kreuzer_skarke_4d"), "Kreuzer-Skarke 4D", ConstructionFamily("toric_hypersurface"), AcquisitionStatus.COMPLETE_COLUMNAR, RedistributionStatus.ACQUIRED_LOCALLY_BY_USER, source_version="60c0e119", identifier_definition="distribution locator plus presentation fingerprint", verified_count=473_800_776, adapter_capabilities=("columnar", "streaming"))
    assert DatasetDescriptor.from_dict(descriptor.to_dict()) == descriptor
    registry_only = DatasetDescriptor(dataset_id("genuine_gcicy_registry"), "gCICY registry", ConstructionFamily("generalized_cicy"), AcquisitionStatus.SOURCE_REGISTRY_ONLY, RedistributionStatus.REMOTE_OR_MANUAL_ONLY)
    assert registry_only.acquisition_status is AcquisitionStatus.SOURCE_REGISTRY_ONLY


def test_source_record_envelope_separates_payloads() -> None:
    ds = dataset_id()
    envelope = SourceRecordEnvelope(
        hodgecy_record_id=HodgeCYID.derived_from_components(IdentityKind.HODGECY_RECORD, "cicy3_oxford", {"source": "Num-1"}),
        dataset_id=ds,
        source_record_id=HodgeCYID.source_record("cicy3_oxford", "Num-1"),
        source_version="accessed-2026-08-20",
        source_locator=DistributionLocator(ds, "cicylist", relative_path="raw/cicy3/cicylist.txt", source_block="Num-1"),
        source_provenance=SourceProvenance(source_dataset="cicy3_oxford", source_locator="Num 1"),
        parser_provenance=ParserProvenance("cicy3-block", "1", "v1"),
        parse_status=ParseStatus.PARSED,
        schema_version=SchemaVersion(),
        payload_type="cicy3_configuration",
        payload_ref="presentation:hcy-placeholder",
        payload_summary={"num_projective_spaces": 7},
    )
    data = envelope.to_dict()
    assert data["payload_type"] == "cicy3_configuration"
    assert "h11" not in data


def test_source_presentation_geometry_can_remain_unresolved() -> None:
    p1 = PresentationRef(HodgeCYID.presentation("cicy3", stable_sha256({"matrix": 1})), "cicy3", "configuration")
    p2 = PresentationRef(HodgeCYID.presentation("cicy3", stable_sha256({"matrix": 2})), "cicy3", "configuration")
    unresolved = GeometryRef(None, ClaimLevel.CANDIDATE)
    assert p1.presentation_id != p2.presentation_id
    assert unresolved.geometry_id is None


def test_provenance_and_validation_round_trip() -> None:
    source = SourceProvenance(source_dataset="cicy4_oxford", physical_file="raw/cicy4/cicy4list.zip", source_locator="record 1")
    assert SourceProvenance.from_dict(source.to_dict()) == source
    event = ValidationEvent(ValidationDimension.HODGE, ValidationStatus.SYNTACTICALLY_VALIDATED, "CY4 Euler identity", {"mismatches": 0})
    assert ValidationEvent.from_dict(event.to_dict()) == event


def test_hodge_diamond_supports_cy3_cy4_and_partial_data() -> None:
    subject = HodgeCYID.presentation("cicy4", stable_sha256({"id": 1}))
    cy4 = HodgeDiamond(4, (HodgeDiamondFact(subject, 4, 1, 1, 1, FactOrigin.SOURCE_REPORTED, ClaimLevel.PARSED), HodgeDiamondFact(subject, 4, 3, 1, 426, FactOrigin.SOURCE_REPORTED, ClaimLevel.PARSED), HodgeDiamondFact(subject, 4, 2, 2, 1752, FactOrigin.SOURCE_REPORTED, ClaimLevel.PARSED)))
    assert cy4.h11 == 1
    assert cy4.h31 == 426
    assert cy4.h21 is None
    cy3 = HodgeDiamond(3, (HodgeDiamondFact(subject, 3, 2, 1, 15, FactOrigin.SOURCE_REPORTED, ClaimLevel.PARSED),))
    assert cy3.h21 == 15
    assert cy3.get(1, 1) is None
    with pytest.raises(ValidationError):
        HodgeDiamondFact(subject, 3, 4, 1, 0, FactOrigin.SOURCE_REPORTED, ClaimLevel.PARSED)


def test_basis_vectors_are_basis_sensitive_and_exact() -> None:
    domain = CoefficientDomain.integers()
    b1 = Basis(HodgeCYID.presentation("cicy3", "basisA"), "H2", domain, ("J1", "J2"), source="Oxford CICY C2")
    b2 = Basis(HodgeCYID.presentation("cicy3", "basisB"), "H2", domain, ("J1", "J2"), source="Favorable CICY C2")
    v1 = BasisVector(b1, (24, 36))
    v2 = BasisVector(b2, (24, 36))
    assert v1.entries == v2.entries
    with pytest.raises(ValidationError):
        v1.equal_in_same_basis(v2)


def test_exact_rational_and_finite_field_serialization() -> None:
    q_basis = Basis(HodgeCYID.presentation("test", "basisQ"), "V", CoefficientDomain.rationals(), ("e1", "e2"))
    q_vec = BasisVector(q_basis, (Fraction(1, 2), "2/3"))
    assert q_vec.entries == ("1/2", "2/3")
    f_basis = Basis(HodgeCYID.presentation("test", "basisF5"), "V", CoefficientDomain.finite_field(5), ("e1", "e2"))
    f_vec = BasisVector(f_basis, (7, -1))
    assert f_vec.entries == (2, 4)
    matrix = BasisMatrix(q_basis, q_basis, ((1, Fraction(1, 3)), (0, 1)))
    assert matrix.shape == (2, 2)
    assert matrix.rows[0][1] == "1/3"
    assert "float" not in canonical_json(q_vec.to_dict())


def test_config_precedence_and_no_directory_creation(tmp_path, monkeypatch) -> None:
    file_root = tmp_path / "file-root"
    env_root = tmp_path / "env-root"
    override_root = tmp_path / "override-root"
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"data_root": str(file_root), "materialization_row_limit": 7}), encoding="utf-8")
    config = HodgeCYConfig.load(config_file=config_file, environ={"HODGECY_DATA_ROOT": str(env_root)})
    assert config.data_root == HodgeCYDataRoot(env_root)
    assert config.materialization_row_limit == 7
    config = HodgeCYConfig.load(data_root=override_root, config_file=config_file, environ={"HODGECY_DATA_ROOT": str(env_root)})
    assert config.data_root == HodgeCYDataRoot(override_root)
    assert not override_root.exists()
    monkeypatch.delenv("HODGECY_DATA_ROOT", raising=False)
    with pytest.raises(ConfigurationError):
        open_data_root()


def test_adapter_algorithm_relationship_and_forbidden_promotion_path() -> None:
    ds = dataset_id("double_octics_ckc")
    adapter = DatasetAdapterDescriptor(ds, "double-octic-fixture", "1", (AdapterCapability.STREAMING,))
    assert adapter.supports(AdapterCapability.STREAMING)
    assert not adapter.supports(AdapterCapability.COLUMNAR)
    algorithm = AlgorithmDescriptor(HodgeCYID(IdentityKind.ALGORITHM, "hodgecy", "rank-Q"), "rank over Q", "1", {"field": "Q"})
    assert algorithm.parameter_hash == stable_sha256({"field": "Q"})
    rel = RelationshipAssertion(HodgeCYID.derived_from_components(IdentityKind.DERIVED_OBJECT, "relationship", {"kind": "same_hodge_candidate"}), "same_hodge_candidate", (RelationshipEndpoint(HodgeCYID.presentation("cicy3", "a"), "left"), RelationshipEndpoint(HodgeCYID.presentation("cicy3", "b"), "right")), ClaimLevel.CANDIDATE)
    assert rel.claim_level is ClaimLevel.CANDIDATE
    assert rel.claim_level is not ClaimLevel.THEOREM_CERTIFIED
