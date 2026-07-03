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


MANUAL_RIGID_TRUE = {"84a"}
REQUIRED_TABLE1_COLUMNS = [
    "arrangement",
    "p3",
    "p4_0",
    "p4_1",
    "p5_0",
    "p5_1",
    "p5_2",
    "l3",
    "h12",
    "h11",
    "euler",
    "rigid",
    "modular_form",
]
NUMERIC_TABLE1_COLUMNS = [
    "p3",
    "p4_0",
    "p4_1",
    "p5_0",
    "p5_1",
    "p5_2",
    "l3",
    "h12",
    "h11",
    "euler",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _raw_data_path(filename: str) -> Path:
    return _repo_root() / "data" / "raw" / filename


def load_table1() -> pd.DataFrame:
    """Load the Cynk--Meyer Table 1 transcription."""
    frame = pd.read_csv(_raw_data_path("cynk_meyer_table1.csv"), dtype={"arrangement": str})
    frame["arrangement"] = frame["arrangement"].astype(str)
    frame["rigid"] = frame["rigid"].astype(bool)
    return frame


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
    """Validate the Cynk--Meyer Table 1 transcription."""
    missing = [column for column in REQUIRED_TABLE1_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required Cynk--Meyer Table 1 columns: {missing}")

    labels = df["arrangement"].astype(str)
    if labels.duplicated().any():
        duplicates = sorted(labels[labels.duplicated()].unique().tolist())
        raise ValueError(f"Arrangement labels must be unique; duplicates: {duplicates}")

    for column in NUMERIC_TABLE1_COLUMNS:
        if not pd.api.types.is_numeric_dtype(df[column]):
            raise ValueError(f"Column '{column}' must be numeric")

    expected_euler = 2 * (df["h11"] - df["h12"])
    if not expected_euler.equals(df["euler"]):
        bad = df.loc[expected_euler != df["euler"], ["arrangement", "h11", "h12", "euler"]]
        raise ValueError(f"Euler identity failed for rows: {bad.to_dict(orient='records')}")

    expected_rigid = df["h12"].eq(0)
    expected_rigid = expected_rigid | df["arrangement"].astype(str).isin(MANUAL_RIGID_TRUE)
    actual_rigid = df["rigid"].astype(bool)
    if not expected_rigid.equals(actual_rigid):
        bad = df.loc[expected_rigid != actual_rigid, ["arrangement", "h12", "rigid"]]
        raise ValueError(
            "Rigid flag must equal h12 == 0 unless manually overridden; "
            f"mismatches: {bad.to_dict(orient='records')}"
        )

    return True
