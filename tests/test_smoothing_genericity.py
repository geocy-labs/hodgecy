from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from hodgecy.arrangements import arrangement_84, arrangement_84a
from hodgecy.smoothing import ALLOWED_VERIFICATION_STATUSES, build_smoothing_verification


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_smoothing_genericity_checks_pass_for_84_and_84a() -> None:
    for arrangement in (arrangement_84(), arrangement_84a()):
        record = build_smoothing_verification(arrangement)
        assert record.G1_avoids_multiple_points is True
        assert record.G2_squarefree_on_double_lines is True
        assert record.double_line_count == 28
        assert record.expected_node_count == 112
        assert record.verification_status == "genericity_verified"
        assert record.verification_status in ALLOWED_VERIFICATION_STATUSES
        assert record.singular_locus_status == "queued"
        assert record.hessian_status == "queued"


def test_smoothing_verification_script_writes_expected_outputs() -> None:
    subprocess.run([sys.executable, "scripts/verify_smoothing_bridge_84_84a.py", "--force"], cwd=repo_root(), check=True)
    for arrangement_id in ("84", "84a"):
        path = repo_root() / "data" / "processed" / f"smoothing_verification_{arrangement_id}.json"
        assert path.exists()
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["arrangement"] == arrangement_id
        assert payload["G1_avoids_multiple_points"] is True
        assert payload["G2_squarefree_on_double_lines"] is True
        assert payload["double_line_count"] == 28
        assert payload["expected_node_count"] == 112
        assert payload["verification_status"] in ALLOWED_VERIFICATION_STATUSES
    assert (repo_root() / "data" / "processed" / "smoothing_verification_summary.csv").exists()
