from __future__ import annotations

import csv
import json
from pathlib import Path
import subprocess
import sys

from hodgecy.defects import build_smoothing_bridge_defect_queue


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_smoothing_bridge_examples_exist_for_84_and_84a() -> None:
    path = repo_root() / "data" / "raw" / "smoothing_bridge_examples.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert {row["source_arrangement"] for row in payload} == {"84", "84a"}


def test_build_smoothing_bridge_defect_queue_has_two_rows() -> None:
    frame = build_smoothing_bridge_defect_queue()
    assert len(frame) == 2
    assert set(frame["example_id"]) == {"smoothing_bridge_84", "smoothing_bridge_84a"}
    assert set(frame["critical_degree_status"]) == {"needs_literature_verification"}
    assert set(frame["defect_status"]) == {"not_computed"}


def test_verified_defect_results_has_headers_and_zero_rows() -> None:
    path = repo_root() / "data" / "processed" / "verified_defect_results.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows == []


def test_build_defect_queue_script_writes_outputs() -> None:
    subprocess.run([sys.executable, "scripts/build_defect_queue.py"], cwd=repo_root(), check=True)
    csv_path = repo_root() / "data" / "processed" / "defect_computation_queue.csv"
    tex_path = repo_root() / "paper" / "tables" / "defect_computation_queue.tex"
    assert csv_path.exists()
    assert tex_path.exists()
