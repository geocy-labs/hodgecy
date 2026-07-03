"""Generate Gate 2 smoothing-bridge profiles for arrangements 84 and 84a."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.arrangements import arrangement_84, arrangement_84a  # noqa: E402
from hodgecy.datasets.cynk_meyer import load_table1  # noqa: E402
from hodgecy.smoothing.bridge import (  # noqa: E402
    QuarticPerturbation,
    grouped_double_lines,
    profile_to_dict,
    smoothing_bridge_profile,
)


def _profile_table_tex(path: Path, profiles: list[dict]) -> None:
    lines = [
        r"\begin{tabular}{@{}p{1.5cm}p{1.8cm}p{1.7cm}p{1.7cm}p{2.2cm}p{2.0cm}p{5.0cm}@{}}",
        r"\toprule",
        r"Arrangement & Double lines & $l_3$ & Nodes / line & Expected nodes & Status & Warnings \\",
        r"\midrule",
    ]
    for profile in profiles:
        warnings = "; ".join(profile["warnings"]) if profile["warnings"] else "None"
        lines.append(
            f"{profile['arrangement_id']} & {profile['number_of_double_lines']} & "
            f"{profile['triple_line_count']} & {profile['expected_nodes_per_double_line']} & "
            f"{profile['expected_nodes_total']} & {profile['status']} & {warnings} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    table = load_table1().set_index("arrangement")
    perturbation = QuarticPerturbation(label="generic_quartic_Q", polynomial=None)

    arr84 = arrangement_84()
    arr84a = arrangement_84a()

    grouped_double_lines(arr84).to_csv(REPO_ROOT / "data" / "processed" / "smoothing_bridge_84_double_lines.csv", index=False)
    grouped_double_lines(arr84a).to_csv(REPO_ROOT / "data" / "processed" / "smoothing_bridge_84a_double_lines.csv", index=False)

    profile_84 = smoothing_bridge_profile(arr84, perturbation=perturbation, table1_row=table.loc["84"].to_dict())
    profile_84a = smoothing_bridge_profile(arr84a, perturbation=perturbation, table1_row=table.loc["84a"].to_dict())

    payload = [profile_to_dict(profile_84), profile_to_dict(profile_84a)]
    (REPO_ROOT / "data" / "processed" / "smoothing_bridge_84_84a_profiles.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    _profile_table_tex(REPO_ROOT / "paper" / "tables" / "smoothing_bridge_84_84a_profiles.tex", payload)


if __name__ == "__main__":
    main()
