from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from hodgecy.arrangements import arrangement_84, arrangement_84a
from hodgecy.smoothing import build_smoothing_verification


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_smoothing_genericity_checks_pass_for_84_and_84a() -> None:
    for arrangement in (arrangement_84(), arrangement_84a()):
        record = build_smoothing_verification(arrangement)
        assert record.q_avoids_all_multiple_points is True
        assert record.all_double_lines_have_four_simple_zeros is True
        assert record.overall_status == "partial"
        assert record.singular_locus_status == "partial"
        assert record.hessian_status == "partial"


def test_smoothing_verification_script_writes_expected_outputs() -> None:
    subprocess.run([sys.executable, "scripts/verify_smoothing_bridge_84_84a.py"], cwd=repo_root(), check=True)
    for arrangement_id in ("84", "84a"):
        path = repo_root() / "data" / "processed" / f"smoothing_verification_{arrangement_id}.json"
        assert path.exists()
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["source_arrangement"] == arrangement_id
        assert payload["q_avoids_all_multiple_points"] is True
        assert payload["all_double_lines_have_four_simple_zeros"] is True
    assert (repo_root() / "data" / "processed" / "smoothing_verification_summary.csv").exists()
