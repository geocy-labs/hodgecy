from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EstimateKind(str, Enum):
    KNOWN = "known"
    ESTIMATED = "estimated"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class QueryEstimate:
    kind: EstimateKind
    rows: int | None = None
    bytes: int | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind.value, "rows": self.rows, "bytes": self.bytes, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class QueryPlanSummary:
    backend: str
    projected_columns: tuple[str, ...]
    heavy_columns: tuple[str, ...] = ()
    predicate_pushdown: bool = False
    partition_count: int | None = None
    row_group_count: int | None = None
    estimated_rows: QueryEstimate = field(default_factory=lambda: QueryEstimate(EstimateKind.UNKNOWN))
    estimated_bytes: QueryEstimate = field(default_factory=lambda: QueryEstimate(EstimateKind.UNKNOWN))
    full_scan_likely: bool = True
    source_relative_paths: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    @property
    def heavy_columns_requested(self) -> bool:
        return bool(self.heavy_columns)

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "projected_columns": list(self.projected_columns),
            "heavy_columns": list(self.heavy_columns),
            "heavy_columns_requested": self.heavy_columns_requested,
            "predicate_pushdown": self.predicate_pushdown,
            "partition_count": self.partition_count,
            "row_group_count": self.row_group_count,
            "estimated_rows": self.estimated_rows.to_dict(),
            "estimated_bytes": self.estimated_bytes.to_dict(),
            "full_scan_likely": self.full_scan_likely,
            "source_relative_paths": list(self.source_relative_paths),
            "notes": list(self.notes),
        }
