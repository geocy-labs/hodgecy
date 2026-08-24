from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from hodgecy.core.results import ComparisonState, EvidenceStatus
from hodgecy.geometry.block_evaluation import (
    EXPECTED_BLOB12_BLOCK_HASHES,
    compare_block_evaluation_results,
    compute_block_evaluation_result,
    load_blob12_block_scheme,
)
from hodgecy.geometry.defects import evaluation_from_points
from hodgecy.geometry.projective_schemes import compare_hilbert_functions, compare_ideals, hilbert_function_range, ideal_of_points


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_blob12_block_ideal_loading_and_hash_verification() -> None:
    for arrangement_id, expected_hash in EXPECTED_BLOB12_BLOCK_HASHES.items():
        scheme = load_blob12_block_scheme(repo_root() / "research_outputs" / "hodgecy_ii" / "final" / "theorem_evidence" / "block_geometry" / arrangement_id / "node_block_certificate.json")

        assert scheme.block_scheme_hash == expected_hash
        assert scheme.base_field == "QQ"
        assert scheme.scheme_dimension == 0
        assert scheme.scheme_degree == 112
        assert scheme.reduced is True
        assert scheme.block_jacobian_containment == "VERIFIED"
        assert scheme.ordinary_node_verified == "UNKNOWN"


def test_degree_8_block_evaluation_for_84_and_84a() -> None:
    results = {}
    for arrangement_id in ("84", "84a"):
        scheme = load_blob12_block_scheme(repo_root() / "research_outputs" / "hodgecy_ii" / "final" / "theorem_evidence" / "block_geometry" / arrangement_id / "node_block_certificate.json")
        result = compute_block_evaluation_result(scheme, degrees=range(0, 9))
        results[arrangement_id] = result

        assert [value.H_B_d for value in result.hilbert_table.values] == [1, 4, 10, 20, 34, 52, 74, 92, 105]
        assert result.H_B_8 == 105
        assert result.evaluation_source_dimension == 165
        assert result.evaluation_target_length == 112
        assert result.evaluation_rank == 105
        assert result.evaluation_kernel_dimension == 60
        assert result.evaluation_cokernel_dimension == 7
        assert result.block_evaluation_deficiency == 7
        assert result.evaluation_relation_dimension == 7
        assert result.actual_classical_defect is None
        assert result.actual_classical_defect_status is EvidenceStatus.UNKNOWN

    comparison = compare_block_evaluation_results(results["84"], results["84a"])
    assert comparison.first_hilbert_difference is None
    assert comparison.critical_values_agree is True
    assert comparison.evaluation_deficiencies_agree is True
    assert comparison.descriptive_case == "Case C - Hilbert collapse over computed range"


def test_transpose_relation_dimension_equals_evaluation_cokernel() -> None:
    evaluation = evaluation_from_points([(1, 0, 0, 0), (0, 1, 0, 0), (1, 1, 0, 0)], ("x", "y", "z", "t"), 1)

    assert evaluation.rank == 2
    assert evaluation.cokernel_dimension == 1
    assert evaluation.target_length - evaluation.rank == evaluation.cokernel_dimension


def test_independent_conditions_have_zero_deficiency() -> None:
    evaluation = evaluation_from_points([(1, 0, 0, 0), (0, 1, 0, 0)], ("x", "y", "z", "t"), 1)

    assert evaluation.rank == evaluation.target_length
    assert evaluation.cokernel_dimension == 0


def test_same_critical_value_different_hilbert_profile_fixture() -> None:
    variables = ("x", "y", "z", "t")
    collinear = ideal_of_points([(1, 0, 0, 0), (0, 1, 0, 0), (1, 1, 0, 0)], variables)
    noncollinear = ideal_of_points([(1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0)], variables)
    left = hilbert_function_range(collinear, start=0, stop=2)
    right = hilbert_function_range(noncollinear, start=0, stop=2)
    comparison = compare_hilbert_functions(left, right)

    assert left.value_at(2) == right.value_at(2) == 3
    assert comparison.state is ComparisonState.DIFFERENT
    assert comparison.first_differing_degree == 1


def test_equal_hilbert_function_does_not_imply_equal_scheme() -> None:
    variables = ("x", "y", "z", "t")
    left_ideal = ideal_of_points([(1, 0, 0, 0)], variables)
    right_ideal = ideal_of_points([(0, 1, 0, 0)], variables)
    left_hilbert = hilbert_function_range(left_ideal, start=0, stop=3)
    right_hilbert = hilbert_function_range(right_ideal, start=0, stop=3)

    assert compare_hilbert_functions(left_hilbert, right_hilbert).state is ComparisonState.EQUAL
    assert compare_ideals(left_ideal, right_ideal)["state"] == "different"


def test_generated_blob13_assets_are_status_aware() -> None:
    subprocess.run([sys.executable, "scripts/hodgecy_ii_final_freeze.py"], cwd=repo_root(), check=True)

    table = (repo_root() / "research_outputs" / "hodgecy_ii" / "manuscript_assets" / "tables" / "block_evaluation_comparison_84_84a.tsv").read_text(encoding="utf-8")
    validation = json.loads((repo_root() / "research_outputs" / "hodgecy_ii" / "manuscript_assets" / "data" / "validation_status_84_84a.json").read_text(encoding="utf-8"))
    scope = json.loads((repo_root() / "research_outputs" / "hodgecy_ii" / "manuscript_assets" / "manifest" / "hodgecy_ii_scope.json").read_text(encoding="utf-8"))

    assert "block evaluation deficiency\t7\t7\tequal\texact block result" in table
    assert "COMPUTED_AND_PROVED_STRUCTURALLY" in table
    assert "verified classical defect\tUNKNOWN\tUNKNOWN\tequal\tnot promoted" in table
    assert {"arrangement": "84", "layer": "classical defect", "status": "UNKNOWN"} in validation
    assert scope["required_geometric_outputs"]["block_evaluation"]["classical_defect"] == "UNKNOWN"


def test_final_block_evaluation_evidence_preserves_core_values() -> None:
    subprocess.run([sys.executable, "scripts/hodgecy_ii_final_freeze.py"], cwd=repo_root(), check=True)
    payload = json.loads((repo_root() / "research_outputs" / "hodgecy_ii" / "final" / "theorem_evidence" / "block_evaluation" / "block_evaluation_comparison_84_84a.json").read_text(encoding="utf-8"))

    assert payload["results"]["84"]["H_B_8"] == 105
    assert payload["results"]["84a"]["H_B_8"] == 105
    assert payload["comparison"]["descriptive_case"] == "Case C - Hilbert collapse over computed range"
