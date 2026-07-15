from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "data" / "raw" / "cynk_kocel_cynk_2026" / "2602.19413v1-cynk-kocel-cynk.pdf"
INDEX_PATH = ROOT / "data" / "raw" / "cynk_kocel_cynk_2026" / "ckc_equation_index_001_455.json"
COVERAGE_PATH = ROOT / "data" / "processed" / "equivariant_spectra" / "ckc_ingestion_coverage.json"
AUDIT_PATH = ROOT / "data" / "processed" / "equivariant_spectra" / "ckc_equation_extraction_audit.csv"


def test_ckc_pdf_extraction_script_outputs_raw_index_when_pdf_present() -> None:
    if not PDF_PATH.exists():
        pytest.skip("CKC source PDF is not present in the local raw data folder.")

    subprocess.run([sys.executable, "scripts/extract_ckc_equation_index_from_pdf.py"], cwd=ROOT, check=True)

    assert INDEX_PATH.exists()
    assert COVERAGE_PATH.exists()
    assert AUDIT_PATH.exists()

    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    coverage = json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))

    assert coverage["records_loaded"] == len(index["records"])
    assert coverage["total_expected_records"] == 455
    if coverage["records_loaded"] < 455:
        assert coverage["missing_ids"]
        assert coverage["parser_coverage_complete"] is False
    else:
        assert coverage["missing_ids"] == []
        assert coverage["parser_coverage_complete"] is True
    assert coverage["full_validated_dataset_loaded"] is False

    assert all(record["validation_status"] == "unvalidated" for record in index["records"])
    assert coverage["validated_records"] == 0
    assert coverage["unvalidated_records"] == coverage["records_loaded"]


def test_ckc_raw_index_does_not_overwrite_validated_control_pair() -> None:
    control_path = ROOT / "data" / "raw" / "cynk_kocel_cynk_2026" / "control_triple_83_84_84a.json"
    control = json.loads(control_path.read_text(encoding="utf-8"))
    by_id = {str(record["arrangement_id"]): record for record in control["records"]}

    assert by_id["84"]["representative_status"] == "validated"
    assert by_id["84a"]["representative_status"] == "validated"
    assert by_id["84"]["parameter_status"] == "fixed_representative"
    assert by_id["84a"]["parameter_status"] == "fixed_representative"

    for arrangement_id in ("84", "84a"):
        smoothing_path = ROOT / "data" / "processed" / f"smoothing_verification_{arrangement_id}.json"
        payload = json.loads(smoothing_path.read_text(encoding="utf-8"))
        assert payload["verification_status"] == "degree112_certified"
