from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pandas as pd

from hodgecy.arrangements import arrangement_84, arrangement_84a, build_concurrency_profile, build_p4_collinearity_graph


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_p4_collinearity_graph_invariants_match_expected_profiles() -> None:
    graph_84 = build_p4_collinearity_graph(build_concurrency_profile(arrangement_84()))
    graph_84a = build_p4_collinearity_graph(build_concurrency_profile(arrangement_84a()))
    assert graph_84.number_of_nodes() == 10
    assert graph_84.number_of_edges() == 39
    assert sorted((degree for _, degree in graph_84.degree()), reverse=True) == [8, 8, 8, 8, 8, 8, 8, 8, 8, 6]
    assert graph_84a.number_of_nodes() == 10
    assert graph_84a.number_of_edges() == 42
    assert sorted((degree for _, degree in graph_84a.degree()), reverse=True) == [9, 9, 9, 9, 8, 8, 8, 8, 8, 8]


def test_generate_paper_assets_writes_p4_certificate() -> None:
    subprocess.run([sys.executable, "scripts/generate_paper_assets.py"], cwd=repo_root(), check=True)
    path = repo_root() / "data" / "processed" / "p4_collinearity_certificate.csv"
    assert path.exists()
    frame = pd.read_csv(path)
    assert len(frame) == 20
    assert set(frame["arrangement"]) == {"84", "84a"}
