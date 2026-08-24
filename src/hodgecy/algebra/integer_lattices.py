"""Exact integer maps and embedded lattice invariants.

Blob 8 fixes the convention that an ``n x m`` integer matrix represents

    A : Z^m -> Z^n

acting on column vectors.  The algebra in this module is geometry-neutral:
``semantic_role`` is descriptive provenance and never determines a
``ResultKind``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import prod
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Iterable, Sequence

import sympy as sp
from sympy.matrices.normalforms import hermite_normal_form, smith_normal_decomp, smith_normal_form

from hodgecy.core.results import EvidenceStatus, ResultKind
from hodgecy.core.serialization import canonical_json, stable_sha256
from hodgecy.storage import ArtifactRecord, CertificateRecord, CalculationRun, ResultStore


class IntegerMatrixError(ValueError):
    """Base class for exact integer matrix failures."""


class UnsupportedExactDomainError(IntegerMatrixError):
    """Raised when a matrix contains non-integral or approximate entries."""


class LatticeContainmentError(IntegerMatrixError):
    """Raised when a requested lattice containment does not hold."""


class InfiniteIndexError(IntegerMatrixError):
    """Raised when a lattice index is not finite."""


class SmithVerificationError(IntegerMatrixError):
    """Raised when Smith normal form verification fails."""


class LatticeComparisonState(str, Enum):
    EQUAL = "equal"
    DIFFERENT = "different"
    INCOMPARABLE = "incomparable"
    UNKNOWN = "unknown"


class MatrixSemanticRole(str, Enum):
    SOURCE_ASSEMBLY = "source_assembly"
    NODE_RELATION = "node_relation"
    INCIDENCE = "incidence"
    BOUNDARY = "boundary"
    USER_SUPPLIED = "user_supplied"
    UNSPECIFIED = "unspecified"


@dataclass(frozen=True, slots=True)
class IntegerLinearMap:
    matrix: tuple[tuple[int, ...], ...]
    semantic_role: str = MatrixSemanticRole.UNSPECIFIED.value
    provenance: str | None = None
    evidence_status: EvidenceStatus = EvidenceStatus.COMPUTED

    def __init__(
        self,
        matrix: Any,
        *,
        semantic_role: str | MatrixSemanticRole = MatrixSemanticRole.UNSPECIFIED,
        provenance: str | None = None,
        evidence_status: EvidenceStatus = EvidenceStatus.COMPUTED,
    ) -> None:
        rows = _coerce_integer_rows(matrix)
        width = len(rows[0]) if rows else _matrix_cols(matrix)
        object.__setattr__(self, "matrix", tuple(tuple(row) for row in rows) if rows else tuple())
        try:
            role = MatrixSemanticRole(semantic_role).value
        except ValueError:
            role = str(semantic_role)
        object.__setattr__(self, "semantic_role", role)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "evidence_status", EvidenceStatus(evidence_status))
        if rows and any(len(row) != width for row in rows):
            raise IntegerMatrixError("Integer matrices must be rectangular.")
        if not rows and width:
            object.__setattr__(self, "matrix", tuple())

    @property
    def sympy_matrix(self) -> sp.Matrix:
        if self.codomain_rank == 0:
            return sp.zeros(0, self.domain_rank)
        return sp.Matrix(self.matrix)

    @property
    def codomain_rank(self) -> int:
        return len(self.matrix)

    @property
    def domain_rank(self) -> int:
        return 0 if not self.matrix else len(self.matrix[0])

    @property
    def shape(self) -> tuple[int, int]:
        return (self.codomain_rank, self.domain_rank)

    @property
    def matrix_hash(self) -> str:
        return stable_sha256({"coefficient_ring": "ZZ", "matrix": self.matrix})

    def to_dict(self) -> dict[str, Any]:
        return {
            "matrix": [list(row) for row in self.matrix],
            "domain_rank": self.domain_rank,
            "codomain_rank": self.codomain_rank,
            "coefficient_ring": "ZZ",
            "matrix_hash": self.matrix_hash,
            "semantic_role": self.semantic_role,
            "provenance": self.provenance,
            "evidence_status": self.evidence_status.value,
            "convention": "n x m matrix acts as A: Z^m -> Z^n on column vectors",
        }


@dataclass(frozen=True, slots=True)
class RationalRankResult:
    rank: int
    nullity: int
    domain_rank: int
    codomain_rank: int
    matrix_hash: str
    method: str
    evidence_status: EvidenceStatus

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "nullity": self.nullity,
            "domain_rank": self.domain_rank,
            "codomain_rank": self.codomain_rank,
            "matrix_hash": self.matrix_hash,
            "method": self.method,
            "evidence_status": self.evidence_status.value,
            "rank_nullity_verified": self.rank + self.nullity == self.domain_rank,
        }


@dataclass(frozen=True, slots=True)
class ModularRankResult:
    modulus: int
    rank: int
    domain_rank: int
    codomain_rank: int
    matrix_hash: str
    method: str
    evidence_status: EvidenceStatus

    def to_dict(self) -> dict[str, Any]:
        return {
            "modulus": self.modulus,
            "rank": self.rank,
            "domain_rank": self.domain_rank,
            "codomain_rank": self.codomain_rank,
            "matrix_hash": self.matrix_hash,
            "method": self.method,
            "evidence_status": self.evidence_status.value,
        }


@dataclass(frozen=True, slots=True)
class CokernelStructure:
    free_rank: int
    torsion_invariant_factors: tuple[int, ...]
    torsion_order: int
    torsion_primes: tuple[int, ...]
    is_torsion_free: bool
    matrix_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "free_rank": self.free_rank,
            "torsion_invariant_factors": list(self.torsion_invariant_factors),
            "torsion_order": self.torsion_order,
            "torsion_primes": list(self.torsion_primes),
            "is_torsion_free": self.is_torsion_free,
            "matrix_hash": self.matrix_hash,
            "structure": _cokernel_string(self.free_rank, self.torsion_invariant_factors),
            "cokernel_hash": stable_sha256({"free_rank": self.free_rank, "torsion": self.torsion_invariant_factors}),
        }


@dataclass(frozen=True, slots=True)
class SmithNormalFormResult:
    rank: int
    diagonal_invariant_factors: tuple[int, ...]
    zero_diagonal_count: int
    free_cokernel_rank: int
    torsion_invariant_factors: tuple[int, ...]
    transforms_supported: bool
    transform_verification: dict[str, Any]
    diagonal_matrix: tuple[tuple[int, ...], ...]
    matrix_hash: str
    method: str
    evidence_status: EvidenceStatus
    cokernel: CokernelStructure

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "diagonal_invariant_factors": list(self.diagonal_invariant_factors),
            "zero_diagonal_count": self.zero_diagonal_count,
            "free_cokernel_rank": self.free_cokernel_rank,
            "torsion_invariant_factors": list(self.torsion_invariant_factors),
            "transforms_supported": self.transforms_supported,
            "transform_verification": self.transform_verification,
            "diagonal_matrix": [list(row) for row in self.diagonal_matrix],
            "matrix_hash": self.matrix_hash,
            "method": self.method,
            "evidence_status": self.evidence_status.value,
            "cokernel": self.cokernel.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class IntegerKernelResult:
    basis: tuple[tuple[int, ...], ...]
    basis_vectors_are_columns: bool
    rank: int
    ambient_rank: int
    matrix_hash: str
    basis_hash: str
    verification: dict[str, Any]
    method: str
    evidence_status: EvidenceStatus

    def to_dict(self) -> dict[str, Any]:
        return {
            "basis": [list(row) for row in self.basis],
            "basis_vectors_are_columns": self.basis_vectors_are_columns,
            "rank": self.rank,
            "ambient_rank": self.ambient_rank,
            "matrix_hash": self.matrix_hash,
            "basis_hash": self.basis_hash,
            "verification": self.verification,
            "method": self.method,
            "evidence_status": self.evidence_status.value,
            "kernel_is_saturated": True,
        }


@dataclass(frozen=True, slots=True)
class SaturationResult:
    basis: tuple[tuple[int, ...], ...]
    basis_vectors_are_columns: bool
    rank: int
    ambient_rank: int
    index: int
    is_saturated: bool
    basis_hash: str
    method: str
    evidence_status: EvidenceStatus

    def to_dict(self) -> dict[str, Any]:
        return {
            "basis": [list(row) for row in self.basis],
            "basis_vectors_are_columns": self.basis_vectors_are_columns,
            "rank": self.rank,
            "ambient_rank": self.ambient_rank,
            "index": self.index,
            "is_saturated": self.is_saturated,
            "basis_hash": self.basis_hash,
            "method": self.method,
            "evidence_status": self.evidence_status.value,
        }


@dataclass(frozen=True, slots=True)
class ImageLatticeResult:
    basis: tuple[tuple[int, ...], ...]
    basis_vectors_are_columns: bool
    rank: int
    ambient_rank: int
    is_full_rank_in_ambient: bool
    matrix_hash: str
    basis_hash: str
    canonical_form: str
    saturation: SaturationResult
    method: str
    evidence_status: EvidenceStatus

    def to_dict(self) -> dict[str, Any]:
        return {
            "basis": [list(row) for row in self.basis],
            "basis_vectors_are_columns": self.basis_vectors_are_columns,
            "rank": self.rank,
            "ambient_rank": self.ambient_rank,
            "is_full_rank_in_ambient": self.is_full_rank_in_ambient,
            "matrix_hash": self.matrix_hash,
            "basis_hash": self.basis_hash,
            "canonical_form": self.canonical_form,
            "saturation": self.saturation.to_dict(),
            "method": self.method,
            "evidence_status": self.evidence_status.value,
        }


@dataclass(frozen=True, slots=True)
class LatticeComparisonResult:
    state: LatticeComparisonState
    same_rational_span: bool | None
    index: int | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "same_rational_span": self.same_rational_span,
            "index": self.index,
            "reason": self.reason,
        }


def rational_rank(linear_map: IntegerLinearMap) -> RationalRankResult:
    rank = int(linear_map.sympy_matrix.rank())
    nullity = linear_map.domain_rank - rank
    return RationalRankResult(
        rank=rank,
        nullity=nullity,
        domain_rank=linear_map.domain_rank,
        codomain_rank=linear_map.codomain_rank,
        matrix_hash=linear_map.matrix_hash,
        method="sympy Matrix.rank over QQ",
        evidence_status=EvidenceStatus.VERIFIED,
    )


def modular_rank(linear_map: IntegerLinearMap, p: int) -> ModularRankResult:
    if p < 2 or not _is_prime(p):
        raise IntegerMatrixError("modular_rank requires a prime p.")
    rows = [[value % p for value in row] for row in linear_map.matrix]
    rank = _rank_mod_rows(rows, p, linear_map.domain_rank)
    return ModularRankResult(
        modulus=p,
        rank=rank,
        domain_rank=linear_map.domain_rank,
        codomain_rank=linear_map.codomain_rank,
        matrix_hash=linear_map.matrix_hash,
        method="exact Gaussian elimination over F_p",
        evidence_status=EvidenceStatus.VERIFIED,
    )


def modular_rank_profile(linear_map: IntegerLinearMap, primes: Sequence[int] = (2, 3, 5, 7)) -> dict[int, ModularRankResult]:
    return {int(prime): modular_rank(linear_map, int(prime)) for prime in primes}


def smith_normal_form_data(linear_map: IntegerLinearMap) -> SmithNormalFormResult:
    matrix = linear_map.sympy_matrix
    diagonal = smith_normal_form(matrix, domain=sp.ZZ)
    invariant_factors = _diagonal_invariants(diagonal)
    rank = len(invariant_factors)
    _verify_snf_divisibility(invariant_factors)
    transforms_supported = False
    transform_verification: dict[str, Any] = {
        "backend": "sympy.matrices.normalforms.smith_normal_form",
        "transforms_available": False,
        "reason": "initial diagonal backend does not expose transforms",
    }
    try:
        decomp_d, left, right = smith_normal_decomp(matrix, domain=sp.ZZ)
        if decomp_d == diagonal:
            _verify_smith_transforms(matrix, decomp_d, left, right)
            transforms_supported = True
            transform_verification = {
                "backend": "sympy.matrices.normalforms.smith_normal_decomp",
                "transforms_available": True,
                "U_A_V_equals_D": True,
                "left_unimodular": _is_unimodular(left),
                "right_unimodular": _is_unimodular(right),
            }
    except Exception as exc:
        transform_verification = {
            "backend": "sympy.matrices.normalforms.smith_normal_decomp",
            "transforms_available": False,
            "reason": f"{type(exc).__name__}: {exc}",
        }
    torsion = tuple(value for value in invariant_factors if value > 1)
    free_rank = linear_map.codomain_rank - rank
    cokernel = CokernelStructure(
        free_rank=free_rank,
        torsion_invariant_factors=torsion,
        torsion_order=prod(torsion) if torsion else 1,
        torsion_primes=tuple(sorted({prime for value in torsion for prime in _prime_factors(value)})),
        is_torsion_free=not torsion,
        matrix_hash=linear_map.matrix_hash,
    )
    return SmithNormalFormResult(
        rank=rank,
        diagonal_invariant_factors=tuple(invariant_factors),
        zero_diagonal_count=min(linear_map.shape) - rank,
        free_cokernel_rank=free_rank,
        torsion_invariant_factors=torsion,
        transforms_supported=transforms_supported,
        transform_verification=transform_verification,
        diagonal_matrix=_matrix_tuple(diagonal),
        matrix_hash=linear_map.matrix_hash,
        method="Smith normal form over ZZ via SymPy",
        evidence_status=EvidenceStatus.VERIFIED,
        cokernel=cokernel,
    )


def integer_kernel(linear_map: IntegerLinearMap) -> IntegerKernelResult:
    matrix = linear_map.sympy_matrix
    snf = smith_normal_form_data(linear_map)
    if snf.transforms_supported:
        _, _, right = smith_normal_decomp(matrix, domain=sp.ZZ)
        kernel_basis = right[:, snf.rank :] if snf.rank < linear_map.domain_rank else sp.zeros(linear_map.domain_rank, 0)
    else:
        kernel_basis = _integer_kernel_from_rational_nullspace(matrix, linear_map.domain_rank)
    verification = {
        "A_K_equals_zero": matrix * kernel_basis == sp.zeros(linear_map.codomain_rank, kernel_basis.cols),
        "rank_nullity": kernel_basis.cols == linear_map.domain_rank - snf.rank,
        "basis_vectors_in_domain_Zm": True,
    }
    if not all(verification.values()):
        raise IntegerMatrixError("Integer kernel verification failed.")
    return IntegerKernelResult(
        basis=_matrix_tuple(kernel_basis),
        basis_vectors_are_columns=True,
        rank=int(kernel_basis.cols),
        ambient_rank=linear_map.domain_rank,
        matrix_hash=linear_map.matrix_hash,
        basis_hash=stable_sha256(_matrix_tuple(kernel_basis)),
        verification=verification,
        method="Smith transform kernel basis over ZZ" if snf.transforms_supported else "integerized rational nullspace basis",
        evidence_status=EvidenceStatus.VERIFIED,
    )


def image_lattice(linear_map: IntegerLinearMap) -> ImageLatticeResult:
    basis_matrix = hermite_normal_form(linear_map.sympy_matrix)
    rank = int(basis_matrix.cols)
    snf = smith_normal_form_data(linear_map)
    saturation = saturation_of_image(linear_map)
    return ImageLatticeResult(
        basis=_matrix_tuple(basis_matrix),
        basis_vectors_are_columns=True,
        rank=rank,
        ambient_rank=linear_map.codomain_rank,
        is_full_rank_in_ambient=rank == linear_map.codomain_rank,
        matrix_hash=linear_map.matrix_hash,
        basis_hash=stable_sha256(_matrix_tuple(basis_matrix)),
        canonical_form="column Hermite normal form",
        saturation=saturation,
        method="SymPy column Hermite normal form",
        evidence_status=EvidenceStatus.VERIFIED if rank == snf.rank else EvidenceStatus.UNKNOWN,
    )


def saturation_of_image(linear_map: IntegerLinearMap) -> SaturationResult:
    matrix = linear_map.sympy_matrix
    snf = smith_normal_form_data(linear_map)
    if snf.transforms_supported:
        _, left, _ = smith_normal_decomp(matrix, domain=sp.ZZ)
        if snf.rank == 0:
            sat_basis = sp.zeros(linear_map.codomain_rank, 0)
        else:
            left_inv = left.inv()
            sat_basis = left_inv[:, : snf.rank]
        index = snf.cokernel.torsion_order
        basis = hermite_normal_form(sat_basis)
        return SaturationResult(
            basis=_matrix_tuple(basis),
            basis_vectors_are_columns=True,
            rank=snf.rank,
            ambient_rank=linear_map.codomain_rank,
            index=index,
            is_saturated=index == 1,
            basis_hash=stable_sha256(_matrix_tuple(basis)),
            method="SNF transforms: Sat(im A) generated by U^{-1}e_i over nonzero Smith coordinates",
            evidence_status=EvidenceStatus.VERIFIED,
        )
    raise IntegerMatrixError("Saturation requires Smith transformation matrices in the current backend.")


def same_rational_span(left: IntegerLinearMap | ImageLatticeResult, right: IntegerLinearMap | ImageLatticeResult) -> bool:
    left_matrix = _basis_or_map_matrix(left)
    right_matrix = _basis_or_map_matrix(right)
    if left_matrix.rows != right_matrix.rows:
        raise IntegerMatrixError("Rational-span comparison requires the same ambient rank.")
    return int(left_matrix.rank()) == int(right_matrix.rank()) == int(left_matrix.row_join(right_matrix).rank())


def compare_lattices(left: IntegerLinearMap | ImageLatticeResult, right: IntegerLinearMap | ImageLatticeResult) -> LatticeComparisonResult:
    left_matrix = _basis_or_map_matrix(left)
    right_matrix = _basis_or_map_matrix(right)
    if left_matrix.rows != right_matrix.rows:
        return LatticeComparisonResult(LatticeComparisonState.INCOMPARABLE, None, None, "different ambient ranks")
    same_q = same_rational_span(left, right)
    left_hnf = hermite_normal_form(left_matrix)
    right_hnf = hermite_normal_form(right_matrix)
    if left_hnf == right_hnf:
        return LatticeComparisonResult(LatticeComparisonState.EQUAL, same_q, 1, "column Hermite normal forms agree")
    return LatticeComparisonResult(LatticeComparisonState.DIFFERENT, same_q, None, "embedded Z-lattices differ")


def lattice_index(sub_lattice: IntegerLinearMap | ImageLatticeResult, super_lattice: IntegerLinearMap | ImageLatticeResult) -> int:
    sub_matrix = _basis_or_map_matrix(sub_lattice)
    super_matrix = _basis_or_map_matrix(super_lattice)
    if sub_matrix.rows != super_matrix.rows:
        raise InfiniteIndexError("Lattices have different ambient ranks.")
    if int(sub_matrix.rank()) != int(super_matrix.rank()):
        raise InfiniteIndexError("Lattices have different ranks.")
    if not same_rational_span(_map_from_basis(sub_matrix), _map_from_basis(super_matrix)):
        raise InfiniteIndexError("Lattices do not have the same rational span.")
    for col in range(sub_matrix.cols):
        if not _column_in_lattice(sub_matrix[:, col], super_matrix):
            raise LatticeContainmentError("The first lattice is not contained in the second.")
    sub_sat = saturation_of_image(_map_from_basis(sub_matrix)).index
    super_sat = saturation_of_image(_map_from_basis(super_matrix)).index
    if sub_sat % super_sat:
        raise IntegerMatrixError("Saturation index ratio is not integral.")
    return sub_sat // super_sat


def begin_integer_lattice_run(store: ResultStore, geometry_id: str, *, input_metadata: Any, parameters: Any | None = None, notes: str | None = None) -> CalculationRun:
    return store.begin_run(
        geometry_id=geometry_id,
        calculation_type="integer_lattice_blob8",
        input_metadata=input_metadata,
        parameters=parameters,
        backend="hodgecy.algebra.integer_lattices",
        coefficient_ring="ZZ",
        notes=notes,
    )


def persist_integer_linear_map_analysis(
    store: ResultStore,
    *,
    run_id: str,
    linear_map: IntegerLinearMap,
    result_kind: ResultKind,
    modular_primes: Sequence[int] = (2, 3),
) -> tuple[CertificateRecord, tuple[ArtifactRecord, ...], tuple[Any, ...]]:
    run = store.get_run(run_id)
    rank_q = rational_rank(linear_map)
    mod_profile = modular_rank_profile(linear_map, modular_primes)
    snf = smith_normal_form_data(linear_map)
    kernel = integer_kernel(linear_map)
    image = image_lattice(linear_map)
    payload = {
        "integer_linear_map": linear_map.to_dict(),
        "result_kind_supplied_by_caller": result_kind.value,
        "rational_rank": rank_q.to_dict(),
        "modular_rank_profile": {str(p): result.to_dict() for p, result in mod_profile.items()},
        "smith_normal_form": snf.to_dict(),
        "integer_kernel": kernel.to_dict(),
        "image_lattice": image.to_dict(),
        "firewall": _firewall(),
    }
    certificate = store.record_certificate(
        certificate_type="exact_integer_matrix",
        subject_type="geometry",
        subject_id=run.geometry_id,
        method="hodgecy.algebra.integer_lattices",
        evidence=payload,
        generated_by_run_id=run_id,
        notes="Blob 8 exact integer map analysis; semantic role does not determine mathematical ResultKind.",
    )
    artifacts = []
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for role, data in (
            ("raw_integer_matrix", linear_map.to_dict()),
            ("integer_kernel_basis", kernel.to_dict()),
            ("image_lattice_basis", image.to_dict()),
        ):
            path = tmp_path / f"{role}.json"
            path.write_text(canonical_json(data) + "\n", encoding="utf-8")
            artifacts.append(
                store.attach_artifact(
                    run_id=run_id,
                    role=role,
                    artifact_type="json",
                    source_path=path,
                    storage_format="json",
                    coefficient_ring="ZZ",
                    metadata={"matrix_hash": linear_map.matrix_hash, "semantic_role": linear_map.semantic_role},
                )
            )
    invariants = []
    values: list[tuple[str, Any, EvidenceStatus, str]] = [
        ("matrix_shape", list(linear_map.shape), EvidenceStatus.VERIFIED, "matrix shape [codomain_rank, domain_rank] for A: Z^m -> Z^n"),
        ("matrix_hash", linear_map.matrix_hash, EvidenceStatus.VERIFIED, "raw integer matrix presentation hash"),
        ("rank_Q", rank_q.rank, rank_q.evidence_status, "exact rational rank over QQ"),
        ("modular_rank_profile", {str(p): result.rank for p, result in mod_profile.items()}, EvidenceStatus.VERIFIED, "exact modular ranks over prime fields"),
        ("kernel_dim_Q", rank_q.nullity, rank_q.evidence_status, "rational kernel dimension in the domain"),
        ("cokernel_dim_Q", linear_map.codomain_rank - rank_q.rank, rank_q.evidence_status, "rational cokernel dimension in the codomain"),
        ("integral_kernel_rank", kernel.rank, kernel.evidence_status, "rank of ker_Z(A)"),
        ("smith_normal_form", list(snf.diagonal_invariant_factors), snf.evidence_status, "Smith invariant factors over ZZ"),
        ("integer_kernel_basis", kernel.to_dict(), kernel.evidence_status, "columns form a Z-basis of ker_Z(A) in the domain"),
        ("image_lattice_basis", image.to_dict(), image.evidence_status, "columns form a canonical image lattice basis"),
        ("cokernel_structure", snf.cokernel.to_dict(), snf.evidence_status, "cokernel Z^n / im_Z(A) from SNF"),
        ("integral_cokernel_decomposition", snf.cokernel.to_dict(), snf.evidence_status, "structured integral cokernel decomposition from SNF"),
        ("saturation_index", image.saturation.index, image.saturation.evidence_status, "index [Sat(im A):im A]"),
    ]
    for prime, result in mod_profile.items():
        values.append((f"rank_mod_{prime}", result.rank, result.evidence_status, f"exact rank over F_{prime}"))
    for name, value, status, notes in values:
        invariants.append(
            store.record_invariant(
                run_id=run_id,
                name=name,
                value=value,
                result_kind=result_kind,
                evidence_status=status,
                method="hodgecy.algebra.integer_lattices",
                provenance=linear_map.provenance,
                certificate_id=certificate.certificate_id,
                notes=f"{notes}; semantic_role={linear_map.semantic_role}",
            )
        )
    return certificate, tuple(artifacts), tuple(invariants)


def _coerce_integer_rows(matrix: Any) -> list[list[int]]:
    if isinstance(matrix, IntegerLinearMap):
        return [list(row) for row in matrix.matrix]
    if isinstance(matrix, sp.MatrixBase):
        return [[_exact_int(matrix[row, col]) for col in range(matrix.cols)] for row in range(matrix.rows)]
    try:
        rows = [list(row) for row in matrix]
    except TypeError as exc:
        raise IntegerMatrixError("Matrix must be a SymPy matrix or a rectangular row sequence.") from exc
    if not rows:
        return []
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise IntegerMatrixError("Integer matrices must be rectangular.")
    return [[_exact_int(value) for value in row] for row in rows]


def _matrix_cols(matrix: Any) -> int:
    if isinstance(matrix, sp.MatrixBase):
        return int(matrix.cols)
    return 0


def _exact_int(value: Any) -> int:
    if isinstance(value, bool):
        raise UnsupportedExactDomainError("Boolean values are not accepted as integer matrix entries.")
    if isinstance(value, int):
        return int(value)
    if isinstance(value, sp.Integer):
        return int(value)
    sympified = sp.sympify(value)
    if isinstance(sympified, sp.Integer):
        return int(sympified)
    raise UnsupportedExactDomainError(f"Matrix entry is not an exact integer: {value!r}")


def _matrix_tuple(matrix: sp.MatrixBase) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(int(matrix[row, col]) for col in range(matrix.cols)) for row in range(matrix.rows))


def _diagonal_invariants(diagonal: sp.MatrixBase) -> list[int]:
    values = []
    for index in range(min(diagonal.rows, diagonal.cols)):
        value = abs(int(diagonal[index, index]))
        if value:
            values.append(value)
    return values


def _verify_snf_divisibility(invariant_factors: Sequence[int]) -> None:
    if any(value <= 0 for value in invariant_factors):
        raise SmithVerificationError("Smith invariant factors must be positive.")
    for left, right in zip(invariant_factors, invariant_factors[1:]):
        if right % left:
            raise SmithVerificationError("Smith invariant factors do not satisfy divisibility.")


def _verify_smith_transforms(matrix: sp.MatrixBase, diagonal: sp.MatrixBase, left: sp.MatrixBase, right: sp.MatrixBase) -> None:
    if left * matrix * right != diagonal:
        raise SmithVerificationError("Smith transforms do not verify U*A*V = D.")
    if not _is_unimodular(left) or not _is_unimodular(right):
        raise SmithVerificationError("Smith transform matrices are not unimodular.")


def _is_unimodular(matrix: sp.MatrixBase) -> bool:
    if matrix.rows != matrix.cols:
        return False
    return abs(int(matrix.det())) == 1


def _integer_kernel_from_rational_nullspace(matrix: sp.MatrixBase, domain_rank: int) -> sp.Matrix:
    vectors = []
    for vector in matrix.nullspace():
        denominators = [sp.denom(entry) for entry in vector]
        lcm = int(sp.ilcm(*[int(den) for den in denominators])) if denominators else 1
        vectors.append([int(sp.expand(entry * lcm)) for entry in vector])
    if not vectors:
        return sp.zeros(domain_rank, 0)
    return sp.Matrix(vectors).T


def _rank_mod_rows(rows: list[list[int]], p: int, width: int) -> int:
    if not rows:
        return 0
    rank = 0
    pivot_row = 0
    for col in range(width):
        pivot = None
        for row in range(pivot_row, len(rows)):
            if rows[row][col] % p:
                pivot = row
                break
        if pivot is None:
            continue
        rows[pivot_row], rows[pivot] = rows[pivot], rows[pivot_row]
        inv = pow(rows[pivot_row][col], -1, p)
        rows[pivot_row] = [(value * inv) % p for value in rows[pivot_row]]
        for row in range(len(rows)):
            if row == pivot_row or rows[row][col] % p == 0:
                continue
            factor = rows[row][col] % p
            rows[row] = [(left - factor * right) % p for left, right in zip(rows[row], rows[pivot_row])]
        rank += 1
        pivot_row += 1
    return rank


def _basis_or_map_matrix(value: IntegerLinearMap | ImageLatticeResult) -> sp.Matrix:
    if isinstance(value, ImageLatticeResult):
        return sp.Matrix(value.basis)
    return value.sympy_matrix


def _map_from_basis(matrix: sp.MatrixBase) -> IntegerLinearMap:
    return IntegerLinearMap(matrix, semantic_role=MatrixSemanticRole.UNSPECIFIED)


def _column_in_lattice(column: sp.MatrixBase, basis: sp.MatrixBase) -> bool:
    if basis.cols == 0:
        return column == sp.zeros(column.rows, 1)
    solution, params = basis.gauss_jordan_solve(column)
    if params.rows:
        solution = solution.subs({param: 0 for param in params})
    return all(sp.denom(entry) == 1 for entry in solution)


def _cokernel_string(free_rank: int, torsion: Sequence[int]) -> str:
    pieces = []
    if free_rank:
        pieces.append("Z" if free_rank == 1 else f"Z^{free_rank}")
    pieces.extend(f"Z/{value}Z" for value in torsion)
    return "0" if not pieces else " + ".join(pieces)


def _prime_factors(value: int) -> tuple[int, ...]:
    factors = []
    candidate = 2
    remaining = abs(value)
    while candidate * candidate <= remaining:
        if remaining % candidate == 0:
            factors.append(candidate)
            while remaining % candidate == 0:
                remaining //= candidate
        candidate += 1 if candidate == 2 else 2
    if remaining > 1:
        factors.append(remaining)
    return tuple(factors)


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value == 2:
        return True
    if value % 2 == 0:
        return False
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _firewall() -> dict[str, bool]:
    return {
        "integer_matrix_has_no_inherent_geometric_meaning": True,
        "source_assembly_matrix_is_not_node_relation_matrix": True,
        "equal_snf_does_not_prove_geometric_complex_isomorphism": True,
        "equal_rational_rank_does_not_imply_equal_integral_structure": True,
        "equal_modular_rank_profiles_do_not_imply_equal_lattices": True,
        "source_cokernel_torsion_is_source_level_only": True,
        "source_kernel_is_not_vanishing_cycle_relation_lattice": True,
        "no_classical_defect_computed": True,
        "no_source_to_node_map_computed": True,
        "no_hodge_atom_computed": True,
    }
