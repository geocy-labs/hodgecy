"""Thin wrappers around external CAS executables used by HodgeCY."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess


def is_executable_available(name: str) -> bool:
    """Return whether the named executable is available on PATH."""
    return shutil.which(name) is not None


def run_macaulay2_script(path: str | Path) -> subprocess.CompletedProcess[str] | None:
    """Run a Macaulay2 script when Macaulay2 is available, otherwise return None."""
    if not is_executable_available("M2"):
        return None
    return subprocess.run(
        ["M2", "--script", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )


def run_singular_script(path: str | Path) -> subprocess.CompletedProcess[str] | None:
    """Run a Singular script when Singular is available, otherwise return None."""
    if not is_executable_available("Singular"):
        return None
    return subprocess.run(
        ["Singular", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
