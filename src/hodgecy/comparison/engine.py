from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from hodgecy.core.errors import ValidationError
from hodgecy.core.results import ComparisonState, EvidenceStatus, ResultKind
from hodgecy.core.serialization import canonical_json
from hodgecy.storage import CalculationRun, InvariantRecord, ResultStore, RunStatus, SpectrumRecord
from hodgecy.storage.errors import RecordNotFoundError, ResultStoreError

from .models import (
    ComparisonOperand,
    ComparisonPolicy,
    ComparisonResult,
    EquivalenceClass,
    EquivalenceClassResult,
    FirstDifferenceResult,
    PairComparisonReport,
    RefinementLevel,
    RefinementResult,
    RunSelectionPolicy,
    SetComparisonResult,
    comparison_metadata,
)


class ComparisonError(ResultStoreError):
    """Base class for generic comparison failures."""


class AmbiguousResultError(ComparisonError):
    """Raised when historical records leave multiple current values unresolved."""


@dataclass(frozen=True, slots=True)
class SelectedInvariant:
    record: InvariantRecord | None
    operand: ComparisonOperand


def canonical_value(value: Any) -> str:
    return canonical_json(_normalize_value(value))


def _normalize_value(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_normalize_value(item) for item in value]
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _normalize_value(item) for key, item in value.items()}
    return value


class ComparisonEngine:
    def __init__(self, store: ResultStore, policy: ComparisonPolicy | None = None) -> None:
        self.store = store
        self.policy = policy or ComparisonPolicy()

    def compare_invariant(
        self,
        geometry_ids: Sequence[str],
        invariant_name: str,
        *,
        result_kind: ResultKind | None = None,
        calculation_type: str | None = None,
        run_ids: Mapping[str, str] | None = None,
        policy: ComparisonPolicy | None = None,
    ) -> ComparisonResult | SetComparisonResult:
        policy = policy or self.policy
        operands = tuple(
            self._select_invariant(
                geometry_id,
                invariant_name,
                result_kind=result_kind,
                calculation_type=calculation_type,
                run_id=None if run_ids is None else run_ids.get(geometry_id),
                policy=policy,
            ).operand
            for geometry_id in geometry_ids
        )
        result_kind = self._common_result_kind(operands, result_kind)
        if len(operands) == 2:
            return self._pair_result(invariant_name, operands, result_kind, policy)
        return self._set_result(invariant_name, operands, result_kind, policy)

    def compare_pair(
        self,
        left_geometry_id: str,
        right_geometry_id: str,
        *,
        invariants: Sequence[str],
        result_kind: ResultKind | None = None,
        calculation_type: str | None = None,
        run_ids: Mapping[str, str] | None = None,
        policy: ComparisonPolicy | None = None,
    ) -> PairComparisonReport:
        policy = policy or self.policy
        results = tuple(
            self.compare_invariant(
                (left_geometry_id, right_geometry_id),
                invariant,
                result_kind=result_kind,
                calculation_type=calculation_type,
                run_ids=run_ids,
                policy=policy,
            )
            for invariant in invariants
        )
        pair_results = tuple(result for result in results if isinstance(result, ComparisonResult))
        first = next((result.comparison_key for result in pair_results if result.state is ComparisonState.DIFFERENT), None)
        return PairComparisonReport(
            left_geometry_id,
            right_geometry_id,
            pair_results,
            first,
            comparison_metadata((left_geometry_id, right_geometry_id), policy, tuple(invariants)),
        )

    def compare_set(
        self,
        comparison_set_id: str,
        *,
        invariants: Sequence[str],
        result_kind: ResultKind | None = None,
        calculation_type: str | None = None,
        policy: ComparisonPolicy | None = None,
    ) -> tuple[SetComparisonResult, ...]:
        comparison_set = self.store.get_comparison_set(comparison_set_id)
        return tuple(
            result
            for result in (
                self.compare_invariant(
                    comparison_set.member_geometry_ids,
                    invariant,
                    result_kind=result_kind,
                    calculation_type=calculation_type,
                    policy=policy,
                )
                for invariant in invariants
            )
            if isinstance(result, SetComparisonResult)
        )

    def group_by_invariants(
        self,
        geometry_ids: Sequence[str],
        invariants: Sequence[str],
        *,
        result_kind: ResultKind | None = None,
        calculation_type: str | None = None,
        policy: ComparisonPolicy | None = None,
    ) -> EquivalenceClassResult:
        policy = policy or self.policy
        groups: dict[str, list[str]] = {}
        group_values: dict[str, dict[str, Any]] = {}
        unresolved: list[str] = []
        for geometry_id in geometry_ids:
            values: dict[str, Any] = {}
            unknown = False
            for invariant in invariants:
                operand = self._select_invariant(geometry_id, invariant, result_kind=result_kind, calculation_type=calculation_type, policy=policy).operand
                if self._is_unknown_operand(operand, policy):
                    unknown = True
                    break
                values[invariant] = operand.value
            if unknown:
                unresolved.append(geometry_id)
                continue
            key = canonical_value(values)
            groups.setdefault(key, []).append(geometry_id)
            group_values.setdefault(key, values)
        classes = tuple(EquivalenceClass(key, tuple(members), group_values[key]) for key, members in sorted(groups.items()))
        return EquivalenceClassResult(
            tuple(invariants),
            classes,
            tuple(unresolved),
            comparison_metadata(tuple(geometry_ids), policy, tuple(invariants)),
        )

    def classify(
        self,
        geometry_ids: Sequence[str],
        levels: Sequence[Sequence[str]],
        *,
        result_kind: ResultKind | None = None,
        calculation_type: str | None = None,
        policy: ComparisonPolicy | None = None,
    ) -> RefinementResult:
        policy = policy or self.policy
        refinement_levels: list[RefinementLevel] = []
        cumulative: list[str] = []
        for index, level in enumerate(levels):
            cumulative.extend(level)
            grouped = self.group_by_invariants(
                geometry_ids,
                tuple(cumulative),
                result_kind=result_kind,
                calculation_type=calculation_type,
                policy=policy,
            )
            refinement_levels.append(RefinementLevel(index, tuple(cumulative), grouped.classes, grouped.unresolved_members))
        return RefinementResult(tuple(refinement_levels), comparison_metadata(tuple(geometry_ids), policy))

    def first_difference(
        self,
        geometry_ids: Sequence[str],
        ordered_invariants: Sequence[str],
        *,
        result_kind: ResultKind | None = None,
        calculation_type: str | None = None,
        policy: ComparisonPolicy | None = None,
    ) -> FirstDifferenceResult:
        policy = policy or self.policy
        checked: list[ComparisonResult | SetComparisonResult] = []
        for invariant in ordered_invariants:
            result = self.compare_invariant(
                geometry_ids,
                invariant,
                result_kind=result_kind,
                calculation_type=calculation_type,
                policy=policy,
            )
            checked.append(result)
            if result.state is ComparisonState.DIFFERENT:
                return FirstDifferenceResult(invariant, ComparisonState.DIFFERENT, f"{invariant} separates the geometries", tuple(checked), comparison_metadata(tuple(geometry_ids), policy, tuple(ordered_invariants)))
            if result.state is ComparisonState.UNKNOWN:
                return FirstDifferenceResult(None, ComparisonState.UNKNOWN, f"{invariant} is unknown and comparison did not skip unknown levels", tuple(checked), comparison_metadata(tuple(geometry_ids), policy, tuple(ordered_invariants)))
            if result.state is ComparisonState.INCOMPARABLE:
                return FirstDifferenceResult(None, ComparisonState.INCOMPARABLE, f"{invariant} is incomparable", tuple(checked), comparison_metadata(tuple(geometry_ids), policy, tuple(ordered_invariants)))
        return FirstDifferenceResult(None, ComparisonState.EQUAL, "all compared invariants equal", tuple(checked), comparison_metadata(tuple(geometry_ids), policy, tuple(ordered_invariants)))

    def compare_spectra(self, left_spectrum_id: str, right_spectrum_id: str) -> ComparisonResult:
        left = self.store.get_spectrum_record(left_spectrum_id)
        right = self.store.get_spectrum_record(right_spectrum_id)
        operands = (
            self._spectrum_operand(left),
            self._spectrum_operand(right),
        )
        metadata = comparison_metadata((left.geometry_id, right.geometry_id), self.policy, ("spectrum",))
        metadata["spectrum_ids"] = [left_spectrum_id, right_spectrum_id]
        if left.result_kind is not right.result_kind or left.concrete_type != right.concrete_type:
            return ComparisonResult(
                "spectrum",
                ComparisonState.INCOMPARABLE,
                operands,
                None,
                "spectra have different mathematical kinds or concrete spectrum types",
                {"left_concrete_type": left.concrete_type, "right_concrete_type": right.concrete_type},
                metadata,
            )
        if left.content_hash == right.content_hash:
            return ComparisonResult(
                "spectrum",
                ComparisonState.EQUAL,
                operands,
                left.result_kind,
                "spectrum content hashes match",
                {"content_hash_equal": True},
                metadata,
            )
        differences = self._field_differences(self._comparable_spectrum_payload(left.payload), self._comparable_spectrum_payload(right.payload))
        state = ComparisonState.EQUAL if not differences else ComparisonState.DIFFERENT
        return ComparisonResult(
            "spectrum",
            state,
            operands,
            left.result_kind,
            "spectrum payloads differ" if differences else "spectrum mathematical payloads equal; stored hashes differ because record metadata differs",
            {"content_hash_equal": False, "field_differences": differences},
            metadata,
        )

    def _select_invariant(
        self,
        geometry_id: str,
        invariant_name: str,
        *,
        result_kind: ResultKind | None,
        calculation_type: str | None = None,
        run_id: str | None = None,
        policy: ComparisonPolicy,
    ) -> SelectedInvariant:
        if run_id is not None:
            run = self.store.get_run(run_id)
            if run.geometry_id != geometry_id:
                raise ValidationError(f"Run {run_id!r} belongs to {run.geometry_id!r}, not {geometry_id!r}")
            records = [record for record in self.store.get_invariants(geometry_id=geometry_id, name=invariant_name, result_kind=result_kind) if record.run_id == run_id]
        else:
            records = self._candidate_invariant_records(geometry_id, invariant_name, result_kind, calculation_type, policy)
        if not records:
            return SelectedInvariant(None, ComparisonOperand(geometry_id, None, EvidenceStatus.UNKNOWN, result_kind=result_kind, reason="invariant not found"))
        record = self._choose_record(records, policy)
        return SelectedInvariant(
            record,
            ComparisonOperand(
                geometry_id=geometry_id,
                value=record.value,
                status=record.evidence_status,
                result_kind=record.result_kind,
                run_id=record.run_id,
                record_id=record.invariant_id,
                content_hash=record.content_hash,
            ),
        )

    def _candidate_invariant_records(
        self,
        geometry_id: str,
        invariant_name: str,
        result_kind: ResultKind | None,
        calculation_type: str | None,
        policy: ComparisonPolicy,
    ) -> list[InvariantRecord]:
        records = list(self.store.get_invariants(geometry_id=geometry_id, name=invariant_name, result_kind=result_kind))
        completed_runs = {
            run.run_id: run
            for run in self.store.get_runs(geometry_id=geometry_id, calculation_type=calculation_type)
            if run.status is RunStatus.COMPLETED
        }
        if policy.run_selection is RunSelectionPolicy.ALL_CURRENT_STRICT:
            return [record for record in records if record.run_id in completed_runs]
        if policy.run_selection is RunSelectionPolicy.EXPLICIT_RUN_IDS:
            raise ValidationError("EXPLICIT_RUN_IDS policy requires run_ids to be supplied")
        current_records = [record for record in records if record.run_id in completed_runs]
        if not current_records:
            return []
        latest_run_id = max(
            {record.run_id for record in current_records},
            key=lambda item: (completed_runs[item].completed_at or completed_runs[item].started_at, item),
        )
        return [record for record in current_records if record.run_id == latest_run_id]

    def _choose_record(self, records: Sequence[InvariantRecord], policy: ComparisonPolicy) -> InvariantRecord:
        if len(records) == 1:
            return records[0]
        distinct = {canonical_value(record.value): record.value for record in records}
        statuses = {record.evidence_status for record in records}
        if policy.run_selection is RunSelectionPolicy.ALL_CURRENT_STRICT and len(distinct) > 1:
            raise AmbiguousResultError("multiple current completed runs provide conflicting invariant values")
        if len(distinct) > 1:
            raise AmbiguousResultError("multiple records provide conflicting invariant values")
        return sorted(records, key=lambda record: record.invariant_id)[-1]

    def _pair_result(self, invariant_name: str, operands: tuple[ComparisonOperand, ...], result_kind: ResultKind | None, policy: ComparisonPolicy) -> ComparisonResult:
        state, reason = self._state_for_operands(operands, policy)
        return ComparisonResult(
            invariant_name,
            state,
            operands,
            result_kind,
            reason,
            {
                "statuses": [operand.status.value for operand in operands],
                "content_hashes": [operand.content_hash for operand in operands],
            },
            comparison_metadata(tuple(operand.geometry_id for operand in operands), policy, (invariant_name,)),
        )

    def _set_result(self, invariant_name: str, operands: tuple[ComparisonOperand, ...], result_kind: ResultKind | None, policy: ComparisonPolicy) -> SetComparisonResult:
        unknown_members = tuple(operand.geometry_id for operand in operands if self._is_unknown_operand(operand, policy))
        groups: dict[str, list[str]] = {}
        distinct_values: dict[str, Any] = {}
        for operand in operands:
            if operand.geometry_id in unknown_members:
                continue
            key = canonical_value(operand.value)
            groups.setdefault(key, []).append(operand.geometry_id)
            distinct_values.setdefault(key, operand.value)
        if len(groups) > 1:
            state = ComparisonState.DIFFERENT
            reason = "comparable values split into multiple equivalence groups"
        elif unknown_members:
            state = ComparisonState.UNKNOWN
            reason = "one or more members have unknown or insufficiently evidenced values and no known split was detected"
        elif len(groups) <= 1:
            state = ComparisonState.EQUAL
            reason = "all comparable values are equal"
        else:
            state = ComparisonState.UNKNOWN
            reason = "no comparable values are available"
        return SetComparisonResult(
            invariant_name,
            state,
            result_kind,
            operands,
            distinct_values,
            {key: tuple(value) for key, value in sorted(groups.items())},
            unknown_members,
            reason,
            comparison_metadata(tuple(operand.geometry_id for operand in operands), policy, (invariant_name,)),
        )

    def _state_for_operands(self, operands: tuple[ComparisonOperand, ...], policy: ComparisonPolicy) -> tuple[ComparisonState, str]:
        kinds = {operand.result_kind for operand in operands if operand.result_kind is not None}
        if len(kinds) > 1:
            return ComparisonState.INCOMPARABLE, "operands have different result kinds"
        if any(self._is_unknown_operand(operand, policy) for operand in operands):
            return ComparisonState.UNKNOWN, "one or more operands have unknown or insufficiently evidenced values"
        values = {canonical_value(operand.value) for operand in operands}
        if len(values) == 1:
            return ComparisonState.EQUAL, "canonical values are equal"
        return ComparisonState.DIFFERENT, "canonical values differ"

    def _is_unknown_operand(self, operand: ComparisonOperand, policy: ComparisonPolicy) -> bool:
        if policy.treat_unknown_as_value:
            return False
        if operand.status in policy.unknown_statuses:
            return True
        if policy.require_verified and operand.status is not EvidenceStatus.VERIFIED:
            return True
        if not policy.allow_imported and operand.status is EvidenceStatus.IMPORTED:
            return True
        if not policy.compare_assumed and operand.status is EvidenceStatus.ASSUMED:
            return True
        if operand.status is EvidenceStatus.UNKNOWN:
            return True
        return False

    @staticmethod
    def _common_result_kind(operands: tuple[ComparisonOperand, ...], requested: ResultKind | None) -> ResultKind | None:
        kinds = {operand.result_kind for operand in operands if operand.result_kind is not None}
        if requested is not None:
            kinds.add(requested)
        return next(iter(kinds)) if len(kinds) == 1 else None

    @staticmethod
    def _spectrum_operand(record: SpectrumRecord) -> ComparisonOperand:
        return ComparisonOperand(
            geometry_id=record.geometry_id,
            value=record.payload,
            status=record.evidence_status,
            result_kind=record.result_kind,
            run_id=record.run_id,
            record_id=record.spectrum_id,
            content_hash=record.content_hash,
        )

    @staticmethod
    def _field_differences(left: Any, right: Any, prefix: str = "") -> list[dict[str, Any]]:
        if isinstance(left, dict) and isinstance(right, dict):
            differences: list[dict[str, Any]] = []
            for key in sorted(set(left) | set(right)):
                path = f"{prefix}.{key}" if prefix else str(key)
                if key not in left or key not in right:
                    differences.append({"field": path, "left": left.get(key), "right": right.get(key)})
                else:
                    differences.extend(ComparisonEngine._field_differences(left[key], right[key], path))
            return differences
        if canonical_value(left) != canonical_value(right):
            return [{"field": prefix or "$", "left": left, "right": right}]
        return []

    @staticmethod
    def _comparable_spectrum_payload(payload: dict[str, Any]) -> dict[str, Any]:
        comparable = dict(payload)
        metadata = dict(comparable.get("metadata") or {})
        metadata.pop("geometry_id", None)
        comparable["metadata"] = metadata
        return comparable
