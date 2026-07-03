from __future__ import annotations

import csv
import json
from pathlib import Path
import subprocess
import sys

from hodgecy.profiles import compare_atom_profiles, profile_from_smoothing_bridge


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_profile_from_smoothing_bridge_builds_expected_block_profile() -> None:
    profile = profile_from_smoothing_bridge("84", 112, 28, 4)
    assert profile.block_count == 28
    assert profile.gluing_deficit == 84
    assert len(profile.block_profile or []) == 28
    assert set(profile.block_profile or []) == {4}


def test_compare_atom_profiles_pending_defect_case() -> None:
    profile_a = profile_from_smoothing_bridge("84", 112, 28, 4)
    profile_b = profile_from_smoothing_bridge("84a", 112, 28, 4)
    comparison = compare_atom_profiles(profile_a, profile_b)
    assert comparison.conclusion == "pending_defect_computation"


def test_comparison_script_writes_json() -> None:
    subprocess.run([sys.executable, "scripts/build_smoothing_bridge_atom_profiles.py"], cwd=repo_root(), check=True)
    subprocess.run([sys.executable, "scripts/compare_smoothing_bridge_84_84a.py"], cwd=repo_root(), check=True)
    output_path = repo_root() / "data" / "processed" / "comparison_smoothing_bridge_84_84a.json"
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["comparison_id"] == "smoothing_bridge_84_vs_smoothing_bridge_84a"


def test_defect_computation_queue_contains_smoothing_bridge_examples() -> None:
    queue_path = repo_root() / "data" / "processed" / "defect_computation_queue.csv"
    with queue_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["example_id"] for row in rows} == {"smoothing_bridge_84", "smoothing_bridge_84a"}
