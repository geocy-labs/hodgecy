from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_standalone_driver_completes_with_force() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/verify_smoothing_bridge_84_84a.py", "--force"],
        cwd=repo_root(),
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Verification workflow summary:" in completed.stdout
    assert "84: genericity_verified" in completed.stdout
    assert "84a: genericity_verified" in completed.stdout
