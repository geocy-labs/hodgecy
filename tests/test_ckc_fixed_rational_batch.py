from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "processed" / "equivariant_spectra" / "ckc_fixed_rational_batch"


def test_ckc_fixed_rational_batch_runs_and_writes_outputs() -> None:
    subprocess.run([sys.executable, "scripts/validate_ckc_fixed_rational_batch.py"], cwd=ROOT, check=True)

    expected = [
        OUT_DIR / "ckc_fixed_rational_spectrum_summary.csv",
        OUT_DIR / "ckc_fixed_rational_spectra.json",
        OUT_DIR / "ckc_fixed_rational_clusters.json",
        OUT_DIR / "ckc_fixed_rational_differentiating_pairs.csv",
        OUT_DIR / "ckc_fixed_rational_validation_report.json",
        ROOT / "paper" / "tables" / "table_ckc_fixed_rational_spectrum_summary.csv",
        ROOT / "paper" / "tables" / "table_ckc_fixed_rational_spectrum_summary.tex",
        ROOT / "paper" / "tables" / "table_ckc_fixed_rational_clusters.csv",
        ROOT / "paper" / "tables" / "table_ckc_fixed_rational_clusters.tex",
        ROOT / "paper" / "tables" / "table_ckc_fixed_rational_differentiating_pairs.csv",
        ROOT / "paper" / "tables" / "table_ckc_fixed_rational_differentiating_pairs.tex",
    ]
    for path in expected:
        assert path.exists()


def test_ckc_fixed_rational_batch_statuses_are_conservative() -> None:
    report = json.loads((OUT_DIR / "ckc_fixed_rational_validation_report.json").read_text(encoding="utf-8"))
    assert report["rational_fixed_candidates_attempted"] == ["1", "3", "19", "32", "69", "93", "238", "239", "240", "241", "245"]
    assert sorted(report["validated_combinatorial"]) == sorted(report["rational_fixed_candidates_attempted"])
    assert report["failed"] == []
    assert report["skipped_algebraic"] == ["452", "453"]

    index_path = ROOT / "data" / "raw" / "cynk_kocel_cynk_2026" / "ckc_equation_index_001_455.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert all(record["validation_status"] == "unvalidated" for record in index["records"])


def test_ckc_fixed_rational_batch_preserves_control_pair_and_smoothing_statuses() -> None:
    control_path = ROOT / "data" / "raw" / "cynk_kocel_cynk_2026" / "control_triple_83_84_84a.json"
    control = json.loads(control_path.read_text(encoding="utf-8"))
    by_id = {str(record["arrangement_id"]): record for record in control["records"]}
    assert by_id["84"]["representative_status"] == "validated"
    assert by_id["84a"]["representative_status"] == "validated"

    for arrangement_id in ("84", "84a"):
        smoothing_path = ROOT / "data" / "processed" / f"smoothing_verification_{arrangement_id}.json"
        payload = json.loads(smoothing_path.read_text(encoding="utf-8"))
        assert payload["verification_status"] == "degree112_certified"
