"""Extract the CKC Section 6.1 equation index from the source PDF."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.equivariant.ckc_pdf_extraction import (  # noqa: E402
    EXPECTED_RECORD_COUNT,
    build_ckc_equation_index,
)


PDF_PATH = REPO_ROOT / "data" / "raw" / "cynk_kocel_cynk_2026" / "2602.19413v1-cynk-kocel-cynk.pdf"
RAW_OUT = REPO_ROOT / "data" / "raw" / "cynk_kocel_cynk_2026" / "ckc_equation_index_001_455.json"
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "equivariant_spectra"
COVERAGE_OUT = PROCESSED_DIR / "ckc_ingestion_coverage.json"
AUDIT_OUT = PROCESSED_DIR / "ckc_equation_extraction_audit.csv"


def _coverage_payload(index: dict) -> dict:
    records = index["records"]
    warnings = [record for record in records if record["parse_warnings"]]
    fixed = [record for record in records if record["fixed_equation_candidate"]]
    parameterized = [record for record in records if record["has_parameters"]]
    return {
        "source_pdf": str(PDF_PATH),
        "total_expected_records": EXPECTED_RECORD_COUNT,
        "records_loaded": index["records_loaded"],
        "missing_ids": index["missing_ids"],
        "fixed_equation_candidates": len(fixed),
        "fixed_equation_candidate_ids": [record["arrangement_id"] for record in fixed],
        "parameterized_records": len(parameterized),
        "parameterized_record_ids": [record["arrangement_id"] for record in parameterized],
        "records_with_parse_warnings": len(warnings),
        "records_with_parse_warning_ids": [record["arrangement_id"] for record in warnings],
        "validated_records": 0,
        "provisional_records": 0,
        "unvalidated_records": len(records),
        "extraction_timestamp": index["extraction_timestamp"],
        "parser_coverage_complete": index["parser_coverage_complete"],
        "full_validated_dataset_loaded": False,
        "notes": (
            "Raw PDF extraction only. Parser coverage is distinct from validated CKC/HodgeCY ingestion; "
            "extracted records are not validated HodgeCY records."
        ),
    }


def _write_audit(records: list[dict]) -> None:
    AUDIT_OUT.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "arrangement_id",
                "extracted",
                "has_parameters",
                "parameter_names",
                "num_linear_factors",
                "parse_warning",
                "equation_preview",
            ],
        )
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "arrangement_id": record["arrangement_id"],
                    "extracted": record["extraction_status"] in {"extracted", "partial"},
                    "has_parameters": record["has_parameters"],
                    "parameter_names": ",".join(record["parameter_names"]),
                    "num_linear_factors": len(record["linear_factor_texts"]),
                    "parse_warning": "; ".join(record["parse_warnings"]),
                    "equation_preview": record["normalized_equation_text"][:120],
                }
            )


def main() -> int:
    if not PDF_PATH.exists():
        print(f"Missing CKC source PDF: {PDF_PATH}")
        print("Copy it manually from: /mnt/data/2602.19413v1-cynk-kocel-cynk.pdf")
        print("Expected destination: data/raw/cynk_kocel_cynk_2026/2602.19413v1-cynk-kocel-cynk.pdf")
        return 0

    index = build_ckc_equation_index(PDF_PATH)
    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    RAW_OUT.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    coverage = _coverage_payload(index)
    COVERAGE_OUT.write_text(json.dumps(coverage, indent=2), encoding="utf-8")
    _write_audit(index["records"])

    print("CKC Section 6.1 extraction complete:")
    print(f"- source PDF: {PDF_PATH}")
    print(f"- records_loaded: {coverage['records_loaded']}")
    print(f"- missing_ids: {coverage['missing_ids']}")
    print(f"- fixed_equation_candidates: {coverage['fixed_equation_candidates']}")
    print(f"- parameterized_records: {coverage['parameterized_records']}")
    print(f"- records_with_parse_warnings: {coverage['records_with_parse_warnings']}")
    print(f"- output JSON: {RAW_OUT}")
    print(f"- coverage JSON: {COVERAGE_OUT}")
    print(f"- audit CSV: {AUDIT_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
