from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pandas as pd

from hodgecy.datasets.cynk_meyer import load_table1
from hodgecy.experiments.clustering import (
    find_same_hodge_different_singularity,
    find_same_modular_form_different_geometry,
    find_same_singularity_different_hodge,
    find_same_singularity_same_hodge_different_modular_form,
    group_by_hodge_profile,
    group_by_singularity_profile,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _has_pair(frame: pd.DataFrame, left: str, right: str) -> bool:
    pairs = set(zip(frame["arrangement_a"], frame["arrangement_b"]))
    return (left, right) in pairs or (right, left) in pairs


def test_same_singularity_different_hodge_flags_83_84() -> None:
    frame = find_same_singularity_different_hodge(load_table1())
    assert _has_pair(frame, "83", "84")


def test_same_singularity_same_hodge_different_modular_form_flags_84_84a() -> None:
    frame = find_same_singularity_same_hodge_different_modular_form(load_table1())
    assert _has_pair(frame, "84", "84a")


def test_same_hodge_different_singularity_contains_3_51_cluster() -> None:
    clusters = group_by_hodge_profile(load_table1())
    row = clusters.loc[(clusters["h12"] == 3) & (clusters["h11"] == 51) & (clusters["euler"] == 96)].iloc[0]
    assert row["arrangements"] == "12,15,20,29,44"
    frame = find_same_hodge_different_singularity(load_table1())
    assert _has_pair(frame, "12", "15")
    assert _has_pair(frame, "12", "44")


def test_same_modular_form_different_geometry_flags_2_85() -> None:
    frame = find_same_modular_form_different_geometry(load_table1())
    assert _has_pair(frame, "2", "85")


def test_group_by_singularity_profile_contains_83_84_84a_cluster() -> None:
    clusters = group_by_singularity_profile(load_table1())
    row = clusters.loc[clusters["arrangements"] == "83,84,84a"].iloc[0]
    assert row["cluster_size"] == 3


def test_script_writes_processed_outputs_and_flags_examples() -> None:
    subprocess.run([sys.executable, "scripts/find_discriminating_pairs.py"], cwd=repo_root(), check=True)

    processed_dir = repo_root() / "data" / "processed"
    hodge_path = processed_dir / "clusters_by_hodge.csv"
    singularity_path = processed_dir / "clusters_by_singularity.csv"
    pairs_path = processed_dir / "discriminating_pairs.csv"

    assert hodge_path.exists()
    assert singularity_path.exists()
    assert pairs_path.exists()

    pairs = pd.read_csv(pairs_path, dtype={"arrangement_a": str, "arrangement_b": str})
    assert pairs.loc[pairs["flag_83_vs_84"]].shape[0] == 1
    assert pairs.loc[pairs["flag_84_vs_84a"]].shape[0] == 1
    assert pairs.loc[pairs["flag_2_vs_85"]].shape[0] == 1
    assert pairs.loc[pairs["flag_hodge_cluster_3_51"]].shape[0] >= 1
