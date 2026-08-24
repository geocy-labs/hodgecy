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

NODE_GEOMETRY_INVARIANTS = (
    "parameter_specialization",
    "fixed_parameter_singular_scheme_degree_certified",
    "generic_parameter_verified",
    "singular_scheme_dimension",
    "singular_scheme_degree",
    "singular_support_cardinality",
    "singular_support_complete",
    "singular_scheme_reduced",
    "pointwise_singular_verified_count",
    "pointwise_odp_verified_count",
    "all_points_odp",
    "double_cover_odp_verified",
    "finite_reduced_odp_scheme",
)

PAIR_ORDER = HODGE_INVARIANTS + SOURCE_INVARIANTS + tuple(name for name, _ in UNKNOWN_LATER_INVARIANTS)
PAIR_WITH_NODE_GEOMETRY_ORDER = PAIR_ORDER + NODE_GEOMETRY_INVARIANTS
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


@dataclass(frozen=True, slots=True)
class HodgeCYIINodeGeometryResult:
    ingest: HodgeCYIICohortIngestResult
    node_runs: tuple[CalculationRun, ...]
    node_invariant_names: tuple[str, ...]
    node_summaries: dict[str, dict[str, Any]]
    pair_84_node_report: PairComparisonReport
    pair_84_node_first_difference: FirstDifferenceResult
    pair_84_appended_report: PairComparisonReport
    report_paths: tuple[Path, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ingest": self.ingest.to_dict(),
            "node_runs": [run.to_dict() for run in self.node_runs],
            "node_invariant_names": list(self.node_invariant_names),
            "node_summaries": self.node_summaries,
            "pair_84_node_report": self.pair_84_node_report.to_dict(),
            "pair_84_node_first_difference": self.pair_84_node_first_difference.to_dict(),
            "pair_84_appended_report": self.pair_84_appended_report.to_dict(),
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


def hodgecy_ii_node_geometry_blob5(
    store: ResultStore,
    *,
    manifest_path: str | Path | None = None,
    root: str | Path | None = None,
    report_dir: str | Path | None = None,
) -> HodgeCYIINodeGeometryResult:
    """Persist the Blob 5 node-geometry baseline for the current HodgeCY II cohort.

    This function does not run the large 112-point double-octic scheme through
    SymPy. It records the exact fixed-parameter model metadata and the existing
    imported degree-112 singular-scheme facts for 84/84a, while leaving support,
    reducedness, Hessian, double-cover ODP, and global finite-reduced-ODP claims
    UNKNOWN until an exact backend/certificate supplies them.
    """

    root_path = Path(root) if root is not None else repo_root()
    ingest = ingest_hodgecy_ii_cohort(store, manifest_path=manifest_path, root=root_path)
    manifest = ingest.manifest
    arrangement_to_geometry = {member["arrangement_id"]: member["geometry_id"] for member in manifest["members"]}
    runs: list[CalculationRun] = []
    node_summaries: dict[str, dict[str, Any]] = {}

    for member in manifest["members"]:
        arrangement_id = member["arrangement_id"]
        geometry_id = member["geometry_id"]
        summary_path = root_path / member["summary_path"]
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        smoothing_path = root_path / "data" / "processed" / f"smoothing_verification_{arrangement_id}.json"
        smoothing = _load_optional_json(smoothing_path)
        input_metadata = {
            "blob": 5,
            "summary_path": member["summary_path"],
            "summary_sha256": stable_sha256(summary),
            "smoothing_verification_path": smoothing_path.relative_to(root_path).as_posix() if smoothing_path.exists() else None,
            "smoothing_verification_sha256": None if smoothing is None else stable_sha256(smoothing),
        }
        run = store.begin_run(
            geometry_id=geometry_id,
            calculation_type="hodgecy_ii_node_geometry_blob5",
            input_metadata=input_metadata,
            parameters={"scope": "singular_scheme_and_odp_certification_baseline", "no_defect_or_hodge_atoms": True},
            backend="hodgecy.cohorts.hodgecy_ii + hodgecy.geometry.singularities",
            coefficient_ring="QQ/imported",
            environment_metadata={"manifest_path": str(manifest_path or MANIFEST_RELATIVE_PATH)},
            notes="Blob 5 node-geometry baseline; missing exact support/reducedness/Hessian data remain UNKNOWN.",
        )
        certificate = _record_blob5_node_certificate(store, run.run_id, member, summary, smoothing, smoothing_path if smoothing is not None else None)
        for record in _node_geometry_records_from_summary(run.run_id, summary, member, smoothing, certificate.certificate_id):
            store.record_invariant(**record)
        runs.append(store.complete_run(run.run_id))
        node_summaries[arrangement_id] = _node_summary(summary, member, smoothing)

    engine = ComparisonEngine(store)
    pair_members = (arrangement_to_geometry["84"], arrangement_to_geometry["84a"])
    pair_node_report = engine.compare_pair(pair_members[0], pair_members[1], invariants=NODE_GEOMETRY_INVARIANTS)
    pair_node_first = engine.first_difference(pair_members, NODE_GEOMETRY_INVARIANTS)
    pair_appended_report = engine.compare_pair(pair_members[0], pair_members[1], invariants=PAIR_WITH_NODE_GEOMETRY_ORDER)

    paths: tuple[Path, ...] = ()
    if report_dir is not None:
        paths = _write_node_geometry_reports(
            Path(report_dir),
            node_summaries=node_summaries,
            pair_node_report=pair_node_report,
            pair_node_first=pair_node_first,
            pair_appended_report=pair_appended_report,
        )

    return HodgeCYIINodeGeometryResult(
        ingest=ingest,
        node_runs=tuple(runs),
        node_invariant_names=NODE_GEOMETRY_INVARIANTS,
        node_summaries=node_summaries,
        pair_84_node_report=pair_node_report,
        pair_84_node_first_difference=pair_node_first,
        pair_84_appended_report=pair_appended_report,
        report_paths=paths,
    )


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


def _load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _record_blob5_node_certificate(
    store: ResultStore,
    run_id: str,
    member: dict[str, Any],
    summary: dict[str, Any],
    smoothing: dict[str, Any] | None,
    smoothing_path: Path | None,
):
    arrangement_id = member["arrangement_id"]
    perturbation = summary.get("quartic_perturbation") or {}
    exact_model_available = smoothing is not None and arrangement_id in {"84", "84a"}
    evidence = {
        "arrangement_id": arrangement_id,
        "geometry_id": member["geometry_id"],
        "level_A_candidate_points": {
            "status": EvidenceStatus.UNKNOWN.value,
            "reason": "No exact complete candidate support list is canonical for Blob 5 ingestion.",
        },
        "level_B_pointwise_singular_verification": {
            "status": EvidenceStatus.UNKNOWN.value,
            "reason": "No pointwise exact support certificates are available in canonical tracked data.",
        },
        "level_C_complete_reduced_singular_scheme": {
            "dimension": perturbation.get("saturated_jacobian_scheme_dimension"),
            "degree": perturbation.get("saturated_jacobian_scheme_degree"),
            "dimension_degree_status": EvidenceStatus.IMPORTED.value if perturbation else EvidenceStatus.UNKNOWN.value,
            "support_complete_status": EvidenceStatus.UNKNOWN.value,
            "reducedness_status": EvidenceStatus.UNKNOWN.value,
        },
        "level_D_ordinary_double_points": {
            "status": EvidenceStatus.UNKNOWN.value,
            "reason": "ordinary_node_verified is not claimed by release v0.2.0; reducedness/support/Hessian certificates are absent here.",
        },
        "double_cover_total_space": {
            "status": EvidenceStatus.UNKNOWN.value,
            "reason": "No explicit pointwise branch ODP certificate was available for the double-cover local theorem step.",
        },
        "parameter_specialization": _parameter_specialization(summary, smoothing),
        "exact_model_available": exact_model_available,
        "exact_backend_gap": _exact_backend_gap(arrangement_id, smoothing),
        "source_paths": {
            "summary_path": member["summary_path"],
            "smoothing_verification_path": None if smoothing_path is None else smoothing_path.as_posix(),
        },
        "mathematical_firewall": {
            "node_count_does_not_imply_node_relation_rank": True,
            "odp_does_not_imply_vanishing_cycle_independence": True,
            "degree_does_not_equal_support_without_reducedness": True,
            "branch_data_not_promoted_without_double_cover_step": True,
            "fixed_parameter_not_generic_parameter": True,
            "no_hodge_atom_constructed": True,
        },
    }
    return store.record_certificate(
        certificate_type="hodgecy_ii_blob5_node_geometry_baseline",
        subject_type="geometry",
        subject_id=member["geometry_id"],
        method="release import plus Blob 5 mathematical firewall",
        evidence=evidence,
        generated_by_run_id=run_id,
        notes="Blob 5 separates imported singular-scheme facts from missing support/reducedness/Hessian/ODP certificates.",
    )


def _node_geometry_records_from_summary(
    run_id: str,
    summary: dict[str, Any],
    member: dict[str, Any],
    smoothing: dict[str, Any] | None,
    certificate_id: str,
) -> list[dict[str, Any]]:
    arrangement_id = member["arrangement_id"]
    perturbation = summary.get("quartic_perturbation") or {}
    provenance = f"Blob 5 node baseline from {member['summary_path']}"
    parameter = _parameter_specialization(summary, smoothing)
    if arrangement_id in {"84", "84a"} and perturbation:
        dimension = perturbation.get("saturated_jacobian_scheme_dimension")
        degree = perturbation.get("saturated_jacobian_scheme_degree")
        fixed_degree = perturbation.get("status") == "degree112_certified" and dimension == 0 and degree is not None
        records = {
            "parameter_specialization": (parameter, EvidenceStatus.IMPORTED, "fixed smoothing metadata imported from canonical records"),
            "fixed_parameter_singular_scheme_degree_certified": (fixed_degree, EvidenceStatus.IMPORTED, "release imports a fixed epsilon singular-scheme degree certificate"),
            "generic_parameter_verified": (None, EvidenceStatus.UNKNOWN, "fixed epsilon=1 data do not prove a generic-parameter statement"),
            "singular_scheme_dimension": (dimension, EvidenceStatus.IMPORTED, "saturated projective Jacobian scheme dimension imported from release"),
            "singular_scheme_degree": (degree, EvidenceStatus.IMPORTED, "saturated projective Jacobian scheme degree imported from release"),
            "singular_support_cardinality": (None, EvidenceStatus.UNKNOWN, "exact support list is not canonical in Blob 5"),
            "singular_support_complete": (None, EvidenceStatus.UNKNOWN, "candidate support completeness is not certified"),
            "singular_scheme_reduced": (None, EvidenceStatus.UNKNOWN, "reducedness certificate is not present in canonical tracked data"),
            "pointwise_singular_verified_count": (None, EvidenceStatus.UNKNOWN, "pointwise F=dF=0 support certificates are absent"),
            "pointwise_odp_verified_count": (None, EvidenceStatus.UNKNOWN, "affine-chart Hessian certificates are absent"),
            "all_points_odp": (None, EvidenceStatus.UNKNOWN, "global ODP claim is withheld"),
            "double_cover_odp_verified": (None, EvidenceStatus.UNKNOWN, "double-cover total-space ODP step has no pointwise input"),
            "finite_reduced_odp_scheme": (None, EvidenceStatus.UNKNOWN, "global certificate prerequisites are incomplete"),
        }
    else:
        records = {
            name: (None, EvidenceStatus.UNKNOWN, "no exact supported singular-fiber model is documented for Blob 5")
            for name in NODE_GEOMETRY_INVARIANTS
        }
        records["parameter_specialization"] = ({}, EvidenceStatus.UNKNOWN, "no exact supported model supplied")

    return [
        {
            "run_id": run_id,
            "name": name,
            "value": value,
            "result_kind": ResultKind.NODE_GEOMETRY,
            "evidence_status": status,
            "method": "hodgecy_ii_blob5_node_geometry_baseline",
            "provenance": provenance,
            "certificate_id": certificate_id,
            "notes": notes,
        }
        for name, (value, status, notes) in records.items()
    ]


def _parameter_specialization(summary: dict[str, Any], smoothing: dict[str, Any] | None) -> dict[str, Any]:
    perturbation = summary.get("quartic_perturbation") or {}
    if not perturbation and smoothing is None:
        return {}
    return {
        "epsilon": perturbation.get("epsilon") or (smoothing or {}).get("epsilon"),
        "quartic_Q": perturbation.get("quartic_Q") or (smoothing or {}).get("quartic_Q"),
        "fixed_specialization_verified": bool(perturbation.get("status") == "degree112_certified"),
        "generic_parameter_verified": None,
        "status_note": "fixed epsilon specialization only; no generic-parameter promotion",
    }


def _exact_backend_gap(arrangement_id: str, smoothing: dict[str, Any] | None) -> str:
    if arrangement_id not in {"84", "84a"}:
        return "No exact supported singular-fiber model is documented for this cohort member."
    if smoothing is None:
        return "No smoothing-verification record is present."
    return (
        "Exact smoothing polynomial metadata is present, but Blob 5 has no in-repo exact CAS certificate for "
        "complete support, reducedness, affine-chart Hessian rank at all 112 points, and the double-cover local step."
    )


def _node_summary(summary: dict[str, Any], member: dict[str, Any], smoothing: dict[str, Any] | None) -> dict[str, Any]:
    perturbation = summary.get("quartic_perturbation") or {}
    return {
        "arrangement_id": member["arrangement_id"],
        "geometry_id": member["geometry_id"],
        "model_used": "fixed epsilon smoothing bridge metadata" if smoothing is not None else "none",
        "parameter_specialization": _parameter_specialization(summary, smoothing),
        "singular_scheme_dimension": perturbation.get("saturated_jacobian_scheme_dimension"),
        "singular_scheme_degree": perturbation.get("saturated_jacobian_scheme_degree"),
        "support_cardinality": None,
        "support_complete": None,
        "reduced": None,
        "pointwise_odp_count": None,
        "double_cover_odp_verified": None,
        "global_certification_status": EvidenceStatus.UNKNOWN.value,
        "backend_gap": _exact_backend_gap(member["arrangement_id"], smoothing),
    }


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


def _write_node_geometry_reports(
    report_dir: Path,
    *,
    node_summaries: dict[str, dict[str, Any]],
    pair_node_report: PairComparisonReport,
    pair_node_first: FirstDifferenceResult,
    pair_appended_report: PairComparisonReport,
) -> tuple[Path, ...]:
    report_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "node_summaries": node_summaries,
        "pair_84_node_report": pair_node_report.to_dict(),
        "pair_84_node_first_difference": pair_node_first.to_dict(),
        "pair_84_appended_report": pair_appended_report.to_dict(),
    }
    paths = (
        report_dir / "hodgecy_ii_node_geometry_blob5.json",
        report_dir / "hodgecy_ii_node_geometry_blob5.md",
        report_dir / "hodgecy_ii_84_84a_node_geometry_comparison.json",
        report_dir / "hodgecy_ii_84_84a_node_geometry_comparison.md",
    )
    paths[0].write_text(_deterministic_json(payload) + "\n", encoding="utf-8")
    paths[1].write_text(_node_geometry_markdown(node_summaries), encoding="utf-8")
    paths[2].write_text(
        _deterministic_json(
            {
                "pair_84_node_report": pair_node_report.to_dict(),
                "pair_84_node_first_difference": pair_node_first.to_dict(),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    paths[3].write_text(_node_pair_markdown(pair_node_report, pair_node_first), encoding="utf-8")
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


def _node_geometry_markdown(node_summaries: dict[str, dict[str, Any]]) -> str:
    lines = ["# HodgeCY II Node Geometry - Blob 5", ""]
    for arrangement_id in sorted(node_summaries):
        item = node_summaries[arrangement_id]
        parameter = item["parameter_specialization"] or {}
        lines.extend(
            [
                f"## {arrangement_id}",
                f"- geometry_id: `{item['geometry_id']}`",
                f"- model used: {item['model_used']}",
                f"- parameter specialization: `{parameter}`",
                f"- singular scheme dimension: `{item['singular_scheme_dimension']}`",
                f"- singular scheme degree: `{item['singular_scheme_degree']}`",
                f"- support cardinality: `{item['support_cardinality']}`",
                f"- reduced: `{item['reduced']}`",
                f"- ODP count: `{item['pointwise_odp_count']}`",
                f"- double-cover ODP verified: `{item['double_cover_odp_verified']}`",
                f"- global certification status: `{item['global_certification_status']}`",
                f"- backend gap: {item['backend_gap']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Firewall",
            "- A degree value is not treated as a support cardinality without support and reducedness certificates.",
            "- No node-relation rank, defect, vanishing-cycle relation, or Hodge atom is computed here.",
            "- Fixed epsilon metadata is not promoted to a generic-parameter theorem.",
            "",
        ]
    )
    return "\n".join(lines)


def _node_pair_markdown(report: PairComparisonReport, first: FirstDifferenceResult) -> str:
    lines = ["# HodgeCY II Node Geometry - 84 vs 84a", "", "| Invariant | 84 | 84a | State |", "| --- | --- | --- | --- |"]
    for result in report.invariant_results:
        left = result.operands[0].value if result.operands else None
        right = result.operands[1].value if len(result.operands) > 1 else None
        lines.append(f"| {result.comparison_key} | `{left}` | `{right}` | {result.state.value} |")
    lines.extend(["", f"First node-geometry distinction: {first.first_difference or first.state.value}", ""])
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
