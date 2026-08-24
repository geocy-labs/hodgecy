"""Certified source-to-node chain-map comparisons.

Blob 10 treats a source-to-node comparison as extra mathematical data: a
chain map between two two-term complexes.  Matching ranks, shared geometry, or
similar matrices never create such a map.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Iterable, Sequence

import sympy as sp

from hodgecy.algebra import IntegerLinearMap, MatrixSemanticRole, integer_kernel, rational_rank, smith_normal_form_data
from hodgecy.core.results import EvidenceStatus, ResultKind
from hodgecy.core.serialization import canonical_json, stable_sha256
from hodgecy.relations.node_relations import NodeRelationComplex, RelationRealizationKind
from hodgecy.storage import ArtifactRecord, CalculationRun, CertificateRecord, ResultStore


class ComparisonMorphismKind(str, Enum):
    THEOREM_BACKED = "theorem_backed"
    EXPLICIT_GENERATOR_MAP = "explicit_generator_map"
    IMPORTED_CERTIFIED = "imported_certified"
    USER_SUPPLIED = "user_supplied"
    UNKNOWN = "unknown"


class FeasibilityState(str, Enum):
    POSSIBLE = "possible"
    IMPOSSIBLE = "impossible"
    UNKNOWN = "unknown"


class SourceToNodeError(ValueError):
    """Base class for source-to-node comparison failures."""


class ChainMapVerificationError(SourceToNodeError):
    """Raised when ``d_node F1 = F0 d_src`` fails exactly."""


class ComparisonMorphismUnavailableError(SourceToNodeError):
    """Raised when a requested morphism would have to be inferred."""


@dataclass(frozen=True, slots=True)
class SourceTwoTermComplex:
    complex_id: str
    differential_matrix: tuple[tuple[str, ...], ...]
    coefficient_ring: str
    c1_basis: tuple[str, ...]
    c0_basis: tuple[str, ...]
    provenance: str | None = None
    evidence_status: EvidenceStatus = EvidenceStatus.VERIFIED

    @classmethod
    def from_matrix(
        cls,
        matrix: Any,
        *,
        complex_id: str,
        coefficient_ring: str = "QQ",
        c1_basis: Sequence[str] | None = None,
        c0_basis: Sequence[str] | None = None,
        provenance: str | None = None,
        evidence_status: EvidenceStatus = EvidenceStatus.VERIFIED,
    ) -> "SourceTwoTermComplex":
        ring = _normalize_ring(coefficient_ring)
        parsed = _coerce_matrix(matrix, ring)
        rows, cols = int(parsed.rows), int(parsed.cols)
        c1_labels = tuple(c1_basis) if c1_basis is not None else tuple(f"src_c1_{index}" for index in range(cols))
        c0_labels = tuple(c0_basis) if c0_basis is not None else tuple(f"src_c0_{index}" for index in range(rows))
        if len(c1_labels) != cols or len(c0_labels) != rows:
            raise SourceToNodeError("Source basis lengths must match the differential matrix shape.")
        return cls(
            complex_id=complex_id,
            differential_matrix=_string_matrix(parsed),
            coefficient_ring=ring,
            c1_basis=c1_labels,
            c0_basis=c0_labels,
            provenance=provenance,
            evidence_status=EvidenceStatus(evidence_status),
        )

    @property
    def matrix(self) -> sp.Matrix:
        return sp.Matrix([[sp.sympify(value) for value in row] for row in self.differential_matrix])

    @property
    def c1_rank(self) -> int:
        return len(self.c1_basis)

    @property
    def c0_rank(self) -> int:
        return len(self.c0_basis)

    @property
    def rank_q(self) -> int:
        return int(self.matrix.rank())

    @property
    def h1_rank_q(self) -> int:
        return self.c1_rank - self.rank_q

    @property
    def h0_rank_q(self) -> int:
        return self.c0_rank - self.rank_q

    @property
    def complex_hash(self) -> str:
        return stable_sha256(
            {
                "complex_id": self.complex_id,
                "coefficient_ring": self.coefficient_ring,
                "differential_matrix": self.differential_matrix,
                "homological_convention": "C1->C0",
            }
        )

    def h1_basis_matrix(self) -> sp.Matrix:
        if self.coefficient_ring == "ZZ":
            return sp.Matrix(integer_kernel(IntegerLinearMap(self.matrix, semantic_role=MatrixSemanticRole.SOURCE_ASSEMBLY)).basis)
        return _nullspace_matrix(self.matrix, self.c1_rank)

    def to_dict(self) -> dict[str, Any]:
        return {
            "complex_id": self.complex_id,
            "coefficient_ring": self.coefficient_ring,
            "homological_convention": {"degree_1": "C1_src", "degree_0": "C0_src", "H1": "ker(d_src)", "H0": "coker(d_src)"},
            "differential_matrix": [list(row) for row in self.differential_matrix],
            "matrix_shape": [self.c0_rank, self.c1_rank],
            "c1_basis": list(self.c1_basis),
            "c0_basis": list(self.c0_basis),
            "rank_Q": self.rank_q,
            "H1_rank_Q": self.h1_rank_q,
            "H0_rank_Q": self.h0_rank_q,
            "complex_hash": self.complex_hash,
            "evidence_status": self.evidence_status.value,
            "provenance": self.provenance,
        }


@dataclass(frozen=True, slots=True)
class SourceGeneratorAssignment:
    source_generator_id: str
    target_terms: tuple[tuple[str, str], ...]
    geometric_justification: str | None = None
    source_stratum: str | None = None
    theorem_or_algorithm: str | None = None
    certificate: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_terms(cls, source_generator_id: str, target_terms: Iterable[tuple[str, Any]], **metadata: Any) -> "SourceGeneratorAssignment":
        return cls(
            source_generator_id=str(source_generator_id),
            target_terms=tuple((str(target_id), sp.sstr(sp.sympify(coeff))) for target_id, coeff in target_terms),
            geometric_justification=metadata.get("geometric_justification"),
            source_stratum=metadata.get("source_stratum"),
            theorem_or_algorithm=metadata.get("theorem_or_algorithm"),
            certificate=dict(metadata.get("certificate") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_generator_id": self.source_generator_id,
            "target_terms": [list(item) for item in self.target_terms],
            "geometric_justification": self.geometric_justification,
            "source_stratum": self.source_stratum,
            "theorem_or_algorithm": self.theorem_or_algorithm,
            "certificate": self.certificate,
        }


@dataclass(frozen=True, slots=True)
class InducedHomologyMap:
    degree: int
    source_rank: int
    target_rank: int
    induced_matrix: tuple[tuple[str, ...], ...]
    induced_rank: int
    kernel_rank: int
    cokernel_rank: int
    killed_basis: tuple[tuple[str, ...], ...]
    image_basis: tuple[tuple[str, ...], ...]
    dependency_basis: tuple[tuple[str, ...], ...]
    coefficient_ring: str
    evidence_status: EvidenceStatus
    certificate: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "degree": self.degree,
            "source_rank": self.source_rank,
            "target_rank": self.target_rank,
            "induced_matrix": [list(row) for row in self.induced_matrix],
            "induced_rank": self.induced_rank,
            "kernel_rank": self.kernel_rank,
            "cokernel_rank": self.cokernel_rank,
            "killed_basis": [list(row) for row in self.killed_basis],
            "image_basis": [list(row) for row in self.image_basis],
            "dependency_basis": [list(row) for row in self.dependency_basis],
            "coefficient_ring": self.coefficient_ring,
            "evidence_status": self.evidence_status.value,
            "certificate": self.certificate,
        }


@dataclass(frozen=True, slots=True)
class SourceSurvivalProfile:
    source_h1_rank: int
    target_h1_rank: int
    induced_rank: int
    killed_rank: int
    surviving_rank: int
    target_unreached_rank: int
    injective: bool
    surjective: bool
    isomorphism: bool
    coefficient_ring: str
    target_relation_kind: RelationRealizationKind
    evidence_status: EvidenceStatus
    kernel_lattice: dict[str, Any] | None = None
    image_lattice: dict[str, Any] | None = None
    cokernel_structure: dict[str, Any] | None = None
    torsion: tuple[int, ...] | None = None
    saturation_index: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_h1_rank": self.source_h1_rank,
            "target_h1_rank": self.target_h1_rank,
            "induced_rank": self.induced_rank,
            "killed_rank": self.killed_rank,
            "surviving_rank": self.surviving_rank,
            "target_unreached_rank": self.target_unreached_rank,
            "injective": self.injective,
            "surjective": self.surjective,
            "isomorphism": self.isomorphism,
            "coefficient_ring": self.coefficient_ring,
            "target_relation_kind": self.target_relation_kind.value,
            "evidence_status": self.evidence_status.value,
            "kernel_lattice": self.kernel_lattice,
            "image_lattice": self.image_lattice,
            "cokernel_structure": self.cokernel_structure,
            "torsion": None if self.torsion is None else list(self.torsion),
            "saturation_index": self.saturation_index,
        }


@dataclass(frozen=True, slots=True)
class ComparisonFeasibilityResult:
    source_h1_rank: int | None
    target_h1_rank: int | None
    coefficient_ring: str
    injective: FeasibilityState
    surjective: FeasibilityState
    isomorphism: FeasibilityState
    evidence_status: EvidenceStatus
    reason: str
    conditional_statements: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_h1_rank": self.source_h1_rank,
            "target_h1_rank": self.target_h1_rank,
            "coefficient_ring": self.coefficient_ring,
            "injective": self.injective.value,
            "surjective": self.surjective.value,
            "isomorphism": self.isomorphism.value,
            "evidence_status": self.evidence_status.value,
            "reason": self.reason,
            "conditional_statements": list(self.conditional_statements),
            "firewall": source_to_node_firewall(),
        }


@dataclass(frozen=True, slots=True)
class SourceToNodeChainMap:
    source_complex: SourceTwoTermComplex
    node_complex: NodeRelationComplex
    degree_1_map: tuple[tuple[str, ...], ...]
    degree_0_map: tuple[tuple[str, ...], ...]
    coefficient_ring: str
    construction_kind: ComparisonMorphismKind
    evidence_status: EvidenceStatus
    certificate: dict[str, Any]
    provenance: str | None
    residual_matrix: tuple[tuple[str, ...], ...]
    F1_hash: str
    F0_hash: str
    chain_map_hash: str
    H1: InducedHomologyMap
    H0: InducedHomologyMap
    survival_profile: SourceSurvivalProfile

    @classmethod
    def from_matrices(
        cls,
        *,
        source_complex: SourceTwoTermComplex,
        node_complex: NodeRelationComplex,
        degree_1_map: Any,
        degree_0_map: Any,
        construction_kind: ComparisonMorphismKind | str,
        certificate: dict[str, Any],
        provenance: str | None = None,
        evidence_status: EvidenceStatus = EvidenceStatus.VERIFIED,
    ) -> "SourceToNodeChainMap":
        ring = _normalize_ring(source_complex.coefficient_ring)
        if _normalize_ring(node_complex.coefficient_ring) != ring:
            raise SourceToNodeError("Source and node complexes must have the same coefficient ring.")
        kind = ComparisonMorphismKind(construction_kind)
        if kind is ComparisonMorphismKind.UNKNOWN:
            raise ComparisonMorphismUnavailableError("UNKNOWN records absence of a source-to-node map; it cannot construct one.")
        d_src = source_complex.matrix
        d_node = _node_matrix(node_complex)
        f1 = _coerce_matrix(degree_1_map, ring)
        f0 = _coerce_matrix(degree_0_map, ring)
        _validate_shape(f1, node_complex.node_module.rank or 0, source_complex.c1_rank, "F1")
        _validate_shape(f0, node_complex.target_module.rank, source_complex.c0_rank, "F0")
        residual = d_node * f1 - f0 * d_src
        if residual != sp.zeros(residual.rows, residual.cols):
            raise ChainMapVerificationError(f"Source-to-node square does not commute exactly; residual={_string_matrix(residual)}")
        h1 = _induced_h1(source_complex, node_complex, f1, ring)
        h0 = _induced_h0(source_complex, node_complex, f0, ring)
        profile = _survival_profile(h1, node_complex.realization_kind, ring)
        f1_entries = _string_matrix(f1)
        f0_entries = _string_matrix(f0)
        f1_hash = stable_sha256({"coefficient_ring": ring, "matrix": f1_entries, "role": "F1"})
        f0_hash = stable_sha256({"coefficient_ring": ring, "matrix": f0_entries, "role": "F0"})
        chain_hash = stable_sha256(
            {
                "source_complex_hash": source_complex.complex_hash,
                "target_complex_hash": node_complex.complex_hash,
                "target_relation_kind": node_complex.realization_kind.value,
                "F1_hash": f1_hash,
                "F0_hash": f0_hash,
                "coefficient_ring": ring,
                "construction_kind": kind.value,
            }
        )
        full_certificate = {
            "certificate_type": "source_to_node_chain_map",
            "source_complex_hash": source_complex.complex_hash,
            "target_complex_hash": node_complex.complex_hash,
            "target_relation_kind": node_complex.realization_kind.value,
            "F1_hash": f1_hash,
            "F0_hash": f0_hash,
            "coefficient_ring": ring,
            "construction_kind": kind.value,
            "chain_map_verification": {"d_node_F1_equals_F0_d_src": True, "residual_matrix": _string_matrix(residual)},
            "basis_conventions": {"source_C1": list(source_complex.c1_basis), "source_C0": list(source_complex.c0_basis)},
            "source_to_node_firewall": source_to_node_firewall(),
            "supplied_certificate": dict(certificate),
        }
        return cls(
            source_complex=source_complex,
            node_complex=node_complex,
            degree_1_map=f1_entries,
            degree_0_map=f0_entries,
            coefficient_ring=ring,
            construction_kind=kind,
            evidence_status=EvidenceStatus(evidence_status),
            certificate=full_certificate,
            provenance=provenance,
            residual_matrix=_string_matrix(residual),
            F1_hash=f1_hash,
            F0_hash=f0_hash,
            chain_map_hash=chain_hash,
            H1=h1,
            H0=h0,
            survival_profile=profile,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_complex": self.source_complex.to_dict(),
            "node_complex": self.node_complex.to_dict(),
            "degree_1_map": [list(row) for row in self.degree_1_map],
            "degree_0_map": [list(row) for row in self.degree_0_map],
            "coefficient_ring": self.coefficient_ring,
            "construction_kind": self.construction_kind.value,
            "evidence_status": self.evidence_status.value,
            "certificate": self.certificate,
            "provenance": self.provenance,
            "residual_matrix": [list(row) for row in self.residual_matrix],
            "F1_hash": self.F1_hash,
            "F0_hash": self.F0_hash,
            "chain_map_hash": self.chain_map_hash,
            "H1": self.H1.to_dict(),
            "H0": self.H0.to_dict(),
            "survival_profile": self.survival_profile.to_dict(),
            "firewall": source_to_node_firewall(),
        }


def source_to_node_firewall() -> dict[str, bool]:
    return {
        "matching_dimensions_do_not_create_chain_map": True,
        "matching_ranks_do_not_create_chain_map": True,
        "matching_snf_does_not_create_chain_map": True,
        "shared_geometry_id_does_not_create_chain_map": True,
        "shared_node_count_does_not_create_chain_map": True,
        "evaluation_relation_is_not_vanishing_cycle_relation": True,
        "source_to_evaluation_is_not_source_to_vanishing": True,
        "rational_comparison_does_not_imply_integral_comparison": True,
        "nonzero_chain_image_does_not_imply_nonzero_homology_image": True,
        "equal_h1_dimensions_do_not_imply_h1_isomorphism": True,
        "feasibility_is_not_existence": True,
        "no_hodge_atom_constructed": True,
    }


def assignment_matrix(
    assignments: Sequence[SourceGeneratorAssignment],
    *,
    source_basis: Sequence[str],
    target_basis: Sequence[str],
    coefficient_ring: str = "QQ",
) -> tuple[tuple[str, ...], ...]:
    ring = _normalize_ring(coefficient_ring)
    source_index = {item: index for index, item in enumerate(source_basis)}
    target_index = {item: index for index, item in enumerate(target_basis)}
    matrix = sp.zeros(len(target_basis), len(source_basis))
    for assignment in assignments:
        if assignment.source_generator_id not in source_index:
            raise SourceToNodeError(f"Unknown source generator: {assignment.source_generator_id}")
        col = source_index[assignment.source_generator_id]
        for target_id, coeff in assignment.target_terms:
            if target_id not in target_index:
                raise SourceToNodeError(f"Unknown target generator: {target_id}")
            matrix[target_index[target_id], col] += sp.sympify(coeff)
    _coerce_matrix(matrix, ring)
    return _string_matrix(matrix)


def compare_chain_maps(left: SourceToNodeChainMap, right: SourceToNodeChainMap) -> dict[str, Any]:
    comparable = (
        left.source_complex.complex_hash == right.source_complex.complex_hash
        and left.node_complex.complex_hash == right.node_complex.complex_hash
        and left.coefficient_ring == right.coefficient_ring
    )
    equal = comparable and left.F1_hash == right.F1_hash and left.F0_hash == right.F0_hash
    return {
        "comparable": comparable,
        "equal": equal,
        "left_chain_map_hash": left.chain_map_hash,
        "right_chain_map_hash": right.chain_map_hash,
        "reason": "F1 and F0 hashes agree" if equal else "chain maps differ or are not comparable",
        "chain_homotopy_classification": "not_implemented_blob10_non_goal",
    }


def h1_rank_feasibility(
    *,
    source_h1_rank: int | None,
    target_h1_rank: int | None,
    coefficient_ring: str = "QQ",
) -> ComparisonFeasibilityResult:
    ring = _normalize_ring(coefficient_ring)
    if source_h1_rank is None or target_h1_rank is None:
        return ComparisonFeasibilityResult(
            source_h1_rank=source_h1_rank,
            target_h1_rank=target_h1_rank,
            coefficient_ring=ring,
            injective=FeasibilityState.UNKNOWN,
            surjective=FeasibilityState.UNKNOWN,
            isomorphism=FeasibilityState.UNKNOWN,
            evidence_status=EvidenceStatus.UNKNOWN,
            reason="H1 ranks are not both known; no morphism existence is asserted.",
        )
    injective = FeasibilityState.IMPOSSIBLE if source_h1_rank > target_h1_rank else FeasibilityState.POSSIBLE
    surjective = FeasibilityState.IMPOSSIBLE if source_h1_rank < target_h1_rank else FeasibilityState.POSSIBLE
    isomorphism = FeasibilityState.POSSIBLE if source_h1_rank == target_h1_rank else FeasibilityState.IMPOSSIBLE
    reason = "Necessary rank constraints only; feasibility is not existence."
    return ComparisonFeasibilityResult(
        source_h1_rank=source_h1_rank,
        target_h1_rank=target_h1_rank,
        coefficient_ring=ring,
        injective=injective,
        surjective=surjective,
        isomorphism=isomorphism,
        evidence_status=EvidenceStatus.COMPUTED,
        reason=reason,
    )


def conditional_defect_feasibility_for_source_h1(source_h1_rank: int) -> tuple[dict[str, Any], ...]:
    return (
        {
            "condition": "defect = 0",
            "target_h1_rank": 0,
            "implication": "any induced H1 map is zero",
            "injective": source_h1_rank == 0,
            "existence_statement": False,
        },
        {
            "condition": "defect = 1",
            "target_h1_rank": 1,
            "implication": "injective H1 comparison is impossible" if source_h1_rank > 1 else "injectivity is dimensionally possible",
            "injective": source_h1_rank <= 1,
            "existence_statement": False,
        },
        {
            "condition": f"defect >= {source_h1_rank}",
            "target_h1_rank": f">={source_h1_rank}",
            "implication": "injectivity is dimensionally possible but not established",
            "injective": "possible",
            "existence_statement": False,
        },
    )


def begin_source_to_node_run(store: ResultStore, geometry_id: str, *, input_metadata: Any, parameters: Any | None = None, notes: str | None = None) -> CalculationRun:
    return store.begin_run(
        geometry_id=geometry_id,
        calculation_type="source_to_node_blob10",
        input_metadata=input_metadata,
        parameters=parameters,
        backend="hodgecy.relations.source_to_node",
        coefficient_ring="QQ/ZZ",
        notes=notes,
    )


def persist_source_to_node_chain_map(
    store: ResultStore,
    *,
    run_id: str,
    chain_map: SourceToNodeChainMap,
) -> tuple[CertificateRecord, ArtifactRecord, tuple[Any, ...]]:
    run = store.get_run(run_id)
    payload = chain_map.to_dict()
    certificate = store.record_certificate(
        certificate_type="source_to_node_chain_map",
        subject_type="geometry",
        subject_id=run.geometry_id,
        method="hodgecy.relations.source_to_node",
        evidence=payload,
        generated_by_run_id=run_id,
        notes="Blob 10 certified source-to-node chain map; not a generic value comparison.",
    )
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "source_to_node_chain_map.json"
        path.write_text(canonical_json(payload) + "\n", encoding="utf-8")
        artifact = store.attach_artifact(
            run_id=run_id,
            role="source_to_node_chain_map",
            artifact_type="json",
            source_path=path,
            storage_format="json",
            coefficient_ring=chain_map.coefficient_ring,
            metadata={"chain_map_hash": chain_map.chain_map_hash, "target_relation_kind": chain_map.node_complex.realization_kind.value},
        )
    invariants = []
    values = (
        ("comparison_morphism_id", chain_map.chain_map_hash, chain_map.evidence_status, "stable hash for the supplied chain map"),
        ("source_complex_hash", chain_map.source_complex.complex_hash, chain_map.source_complex.evidence_status, "source two-term complex hash"),
        ("target_complex_hash", chain_map.node_complex.complex_hash, chain_map.node_complex.evidence_status, "target node-relation complex hash"),
        ("target_relation_kind", chain_map.node_complex.realization_kind.value, chain_map.node_complex.evidence_status, "preserved Blob 9 node-relation kind"),
        ("coefficient_ring", chain_map.coefficient_ring, chain_map.evidence_status, "coefficient ring for this comparison only"),
        ("F1_hash", chain_map.F1_hash, chain_map.evidence_status, "degree-1 chain-map matrix hash"),
        ("F0_hash", chain_map.F0_hash, chain_map.evidence_status, "degree-0 chain-map matrix hash"),
        ("chain_map_verified", True, chain_map.evidence_status, "exact d_node*F1 = F0*d_src verification"),
        ("H1_induced_rank", chain_map.H1.induced_rank, chain_map.H1.evidence_status, "rank of induced H1 map"),
        ("H1_kernel", chain_map.H1.killed_basis, chain_map.H1.evidence_status, "basis-dependent presentation of ker H1(F)"),
        ("H1_image", chain_map.H1.image_basis, chain_map.H1.evidence_status, "basis-dependent presentation of im H1(F)"),
        ("H1_cokernel", chain_map.H1.cokernel_rank, chain_map.H1.evidence_status, "target H1 rank minus induced rank"),
        ("source_h1_rank", chain_map.survival_profile.source_h1_rank, chain_map.evidence_status, "source H1 rank"),
        ("surviving_rank", chain_map.survival_profile.surviving_rank, chain_map.evidence_status, "rank of source classes surviving in target H1"),
        ("killed_rank", chain_map.survival_profile.killed_rank, chain_map.evidence_status, "rank of source H1 classes killed"),
    )
    for name, value, status, notes in values:
        invariants.append(
            store.record_invariant(
                run_id=run_id,
                name=name,
                value=value,
                result_kind=ResultKind.NODE_RELATION,
                evidence_status=status,
                method="hodgecy.relations.source_to_node",
                provenance=chain_map.provenance,
                certificate_id=certificate.certificate_id,
                notes=f"{notes}; artifact_id={artifact.artifact_id}",
            )
        )
    return certificate, artifact, tuple(invariants)


def _induced_h1(source: SourceTwoTermComplex, node: NodeRelationComplex, f1: sp.Matrix, ring: str) -> InducedHomologyMap:
    source_kernel = source.h1_basis_matrix()
    node_kernel = _node_h1_basis_matrix(node)
    images = f1 * source_kernel
    residual = _node_matrix(node) * images
    if residual != sp.zeros(residual.rows, residual.cols):
        raise ChainMapVerificationError("F1(ker d_src) is not contained in ker d_node.")
    source_rank = int(source_kernel.cols)
    target_rank = int(node_kernel.cols)
    induced_rank = int(images.rank())
    dependency = _nullspace_matrix(images, source_rank)
    image_basis = _columnspace_matrix(images, images.rows)
    certificate = {"F1_ker_source_subset_ker_node": True, "basis_dependent_presentations": True}
    if ring == "ZZ":
        image_map = IntegerLinearMap(images, semantic_role=MatrixSemanticRole.NODE_RELATION)
        snf = smith_normal_form_data(image_map)
        certificate["integral_image_cokernel"] = snf.cokernel.to_dict()
    return InducedHomologyMap(
        degree=1,
        source_rank=source_rank,
        target_rank=target_rank,
        induced_matrix=_string_matrix(images),
        induced_rank=induced_rank,
        kernel_rank=source_rank - induced_rank,
        cokernel_rank=target_rank - induced_rank,
        killed_basis=_string_matrix(source_kernel * dependency) if dependency.cols else (),
        image_basis=_string_matrix(image_basis),
        dependency_basis=_string_matrix(dependency),
        coefficient_ring=ring,
        evidence_status=EvidenceStatus.VERIFIED,
        certificate=certificate,
    )


def _induced_h0(source: SourceTwoTermComplex, node: NodeRelationComplex, f0: sp.Matrix, ring: str) -> InducedHomologyMap:
    d_src = source.matrix
    d_node = _node_matrix(node)
    source_rank = source.c0_rank - int(d_src.rank())
    target_rank = node.target_module.rank - int(d_node.rank())
    if source_rank < 0 or target_rank < 0:
        raise SourceToNodeError("Invalid H0 ranks from two-term complexes.")
    joined = d_node.row_join(f0)
    induced_rank = int(joined.rank()) - int(d_node.rank())
    kernel_rank = source_rank - induced_rank
    cokernel_rank = target_rank - induced_rank
    certificate = {
        "rank_formula": "rank([d_node,F0])-rank(d_node)",
        "quotient_convention": "H0=coker(d)",
        "basis_level_quotient_map": "not canonical without quotient basis",
    }
    if ring == "ZZ":
        certificate["source_cokernel_structure"] = smith_normal_form_data(IntegerLinearMap(d_src, semantic_role=MatrixSemanticRole.SOURCE_ASSEMBLY)).cokernel.to_dict()
        certificate["target_cokernel_structure"] = smith_normal_form_data(IntegerLinearMap(d_node, semantic_role=MatrixSemanticRole.NODE_RELATION)).cokernel.to_dict()
    return InducedHomologyMap(
        degree=0,
        source_rank=source_rank,
        target_rank=target_rank,
        induced_matrix=(),
        induced_rank=induced_rank,
        kernel_rank=kernel_rank,
        cokernel_rank=cokernel_rank,
        killed_basis=(),
        image_basis=(),
        dependency_basis=(),
        coefficient_ring=ring,
        evidence_status=EvidenceStatus.VERIFIED,
        certificate=certificate,
    )


def _survival_profile(h1: InducedHomologyMap, target_relation_kind: RelationRealizationKind, ring: str) -> SourceSurvivalProfile:
    injective = h1.kernel_rank == 0
    surjective = h1.cokernel_rank == 0
    cokernel = h1.certificate.get("integral_image_cokernel") if ring == "ZZ" else None
    torsion = tuple(cokernel.get("torsion_invariant_factors", ())) if isinstance(cokernel, dict) else None
    return SourceSurvivalProfile(
        source_h1_rank=h1.source_rank,
        target_h1_rank=h1.target_rank,
        induced_rank=h1.induced_rank,
        killed_rank=h1.kernel_rank,
        surviving_rank=h1.induced_rank,
        target_unreached_rank=h1.cokernel_rank,
        injective=injective,
        surjective=surjective,
        isomorphism=injective and surjective,
        coefficient_ring=ring,
        target_relation_kind=target_relation_kind,
        evidence_status=h1.evidence_status,
        cokernel_structure=cokernel if isinstance(cokernel, dict) else None,
        torsion=torsion,
    )


def _node_matrix(node: NodeRelationComplex) -> sp.Matrix:
    return sp.Matrix([[sp.sympify(value) for value in row] for row in node.realization_matrix])


def _node_h1_basis_matrix(node: NodeRelationComplex) -> sp.Matrix:
    if node.coefficient_ring == "ZZ":
        return sp.Matrix(integer_kernel(IntegerLinearMap(_node_matrix(node), semantic_role=MatrixSemanticRole.NODE_RELATION)).basis)
    return _nullspace_matrix(_node_matrix(node), node.node_module.rank or 0)


def _normalize_ring(ring: str) -> str:
    if ring in {"Q", "QQ"}:
        return "QQ"
    if ring in {"Z", "ZZ"}:
        return "ZZ"
    raise SourceToNodeError(f"Unsupported coefficient ring: {ring}")


def _coerce_matrix(matrix: Any, ring: str) -> sp.Matrix:
    result = sp.Matrix(matrix)
    for value in result:
        sympified = sp.sympify(value)
        if sympified.free_symbols or sympified.has(sp.Float):
            raise SourceToNodeError(f"Matrix entry is not exact: {value!r}")
        if ring == "QQ" and sympified.is_Rational is not True:
            raise SourceToNodeError(f"Matrix entry is not rational: {value!r}")
        if ring == "ZZ" and sympified.is_Integer is not True:
            raise SourceToNodeError(f"Matrix entry is not integral: {value!r}")
    return result


def _validate_shape(matrix: sp.Matrix, rows: int, cols: int, label: str) -> None:
    if (int(matrix.rows), int(matrix.cols)) != (rows, cols):
        raise SourceToNodeError(f"{label} shape must be {(rows, cols)}, got {(int(matrix.rows), int(matrix.cols))}.")


def _string_matrix(matrix: sp.Matrix) -> tuple[tuple[str, ...], ...]:
    return tuple(tuple(sp.sstr(matrix[row, col]) for col in range(matrix.cols)) for row in range(matrix.rows))


def _nullspace_matrix(matrix: sp.Matrix, ambient_rank: int) -> sp.Matrix:
    vectors = matrix.nullspace()
    return sp.zeros(ambient_rank, 0) if not vectors else sp.Matrix.hstack(*vectors)


def _columnspace_matrix(matrix: sp.Matrix, ambient_rank: int) -> sp.Matrix:
    vectors = matrix.columnspace()
    return sp.zeros(ambient_rank, 0) if not vectors else sp.Matrix.hstack(*vectors)
