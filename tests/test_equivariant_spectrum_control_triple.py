from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pandas as pd


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_control_triple_script_writes_outputs_without_changing_smoothing_statuses() -> None:
    subprocess.run([sys.executable, "scripts/compute_equivariant_spectrum_control_triple.py"], cwd=repo_root(), check=True)
    out_dir = repo_root() / "data" / "processed" / "equivariant_spectra"
    for arrangement_id in ("83", "84", "84a"):
        assert (out_dir / f"hodgecy_equivariant_spectrum_{arrangement_id}.json").exists()
    assert (out_dir / "hodgecy_equivariant_spectrum_control_triple_summary.csv").exists()

    for table_name in (
        "table_equivariant_spectrum_control_triple.csv",
        "table_gluing_complex_control_triple.csv",
        "table_automorphism_orbits_control_triple.csv",
    ):
        assert (repo_root() / "paper" / "tables" / table_name).exists()

    for arrangement_id in ("84", "84a"):
        payload = json.loads((repo_root() / "data" / "processed" / f"smoothing_verification_{arrangement_id}.json").read_text(encoding="utf-8"))
        assert payload["verification_status"] == "degree112_certified"


def test_control_triple_summary_contains_expected_values() -> None:
    summary_path = repo_root() / "data" / "processed" / "equivariant_spectra" / "hodgecy_equivariant_spectrum_control_triple_summary.csv"
    if not summary_path.exists():
        subprocess.run([sys.executable, "scripts/compute_equivariant_spectrum_control_triple.py"], cwd=repo_root(), check=True)
    summary = pd.read_csv(summary_path, dtype={"arrangement_id": str})
    by_id = {row.arrangement_id: row for row in summary.itertuples(index=False)}
    assert "representative_status" in summary.columns
    assert by_id["83"].representative_status == "provisional"
    assert by_id["84"].representative_status == "validated"
    assert by_id["84a"].representative_status == "validated"
    assert by_id["84"].incidence_table_size == 10
    assert by_id["84"].automorphism_group_order == 6
    assert by_id["84"].gluing_matrix_shape == "26x28"
    assert by_id["84a"].automorphism_group_order == 24
    assert by_id["83"].gluing_matrix_shape == "31x25"


def test_existing_p4_profile_data_remain_unchanged() -> None:
    spectrum_84 = json.loads((repo_root() / "data" / "processed" / "equivariant_spectra" / "hodgecy_equivariant_spectrum_84.json").read_text(encoding="utf-8"))
    spectrum_84a = json.loads((repo_root() / "data" / "processed" / "equivariant_spectra" / "hodgecy_equivariant_spectrum_84a.json").read_text(encoding="utf-8"))
    assert spectrum_84["p4_graph_summary_if_available"]["edge_count"] == 39
    assert spectrum_84["p4_graph_summary_if_available"]["degree_sequence"] == "[6,8^9]"
    assert spectrum_84a["p4_graph_summary_if_available"]["edge_count"] == 42
    assert spectrum_84a["p4_graph_summary_if_available"]["degree_sequence"] == "[8^6,9^4]"
    assert spectrum_84["character_kernel_cokernel"]["status"] == "not_computed"


def test_83_provenance_and_inventory_status_are_explicit() -> None:
    spectrum_83 = json.loads((repo_root() / "data" / "processed" / "equivariant_spectra" / "hodgecy_equivariant_spectrum_83.json").read_text(encoding="utf-8"))
    assert spectrum_83["representative_status"] == "provisional"
    assert spectrum_83["inventory_matches_expected"] is False
    assert spectrum_83["expected_cynk_inventory"] == {
        "p3": 16,
        "p4_0": 10,
        "p4_1": 0,
        "p5_0": 0,
        "p5_1": 0,
        "p5_2": 0,
        "l3": 0,
    }
    assert spectrum_83["computed_inventory"] == {
        "p3": 26,
        "p4_0": 3,
        "p4_1": 0,
        "p5_0": 2,
        "p5_1": 0,
        "p5_2": 0,
        "l3": 1,
    }
    assert spectrum_83["source_equation"].startswith("x(A0x + A1y)")
    assert spectrum_83["parameter_choice"] == {"A0": "1", "A1": "2", "A2": "3", "A3": "5"}


def test_manuscript_facing_tables_do_not_present_83_as_final() -> None:
    table = pd.read_csv(repo_root() / "paper" / "tables" / "table_equivariant_spectrum_control_triple.csv", dtype={"arrangement_id": str})
    row83 = table.loc[table["arrangement_id"] == "83"].iloc[0]
    assert row83["representative_status"] == "provisional"
    assert row83["inventory_matches_expected"] == False
