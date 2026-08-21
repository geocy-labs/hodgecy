from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hodgecy.core.ids import HodgeCYID, IdentityKind
from hodgecy.core.relationships import EvidenceType, RelationshipAssertion, RelationshipEndpoint, RelationshipType
from hodgecy.core.status import ClaimLevel


@dataclass(frozen=True, slots=True)
class GroupPayload:
    label: str
    order: int | None = None
    generators: tuple[str, ...] = ()
    presentation: dict[str, Any] = field(default_factory=dict)
    source_label: str | None = None

    @property
    def object_id(self) -> HodgeCYID:
        return HodgeCYID.derived_from_components(
            IdentityKind.DERIVED_OBJECT,
            "group",
            {"label": self.label, "order": self.order, "generators": self.generators, "presentation": self.presentation},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_object_id": self.object_id.to_dict(),
            "label": self.label,
            "order": self.order,
            "generators": list(self.generators),
            "presentation": self.presentation,
            "source_label": self.source_label,
        }


@dataclass(frozen=True, slots=True)
class GroupActionPayload:
    parent_dataset_id: str
    parent_source_id: str
    action_id: str
    group: GroupPayload
    action_type: str = "free_action"
    action_payload: dict[str, Any] = field(default_factory=dict)
    source_record_id: str | None = None
    freeness_certified: bool = False

    @property
    def object_id(self) -> HodgeCYID:
        return HodgeCYID.derived_from_components(
            IdentityKind.DERIVED_OBJECT,
            "group_action",
            {
                "parent_dataset_id": self.parent_dataset_id,
                "parent_source_id": self.parent_source_id,
                "action_id": self.action_id,
                "group": self.group.to_dict(),
                "action_type": self.action_type,
                "action_payload": self.action_payload,
            },
        )

    @property
    def relationship_type(self) -> RelationshipType:
        return RelationshipType.INVOLUTION_ON if self.action_type == "involution" else RelationshipType.FREE_ACTION_ON

    @property
    def claim_level(self) -> ClaimLevel:
        return ClaimLevel.COMPUTATIONALLY_CERTIFIED if self.freeness_certified else ClaimLevel.SOURCE_REPORTED

    @property
    def evidence_type(self) -> EvidenceType:
        return EvidenceType.COMPUTATION_CERTIFIED if self.freeness_certified else EvidenceType.SOURCE_EXPLICIT

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_object_id": self.object_id.to_dict(),
            "parent_dataset_id": self.parent_dataset_id,
            "parent_source_id": self.parent_source_id,
            "action_id": self.action_id,
            "group": self.group.to_dict(),
            "action_type": self.action_type,
            "action_payload": self.action_payload,
            "source_record_id": self.source_record_id,
            "freeness_certified": self.freeness_certified,
        }

    def to_relationship(self) -> RelationshipAssertion:
        parent = RelationshipEndpoint(
            object_id=HodgeCYID.source_record(self.parent_dataset_id, self.parent_source_id),
            role="space",
            dataset_id=HodgeCYID.dataset(self.parent_dataset_id),
            native_id=self.parent_source_id,
        )
        action = RelationshipEndpoint(object_id=self.object_id, role="group_action", native_id=self.action_id)
        return RelationshipAssertion.build(
            relation_type=self.relationship_type,
            endpoints=(action, parent),
            claim_level=self.claim_level,
            evidence_type=self.evidence_type,
            directed=True,
            source_dataset=HodgeCYID.dataset(f"{self.parent_dataset_id}_group_actions"),
            source_record_id=self.source_record_id or self.action_id,
            payload={"group_action": self.to_dict(), "source_claim_only": not self.freeness_certified},
        )


@dataclass(frozen=True, slots=True)
class QuotientPayload:
    parent_dataset_id: str
    parent_source_id: str
    quotient_id: str
    action: GroupActionPayload
    quotient_payload: dict[str, Any] = field(default_factory=dict)
    source_record_id: str | None = None

    @property
    def object_id(self) -> HodgeCYID:
        return HodgeCYID.derived_from_components(
            IdentityKind.DERIVED_OBJECT,
            "quotient",
            {
                "parent_dataset_id": self.parent_dataset_id,
                "parent_source_id": self.parent_source_id,
                "quotient_id": self.quotient_id,
                "action": self.action.to_dict(),
                "quotient_payload": self.quotient_payload,
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "quotient_object_id": self.object_id.to_dict(),
            "parent_dataset_id": self.parent_dataset_id,
            "parent_source_id": self.parent_source_id,
            "quotient_id": self.quotient_id,
            "action": self.action.to_dict(),
            "quotient_payload": self.quotient_payload,
            "source_record_id": self.source_record_id,
        }

    def to_relationship(self) -> RelationshipAssertion:
        quotient = RelationshipEndpoint(object_id=self.object_id, role="quotient", native_id=self.quotient_id)
        parent = RelationshipEndpoint(
            object_id=HodgeCYID.source_record(self.parent_dataset_id, self.parent_source_id),
            role="cover",
            dataset_id=HodgeCYID.dataset(self.parent_dataset_id),
            native_id=self.parent_source_id,
        )
        return RelationshipAssertion.build(
            relation_type=RelationshipType.QUOTIENT_OF,
            endpoints=(quotient, parent),
            claim_level=ClaimLevel.SOURCE_REPORTED,
            evidence_type=EvidenceType.SOURCE_EXPLICIT,
            directed=True,
            source_dataset=HodgeCYID.dataset(f"{self.parent_dataset_id}_quotients"),
            source_record_id=self.source_record_id or self.quotient_id,
            payload={"quotient": self.to_dict(), "source_claim_only": True},
        )