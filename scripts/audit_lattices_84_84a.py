"""Run the Gate 1 lattice audit for Cynk--Meyer arrangements 84 and 84a."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.arrangements import (  # noqa: E402
    arrangement_84,
    arrangement_84a,
    are_rank_fingerprints_equal,
    canonical_subset_rank_fingerprint,
    find_incidence_isomorphisms,
    incidence_isomorphic,
    maximal_incidence_strata,
    subset_rank_table,
)


def _write_tex_summary(path: Path, summary: dict) -> None:
    first_isomorphism = summary["first_isomorphism"]
    first_iso_text = "None found"
    if first_isomorphism is not None:
        pairs = ", ".join(
            f"{left}->{right}" for left, right in first_isomorphism["plane_label_map"].items()
        )
        first_iso_text = pairs

    path.write_text(
        "\n".join(
            [
                r"\begin{tabular}{@{}p{4.6cm}p{9.2cm}@{}}",
                r"\toprule",
                r"Quantity & Result \\",
                r"\midrule",
                rf"Arrangements & {summary['arrangement_ids'][0]} vs.\ {summary['arrangement_ids'][1]} \\",
                rf"Same subset-rank fingerprint & {'Yes' if summary['same_subset_rank_fingerprint'] else 'No'} \\",
                rf"Incidence-isomorphic & {'Yes' if summary['incidence_isomorphic'] else 'No'} \\",
                rf"Number of isomorphisms found & {summary['number_of_isomorphisms_found']} \\",
                rf"First isomorphism & {first_iso_text} \\",
                rf"Notes & {summary['notes']} \\",
                r"\bottomrule",
                r"\end{tabular}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    arr84 = arrangement_84()
    arr84a = arrangement_84a()

    subset_rank_table(arr84).to_csv(REPO_ROOT / "data" / "processed" / "lattice_audit_84_subset_ranks.csv", index=False)
    subset_rank_table(arr84a).to_csv(REPO_ROOT / "data" / "processed" / "lattice_audit_84a_subset_ranks.csv", index=False)
    maximal_incidence_strata(arr84).to_csv(
        REPO_ROOT / "data" / "processed" / "lattice_audit_84_maximal_strata.csv",
        index=False,
    )
    maximal_incidence_strata(arr84a).to_csv(
        REPO_ROOT / "data" / "processed" / "lattice_audit_84a_maximal_strata.csv",
        index=False,
    )

    isomorphisms = find_incidence_isomorphisms(arr84, arr84a, max_results=10)
    summary = {
        "arrangement_ids": [arr84.arrangement_id, arr84a.arrangement_id],
        "fingerprint_84": canonical_subset_rank_fingerprint(arr84),
        "fingerprint_84a": canonical_subset_rank_fingerprint(arr84a),
        "same_subset_rank_fingerprint": are_rank_fingerprints_equal(arr84, arr84a),
        "incidence_isomorphic": incidence_isomorphic(arr84, arr84a),
        "number_of_isomorphisms_found": len(isomorphisms),
        "first_isomorphism": isomorphisms[0] if isomorphisms else None,
        "notes": (
            "This is an arrangement-incidence audit, not a Hodge atom computation. "
            "It tests whether the motivational pair 84/84a is separated by incidence data."
        ),
    }

    summary_path = REPO_ROOT / "data" / "processed" / "lattice_audit_84_84a_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_tex_summary(REPO_ROOT / "paper" / "tables" / "lattice_audit_84_84a_summary.tex", summary)


if __name__ == "__main__":
    main()
