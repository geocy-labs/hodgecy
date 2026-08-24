from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from hodgecy.relations import source_evaluation_firewall


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _comparison_payload() -> dict:
    return json.loads(
        (
            repo_root()
            / "research_outputs"
            / "hodgecy_ii"
            / "final"
            / "theorem_evidence"
            / "source_block_comparison"
            / "source_block_evaluation_comparison_84_84a.json"
        ).read_text(encoding="utf-8")
    )


def test_final_comparison_preserves_source_split_and_block_collapse() -> None:
    payload = _comparison_payload()

    assert payload["status"] == "EXACT_BLOCK_EVALUATION_COLLAPSE"
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


def test_final_firewall_and_rank_feasibility_are_explicit() -> None:
    payload = _comparison_payload()
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


def test_final_freeze_writes_deterministic_source_block_assets() -> None:
    subprocess.run([sys.executable, "scripts/hodgecy_ii_final_freeze.py"], cwd=repo_root(), check=True)

    payload = _comparison_payload()
    table = (repo_root() / "research_outputs" / "hodgecy_ii" / "manuscript_assets" / "tables" / "source_block_evaluation_comparison_84_84a.tsv").read_text(encoding="utf-8")
    scope = json.loads((repo_root() / "research_outputs" / "hodgecy_ii" / "manuscript_assets" / "manifest" / "hodgecy_ii_scope.json").read_text(encoding="utf-8"))

    assert payload["non_determination_certificate"]["certificate_id"] == "block_evaluation_does_not_determine_integral_source_type"
    assert "source SNF\t(1^23,2,6,12)\t(1^21,2,4^3,12)\tdifferent\tVERIFIED" in table
    assert "proved by Hilbert-Burch plus regular quartic section" in table
    assert "source-to-evaluation chain map\tUNKNOWN\tUNKNOWN\tnot constructed\tUNKNOWN" in table
    assert scope["required_geometric_outputs"]["claim_boundaries"]["source_to_evaluation_chain_map"] == "UNKNOWN"
