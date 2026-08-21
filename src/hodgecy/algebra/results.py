from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from hodgecy.core.ids import HodgeCYID, IdentityKind
from hodgecy.core.provenance import ComputationProvenance
from hodgecy.core.serialization import stable_sha256
from hodgecy.core.status import Exactness, ValidationEvent
from hodgecy.core.versions import SchemaVersion
from hodgecy.math import BasisMatrix

RESULT_SCHEMA_VERSION = "exact_algebra_result.v1"


class ExactAlgebraOperation(str, Enum):
    RANK_Q = "rank_Q"
    RANK_MOD_P = "rank_mod_p"
    SMITH_NORMAL_FORM = "smith_normal_form"
    KERNEL_COKERNEL_Q = "kernel_cokernel_Q"
    CHAIN_COMPLEX_SUMMARY = "chain_complex_summary"


@dataclass(frozen=True, slots=True)
class ExactMatrixRef:
    matrix_id: HodgeCYID
    shape: tuple[int, int]
    coefficient_domain: str
    row_basis_id: HodgeCYID | None = None
    column_basis_id: HodgeCYID | None = None
    payload_hash: str | None = None
    label: str | None = None

    @classmethod
    def from_basis_matrix(cls, matrix: BasisMatrix, *, label: str | None = None) -> "ExactMatrixRef":
        payload_hash = stable_sha256(matrix.to_dict())
        return cls(
            matrix_id=HodgeCYID.derived_from_components(IdentityKind.DERIVED_OBJECT, "exact_matrix", {"payload_hash": payload_hash, "label": label}),
            shape=matrix.shape,
            coefficient_domain=matrix.row_basis.coefficient_domain.kind.value,
            row_basis_id=matrix.row_basis.basis_id,
            column_basis_id=matrix.column_basis.basis_id,
            payload_hash=payload_hash,
            label=label,
        )

    @classmethod
    def from_sympy_matrix(cls, matrix: Any, *, label: str | None = None, coefficient_domain: str = "Z") -> "ExactMatrixRef":
        rows = int(getattr(matrix, "rows"))
        cols = int(getattr(matrix, "cols"))
        payload = [[str(matrix[row, col]) for col in range(cols)] for row in range(rows)]
        payload_hash = stable_sha256(payload)
        return cls(
            matrix_id=HodgeCYID.derived_from_components(IdentityKind.DERIVED_OBJECT, "exact_matrix", {"payload_hash": payload_hash, "label": label}),
            shape=(rows, cols),
            coefficient_domain=coefficient_domain,
            payload_hash=payload_hash,
            label=label,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "matrix_id": self.matrix_id.to_dict(),
            "shape": list(self.shape),
            "coefficient_domain": self.coefficient_domain,
            "row_basis_id": None if self.row_basis_id is None else self.row_basis_id.to_dict(),
            "column_basis_id": None if self.column_basis_id is None else self.column_basis_id.to_dict(),
            "payload_hash": self.payload_hash,
            "label": self.label,
        }


@dataclass(frozen=True, slots=True)
class ExactAlgebraResult:
    operation: ExactAlgebraOperation
    matrix_ref: ExactMatrixRef
    value: dict[str, Any]
    result_id: HodgeCYID | None = None
    algorithm: str = "sympy"
    algorithm_version: str | None = None
    computation_provenance: ComputationProvenance | None = None
    validation_events: tuple[ValidationEvent, ...] = ()
    exactness: Exactness = Exactness.EXACT
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: SchemaVersion = SchemaVersion(RESULT_SCHEMA_VERSION)

    def __post_init__(self) -> None:
        if self.result_id is None:
            object.__setattr__(self, "result_id", self._derived_id())
        assert self.result_id is not None
        self.result_id.require_kind(IdentityKind.DERIVED_OBJECT)

    def _derived_id(self) -> HodgeCYID:
        return HodgeCYID.derived_from_components(
            IdentityKind.DERIVED_OBJECT,
            "exact_algebra_result",
            {
                "operation": self.operation.value,
                "matrix_ref": self.matrix_ref.to_dict(),
                "value": self.value,
                "algorithm": self.algorithm,
                "algorithm_version": self.algorithm_version,
                "exactness": self.exactness.value,
                "schema_version": self.schema_version.to_dict(),
            },
        )

    def to_dict(self) -> dict[str, Any]:
        assert self.result_id is not None
        return {
            "result_id": self.result_id.to_dict(),
            "operation": self.operation.value,
            "matrix_ref": self.matrix_ref.to_dict(),
            "value": self.value,
            "algorithm": self.algorithm,
            "algorithm_version": self.algorithm_version,
            "computation_provenance": None if self.computation_provenance is None else self.computation_provenance.to_dict(),
            "validation_events": [event.to_dict() for event in self.validation_events],
            "exactness": self.exactness.value,
            "metadata": self.metadata,
            "schema_version": self.schema_version.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class RankResult:
    result: ExactAlgebraResult

    @property
    def rank(self) -> int:
        return int(self.result.value["rank"])

    @property
    def modulus(self) -> int | None:
        return self.result.value.get("modulus")

    def to_dict(self) -> dict[str, Any]:
        return self.result.to_dict()


@dataclass(frozen=True, slots=True)
class SmithNormalFormResult:
    result: ExactAlgebraResult

    @property
    def invariants(self) -> list[int] | None:
        values = self.result.value.get("invariants")
        return None if values is None else [int(value) for value in values]

    @property
    def status(self) -> str:
        return str(self.result.value["status"])

    def to_dict(self) -> dict[str, Any]:
        return self.result.to_dict()


@dataclass(frozen=True, slots=True)
class KernelCokernelResult:
    result: ExactAlgebraResult

    @property
    def kernel_dimension(self) -> int:
        return int(self.result.value["kernel_dimension"])

    @property
    def cokernel_dimension(self) -> int:
        return int(self.result.value["cokernel_dimension"])

    def to_dict(self) -> dict[str, Any]:
        return self.result.to_dict()


def rank_over_q_result(matrix: Any, *, matrix_ref: ExactMatrixRef | None = None) -> RankResult:
    ref = matrix_ref or ExactMatrixRef.from_sympy_matrix(matrix, coefficient_domain="Q")
    rank = int(matrix.rank())
    return RankResult(ExactAlgebraResult(ExactAlgebraOperation.RANK_Q, ref, {"rank": rank, "field": "Q"}))


def rank_mod_p_result(matrix: Any, *, p: int = 2, matrix_ref: ExactMatrixRef | None = None) -> RankResult:
    if p < 2 or not _is_prime(p):
        raise ValueError("rank_mod_p_result requires a prime p")
    ref = matrix_ref or ExactMatrixRef.from_sympy_matrix(matrix, coefficient_domain=f"F_{p}")
    rows = [[int(matrix[row, col]) % p for col in range(matrix.cols)] for row in range(matrix.rows)]
    if not rows:
        rank = 0
    else:
        rank = 0
        pivot_row = 0
        for col in range(matrix.cols):
            pivot = None
            for row in range(pivot_row, matrix.rows):
                if rows[row][col] % p != 0:
                    pivot = row
                    break
            if pivot is None:
                continue
            rows[pivot_row], rows[pivot] = rows[pivot], rows[pivot_row]
            inv = pow(rows[pivot_row][col], -1, p)
            rows[pivot_row] = [(value * inv) % p for value in rows[pivot_row]]
            for row in range(matrix.rows):
                if row == pivot_row or rows[row][col] % p == 0:
                    continue
                factor = rows[row][col] % p
                rows[row] = [(left - factor * right) % p for left, right in zip(rows[row], rows[pivot_row])]
            rank += 1
            pivot_row += 1
    return RankResult(ExactAlgebraResult(ExactAlgebraOperation.RANK_MOD_P, ref, {"rank": rank, "field": f"F_{p}", "modulus": p}))


def kernel_cokernel_result_q(matrix: Any, *, matrix_ref: ExactMatrixRef | None = None) -> KernelCokernelResult:
    ref = matrix_ref or ExactMatrixRef.from_sympy_matrix(matrix, coefficient_domain="Q")
    rank = int(matrix.rank())
    value = {"rank": rank, "kernel_dimension": int(matrix.cols - rank), "cokernel_dimension": int(matrix.rows - rank), "field": "Q"}
    return KernelCokernelResult(ExactAlgebraResult(ExactAlgebraOperation.KERNEL_COKERNEL_Q, ref, value))


def smith_normal_form_result(matrix: Any, *, matrix_ref: ExactMatrixRef | None = None) -> SmithNormalFormResult:
    ref = matrix_ref or ExactMatrixRef.from_sympy_matrix(matrix, coefficient_domain="Z")
    try:
        from sympy.matrices.normalforms import smith_normal_form
        import sympy as sp

        normal = smith_normal_form(matrix, domain=sp.ZZ)
        invariants = []
        for index in range(min(normal.rows, normal.cols)):
            value = int(abs(normal[index, index]))
            if value:
                invariants.append(value)
        value_payload = {"status": "computed", "invariants": invariants, "domain": "Z"}
        exactness = Exactness.EXACT
    except Exception as exc:
        value_payload = {"status": "failed", "invariants": None, "domain": "Z", "error": type(exc).__name__}
        exactness = Exactness.FAILED
    return SmithNormalFormResult(ExactAlgebraResult(ExactAlgebraOperation.SMITH_NORMAL_FORM, ref, value_payload, exactness=exactness))

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
