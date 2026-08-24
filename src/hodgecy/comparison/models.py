from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from hodgecy import __version__ as HODGECY_VERSION
from hodgecy.core.results import ComparisonState, EvidenceStatus, ResultKind
from hodgecy.core.serialization import canonical_json
from hodgecy.storage.models import utc_now_iso

COMPARISON_SCHEMA_VERSION = "comparison_result.v1"


class RunSelectionPolicy(str, Enum):
    LATEST_COMPLETED_NON_SUPERSEDED = "latest_completed_non_superseded"
    ALL_CURRENT_STRICT = "all_current_strict"
    EXPLICIT_RUN_IDS = "explicit_run_ids"


@dataclass(frozen=True, slots=True)
class ComparisonPolicy:
    run_selection: RunSelectionPolicy = RunSelectionPolicy.LATEST_COMPLETED_NON_SUPERSEDED
    require_verified: bool = False
    allow_imported: bool = True
    compare_assumed: bool = True
    unknown_statuses: tuple[EvidenceStatus, ...] = (EvidenceStatus.UNKNOWN, EvidenceStatus.CONJECTURAL)
    treat_unknown_as_value: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_selection": self.run_selection.value,
            "require_verified": self.require_verified,
            "allow_imported": self.allow_imported,
            "compare_assumed": self.compare_assumed,
            "unknown_statuses": [status.value for status in self.unknown_statuses],
            "treat_unknown_as_value": self.treat_unknown_as_value,
        }


@dataclass(frozen=True, slots=True)
class ComparisonOperand:
    geometry_id: str
    value: Any
    status: EvidenceStatus
    result_kind: ResultKind | None = None
    run_id: str | None = None
    record_id: str | None = None
    content_hash: str | None = None
    reason: str | None = None

    def canonical_value(self) -> str:
        return canonical_json(self.value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "geometry_id": self.geometry_id,
            "value": self.value,
            "status": self.status.value,
            "result_kind": None if self.result_kind is None else self.result_kind.value,
            "run_id": self.run_id,
            "record_id": self.record_id,
            "content_hash": self.content_hash,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    comparison_key: str
    state: ComparisonState
    operands: tuple[ComparisonOperand, ...]
    result_kind: ResultKind | None = None
    reason: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = COMPARISON_SCHEMA_VERSION

    @property
    def left_value(self) -> Any:
        return self.operands[0].value if self.operands else None

    @property
    def right_value(self) -> Any:
        return self.operands[1].value if len(self.operands) > 1 else None

    @property
    def left_status(self) -> EvidenceStatus | None:
        return self.operands[0].status if self.operands else None

    @property
    def right_status(self) -> EvidenceStatus | None:
        return self.operands[1].status if len(self.operands) > 1 else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "comparison_key": self.comparison_key,
            "state": self.state.value,
            "operands": [operand.to_dict() for operand in self.operands],
            "result_kind": None if self.result_kind is None else self.result_kind.value,
            "reason": self.reason,
            "evidence": self.evidence,
            "metadata": self.metadata,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class SetComparisonResult:
    comparison_key: str
    state: ComparisonState
    result_kind: ResultKind | None
    operands: tuple[ComparisonOperand, ...]
    distinct_values: dict[str, Any]
    equivalence_groups: dict[str, tuple[str, ...]]
    unknown_members: tuple[str, ...] = ()
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = COMPARISON_SCHEMA_VERSION

    @property
    def all_equal(self) -> bool:
        return self.state is ComparisonState.EQUAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "comparison_key": self.comparison_key,
            "state": self.state.value,
            "result_kind": None if self.result_kind is None else self.result_kind.value,
            "operands": [operand.to_dict() for operand in self.operands],
            "distinct_values": self.distinct_values,
            "equivalence_groups": {key: list(value) for key, value in self.equivalence_groups.items()},
            "unknown_members": list(self.unknown_members),
            "all_equal": self.all_equal,
            "reason": self.reason,
            "metadata": self.metadata,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class PairComparisonReport:
    left_geometry_id: str
    right_geometry_id: str
    invariant_results: tuple[ComparisonResult, ...]
    first_difference: str | None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "left_geometry_id": self.left_geometry_id,
            "right_geometry_id": self.right_geometry_id,
            "invariant_results": [result.to_dict() for result in self.invariant_results],
            "first_difference": self.first_difference,
            "metadata": self.metadata,
        }

    def to_markdown(self) -> str:
        lines = [f"# {self.left_geometry_id} vs {self.right_geometry_id}", "", "| Invariant | State |", "| --- | --- |"]
        for result in self.invariant_results:
            lines.append(f"| {result.comparison_key} | {result.state.value} |")
        lines.extend(["", f"First distinction: {self.first_difference or 'None'}", ""])
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class EquivalenceClass:
    class_key: str
    member_geometry_ids: tuple[str, ...]
    values: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"class_key": self.class_key, "member_geometry_ids": list(self.member_geometry_ids), "values": self.values}


@dataclass(frozen=True, slots=True)
class EquivalenceClassResult:
    invariant_names: tuple[str, ...]
    classes: tuple[EquivalenceClass, ...]
    unresolved_members: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "invariant_names": list(self.invariant_names),
            "classes": [item.to_dict() for item in self.classes],
            "unresolved_members": list(self.unresolved_members),
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class RefinementLevel:
    level_index: int
    invariant_names: tuple[str, ...]
    classes: tuple[EquivalenceClass, ...]
    unresolved_members: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "level_index": self.level_index,
            "invariant_names": list(self.invariant_names),
            "classes": [item.to_dict() for item in self.classes],
            "unresolved_members": list(self.unresolved_members),
        }


@dataclass(frozen=True, slots=True)
class RefinementResult:
    levels: tuple[RefinementLevel, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"levels": [level.to_dict() for level in self.levels], "metadata": self.metadata}


@dataclass(frozen=True, slots=True)
class FirstDifferenceResult:
    first_difference: str | None
    state: ComparisonState
    reason: str
    checked: tuple[ComparisonResult | SetComparisonResult, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "first_difference": self.first_difference,
            "state": self.state.value,
            "reason": self.reason,
            "checked": [item.to_dict() for item in self.checked],
            "metadata": self.metadata,
        }


def comparison_metadata(geometry_ids: tuple[str, ...], policy: ComparisonPolicy, invariant_names: tuple[str, ...] = ()) -> dict[str, Any]:
    return {
        "comparison_time": utc_now_iso(),
        "geometry_ids": list(geometry_ids),
        "invariant_names": list(invariant_names),
        "comparison_policy": policy.to_dict(),
        "schema_version": COMPARISON_SCHEMA_VERSION,
        "hodgecy_version": HODGECY_VERSION,
    }
