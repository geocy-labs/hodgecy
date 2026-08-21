from __future__ import annotations

import pytest

from hodgecy.core import (
    AcquisitionStatus,
    ClaimLevel,
    ConstructionFamily,
    DatasetDescriptor,
    EvidenceType,
    HodgeCYID,
    IdentityKind,
    JoinState,
    RedistributionStatus,
    RelationshipAssertion,
    RelationshipEndpoint,
    RelationshipType,
    stable_sha256,
)
from hodgecy.core.errors import ValidationError
from hodgecy.geometry import FibrationPayload, GroupActionPayload, GroupPayload, QuotientPayload
from hodgecy.relationships import (
    RelationshipQueryService,
    exact_source_crosswalk,
    forbid_free_action_certification_from_source,
    forbid_geometry_identity_from_hodge_numbers,
    forbid_geometry_identity_from_weight_crosswalk,
    forbid_mirror_from_hodge_swap,
    one_to_many_relationships,
    register_relationship_parquet_source,
)
from hodgecy.relationships.joins import relationship_rows, source_endpoint
from hodgecy.storage import DatasetInstance, TableKind, open_catalog


def _endpoint(local: str, role: str) -> RelationshipEndpoint:
    return RelationshipEndpoint(HodgeCYID.presentation("cicy3", stable_sha256({"local": local})), role)


def test_relationship_assertion_keeps_schema_evidence_and_directionality() -> None:
    relation = RelationshipAssertion.build(
        relation_type=RelationshipType.MIRROR_OF,
        endpoints=(_endpoint("a", "left"), _endpoint("b", "right")),
        claim_level=ClaimLevel.CANDIDATE,
        evidence_type=EvidenceType.HEURISTIC,
        directed=False,
        payload={"rule": "test-only"},
    )

    round_trip = RelationshipAssertion.from_dict(relation.to_dict())
    assert round_trip.relationship_id.kind is IdentityKind.DERIVED_OBJECT
    assert round_trip.relationship_type == "mirror_of"
    assert round_trip.directionality.value == "symmetric"
    assert round_trip.evidence_type is EvidenceType.HEURISTIC
    assert round_trip.claim_level is ClaimLevel.CANDIDATE
    assert round_trip.schema.version.value == "relationship.v1"


def test_exact_source_crosswalk_does_not_claim_geometry_identity() -> None:
    result = exact_source_crosswalk(
        left_dataset_id="cicy3_standard",
        right_dataset_id="cicy3_favorable",
        left_records=({"Num": 1}, {"Num": "bad/id"}),
        right_records=({"Num": 1},),
        left_key="Num",
        right_key="Num",
    )

    assert result.relationship_count == 1
    assert result.rejected_count == 1
    relation = result.relationships[0]
    assert relation.relationship_type == RelationshipType.SOURCE_CROSSWALK.value
    assert relation.evidence_type is EvidenceType.EXACT_SOURCE_ID
    assert relation.payload["geometric_identity_claimed"] is False
    assert relation.endpoints[0].dataset_id == HodgeCYID.dataset("cicy3_standard")
    assert source_endpoint("cicy3_standard", "bad/id", role="source").object_id.local_id == "bad_id"


def test_ambiguous_and_unmatched_joins_are_rejected_not_materialized() -> None:
    result = exact_source_crosswalk(
        left_dataset_id="left_fixture",
        right_dataset_id="right_fixture",
        left_records=({"Num": 1}, {"Num": 2}),
        right_records=({"Num": 1}, {"Num": 1}),
        left_key="Num",
        right_key="Num",
    )

    assert result.relationship_count == 0
    assert result.ambiguous_count == 1
    assert {row.failure_type for row in result.rejected} == {JoinState.AMBIGUOUS, JoinState.UNMATCHED}


def test_one_to_many_fibration_relationships_keep_parent_ids_exact() -> None:
    result = one_to_many_relationships(
        parent_dataset_id="cicy3_standard",
        child_dataset_id="cicy3_fibrations",
        parent_records=({"Num": 84},),
        child_records=(
            {"parent": 84, "fib": "84-f1"},
            {"parent": 84, "fib": "84-f2"},
            {"parent": 999, "fib": "orphan"},
        ),
        parent_key="Num",
        child_parent_key="parent",
        child_key="fib",
        relationship_type=RelationshipType.FIBRATION_OF,
        child_role="fibration",
    )

    assert result.relationship_count == 2
    assert result.rejected_count == 1
    assert all(rel.endpoints[0].object_id.local_id == "84" for rel in result.relationships)
    assert result.rejected[0].failure_type is JoinState.DANGLING_ENDPOINT


def test_fibration_and_symmetry_payloads_lower_to_source_relationships() -> None:
    fibration = FibrationPayload(
        parent_dataset_id="cicy3_standard",
        parent_source_id="84",
        fibration_id="84-f1",
        fibration_type="genus_one",
        fiber_payload={"dimension": 1},
        base_payload={"dimension": 2},
    ).to_relationship()
    group = GroupPayload("Z2", order=2, generators=("g",))
    action = GroupActionPayload("cicy3_standard", "84", "free-1", group, action_payload={"rule": "source row"})
    action_relation = action.to_relationship()
    quotient_relation = QuotientPayload("cicy3_standard", "84", "q-1", action).to_relationship()

    assert fibration.relationship_type == "fibration_of"
    assert fibration.claim_level is ClaimLevel.SOURCE_REPORTED
    assert action_relation.relationship_type == "free_action_on"
    assert action_relation.claim_level is ClaimLevel.SOURCE_REPORTED
    assert action_relation.payload["source_claim_only"] is True
    assert quotient_relation.relationship_type == "quotient_of"
    assert quotient_relation.endpoints[1].object_id == HodgeCYID.source_record("cicy3_standard", "84")


def test_relationship_claim_policy_guards_forbid_promotion_shortcuts() -> None:
    with pytest.raises(ValidationError):
        forbid_geometry_identity_from_hodge_numbers()
    with pytest.raises(ValidationError):
        forbid_mirror_from_hodge_swap()
    with pytest.raises(ValidationError):
        forbid_geometry_identity_from_weight_crosswalk()
    with pytest.raises(ValidationError):
        forbid_free_action_certification_from_source(EvidenceType.SOURCE_EXPLICIT)
    forbid_free_action_certification_from_source(EvidenceType.COMPUTATION_CERTIFIED)


def test_relationship_and_fibration_tables_register_and_query(tmp_path) -> None:
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")

    raw = tmp_path / "raw" / "relationships"
    raw.mkdir(parents=True)
    relationship_path = raw / "cicy_relationships.parquet"
    result = one_to_many_relationships(
        parent_dataset_id="cicy3_standard",
        child_dataset_id="cicy3_fibrations",
        parent_records=({"Num": 84},),
        child_records=({"parent": 84, "fib": "84-f1"}, {"parent": 84, "fib": "84-f2"}),
        parent_key="Num",
        child_parent_key="parent",
        child_key="fib",
        relationship_type=RelationshipType.FIBRATION_OF,
        child_role="fibration",
    )
    pq.write_table(pa.Table.from_pylist(relationship_rows(result.relationships)), relationship_path)
    fibration_path = raw / "fibration_rows.parquet"
    pq.write_table(pa.table({"parent_id": ["84", "84"], "fibration_id": ["84-f1", "84-f2"]}), fibration_path)

    catalog = open_catalog(tmp_path, create=True)
    descriptor = catalog.register_dataset(DatasetDescriptor(
        dataset_id=HodgeCYID.dataset("cicy3_relationships"),
        name="CICY relationship fixture",
        construction_family=ConstructionFamily.known("cicy"),
        acquisition_status=AcquisitionStatus.COMPLETE_COLUMNAR,
        redistribution_status=RedistributionStatus.REDISTRIBUTABLE,
    ))
    catalog.register_instance(DatasetInstance(
        instance_id="cicy3_relationships_v1",
        dataset_id=descriptor.dataset_id,
        source_version="fixture-v1",
        source_revision="join-matrix-fixture",
        acquisition_status=AcquisitionStatus.COMPLETE_COLUMNAR,
        redistribution_status=RedistributionStatus.REDISTRIBUTABLE,
        record_count=2,
    ))
    register_relationship_parquet_source(
        catalog,
        columnar_id="cicy_relationships_columnar",
        instance_id="cicy3_relationships_v1",
        source_id="cicy_relationships_parquet",
        relative_path="raw/relationships/cicy_relationships.parquet",
        table_name="cicy_relationships",
        relationship_types=(RelationshipType.FIBRATION_OF.value,),
        endpoint_datasets=("cicy3_standard", "cicy3_fibrations"),
    )
    catalog.register_parquet_source(
        columnar_id="cicy_fibrations_columnar",
        instance_id="cicy3_relationships_v1",
        source_id="cicy_fibrations_parquet",
        relative_path="raw/relationships/fibration_rows.parquet",
        table_name="cicy_fibration_rows",
        table_kind=TableKind.FIBRATION,
        parent_key="parent_id",
        child_key="fibration_id",
        query_safe_columns=("parent_id", "fibration_id"),
    )

    source_id = result.relationships[0].endpoints[0].object_id.local_id
    service = RelationshipQueryService(catalog, table="cicy_relationships")
    assert service.has_relation(source_id, relationship_type="fibration_of") is True
    assert service.relation_count(source_id, relationship_type="fibration_of") == 2
    assert service.related_records(source_id).to_arrow().num_rows == 2
    assert catalog.list_tables(TableKind.RELATIONSHIP)[0].metadata["relationship_schema"] == "relationship.v1"
    fibration_table = catalog.list_tables(TableKind.FIBRATION)[0]
    assert fibration_table.parent_key == "parent_id"
    assert fibration_table.child_key == "fibration_id"
    assert catalog.list_physical_sources("cicy3_relationships_v1")[0].metadata["parquet_row_count"] == 2