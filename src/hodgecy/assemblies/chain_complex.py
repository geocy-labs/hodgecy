from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hodgecy.algebra.results import ExactAlgebraResult, ExactMatrixRef, kernel_cokernel_result_q, rank_mod_p_result, rank_over_q_result, smith_normal_form_result
from hodgecy.core.errors import ValidationError
from hodgecy.core.ids import HodgeCYID, IdentityKind
from hodgecy.core.serialization import stable_sha256
from hodgecy.core.versions import SchemaVersion
from hodgecy.math import BasisMatrix

ASSEMBLY_SCHEMA_VERSION = "assembly_summary.v1"


@dataclass(frozen=True, slots=True)
class ChainModule:
    module_id: HodgeCYID
    degree: int
    rank: int
    label: str | None = None

    def __post_init__(self) -> None:
        self.module_id.require_kind(IdentityKind.DERIVED_OBJECT)
        if self.rank < 0:
            raise ValidationError("ChainModule rank must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {"module_id": self.module_id.to_dict(), "degree": self.degree, "rank": self.rank, "label": self.label}


@dataclass(frozen=True, slots=True)
class ChainMap:
    map_id: HodgeCYID
    source_module: HodgeCYID
    target_module: HodgeCYID
    matrix_ref: ExactMatrixRef
    degree_shift: int = -1
    label: str | None = None

    def __post_init__(self) -> None:
        self.map_id.require_kind(IdentityKind.DERIVED_OBJECT)
        self.source_module.require_kind(IdentityKind.DERIVED_OBJECT)
        self.target_module.require_kind(IdentityKind.DERIVED_OBJECT)

    def to_dict(self) -> dict[str, Any]:
        return {
            "map_id": self.map_id.to_dict(),
            "source_module": self.source_module.to_dict(),
            "target_module": self.target_module.to_dict(),
            "matrix_ref": self.matrix_ref.to_dict(),
            "degree_shift": self.degree_shift,
            "label": self.label,
        }


@dataclass(frozen=True, slots=True)
class ChainComplexSummary:
    assembly_id: HodgeCYID
    modules: tuple[ChainModule, ...]
    maps: tuple[ChainMap, ...]
    exact_results: tuple[ExactAlgebraResult, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: SchemaVersion = SchemaVersion(ASSEMBLY_SCHEMA_VERSION)

    def __post_init__(self) -> None:
        self.assembly_id.require_kind(IdentityKind.DERIVED_OBJECT)
        module_ids = {module.module_id for module in self.modules}
        for chain_map in self.maps:
            if chain_map.source_module not in module_ids or chain_map.target_module not in module_ids:
                raise ValidationError("ChainMap endpoints must be registered ChainModule objects")

    def to_dict(self) -> dict[str, Any]:
        return {
            "assembly_id": self.assembly_id.to_dict(),
            "modules": [module.to_dict() for module in self.modules],
            "maps": [chain_map.to_dict() for chain_map in self.maps],
            "exact_results": [result.to_dict() for result in self.exact_results],
            "metadata": self.metadata,
            "schema_version": self.schema_version.to_dict(),
        }


def module_id(label: str, *, degree: int, rank: int) -> HodgeCYID:
    return HodgeCYID.derived_from_components(IdentityKind.DERIVED_OBJECT, "chain_module", {"label": label, "degree": degree, "rank": rank})


def map_id(label: str, matrix_ref: ExactMatrixRef) -> HodgeCYID:
    return HodgeCYID.derived_from_components(IdentityKind.DERIVED_OBJECT, "chain_map", {"label": label, "matrix_ref": matrix_ref.to_dict()})


def basis_matrix_chain_map(label: str, matrix: BasisMatrix, source: ChainModule, target: ChainModule) -> ChainMap:
    ref = ExactMatrixRef.from_basis_matrix(matrix, label=label)
    if ref.shape != (target.rank, source.rank):
        raise ValidationError("Boundary matrix shape must be target rank by source rank")
    return ChainMap(map_id(label, ref), source.module_id, target.module_id, ref, label=label)


def summarize_single_boundary(label: str, matrix: Any, *, rank_primes: tuple[int, ...] = (2,)) -> ChainComplexSummary:
    ref = ExactMatrixRef.from_sympy_matrix(matrix, label=label)
    target = ChainModule(module_id(f"{label}_target", degree=0, rank=int(matrix.rows)), degree=0, rank=int(matrix.rows), label=f"{label} target")
    source = ChainModule(module_id(f"{label}_source", degree=1, rank=int(matrix.cols)), degree=1, rank=int(matrix.cols), label=f"{label} source")
    boundary = ChainMap(map_id(label, ref), source.module_id, target.module_id, ref, label=label)
    rank_q = rank_over_q_result(matrix, matrix_ref=ref).result
    rank_mod = tuple(rank_mod_p_result(matrix, p=p, matrix_ref=ref).result for p in rank_primes)
    kernel_cokernel = kernel_cokernel_result_q(matrix, matrix_ref=ref).result
    smith = smith_normal_form_result(matrix, matrix_ref=ref).result
    assembly_id = HodgeCYID.derived_from_components(
        IdentityKind.DERIVED_OBJECT,
        "chain_complex",
        {"label": label, "matrix_ref": ref.to_dict(), "schema_version": ASSEMBLY_SCHEMA_VERSION},
    )
    return ChainComplexSummary(
        assembly_id=assembly_id,
        modules=(target, source),
        maps=(boundary,),
        exact_results=(rank_q,) + rank_mod + (kernel_cokernel, smith),
        metadata={"label": label, "boundary_count": 1, "summary_hash": stable_sha256(ref.to_dict())},
    )
