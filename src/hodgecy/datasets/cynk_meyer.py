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
HODGECY_ROLE_VALUES = {
    "motivational_control",
    "rigid_arithmetic_control",
    "family_operator_candidate",
    "nodal_atom_candidate",
    "unknown",
}
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
    "is_rigid_example",
    "is_h12_one_parameter_family",
    "is_nodal_conifold_candidate",
    "has_modular_form_label",
    "has_explicit_paper_equation",
    "hodgecy_role",
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
    bool_columns = [
        "rigid",
        "is_rigid_example",
        "is_h12_one_parameter_family",
        "is_nodal_conifold_candidate",
        "has_modular_form_label",
        "has_explicit_paper_equation",
    ]
    for column in bool_columns:
        frame[column] = frame[column].astype(bool)
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

    expected_is_rigid_example = actual_rigid
    if not expected_is_rigid_example.equals(df["is_rigid_example"].astype(bool)):
        bad = df.loc[
            expected_is_rigid_example != df["is_rigid_example"].astype(bool),
            ["arrangement", "rigid", "is_rigid_example"],
        ]
        raise ValueError(f"is_rigid_example must mirror rigid rows: {bad.to_dict(orient='records')}")

    expected_one_parameter = df["h12"].eq(1)
    if not expected_one_parameter.equals(df["is_h12_one_parameter_family"].astype(bool)):
        bad = df.loc[
            expected_one_parameter != df["is_h12_one_parameter_family"].astype(bool),
            ["arrangement", "h12", "is_h12_one_parameter_family"],
        ]
        raise ValueError(
            "is_h12_one_parameter_family must match h12 == 1 rows: "
            f"{bad.to_dict(orient='records')}"
        )

    expected_has_modular_form = df["modular_form"].fillna("").astype(str).ne("")
    if not expected_has_modular_form.equals(df["has_modular_form_label"].astype(bool)):
        bad = df.loc[
            expected_has_modular_form != df["has_modular_form_label"].astype(bool),
            ["arrangement", "modular_form", "has_modular_form_label"],
        ]
        raise ValueError(
            "has_modular_form_label must track non-empty modular_form rows: "
            f"{bad.to_dict(orient='records')}"
        )

    expected_explicit_equation = expected_is_rigid_example | expected_one_parameter
    if not expected_explicit_equation.equals(df["has_explicit_paper_equation"].astype(bool)):
        bad = df.loc[
            expected_explicit_equation != df["has_explicit_paper_equation"].astype(bool),
            ["arrangement", "rigid", "h12", "has_explicit_paper_equation"],
        ]
        raise ValueError(
            "has_explicit_paper_equation must match the rigid-or-h12=1 paper cases: "
            f"{bad.to_dict(orient='records')}"
        )

    expected_nodal_candidates = df["arrangement"].astype(str).isin({"83", "84", "84a"})
    if not expected_nodal_candidates.equals(df["is_nodal_conifold_candidate"].astype(bool)):
        bad = df.loc[
            expected_nodal_candidates != df["is_nodal_conifold_candidate"].astype(bool),
            ["arrangement", "is_nodal_conifold_candidate"],
        ]
        raise ValueError(
            "is_nodal_conifold_candidate must flag the 83/84/84a discriminator cases: "
            f"{bad.to_dict(orient='records')}"
        )

    role_series = df["hodgecy_role"].astype(str)
    invalid_roles = sorted(set(role_series) - HODGECY_ROLE_VALUES)
    if invalid_roles:
        raise ValueError(f"Unsupported hodgecy_role values: {invalid_roles}")

    expected_role = pd.Series("unknown", index=df.index, dtype="object")
    expected_role = expected_role.mask(expected_one_parameter, "family_operator_candidate")
    expected_role = expected_role.mask(expected_nodal_candidates, "nodal_atom_candidate")
    expected_role = expected_role.mask(expected_has_modular_form, "rigid_arithmetic_control")
    expected_role = expected_role.mask(
        expected_is_rigid_example & ~expected_has_modular_form,
        "motivational_control",
    )
    mismatched_role = expected_role.ne(role_series)
    if mismatched_role.any():
        bad = df.loc[mismatched_role, ["arrangement", "hodgecy_role"]].copy()
        bad["expected_role"] = expected_role.loc[mismatched_role].values
        raise ValueError(f"hodgecy_role mismatch rows: {bad.to_dict(orient='records')}")

    return True
