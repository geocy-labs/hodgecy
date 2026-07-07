from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pandas as pd


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_generated_assets_include_partial_verification_and_p4_figures() -> None:
    subprocess.run([sys.executable, "scripts/generate_paper_assets.py"], cwd=repo_root(), check=True)

    smoothing = pd.read_csv(repo_root() / "paper" / "tables" / "table_smoothing_bridge_profiles.csv", dtype={"source_arrangement": str})
    assert set(smoothing["verification_status"]) == {"partial"}
    assert set(smoothing["expected_node_count_status"]) == {"partial_exact_genericity_verified_CAS_pending"}

    for suffix in ("png", "pdf"):
        assert (repo_root() / "paper" / "figures" / f"fig_concurrency_graph_84.{suffix}").exists()
        assert (repo_root() / "paper" / "figures" / f"fig_concurrency_graph_84a.{suffix}").exists()
