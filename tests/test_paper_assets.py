from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pandas as pd


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_generate_paper_assets_runs_and_writes_outputs(tmp_path: Path) -> None:
    asset_root = tmp_path / "paper_assets"
    env = {**os.environ, "HODGECY_PAPER_ASSET_ROOT": str(asset_root)}

    subprocess.run([sys.executable, "scripts/generate_paper_assets.py"], cwd=repo_root(), env=env, check=True)

    required_table_csvs = [
        "table_tier_a_controls.csv",
        "table_same_hodge_clusters.csv",
        "table_smoothing_bridge_profiles.csv",
        "table_concurrency_comparison_84_84a.csv",
        "table_defect_queue.csv",
    ]
    required_table_texs = [
        "table_tier_a_controls.tex",
        "table_same_hodge_clusters.tex",
        "table_smoothing_bridge_profiles.tex",
        "table_concurrency_comparison_84_84a.tex",
        "table_defect_queue.tex",
    ]
    for name in required_table_csvs:
        assert (asset_root / "paper" / "tables" / name).exists()
    for name in required_table_texs:
        assert (asset_root / "paper" / "tables" / name).exists()

    for name in [
        "fig_hodge_scatter.png",
        "fig_same_hodge_cluster_sizes.png",
        "fig_smoothing_bridge_schematic.png",
        "fig_hodgecy_pipeline.png",
    ]:
        assert (asset_root / "paper" / "figures" / name).exists()

    graph84 = asset_root / "paper" / "figures" / "fig_concurrency_graph_84.png"
    graph84a = asset_root / "paper" / "figures" / "fig_concurrency_graph_84a.png"
    skipped = asset_root / "data" / "processed" / "paper_figures" / "concurrency_graphs_skipped.json"
    assert (graph84.exists() and graph84a.exists()) or skipped.exists()

    tier_a = pd.read_csv(asset_root / "paper" / "tables" / "table_tier_a_controls.csv", dtype={"arrangement": str})
    assert set(tier_a["arrangement"]) == {"83", "84", "84a"}

    smoothing = pd.read_csv(asset_root / "paper" / "tables" / "table_smoothing_bridge_profiles.csv", dtype={"example_id": str})
    assert {"smoothing_bridge_84", "smoothing_bridge_84a"}.issubset(set(smoothing["example_id"]))
