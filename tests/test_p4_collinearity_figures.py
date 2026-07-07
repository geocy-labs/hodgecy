from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pandas as pd


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_p4_collinearity_outputs_match_expected_degree_sequences() -> None:
    subprocess.run([sys.executable, "scripts/generate_paper_assets.py"], cwd=repo_root(), check=True)
    certificate = pd.read_csv(repo_root() / "data" / "processed" / "p4_collinearity_certificate.csv")
    degree_84 = sorted(certificate.loc[certificate["arrangement"] == "84", "degree"].tolist())
    degree_84a = sorted(certificate.loc[certificate["arrangement"] == "84a", "degree"].tolist())
    assert degree_84 == [6, 8, 8, 8, 8, 8, 8, 8, 8, 8]
    assert degree_84a == [8, 8, 8, 8, 8, 8, 9, 9, 9, 9]
    for suffix in ("png", "pdf"):
        assert (repo_root() / "paper" / "figures" / f"fig_concurrency_graph_84.{suffix}").exists()
        assert (repo_root() / "paper" / "figures" / f"fig_concurrency_graph_84a.{suffix}").exists()
