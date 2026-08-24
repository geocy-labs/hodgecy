from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_blob15_final_freeze_generates_core_records() -> None:
    subprocess.run([sys.executable, "scripts/hodgecy_ii_final_freeze.py"], cwd=repo_root(), check=True)

    final = _json(repo_root() / "research_outputs" / "hodgecy_ii" / "final" / "hodgecy_ii_final_results.json")
    questions = _json(repo_root() / "research_outputs" / "hodgecy_ii" / "final" / "hodgecy_ii_question_status.json")["questions"]
    evidence = _json(repo_root() / "research_outputs" / "hodgecy_ii" / "manuscript_assets" / "tables" / "final_evidence_status_matrix.json")

    assert final["population_context"]["processed"] == 456
    assert final["population_context"]["nontrivial_sets"] == 114
    assert final["population_context"]["pairs"] + final["population_context"]["triples"] + final["population_context"]["larger_sets"] == 114
    assert final["comparison_results"]["source_to_evaluation_chain_map"] == "unknown"
    assert final["block_geometry_results"]["84"]["ordinary_node_status"] == "UNKNOWN"
    assert {row["question_id"]: row["status"] for row in questions}["Q8"] == "ANSWERED"
    assert {row["question_id"]: row["status"] for row in questions}["Q10"] == "OPEN"
    assert {"statement": "classical defect=7", "status": "CONDITIONAL", "basis": "Only if ordinary-node/full-node hypotheses are certified."} in evidence
    assert {"statement": "source-to-evaluation morphism", "status": "OPEN", "basis": "No chain map constructed."} in evidence


def test_blob15_manuscript_inventories_and_handoff_are_frozen() -> None:
    subprocess.run([sys.executable, "scripts/hodgecy_ii_final_freeze.py"], cwd=repo_root(), check=True)

    table_inventory = _json(repo_root() / "research_outputs" / "hodgecy_ii" / "manuscript_assets" / "manifest" / "final_manuscript_table_inventory.json")["tables"]
    figure_inventory = _json(repo_root() / "research_outputs" / "hodgecy_ii" / "manuscript_assets" / "manifest" / "final_manuscript_figure_inventory.json")["figures"]
    handoff = _json(repo_root() / "research_outputs" / "hodgecy_ii" / "manuscript_assets" / "manifest" / "hodgecy_iii_handoff.json")
    fresh = _json(repo_root() / "research_outputs" / "hodgecy_ii" / "final" / "reproduction" / "fresh_store_reproduction.json")

    assert {row["table_id"] for row in table_inventory} >= {"II.1", "II.5", "II.6", "II.7"}
    assert {row["figure_id"] for row in figure_inventory} >= {"II.1", "II.4", "II.6", "S.1"}
    assert handoff["status"] == "DEFERRED_TO_HODGECY_III"
    assert handoff["population"] == {"processed": 456, "nontrivial_sets": 114}
    assert fresh["status"] == "PASS"
    assert all(item["matches_canonical"] for item in fresh["comparisons"])


def test_reproduce_hodgecy_ii_top_level_command() -> None:
    subprocess.run([sys.executable, "scripts/reproduce_hodgecy_ii.py"], cwd=repo_root(), check=True)

    manifest = _json(repo_root() / "research_outputs" / "hodgecy_ii" / "final" / "hodgecy_ii_final_research_manifest.json")
    assert manifest["package_version"] == "1.0.0"
    assert manifest["release_tag"] is None
    assert "research_outputs/hodgecy_ii/complete_fidelity_pairs_and_sets.tsv" in manifest["primary_input_hashes"]
