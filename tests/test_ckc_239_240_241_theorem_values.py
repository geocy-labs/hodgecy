from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
BATCH_DIR = ROOT / "data" / "processed" / "equivariant_spectra" / "ckc_fixed_rational_batch"
TARGET_IDS = {"239", "240", "241"}
EXPECTED_INVENTORY = {
    "p3": 16,
    "p4_0": 10,
    "p4_1": 0,
    "p5_0": 0,
    "p5_1": 0,
    "p5_2": 0,
    "l3": 0,
}


def test_ckc_239_240_241_theorem_values_exist_and_separate() -> None:
    subprocess.run([sys.executable, "scripts/build_ckc_239_240_241_theorem_values.py"], cwd=ROOT, check=True)

    spectra_path = BATCH_DIR / "ckc_fixed_rational_spectra.json"
    values_path = BATCH_DIR / "ckc_239_240_241_theorem_values.json"
    summary_path = BATCH_DIR / "theorem_summary_239_240_241.json"
    table_csv = ROOT / "paper" / "tables" / "table_ckc_239_240_241_equivariant_signature.csv"
    table_tex = ROOT / "paper" / "tables" / "table_ckc_239_240_241_equivariant_signature.tex"

    assert values_path.exists()
    assert summary_path.exists()
    assert table_csv.exists()
    assert table_tex.exists()

    spectra_payload = json.loads(spectra_path.read_text(encoding="utf-8"))
    records = {item["arrangement_id"]: item for item in spectra_payload["spectra"] if item["arrangement_id"] in TARGET_IDS}
    assert set(records) == TARGET_IDS
    for item in records.values():
        assert item["computed_inventory"] == EXPECTED_INVENTORY

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["same_inventory"] is True
    assert summary["shared_inventory"] == "p3=16,p4_0=10,p4_1=0,p5_0=0,p5_1=0,p5_2=0,l3=0"
    assert summary["pairwise_equivariant_signatures_all_equal"] is False
    assert any(summary["differentiating_fields"].values())
