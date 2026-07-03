"""Build candidate HodgeCY atom profiles from smoothing-bridge outputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.arrangements import arrangement_84, arrangement_84a  # noqa: E402
from hodgecy.profiles import profile_from_smoothing_bridge, to_dict  # noqa: E402
from hodgecy.smoothing.bridge import (  # noqa: E402
    QuarticPerturbation,
    profile_to_dict,
    smoothing_bridge_profile,
)


def _load_or_compute_smoothing_profiles() -> list[dict]:
    path = REPO_ROOT / "data" / "processed" / "smoothing_bridge_84_84a_profiles.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    perturbation = QuarticPerturbation(label="generic_quartic_Q", polynomial=None)
    profiles = [
        profile_to_dict(smoothing_bridge_profile(arrangement_84(), perturbation=perturbation)),
        profile_to_dict(smoothing_bridge_profile(arrangement_84a(), perturbation=perturbation)),
    ]
    path.write_text(json.dumps(profiles, indent=2), encoding="utf-8")
    return profiles


def _profile_summary(profile: dict) -> str:
    block_count = profile.get("block_count")
    block_profile = profile.get("block_profile") or []
    if block_count is None or not block_profile:
        return "unknown"
    return f"{block_count} blocks of size {block_profile[0]}"


def main() -> None:
    smoothing_profiles = _load_or_compute_smoothing_profiles()
    atom_profiles = []
    for profile in smoothing_profiles:
        atom_profile = profile_from_smoothing_bridge(
            arrangement_id=profile["arrangement_id"],
            expected_node_count=profile["expected_nodes_total"],
            double_line_count=profile["number_of_double_lines"],
            nodes_per_line=profile["expected_nodes_per_double_line"],
            classical_defect=None,
            defect_status="not_computed",
            notes="Derived from Gate 2 smoothing-bridge combinatorial expectations.",
        )
        atom_profiles.append(atom_profile)

    payload = [to_dict(profile) for profile in atom_profiles]
    (REPO_ROOT / "data" / "processed" / "smoothing_bridge_atom_profiles.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    lines = [
        r"\begin{tabular}{@{}p{2.0cm}p{1.6cm}p{2.0cm}p{1.2cm}p{1.2cm}p{1.4cm}p{1.5cm}p{2.2cm}p{1.5cm}p{2.0cm}p{1.6cm}p{4.5cm}@{}}",
        r"\toprule",
        r"Example & Source & Construction & Nodes & Defect & Defect status & Formal rank & Block summary & Gluing deficit & Block source & Status & Notes \\",
        r"\midrule",
    ]
    for profile in payload:
        lines.append(
            f"{profile['example_id']} & {profile['source_arrangement']} & {profile['construction']} & "
            f"{profile['node_count']} & {profile['classical_defect']} & {profile['defect_status']} & "
            f"{profile['flexible_formal_rank']} & {_profile_summary(profile)} & {profile['gluing_deficit']} & "
            f"{profile['block_profile_source']} & {profile['status']} & {profile['notes']} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", ""])
    (REPO_ROOT / "paper" / "tables" / "smoothing_bridge_atom_profiles.tex").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
