"""Write HodgeCY II Hilbert-Burch block-theorem evidence."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.geometry.hilbert_burch import write_hilbert_burch_evidence  # noqa: E402


REQUIRED_FINAL_ASSETS = (
    "research_outputs/hodgecy_ii/final/hodgecy_ii_literature_review.json",
    "research_outputs/hodgecy_ii/final/hodgecy_ii_literature_review.md",
    "research_outputs/hodgecy_ii/final/hodgecy_ii_related_work.bib",
    "research_outputs/hodgecy_ii/final/hodgecy_ii_star_configuration_audit.json",
    "research_outputs/hodgecy_ii/final/hodgecy_ii_star_configuration_audit.md",
    "research_outputs/hodgecy_ii/final/hodgecy_ii_hilbert_burch_theorem.tex",
)


def verify_final_assets() -> None:
    import json

    missing = [path for path in REQUIRED_FINAL_ASSETS if not (REPO_ROOT / path).exists()]
    if missing:
        raise SystemExit(f"Missing Hilbert-Burch final assets: {missing}")

    literature = json.loads((REPO_ROOT / REQUIRED_FINAL_ASSETS[0]).read_text(encoding="utf-8"))
    if literature["novelty_statement"]["rejected_claim"] != "No previous work has found >10,000 Calabi-Yau collisions.":
        raise SystemExit("Literature review novelty firewall is missing.")
    if "appears absent in the literature reviewed here" not in literature["novelty_statement"]["conservative_claim"]:
        raise SystemExit("Literature review uses an overstrong novelty claim.")

    audit = json.loads((REPO_ROOT / REQUIRED_FINAL_ASSETS[3]).read_text(encoding="utf-8"))
    if audit["geramita_harbourne_migliore"]["hypothesis_match"] != "PARTIAL":
        raise SystemExit("Star-configuration hypothesis mismatch audit is missing.")
    if audit["direct_line_skeleton_proof"]["status"] != "PROVED":
        raise SystemExit("Direct line-skeleton proof audit is not proved.")

    theorem = (REPO_ROOT / REQUIRED_FINAL_ASSETS[5]).read_text(encoding="utf-8")
    required_snippets = [
        "\\label{thm:hodgecy-ii-eight-plane-line-skeleton}",
        "\\oplus",
        "not a promotion",
        "do not determine the integral",
    ]
    missing_snippets = [snippet for snippet in required_snippets if snippet not in theorem]
    if missing_snippets:
        raise SystemExit(f"Hilbert-Burch theorem asset is missing snippets: {missing_snippets}")


def main() -> None:
    json_path, md_path, payload = write_hilbert_burch_evidence(REPO_ROOT)
    verify_final_assets()
    print("HodgeCY II Hilbert-Burch evidence generated")
    print(f"- status: {payload['status']}")
    print(f"- json: {json_path.relative_to(REPO_ROOT).as_posix()}")
    print(f"- markdown: {md_path.relative_to(REPO_ROOT).as_posix()}")
    print("- final literature/proof assets: verified")


if __name__ == "__main__":
    main()
