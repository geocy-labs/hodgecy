"""Schema-level support for classical node-scheme defect computations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class NodeSchemeData:
    example_id: str
    ambient: str | None
    equation: str | None
    node_count: int | None
    node_coordinates: list | None
    ideal_generators: list[str] | None
    critical_degree: int | None
    source: str | None
    status: str = "not_computed"
    notes: str | None = None


@dataclass(slots=True)
class HilbertFunctionResult:
    example_id: str
    critical_degree: int | None
    hilbert_value: int | None
    expected_independent_conditions: int | None
    computed_by: str | None
    status: str = "not_computed"
    notes: str | None = None


@dataclass(slots=True)
class NodeDefectProfile:
    example_id: str
    node_count: int | None
    critical_degree: int | None
    hilbert_value: int | None
    expected_independent_conditions: int | None
    classical_defect: int | None
    status: str
    notes: str | None = None


def compute_hilbert_function_placeholder(node_scheme: NodeSchemeData) -> HilbertFunctionResult:
    """Return a clearly marked placeholder until an external CAS computes the data."""
    note = "External CAS computation is required for the Hilbert-function evaluation."
    if node_scheme.notes:
        note = f"{note} {node_scheme.notes}"
    return HilbertFunctionResult(
        example_id=node_scheme.example_id,
        critical_degree=node_scheme.critical_degree,
        hilbert_value=None,
        expected_independent_conditions=None,
        computed_by=None,
        status="not_computed",
        notes=note,
    )


def compute_defect_from_hilbert_function(result: HilbertFunctionResult) -> int | None:
    """Compute the classical defect when the numeric Hilbert-function data are available."""
    if result.hilbert_value is None or result.expected_independent_conditions is None:
        return None
    return result.expected_independent_conditions - result.hilbert_value


def defect_profile(
    node_scheme: NodeSchemeData,
    result: HilbertFunctionResult | None = None,
) -> NodeDefectProfile:
    """Assemble a defect profile without inventing absent CAS output."""
    resolved_result = result or compute_hilbert_function_placeholder(node_scheme)
    classical_defect = compute_defect_from_hilbert_function(resolved_result)
    notes = node_scheme.notes
    if resolved_result.notes:
        notes = resolved_result.notes if notes is None else f"{notes} {resolved_result.notes}"
    return NodeDefectProfile(
        example_id=node_scheme.example_id,
        node_count=node_scheme.node_count,
        critical_degree=resolved_result.critical_degree,
        hilbert_value=resolved_result.hilbert_value,
        expected_independent_conditions=resolved_result.expected_independent_conditions,
        classical_defect=classical_defect,
        status=resolved_result.status,
        notes=notes,
    )
