from __future__ import annotations

import csv
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "processed" / "equivariant_spectra" / "fixed_equation_batch_001"


def test_fixed_equation_batch_001_outputs_are_additive_and_scoped() -> None:
    subprocess.run([sys.executable, "scripts/compute_fixed_equation_batch_001.py"], cwd=ROOT, check=True)

    expected_outputs = [
        OUT_DIR / "batch_manifest.json",
        OUT_DIR / "spectrum_summary.csv",
        OUT_DIR / "clusters_by_inventory_hodge.csv",
        OUT_DIR / "clusters_by_inventory_hodge.json",
        OUT_DIR / "differentiating_pairs_same_inventory_hodge.csv",
        OUT_DIR / "hodgecy_equivariant_spectrum_84.json",
        OUT_DIR / "hodgecy_equivariant_spectrum_84a.json",
    ]
    for path in expected_outputs:
        assert path.exists()

    manifest = json.loads((OUT_DIR / "batch_manifest.json").read_text(encoding="utf-8"))
    assert manifest["batch_id"] == "fixed_equation_batch_001"
    assert manifest["selected_arrangement_ids"] == ["84", "84a"]
    assert manifest["differentiating_pair_count"] == 1
    assert manifest["skipped_records"][0]["arrangement_id"] == "83"


def test_fixed_equation_batch_001_cluster_separates_84_84a_equivariantly() -> None:
    with (OUT_DIR / "differentiating_pairs_same_inventory_hodge.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    row = rows[0]
    assert row["left_arrangement"] == "84"
    assert row["right_arrangement"] == "84a"
    assert row["shared_local_inventory"] == "p3=16;p4_0=10;p4_1=0;p5_0=0;p5_1=0;p5_2=0;l3=0"
    assert row["shared_hodge"] == "h12=0;h11=40;euler=80"
    assert row["left_automorphism_group_order"] == "6"
    assert row["right_automorphism_group_order"] == "24"
    assert row["left_rank_Q"] == "26"
    assert row["right_rank_Q"] == "26"
    assert row["left_rank_F2"] == "23"
    assert row["right_rank_F2"] == "21"
    assert "smith_normal_form" in row["differences"]


def test_fixed_equation_batch_001_preserves_smoothing_statuses() -> None:
    for arrangement_id in ("84", "84a"):
        path = ROOT / "data" / "processed" / f"smoothing_verification_{arrangement_id}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["verification_status"] == "degree112_certified"
