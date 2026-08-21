from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hodgecy.core.ids import HodgeCYID, IdentityKind
from hodgecy.core.relationships import EvidenceType, RelationshipAssertion, RelationshipEndpoint, RelationshipType
from hodgecy.core.serialization import stable_sha256
from hodgecy.core.status import ClaimLevel, ValidationEvent


@dataclass(frozen=True, slots=True)
class FibrationPayload:
    parent_dataset_id: str
    parent_source_id: str
    fibration_id: str
    fibration_type: str
    fiber_payload: dict[str, Any] = field(default_factory=dict)
    base_payload: dict[str, Any] = field(default_factory=dict)
    ambient_decomposition: dict[str, Any] = field(default_factory=dict)
    nested_parent_id: str | None = None
    source_method: str | None = None
    source_record_id: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)
    validation_events: tuple[ValidationEvent, ...] = ()

    @property
    def object_id(self) -> HodgeCYID:
        return HodgeCYID.derived_from_components(
            IdentityKind.DERIVED_OBJECT,
            "fibration",
            {
                "parent_dataset_id": self.parent_dataset_id,
                "parent_source_id": self.parent_source_id,
                "fibration_id": self.fibration_id,
                "fibration_type": self.fibration_type,
                "fiber_payload": self.fiber_payload,
                "base_payload": self.base_payload,
                "ambient_decomposition": self.ambient_decomposition,
                "nested_parent_id": self.nested_parent_id,
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "fibration_object_id": self.object_id.to_dict(),
            "parent_dataset_id": self.parent_dataset_id,
            "parent_source_id": self.parent_source_id,
            "fibration_id": self.fibration_id,
            "fibration_type": self.fibration_type,
            "fiber_payload": self.fiber_payload,
            "base_payload": self.base_payload,
            "ambient_decomposition": self.ambient_decomposition,
            "nested_parent_id": self.nested_parent_id,
            "source_method": self.source_method,
            "source_record_id": self.source_record_id,
            "provenance": self.provenance,
            "payload_hash": stable_sha256({
                "parent_dataset_id": self.parent_dataset_id,
                "parent_source_id": self.parent_source_id,
                "fibration_id": self.fibration_id,
                "fibration_type": self.fibration_type,
                "fiber_payload": self.fiber_payload,
                "base_payload": self.base_payload,
                "ambient_decomposition": self.ambient_decomposition,
                "nested_parent_id": self.nested_parent_id,
            }),
        }

    def to_relationship(self) -> RelationshipAssertion:
        relation = RelationshipType.NESTED_FIBRATION_OF if self.nested_parent_id is not None else RelationshipType.FIBRATION_OF
        parent = RelationshipEndpoint(
            object_id=HodgeCYID.source_record(self.parent_dataset_id, self.parent_source_id),
            role="parent",
            dataset_id=HodgeCYID.dataset(self.parent_dataset_id),
            native_id=self.parent_source_id,
        )
        child = RelationshipEndpoint(object_id=self.object_id, role="fibration", native_id=self.fibration_id)
        return RelationshipAssertion.build(
            relation_type=relation,
            endpoints=(parent, child),
            claim_level=ClaimLevel.SOURCE_REPORTED,
            evidence_type=EvidenceType.SOURCE_EXPLICIT,
            directed=True,
            source_dataset=HodgeCYID.dataset(f"{self.parent_dataset_id}_fibrations"),
            source_record_id=self.source_record_id or self.fibration_id,
            payload={"fibration": self.to_dict(), "source_claim_only": True},
        )


def fibration_rows(fibrations: tuple[FibrationPayload, ...] | list[FibrationPayload]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for payload in fibrations:
        rows.append({
            "fibration_id": payload.object_id.local_id,
            "parent_id": payload.parent_source_id,
            "parent_dataset": payload.parent_dataset_id,
            "native_fibration_id": payload.fibration_id,
            "fibration_type": payload.fibration_type,
            "nested_parent_id": payload.nested_parent_id,
            "source_record_id": payload.source_record_id or payload.fibration_id,
        })
    return rows