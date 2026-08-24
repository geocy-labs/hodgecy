from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_standalone_driver_completes_with_force(tmp_path: Path) -> None:
    processed_root = tmp_path / "data" / "processed"
    env = {**os.environ, "HODGECY_PAPER_ASSET_ROOT": str(tmp_path)}

    completed = subprocess.run(
        [sys.executable, "scripts/verify_smoothing_bridge_84_84a.py", "--force", "--out-dir", str(processed_root)],
        cwd=repo_root(),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Verification workflow summary:" in completed.stdout
    assert "84: degree112_certified" in completed.stdout
    assert "84a: degree112_certified" in completed.stdout
