"""Compare Gate 3 candidate atom profiles for smoothing_bridge_84 and smoothing_bridge_84a."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.datasets.cynk_meyer import load_table1  # noqa: E402
from hodgecy.profiles import (  # noqa: E402
    HodgeCYAtomProfile,
    compare_atom_profiles,
    comparison_to_dict,
)


def _load_atom_profiles() -> list[dict]:
    path = REPO_ROOT / "data" / "processed" / "smoothing_bridge_atom_profiles.json"
    if not path.exists():
        subprocess.run([sys.executable, "scripts/build_smoothing_bridge_atom_profiles.py"], cwd=REPO_ROOT, check=True)
    return json.loads(path.read_text(encoding="utf-8"))


def _to_profile(record: dict) -> HodgeCYAtomProfile:
    return HodgeCYAtomProfile(**record)


def main() -> None:
    payload = _load_atom_profiles()
    profile_map = {record["source_arrangement"]: _to_profile(record) for record in payload}
    table = load_table1().set_index("arrangement")

    comparison = comparison_to_dict(
        compare_atom_profiles(
            profile_map["84"],
            profile_map["84a"],
            table.loc["84"].to_dict(),
            table.loc["84a"].to_dict(),
        )
    )

    lattice_summary_path = REPO_ROOT / "data" / "processed" / "lattice_audit_84_84a_summary.json"
    if lattice_summary_path.exists():
        lattice_summary = json.loads(lattice_summary_path.read_text(encoding="utf-8"))
        comparison["source_lattice_isomorphic"] = lattice_summary.get("incidence_isomorphic")
        comparison["source_lattice_audit_status"] = "available"
    else:
        comparison["source_lattice_isomorphic"] = None
        comparison["source_lattice_audit_status"] = "not_available"

    (REPO_ROOT / "data" / "processed" / "comparison_smoothing_bridge_84_84a.json").write_text(
        json.dumps(comparison, indent=2),
        encoding="utf-8",
    )

    lines = [
        r"\begin{tabular}{@{}p{4.8cm}p{8.8cm}@{}}",
        r"\toprule",
        r"Quantity & Result \\",
        r"\midrule",
        rf"Same node count & {comparison['same_node_count']} \\",
        rf"Same classical defect & {comparison['same_classical_defect']} \\",
        rf"Same block profile & {comparison['same_block_profile']} \\",
        rf"Same gluing deficit & {comparison['same_gluing_deficit']} \\",
        rf"Same Hodge numbers & {comparison['same_hodge_numbers']} \\",
        rf"Same singularity profile & {comparison['same_singularity_profile']} \\",
        rf"Same modular form & {comparison['same_modular_form']} \\",
        rf"Source lattice isomorphic & {comparison['source_lattice_isomorphic']} \\",
        rf"Conclusion & {comparison['conclusion']} \\",
        rf"Status & {comparison['status']} \\",
        rf"Notes & {comparison['notes']} \\",
        r"\bottomrule",
        r"\end{tabular}",
        "",
    ]
    (REPO_ROOT / "paper" / "tables" / "comparison_smoothing_bridge_84_84a.tex").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
