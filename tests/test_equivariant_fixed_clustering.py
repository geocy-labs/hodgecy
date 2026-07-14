from __future__ import annotations

import csv
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_fixed_equation_clustering_outputs_identify_84_84a_witness() -> None:
    subprocess.run([sys.executable, "scripts/cluster_equivariant_spectra_fixed_equations.py"], cwd=ROOT, check=True)

    summary_path = ROOT / "data" / "processed" / "equivariant_spectra" / "fixed_equation_equivariant_spectrum_summary.csv"
    clusters_path = ROOT / "data" / "processed" / "equivariant_spectra" / "fixed_equation_equivariant_clusters.json"
    pairs_path = ROOT / "data" / "processed" / "equivariant_spectra" / "fixed_equation_equivariant_differentiating_pairs.csv"
    paper_pairs_path = ROOT / "paper" / "tables" / "table_fixed_equation_equivariant_differentiating_pairs.tex"

    assert summary_path.exists()
    assert clusters_path.exists()
    assert pairs_path.exists()
    assert paper_pairs_path.exists()

    with summary_path.open(newline="", encoding="utf-8") as handle:
        summary_rows = list(csv.DictReader(handle))
    assert [row["arrangement_id"] for row in summary_rows] == ["84", "84a"]
    assert "83" not in {row["arrangement_id"] for row in summary_rows}

    payload = json.loads(clusters_path.read_text(encoding="utf-8"))
    assert payload["coverage"]["fixed_non_parameterized_records"] == 2
    assert payload["coverage"]["skipped_records"][0]["arrangement_id"] == "83"
    assert payload["clusters"][0]["members"] == ["84", "84a"]
    assert payload["clusters"][0]["equivariant_data_varies"] is True

    with pairs_path.open(newline="", encoding="utf-8") as handle:
        pair_rows = list(csv.DictReader(handle))
    assert len(pair_rows) == 1
    pair = pair_rows[0]
    assert pair["left_arrangement"] == "84"
    assert pair["right_arrangement"] == "84a"
    assert pair["shared_local_inventory"] == "p3=16;p4_0=10;p4_1=0;p5_0=0;p5_1=0;p5_2=0;l3=0"
    assert pair["shared_hodge"] == "h12=0;h11=40;euler=80"
    assert pair["left_automorphism_group_order"] == "6"
    assert pair["right_automorphism_group_order"] == "24"
    assert pair["left_rank_F2"] == "23"
    assert pair["right_rank_F2"] == "21"
    assert "smith_normal_form" in pair["differences"]


def test_fixed_equation_clustering_does_not_change_smoothing_statuses() -> None:
    for arrangement_id in ("84", "84a"):
        path = ROOT / "data" / "processed" / f"smoothing_verification_{arrangement_id}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["verification_status"] == "degree112_certified"
