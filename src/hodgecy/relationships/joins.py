from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Iterable

from hodgecy.core.ids import DistributionLocator, HodgeCYID
from hodgecy.core.relationships import EvidenceType, JoinState, RelationshipAssertion, RelationshipEndpoint, RelationshipType
from hodgecy.core.serialization import stable_sha256
from hodgecy.core.status import ClaimLevel, ValidationDimension, ValidationEvent, ValidationStatus
from hodgecy.core.versions import SchemaVersion


@dataclass(frozen=True, slots=True)
class RejectedRelationship:
    dataset_id: HodgeCYID
    source_locator: DistributionLocator | None
    failure_type: JoinState
    reason: str
    candidate_endpoints: tuple[RelationshipEndpoint, ...] = ()
    raw_reference: dict[str, Any] = field(default_factory=dict)
    parser_version: str = "relationship_builder.v1"
    schema_version: SchemaVersion = SchemaVersion("relationship_rejected.v1")

    @property
    def rejected_id(self) -> str:
        return stable_sha256({
            "dataset_id": self.dataset_id.serialize(),
            "failure_type": self.failure_type.value,
            "reason": self.reason,
            "candidate_endpoints": [endpoint.to_dict() for endpoint in self.candidate_endpoints],
            "raw_reference": self.raw_reference,
            "schema_version": self.schema_version.to_dict(),
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "rejected_id": self.rejected_id,
            "dataset_id": self.dataset_id.to_dict(),
            "source_locator": None if self.source_locator is None else self.source_locator.to_dict(),
            "failure_type": self.failure_type.value,
            "reason": self.reason,
            "candidate_endpoints": [endpoint.to_dict() for endpoint in self.candidate_endpoints],
            "raw_reference": self.raw_reference,
            "parser_version": self.parser_version,
            "schema_version": self.schema_version.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class AmbiguousJoin:
    join_key: str
    left_endpoint: RelationshipEndpoint
    candidate_endpoints: tuple[RelationshipEndpoint, ...]
    evidence_type: EvidenceType
    reason: str = "multiple candidate endpoints"

    def to_dict(self) -> dict[str, Any]:
        return {
            "join_key": self.join_key,
            "left_endpoint": self.left_endpoint.to_dict(),
            "candidate_endpoints": [endpoint.to_dict() for endpoint in self.candidate_endpoints],
            "evidence_type": self.evidence_type.value,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class RelationshipBuildResult:
    relationships: tuple[RelationshipAssertion, ...]
    rejected: tuple[RejectedRelationship, ...] = ()
    ambiguous: tuple[AmbiguousJoin, ...] = ()
    validation_events: tuple[ValidationEvent, ...] = ()

    @property
    def relationship_count(self) -> int:
        return len(self.relationships)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected)

    @property
    def ambiguous_count(self) -> int:
        return len(self.ambiguous)

    def to_dict(self) -> dict[str, Any]:
        return {
            "relationship_count": self.relationship_count,
            "rejected_count": self.rejected_count,
            "ambiguous_count": self.ambiguous_count,
            "relationships": [row.to_dict() for row in self.relationships],
            "rejected": [row.to_dict() for row in self.rejected],
            "ambiguous": [row.to_dict() for row in self.ambiguous],
            "validation_events": [event.to_dict() for event in self.validation_events],
        }


def source_endpoint(dataset_id: str, native_id: object, *, role: str) -> RelationshipEndpoint:
    native = _token(native_id)
    return RelationshipEndpoint(
        object_id=HodgeCYID.source_record(dataset_id, native),
        role=role,
        dataset_id=HodgeCYID.dataset(dataset_id),
        native_id=str(native_id),
    )


def exact_source_crosswalk(
    *,
    left_dataset_id: str,
    right_dataset_id: str,
    left_records: Iterable[dict[str, Any]],
    right_records: Iterable[dict[str, Any]],
    left_key: str,
    right_key: str,
    relationship_type: RelationshipType = RelationshipType.SOURCE_CROSSWALK,
    evidence_type: EvidenceType = EvidenceType.EXACT_SOURCE_ID,
    source_dataset_id: str | None = None,
    join_method: str = "exact_source_id",
) -> RelationshipBuildResult:
    right_index: dict[str, list[dict[str, Any]]] = {}
    for row in right_records:
        key = str(row.get(right_key))
        right_index.setdefault(key, []).append(row)
    relationships: list[RelationshipAssertion] = []
    rejected: list[RejectedRelationship] = []
    ambiguous: list[AmbiguousJoin] = []
    source_dataset = HodgeCYID.dataset(source_dataset_id or f"{left_dataset_id}_to_{right_dataset_id}")
    for left in left_records:
        key = str(left.get(left_key))
        left_endpoint = source_endpoint(left_dataset_id, left.get(left_key), role="source")
        matches = right_index.get(key, [])
        if not matches:
            rejected.append(RejectedRelationship(
                dataset_id=source_dataset,
                source_locator=None,
                failure_type=JoinState.UNMATCHED,
                reason=f"no right endpoint for join key {key}",
                candidate_endpoints=(left_endpoint,),
                raw_reference={"join_key": key, "left": left},
            ))
            continue
        candidate_endpoints = tuple(source_endpoint(right_dataset_id, row.get(right_key), role="target") for row in matches)
        if len(candidate_endpoints) > 1:
            ambiguous.append(AmbiguousJoin(key, left_endpoint, candidate_endpoints, evidence_type))
            rejected.append(RejectedRelationship(
                dataset_id=source_dataset,
                source_locator=None,
                failure_type=JoinState.AMBIGUOUS,
                reason=f"ambiguous right endpoints for join key {key}",
                candidate_endpoints=(left_endpoint,) + candidate_endpoints,
                raw_reference={"join_key": key, "left": left, "matches": matches},
            ))
            continue
        relationships.append(RelationshipAssertion.build(
            relation_type=relationship_type,
            endpoints=(left_endpoint, candidate_endpoints[0]),
            claim_level=ClaimLevel.SOURCE_REPORTED,
            evidence_type=evidence_type,
            directed=True,
            source_dataset=source_dataset,
            source_record_id=key,
            payload={"join_key": key, "join_method": join_method, "geometric_identity_claimed": False},
        ))
    return RelationshipBuildResult(tuple(relationships), tuple(rejected), tuple(ambiguous), (_event("exact_source_crosswalk", len(relationships), len(rejected)),))


def one_to_many_relationships(
    *,
    parent_dataset_id: str,
    child_dataset_id: str,
    parent_records: Iterable[dict[str, Any]],
    child_records: Iterable[dict[str, Any]],
    parent_key: str,
    child_parent_key: str,
    child_key: str,
    relationship_type: RelationshipType,
    evidence_type: EvidenceType = EvidenceType.SOURCE_EXPLICIT,
    source_dataset_id: str | None = None,
    child_role: str = "child",
) -> RelationshipBuildResult:
    parent_ids = {str(row.get(parent_key)) for row in parent_records}
    relationships: list[RelationshipAssertion] = []
    rejected: list[RejectedRelationship] = []
    source_dataset = HodgeCYID.dataset(source_dataset_id or f"{parent_dataset_id}_to_{child_dataset_id}")
    for child in child_records:
        parent_native = str(child.get(child_parent_key))
        child_native = str(child.get(child_key))
        parent_endpoint = source_endpoint(parent_dataset_id, parent_native, role="parent")
        child_endpoint = source_endpoint(child_dataset_id, child_native, role=child_role)
        if parent_native not in parent_ids:
            rejected.append(RejectedRelationship(
                dataset_id=source_dataset,
                source_locator=None,
                failure_type=JoinState.DANGLING_ENDPOINT,
                reason=f"parent endpoint {parent_native} is not present",
                candidate_endpoints=(parent_endpoint, child_endpoint),
                raw_reference=child,
            ))
            continue
        relationships.append(RelationshipAssertion.build(
            relation_type=relationship_type,
            endpoints=(parent_endpoint, child_endpoint),
            claim_level=ClaimLevel.SOURCE_REPORTED,
            evidence_type=evidence_type,
            directed=True,
            source_dataset=source_dataset,
            source_record_id=child_native,
            payload={"parent_key": parent_native, "child_key": child_native, "source_claim_only": True},
        ))
    return RelationshipBuildResult(tuple(relationships), tuple(rejected), (), (_event("one_to_many_relationships", len(relationships), len(rejected)),))


def relationship_rows(relationships: Iterable[RelationshipAssertion]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for relationship in relationships:
        source = relationship.endpoints[0]
        target = relationship.endpoints[1] if len(relationship.endpoints) > 1 else relationship.endpoints[0]
        rows.append({
            "relationship_id": relationship.relationship_id.local_id,
            "relationship_type": relationship.relationship_type,
            "source_id": source.object_id.local_id,
            "source_dataset": None if source.dataset_id is None else source.dataset_id.local_id,
            "target_id": target.object_id.local_id,
            "target_dataset": None if target.dataset_id is None else target.dataset_id.local_id,
            "evidence_type": relationship.evidence_type.value,
            "claim_level": relationship.claim_level.value,
            "join_state": relationship.join_state.value,
            "directed": relationship.directed,
            "source_record_id": relationship.source_record_id,
        })
    return rows


def _event(method: str, relationship_count: int, rejected_count: int) -> ValidationEvent:
    return ValidationEvent(
        dimension=ValidationDimension.RELATIONSHIP,
        status=ValidationStatus.SYNTACTICALLY_VALIDATED,
        method=method,
        evidence={"relationship_count": relationship_count, "rejected_count": rejected_count},
        validator="hodgecy.relationships.joins",
        validator_version="1.0.0",
    )


def _token(value: object) -> str:
    text = re.sub(r"[^A-Za-z0-9._=-]+", "_", str(value).strip())
    text = text.strip("_")
    if not text:
        return "missing"
    if not text[0].isalnum():
        return f"id{text}"
    return text
