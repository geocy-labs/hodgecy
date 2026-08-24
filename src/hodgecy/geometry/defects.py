"""Critical-degree evaluation maps and classical nodal defect checks.

Blob 7 builds on Blob 6 Hilbert functions.  The generic layer computes
evaluation ranks and cokernels for exact finite projective schemes; the phrase
"classical nodal defect" is reserved for cases whose geometric hypotheses are
certified.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import comb
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Iterable, Sequence

import sympy as sp

from hodgecy.core.results import EvidenceStatus, ResultKind
from hodgecy.core.serialization import canonical_json, stable_sha256
from hodgecy.geometry.projective_schemes import ProjectiveSchemeIdeal, hilbert_function, monomials_of_degree
from hodgecy.geometry.singularities import ProjectivePoint
from hodgecy.storage import ArtifactRecord, CalculationRun, CertificateRecord, ResultStore


class DefectConvention(str, Enum):
    NODAL_DOUBLE_SOLID_CLEMENS_CYNK = "nodal_double_solid_clemens_cynk"


class EvaluationMethod(str, Enum):
    HILBERT_FUNCTION = "hilbert_function"
    EXPLICIT_POINT_MATRIX = "explicit_point_matrix"


@dataclass(frozen=True, slots=True)
class CriticalDegreeResult:
    convention: DefectConvention
    ambient_base: str
    ambient_dimension: int
    cover_degree: int
    branch_degree: int
    characteristic: int
    d: int
    critical_degree: int
    source_dimension: int
    evidence_status: EvidenceStatus
    certificate: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "convention": self.convention.value,
            "ambient_base": self.ambient_base,
            "ambient_dimension": self.ambient_dimension,
            "cover_degree": self.cover_degree,
            "branch_degree": self.branch_degree,
            "characteristic": self.characteristic,
            "d": self.d,
            "critical_degree": self.critical_degree,
            "source_dimension": self.source_dimension,
            "evidence_status": self.evidence_status.value,
            "certificate": self.certificate,
        }


@dataclass(frozen=True, slots=True)
class EvaluationMapResult:
    geometry_id: str | None
    scheme_ideal_hash: str | None
    degree: int
    source_dimension: int
    target_length: int | None
    rank: int | None
    kernel_dimension: int | None
    cokernel_dimension: int | None
    rank_deficiency: int | None
    method: EvaluationMethod
    coefficient_field: str
    evidence_status: EvidenceStatus
    certificates: tuple[dict[str, Any], ...] = ()
    provenance: str | None = None
    matrix_shape: tuple[int, int] | None = None
    monomial_basis: tuple[tuple[int, ...], ...] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "geometry_id": self.geometry_id,
            "scheme_ideal_hash": self.scheme_ideal_hash,
            "degree": self.degree,
            "source_dimension": self.source_dimension,
            "target_length": self.target_length,
            "rank": self.rank,
            "kernel_dimension": self.kernel_dimension,
            "cokernel_dimension": self.cokernel_dimension,
            "rank_deficiency": self.rank_deficiency,
            "method": self.method.value,
            "coefficient_field": self.coefficient_field,
            "evidence_status": self.evidence_status.value,
            "certificates": list(self.certificates),
            "provenance": self.provenance,
            "matrix_shape": None if self.matrix_shape is None else list(self.matrix_shape),
            "monomial_basis": None if self.monomial_basis is None else [list(item) for item in self.monomial_basis],
        }


@dataclass(frozen=True, slots=True)
class EvaluationCrossCheckResult:
    degree: int
    hilbert_rank: int | None
    explicit_rank: int | None
    agrees: bool | None
    evidence_status: EvidenceStatus
    certificate: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "degree": self.degree,
            "hilbert_rank": self.hilbert_rank,
            "explicit_rank": self.explicit_rank,
            "agrees": self.agrees,
            "evidence_status": self.evidence_status.value,
            "certificate": self.certificate,
        }


@dataclass(frozen=True, slots=True)
class ClassicalDefectResult:
    geometry_id: str | None
    node_scheme_id: str | None
    scheme_ideal_hash: str | None
    branch_degree: int | None
    critical_degree: int | None
    source_dimension: int | None
    scheme_length: int | None
    evaluation_rank: int | None
    cokernel_dimension: int | None
    rank_deficiency: int | None
    classical_defect: int | None
    evidence_status: EvidenceStatus
    prerequisites: dict[str, bool]
    certificate_id: str | None = None
    method: str | None = None
    provenance: str | None = None
    certificate: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "geometry_id": self.geometry_id,
            "node_scheme_id": self.node_scheme_id,
            "scheme_ideal_hash": self.scheme_ideal_hash,
            "branch_degree": self.branch_degree,
            "critical_degree": self.critical_degree,
            "N_k": self.source_dimension,
            "scheme_length": self.scheme_length,
            "evaluation_rank": self.evaluation_rank,
            "cokernel_dimension": self.cokernel_dimension,
            "rank_deficiency": self.rank_deficiency,
            "classical_defect": self.classical_defect,
            "evidence_status": self.evidence_status.value,
            "prerequisites": dict(self.prerequisites),
            "certificate_id": self.certificate_id,
            "method": self.method,
            "provenance": self.provenance,
            "certificate": self.certificate,
        }


def projective_source_dimension(ambient_dimension: int, degree: int) -> int:
    if ambient_dimension < 0 or degree < 0:
        raise ValueError("Ambient dimension and degree must be nonnegative.")
    return comb(ambient_dimension + degree, ambient_dimension)


def resolve_critical_degree(
    convention: DefectConvention | str,
    *,
    branch_degree: int,
    ambient_base: str = "P^3",
    ambient_dimension: int = 3,
    cover_degree: int = 2,
    characteristic: int = 0,
) -> CriticalDegreeResult:
    convention = DefectConvention(convention)
    if convention is not DefectConvention.NODAL_DOUBLE_SOLID_CLEMENS_CYNK:
        raise ValueError(f"Unsupported defect convention: {convention.value}")
    if ambient_base != "P^3" or ambient_dimension != 3:
        raise ValueError("The Clemens/Cynk nodal double-solid rule is implemented only for base P^3.")
    if cover_degree != 2:
        raise ValueError("The Clemens/Cynk rule requires a double cover.")
    if characteristic != 0:
        raise ValueError("The Clemens/Cynk rule is recorded here only in characteristic 0.")
    if branch_degree <= 0 or branch_degree % 2:
        raise ValueError("The branch degree must be positive and even.")
    d = branch_degree // 2
    critical_degree = 3 * d - 4
    if critical_degree < 0:
        raise ValueError("The resolved critical degree is negative.")
    certificate = {
        "certificate_type": "critical_degree_rule",
        "convention": convention.value,
        "theorem_reference": "Clemens/Cynk nodal double-solid convention",
        "rule": "for a double cover of P^3 branched over degree 2d, k_crit = 3d - 4",
        "applicability_checks": {
            "ambient_base": ambient_base,
            "ambient_dimension": ambient_dimension,
            "cover_degree": cover_degree,
            "characteristic": characteristic,
            "branch_degree_even": True,
        },
    }
    return CriticalDegreeResult(
        convention=convention,
        ambient_base=ambient_base,
        ambient_dimension=ambient_dimension,
        cover_degree=cover_degree,
        branch_degree=branch_degree,
        characteristic=characteristic,
        d=d,
        critical_degree=critical_degree,
        source_dimension=projective_source_dimension(ambient_dimension, critical_degree),
        evidence_status=EvidenceStatus.VERIFIED,
        certificate=certificate,
    )


def evaluation_from_hilbert(
    ideal: ProjectiveSchemeIdeal,
    degree: int,
    *,
    target_length: int | None = None,
    order: str = "grevlex",
) -> EvaluationMapResult:
    value = hilbert_function(ideal, degree, order=order)
    length = target_length if target_length is not None else ideal.scheme_degree
    source_dimension = value.dim_S_d
    rank = value.dim_quotient_d
    return EvaluationMapResult(
        geometry_id=ideal.geometry_id,
        scheme_ideal_hash=ideal.ideal_hash,
        degree=degree,
        source_dimension=source_dimension,
        target_length=length,
        rank=rank,
        kernel_dimension=source_dimension - rank,
        cokernel_dimension=None if length is None else length - rank,
        rank_deficiency=None if length is None else min(source_dimension, length) - rank,
        method=EvaluationMethod.HILBERT_FUNCTION,
        coefficient_field=ideal.base_field,
        evidence_status=value.evidence_status,
        certificates=(
            {
                "certificate_type": "evaluation_rank",
                "route": EvaluationMethod.HILBERT_FUNCTION.value,
                "identity": "rank(ev_{Sigma,k}) = dim(S/I_Sigma)_k",
                "degree": degree,
                "hilbert_value": value.to_dict(),
                "firewall": {
                    "evaluation_rank_is_not_source_assembly_rank": True,
                    "evaluation_kernel_is_not_source_assembly_kernel": True,
                },
            },
        ),
        provenance="computed from exact homogeneous ideal via Blob 6 Hilbert function",
    )


def evaluation_from_points(
    points: Iterable[ProjectivePoint | Sequence[Any]],
    variables: Sequence[str],
    degree: int,
    *,
    geometry_id: str | None = None,
) -> EvaluationMapResult:
    if degree < 0:
        raise ValueError("Evaluation degree must be nonnegative.")
    projective_points = _unique_points(points)
    if not projective_points:
        raise ValueError("Cannot evaluate on an empty point set.")
    if any(len(point.coordinates) != len(variables) for point in projective_points):
        raise ValueError("Point coordinate count must match the declared variables.")
    basis = monomials_of_degree(len(variables), degree)
    rows = [[_evaluate_monomial(point.coordinates, monomial) for monomial in basis] for point in projective_points]
    matrix = sp.Matrix(rows)
    rank = int(matrix.rank())
    source_dimension = len(basis)
    target_length = len(projective_points)
    return EvaluationMapResult(
        geometry_id=geometry_id,
        scheme_ideal_hash=None,
        degree=degree,
        source_dimension=source_dimension,
        target_length=target_length,
        rank=rank,
        kernel_dimension=source_dimension - rank,
        cokernel_dimension=target_length - rank,
        rank_deficiency=min(source_dimension, target_length) - rank,
        method=EvaluationMethod.EXPLICIT_POINT_MATRIX,
        coefficient_field="QQ",
        evidence_status=EvidenceStatus.VERIFIED,
        certificates=(
            {
                "certificate_type": "evaluation_rank",
                "route": EvaluationMethod.EXPLICIT_POINT_MATRIX.value,
                "matrix_convention": "rows are sorted normalized projective points; columns are monomials_of_degree order",
                "point_ids": [point.point_id for point in projective_points],
                "degree": degree,
            },
        ),
        provenance="explicit rational point evaluation matrix",
        matrix_shape=(target_length, source_dimension),
        monomial_basis=basis,
    )


def cross_check_evaluation_methods(hilbert: EvaluationMapResult, explicit: EvaluationMapResult) -> EvaluationCrossCheckResult:
    if hilbert.degree != explicit.degree:
        raise ValueError("Cannot cross-check evaluation results in different degrees.")
    agrees = None if hilbert.rank is None or explicit.rank is None else hilbert.rank == explicit.rank
    certificate = {
        "certificate_type": "hilbert_evaluation_agreement",
        "degree": hilbert.degree,
        "hilbert_method": hilbert.method.value,
        "explicit_method": explicit.method.value,
        "hilbert_rank": hilbert.rank,
        "explicit_rank": explicit.rank,
        "agrees": agrees,
    }
    return EvaluationCrossCheckResult(
        degree=hilbert.degree,
        hilbert_rank=hilbert.rank,
        explicit_rank=explicit.rank,
        agrees=agrees,
        evidence_status=EvidenceStatus.VERIFIED if agrees is True else EvidenceStatus.UNKNOWN,
        certificate=certificate,
    )


def classical_defect_from_evaluation(
    evaluation: EvaluationMapResult,
    *,
    critical_degree: CriticalDegreeResult,
    prerequisites: dict[str, bool],
    node_scheme_id: str | None = None,
) -> ClassicalDefectResult:
    all_prerequisites = all(prerequisites.values())
    exact_evaluation = evaluation.evidence_status is EvidenceStatus.VERIFIED and evaluation.cokernel_dimension is not None
    verified = all_prerequisites and exact_evaluation and evaluation.degree == critical_degree.critical_degree
    classical_defect = evaluation.cokernel_dimension if verified else None
    certificate = {
        "certificate_type": "classical_nodal_defect",
        "critical_degree_certificate": critical_degree.certificate,
        "evaluation_certificates": [dict(item) for item in evaluation.certificates],
        "prerequisites": dict(prerequisites),
        "firewall": defect_firewall(),
    }
    return ClassicalDefectResult(
        geometry_id=evaluation.geometry_id,
        node_scheme_id=node_scheme_id,
        scheme_ideal_hash=evaluation.scheme_ideal_hash,
        branch_degree=critical_degree.branch_degree,
        critical_degree=critical_degree.critical_degree,
        source_dimension=evaluation.source_dimension,
        scheme_length=evaluation.target_length,
        evaluation_rank=evaluation.rank,
        cokernel_dimension=evaluation.cokernel_dimension,
        rank_deficiency=evaluation.rank_deficiency,
        classical_defect=classical_defect,
        evidence_status=EvidenceStatus.VERIFIED if verified else EvidenceStatus.UNKNOWN,
        prerequisites=dict(prerequisites),
        method=evaluation.method.value,
        provenance="classical defect promotion requires certified nodal double-solid prerequisites",
        certificate=certificate,
    )


def defect_firewall() -> dict[str, bool]:
    return {
        "critical_degree_known_does_not_imply_defect_known": True,
        "scheme_degree_does_not_imply_evaluation_rank": True,
        "evaluation_rank_is_not_source_assembly_rank": True,
        "evaluation_kernel_is_not_source_assembly_kernel": True,
        "classical_defect_is_not_node_relation_lattice_rank": True,
        "equal_defects_do_not_imply_equal_node_schemes": True,
        "equal_defects_do_not_imply_equal_source_assembly_complexes": True,
        "noncertified_evaluation_deficiency_is_not_classical_defect": True,
        "no_vanishing_cycle_relation_constructed": True,
        "no_hodge_atom_constructed": True,
    }


def begin_defect_run(store: ResultStore, geometry_id: str, *, input_metadata: Any, parameters: Any | None = None, notes: str | None = None) -> CalculationRun:
    return store.begin_run(
        geometry_id=geometry_id,
        calculation_type="critical_degree_evaluation_defect_blob7",
        input_metadata=input_metadata,
        parameters=parameters,
        backend="hodgecy.geometry.defects",
        coefficient_ring="QQ",
        notes=notes,
    )


def persist_classical_defect_result(
    store: ResultStore,
    *,
    run_id: str,
    critical_degree: CriticalDegreeResult | None,
    defect_result: ClassicalDefectResult,
) -> tuple[CertificateRecord, ArtifactRecord, tuple[Any, ...]]:
    run = store.get_run(run_id)
    payload = {
        "critical_degree": None if critical_degree is None else critical_degree.to_dict(),
        "defect_result": defect_result.to_dict(),
        "firewall": defect_firewall(),
    }
    certificate = store.record_certificate(
        certificate_type="classical_nodal_defect",
        subject_type="geometry",
        subject_id=run.geometry_id,
        method="hodgecy.geometry.defects",
        evidence=payload,
        generated_by_run_id=run_id,
        notes="Blob 7 critical-degree/evaluation checkpoint; classical defect is VERIFIED only when prerequisites are complete.",
    )
    with TemporaryDirectory() as tmp:
        artifact_path = Path(tmp) / "classical_defect_result.json"
        artifact_path.write_text(canonical_json(payload) + "\n", encoding="utf-8")
        artifact = store.attach_artifact(
            run_id=run_id,
            role="classical_defect_result",
            artifact_type="json",
            source_path=artifact_path,
            storage_format="json",
            coefficient_ring="QQ",
            metadata={"critical_degree": defect_result.critical_degree, "scheme_ideal_hash": defect_result.scheme_ideal_hash},
        )
    method = defect_result.method or "hodgecy.geometry.defects"
    invariants = []
    for name, value, status, notes in (
        ("critical_degree", defect_result.critical_degree, EvidenceStatus.UNKNOWN if defect_result.critical_degree is None else EvidenceStatus.VERIFIED, "theorem-derived critical degree; not a defect value"),
        ("evaluation_source_dimension", defect_result.source_dimension, EvidenceStatus.UNKNOWN if defect_result.source_dimension is None else EvidenceStatus.VERIFIED, "N_k = h^0(P^3,O(k))"),
        ("evaluation_target_length", defect_result.scheme_length, EvidenceStatus.UNKNOWN if defect_result.scheme_length is None else EvidenceStatus.VERIFIED, "scheme length used as evaluation target dimension"),
        ("evaluation_rank", defect_result.evaluation_rank, EvidenceStatus.UNKNOWN if defect_result.evaluation_rank is None else defect_result.evidence_status, "rank of ev_{Sigma,k}; not a source-assembly rank"),
        ("evaluation_kernel_dimension", None if defect_result.source_dimension is None or defect_result.evaluation_rank is None else defect_result.source_dimension - defect_result.evaluation_rank, EvidenceStatus.UNKNOWN if defect_result.evaluation_rank is None else defect_result.evidence_status, "kernel of the projective evaluation map; not a source-assembly kernel"),
        ("evaluation_cokernel_dimension", defect_result.cokernel_dimension, EvidenceStatus.UNKNOWN if defect_result.cokernel_dimension is None else defect_result.evidence_status, "algebraic evaluation cokernel dimension"),
        ("evaluation_rank_deficiency", defect_result.rank_deficiency, EvidenceStatus.UNKNOWN if defect_result.rank_deficiency is None else defect_result.evidence_status, "min(N_k,length)-rank; separate from cokernel if N_k < length"),
        ("classical_defect", defect_result.classical_defect, defect_result.evidence_status if defect_result.classical_defect is not None else EvidenceStatus.UNKNOWN, "classical nodal defect only after prerequisite certification"),
    ):
        invariants.append(
            store.record_invariant(
                run_id=run_id,
                name=name,
                value=value,
                result_kind=ResultKind.NODE_GEOMETRY,
                evidence_status=status,
                method=method,
                certificate_id=certificate.certificate_id,
                notes=f"{notes}; artifact_id={artifact.artifact_id}",
            )
        )
    return certificate, artifact, tuple(invariants)


def unknown_classical_defect_result(
    *,
    geometry_id: str,
    critical_degree: CriticalDegreeResult | None,
    scheme_length: int | None = None,
    reason: str,
    prerequisites: dict[str, bool] | None = None,
) -> ClassicalDefectResult:
    default_prerequisites = {
        "finite_singular_scheme": False,
        "complete_support": False,
        "reducedness": False,
        "ordinary_node_classification": False,
        "exact_node_ideal": False,
        "applicable_double_solid_model": critical_degree is not None,
        "certified_critical_degree_rule": critical_degree is not None,
        "exact_evaluation_or_hilbert_computation": False,
    }
    if prerequisites is not None:
        default_prerequisites.update(prerequisites)
    return ClassicalDefectResult(
        geometry_id=geometry_id,
        node_scheme_id=None,
        scheme_ideal_hash=None,
        branch_degree=None if critical_degree is None else critical_degree.branch_degree,
        critical_degree=None if critical_degree is None else critical_degree.critical_degree,
        source_dimension=None if critical_degree is None else critical_degree.source_dimension,
        scheme_length=scheme_length,
        evaluation_rank=None,
        cokernel_dimension=None,
        rank_deficiency=None,
        classical_defect=None,
        evidence_status=EvidenceStatus.UNKNOWN,
        prerequisites=default_prerequisites,
        method=None,
        provenance=reason,
        certificate={
            "certificate_type": "classical_nodal_defect",
            "status": EvidenceStatus.UNKNOWN.value,
            "reason": reason,
            "critical_degree_certificate": None if critical_degree is None else critical_degree.certificate,
            "firewall": defect_firewall(),
        },
    )


def _evaluate_monomial(coordinates: Sequence[sp.Expr], monomial: Sequence[int]) -> sp.Expr:
    value = sp.Integer(1)
    for coordinate, exponent in zip(coordinates, monomial):
        value *= coordinate**exponent
    return sp.simplify(value)


def _unique_points(points: Iterable[ProjectivePoint | Sequence[Any]]) -> tuple[ProjectivePoint, ...]:
    unique: dict[str, ProjectivePoint] = {}
    for point in points:
        projective = point if isinstance(point, ProjectivePoint) else ProjectivePoint.from_iterable(point)
        unique[projective.point_id] = projective
    return tuple(unique[key] for key in sorted(unique))
