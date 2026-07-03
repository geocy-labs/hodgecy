from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pandas as pd


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_family_candidate_report_script_creates_expected_rows() -> None:
    subprocess.run([sys.executable, "scripts/report_family_candidates.py"], cwd=repo_root(), check=True)
    output_path = repo_root() / "data" / "processed" / "family_candidates.csv"
    assert output_path.exists()

    frame = pd.read_csv(output_path, dtype={"arrangement": str})
    assert set(frame["arrangement"]) == {"1", "5", "14"}
    assert set(frame["hodgecy_role"]) == {"family_operator_candidate"}
    assert set(frame["nodal_special_fibers_known"]) == {"unknown"}
    assert set(frame["operator_data_needed"]) == {"yes"}
