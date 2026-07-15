"""PDF extraction helpers for the CKC Section 6.1 equation list."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any


SOURCE_REFERENCE = "Cynk--Kocel--Cynk 2026, Section 6.1"
SOURCE_SECTION = "6.1"
EXPECTED_RECORD_COUNT = 455


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF using an available non-OCR backend."""
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    try:
        import fitz  # type: ignore

        with fitz.open(pdf_path) as document:
            return "\n".join(page.get_text() for page in document)
    except ImportError:
        pass

    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(pdf_path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except ImportError:
        pass

    try:
        from pdfminer.high_level import extract_text  # type: ignore

        return str(extract_text(str(pdf_path)))
    except ImportError as exc:
        raise RuntimeError("No supported PDF text backend found. Install pymupdf, pypdf, or pdfminer.six.") from exc


def extract_section_6_1_text(full_text: str) -> str:
    """Return the Section 6.1 Equations block from extracted PDF text."""
    start_match = re.search(r"6\.1\.?\s*Equations\.?", full_text, flags=re.IGNORECASE)
    if not start_match:
        raise ValueError("Could not locate Section 6.1 Equations in extracted text.")
    end_match = re.search(r"6\.2\.?\s*Magma\s+code\.?", full_text[start_match.end() :], flags=re.IGNORECASE)
    if not end_match:
        raise ValueError("Could not locate Section 6.2 boundary after Section 6.1.")
    return full_text[start_match.end() : start_match.end() + end_match.start()]


def normalize_equation_text(equation_text: str) -> str:
    """Normalize spacing and Unicode math glyphs without changing content semantics."""
    text = equation_text
    replacements = {
        "\u2212": "-",
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u00a0": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"A\s+(\d+)", r"A\1", text)
    text = re.sub(r"\s+", "", text)
    return text


def detect_parameters(equation_text: str) -> list[str]:
    """Return sorted parameter names like A0, A1, etc. found in an equation."""
    normalized = normalize_equation_text(equation_text)
    return sorted(set(re.findall(r"A\d+", normalized)), key=lambda item: int(item[1:]))


def split_linear_factors(equation_text: str) -> list[str]:
    """Split the concatenated CKC product expression into linear-factor strings.

    The PDF text represents products by adjacency, for example ``xy(x+y)z``.
    Parenthesized factors are kept together, while bare coordinate variables
    ``x,y,z,t`` are treated as one factor each.
    """
    text = normalize_equation_text(equation_text)
    factors: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char in "*· ":
            index += 1
            continue
        if char in "xyzt":
            factors.append(char)
            index += 1
            continue
        if char == "(":
            depth = 1
            start = index
            index += 1
            while index < len(text) and depth:
                if text[index] == "(":
                    depth += 1
                elif text[index] == ")":
                    depth -= 1
                index += 1
            factors.append(text[start:index])
            continue
        start = index
        while index < len(text) and text[index] not in "(xyzt":
            index += 1
        if index > start:
            factors.append(text[start:index])
    return [factor for factor in factors if factor]


def _clean_section_text(section_text: str) -> str:
    text = section_text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"CLASSIFICATION OF DOUBLE OCTIC CALABI[-–]YAU THREEFOLDS II\s+\d+", " ", text)
    text = re.sub(r"\d+\s+S\s+LAWOMIR CYNK AND BEATA KOCEL[-–]CYNK", " ", text)
    text = re.sub(r"S\s+LAWOMIR", "SLAWOMIR", text)
    return text


def parse_numbered_equations(section_text: str) -> list[dict[str, Any]]:
    """Parse numbered equation records from Section 6.1 text."""
    cleaned = _clean_section_text(section_text)
    matches = list(re.finditer(r"(?<![A-Za-z0-9])(\d{1,3}):", cleaned))
    records: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        arrangement_id = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(cleaned)
        equation_text = cleaned[start:end].strip()
        equation_text = re.sub(r"\s+", " ", equation_text)
        normalized = normalize_equation_text(equation_text)
        factors = split_linear_factors(equation_text)
        parameters = detect_parameters(equation_text)
        warnings = []
        if not equation_text:
            warnings.append("empty_equation_text")
        if len(factors) != 8:
            warnings.append(f"linear_factor_count={len(factors)}")
        records.append(
            {
                "arrangement_id": arrangement_id,
                "equation_text": equation_text,
                "normalized_equation_text": normalized,
                "linear_factor_texts": factors,
                "has_parameters": bool(parameters),
                "parameter_names": parameters,
                "fixed_equation_candidate": not bool(parameters) and len(factors) == 8,
                "source_section": SOURCE_SECTION,
                "source_reference": SOURCE_REFERENCE,
                "extraction_status": "partial" if warnings else "extracted",
                "validation_status": "unvalidated",
                "parse_warnings": warnings,
                "notes": "Raw PDF extraction record. Validation requires independent incidence and inventory checks.",
            }
        )
    return records


def build_ckc_equation_index(pdf_path: Path) -> dict[str, Any]:
    """Build a JSON-serializable CKC equation index from the source PDF."""
    full_text = extract_text_from_pdf(pdf_path)
    section_text = extract_section_6_1_text(full_text)
    records = parse_numbered_equations(section_text)
    loaded_ids = {int(record["arrangement_id"]) for record in records if record["arrangement_id"].isdigit()}
    missing_ids = [str(index) for index in range(1, EXPECTED_RECORD_COUNT + 1) if index not in loaded_ids]
    return {
        "source_file": str(pdf_path),
        "source_section": SOURCE_SECTION,
        "source_reference": SOURCE_REFERENCE,
        "total_expected_records": EXPECTED_RECORD_COUNT,
        "records_loaded": len(records),
        "missing_ids": missing_ids,
        "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
        "validation_status": "unvalidated",
        "parser_coverage_complete": len(records) == EXPECTED_RECORD_COUNT and not missing_ids,
        "full_validated_dataset_loaded": False,
        "records": [
            {
                **record,
                "source_file": str(pdf_path),
            }
            for record in records
        ],
    }
