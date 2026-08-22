"""Typed HodgeCY II research records.

This module deliberately separates source assembly diagnostics from verified
node relation data and genuine Hodge-atom data. It provides small exact
building blocks for the HodgeCY II pipeline without promoting unresolved
geometry to theorem status.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

import sympy as sp


class EvidenceStatus(str, Enum):
    """Research evidence status for a computed or theoretical object."""

    CONJECTURAL = "conjectural"
    CANDIDATE = "candidate"
    COMPUTATIONALLY_VERIFIED = "computationally_verified"
    THEOREM_READY = "theorem_ready"
    BLOCKED = "blocked"
    UNRESOLVED = "unresolved"


class RealizationStatus(str, Enum):
    """Where an invariant has been realized."""

    SOURCE_ONLY = "SOURCE_ONLY"
    NODE_REALIZED = "NODE_REALIZED"
    HODGE_REALIZED = "HODGE_REALIZED"
    EQUIVARIANT_HODGE_REALIZED = "EQUIVARIANT_HODGE_REALIZED"
    EXTENSION_REALIZED = "EXTENSION_REALIZED"


class FidelityLevel(str, Enum):
    """HodgeCY II fidelity ladder."""

    F0_HODGE_NUMBERS = "F0_HODGE_NUMBERS"
    F1_LOCAL_ATOMS = "F1_LOCAL_ATOMS"
    F2_RATIONAL_RELATIONS = "F2_RATIONAL_RELATIONS"
    F3_INTEGRAL_RELATIONS = "F3_INTEGRAL_RELATIONS"
    F4_EQUIVARIANT_REALIZATION = "F4_EQUIVARIANT_REALIZATION"
    F5_LMHS_EXTENSION = "F5_LMHS_EXTENSION"


class FidelityDepth(str, Enum):
    """Allowed outcomes for the first separating level."""

    F0_HODGE_NUMBERS = "F0_HODGE_NUMBERS"
    F1_LOCAL_ATOMS = "F1_LOCAL_ATOMS"
    F2_RATIONAL_RELATIONS = "F2_RATIONAL_RELATIONS"
    F3_INTEGRAL_RELATIONS = "F3_INTEGRAL_RELATIONS"
    F4_EQUIVARIANT_REALIZATION = "F4_EQUIVARIANT_REALIZATION"
    F5_LMHS_EXTENSION = "F5_LMHS_EXTENSION"
    NO_SEPARATION_DETECTED = "NO_SEPARATION_DETECTED"
    UNRESOLVED = "UNRESOLVED"


class ResultClass(str, Enum):
    """Allowed final result classes for the 84/84a comparison."""

    RATIONAL_FIDELITY = "RATIONAL_FIDELITY"
    INTEGRAL_FIDELITY = "INTEGRAL_FIDELITY"
    EQUIVARIANT_FIDELITY = "EQUIVARIANT_FIDELITY"
    EXTENSION_FIDELITY = "EXTENSION_FIDELITY"
    SOURCE_DISTINCTION_FORGOTTEN = "SOURCE_DISTINCTION_FORGOTTEN"
    PARTIALLY_RESOLVED = "PARTIALLY_RESOLVED"


class GateAEvidenceState(str, Enum):
    """Evidence classification for Gate A ordinary-node promotion."""

    CERTIFICATE_GRADE = "CERTIFICATE_GRADE"
    REPRODUCIBLE_BUT_INCOMPLETE = "REPRODUCIBLE_BUT_INCOMPLETE"
    LOG_ONLY = "LOG_ONLY"
    CLAIM_WITHOUT_REPRODUCIBLE_INPUT = "CLAIM_WITHOUT_REPRODUCIBLE_INPUT"
    STALE_INPUT = "STALE_INPUT"
    INCONSISTENT = "INCONSISTENT"
    IRRELEVANT = "IRRELEVANT"
    UNKNOWN = "UNKNOWN"


GATE_A_REQUIRED_COMPONENTS = (
    "saturated_jacobian_scheme",
    "zero_dimensionality",
    "degree_112",
    "support_matches_28x4_blocks",
    "radicality",
    "geometric_support_count_112",
    "branch_quadratic_rank_3",
    "double_cover_quadratic_rank_4",
    "frozen_exact_node_ideal",
    "reproducible_cas_metadata",
)


@dataclass(frozen=True, slots=True)
class FidelityLayer:
    """One level of a pairwise fidelity comparison."""

    level: FidelityLevel
    left_value: Any
    right_value: Any
    evidence_status: EvidenceStatus
    realization_status: RealizationStatus
    source_label: str | None = None
    notes: str | None = None

    @property
    def separates(self) -> bool:
        return self.left_value != self.right_value

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level.value,
            "left_value": self.left_value,
            "right_value": self.right_value,
            "separates": self.separates,
            "evidence_status": self.evidence_status.value,
            "realization_status": self.realization_status.value,
            "source_label": self.source_label,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class GateAComponent:
    """One required component of ordinary-node verification."""

    name: str
    passed: bool
    evidence_state: GateAEvidenceState
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "evidence_state": self.evidence_state.value,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class GateAPromotionDecision:
    """Promotion decision for one arrangement at Gate A."""

    arrangement_id: str
    current_status: str
    promoted_status: str
    components: tuple[GateAComponent, ...]

    @property
    def can_promote(self) -> bool:
        return all(component.passed for component in self.components)

    @property
    def missing_components(self) -> tuple[str, ...]:
        return tuple(component.name for component in self.components if not component.passed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "arrangement_id": self.arrangement_id,
            "current_status": self.current_status,
            "promoted_status": self.promoted_status,
            "can_promote": self.can_promote,
            "missing_components": list(self.missing_components),
            "components": [component.to_dict() for component in self.components],
        }


@dataclass(frozen=True, slots=True)
class SourceSurvivalProfile:
    """Diagnostic for a source-to-node comparison.

    This is not a Hodge atom spectrum. It is only a record of what is known
    about source relation data after a mathematically specified comparison map.
    """

    arrangement_id: str
    source_relation_rank: int | None
    realized_relation_rank: int | None
    comparison_rank: int | None
    source_smith_normal_form: tuple[int, ...] | None
    realized_smith_normal_form: tuple[int, ...] | None
    surviving_torsion: tuple[int, ...] | None
    kernel_data: Mapping[str, Any] | None
    cokernel_data: Mapping[str, Any] | None
    evidence_status: EvidenceStatus
    realization_status: RealizationStatus
    notes: str
    terminology_guard: str = field(default="source_survival_profile_is_not_hodge_atom_spectrum")

    def to_dict(self) -> dict[str, Any]:
        return {
            "arrangement_id": self.arrangement_id,
            "source_relation_rank": self.source_relation_rank,
            "realized_relation_rank": self.realized_relation_rank,
            "comparison_rank": self.comparison_rank,
            "source_smith_normal_form": list(self.source_smith_normal_form) if self.source_smith_normal_form is not None else None,
            "realized_smith_normal_form": list(self.realized_smith_normal_form) if self.realized_smith_normal_form is not None else None,
            "surviving_torsion": list(self.surviving_torsion) if self.surviving_torsion is not None else None,
            "kernel_data": dict(self.kernel_data) if self.kernel_data is not None else None,
            "cokernel_data": dict(self.cokernel_data) if self.cokernel_data is not None else None,
            "evidence_status": self.evidence_status.value,
            "realization_status": self.realization_status.value,
            "notes": self.notes,
            "terminology_guard": self.terminology_guard,
        }


def first_separating_level(layers: Sequence[FidelityLayer]) -> FidelityDepth:
    """Return the first justified separating level in the given ladder."""

    order = {level: index for index, level in enumerate(FidelityLevel)}
    sorted_layers = sorted(layers, key=lambda layer: order[layer.level])
    saw_unresolved = False
    for layer in sorted_layers:
        if layer.evidence_status in {EvidenceStatus.BLOCKED, EvidenceStatus.UNRESOLVED, EvidenceStatus.CONJECTURAL}:
            saw_unresolved = True
            continue
        if layer.separates:
            return FidelityDepth(layer.level.value)
    return FidelityDepth.UNRESOLVED if saw_unresolved else FidelityDepth.NO_SEPARATION_DETECTED


def beta_block_expansion_matrix(block_count: int, nodes_per_block: int = 4) -> sp.Matrix:
    """Return the exact matrix for beta: Z<blocks> -> Z<nodes>.

    The rows are formal node labels ordered block by block, and the columns are
    source double-line blocks. Every column has ``nodes_per_block`` ones and
    every row has exactly one one.
    """

    if block_count <= 0:
        raise ValueError("block_count must be positive")
    if nodes_per_block <= 0:
        raise ValueError("nodes_per_block must be positive")
    rows = block_count * nodes_per_block
    matrix = sp.zeros(rows, block_count)
    for block_index in range(block_count):
        for local_index in range(nodes_per_block):
            matrix[block_index * nodes_per_block + local_index, block_index] = 1
    return matrix


def source_survival_profile(
    arrangement_id: str,
    *,
    source_relation_rank: int | None,
    source_smith_normal_form: Sequence[int] | None,
    comparison_matrix: sp.Matrix | None = None,
    realized_relation_rank: int | None = None,
    realized_smith_normal_form: Sequence[int] | None = None,
    notes: str | None = None,
) -> SourceSurvivalProfile:
    """Build a conservative source-survival diagnostic."""

    if comparison_matrix is None:
        return SourceSurvivalProfile(
            arrangement_id=arrangement_id,
            source_relation_rank=source_relation_rank,
            realized_relation_rank=realized_relation_rank,
            comparison_rank=None,
            source_smith_normal_form=tuple(source_smith_normal_form) if source_smith_normal_form is not None else None,
            realized_smith_normal_form=tuple(realized_smith_normal_form) if realized_smith_normal_form is not None else None,
            surviving_torsion=None,
            kernel_data=None,
            cokernel_data=None,
            evidence_status=EvidenceStatus.UNRESOLVED,
            realization_status=RealizationStatus.SOURCE_ONLY,
            notes=notes or "No geometrically justified source-to-node comparison map has been supplied.",
        )

    rank = int(comparison_matrix.rank())
    kernel_dim = int(comparison_matrix.cols - rank)
    cokernel_dim = int(comparison_matrix.rows - rank)
    return SourceSurvivalProfile(
        arrangement_id=arrangement_id,
        source_relation_rank=source_relation_rank,
        realized_relation_rank=realized_relation_rank,
        comparison_rank=rank,
        source_smith_normal_form=tuple(source_smith_normal_form) if source_smith_normal_form is not None else None,
        realized_smith_normal_form=tuple(realized_smith_normal_form) if realized_smith_normal_form is not None else None,
        surviving_torsion=None,
        kernel_data={"rank_Q": kernel_dim},
        cokernel_data={"rank_Q": cokernel_dim},
        evidence_status=EvidenceStatus.CANDIDATE,
        realization_status=RealizationStatus.NODE_REALIZED,
        notes=notes or "Comparison matrix supplied; torsion/saturation survival remains to be computed.",
    )


def gate_a_promotion_decision(
    arrangement_id: str,
    *,
    current_status: str,
    passed_components: Mapping[str, bool],
    component_evidence: Mapping[str, GateAEvidenceState] | None = None,
    component_notes: Mapping[str, str] | None = None,
) -> GateAPromotionDecision:
    """Return a conservative ordinary-node promotion decision."""

    evidence = component_evidence or {}
    notes = component_notes or {}
    components = tuple(
        GateAComponent(
            name=component,
            passed=bool(passed_components.get(component, False)),
            evidence_state=evidence.get(component, GateAEvidenceState.UNKNOWN),
            notes=notes.get(component, ""),
        )
        for component in GATE_A_REQUIRED_COMPONENTS
    )
    promoted = "ordinary_node_verified" if all(component.passed for component in components) else current_status
    return GateAPromotionDecision(
        arrangement_id=arrangement_id,
        current_status=current_status,
        promoted_status=promoted,
        components=components,
    )
