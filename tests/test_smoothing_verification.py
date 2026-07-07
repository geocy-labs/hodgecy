from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from hodgecy.smoothing import ALLOWED_VERIFICATION_STATUSES


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_verification_json_schema_fields_exist() -> None:
    subprocess.run([sys.executable, "scripts/verify_smoothing_bridge_84_84a.py", "--force"], cwd=repo_root(), check=True)
    for arrangement_id in ("84", "84a"):
        path = repo_root() / "data" / "processed" / f"smoothing_verification_{arrangement_id}.json"
        assert path.exists()
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["arrangement"] == arrangement_id
        assert payload["quartic_Q"] == "x^4 + 2*y^4 + 3*z^4 + 5*t^4 + x*y*z*t"
        assert payload["epsilon"] == "1"
        assert payload["verification_status"] in ALLOWED_VERIFICATION_STATUSES
        assert payload["G1_avoids_multiple_points"] is True
        assert payload["G2_squarefree_on_double_lines"] is True
        assert payload["double_line_count"] == 28
        assert payload["expected_node_count"] == 112
