from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .chain_complex import ChainComplexSummary, summarize_single_boundary


@dataclass(frozen=True, slots=True)
class GluingComplexAssembly:
    label: str
    summary: ChainComplexSummary

    @property
    def rank_Q(self) -> int:
        return _value(self.summary, "rank_Q", "rank")

    @property
    def rank_F2(self) -> int:
        for result in self.summary.exact_results:
            if result.operation.value == "rank_mod_p" and result.value.get("modulus") == 2:
                return int(result.value["rank"])
        raise KeyError("rank_F2 was not computed for this assembly")

    @property
    def kernel_dim_Q(self) -> int:
        return _value(self.summary, "kernel_cokernel_Q", "kernel_dimension")

    @property
    def cokernel_dim_Q(self) -> int:
        return _value(self.summary, "kernel_cokernel_Q", "cokernel_dimension")

    @property
    def smith_normal_form(self) -> list[int] | None:
        for result in self.summary.exact_results:
            if result.operation.value == "smith_normal_form":
                values = result.value.get("invariants")
                return None if values is None else [int(value) for value in values]
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "rank_Q": self.rank_Q,
            "rank_F2": self.rank_F2,
            "kernel_dim_Q": self.kernel_dim_Q,
            "cokernel_dim_Q": self.cokernel_dim_Q,
            "smith_normal_form": self.smith_normal_form,
            "summary": self.summary.to_dict(),
        }


def summarize_gluing_matrix(matrix: Any, *, label: str = "gluing_complex", rank_primes: tuple[int, ...] = (2,)) -> GluingComplexAssembly:
    return GluingComplexAssembly(label=label, summary=summarize_single_boundary(label, matrix, rank_primes=rank_primes))


def _value(summary: ChainComplexSummary, operation: str, key: str) -> int:
    for result in summary.exact_results:
        if result.operation.value == operation:
            return int(result.value[key])
    raise KeyError(f"{operation}.{key} was not computed for this assembly")
