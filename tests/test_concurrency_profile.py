from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from hodgecy.arrangements import arrangement_84, arrangement_84a, build_concurrency_profile


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_profiles_build_for_84_and_84a() -> None:
    profile_84 = build_concurrency_profile(arrangement_84())
    profile_84a = build_concurrency_profile(arrangement_84a())
    assert profile_84.arrangement_id == "84"
    assert profile_84a.arrangement_id == "84a"


def test_detected_counts_match_table1_for_84_and_84a() -> None:
    profile_84 = build_concurrency_profile(arrangement_84())
    profile_84a = build_concurrency_profile(arrangement_84a())
    assert profile_84.p3_count == 16
    assert profile_84a.p3_count == 16
    assert profile_84.p4_count == 10
    assert profile_84a.p4_count == 10
    assert profile_84.double_line_count == 28
    assert profile_84a.double_line_count == 28


def test_line_profile_counts_are_json_safe() -> None:
    payload = json.dumps(build_concurrency_profile(arrangement_84()).line_profile_counts)
    assert isinstance(payload, str)


def test_script_writes_comparison_json() -> None:
    subprocess.run([sys.executable, "scripts/build_concurrency_profiles_84_84a.py"], cwd=repo_root(), check=True)
    output_path = repo_root() / "data" / "processed" / "concurrency_comparison_84_84a.json"
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "conclusion" in payload
