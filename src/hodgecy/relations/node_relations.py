"""Verified node-relation complexes.

The homological convention in this module is ``[C_node -> T]`` with
``C_node`` in degree 1 and ``T`` in degree 0.  A relation module is therefore
``ker(rho)`` for an explicitly supplied realization map ``rho``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Iterable, Sequence

import sympy as sp

from hodgecy.algebra import (
    IntegerLinearMap,
    MatrixSemanticRole,
    image_lattice,
    integer_kernel,
    rational_rank,
    smith_normal_form_data,
)
from hodgecy.core.results import EvidenceStatus, ResultKind
from hodgecy.core.serialization import canonical_json, stable_sha256
from hodgecy.geometry.defects import EvaluationMethod
from hodgecy.geometry.projective_schemes import ProjectiveSchemeIdeal, hilbert_function, monomials_of_degree
from hodgecy.geometry.singularities import ProjectivePoint
from hodgecy.storage import ArtifactRecord, CalculationRun, CertificateRecord, ResultStore


class RelationRealizationKind(str, Enum):
    EVALUATION_CONDITION = "evaluation_condition"
    EXCEPTIONAL_CURVE = "exceptional_curve"
    VANISHING_CYCLE = "vanishing_cycle"
    DEFORMATION_OBSTRUCTION = "deformation_obstruction"
    IMPORTED_CERTIFIED = "imported_certified"
    USER_SUPPLIED = "user_supplied"
    UNKNOWN = "unknown"


class NodeRelationError(ValueError):
    """Base class for node-relation framework errors."""


class VerifiedNodeSupportRequiredError(NodeRelationError):
    """Raised when a finite node module is requested without verified support."""


class GeometricRelationPresentationUnavailableError(NodeRelationError):
    """Raised for relation kinds requiring data not supplied to this framework."""


class IntegralRelationModelUnavailableError(NodeRelationError):
    """Raised when an integral relation complex lacks an integral certificate."""


@dataclass(frozen=True, slots=True)
class NodeGeneratorModule:
    geometry_id: str
    node_scheme_id: str
    coefficient_ring: str
    ordered_node_ids: tuple[str, ...]
    rank: int | None
    evidence_status: EvidenceStatus
    node_scheme_certificate: dict[str, Any] = field(default_factory=dict)
    provenance: str | None = None

    @classmethod
    def from_verified_support(
        cls,
        *,
        geometry_id: str,
        node_scheme_id: str,
        ordered_node_ids: Iterable[str],
        node_scheme_certificate: dict[str, Any],
        coefficient_ring: str = "QQ",
        provenance: str | None = None,
    ) -> "NodeGeneratorModule":
        node_ids = tuple(str(item) for item in ordered_node_ids)
        if not node_ids:
            raise VerifiedNodeSupportRequiredError("A node-generator module requires an ordered verified finite support.")
        status = _certificate_status(node_scheme_certificate)
        if status is not EvidenceStatus.VERIFIED:
            raise VerifiedNodeSupportRequiredError("A node-generator module cannot be certified from degree or incomplete support alone.")
        return cls(
            geometry_id=geometry_id,
            node_scheme_id=node_scheme_id,
            coefficient_ring=str(coefficient_ring),
            ordered_node_ids=node_ids,
            rank=len(node_ids),
            evidence_status=EvidenceStatus.VERIFIED,
            node_scheme_certificate=dict(node_scheme_certificate),
            provenance=provenance,
        )

    @classmethod
    def from_degree_only(cls, *args: Any, **kwargs: Any) -> "NodeGeneratorModule":
        raise VerifiedNodeSupportRequiredError("A scheme degree is not a verified finite node support or ordered generator module.")

    @classmethod
    def expected_uncertified(
        cls,
        *,
        geometry_id: str,
        node_scheme_id: str,
        expected_rank: int | None,
        reason: str,
        coefficient_ring: str = "QQ",
        provenance: str | None = None,
    ) -> "NodeGeneratorModule":
        return cls(
            geometry_id=geometry_id,
            node_scheme_id=node_scheme_id,
            coefficient_ring=str(coefficient_ring),
            ordered_node_ids=(),
            rank=expected_rank,
            evidence_status=EvidenceStatus.UNKNOWN,
            node_scheme_certificate={"status": EvidenceStatus.UNKNOWN.value, "reason": reason},
            provenance=provenance,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "geometry_id": self.geometry_id,
            "node_scheme_id": self.node_scheme_id,
            "coefficient_ring": self.coefficient_ring,
            "ordered_node_ids": list(self.ordered_node_ids),
            "rank": self.rank,
            "evidence_status": self.evidence_status.value,
            "node_scheme_certificate": self.node_scheme_certificate,
            "provenance": self.provenance,
            "generator_module_firewall": {
                "degree_only_is_not_support": True,
                "source_assembly_generators_are_not_node_generators": True,
            },
        }


@dataclass(frozen=True, slots=True)
class TargetModule:
    target_id: str
    coefficient_ring: str
    rank: int
    basis_labels: tuple[str, ...] = ()
    provenance: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "coefficient_ring": self.coefficient_ring,
            "rank": self.rank,
            "basis_labels": list(self.basis_labels),
            "provenance": self.provenance,
        }


@dataclass(frozen=True, slots=True)
class NodeRelationComplex:
    node_module: NodeGeneratorModule
    target_module: TargetModule
    realization_kind: RelationRealizationKind
    coefficient_ring: str
    realization_matrix: tuple[tuple[str, ...], ...]
    map_hash: str
    complex_hash: str
    image_rank: int
    relation_rank: int
    cokernel_dimension: int
    relation_basis: tuple[tuple[str, ...], ...]
    method: str
    evidence_status: EvidenceStatus
    certificate: dict[str, Any] = field(default_factory=dict)
    provenance: str | None = None
    smith_normal_form: tuple[int, ...] | None = None
    torsion_type: tuple[int, ...] | None = None
    saturation_index: int | None = None

    @classmethod
    def from_presentation(
        cls,
        *,
        node_module: NodeGeneratorModule,
        target_module: TargetModule,
        realization_matrix: Any,
        realization_kind: RelationRealizationKind | str,
        certificate: dict[str, Any],
        provenance: str | None = None,
        evidence_status: EvidenceStatus = EvidenceStatus.VERIFIED,
        method: str = "explicit realization map rho: C_node -> T",
    ) -> "NodeRelationComplex":
        kind = RelationRealizationKind(realization_kind)
        if kind is RelationRealizationKind.UNKNOWN:
            raise GeometricRelationPresentationUnavailableError("UNKNOWN is a status, not a realized relation presentation.")
        if node_module.rank is None or node_module.evidence_status is not EvidenceStatus.VERIFIED:
            raise VerifiedNodeSupportRequiredError("An explicit relation complex requires a verified node-generator module.")
        if node_module.coefficient_ring != target_module.coefficient_ring:
            raise NodeRelationError("Node and target modules must use the same coefficient ring.")
        ring = node_module.coefficient_ring
        if ring == "ZZ":
            return _integral_node_relation_complex(
                node_module=node_module,
                target_module=target_module,
                realization_matrix=realization_matrix,
                realization_kind=kind,
                certificate=certificate,
                provenance=provenance,
                evidence_status=evidence_status,
                method=method,
            )
        if ring != "QQ":
            raise NodeRelationError(f"Unsupported coefficient ring for node relation complex: {ring}")
        matrix = _coerce_exact_matrix(realization_matrix)
        _validate_shape(matrix, target_module.rank, node_module.rank)
        rank = int(matrix.rank())
        basis = _string_matrix(matrix.nullspace())
        matrix_entries = _string_matrix(matrix)
        map_hash = stable_sha256({"coefficient_ring": "QQ", "matrix": matrix_entries, "convention": "rho:C_node->T"})
        complex_hash = stable_sha256(
            {
                "map_hash": map_hash,
                "realization_kind": kind.value,
                "node_module": node_module.to_dict(),
                "target_module": target_module.to_dict(),
            }
        )
        return cls(
            node_module=node_module,
            target_module=target_module,
            realization_kind=kind,
            coefficient_ring="QQ",
            realization_matrix=matrix_entries,
            map_hash=map_hash,
            complex_hash=complex_hash,
            image_rank=rank,
            relation_rank=node_module.rank - rank,
            cokernel_dimension=target_module.rank - rank,
            relation_basis=basis,
            method=method,
            evidence_status=EvidenceStatus(evidence_status),
            certificate=dict(certificate),
            provenance=provenance,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_module": self.node_module.to_dict(),
            "target_module": self.target_module.to_dict(),
            "homological_convention": {"degree_1": "C_node", "degree_0": "T", "relation_module": "ker(rho)"},
            "realization_kind": self.realization_kind.value,
            "coefficient_ring": self.coefficient_ring,
            "realization_matrix": [list(row) for row in self.realization_matrix],
            "map_hash": self.map_hash,
            "complex_hash": self.complex_hash,
            "image_rank": self.image_rank,
            "relation_rank": self.relation_rank,
            "cokernel_dimension": self.cokernel_dimension,
            "relation_basis": [list(row) for row in self.relation_basis],
            "method": self.method,
            "evidence_status": self.evidence_status.value,
            "certificate": self.certificate,
            "provenance": self.provenance,
            "smith_normal_form": None if self.smith_normal_form is None else list(self.smith_normal_form),
            "torsion_type": None if self.torsion_type is None else list(self.torsion_type),
            "saturation_index": self.saturation_index,
            "firewall": node_relation_firewall(),
        }


@dataclass(frozen=True, slots=True)
class EvaluationRelationRankSummary:
    geometry_id: str | None
    node_scheme_id: str | None
    degree: int
    source_dimension: int
    target_length: int | None
    evaluation_rank: int | None
    relation_rank: int | None
    cokernel_dimension: int | None
    evidence_status: EvidenceStatus
    method: EvaluationMethod
    certificate: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "geometry_id": self.geometry_id,
            "node_scheme_id": self.node_scheme_id,
            "degree": self.degree,
            "source_dimension": self.source_dimension,
            "target_length": self.target_length,
            "evaluation_rank": self.evaluation_rank,
            "relation_rank": self.relation_rank,
            "cokernel_dimension": self.cokernel_dimension,
            "evidence_status": self.evidence_status.value,
            "method": self.method.value,
            "certificate": self.certificate,
        }


def evaluation_relation_from_matrix(
    evaluation_matrix: Any,
    *,
    node_module: NodeGeneratorModule,
    degree: int,
    source_dimension: int | None = None,
    monomial_basis: Sequence[Sequence[int]] | None = None,
    trivialization: dict[str, Any] | None = None,
    classical_defect: int | None = None,
    provenance: str | None = None,
) -> NodeRelationComplex:
    matrix = _coerce_exact_matrix(evaluation_matrix)
    if node_module.rank is None:
        raise VerifiedNodeSupportRequiredError("Evaluation relation construction requires a verified node-module rank.")
    if matrix.rows != node_module.rank:
        raise NodeRelationError("Evaluation matrix row count must equal the node-generator rank.")
    n_source = int(source_dimension if source_dimension is not None else matrix.cols)
    if matrix.cols != n_source:
        raise NodeRelationError("Evaluation matrix column count must match the supplied source dimension.")
    rho = matrix.T
    rank = int(matrix.rank())
    relation_dim = node_module.rank - rank
    if classical_defect is not None and classical_defect != relation_dim:
        raise NodeRelationError("Critical-degree evaluation relation dimension disagrees with the supplied classical defect.")
    target = TargetModule(
        target_id=f"S_{degree}",
        coefficient_ring="QQ",
        rank=n_source,
        basis_labels=tuple(_monomial_label(item) for item in monomial_basis) if monomial_basis is not None else (),
        provenance="critical-degree homogeneous source space",
    )
    certificate = {
        "certificate_type": "rational_critical_degree_evaluation_relation",
        "degree": degree,
        "evaluation_matrix_shape": [int(matrix.rows), int(matrix.cols)],
        "relation_map_shape": [int(rho.rows), int(rho.cols)],
        "evaluation_rank": rank,
        "relation_rank_identity": "dim ker(E^T) = r - rank(E) = dim coker(E) when target length is r",
        "relation_rank": relation_dim,
        "classical_defect_cross_check": classical_defect,
        "trivialization": trivialization or {},
        "firewall": node_relation_firewall(),
    }
    return NodeRelationComplex.from_presentation(
        node_module=node_module,
        target_module=target,
        realization_matrix=rho,
        realization_kind=RelationRealizationKind.EVALUATION_CONDITION,
        certificate=certificate,
        provenance=provenance or "transpose of exact rational point-evaluation matrix",
        method="critical-degree evaluation relation via rho=E^T",
    )


def evaluation_relation_from_points(
    points: Iterable[ProjectivePoint | Sequence[Any]],
    variables: Sequence[str],
    degree: int,
    *,
    geometry_id: str,
    node_scheme_id: str,
    node_scheme_certificate: dict[str, Any],
    ordered_node_ids: Sequence[str] | None = None,
    provenance: str | None = None,
) -> NodeRelationComplex:
    projective_points = _unique_points(points)
    ids = tuple(ordered_node_ids) if ordered_node_ids is not None else tuple(point.point_id for point in projective_points)
    node_module = NodeGeneratorModule.from_verified_support(
        geometry_id=geometry_id,
        node_scheme_id=node_scheme_id,
        ordered_node_ids=ids,
        node_scheme_certificate=node_scheme_certificate,
        provenance=provenance,
    )
    basis = monomials_of_degree(len(variables), degree)
    rows = [[_evaluate_monomial(point.coordinates, monomial) for monomial in basis] for point in projective_points]
    return evaluation_relation_from_matrix(
        rows,
        node_module=node_module,
        degree=degree,
        source_dimension=len(basis),
        monomial_basis=basis,
        trivialization={
            "projective_point_order": [point.point_id for point in projective_points],
            "scaling_convention": "normalized projective coordinate representatives",
            "variables": list(variables),
        },
        provenance=provenance or "exact rational point support and normalized projective trivialization",
    )


def evaluation_relation_from_hilbert(
    ideal: ProjectiveSchemeIdeal,
    degree: int,
    *,
    node_scheme_id: str | None = None,
    target_length: int | None = None,
    order: str = "grevlex",
) -> EvaluationRelationRankSummary:
    value = hilbert_function(ideal, degree, order=order)
    length = target_length if target_length is not None else ideal.scheme_degree
    relation_rank = None if length is None else length - value.dim_quotient_d
    certificate = {
        "certificate_type": "evaluation_relation_hilbert_rank_summary",
        "route": "quotient_ring_hilbert_function",
        "identity": "rank(ev_{Sigma,k}) = dim(S/I_Sigma)_k; relation rank requires length-rank",
        "degree": degree,
        "hilbert_value": value.to_dict(),
        "matrix_available": False,
        "firewall": node_relation_firewall(),
    }
    return EvaluationRelationRankSummary(
        geometry_id=ideal.geometry_id,
        node_scheme_id=node_scheme_id,
        degree=degree,
        source_dimension=value.dim_S_d,
        target_length=length,
        evaluation_rank=value.dim_quotient_d,
        relation_rank=relation_rank,
        cokernel_dimension=relation_rank,
        evidence_status=value.evidence_status,
        method=EvaluationMethod.HILBERT_FUNCTION,
        certificate=certificate,
    )


def unsupported_vanishing_cycle_relation(*args: Any, **kwargs: Any) -> NodeRelationComplex:
    raise GeometricRelationPresentationUnavailableError("Vanishing-cycle relations require topological cycle/monodromy data; no constructor is available from node counts or evaluation data alone.")


def unsupported_exceptional_curve_relation(*args: Any, **kwargs: Any) -> NodeRelationComplex:
    raise GeometricRelationPresentationUnavailableError("Exceptional-curve relations require an explicit resolution and curve-homology presentation.")


def node_relation_firewall() -> dict[str, bool]:
    return {
        "evaluation_relation_is_not_vanishing_cycle_relation": True,
        "evaluation_relation_is_not_exceptional_curve_relation": True,
        "source_assembly_kernel_is_not_node_relation_lattice": True,
        "classical_defect_does_not_imply_vanishing_cycle_relation_rank": True,
        "same_rank_does_not_imply_same_complex": True,
        "degree_only_does_not_verify_node_generator_module": True,
        "source_to_node_map_not_constructed": True,
        "no_hodge_atom_constructed": True,
    }


def begin_node_relation_run(store: ResultStore, geometry_id: str, *, input_metadata: Any, parameters: Any | None = None, notes: str | None = None) -> CalculationRun:
    return store.begin_run(
        geometry_id=geometry_id,
        calculation_type="node_relation_blob9",
        input_metadata=input_metadata,
        parameters=parameters,
        backend="hodgecy.relations.node_relations",
        coefficient_ring="QQ/ZZ",
        notes=notes,
    )


def persist_node_relation_complex(
    store: ResultStore,
    *,
    run_id: str,
    complex: NodeRelationComplex,
) -> tuple[CertificateRecord, ArtifactRecord, tuple[Any, ...]]:
    run = store.get_run(run_id)
    payload = complex.to_dict()
    certificate = store.record_certificate(
        certificate_type="node_relation_complex",
        subject_type="geometry",
        subject_id=run.geometry_id,
        method="hodgecy.relations.node_relations",
        evidence=payload,
        generated_by_run_id=run_id,
        notes="Blob 9 node-relation complex; realization kind is explicit and not inferred from matrix role.",
    )
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "node_relation_complex.json"
        path.write_text(canonical_json(payload) + "\n", encoding="utf-8")
        artifact = store.attach_artifact(
            run_id=run_id,
            role="node_relation_complex",
            artifact_type="json",
            source_path=path,
            storage_format="json",
            shape=[len(complex.realization_matrix), len(complex.realization_matrix[0]) if complex.realization_matrix else 0],
            coefficient_ring=complex.coefficient_ring,
            metadata={"map_hash": complex.map_hash, "complex_hash": complex.complex_hash, "realization_kind": complex.realization_kind.value},
        )
    invariants = []
    values = (
        ("relation_realization_kind", complex.realization_kind.value, complex.evidence_status, "explicit realization kind; not inferred"),
        ("node_generator_rank", complex.node_module.rank, complex.node_module.evidence_status, "rank of verified C_node"),
        ("relation_map_shape", [complex.target_module.rank, complex.node_module.rank], complex.evidence_status, "shape [target_rank, node_rank] for rho:C_node->T"),
        ("relation_map_hash", complex.map_hash, complex.evidence_status, "hash of rho matrix with convention"),
        ("relation_complex_hash", complex.complex_hash, complex.evidence_status, "hash includes realization kind and modules"),
        ("relation_rank", complex.relation_rank, complex.evidence_status, "rank of ker(rho) in degree 1"),
        ("image_rank", complex.image_rank, complex.evidence_status, "rank of im(rho)"),
        ("relation_cokernel_dimension", complex.cokernel_dimension, complex.evidence_status, "dimension/rank of coker(rho)"),
        ("relation_snf", None if complex.smith_normal_form is None else list(complex.smith_normal_form), _status_for_optional(complex.smith_normal_form, complex.evidence_status), "Smith invariant factors for certified integral models only"),
        ("relation_torsion", None if complex.torsion_type is None else list(complex.torsion_type), _status_for_optional(complex.torsion_type, complex.evidence_status), "torsion factors for certified integral models only"),
        ("relation_saturation_index", complex.saturation_index, _status_for_optional(complex.saturation_index, complex.evidence_status), "image saturation index for certified integral models only"),
    )
    for name, value, status, notes in values:
        invariants.append(
            store.record_invariant(
                run_id=run_id,
                name=name,
                value=value,
                result_kind=ResultKind.NODE_RELATION,
                evidence_status=status,
                method=complex.method,
                provenance=complex.provenance,
                certificate_id=certificate.certificate_id,
                notes=f"{notes}; artifact_id={artifact.artifact_id}",
            )
        )
    return certificate, artifact, tuple(invariants)


def _integral_node_relation_complex(
    *,
    node_module: NodeGeneratorModule,
    target_module: TargetModule,
    realization_matrix: Any,
    realization_kind: RelationRealizationKind,
    certificate: dict[str, Any],
    provenance: str | None,
    evidence_status: EvidenceStatus,
    method: str,
) -> NodeRelationComplex:
    if _certificate_status(certificate) is not EvidenceStatus.VERIFIED or certificate.get("integral_model_certified") is not True:
        raise IntegralRelationModelUnavailableError("Integral node-relation complexes require a verified supplied integral model certificate.")
    linear_map = IntegerLinearMap(realization_matrix, semantic_role=MatrixSemanticRole.NODE_RELATION, provenance=provenance, evidence_status=evidence_status)
    if linear_map.shape != (target_module.rank, node_module.rank):
        raise NodeRelationError(f"Realization map shape must be {(target_module.rank, node_module.rank)}, got {linear_map.shape}.")
    rank = rational_rank(linear_map)
    kernel = integer_kernel(linear_map)
    snf = smith_normal_form_data(linear_map)
    image = image_lattice(linear_map)
    matrix_entries = tuple(tuple(str(value) for value in row) for row in linear_map.matrix)
    map_hash = stable_sha256({"coefficient_ring": "ZZ", "matrix": matrix_entries, "convention": "rho:C_node->T"})
    complex_hash = stable_sha256(
        {
            "map_hash": map_hash,
            "realization_kind": realization_kind.value,
            "node_module": node_module.to_dict(),
            "target_module": target_module.to_dict(),
        }
    )
    return NodeRelationComplex(
        node_module=node_module,
        target_module=target_module,
        realization_kind=realization_kind,
        coefficient_ring="ZZ",
        realization_matrix=matrix_entries,
        map_hash=map_hash,
        complex_hash=complex_hash,
        image_rank=rank.rank,
        relation_rank=kernel.rank,
        cokernel_dimension=snf.cokernel.free_rank,
        relation_basis=tuple(tuple(str(value) for value in row) for row in kernel.basis),
        method=method,
        evidence_status=EvidenceStatus(evidence_status),
        certificate=dict(certificate),
        provenance=provenance,
        smith_normal_form=snf.diagonal_invariant_factors,
        torsion_type=snf.cokernel.torsion_invariant_factors,
        saturation_index=image.saturation.index,
    )


def _certificate_status(certificate: dict[str, Any]) -> EvidenceStatus:
    value = certificate.get("evidence_status", certificate.get("status", EvidenceStatus.UNKNOWN.value))
    return EvidenceStatus(value)


def _coerce_exact_matrix(matrix: Any) -> sp.Matrix:
    result = sp.Matrix(matrix)
    for value in result:
        sympified = sp.sympify(value)
        if sympified.free_symbols:
            raise NodeRelationError(f"Matrix entry is symbolic, not an exact rational value: {value!r}")
        if sympified.has(sp.Float):
            raise NodeRelationError(f"Matrix entry is approximate, not exact: {value!r}")
        if sympified.is_Rational is not True:
            raise NodeRelationError(f"Matrix entry is not rational: {value!r}")
    return result


def _validate_shape(matrix: sp.Matrix, target_rank: int, node_rank: int) -> None:
    expected = (target_rank, node_rank)
    actual = (int(matrix.rows), int(matrix.cols))
    if actual != expected:
        raise NodeRelationError(f"Realization map shape must be {expected}, got {actual}.")


def _string_matrix(matrix_or_vectors: sp.Matrix | list[sp.Matrix]) -> tuple[tuple[str, ...], ...]:
    if isinstance(matrix_or_vectors, list):
        if not matrix_or_vectors:
            return ()
        matrix = sp.Matrix.hstack(*matrix_or_vectors)
    else:
        matrix = matrix_or_vectors
    return tuple(tuple(sp.sstr(matrix[row, col]) for col in range(matrix.cols)) for row in range(matrix.rows))


def _monomial_label(monomial: Sequence[int]) -> str:
    return "(" + ",".join(str(int(value)) for value in monomial) + ")"


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


def _status_for_optional(value: Any, status: EvidenceStatus) -> EvidenceStatus:
    return status if value is not None else EvidenceStatus.NOT_APPLICABLE
