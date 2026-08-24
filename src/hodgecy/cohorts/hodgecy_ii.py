from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hodgecy.comparison import ComparisonEngine, FirstDifferenceResult, PairComparisonReport, RefinementResult, SetComparisonResult
from hodgecy.core.results import EvidenceStatus, ResultKind
from hodgecy.core.serialization import canonical_json, stable_sha256
from hodgecy.storage import CalculationRun, ComparisonSetRecord, GeometryRecord, InvariantRecord, ResultStore
from hodgecy.storage.errors import RecordNotFoundError

LOCAL_INVENTORY_FIELDS = ("p3", "p4_0", "p4_1", "p5_0", "p5_1", "p5_2", "l3")
MANIFEST_RELATIVE_PATH = Path("data") / "cohorts" / "hodgecy_ii.json"

SOURCE_INVARIANTS = (
    "local_inventory",
    "matrix_shape",
    "rank_Q",
    "rank_mod_2",
    "rank_mod_3",
    "kernel_dim_Q",
    "cokernel_dim_Q",
    "integral_kernel_rank",
    "integral_cokernel_decomposition",
    "smith_normal_form",
    "automorphism_group_order",
    "plane_orbit_sizes",
    "double_line_orbit_sizes",
    "multiple_point_orbit_sizes",
    "character_C1_distribution",
    "character_C0_distribution",
)

HODGE_INVARIANTS = ("h11", "h12", "euler")
UNKNOWN_LATER_INVARIANTS = (
    ("node_relation_rank", ResultKind.NODE_RELATION),
    ("classical_defect", ResultKind.NODE_GEOMETRY),
    ("conifold_atom_spectrum", ResultKind.CONIFOLD_ATOM),
)

PAIR_ORDER = HODGE_INVARIANTS + SOURCE_INVARIANTS + tuple(name for name, _ in UNKNOWN_LATER_INVARIANTS)
PAIR_AVAILABLE_FIRST_DIFFERENCE_ORDER = HODGE_INVARIANTS + SOURCE_INVARIANTS
SOURCE_REFINEMENT_LEVELS = (
    ("local_inventory",),
    ("rank_Q", "kernel_dim_Q", "cokernel_dim_Q"),
    ("smith_normal_form", "integral_cokernel_decomposition"),
    ("automorphism_group_order", "plane_orbit_sizes", "double_line_orbit_sizes", "multiple_point_orbit_sizes"),
    ("character_C1_distribution", "character_C0_distribution"),
)


@dataclass(frozen=True, slots=True)
class HodgeCYIICohortIngestResult:
    manifest: dict[str, Any]
    geometries: tuple[GeometryRecord, ...]
    comparison_sets: tuple[ComparisonSetRecord, ...]
    runs: tuple[CalculationRun, ...]
    invariant_names: tuple[str, ...]
    additional_documented_members: tuple[str, ...]
    excluded_documented_records: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "cohort_id": self.manifest["cohort_id"],
            "geometries": [geometry.to_dict() for geometry in self.geometries],
            "comparison_sets": [comparison_set.to_dict() for comparison_set in self.comparison_sets],
            "runs": [run.to_dict() for run in self.runs],
            "invariant_names": list(self.invariant_names),
            "additional_documented_members": list(self.additional_documented_members),
            "excluded_documented_records": list(self.excluded_documented_records),
        }


@dataclass(frozen=True, slots=True)
class HodgeCYIIBaselineResult:
    ingest: HodgeCYIICohortIngestResult
    pair_84_report: PairComparisonReport
    pair_84_first_available_difference: FirstDifferenceResult
    set_239_241_results: tuple[SetComparisonResult, ...]
    set_239_241_refinement: RefinementResult
    set_239_241_first_split: FirstDifferenceResult
    source_cohort_refinement: RefinementResult
    source_cohort_first_split: FirstDifferenceResult
    report_paths: tuple[Path, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ingest": self.ingest.to_dict(),
            "pair_84_report": self.pair_84_report.to_dict(),
            "pair_84_first_available_difference": self.pair_84_first_available_difference.to_dict(),
            "set_239_241_results": [result.to_dict() for result in self.set_239_241_results],
            "set_239_241_refinement": self.set_239_241_refinement.to_dict(),
            "set_239_241_first_split": self.set_239_241_first_split.to_dict(),
            "source_cohort_refinement": self.source_cohort_refinement.to_dict(),
            "source_cohort_first_split": self.source_cohort_first_split.to_dict(),
            "report_paths": [path.as_posix() for path in self.report_paths],
        }


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_hodgecy_ii_manifest(path: str | Path | None = None) -> dict[str, Any]:
    manifest_path = Path(path) if path is not None else repo_root() / MANIFEST_RELATIVE_PATH
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def ingest_hodgecy_ii_cohort(store: ResultStore, *, manifest_path: str | Path | None = None, root: str | Path | None = None) -> HodgeCYIICohortIngestResult:
    root_path = Path(root) if root is not None else repo_root()
    manifest = load_hodgecy_ii_manifest(manifest_path)
    arrangement_to_geometry = {member["arrangement_id"]: member["geometry_id"] for member in manifest["members"]}
    geometries: list[GeometryRecord] = []
    runs: list[CalculationRun] = []
    invariant_names: set[str] = set()

    for member in manifest["members"]:
        summary_path = root_path / member["summary_path"]
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        geometry = store.add_geometry(
            geometry_id=member["geometry_id"],
            display_name=member["display_name"],
            geometry_type=member["geometry_type"],
            source_dataset=member.get("source_dataset"),
            source_dataset_version=member.get("source_dataset_version"),
            source_entry_id=member.get("source_entry_id"),
            metadata={
                "arrangement_id": member["arrangement_id"],
                "summary_path": member["summary_path"],
                "cohort_id": manifest["cohort_id"],
            },
            provenance=member.get("provenance"),
        )
        geometries.append(geometry)
        run = store.begin_run(
            geometry_id=geometry.geometry_id,
            calculation_type="hodgecy_ii_source_baseline",
            input_metadata={"manifest": manifest["cohort_id"], "summary_sha256": stable_sha256(summary), "summary_path": member["summary_path"]},
            parameters={"ingest_scope": "source_and_coarse_baseline_only"},
            backend="hodgecy.cohorts.hodgecy_ii",
            coefficient_ring="mixed/source",
            environment_metadata={"manifest_path": str(manifest_path or MANIFEST_RELATIVE_PATH)},
            notes="Immutable import run for HodgeCY II source/coarse baseline; reruns create historical import records.",
        )
        for record in _records_from_summary(run.run_id, geometry.geometry_id, summary, member):
            store.record_invariant(**record)
            invariant_names.add(record["name"])
        runs.append(store.complete_run(run.run_id))

    comparison_sets = tuple(_ensure_comparison_set(store, item, arrangement_to_geometry) for item in manifest["comparison_sets"])
    return HodgeCYIICohortIngestResult(
        manifest=manifest,
        geometries=tuple(geometries),
        comparison_sets=comparison_sets,
        runs=tuple(runs),
        invariant_names=tuple(sorted(invariant_names)),
        additional_documented_members=(),
        excluded_documented_records=tuple(manifest.get("excluded_explicit_records") or ()),
    )


def baseline_hodgecy_ii_comparison(
    store: ResultStore,
    *,
    manifest_path: str | Path | None = None,
    root: str | Path | None = None,
    report_dir: str | Path | None = None,
) -> HodgeCYIIBaselineResult:
    ingest = ingest_hodgecy_ii_cohort(store, manifest_path=manifest_path, root=root)
    manifest = ingest.manifest
    arrangement_to_geometry = {member["arrangement_id"]: member["geometry_id"] for member in manifest["members"]}
    comparison_set_ids = {item["comparison_set_id"]: item for item in manifest["comparison_sets"]}
    engine = ComparisonEngine(store)

    pair_members = tuple(arrangement_to_geometry[item] for item in comparison_set_ids["hodgecy-ii-84-pair"]["members"])
    set_members = tuple(arrangement_to_geometry[item] for item in comparison_set_ids["hodgecy-ii-239-241"]["members"])
    source_members = tuple(arrangement_to_geometry[item] for item in comparison_set_ids["hodgecy-ii-source-cohort"]["members"])

    pair_report = engine.compare_pair(pair_members[0], pair_members[1], invariants=PAIR_ORDER)
    pair_first = engine.first_difference(pair_members, PAIR_AVAILABLE_FIRST_DIFFERENCE_ORDER)
    set_results = tuple(engine.compare_invariant(set_members, invariant) for invariant in SOURCE_INVARIANTS)
    set_results = tuple(result for result in set_results if isinstance(result, SetComparisonResult))
    set_refinement = engine.classify(set_members, SOURCE_REFINEMENT_LEVELS)
    set_first = engine.first_difference(set_members, tuple(name for level in SOURCE_REFINEMENT_LEVELS for name in level))
    source_refinement = engine.classify(source_members, SOURCE_REFINEMENT_LEVELS)
    source_first = engine.first_difference(source_members, tuple(name for level in SOURCE_REFINEMENT_LEVELS for name in level))

    paths: tuple[Path, ...] = ()
    if report_dir is not None:
        paths = _write_reports(
            Path(report_dir),
            pair_report=pair_report,
            pair_first=pair_first,
            set_results=set_results,
            set_refinement=set_refinement,
            set_first=set_first,
            source_refinement=source_refinement,
            source_first=source_first,
        )

    return HodgeCYIIBaselineResult(ingest, pair_report, pair_first, set_results, set_refinement, set_first, source_refinement, source_first, paths)


def _records_from_summary(run_id: str, geometry_id: str, summary: dict[str, Any], member: dict[str, Any]) -> list[dict[str, Any]]:
    provenance = f"imported from {member['summary_path']}"
    records: list[dict[str, Any]] = []
    hodge_data = summary.get("hodge_data")
    for name in HODGE_INVARIANTS:
        records.append(
            {
                "run_id": run_id,
                "name": name,
                "value": None if hodge_data is None else hodge_data.get(name),
                "result_kind": ResultKind.HODGE_DATA,
                "evidence_status": EvidenceStatus.UNKNOWN if hodge_data is None else EvidenceStatus.IMPORTED,
                "method": "release theorem summary import",
                "provenance": provenance,
                "notes": "coarse imported Hodge datum" if hodge_data is not None else "hodge datum unavailable in source summary",
            }
        )

    local_inventory = dict(zip(LOCAL_INVENTORY_FIELDS, summary["local_inventory"]))
    source_values = {
        "local_inventory": local_inventory,
        "matrix_shape": summary.get("matrix_shape"),
        "rank_Q": summary.get("rank_Q"),
        "rank_mod_2": summary.get("rank_mod_2"),
        "rank_mod_3": summary.get("rank_mod_3"),
        "kernel_dim_Q": summary.get("kernel_dim_Q"),
        "cokernel_dim_Q": summary.get("cokernel_dim_Q"),
        "integral_kernel_rank": summary.get("integral_kernel_rank"),
        "integral_cokernel_decomposition": summary.get("integral_cokernel_decomposition"),
        "smith_normal_form": summary.get("smith_normal_form"),
        "automorphism_group_order": summary.get("automorphism_group_order"),
        "plane_orbit_sizes": summary.get("plane_orbit_sizes"),
        "double_line_orbit_sizes": summary.get("double_line_orbit_sizes"),
        "multiple_point_orbit_sizes": summary.get("multiple_point_orbit_sizes"),
        "character_C1_distribution": summary.get("character_C1_distribution"),
        "character_C0_distribution": summary.get("character_C0_distribution"),
    }
    for name, value in source_values.items():
        records.append(
            {
                "run_id": run_id,
                "name": name,
                "value": value,
                "result_kind": ResultKind.SOURCE_ASSEMBLY,
                "evidence_status": EvidenceStatus.IMPORTED,
                "method": "release theorem summary import",
                "provenance": provenance,
                "notes": "SOURCE-level arrangement/source invariant; not a node-relation or Hodge-atom result",
            }
        )

    for name, result_kind in UNKNOWN_LATER_INVARIANTS:
        records.append(
            {
                "run_id": run_id,
                "name": name,
                "value": None,
                "result_kind": result_kind,
                "evidence_status": EvidenceStatus.UNKNOWN,
                "method": None,
                "provenance": provenance,
                "notes": "not computed in Blob 4; placeholder preserves mathematical level without promotion",
            }
        )
    return records


def _ensure_comparison_set(store: ResultStore, item: dict[str, Any], arrangement_to_geometry: dict[str, str]) -> ComparisonSetRecord:
    comparison_set_id = item["comparison_set_id"]
    try:
        return store.get_comparison_set(comparison_set_id)
    except RecordNotFoundError:
        return store.create_comparison_set(
            comparison_set_id=comparison_set_id,
            display_name=item["display_name"],
            member_geometry_ids=[arrangement_to_geometry[member] for member in item["members"]],
            selection_criterion=item.get("selection_criterion"),
            notes=item.get("notes"),
        )


def _write_reports(
    report_dir: Path,
    *,
    pair_report: PairComparisonReport,
    pair_first: FirstDifferenceResult,
    set_results: tuple[SetComparisonResult, ...],
    set_refinement: RefinementResult,
    set_first: FirstDifferenceResult,
    source_refinement: RefinementResult,
    source_first: FirstDifferenceResult,
) -> tuple[Path, ...]:
    report_dir.mkdir(parents=True, exist_ok=True)
    pair_payload = {
        "pair_report": pair_report.to_dict(),
        "first_current_available_distinction": pair_first.to_dict(),
    }
    set_payload = {
        "set_results": [result.to_dict() for result in set_results],
        "refinement": set_refinement.to_dict(),
        "first_split": set_first.to_dict(),
    }
    source_payload = {
        "refinement": source_refinement.to_dict(),
        "first_split": source_first.to_dict(),
    }
    paths = (
        report_dir / "hodgecy_ii_84_pair_baseline.json",
        report_dir / "hodgecy_ii_239_241_baseline.json",
        report_dir / "hodgecy_ii_source_cohort_baseline.json",
        report_dir / "hodgecy_ii_84_pair_baseline.md",
        report_dir / "hodgecy_ii_239_241_baseline.md",
        report_dir / "hodgecy_ii_source_cohort_baseline.md",
    )
    paths[0].write_text(_deterministic_json(pair_payload) + "\n", encoding="utf-8")
    paths[1].write_text(_deterministic_json(set_payload) + "\n", encoding="utf-8")
    paths[2].write_text(_deterministic_json(source_payload) + "\n", encoding="utf-8")
    paths[3].write_text(_pair_markdown(pair_report, pair_first), encoding="utf-8")
    paths[4].write_text(_set_markdown("HodgeCY II Baseline - 239 / 240 / 241", set_results, set_refinement, set_first), encoding="utf-8")
    paths[5].write_text(_refinement_markdown("HodgeCY II Baseline - source cohort", source_refinement, source_first), encoding="utf-8")
    return paths


def _deterministic_json(payload: dict[str, Any]) -> str:
    return canonical_json(_strip_comparison_times(payload))


def _strip_comparison_times(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _strip_comparison_times(item) for key, item in value.items() if key != "comparison_time"}
    if isinstance(value, list):
        return [_strip_comparison_times(item) for item in value]
    return value


def _pair_markdown(report: PairComparisonReport, first: FirstDifferenceResult) -> str:
    lines = ["# HodgeCY II Baseline - 84 vs 84a", "", "| Invariant | Left | Right | State |", "| --- | --- | --- | --- |"]
    for result in report.invariant_results:
        left = result.operands[0].value if result.operands else None
        right = result.operands[1].value if len(result.operands) > 1 else None
        lines.append(f"| {result.comparison_key} | `{left}` | `{right}` | {result.state.value} |")
    lines.extend(["", f"First current available distinction: {first.first_difference or first.state.value}", ""])
    return "\n".join(lines)


def _set_markdown(title: str, results: tuple[SetComparisonResult, ...], refinement: RefinementResult, first: FirstDifferenceResult) -> str:
    lines = [f"# {title}", ""]
    for result in results:
        lines.append(f"## {result.comparison_key}")
        lines.append(f"State: {result.state.value}")
        for value, members in result.equivalence_groups.items():
            lines.append(f"- `{value}`: {', '.join(members)}")
        if result.unknown_members:
            lines.append(f"- UNKNOWN: {', '.join(result.unknown_members)}")
        lines.append("")
    lines.append(_refinement_markdown("Refinement", refinement, first))
    return "\n".join(lines)


def _refinement_markdown(title: str, refinement: RefinementResult, first: FirstDifferenceResult) -> str:
    lines = [f"# {title}", ""]
    for level in refinement.levels:
        lines.append(f"## Level {level.level_index}: {', '.join(level.invariant_names)}")
        for item in level.classes:
            lines.append(f"- {', '.join(item.member_geometry_ids)}")
        if level.unresolved_members:
            lines.append(f"- UNKNOWN: {', '.join(level.unresolved_members)}")
        lines.append("")
    lines.append(f"First split: {first.first_difference or first.state.value}")
    lines.append("")
    return "\n".join(lines)
