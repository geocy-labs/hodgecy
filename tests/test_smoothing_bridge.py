from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pandas as pd

from hodgecy.arrangements import arrangement_84
from hodgecy.datasets.cynk_meyer import load_table1
from hodgecy.smoothing.bridge import (
    SmoothingBridgeProfile,
    double_line_candidates,
    grouped_double_lines,
    smoothing_bridge_profile,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_double_line_candidates_for_84_has_28_pairs() -> None:
    frame = double_line_candidates(arrangement_84())
    assert len(frame) == 28


def test_grouped_double_lines_returns_dataframe() -> None:
    frame = grouped_double_lines(arrangement_84())
    assert isinstance(frame, pd.DataFrame)


def test_smoothing_bridge_profile_returns_expected_shape() -> None:
    table_row = load_table1().set_index("arrangement").loc["84"].to_dict()
    profile = smoothing_bridge_profile(arrangement_84(), table1_row=table_row)
    assert isinstance(profile, SmoothingBridgeProfile)
    assert profile.expected_nodes_total in {112, None}
    if profile.expected_nodes_total is None:
        assert profile.warnings


def test_smoothing_bridge_script_writes_json() -> None:
    subprocess.run([sys.executable, "scripts/smoothing_bridge_84_84a.py"], cwd=repo_root(), check=True)
    output_path = repo_root() / "data" / "processed" / "smoothing_bridge_84_84a_profiles.json"
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert [row["arrangement_id"] for row in payload] == ["84", "84a"]
