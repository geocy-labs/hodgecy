"""Build concurrency-aware profiles for arrangements 84 and 84a."""

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
    build_concurrency_profile,
    colored_graph_isomorphic,
    concurrency_profile_to_dict,
)


def _normalize_line_profiles(items: list[dict]) -> list[tuple[tuple[int, ...], int]]:
    return sorted((tuple(item["profile"]), item["count"]) for item in items)


def main() -> None:
    profile_84 = build_concurrency_profile(arrangement_84())
    profile_84a = build_concurrency_profile(arrangement_84a())

    payload_84 = concurrency_profile_to_dict(profile_84)
    payload_84a = concurrency_profile_to_dict(profile_84a)

    (REPO_ROOT / "data" / "processed" / "concurrency_profile_84.json").write_text(
        json.dumps(payload_84, indent=2),
        encoding="utf-8",
    )
    (REPO_ROOT / "data" / "processed" / "concurrency_profile_84a.json").write_text(
        json.dumps(payload_84a, indent=2),
        encoding="utf-8",
    )

    graph_iso = colored_graph_isomorphic(profile_84, profile_84a)
    same_double_line_count = profile_84.double_line_count == profile_84a.double_line_count
    same_multiple_point_counts = profile_84.multiple_point_count_by_multiplicity == profile_84a.multiple_point_count_by_multiplicity
    same_line_profile_counts = _normalize_line_profiles(profile_84.line_profile_counts) == _normalize_line_profiles(profile_84a.line_profile_counts)
    same_p4_degree_sequence = profile_84.p4_collinearity_degree_sequence == profile_84a.p4_collinearity_degree_sequence

    if graph_iso is None:
        conclusion = "graph_isomorphism_unknown"
    elif not all([same_double_line_count, same_multiple_point_counts, same_line_profile_counts, same_p4_degree_sequence]) or graph_iso is False:
        conclusion = "separated_by_concurrency_profile"
    else:
        conclusion = "not_separated_by_current_concurrency_profile"

    comparison = {
        "same_double_line_count": same_double_line_count,
        "same_multiple_point_counts": same_multiple_point_counts,
        "same_line_profile_counts": same_line_profile_counts,
        "same_p4_degree_sequence": same_p4_degree_sequence,
        "colored_graph_isomorphic": graph_iso,
        "conclusion": conclusion,
    }
    (REPO_ROOT / "data" / "processed" / "concurrency_comparison_84_84a.json").write_text(
        json.dumps(comparison, indent=2),
        encoding="utf-8",
    )

    lines = [
        r"\begin{tabular}{@{}p{4.8cm}p{8.4cm}@{}}",
        r"\toprule",
        r"Quantity & Result \\",
        r"\midrule",
        rf"Same double-line count & {same_double_line_count} \\",
        rf"Same multiple-point counts & {same_multiple_point_counts} \\",
        rf"Same line-profile counts & {same_line_profile_counts} \\",
        rf"Same p4 degree sequence & {same_p4_degree_sequence} \\",
        rf"Colored-graph isomorphic & {graph_iso} \\",
        rf"Conclusion & {conclusion} \\",
        r"\bottomrule",
        r"\end{tabular}",
        "",
    ]
    (REPO_ROOT / "paper" / "tables" / "concurrency_profile_84_84a.tex").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
