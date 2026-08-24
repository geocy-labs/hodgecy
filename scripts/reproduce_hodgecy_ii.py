"""Top-level HodgeCY II reproduction and final-freeze command.

The default path validates frozen theorem-bearing inputs and regenerates the
final synthesis assets. It does not rerun historical 456-record mining or
promote unsupported ordinary-node/defect/source-to-evaluation claims.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy import __version__ as HODGECY_VERSION  # noqa: E402


REQUIRED_INPUTS = [
    "research_outputs/hodgecy_ii/complete_fidelity_pairs_and_sets.tsv",
    "research_outputs/hodgecy_ii/final/theorem_evidence/source_lattice/source_lattice_comparison_84_84a.json",
    "research_outputs/hodgecy_ii/final/theorem_evidence/block_geometry/block_geometry_certification_84_84a.json",
    "research_outputs/hodgecy_ii/final/theorem_evidence/block_evaluation/block_evaluation_comparison_84_84a.json",
    "research_outputs/hodgecy_ii/final/theorem_evidence/hilbert_burch_block_theorem.json",
    "research_outputs/hodgecy_ii/final/theorem_evidence/source_block_comparison/source_block_evaluation_comparison_84_84a.json",
]


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def validate_inputs() -> None:
    missing = [path for path in REQUIRED_INPUTS if not (REPO_ROOT / path).exists()]
    if missing:
        raise SystemExit(f"Missing required HodgeCY II inputs: {missing}")


def validate_final_outputs() -> dict:
    payload = json.loads((REPO_ROOT / "research_outputs" / "hodgecy_ii" / "final" / "hodgecy_ii_final_results.json").read_text(encoding="utf-8"))
    population = payload["population_context"]
    if population["processed"] != 456 or population["nontrivial_sets"] != 114:
        raise SystemExit("Unexpected HodgeCY II final population counts.")
    comparison = payload["comparison_results"]
    if comparison["source_to_evaluation_chain_map"] != "unknown":
        raise SystemExit("Unsupported source-to-evaluation morphism promotion detected.")
    if payload["scope"]["package_version"] != HODGECY_VERSION:
        raise SystemExit("Package version mismatch in final results.")
    return payload


def main() -> None:
    validate_inputs()
    run([sys.executable, "scripts/hodgecy_ii_final_freeze.py"])
    payload = validate_final_outputs()
    population = payload["population_context"]
    print("HodgeCY II reproduction completed")
    print(f"- package version: {HODGECY_VERSION}")
    print(f"- processed: {population['processed']}")
    print(f"- nontrivial sets: {population['nontrivial_sets']}")
    print(f"- pairs/triples/larger: {population['pairs']} / {population['triples']} / {population['larger_sets']}")
    print("- unsupported promotions: none")


if __name__ == "__main__":
    main()
