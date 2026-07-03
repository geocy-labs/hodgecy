from __future__ import annotations

from pathlib import Path

import pandas as pd

from hodgecy.datasets.cynk_meyer import (
    load_family_equations,
    load_rigid_equations,
    load_table1,
    validate_table1,
)


MODULAR_LABELS = {
    "2": "8k4A",
    "6": "32k4C",
    "23": "64k4A",
    "43": "16k4A",
    "61": "64k4C",
    "84": "6k4A",
    "84a": "12k4A",
    "85": "8k4A",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_raw_dataset_files_exist() -> None:
    raw_dir = repo_root() / "data" / "raw"
    expected = [
        raw_dir / "cynk_meyer_table1.csv",
        raw_dir / "cynk_meyer_rigid_equations.json",
        raw_dir / "cynk_meyer_families.json",
    ]
    for path in expected:
        assert path.exists(), f"Missing expected dataset file: {path}"


def test_load_table1_returns_dataframe() -> None:
    frame = load_table1()
    assert isinstance(frame, pd.DataFrame)
    assert not frame.empty
    assert validate_table1(frame) is True


def test_load_rigid_equations_returns_list() -> None:
    payload = load_rigid_equations()
    assert isinstance(payload, list)
    assert payload
    assert isinstance(payload[0], dict)


def test_load_family_equations_returns_list() -> None:
    payload = load_family_equations()
    assert isinstance(payload, list)
    assert payload
    assert isinstance(payload[0], dict)


def test_table1_row_count_includes_84a() -> None:
    frame = load_table1()
    assert len(frame) == 86


def test_84_and_84a_share_same_numerical_data() -> None:
    frame = load_table1().set_index("arrangement")
    cols = ["p3", "p4_0", "p4_1", "p5_0", "p5_1", "p5_2", "l3", "h12", "h11", "euler", "rigid"]
    assert frame.loc["84", cols].to_dict() == frame.loc["84a", cols].to_dict()
    assert frame.loc["84", "modular_form"] == "6k4A"
    assert frame.loc["84a", "modular_form"] == "12k4A"


def test_83_and_84_have_same_singularity_counts_but_different_hodge_data() -> None:
    frame = load_table1().set_index("arrangement")
    singularity_cols = ["p3", "p4_0", "p4_1", "p5_0", "p5_1", "p5_2", "l3"]
    assert frame.loc["83", singularity_cols].to_dict() == frame.loc["84", singularity_cols].to_dict()
    assert frame.loc["83", "h12"] != frame.loc["84", "h12"]
    assert frame.loc["83", "h11"] != frame.loc["84", "h11"]


def test_modular_form_labels_match_paper_labels() -> None:
    frame = load_table1().set_index("arrangement")
    for arrangement, label in MODULAR_LABELS.items():
        assert frame.loc[arrangement, "modular_form"] == label
    rigid_rows = frame.loc[frame["rigid"]]
    assert set(rigid_rows.index) == set(MODULAR_LABELS)
