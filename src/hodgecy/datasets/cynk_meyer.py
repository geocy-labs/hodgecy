"""Cynk--Meyer dataset stubs.

This module provides light-weight loaders for the first HodgeCY research
dataset. It intentionally avoids heavy geometry logic at this stage and only
supplies basic file loading plus schema checks for the transcribed tables.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _raw_data_path(filename: str) -> Path:
    return _repo_root() / "data" / "raw" / filename


def load_table1() -> pd.DataFrame:
    """Load the placeholder transcription for Table 1."""
    return pd.read_csv(_raw_data_path("cynk_meyer_table1.csv"))


def load_rigid_equations() -> list[dict[str, Any]]:
    """Load placeholder rigid double octic equations."""
    with _raw_data_path("cynk_meyer_rigid_equations.json").open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return list(payload)


def load_family_equations() -> list[dict[str, Any]]:
    """Load placeholder family-level double octic equations."""
    with _raw_data_path("cynk_meyer_families.json").open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return list(payload)


def validate_table1(df: pd.DataFrame) -> bool:
    """Check that the placeholder Table 1 transcription has required columns."""
    required = {
        "arrangement_id",
        "label",
        "h11",
        "h12",
        "euler_characteristic",
        "notes",
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing required Cynk--Meyer Table 1 columns: {missing}")
    return True
