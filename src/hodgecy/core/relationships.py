from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .ids import DistributionLocator, HodgeCYID, IdentityKind
from .provenance import SourceProvenance
from .serialization import stable_sha256
from .status import ClaimLevel, ValidationEvent
from .versions import SchemaVersion

RELATIONSHIP_SCHEMA_NAME = "hodgecy.relationship"
RELATIONSHIP_SCHEMA_VERSION = "relationship.v1"


class RelationshipType(str, Enum):
    SOURCE_CROSSWALK = "source_crosswalk"
    ALTERNATE_PRESENTATION_OF = "alternate_presentation_of"
    FAVORABLE_PRESENTATION_OF = "favorable_presentation_of"
    FIBRATION_OF = "fibration_of"
    NESTED_FIBRATION_OF = "nested_fibration_of"
    FREE_ACTION_ON = "free_action_on"
    QUOTIENT_OF = "quotient_of"
    COVER_OF = "cover_of"
    INVOLUTION_ON = "involution_on"
    ORIENTIFOLD_OF = "orientifold_of"
    OPERATOR_FOR = "operator_for"
    TOPOLOGICAL_DATA_FOR = "topological_data_for"
    DIVISOR_OF = "divisor_of"
    TRIANGULATION_OF = "triangulation_of"
    NEF_PARTITION_OF = "nef_partition_of"
    MIRROR_OF = "mirror_of"
    DUAL_TO = "dual_to"
    BIRATIONAL_TO = "birational_to"
    FLOP_RELATED_TO = "flop_related_to"
    DEFORMATION_RELATED_TO = "deformation_related_to"
    DEGENERATES_TO = "degenerates_to"
    RESOLVES = "resolves"
    SMOOTHS = "smooths"
    CONIFOLD_TRANSITION_TO = "conifold_transition_to"


class EvidenceType(str, Enum):
    SOURCE_EXPLICIT = "SOURCE_EXPLICIT"
    EXACT_SOURCE_ID = "EXACT_SOURCE_ID"
    EXACT_PRESENTATION_MATCH = "EXACT_PRESENTATION_MATCH"
    LITERATURE_THEOREM = "LITERATURE_THEOREM"
    COMPUTATION_CERTIFIED = "COMPUTATION_CERTIFIED"
    COMPUTED_CANDIDATE = "COMPUTED_CANDIDATE"
    HEURISTIC = "HEURISTIC"
    USER_ASSERTED = "USER_ASSERTED"


class Directionality(str, Enum):
    DIRECTED = "directed"
    SYMMETRIC = "symmetric"


class JoinState(str, Enum):
    EXACT_MATCH = "exact_match"
    UNMATCHED = "unmatched"
    AMBIGUOUS = "ambiguous"
    DANGLING_ENDPOINT = "dangling_endpoint"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class RelationshipSchema:
    name: str = RELATIONSHIP_SCHEMA_NAME
    version: SchemaVersion = SchemaVersion(RELATIONSHIP_SCHEMA_VERSION)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "version": self.version.to_dict()}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RelationshipSchema":
        return cls(name=str(payload.get("name") or RELATIONSHIP_SCHEMA_NAME), version=SchemaVersion.from_dict(payload.get("version", {"value": RELATIONSHIP_SCHEMA_VERSION})))


@dataclass(frozen=True, slots=True)
class RelationshipEndpoint:
    object_id: HodgeCYID
    role: str
    dataset_id: HodgeCYID | None = None
    native_id: str | None = None
    label: str | None = None

    def __post_init__(self) -> None:
        if self.dataset_id is not None:
            self.dataset_id.require_kind(IdentityKind.DATASET)

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id.to_dict(),
            "role": self.role,
            "dataset_id": None if self.dataset_id is None else self.dataset_id.to_dict(),
            "native_id": self.native_id,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RelationshipEndpoint":
        dataset = payload.get("dataset_id")
        return cls(
            object_id=HodgeCYID.from_dict(payload["object_id"]),
            role=str(payload["role"]),
            dataset_id=None if dataset is None else HodgeCYID.from_dict(dataset),
            native_id=payload.get("native_id"),
            label=payload.get("label"),
        )


@dataclass(frozen=True, slots=True)
class RelationshipAssertion:
    relationship_id: HodgeCYID
    relation_type: RelationshipType | str
    endpoints: tuple[RelationshipEndpoint, ...]
    claim_level: ClaimLevel
    directed: bool = True
    provenance_id: str | None = None
    validation_events: tuple[ValidationEvent, ...] = ()
    payload: dict[str, Any] = field(default_factory=dict)
    evidence_type: EvidenceType = EvidenceType.USER_ASSERTED
    join_state: JoinState = JoinState.EXACT_MATCH
    source_dataset: HodgeCYID | None = None
    source_record_id: str | None = None
    source_locator: DistributionLocator | None = None
    source_provenance: SourceProvenance | None = None
    schema: RelationshipSchema = field(default_factory=RelationshipSchema)

    def __post_init__(self) -> None:
        self.relationship_id.require_kind(IdentityKind.DERIVED_OBJECT)
        if len(self.endpoints) < 1:
            raise ValueError("RelationshipAssertion requires at least one endpoint")
        if self.source_dataset is not None:
            self.source_dataset.require_kind(IdentityKind.DATASET)

    @property
    def relationship_type(self) -> str:
        return self.relation_type.value if isinstance(self.relation_type, RelationshipType) else str(self.relation_type)

    @property
    def directionality(self) -> Directionality:
        return Directionality.DIRECTED if self.directed else Directionality.SYMMETRIC

    def to_dict(self) -> dict[str, Any]:
        return {
            "relationship_id": self.relationship_id.to_dict(),
            "relationship_type": self.relationship_type,
            "endpoints": [endpoint.to_dict() for endpoint in self.endpoints],
            "claim_level": self.claim_level.value,
            "directionality": self.directionality.value,
            "directed": self.directed,
            "evidence_type": self.evidence_type.value,
            "join_state": self.join_state.value,
            "source_dataset": None if self.source_dataset is None else self.source_dataset.to_dict(),
            "source_record_id": self.source_record_id,
            "source_locator": None if self.source_locator is None else self.source_locator.to_dict(),
            "source_provenance": None if self.source_provenance is None else self.source_provenance.to_dict(),
            "provenance_id": self.provenance_id,
            "validation_events": [event.to_dict() for event in self.validation_events],
            "payload": self.payload,
            "schema": self.schema.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RelationshipAssertion":
        source_dataset = payload.get("source_dataset")
        source_locator = payload.get("source_locator")
        source_provenance = payload.get("source_provenance")
        directed = bool(payload.get("directed", payload.get("directionality") != Directionality.SYMMETRIC.value))
        return cls(
            relationship_id=HodgeCYID.from_dict(payload["relationship_id"]),
            relation_type=str(payload["relationship_type"]),
            endpoints=tuple(RelationshipEndpoint.from_dict(row) for row in payload.get("endpoints") or ()),
            claim_level=ClaimLevel(payload["claim_level"]),
            directed=directed,
            provenance_id=payload.get("provenance_id"),
            validation_events=tuple(ValidationEvent.from_dict(row) for row in payload.get("validation_events") or ()),
            payload=dict(payload.get("payload") or {}),
            evidence_type=EvidenceType(payload.get("evidence_type", EvidenceType.USER_ASSERTED.value)),
            join_state=JoinState(payload.get("join_state", JoinState.EXACT_MATCH.value)),
            source_dataset=None if source_dataset is None else HodgeCYID.from_dict(source_dataset),
            source_record_id=payload.get("source_record_id"),
            source_locator=None if source_locator is None else DistributionLocator.from_dict(source_locator),
            source_provenance=None if source_provenance is None else SourceProvenance.from_dict(source_provenance),
            schema=RelationshipSchema.from_dict(payload.get("schema") or {}),
        )

    @classmethod
    def build(
        cls,
        *,
        relation_type: RelationshipType | str,
        endpoints: tuple[RelationshipEndpoint, ...],
        claim_level: ClaimLevel,
        evidence_type: EvidenceType,
        directed: bool = True,
        join_state: JoinState = JoinState.EXACT_MATCH,
        source_dataset: HodgeCYID | None = None,
        source_record_id: str | None = None,
        source_locator: DistributionLocator | None = None,
        source_provenance: SourceProvenance | None = None,
        payload: dict[str, Any] | None = None,
    ) -> "RelationshipAssertion":
        relationship_type = relation_type.value if isinstance(relation_type, RelationshipType) else str(relation_type)
        relationship_id = HodgeCYID.derived_from_components(
            IdentityKind.DERIVED_OBJECT,
            "relationship",
            {
                "relationship_type": relationship_type,
                "endpoints": [endpoint.to_dict() for endpoint in endpoints],
                "evidence_type": evidence_type.value,
                "join_state": join_state.value,
                "source_dataset": None if source_dataset is None else source_dataset.serialize(),
                "source_record_id": source_record_id,
                "payload": payload or {},
                "schema": RelationshipSchema().to_dict(),
            },
        )
        return cls(
            relationship_id=relationship_id,
            relation_type=relationship_type,
            endpoints=endpoints,
            claim_level=claim_level,
            directed=directed,
            payload=payload or {},
            evidence_type=evidence_type,
            join_state=join_state,
            source_dataset=source_dataset,
            source_record_id=source_record_id,
            source_locator=source_locator,
            source_provenance=source_provenance,
        )

    def stable_id(self) -> str:
        payload = self.to_dict()
        payload.pop("validation_events", None)
        return stable_sha256(payload)
