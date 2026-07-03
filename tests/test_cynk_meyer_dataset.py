from __future__ import annotations

from pathlib import Path

import pandas as pd

from hodgecy.datasets.cynk_meyer import (
    load_family_equations,
    load_rigid_equations,
    load_table1,
    validate_table1,
)


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
