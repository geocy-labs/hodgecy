from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hodgecy.algebra import IntegerLinearMap, MatrixSemanticRole, persist_integer_linear_map_analysis
from hodgecy.comparison import ComparisonEngine, FirstDifferenceResult, PairComparisonReport, RefinementResult, SetComparisonResult
from hodgecy.core.results import EvidenceStatus, ResultKind
from hodgecy.geometry import DefectConvention, CriticalDegreeResult, persist_classical_defect_result, resolve_critical_degree, unknown_classical_defect_result
from hodgecy.equivariant.source_complex import source_complex_from_incidence
from hodgecy.core.serialization import canonical_json, stable_sha256
from hodgecy.relations import RelationRealizationKind, conditional_defect_feasibility_for_source_h1, node_relation_firewall, source_to_node_firewall
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

NODE_IDEAL_HILBERT_INVARIANTS = (
    "exact_node_ideal_available",
    "node_ideal_source",
    "scheme_ideal_hash",
    "scheme_ideal_saturated",
    "scheme_dimension_from_ideal",
    "scheme_degree_from_ideal",
    "hilbert_function_table",
    "hilbert_stabilization_degree",
    "hilbert_polynomial",
    "hilbert_computation_status",
)

DEFECT_BLOB7_INVARIANTS = (
    "critical_degree",
    "evaluation_source_dimension",
    "evaluation_target_length",
    "evaluation_rank",
    "evaluation_kernel_dimension",
    "evaluation_cokernel_dimension",
    "evaluation_rank_deficiency",
    "classical_defect",
)

INTEGRAL_LATTICE_BLOB8_INVARIANTS = (
    "matrix_shape",
    "rank_Q",
    "rank_mod_2",
    "rank_mod_3",
    "kernel_dim_Q",
    "cokernel_dim_Q",
    "integral_kernel_rank",
    "smith_normal_form",
    "integral_cokernel_decomposition",
    "cokernel_structure",
    "saturation_index",
    "matrix_hash",
)

NODE_RELATION_BLOB9_INVARIANTS = (
    "expected_relation_realization_kind",
    "expected_node_count",
    "expected_node_generator_rank",
    "critical_degree",
    "evaluation_source_dimension",
    "expected_evaluation_matrix_shape",
    "expected_relation_map_shape",
    "node_generator_rank",
    "node_generator_module_status",
    "rational_evaluation_relation_complex",
    "rational_evaluation_relation_rank",
    "integral_evaluation_relation_complex",
    "integral_evaluation_relation_snf",
    "integral_evaluation_relation_torsion",
    "vanishing_cycle_relation_complex",
    "exceptional_curve_relation_complex",
    "source_to_node_map_status",
)

SOURCE_TO_NODE_BLOB10_INVARIANTS = (
    "source_d_shape",
    "source_rank_Q",
    "source_H1_rank_Q",
    "source_H0_rank_Q",
    "source_H0_Z_torsion",
    "expected_node_count",
    "critical_degree",
    "expected_evaluation_matrix_shape",
    "expected_relation_map_shape",
    "node_evaluation_H1_rank",
    "source_to_evaluation_chain_map",
    "source_to_vanishing_chain_map",
    "source_to_exceptional_chain_map",
    "conditional_defect_feasibility",
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


@dataclass(frozen=True, slots=True)
class HodgeCYIINodeIdealHilbertResult:
    ingest: HodgeCYIICohortIngestResult
    runs: tuple[CalculationRun, ...]
    summaries: dict[str, dict[str, Any]]
    pair_84_hilbert_report: PairComparisonReport
    pair_84_hilbert_first_difference: FirstDifferenceResult
    report_paths: tuple[Path, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ingest": self.ingest.to_dict(),
            "runs": [run.to_dict() for run in self.runs],
            "summaries": self.summaries,
            "pair_84_hilbert_report": self.pair_84_hilbert_report.to_dict(),
            "pair_84_hilbert_first_difference": self.pair_84_hilbert_first_difference.to_dict(),
            "report_paths": [path.as_posix() for path in self.report_paths],
        }


@dataclass(frozen=True, slots=True)
class HodgeCYIIDefectBlob7Result:
    ingest: HodgeCYIICohortIngestResult
    runs: tuple[CalculationRun, ...]
    summaries: dict[str, dict[str, Any]]
    pair_84_defect_report: PairComparisonReport
    pair_84_defect_first_difference: FirstDifferenceResult
    report_paths: tuple[Path, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ingest": self.ingest.to_dict(),
            "runs": [run.to_dict() for run in self.runs],
            "summaries": self.summaries,
            "pair_84_defect_report": self.pair_84_defect_report.to_dict(),
            "pair_84_defect_first_difference": self.pair_84_defect_first_difference.to_dict(),
            "report_paths": [path.as_posix() for path in self.report_paths],
        }


@dataclass(frozen=True, slots=True)
class HodgeCYIIIntegralLatticeBlob8Result:
    ingest: HodgeCYIICohortIngestResult
    runs: tuple[CalculationRun, ...]
    summaries: dict[str, dict[str, Any]]
    pair_84_source_lattice_report: PairComparisonReport
    pair_84_source_lattice_first_difference: FirstDifferenceResult
    set_239_241_source_lattice_first_difference: FirstDifferenceResult
    report_paths: tuple[Path, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ingest": self.ingest.to_dict(),
            "runs": [run.to_dict() for run in self.runs],
            "summaries": self.summaries,
            "pair_84_source_lattice_report": self.pair_84_source_lattice_report.to_dict(),
            "pair_84_source_lattice_first_difference": self.pair_84_source_lattice_first_difference.to_dict(),
            "set_239_241_source_lattice_first_difference": self.set_239_241_source_lattice_first_difference.to_dict(),
            "report_paths": [path.as_posix() for path in self.report_paths],
        }


@dataclass(frozen=True, slots=True)
class HodgeCYIINodeRelationBlob9Result:
    ingest: HodgeCYIICohortIngestResult
    runs: tuple[CalculationRun, ...]
    summaries: dict[str, dict[str, Any]]
    pair_84_node_relation_report: PairComparisonReport
    pair_84_node_relation_first_difference: FirstDifferenceResult
    report_paths: tuple[Path, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ingest": self.ingest.to_dict(),
            "runs": [run.to_dict() for run in self.runs],
            "summaries": self.summaries,
            "pair_84_node_relation_report": self.pair_84_node_relation_report.to_dict(),
            "pair_84_node_relation_first_difference": self.pair_84_node_relation_first_difference.to_dict(),
            "report_paths": [path.as_posix() for path in self.report_paths],
        }


@dataclass(frozen=True, slots=True)
class HodgeCYIISourceToNodeBlob10Result:
    ingest: HodgeCYIICohortIngestResult
    runs: tuple[CalculationRun, ...]
    summaries: dict[str, dict[str, Any]]
    pair_84_source_to_node_report: PairComparisonReport
    pair_84_source_to_node_first_difference: FirstDifferenceResult
    report_paths: tuple[Path, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ingest": self.ingest.to_dict(),
            "runs": [run.to_dict() for run in self.runs],
            "summaries": self.summaries,
            "pair_84_source_to_node_report": self.pair_84_source_to_node_report.to_dict(),
            "pair_84_source_to_node_first_difference": self.pair_84_source_to_node_first_difference.to_dict(),
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


def hodgecy_ii_node_ideal_hilbert_blob6(
    store: ResultStore,
    *,
    manifest_path: str | Path | None = None,
    root: str | Path | None = None,
    report_dir: str | Path | None = None,
) -> HodgeCYIINodeIdealHilbertResult:
    """Persist the Blob 6 node-ideal/Hilbert checkpoint for HodgeCY II.

    The current canonical records contain imported singular-scheme degree data
    for 84/84a but no frozen exact homogeneous node ideal. Blob 6 therefore
    records Hilbert data as UNKNOWN for the research cohort rather than
    constructing an ideal from degree or candidate support.
    """

    root_path = Path(root) if root is not None else repo_root()
    ingest = ingest_hodgecy_ii_cohort(store, manifest_path=manifest_path, root=root_path)
    manifest = ingest.manifest
    arrangement_to_geometry = {member["arrangement_id"]: member["geometry_id"] for member in manifest["members"]}
    runs: list[CalculationRun] = []
    summaries: dict[str, dict[str, Any]] = {}

    for member in manifest["members"]:
        arrangement_id = member["arrangement_id"]
        summary_path = root_path / member["summary_path"]
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        input_metadata = {
            "blob": 6,
            "summary_path": member["summary_path"],
            "summary_sha256": stable_sha256(summary),
            "blob5_report": "research_outputs/hodgecy_ii/node_geometry_blob5/hodgecy_ii_node_geometry_blob5.json",
        }
        run = store.begin_run(
            geometry_id=member["geometry_id"],
            calculation_type="hodgecy_ii_node_ideal_hilbert_blob6",
            input_metadata=input_metadata,
            parameters={"scope": "node_ideal_and_hilbert_checkpoint", "no_defect": True},
            backend="hodgecy.cohorts.hodgecy_ii + hodgecy.geometry.projective_schemes",
            coefficient_ring="QQ/unknown-ideal",
            environment_metadata={"manifest_path": str(manifest_path or MANIFEST_RELATIVE_PATH)},
            notes="Blob 6 checkpoint; exact node ideals are not fabricated from degree data.",
        )
        certificate = _record_blob6_hilbert_certificate(store, run.run_id, member, summary)
        for record in _node_ideal_hilbert_records(run.run_id, member, summary, certificate.certificate_id):
            store.record_invariant(**record)
        runs.append(store.complete_run(run.run_id))
        summaries[arrangement_id] = _node_ideal_hilbert_summary(member, summary)

    engine = ComparisonEngine(store)
    pair_members = (arrangement_to_geometry["84"], arrangement_to_geometry["84a"])
    pair_report = engine.compare_pair(pair_members[0], pair_members[1], invariants=NODE_IDEAL_HILBERT_INVARIANTS)
    pair_first = engine.first_difference(pair_members, NODE_IDEAL_HILBERT_INVARIANTS)

    paths: tuple[Path, ...] = ()
    if report_dir is not None:
        paths = _write_node_ideal_hilbert_reports(Path(report_dir), summaries=summaries, pair_report=pair_report, pair_first=pair_first)

    return HodgeCYIINodeIdealHilbertResult(
        ingest=ingest,
        runs=tuple(runs),
        summaries=summaries,
        pair_84_hilbert_report=pair_report,
        pair_84_hilbert_first_difference=pair_first,
        report_paths=paths,
    )


def hodgecy_ii_defect_blob7(
    store: ResultStore,
    *,
    manifest_path: str | Path | None = None,
    root: str | Path | None = None,
    report_dir: str | Path | None = None,
) -> HodgeCYIIDefectBlob7Result:
    """Persist the Blob 7 critical-degree/defect checkpoint for HodgeCY II."""

    root_path = Path(root) if root is not None else repo_root()
    ingest = ingest_hodgecy_ii_cohort(store, manifest_path=manifest_path, root=root_path)
    manifest = ingest.manifest
    arrangement_to_geometry = {member["arrangement_id"]: member["geometry_id"] for member in manifest["members"]}
    runs: list[CalculationRun] = []
    summaries: dict[str, dict[str, Any]] = {}

    for member in manifest["members"]:
        arrangement_id = member["arrangement_id"]
        summary_path = root_path / member["summary_path"]
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        critical = _hodgecy_ii_critical_degree(member, summary)
        gap = _defect_gap(member, critical)
        defect_result = unknown_classical_defect_result(
            geometry_id=member["geometry_id"],
            critical_degree=critical,
            scheme_length=None,
            reason=gap,
            prerequisites=_hodgecy_ii_defect_prerequisites(critical),
        )
        input_metadata = {
            "blob": 7,
            "summary_path": member["summary_path"],
            "summary_sha256": stable_sha256(summary),
            "blob6_report": "research_outputs/hodgecy_ii/node_ideal_hilbert_blob6/hodgecy_ii_node_ideal_hilbert_blob6.json",
        }
        run = store.begin_run(
            geometry_id=member["geometry_id"],
            calculation_type="hodgecy_ii_defect_blob7",
            input_metadata=input_metadata,
            parameters={"scope": "critical_degree_and_defect_checkpoint", "no_node_relations_or_hodge_atoms": True},
            backend="hodgecy.cohorts.hodgecy_ii + hodgecy.geometry.defects",
            coefficient_ring="QQ/unknown-node-ideal",
            environment_metadata={"manifest_path": str(manifest_path or MANIFEST_RELATIVE_PATH)},
            notes="Blob 7 checkpoint; critical degree may be theorem-derived, but defect remains UNKNOWN without exact node ideal/evaluation.",
        )
        persist_classical_defect_result(store, run_id=run.run_id, critical_degree=critical, defect_result=defect_result)
        runs.append(store.complete_run(run.run_id))
        summaries[arrangement_id] = _defect_summary(member, summary, critical, defect_result, gap)

    engine = ComparisonEngine(store)
    pair_members = (arrangement_to_geometry["84"], arrangement_to_geometry["84a"])
    pair_report = engine.compare_pair(pair_members[0], pair_members[1], invariants=DEFECT_BLOB7_INVARIANTS)
    pair_first = engine.first_difference(pair_members, DEFECT_BLOB7_INVARIANTS)

    paths: tuple[Path, ...] = ()
    if report_dir is not None:
        paths = _write_defect_blob7_reports(Path(report_dir), summaries=summaries, pair_report=pair_report, pair_first=pair_first)

    return HodgeCYIIDefectBlob7Result(
        ingest=ingest,
        runs=tuple(runs),
        summaries=summaries,
        pair_84_defect_report=pair_report,
        pair_84_defect_first_difference=pair_first,
        report_paths=paths,
    )


def hodgecy_ii_integral_lattice_blob8(
    store: ResultStore,
    *,
    manifest_path: str | Path | None = None,
    root: str | Path | None = None,
    report_dir: str | Path | None = None,
) -> HodgeCYIIIntegralLatticeBlob8Result:
    """Cross-check HodgeCY II source gluing matrices with the Blob 8 engine."""

    root_path = Path(root) if root is not None else repo_root()
    ingest = ingest_hodgecy_ii_cohort(store, manifest_path=manifest_path, root=root_path)
    manifest = ingest.manifest
    arrangement_to_geometry = {member["arrangement_id"]: member["geometry_id"] for member in manifest["members"]}
    runs: list[CalculationRun] = []
    summaries: dict[str, dict[str, Any]] = {}

    for member in manifest["members"]:
        arrangement_id = member["arrangement_id"]
        source_record, source_path = _source_lattice_record(root_path, arrangement_id)
        source_complex = source_complex_from_incidence(
            source_record["incidence_table"],
            arrangement_id=arrangement_id,
            linear_forms=source_record.get("linear_forms"),
            source_provenance={"source_path": source_path.relative_to(root_path).as_posix(), "blob": 8},
            rank_primes=(2, 3),
        )
        linear_map = IntegerLinearMap(
            source_complex.matrix_entries,
            semantic_role=MatrixSemanticRole.SOURCE_ASSEMBLY,
            provenance=f"source gluing matrix rebuilt from {source_path.relative_to(root_path).as_posix()}",
        )
        run = store.begin_run(
            geometry_id=member["geometry_id"],
            calculation_type="hodgecy_ii_integral_lattice_blob8",
            input_metadata={
                "blob": 8,
                "source_path": source_path.relative_to(root_path).as_posix(),
                "source_sha256": stable_sha256(source_record),
                "matrix_hash": linear_map.matrix_hash,
            },
            parameters={"scope": "source_assembly_integer_lattice_cross_check", "rank_primes": [2, 3], "no_node_relation_or_hodge_atom": True},
            backend="hodgecy.cohorts.hodgecy_ii + hodgecy.algebra.integer_lattices",
            coefficient_ring="ZZ",
            environment_metadata={"manifest_path": str(manifest_path or MANIFEST_RELATIVE_PATH)},
            notes="Blob 8 SOURCE_ASSEMBLY lattice checkpoint; no node-relation or source-to-node interpretation.",
        )
        persist_integer_linear_map_analysis(
            store,
            run_id=run.run_id,
            linear_map=linear_map,
            result_kind=ResultKind.SOURCE_ASSEMBLY,
            modular_primes=(2, 3),
        )
        runs.append(store.complete_run(run.run_id))
        summaries[arrangement_id] = _integral_lattice_summary(member, linear_map, source_complex, source_record, source_path, root_path)

    engine = ComparisonEngine(store)
    pair_members = (arrangement_to_geometry["84"], arrangement_to_geometry["84a"])
    set_members = tuple(arrangement_to_geometry[item] for item in ("239", "240", "241"))
    pair_report = engine.compare_pair(pair_members[0], pair_members[1], invariants=INTEGRAL_LATTICE_BLOB8_INVARIANTS)
    pair_first = engine.first_difference(pair_members, INTEGRAL_LATTICE_BLOB8_INVARIANTS)
    set_first = engine.first_difference(set_members, INTEGRAL_LATTICE_BLOB8_INVARIANTS)

    paths: tuple[Path, ...] = ()
    if report_dir is not None:
        paths = _write_integral_lattice_blob8_reports(Path(report_dir), summaries=summaries, pair_report=pair_report, pair_first=pair_first, set_first=set_first)

    return HodgeCYIIIntegralLatticeBlob8Result(
        ingest=ingest,
        runs=tuple(runs),
        summaries=summaries,
        pair_84_source_lattice_report=pair_report,
        pair_84_source_lattice_first_difference=pair_first,
        set_239_241_source_lattice_first_difference=set_first,
        report_paths=paths,
    )


def hodgecy_ii_node_relation_blob9(
    store: ResultStore,
    *,
    manifest_path: str | Path | None = None,
    root: str | Path | None = None,
    report_dir: str | Path | None = None,
) -> HodgeCYIINodeRelationBlob9Result:
    """Record the Blob 9 node-relation status without promoting source data."""

    root_path = Path(root) if root is not None else repo_root()
    ingest = ingest_hodgecy_ii_cohort(store, manifest_path=manifest_path, root=root_path)
    manifest = ingest.manifest
    arrangement_to_geometry = {member["arrangement_id"]: member["geometry_id"] for member in manifest["members"]}
    runs: list[CalculationRun] = []
    summaries: dict[str, dict[str, Any]] = {}

    for member in manifest["members"]:
        arrangement_id = member["arrangement_id"]
        summary_path = root_path / member["summary_path"]
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        critical = _hodgecy_ii_critical_degree(member, summary)
        relation_summary = _node_relation_summary(member, summary, critical)
        run = store.begin_run(
            geometry_id=member["geometry_id"],
            calculation_type="hodgecy_ii_node_relation_blob9",
            input_metadata={
                "blob": 9,
                "summary_path": member["summary_path"],
                "summary_sha256": stable_sha256(summary),
                "blob8_report": "research_outputs/hodgecy_ii/integral_lattice_blob8/hodgecy_ii_integral_lattice_blob8.json",
            },
            parameters={"scope": "verified_node_relation_status", "no_source_to_node_map_or_hodge_atom": True},
            backend="hodgecy.cohorts.hodgecy_ii + hodgecy.relations.node_relations",
            coefficient_ring="QQ/ZZ-unknown",
            environment_metadata={"manifest_path": str(manifest_path or MANIFEST_RELATIVE_PATH)},
            notes="Blob 9 checkpoint; expected critical-degree shapes may be recorded, but actual node-relation complexes remain UNKNOWN without verified support/map.",
        )
        certificate = _record_blob9_node_relation_certificate(store, run.run_id, member, relation_summary)
        for record in _node_relation_records(run.run_id, member, relation_summary, certificate.certificate_id):
            store.record_invariant(**record)
        runs.append(store.complete_run(run.run_id))
        summaries[arrangement_id] = relation_summary

    engine = ComparisonEngine(store)
    pair_members = (arrangement_to_geometry["84"], arrangement_to_geometry["84a"])
    pair_report = engine.compare_pair(pair_members[0], pair_members[1], invariants=NODE_RELATION_BLOB9_INVARIANTS)
    pair_first = engine.first_difference(pair_members, NODE_RELATION_BLOB9_INVARIANTS)

    paths: tuple[Path, ...] = ()
    if report_dir is not None:
        paths = _write_node_relation_blob9_reports(Path(report_dir), summaries=summaries, pair_report=pair_report, pair_first=pair_first)

    return HodgeCYIINodeRelationBlob9Result(
        ingest=ingest,
        runs=tuple(runs),
        summaries=summaries,
        pair_84_node_relation_report=pair_report,
        pair_84_node_relation_first_difference=pair_first,
        report_paths=paths,
    )


def hodgecy_ii_source_to_node_blob10(
    store: ResultStore,
    *,
    manifest_path: str | Path | None = None,
    root: str | Path | None = None,
    report_dir: str | Path | None = None,
) -> HodgeCYIISourceToNodeBlob10Result:
    """Record the Blob 10 source-to-node comparison checkpoint."""

    root_path = Path(root) if root is not None else repo_root()
    ingest = ingest_hodgecy_ii_cohort(store, manifest_path=manifest_path, root=root_path)
    manifest = ingest.manifest
    arrangement_to_geometry = {member["arrangement_id"]: member["geometry_id"] for member in manifest["members"]}
    runs: list[CalculationRun] = []
    summaries: dict[str, dict[str, Any]] = {}

    for member in manifest["members"]:
        arrangement_id = member["arrangement_id"]
        summary_path = root_path / member["summary_path"]
        theorem_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        critical = _hodgecy_ii_critical_degree(member, theorem_summary)
        source_record, source_path = _source_lattice_record(root_path, arrangement_id)
        source_complex = source_complex_from_incidence(
            source_record["incidence_table"],
            arrangement_id=arrangement_id,
            linear_forms=source_record.get("linear_forms"),
            source_provenance={"source_path": source_path.relative_to(root_path).as_posix(), "blob": 10},
            rank_primes=(2, 3),
        )
        linear_map = IntegerLinearMap(
            source_complex.matrix_entries,
            semantic_role=MatrixSemanticRole.SOURCE_ASSEMBLY,
            provenance=f"source matrix for Blob 10 from {source_path.relative_to(root_path).as_posix()}",
        )
        comparison_summary = _source_to_node_summary(member, theorem_summary, critical, linear_map)
        run = store.begin_run(
            geometry_id=member["geometry_id"],
            calculation_type="hodgecy_ii_source_to_node_blob10",
            input_metadata={
                "blob": 10,
                "summary_path": member["summary_path"],
                "summary_sha256": stable_sha256(theorem_summary),
                "source_path": source_path.relative_to(root_path).as_posix(),
                "source_sha256": stable_sha256(source_record),
            },
            parameters={"scope": "source_to_node_comparison_checkpoint", "no_source_to_node_map_inference": True},
            backend="hodgecy.cohorts.hodgecy_ii + hodgecy.relations.source_to_node",
            coefficient_ring="QQ/ZZ-unknown-target",
            environment_metadata={"manifest_path": str(manifest_path or MANIFEST_RELATIVE_PATH)},
            notes="Blob 10 checkpoint; source ranks are computed, but comparison morphisms remain UNKNOWN without explicit chain maps.",
        )
        certificate = _record_blob10_source_to_node_certificate(store, run.run_id, member, comparison_summary)
        for record in _source_to_node_records(run.run_id, member, comparison_summary, certificate.certificate_id):
            store.record_invariant(**record)
        runs.append(store.complete_run(run.run_id))
        summaries[arrangement_id] = comparison_summary

    engine = ComparisonEngine(store)
    pair_members = (arrangement_to_geometry["84"], arrangement_to_geometry["84a"])
    pair_report = engine.compare_pair(pair_members[0], pair_members[1], invariants=SOURCE_TO_NODE_BLOB10_INVARIANTS)
    pair_first = engine.first_difference(pair_members, SOURCE_TO_NODE_BLOB10_INVARIANTS)

    paths: tuple[Path, ...] = ()
    if report_dir is not None:
        paths = _write_source_to_node_blob10_reports(Path(report_dir), summaries=summaries, pair_report=pair_report, pair_first=pair_first)

    return HodgeCYIISourceToNodeBlob10Result(
        ingest=ingest,
        runs=tuple(runs),
        summaries=summaries,
        pair_84_source_to_node_report=pair_report,
        pair_84_source_to_node_first_difference=pair_first,
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


def _record_blob6_hilbert_certificate(store: ResultStore, run_id: str, member: dict[str, Any], summary: dict[str, Any]):
    arrangement_id = member["arrangement_id"]
    perturbation = summary.get("quartic_perturbation") or {}
    evidence = {
        "arrangement_id": arrangement_id,
        "geometry_id": member["geometry_id"],
        "exact_node_ideal_available": False,
        "ideal_source": None,
        "imported_singular_scheme_dimension": perturbation.get("saturated_jacobian_scheme_dimension"),
        "imported_singular_scheme_degree": perturbation.get("saturated_jacobian_scheme_degree"),
        "hilbert_function_status": EvidenceStatus.UNKNOWN.value,
        "reason": _node_ideal_gap(arrangement_id),
        "firewall": {
            "degree_112_does_not_determine_ideal": True,
            "node_ideal_is_not_node_relation_lattice": True,
            "hilbert_function_is_not_vanishing_cycle_spectrum": True,
            "equal_hilbert_functions_do_not_imply_equal_schemes": True,
            "candidate_point_ideal_not_complete_without_certificate": True,
            "eventual_hilbert_value_does_not_imply_reducedness": True,
            "no_classical_defect_asserted": True,
        },
    }
    return store.record_certificate(
        certificate_type="hodgecy_ii_blob6_node_ideal_hilbert_checkpoint",
        subject_type="geometry",
        subject_id=member["geometry_id"],
        method="missing exact ideal checkpoint",
        evidence=evidence,
        generated_by_run_id=run_id,
        notes="No exact homogeneous node ideal is available; Hilbert data remain UNKNOWN.",
    )


def _node_ideal_hilbert_records(run_id: str, member: dict[str, Any], summary: dict[str, Any], certificate_id: str) -> list[dict[str, Any]]:
    arrangement_id = member["arrangement_id"]
    gap = _node_ideal_gap(arrangement_id)
    values = {
        "exact_node_ideal_available": (False, EvidenceStatus.COMPUTED, gap),
        "node_ideal_source": (None, EvidenceStatus.UNKNOWN, "no exact ideal source is available"),
        "scheme_ideal_hash": (None, EvidenceStatus.UNKNOWN, "no homogeneous ideal generators are available to hash"),
        "scheme_ideal_saturated": (None, EvidenceStatus.UNKNOWN, "saturation cannot be assessed without an exact ideal"),
        "scheme_dimension_from_ideal": (None, EvidenceStatus.UNKNOWN, "dimension from ideal is unavailable"),
        "scheme_degree_from_ideal": (None, EvidenceStatus.UNKNOWN, "degree from ideal is unavailable; imported degree is not an ideal"),
        "hilbert_function_table": (None, EvidenceStatus.UNKNOWN, "Hilbert table cannot be computed without exact homogeneous ideal"),
        "hilbert_stabilization_degree": (None, EvidenceStatus.UNKNOWN, "stabilization cannot be assessed without Hilbert values"),
        "hilbert_polynomial": (None, EvidenceStatus.UNKNOWN, "Hilbert polynomial cannot be computed without exact homogeneous ideal"),
        "hilbert_computation_status": ("unknown_missing_exact_ideal", EvidenceStatus.UNKNOWN, gap),
    }
    return [
        {
            "run_id": run_id,
            "name": name,
            "value": value,
            "result_kind": ResultKind.NODE_GEOMETRY,
            "evidence_status": status,
            "method": "hodgecy_ii_blob6_node_ideal_hilbert_checkpoint",
            "provenance": f"Blob 6 checkpoint from {member['summary_path']}",
            "certificate_id": certificate_id,
            "notes": notes,
        }
        for name, (value, status, notes) in values.items()
    ]


def _node_ideal_hilbert_summary(member: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    perturbation = summary.get("quartic_perturbation") or {}
    return {
        "arrangement_id": member["arrangement_id"],
        "geometry_id": member["geometry_id"],
        "exact_node_or_singular_ideal_available": False,
        "source_of_ideal": None,
        "imported_singular_scheme_dimension": perturbation.get("saturated_jacobian_scheme_dimension"),
        "imported_singular_scheme_degree": perturbation.get("saturated_jacobian_scheme_degree"),
        "hilbert_computation_status": "UNKNOWN",
        "hilbert_values": None,
        "reason": _node_ideal_gap(member["arrangement_id"]),
    }


def _node_ideal_gap(arrangement_id: str) -> str:
    if arrangement_id in {"84", "84a"}:
        return (
            "Imported fixed-parameter singular-scheme dimension/degree exist, but no frozen exact homogeneous "
            "node/singular ideal generators are present; degree 112 is not enough to reconstruct I_Sigma."
        )
    return "No exact supported node/singular-scheme ideal is documented for this cohort member."


def _hodgecy_ii_critical_degree(member: dict[str, Any], summary: dict[str, Any]) -> CriticalDegreeResult | None:
    if member["arrangement_id"] in {"84", "84a"} and summary.get("quartic_perturbation"):
        return resolve_critical_degree(DefectConvention.NODAL_DOUBLE_SOLID_CLEMENS_CYNK, branch_degree=8)
    return None


def _hodgecy_ii_defect_prerequisites(critical: CriticalDegreeResult | None) -> dict[str, bool]:
    return {
        "finite_singular_scheme": False,
        "complete_support": False,
        "reducedness": False,
        "ordinary_node_classification": False,
        "exact_node_ideal": False,
        "applicable_double_solid_model": critical is not None,
        "certified_critical_degree_rule": critical is not None,
        "exact_evaluation_or_hilbert_computation": False,
    }


def _defect_gap(member: dict[str, Any], critical: CriticalDegreeResult | None) -> str:
    if critical is None:
        return "No applicable exact double-solid defect model is documented for this cohort member."
    return (
        "The standard nodal double-solid critical-degree rule gives k_crit=8 for the double-octic model, "
        "but the exact node ideal, complete reduced ODP scheme, and H_Sigma(8) are not certified."
    )


def _defect_summary(
    member: dict[str, Any],
    summary: dict[str, Any],
    critical: CriticalDegreeResult | None,
    defect_result,
    gap: str,
) -> dict[str, Any]:
    perturbation = summary.get("quartic_perturbation") or {}
    return {
        "arrangement_id": member["arrangement_id"],
        "geometry_id": member["geometry_id"],
        "model": None if critical is None else "nodal double solid / double cover of P^3",
        "branch_degree": None if critical is None else critical.branch_degree,
        "critical_degree_rule": None if critical is None else critical.convention.value,
        "critical_degree": None if critical is None else critical.critical_degree,
        "N_k": None if critical is None else critical.source_dimension,
        "node_scheme_status": {
            "imported_singular_scheme_dimension": perturbation.get("saturated_jacobian_scheme_dimension"),
            "imported_singular_scheme_degree": perturbation.get("saturated_jacobian_scheme_degree"),
            "complete_support": None,
            "reduced": None,
            "ordinary_nodes": None,
        },
        "exact_node_ideal_available": False,
        "H_Sigma_kcrit": None,
        "evaluation_rank": None,
        "evaluation_kernel_dimension": None,
        "evaluation_cokernel_dimension": None,
        "classical_defect": None,
        "certificate_status": defect_result.evidence_status.value,
        "reason": gap,
        "pending_template": None
        if critical is None
        else "If a verified reduced 112-node ideal becomes available, delta = 112 - H_Sigma(8) = 112 - rank(ev_{Sigma,8}).",
    }


def _record_blob9_node_relation_certificate(store: ResultStore, run_id: str, member: dict[str, Any], summary: dict[str, Any]):
    evidence = {
        "arrangement_id": member["arrangement_id"],
        "geometry_id": member["geometry_id"],
        "node_relation_summary": summary,
        "firewall": node_relation_firewall(),
        "unknown_status_basis": {
            "node_generator_module": "complete verified finite support is not available",
            "rational_evaluation_relation_complex": "no exact evaluation matrix E_k is available",
            "integral_evaluation_relation_complex": "no certified integral realization map rho is available",
            "vanishing_cycle_relation_complex": "no topology/monodromy presentation is available",
            "exceptional_curve_relation_complex": "no resolution curve-homology presentation is available",
            "source_to_node_map": "not constructed in Blob 9",
        },
    }
    return store.record_certificate(
        certificate_type="hodgecy_ii_blob9_node_relation_checkpoint",
        subject_type="geometry",
        subject_id=member["geometry_id"],
        method="Blob 9 node-relation framework status audit",
        evidence=evidence,
        generated_by_run_id=run_id,
        notes="Expected matrix shapes are metadata; no node-relation complex is promoted without a verified realization map.",
    )


def _node_relation_records(run_id: str, member: dict[str, Any], summary: dict[str, Any], certificate_id: str) -> list[dict[str, Any]]:
    provenance = f"Blob 9 node-relation status from {member['summary_path']}"
    unknown_notes = "UNKNOWN without verified node support and an explicit realization map rho:C_node->T"
    values: dict[str, tuple[Any, EvidenceStatus, str]] = {
        "expected_relation_realization_kind": (
            summary["expected_relation_realization_kind"],
            EvidenceStatus.COMPUTED if summary["expected_relation_realization_kind"] is not None else EvidenceStatus.UNKNOWN,
            "expected route only; not an actual realized relation complex",
        ),
        "expected_node_count": (
            summary["expected_node_count"],
            EvidenceStatus.IMPORTED if summary["expected_node_count"] is not None else EvidenceStatus.UNKNOWN,
            "imported singular-scheme degree used as expected r only; not verified support",
        ),
        "expected_node_generator_rank": (
            summary["expected_node_generator_rank"],
            EvidenceStatus.IMPORTED if summary["expected_node_generator_rank"] is not None else EvidenceStatus.UNKNOWN,
            "expected rank metadata; node_generator_rank remains UNKNOWN",
        ),
        "critical_degree": (
            summary["critical_degree"],
            EvidenceStatus.VERIFIED if summary["critical_degree"] is not None else EvidenceStatus.UNKNOWN,
            "critical degree theorem metadata, not a relation rank",
        ),
        "evaluation_source_dimension": (
            summary["evaluation_source_dimension"],
            EvidenceStatus.VERIFIED if summary["evaluation_source_dimension"] is not None else EvidenceStatus.UNKNOWN,
            "N_k = h^0(P^3,O(k)) when the double-octic critical-degree rule applies",
        ),
        "expected_evaluation_matrix_shape": (
            summary["expected_evaluation_matrix_shape"],
            EvidenceStatus.COMPUTED if summary["expected_evaluation_matrix_shape"] is not None else EvidenceStatus.UNKNOWN,
            "expected shape [r_expected,N_k] for E_k only",
        ),
        "expected_relation_map_shape": (
            summary["expected_relation_map_shape"],
            EvidenceStatus.COMPUTED if summary["expected_relation_map_shape"] is not None else EvidenceStatus.UNKNOWN,
            "expected shape [N_k,r_expected] for rho=E_k^T only",
        ),
        "node_generator_rank": (None, EvidenceStatus.UNKNOWN, "actual C_node rank is not certified by degree-only data"),
        "node_generator_module_status": (summary["node_generator_module_status"], EvidenceStatus.UNKNOWN, unknown_notes),
        "rational_evaluation_relation_complex": (None, EvidenceStatus.UNKNOWN, "no exact rational evaluation matrix is available"),
        "rational_evaluation_relation_rank": (None, EvidenceStatus.UNKNOWN, "dim ker(E^T) cannot be computed without E"),
        "integral_evaluation_relation_complex": (None, EvidenceStatus.UNKNOWN, "no certified integral realization matrix is supplied"),
        "integral_evaluation_relation_snf": (None, EvidenceStatus.UNKNOWN, "SNF applies only after a certified integral model"),
        "integral_evaluation_relation_torsion": (None, EvidenceStatus.UNKNOWN, "torsion applies only after a certified integral model"),
        "vanishing_cycle_relation_complex": (None, EvidenceStatus.UNKNOWN, "requires topology/monodromy data; not evaluation data"),
        "exceptional_curve_relation_complex": (None, EvidenceStatus.UNKNOWN, "requires an explicit resolution and curve homology"),
        "source_to_node_map_status": (summary["source_to_node_map_status"], EvidenceStatus.UNKNOWN, "Blob 9 does not construct a source-to-node map"),
    }
    return [
        {
            "run_id": run_id,
            "name": name,
            "value": value,
            "result_kind": ResultKind.NODE_RELATION,
            "evidence_status": status,
            "method": "hodgecy_ii_blob9_node_relation_checkpoint",
            "provenance": provenance,
            "certificate_id": certificate_id,
            "notes": notes,
        }
        for name, (value, status, notes) in values.items()
    ]


def _node_relation_summary(member: dict[str, Any], summary: dict[str, Any], critical: CriticalDegreeResult | None) -> dict[str, Any]:
    arrangement_id = member["arrangement_id"]
    perturbation = summary.get("quartic_perturbation") or {}
    expected_count = perturbation.get("saturated_jacobian_scheme_degree") if arrangement_id in {"84", "84a"} else None
    n_source = None if critical is None else critical.source_dimension
    return {
        "arrangement_id": arrangement_id,
        "geometry_id": member["geometry_id"],
        "expected_relation_realization_kind": RelationRealizationKind.EVALUATION_CONDITION.value if expected_count is not None and critical is not None else None,
        "expected_node_count": expected_count,
        "expected_node_generator_rank": expected_count,
        "critical_degree": None if critical is None else critical.critical_degree,
        "evaluation_source_dimension": n_source,
        "expected_evaluation_matrix_shape": None if expected_count is None or n_source is None else [expected_count, n_source],
        "expected_relation_map_shape": None if expected_count is None or n_source is None else [n_source, expected_count],
        "node_generator_module_status": "UNKNOWN",
        "node_generator_module_reason": (
            "imported degree 112 is present, but ordered complete support/reduced ODP verification is not"
            if expected_count is not None
            else "no exact supported node model is documented"
        ),
        "rational_evaluation_relation_complex_status": "UNKNOWN",
        "integral_evaluation_relation_complex_status": "UNKNOWN",
        "vanishing_cycle_relation_complex_status": "UNKNOWN",
        "exceptional_curve_relation_complex_status": "UNKNOWN",
        "source_to_node_map_status": "NOT_CONSTRUCTED",
        "source_level_snapshot": {
            "rank_Q": summary.get("rank_Q"),
            "rank_mod_2": summary.get("rank_mod_2"),
            "smith_normal_form": summary.get("smith_normal_form"),
            "firewall": "SOURCE_ASSEMBLY data are retained separately and are not promoted to NODE_RELATION.",
        },
        "pending_template": None
        if expected_count is None or n_source is None
        else "With verified support and trivializations, build E_8: QQ^165 -> QQ^112, then rho=E_8^T: QQ^112 -> QQ^165.",
        "firewall": node_relation_firewall(),
    }


def _record_blob10_source_to_node_certificate(store: ResultStore, run_id: str, member: dict[str, Any], summary: dict[str, Any]):
    evidence = {
        "arrangement_id": member["arrangement_id"],
        "geometry_id": member["geometry_id"],
        "source_to_node_summary": summary,
        "firewall": source_to_node_firewall(),
        "unknown_status_basis": {
            "source_to_evaluation_chain_map": "no exact node evaluation complex and no F1/F0 chain map are available",
            "source_to_vanishing_chain_map": "no vanishing-cycle complex and no F1/F0 chain map are available",
            "source_to_exceptional_chain_map": "no exceptional-curve complex and no F1/F0 chain map are available",
        },
    }
    return store.record_certificate(
        certificate_type="hodgecy_ii_blob10_source_to_node_checkpoint",
        subject_type="geometry",
        subject_id=member["geometry_id"],
        method="Blob 10 source-to-node comparison status audit",
        evidence=evidence,
        generated_by_run_id=run_id,
        notes="Source facts and rank feasibility are not existence statements for a source-to-node chain map.",
    )


def _source_to_node_records(run_id: str, member: dict[str, Any], summary: dict[str, Any], certificate_id: str) -> list[dict[str, Any]]:
    provenance = f"Blob 10 source-to-node checkpoint from {member['summary_path']}"
    source_values = {
        "source_d_shape": (summary["source_complex"]["d_src_shape"], EvidenceStatus.VERIFIED, "shape [C0_src,C1_src] for d_src:C1_src->C0_src"),
        "source_rank_Q": (summary["source_complex"]["rank_Q"], EvidenceStatus.VERIFIED, "exact rational rank of d_src"),
        "source_H1_rank_Q": (summary["source_complex"]["H1_rank_Q"], EvidenceStatus.VERIFIED, "dim_Q ker(d_src)"),
        "source_H0_rank_Q": (summary["source_complex"]["H0_rank_Q"], EvidenceStatus.VERIFIED, "dim_Q coker(d_src)"),
        "source_H0_Z_torsion": (summary["source_complex"]["H0_Z_torsion"], EvidenceStatus.VERIFIED, "integral source cokernel torsion from Smith normal form"),
    }
    node_values = {
        "expected_node_count": (summary["node_complex"]["expected_node_count"], EvidenceStatus.IMPORTED if summary["node_complex"]["expected_node_count"] is not None else EvidenceStatus.UNKNOWN, "expected target node count only"),
        "critical_degree": (summary["node_complex"]["critical_degree"], EvidenceStatus.VERIFIED if summary["node_complex"]["critical_degree"] is not None else EvidenceStatus.UNKNOWN, "critical degree metadata"),
        "expected_evaluation_matrix_shape": (summary["node_complex"]["expected_evaluation_matrix_shape"], EvidenceStatus.COMPUTED if summary["node_complex"]["expected_evaluation_matrix_shape"] is not None else EvidenceStatus.UNKNOWN, "expected E_k shape only"),
        "expected_relation_map_shape": (summary["node_complex"]["expected_relation_map_shape"], EvidenceStatus.COMPUTED if summary["node_complex"]["expected_relation_map_shape"] is not None else EvidenceStatus.UNKNOWN, "expected rho=E_k^T shape only"),
        "node_evaluation_H1_rank": (None, EvidenceStatus.UNKNOWN, "actual evaluation relation H1 is UNKNOWN without E_k/rho"),
    }
    comparison_values = {
        "source_to_evaluation_chain_map": (None, EvidenceStatus.UNKNOWN, "no explicit F1/F0 chain map to evaluation relation is supplied"),
        "source_to_vanishing_chain_map": (None, EvidenceStatus.UNKNOWN, "no vanishing-cycle target or chain map is supplied"),
        "source_to_exceptional_chain_map": (None, EvidenceStatus.UNKNOWN, "no exceptional-curve target or chain map is supplied"),
        "conditional_defect_feasibility": (summary["comparison_morphism"]["conditional_defect_feasibility"], EvidenceStatus.COMPUTED, "rank-only conditions; feasibility is not existence"),
    }
    records = []
    for result_kind, values in ((ResultKind.SOURCE_ASSEMBLY, source_values), (ResultKind.NODE_RELATION, node_values | comparison_values)):
        for name, (value, status, notes) in values.items():
            records.append(
                {
                    "run_id": run_id,
                    "name": name,
                    "value": value,
                    "result_kind": result_kind,
                    "evidence_status": status,
                    "method": "hodgecy_ii_blob10_source_to_node_checkpoint",
                    "provenance": provenance,
                    "certificate_id": certificate_id,
                    "notes": notes,
                }
            )
    return records


def _source_to_node_summary(
    member: dict[str, Any],
    theorem_summary: dict[str, Any],
    critical: CriticalDegreeResult | None,
    linear_map: IntegerLinearMap,
) -> dict[str, Any]:
    from hodgecy.algebra import rational_rank, smith_normal_form_data

    arrangement_id = member["arrangement_id"]
    rank = rational_rank(linear_map)
    snf = smith_normal_form_data(linear_map)
    perturbation = theorem_summary.get("quartic_perturbation") or {}
    expected_node_count = perturbation.get("saturated_jacobian_scheme_degree") if arrangement_id in {"84", "84a"} else None
    n_source_eval = None if critical is None else critical.source_dimension
    h1_rank = linear_map.domain_rank - rank.rank
    h0_rank = linear_map.codomain_rank - rank.rank
    conditional = list(conditional_defect_feasibility_for_source_h1(h1_rank)) if arrangement_id in {"84", "84a"} else []
    return {
        "arrangement_id": arrangement_id,
        "geometry_id": member["geometry_id"],
        "source_complex": {
            "d_src_shape": list(linear_map.shape),
            "rank_Q": rank.rank,
            "H1_rank_Q": h1_rank,
            "H0_rank_Q": h0_rank,
            "H0_Z_torsion": list(snf.cokernel.torsion_invariant_factors),
            "H0_Z_cokernel": snf.cokernel.to_dict(),
            "interpretation": "SOURCE_ASSEMBLY two-term complex C1_src -> C0_src",
        },
        "node_complex": {
            "expected_node_count": expected_node_count,
            "critical_degree": None if critical is None else critical.critical_degree,
            "expected_evaluation_matrix_shape": None if expected_node_count is None or n_source_eval is None else [expected_node_count, n_source_eval],
            "expected_relation_map_shape": None if expected_node_count is None or n_source_eval is None else [n_source_eval, expected_node_count],
            "actual_E_k": None,
            "defect": None,
            "H1_C_eval": None,
            "status": "UNKNOWN",
        },
        "comparison_morphism": {
            "source_to_evaluation_chain_map": "UNKNOWN",
            "source_to_vanishing_chain_map": "UNKNOWN",
            "source_to_exceptional_chain_map": "UNKNOWN",
            "source_to_evaluation_reason": "no explicit chain map F1/F0 and no exact node relation complex",
            "conditional_defect_feasibility": conditional,
        },
        "firewall": source_to_node_firewall(),
    }


def _source_lattice_record(root_path: Path, arrangement_id: str) -> tuple[dict[str, Any], Path]:
    if arrangement_id in {"84", "84a"}:
        path = root_path / "data" / "processed" / "equivariant_spectra" / f"hodgecy_equivariant_spectrum_{arrangement_id}.json"
        return json.loads(path.read_text(encoding="utf-8")), path
    path = root_path / "data" / "processed" / "equivariant_spectra" / "ckc_fixed_rational_batch" / "ckc_fixed_rational_spectra.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    for item in payload["spectra"]:
        if str(item["arrangement_id"]) == arrangement_id:
            return item, path
    raise KeyError(f"No source lattice record found for arrangement {arrangement_id}")


def _integral_lattice_summary(
    member: dict[str, Any],
    linear_map: IntegerLinearMap,
    source_complex,
    source_record: dict[str, Any],
    source_path: Path,
    root_path: Path,
) -> dict[str, Any]:
    from hodgecy.algebra import image_lattice, modular_rank, rational_rank, smith_normal_form_data

    rank = rational_rank(linear_map)
    rank2 = modular_rank(linear_map, 2)
    rank3 = modular_rank(linear_map, 3)
    snf = smith_normal_form_data(linear_map)
    image = image_lattice(linear_map)
    return {
        "arrangement_id": member["arrangement_id"],
        "geometry_id": member["geometry_id"],
        "matrix_available": True,
        "matrix_role": linear_map.semantic_role,
        "matrix_shape": list(linear_map.shape),
        "matrix_hash": linear_map.matrix_hash,
        "source_path": source_path.relative_to(root_path).as_posix(),
        "rank_Q": rank.rank,
        "rank_mod_2": rank2.rank,
        "rank_mod_3": rank3.rank,
        "kernel_dim_Q": rank.nullity,
        "cokernel_dim_Q": linear_map.codomain_rank - rank.rank,
        "smith_normal_form": list(snf.diagonal_invariant_factors),
        "cokernel_free_rank": snf.cokernel.free_rank,
        "torsion_factors": list(snf.cokernel.torsion_invariant_factors),
        "torsion_order": snf.cokernel.torsion_order,
        "torsion_primes": list(snf.cokernel.torsion_primes),
        "saturation_index": image.saturation.index,
        "legacy_cross_check": {
            "rank_Q_matches_source_record": source_record.get("rank_Q") == rank.rank,
            "rank_mod_2_matches_source_record": source_record.get("rank_F2", source_record.get("rank_mod_2")) == rank2.rank,
            "smith_normal_form_matches_source_record": source_record.get("smith_normal_form") == list(snf.diagonal_invariant_factors),
            "source_complex_matrix_shape": source_complex.algebra["gluing_matrix_shape"],
        },
        "firewall": {
            "source_assembly_matrix_is_not_node_relation_matrix": True,
            "source_kernel_is_not_vanishing_cycle_relation_lattice": True,
            "no_source_to_node_map_computed": True,
            "no_hodge_atom_computed": True,
        },
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


def _write_node_ideal_hilbert_reports(
    report_dir: Path,
    *,
    summaries: dict[str, dict[str, Any]],
    pair_report: PairComparisonReport,
    pair_first: FirstDifferenceResult,
) -> tuple[Path, ...]:
    report_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "summaries": summaries,
        "pair_84_hilbert_report": pair_report.to_dict(),
        "pair_84_hilbert_first_difference": pair_first.to_dict(),
    }
    paths = (
        report_dir / "hodgecy_ii_node_ideal_hilbert_blob6.json",
        report_dir / "hodgecy_ii_node_ideal_hilbert_blob6.md",
        report_dir / "hodgecy_ii_84_84a_hilbert_comparison.json",
        report_dir / "hodgecy_ii_84_84a_hilbert_comparison.md",
    )
    paths[0].write_text(_deterministic_json(payload) + "\n", encoding="utf-8")
    paths[1].write_text(_node_ideal_hilbert_markdown(summaries), encoding="utf-8")
    paths[2].write_text(_deterministic_json({"pair_84_hilbert_report": pair_report.to_dict(), "pair_84_hilbert_first_difference": pair_first.to_dict()}) + "\n", encoding="utf-8")
    paths[3].write_text(_hilbert_pair_markdown(pair_report, pair_first), encoding="utf-8")
    return paths


def _write_defect_blob7_reports(
    report_dir: Path,
    *,
    summaries: dict[str, dict[str, Any]],
    pair_report: PairComparisonReport,
    pair_first: FirstDifferenceResult,
) -> tuple[Path, ...]:
    report_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "summaries": summaries,
        "pair_84_defect_report": pair_report.to_dict(),
        "pair_84_defect_first_difference": pair_first.to_dict(),
    }
    paths = (
        report_dir / "hodgecy_ii_defect_blob7.json",
        report_dir / "hodgecy_ii_defect_blob7.md",
        report_dir / "hodgecy_ii_84_84a_defect_comparison.json",
        report_dir / "hodgecy_ii_84_84a_defect_comparison.md",
    )
    paths[0].write_text(_deterministic_json(payload) + "\n", encoding="utf-8")
    paths[1].write_text(_defect_blob7_markdown(summaries), encoding="utf-8")
    paths[2].write_text(_deterministic_json({"pair_84_defect_report": pair_report.to_dict(), "pair_84_defect_first_difference": pair_first.to_dict()}) + "\n", encoding="utf-8")
    paths[3].write_text(_defect_pair_markdown(pair_report, pair_first), encoding="utf-8")
    return paths


def _write_integral_lattice_blob8_reports(
    report_dir: Path,
    *,
    summaries: dict[str, dict[str, Any]],
    pair_report: PairComparisonReport,
    pair_first: FirstDifferenceResult,
    set_first: FirstDifferenceResult,
) -> tuple[Path, ...]:
    report_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "summaries": summaries,
        "pair_84_source_lattice_report": pair_report.to_dict(),
        "pair_84_source_lattice_first_difference": pair_first.to_dict(),
        "set_239_241_source_lattice_first_difference": set_first.to_dict(),
    }
    paths = (
        report_dir / "hodgecy_ii_integral_lattice_blob8.json",
        report_dir / "hodgecy_ii_integral_lattice_blob8.md",
        report_dir / "hodgecy_ii_84_84a_source_lattice_comparison.json",
        report_dir / "hodgecy_ii_84_84a_source_lattice_comparison.md",
    )
    paths[0].write_text(_deterministic_json(payload) + "\n", encoding="utf-8")
    paths[1].write_text(_integral_lattice_blob8_markdown(summaries, set_first), encoding="utf-8")
    paths[2].write_text(_deterministic_json({"pair_84_source_lattice_report": pair_report.to_dict(), "pair_84_source_lattice_first_difference": pair_first.to_dict()}) + "\n", encoding="utf-8")
    paths[3].write_text(_source_lattice_pair_markdown(pair_report, pair_first), encoding="utf-8")
    return paths


def _write_node_relation_blob9_reports(
    report_dir: Path,
    *,
    summaries: dict[str, dict[str, Any]],
    pair_report: PairComparisonReport,
    pair_first: FirstDifferenceResult,
) -> tuple[Path, ...]:
    report_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "summaries": summaries,
        "pair_84_node_relation_report": pair_report.to_dict(),
        "pair_84_node_relation_first_difference": pair_first.to_dict(),
    }
    paths = (
        report_dir / "hodgecy_ii_node_relation_blob9.json",
        report_dir / "hodgecy_ii_node_relation_blob9.md",
        report_dir / "hodgecy_ii_84_84a_relation_status.json",
        report_dir / "hodgecy_ii_84_84a_relation_status.md",
    )
    paths[0].write_text(_deterministic_json(payload) + "\n", encoding="utf-8")
    paths[1].write_text(_node_relation_blob9_markdown(summaries), encoding="utf-8")
    paths[2].write_text(_deterministic_json({"pair_84_node_relation_report": pair_report.to_dict(), "pair_84_node_relation_first_difference": pair_first.to_dict()}) + "\n", encoding="utf-8")
    paths[3].write_text(_node_relation_pair_markdown(pair_report, pair_first), encoding="utf-8")
    return paths


def _write_source_to_node_blob10_reports(
    report_dir: Path,
    *,
    summaries: dict[str, dict[str, Any]],
    pair_report: PairComparisonReport,
    pair_first: FirstDifferenceResult,
) -> tuple[Path, ...]:
    report_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "summaries": summaries,
        "pair_84_source_to_node_report": pair_report.to_dict(),
        "pair_84_source_to_node_first_difference": pair_first.to_dict(),
    }
    paths = (
        report_dir / "hodgecy_ii_source_to_node_blob10.json",
        report_dir / "hodgecy_ii_source_to_node_blob10.md",
        report_dir / "hodgecy_ii_84_84a_source_to_node_status.json",
        report_dir / "hodgecy_ii_84_84a_source_to_node_status.md",
    )
    paths[0].write_text(_deterministic_json(payload) + "\n", encoding="utf-8")
    paths[1].write_text(_source_to_node_blob10_markdown(summaries), encoding="utf-8")
    paths[2].write_text(_deterministic_json({"pair_84_source_to_node_report": pair_report.to_dict(), "pair_84_source_to_node_first_difference": pair_first.to_dict()}) + "\n", encoding="utf-8")
    paths[3].write_text(_source_to_node_pair_markdown(pair_report, pair_first), encoding="utf-8")
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


def _node_ideal_hilbert_markdown(summaries: dict[str, dict[str, Any]]) -> str:
    lines = ["# HodgeCY II Node Ideal and Hilbert - Blob 6", ""]
    for arrangement_id in sorted(summaries):
        item = summaries[arrangement_id]
        lines.extend(
            [
                f"## {arrangement_id}",
                f"- geometry_id: `{item['geometry_id']}`",
                f"- exact node/singular ideal available: `{item['exact_node_or_singular_ideal_available']}`",
                f"- source of ideal: `{item['source_of_ideal']}`",
                f"- imported singular scheme dimension: `{item['imported_singular_scheme_dimension']}`",
                f"- imported singular scheme degree: `{item['imported_singular_scheme_degree']}`",
                f"- Hilbert computation status: `{item['hilbert_computation_status']}`",
                f"- Hilbert values: `{item['hilbert_values']}`",
                f"- reason: {item['reason']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Firewall",
            "- Degree 112 does not determine a homogeneous node ideal.",
            "- A node ideal or Hilbert function is not a node-relation lattice or vanishing-cycle spectrum.",
            "- Equal Hilbert functions do not imply equal schemes.",
            "- No classical defect is computed in Blob 6.",
            "",
        ]
    )
    return "\n".join(lines)


def _hilbert_pair_markdown(report: PairComparisonReport, first: FirstDifferenceResult) -> str:
    lines = ["# HodgeCY II Hilbert Comparison - 84 vs 84a", "", "| Invariant | 84 | 84a | State |", "| --- | --- | --- | --- |"]
    for result in report.invariant_results:
        left = result.operands[0].value if result.operands else None
        right = result.operands[1].value if len(result.operands) > 1 else None
        lines.append(f"| {result.comparison_key} | `{left}` | `{right}` | {result.state.value} |")
    lines.extend(["", f"First Hilbert distinction: {first.first_difference or first.state.value}", ""])
    return "\n".join(lines)


def _defect_blob7_markdown(summaries: dict[str, dict[str, Any]]) -> str:
    lines = ["# HodgeCY II Critical-Degree Defect - Blob 7", ""]
    for arrangement_id in sorted(summaries):
        item = summaries[arrangement_id]
        node_status = item["node_scheme_status"]
        lines.extend(
            [
                f"## {arrangement_id}",
                f"- geometry_id: `{item['geometry_id']}`",
                f"- model: `{item['model']}`",
                f"- branch degree: `{item['branch_degree']}`",
                f"- critical-degree rule: `{item['critical_degree_rule']}`",
                f"- critical degree: `{item['critical_degree']}`",
                f"- N_k: `{item['N_k']}`",
                f"- imported singular scheme dimension: `{node_status['imported_singular_scheme_dimension']}`",
                f"- imported singular scheme degree: `{node_status['imported_singular_scheme_degree']}`",
                f"- complete support: `{node_status['complete_support']}`",
                f"- reduced: `{node_status['reduced']}`",
                f"- ordinary nodes: `{node_status['ordinary_nodes']}`",
                f"- exact node ideal available: `{item['exact_node_ideal_available']}`",
                f"- H_Sigma(kcrit): `{item['H_Sigma_kcrit']}`",
                f"- evaluation rank: `{item['evaluation_rank']}`",
                f"- defect: `{item['classical_defect']}`",
                f"- certificate status: `{item['certificate_status']}`",
                f"- reason: {item['reason']}",
            ]
        )
        if item["pending_template"] is not None:
            lines.append(f"- pending template: {item['pending_template']}")
        lines.append("")
    lines.extend(
        [
            "## Firewall",
            "- Critical degree known is not defect known.",
            "- Scheme degree 112 is not evaluation rank.",
            "- Evaluation rank and kernel are not source-assembly rank or kernel.",
            "- Classical defect is not a node-relation lattice rank.",
            "- Equal defects do not imply equal node schemes or equal source assemblies.",
            "- No vanishing-cycle relation or Hodge atom is constructed.",
            "",
        ]
    )
    return "\n".join(lines)


def _defect_pair_markdown(report: PairComparisonReport, first: FirstDifferenceResult) -> str:
    lines = ["# HodgeCY II Defect Comparison - 84 vs 84a", "", "| Invariant | 84 | 84a | State |", "| --- | --- | --- | --- |"]
    for result in report.invariant_results:
        left = result.operands[0].value if result.operands else None
        right = result.operands[1].value if len(result.operands) > 1 else None
        lines.append(f"| {result.comparison_key} | `{left}` | `{right}` | {result.state.value} |")
    lines.extend(["", f"First defect-level distinction: {first.first_difference or first.state.value}", ""])
    return "\n".join(lines)


def _integral_lattice_blob8_markdown(summaries: dict[str, dict[str, Any]], set_first: FirstDifferenceResult) -> str:
    lines = ["# HodgeCY II Integral Lattice - Blob 8", ""]
    lines.append("| Geometry | Role | Shape | Matrix Hash | rank_Q | rank_mod_2 | rank_mod_3 | SNF | Torsion | Sat Index |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for arrangement_id in sorted(summaries):
        item = summaries[arrangement_id]
        shape = "x".join(str(value) for value in item["matrix_shape"])
        snf = ",".join(str(value) for value in item["smith_normal_form"])
        torsion = ",".join(str(value) for value in item["torsion_factors"]) or "none"
        lines.append(
            f"| {arrangement_id} | {item['matrix_role']} | {shape} | `{item['matrix_hash'][:16]}` | "
            f"{item['rank_Q']} | {item['rank_mod_2']} | {item['rank_mod_3']} | `{snf}` | `{torsion}` | {item['saturation_index']} |"
        )
    lines.extend(
        [
            "",
            f"239/240/241 first source-lattice split: {set_first.first_difference or set_first.state.value}",
            "",
            "## Firewall",
            "- These are SOURCE_ASSEMBLY gluing matrices only.",
            "- A source assembly matrix is not a node-relation matrix.",
            "- Equal SNF does not prove geometric complex isomorphism.",
            "- Equal rational rank does not imply equal integral structure.",
            "- Source kernels are not vanishing-cycle relation lattices.",
            "- No source-to-node map or Hodge atom is computed.",
            "",
        ]
    )
    return "\n".join(lines)


def _source_lattice_pair_markdown(report: PairComparisonReport, first: FirstDifferenceResult) -> str:
    lines = ["# HodgeCY II Source Lattice Comparison - 84 vs 84a", "", "| Invariant | 84 | 84a | State |", "| --- | --- | --- | --- |"]
    for result in report.invariant_results:
        left = result.operands[0].value if result.operands else None
        right = result.operands[1].value if len(result.operands) > 1 else None
        lines.append(f"| {result.comparison_key} | `{left}` | `{right}` | {result.state.value} |")
    lines.extend(["", f"First source-lattice distinction: {first.first_difference or first.state.value}", ""])
    return "\n".join(lines)


def _node_relation_blob9_markdown(summaries: dict[str, dict[str, Any]]) -> str:
    lines = ["# HodgeCY II Node Relation - Blob 9", ""]
    lines.append("| Geometry | Expected Kind | Expected Nodes | kcrit | N_k | E_k Shape | rho Shape | Rational Relation | Integral Relation | Vanishing Cycle | Exceptional Curve |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for arrangement_id in sorted(summaries):
        item = summaries[arrangement_id]
        e_shape = "x".join(str(value) for value in item["expected_evaluation_matrix_shape"]) if item["expected_evaluation_matrix_shape"] else "UNKNOWN"
        rho_shape = "x".join(str(value) for value in item["expected_relation_map_shape"]) if item["expected_relation_map_shape"] else "UNKNOWN"
        lines.append(
            f"| {arrangement_id} | `{item['expected_relation_realization_kind']}` | `{item['expected_node_count']}` | "
            f"`{item['critical_degree']}` | `{item['evaluation_source_dimension']}` | `{e_shape}` | `{rho_shape}` | "
            f"`{item['rational_evaluation_relation_complex_status']}` | `{item['integral_evaluation_relation_complex_status']}` | "
            f"`{item['vanishing_cycle_relation_complex_status']}` | `{item['exceptional_curve_relation_complex_status']}` |"
        )
    lines.extend(
        [
            "",
            "## 84 / 84a Status",
            "- imported scheme degree: `112` for each",
            "- critical degree: `8` for each",
            "- expected evaluation matrix: `E_8: QQ^165 -> QQ^112` for each",
            "- expected relation map: `rho=E_8^T: QQ^112 -> QQ^165` for each",
            "- actual node generator module: `UNKNOWN`",
            "- rational evaluation relation complex: `UNKNOWN`",
            "- integral evaluation relation complex: `UNKNOWN`",
            "- vanishing-cycle and exceptional-curve relations: `UNKNOWN`",
            "",
            "## Firewall",
            "- Evaluation-condition relations are not vanishing-cycle relations.",
            "- Evaluation-condition relations are not exceptional-curve relations.",
            "- A source-assembly kernel is not a node-relation lattice.",
            "- Defect rank does not imply a vanishing-cycle relation rank.",
            "- Same rank does not imply same complex.",
            "- No source-to-node map or Hodge atom is constructed.",
            "",
        ]
    )
    return "\n".join(lines)


def _node_relation_pair_markdown(report: PairComparisonReport, first: FirstDifferenceResult) -> str:
    lines = ["# HodgeCY II Node Relation Status - 84 vs 84a", "", "| Invariant | 84 | 84a | State |", "| --- | --- | --- | --- |"]
    for result in report.invariant_results:
        left = result.operands[0].value if result.operands else None
        right = result.operands[1].value if len(result.operands) > 1 else None
        lines.append(f"| {result.comparison_key} | `{left}` | `{right}` | {result.state.value} |")
    lines.extend(["", f"First node-relation distinction: {first.first_difference or first.state.value}", ""])
    return "\n".join(lines)


def _source_to_node_blob10_markdown(summaries: dict[str, dict[str, Any]]) -> str:
    lines = ["# HodgeCY II Source-to-Node Comparison - Blob 10", ""]
    lines.extend(["## Source Complex", "", "| Geometry | d_src Shape | rank_Q | H1_Q | H0_Q | H0_Z torsion |", "| --- | --- | --- | --- | --- | --- |"])
    for arrangement_id in sorted(summaries):
        source = summaries[arrangement_id]["source_complex"]
        torsion = ",".join(str(value) for value in source["H0_Z_torsion"]) or "none"
        lines.append(
            f"| {arrangement_id} | `{source['d_src_shape']}` | `{source['rank_Q']}` | "
            f"`{source['H1_rank_Q']}` | `{source['H0_rank_Q']}` | `{torsion}` |"
        )
    lines.extend(["", "## Node Complex", "", "| Geometry | Expected Nodes | kcrit | E_k Shape | rho Shape | H1(C_eval) |", "| --- | --- | --- | --- | --- | --- |"])
    for arrangement_id in sorted(summaries):
        node = summaries[arrangement_id]["node_complex"]
        lines.append(
            f"| {arrangement_id} | `{node['expected_node_count']}` | `{node['critical_degree']}` | "
            f"`{node['expected_evaluation_matrix_shape']}` | `{node['expected_relation_map_shape']}` | `UNKNOWN` |"
        )
    lines.extend(["", "## Comparison Morphism", "", "| Geometry | Source -> Eval | Source -> Vanishing | Source -> Exceptional |", "| --- | --- | --- | --- |"])
    for arrangement_id in sorted(summaries):
        comparison = summaries[arrangement_id]["comparison_morphism"]
        lines.append(
            f"| {arrangement_id} | `{comparison['source_to_evaluation_chain_map']}` | "
            f"`{comparison['source_to_vanishing_chain_map']}` | `{comparison['source_to_exceptional_chain_map']}` |"
        )
    lines.extend(
        [
            "",
            "## 84 / 84a Conditional Rank Constraints",
            "- source H1_Q rank is `2` for both 84 and 84a.",
            "- if defect = 0, any induced H1 map to the evaluation relation is zero.",
            "- if defect = 1, injective H1 comparison is impossible.",
            "- if defect >= 2, injectivity is dimensionally possible but not established.",
            "",
            "## Firewall",
            "- Matching dimensions, ranks, SNF, geometry IDs, or node counts do not create a chain map.",
            "- A source-to-evaluation map is not a source-to-vanishing map.",
            "- Rational comparison does not imply integral comparison.",
            "- Feasibility is not existence.",
            "- No Hodge atom is constructed.",
            "",
        ]
    )
    return "\n".join(lines)


def _source_to_node_pair_markdown(report: PairComparisonReport, first: FirstDifferenceResult) -> str:
    lines = ["# HodgeCY II Source-to-Node Status - 84 vs 84a", "", "| Invariant | 84 | 84a | State |", "| --- | --- | --- | --- |"]
    for result in report.invariant_results:
        left = result.operands[0].value if result.operands else None
        right = result.operands[1].value if len(result.operands) > 1 else None
        lines.append(f"| {result.comparison_key} | `{left}` | `{right}` | {result.state.value} |")
    lines.extend(["", f"First source-to-node status distinction: {first.first_difference or first.state.value}", ""])
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
