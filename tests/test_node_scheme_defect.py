from __future__ import annotations

from hodgecy.defects.node_scheme import (
    HilbertFunctionResult,
    NodeSchemeData,
    compute_defect_from_hilbert_function,
    compute_hilbert_function_placeholder,
    defect_profile,
)


def test_placeholder_hilbert_function_is_not_computed() -> None:
    node_scheme = NodeSchemeData(
        example_id="cm-84",
        ambient="P3",
        equation=None,
        node_count=None,
        node_coordinates=None,
        ideal_generators=None,
        critical_degree=5,
        source="test",
    )
    result = compute_hilbert_function_placeholder(node_scheme)
    assert result.example_id == "cm-84"
    assert result.status == "not_computed"
    assert result.hilbert_value is None


def test_compute_defect_from_hilbert_function_numeric_case() -> None:
    result = HilbertFunctionResult(
        example_id="cm-x",
        critical_degree=7,
        hilbert_value=10,
        expected_independent_conditions=13,
        computed_by="test",
        status="computed",
    )
    assert compute_defect_from_hilbert_function(result) == 3


def test_defect_profile_uses_placeholder_when_missing_result() -> None:
    node_scheme = NodeSchemeData(
        example_id="cm-y",
        ambient=None,
        equation=None,
        node_count=12,
        node_coordinates=None,
        ideal_generators=None,
        critical_degree=None,
        source=None,
        notes="Schema-only check.",
    )
    profile = defect_profile(node_scheme)
    assert profile.example_id == "cm-y"
    assert profile.node_count == 12
    assert profile.classical_defect is None
    assert profile.status == "not_computed"
