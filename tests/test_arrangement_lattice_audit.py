from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pandas as pd

from hodgecy.arrangements import (
    arrangement_84,
    arrangement_84a,
    find_incidence_isomorphisms,
    incidence_isomorphic,
    maximal_incidence_strata,
    plane_matrix,
    subset_rank_table,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_arrangements_have_eight_planes() -> None:
    assert len(arrangement_84().planes) == 8
    assert len(arrangement_84a().planes) == 8


def test_plane_matrix_shape() -> None:
    matrix = plane_matrix(arrangement_84())
    assert matrix.shape == (8, 4)


def test_subset_rank_table_has_full_nonempty_power_set() -> None:
    table = subset_rank_table(arrangement_84())
    assert len(table) == 255


def test_maximal_incidence_strata_returns_dataframe() -> None:
    frame = maximal_incidence_strata(arrangement_84())
    assert isinstance(frame, pd.DataFrame)


def test_incidence_isomorphic_api_shapes() -> None:
    result = incidence_isomorphic(arrangement_84(), arrangement_84a())
    isomorphisms = find_incidence_isomorphisms(arrangement_84(), arrangement_84a(), max_results=3)
    assert isinstance(result, bool)
    assert isinstance(isomorphisms, list)


def test_audit_script_runs_and_writes_summary() -> None:
    subprocess.run([sys.executable, "scripts/audit_lattices_84_84a.py"], cwd=repo_root(), check=True)
    summary_path = repo_root() / "data" / "processed" / "lattice_audit_84_84a_summary.json"
    assert summary_path.exists()
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["arrangement_ids"] == ["84", "84a"]
    assert isinstance(payload["incidence_isomorphic"], bool)
