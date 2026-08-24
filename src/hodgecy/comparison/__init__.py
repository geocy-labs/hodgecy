"""Generic comparison engine for persisted HodgeCY results."""

from .engine import AmbiguousResultError, ComparisonEngine, ComparisonError, canonical_value
from .models import (
    COMPARISON_SCHEMA_VERSION,
    ComparisonOperand,
    ComparisonPolicy,
    ComparisonResult,
    EquivalenceClass,
    EquivalenceClassResult,
    FirstDifferenceResult,
    PairComparisonReport,
    RefinementLevel,
    RefinementResult,
    RunSelectionPolicy,
    SetComparisonResult,
)

__all__ = [
    "AmbiguousResultError",
    "COMPARISON_SCHEMA_VERSION",
    "ComparisonEngine",
    "ComparisonError",
    "ComparisonOperand",
    "ComparisonPolicy",
    "ComparisonResult",
    "EquivalenceClass",
    "EquivalenceClassResult",
    "FirstDifferenceResult",
    "PairComparisonReport",
    "RefinementLevel",
    "RefinementResult",
    "RunSelectionPolicy",
    "SetComparisonResult",
    "canonical_value",
]
