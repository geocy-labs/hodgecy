from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from hodgecy.relations import SourceEvaluationStatus, source_evaluation_firewall


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_blob14_comparison_preserves_source_split_and_block_collapse() -> None:
    sys.path.insert(0, str(repo_root() / "scripts"))
    from hodgecy_ii_source_evaluation_blob14 import build_comparison

    comparison = build_comparison()
    payload = comparison.to_dict()

    assert comparison.status is SourceEvaluationStatus.EXACT_BLOCK_EVALUATION_COLLAPSE
    assert payload["source_axis"]["first_separating_level"] == "integral source"
    assert payload["geometry_evaluation_axis"]["first_separating_level"] is None
    assert payload["source_rational_comparison"]["state"] == "equal"
    assert payload["source_integral_comparison"]["state"] == "different"
    assert payload["source_integral_comparison"]["84"]["rank_mod_2"] == 23
    assert payload["source_integral_comparison"]["84a"]["rank_mod_2"] == 21
    assert payload["block_hilbert_comparison"]["profile"] == [1, 4, 10, 20, 34, 52, 74, 92, 105]
    assert payload["critical_evaluation_comparison"]["rank"] == 105
    assert payload["critical_evaluation_comparison"]["deficiency"] == 7
    assert payload["evaluation_relation_comparison"]["relation_dimension"] == 7


def test_blob14_firewall_and_rank_feasibility_are_explicit() -> None:
    sys.path.insert(0, str(repo_root() / "scripts"))
    from hodgecy_ii_source_evaluation_blob14 import build_comparison

    comparison = build_comparison()
    payload = comparison.to_dict()
    feasibility = payload["feasibility_2_to_7"]

    assert feasibility["source_h1_rank"] == 2
    assert feasibility["target_h1_rank"] == 7
    assert feasibility["injective"] == "possible"
    assert feasibility["surjective"] == "impossible"
    assert feasibility["isomorphism"] == "impossible"
    assert payload["comparison_morphism_status"]["source_to_evaluation_chain_map"] == "unknown"
    assert payload["comparison_morphism_status"]["explicit_theorem_backed_data_available"] is False
    assert payload["relation_dimension_comparison"]["no_identification_or_subspace_inference"] is True
    assert source_evaluation_firewall()["block_index_correspondence_is_not_chain_map"] is True


def test_blob14_generator_writes_deterministic_core_assets() -> None:
    subprocess.run([sys.executable, "scripts/hodgecy_ii_source_evaluation_blob14.py"], cwd=repo_root(), check=True)
    payload = json.loads((repo_root() / "research_outputs" / "hodgecy_ii" / "source_evaluation_blob14" / "hodgecy_ii_84_84a_source_evaluation_comparison.json").read_text(encoding="utf-8"))
    table = (repo_root() / "research_outputs" / "hodgecy_ii" / "manuscript_assets" / "tables" / "source_block_evaluation_comparison_84_84a.tsv").read_text(encoding="utf-8")
    scope = json.loads((repo_root() / "research_outputs" / "hodgecy_ii" / "manuscript_assets" / "manifest" / "hodgecy_ii_scope.json").read_text(encoding="utf-8"))

    assert payload["status"] == "EXACT_BLOCK_EVALUATION_COLLAPSE"
    assert payload["non_determination_certificate"]["certificate_id"] == "block_evaluation_does_not_determine_integral_source_type"
    assert "source SNF\t(1^23,2,6,12)\t(1^21,2,4^3,12)\tdifferent\tVERIFIED" in table
    assert "source-to-evaluation chain map\tUNKNOWN\tUNKNOWN\tnot constructed\tUNKNOWN" in table
    assert scope["required_geometric_outputs"]["blob_14"]["source_to_evaluation_chain_map"] == "UNKNOWN"
