"""Staged CKC records and generic incidence reconstruction from authoritative raw."""

from __future__ import annotations

import csv
import json
from itertools import combinations
from pathlib import Path
import re
from typing import Any

import pandas as pd
import sympy as sp

from hodgecy.equivariant import (
    incidence_table_from_linear_forms,
    is_identically_zero,
    parse_linear_factor_text,
    singular_strata_from_incidence_table,
    source_complex_from_incidence,
)
from hodgecy.research.ckc_authoritative_raw_ingest import EXPECTED_CKC_IDS

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_RELATIVE = Path("raw") / "cynk_kocel_cynk_2026" / "authoritative"
OUT_ROOT = REPO_ROOT / "research_outputs" / "hodgecy_ii" / "ckc_authoritative_staging"
INVENTORY_KEYS = ("p3", "p4_0", "p4_1", "p5_0", "p5_1", "p5_2", "l3")


def run_authoritative_staging(data_root: str | Path, *, output_root: str | Path = OUT_ROOT) -> dict[str, Any]:
    data_root = Path(data_root)
    raw_root = data_root / RAW_RELATIVE
    out_root = Path(output_root)
    out_root.mkdir(parents=True, exist_ok=True)
    mismatch_dir = out_root / "remaining_mismatch_dossiers"
    mismatch_dir.mkdir(parents=True, exist_ok=True)
    for stale in mismatch_dir.glob("ckc_*_mismatch.json"):
        stale.unlink()

    print("loading authoritative raw")
    raw = load_authoritative_raw(raw_root)
    print("loading expected inventory and historical payload")
    expected = load_expected_inventory()
    historical = load_historical_payload()
    print("staging parameter conditions")
    staged_conditions = stage_parameter_conditions(raw["parameter_conditions"])
    print("building staged records")
    staged_records, parse_audit = build_staged_records(raw, expected, historical, staged_conditions)
    print("refining historical discrepancies")
    refined = refine_historical_discrepancies(staged_records, historical)
    print("reconstructing generic incidence")
    incidence_rows, incidence_payloads, coverage_rows, mismatch_rows = reconstruct_incidence(staged_records)
    print("writing outputs")
    write_outputs(out_root, staged_records, staged_conditions, parse_audit, refined, incidence_rows, incidence_payloads, coverage_rows)
    for row in mismatch_rows:
        write_json(mismatch_dir / f"ckc_{int(row['arrangement_id']):03d}_mismatch.json", row)
    summary = build_summary(staged_records, refined, incidence_rows, coverage_rows, mismatch_rows)
    write_reports(out_root, summary, mismatch_rows)
    return summary


def load_authoritative_raw(raw_root: Path) -> dict[str, Any]:
    structured = raw_root / "structured_raw"
    return {
        "pages": read_jsonl(structured / "ckc_pdf_pages.jsonl"),
        "source_files": read_jsonl(structured / "ckc_source_files.jsonl"),
        "tex_blocks": read_jsonl(structured / "ckc_tex_blocks.jsonl"),
        "tables": read_jsonl(structured / "ckc_tables.jsonl"),
        "equations": read_jsonl(structured / "ckc_arrangement_equations.jsonl"),
        "parameter_conditions": read_jsonl(structured / "ckc_parameter_conditions.jsonl"),
        "incidence_blocks": read_jsonl(structured / "ckc_classification_incidence_blocks.jsonl"),
        "code_blocks": read_jsonl(structured / "ckc_raw_code_blocks.jsonl"),
    }


def load_expected_inventory() -> dict[str, dict[str, Any]]:
    path = REPO_ROOT / "research_outputs" / "hodgecy_ii" / "source_assembly_blocker_elimination" / "all_456_source_assemblies.parquet"
    frame = pd.read_parquet(path)
    expected: dict[str, dict[str, Any]] = {}
    for row in frame.to_dict("records"):
        arrangement_id = str(row["presentation_id"])
        expected[arrangement_id] = {
            "inventory": parse_jsonish(row.get("local_inventory")),
            "hodge": parse_jsonish(row.get("hodge")),
            "inventory_provenance": "authoritative_tex_forgotten_table" if arrangement_id in {"451", "452", "453", "454", "455"} else "existing_hodgecy_processed_ckc_inventory",
            "hodge_signature": row.get("hodge_signature"),
            "existing_assembly_status": row.get("assembly_computation_status"),
            "existing_matrix_path": row.get("matrix_path"),
            "existing_matrix_hash": row.get("matrix_hash"),
        }
    return expected


def load_historical_payload() -> dict[str, dict[str, Any]]:
    path = REPO_ROOT / "data" / "raw" / "cynk_kocel_cynk_2026" / "ckc_equation_index_001_455.json"
    payload = read_json(path)
    return {str(row["arrangement_id"]): row for row in payload["records"]}


def stage_parameter_conditions(raw_conditions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in raw_conditions:
        linked = [str(value) for value in item.get("linked_arrangements") or [] if str(value).isdigit()]
        affected = affected_ids_from_condition(item, linked)
        raw_tex = item.get("raw_tex") or ""
        rows.append(
            {
                "condition_id": item["raw_parameter_condition_id"],
                "raw_tex": raw_tex,
                "normalized_mathematical_form": normalize_tex_math(raw_tex),
                "source_file": item["source_location"]["source_file"],
                "source_lines": item["source_location"]["lines"],
                "section_path": item.get("section_path") or {},
                "scope_type": condition_scope_type(item, linked, affected),
                "affected_ckc_ids": affected,
                "parameter_symbols": sorted(set(re.findall(r"A_\{?\d+\}?|A\d+", raw_tex)), key=parameter_sort_key),
                "equality_constraints": extract_constraints(raw_tex, equality=True),
                "nonvanishing_constraints": extract_constraints(raw_tex, equality=False),
                "excluded_values": extract_excluded_values(raw_tex),
                "field_constraints": extract_field_constraints(raw_tex),
            }
        )
    return rows


def condition_scope_type(item: dict[str, Any], linked: list[str], affected: list[str]) -> str:
    if len(linked) == 1:
        return "single_arrangement"
    if len(linked) > 1 and linked == contiguous_ids(linked):
        return "contiguous_ckc_id_range"
    if len(linked) > 1:
        return "listed_arrangement_ids"
    section = (item.get("section_path") or {}).get("subsection") or (item.get("section_path") or {}).get("section")
    if section:
        return "section_or_subsection"
    return "global_document"


def affected_ids_from_condition(item: dict[str, Any], linked: list[str]) -> list[str]:
    if linked:
        return contiguous_ids(linked)
    return []


def contiguous_ids(values: list[str]) -> list[str]:
    ordered = sorted({int(value) for value in values})
    if not ordered:
        return []
    if ordered == list(range(ordered[0], ordered[-1] + 1)):
        return [str(value) for value in ordered]
    return [str(value) for value in ordered]


def extract_constraints(raw_tex: str, *, equality: bool) -> list[str]:
    text = normalize_tex_math(raw_tex)
    if equality:
        return re.findall(r"[^.;,]*=[^.;,]*", text)
    return re.findall(r"[^.;,]*(?:!=|not=|\\not=|non-zero|nonzero)[^.;,]*", text, flags=re.IGNORECASE)


def extract_excluded_values(raw_tex: str) -> list[str]:
    text = normalize_tex_math(raw_tex)
    return re.findall(r"(?:not=|!=|excluded|exceptional)[^.;]*", text, flags=re.IGNORECASE)


def extract_field_constraints(raw_tex: str) -> list[str]:
    return re.findall(r"\\QQ\[[^\]]+\]|\\mathbb\{Q\}\[[^\]]+\]|quadratic field|Galois", raw_tex, flags=re.IGNORECASE)


def build_staged_records(
    raw: dict[str, Any],
    expected: dict[str, dict[str, Any]],
    historical: dict[str, dict[str, Any]],
    staged_conditions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    equations = {row["arrangement_id"]: row for row in raw["equations"]}
    conditions_by_id: dict[str, list[dict[str, Any]]] = {arrangement_id: [] for arrangement_id in EXPECTED_CKC_IDS}
    for condition in staged_conditions:
        for arrangement_id in condition["affected_ckc_ids"]:
            if arrangement_id in conditions_by_id:
                conditions_by_id[arrangement_id].append(condition)
    records = []
    audit = []
    for arrangement_id in EXPECTED_CKC_IDS:
        equation = equations[arrangement_id]
        parsed = parse_tex_product(equation["normalized_display_text"], arrangement_id=arrangement_id)
        linear_forms = []
        form_errors = []
        for index, factor in enumerate(parsed["canonical_factor_texts"]):
            try:
                parsed_form = parse_linear_factor_text(factor, parameter_names=parameter_names_for(parsed["canonical_factor_texts"]))
                linear_forms.append(
                    {
                        "index": index,
                        "label": f"p{index + 1}",
                        "coefficients": [str(value) for value in parsed_form.coefficients],
                        "equation": factor,
                        "coefficient_domain": parsed_form.coefficient_domain,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                form_errors.append(f"factor_{index + 1}: {exc}")
        coefficient_domain = coefficient_domain_from_forms(linear_forms, parsed["algebraic_constants"], parsed["parameter_symbols"])
        canonical_arrangement = canonical_arrangement_signature(linear_forms) if len(linear_forms) == 8 and not form_errors else None
        expected_row = expected.get(arrangement_id, {})
        condition_refs = [item["condition_id"] for item in conditions_by_id.get(arrangement_id, [])]
        staged = {
            "arrangement_id": arrangement_id,
            "raw_equation_references": [equation["raw_equation_block_id"]],
            "canonical_equation_representation": parsed["canonical_product_text"],
            "canonical_eight_factors": parsed["canonical_factor_texts"],
            "linear_forms": linear_forms,
            "parameter_symbols": parsed["parameter_symbols"],
            "coefficient_domain": coefficient_domain,
            "algebraic_constants": parsed["algebraic_constants"],
            "parameter_condition_references": condition_refs,
            "parameter_condition_scope": sorted({item["scope_type"] for item in conditions_by_id.get(arrangement_id, [])}),
            "classification_incidence_context_references": classification_refs_for(raw["incidence_blocks"], arrangement_id),
            "table_derived_singularity_inventory": expected_row.get("inventory"),
            "table_inventory_provenance": expected_row.get("inventory_provenance"),
            "hodge_values": expected_row.get("hodge"),
            "field_of_definition_statements": field_statement_refs(conditions_by_id.get(arrangement_id, [])),
            "galois_remarks": galois_refs(conditions_by_id.get(arrangement_id, [])),
            "projective_equivalence_remarks": projective_refs(conditions_by_id.get(arrangement_id, [])),
            "magma_code_provenance": code_provenance(raw["code_blocks"]),
            "pdf_page_references": [equation.get("page_number")],
            "tex_source_references": [{"source_file": equation["tex_source_file"], "lines": equation["tex_lines"]}],
            "validation_status": "STAGED_EXACT_8_FACTOR_PARSE" if parsed["ast_status"] == "parsed" and len(linear_forms) == 8 and not form_errors else "STAGED_PARSE_UNRESOLVED",
            "parse_warnings": parsed["parse_warnings"] + form_errors,
            "canonical_arrangement_signature": canonical_arrangement,
            "historical_discrepancy_status": "pending_refined_comparison",
            "historical_payload_factor_count": len((historical.get(arrangement_id) or {}).get("linear_factor_texts") or []),
        }
        records.append(staged)
        audit.append(
            {
                "arrangement_id": arrangement_id,
                "raw_equation": equation["normalized_display_text"],
                "ast_status": parsed["ast_status"],
                "top_level_factor_count": parsed["top_level_factor_count"],
                "canonical_eight_factors": json.dumps(parsed["canonical_factor_texts"], ensure_ascii=False),
                "coefficient_domain": coefficient_domain,
                "parse_warnings": "; ".join(staged["parse_warnings"]),
            }
        )
    return records, audit


def parse_tex_product(raw_equation: str, *, arrangement_id: str = "") -> dict[str, Any]:
    factors = top_level_tex_factors(raw_equation)
    warnings = []
    canonical = []
    for factor in factors:
        text, factor_warnings = tex_factor_to_linear_text(factor)
        warnings.extend(f"{arrangement_id}:{warning}" for warning in factor_warnings)
        canonical.append(text)
    return {
        "ast_status": "parsed" if len(canonical) == 8 else "factor_count_unresolved",
        "top_level_factor_count": len(canonical),
        "canonical_factor_texts": canonical,
        "canonical_product_text": "*".join(canonical),
        "parameter_symbols": sorted(set(re.findall(r"A\d+", " ".join(canonical))), key=parameter_sort_key),
        "algebraic_constants": sorted(set(re.findall(r"sqrt\([^)]+\)", " ".join(canonical)))),
        "parse_warnings": warnings + ([] if len(canonical) == 8 else [f"top_level_factor_count={len(canonical)}"]),
    }


def top_level_tex_factors(text: str) -> list[str]:
    compact = text.strip()
    factors: list[str] = []
    index = 0
    while index < len(compact):
        char = compact[index]
        if char.isspace() or char == "*":
            index += 1
            continue
        if char in "xyzt":
            factors.append(char)
            index += 1
            continue
        if char == "(":
            end, warning = consume_parenthesized(compact, index)
            factors.append(compact[index : end + 1])
            index = end + 1
            continue
        start = index
        while index < len(compact) and compact[index] not in "(xyzt":
            index += 1
        if index > start:
            factors.append(compact[start:index])
    return [factor for factor in factors if factor.strip()]


def consume_parenthesized(text: str, start: int) -> tuple[int, str | None]:
    paren_depth = 0
    brace_depth = 0
    index = start
    while index < len(text):
        char = text[index]
        if char == "\\":
            index += 1
            while index < len(text) and text[index].isalpha():
                index += 1
            continue
        if char == "{":
            brace_depth += 1
        elif char == "}":
            brace_depth = max(0, brace_depth - 1)
        elif brace_depth == 0 and char == "(":
            paren_depth += 1
        elif brace_depth == 0 and char == ")":
            paren_depth -= 1
            if paren_depth == 0:
                return index, None
        index += 1
    return len(text) - 1, "unbalanced_parenthesis"


def tex_factor_to_linear_text(factor: str) -> tuple[str, list[str]]:
    warnings = []
    text = factor.strip()
    text = text.replace("\\left", "").replace("\\right", "")
    text = re.sub(r"A_\{(\d+)\}", r"A\1", text)
    text = re.sub(r"A_(\d+)", r"A\1", text)
    text = replace_tex_sqrt(text)
    text, frac_warnings = replace_tex_fracs(text)
    warnings.extend(frac_warnings)
    if re.search(r"\([^()]*\)[{}]?\s*/\s*\(?2\)?z", text):
        warnings.append("possible_fraction_grouping_typo")
    text = text.replace("{", "").replace("}", "")
    text = text.replace("\\,", "")
    text = re.sub(r"\s+", "", text)
    text = text.replace("^", "**")
    text = re.sub(r"(\d|\))(?=[A-Za-z])", r"\1*", text)
    text = re.sub(r"(?<=[A-Za-z0-9])\(", r"*(", text)
    text = re.sub(r"\)(?=[A-Za-z0-9])", r")*", text)
    text = text.replace("sqrt*(", "sqrt(")
    text = text.replace("+-", "-")
    return text, warnings


def replace_tex_sqrt(text: str) -> str:
    out = []
    index = 0
    while index < len(text):
        if text.startswith("\\sqrt", index):
            index += len("\\sqrt")
            if index < len(text) and text[index] == "{":
                group, index = read_braced(text, index)
                out.append(f"sqrt({group})")
            else:
                out.append("sqrt")
            continue
        out.append(text[index])
        index += 1
    return "".join(out)


def replace_tex_fracs(text: str) -> tuple[str, list[str]]:
    warnings = []
    out = []
    index = 0
    while index < len(text):
        if text.startswith("\\frac", index):
            index += len("\\frac")
            numerator, index = read_tex_argument(text, index)
            denominator, index = read_tex_argument(text, index)
            if numerator.count("(") != numerator.count(")"):
                warnings.append("unbalanced_parenthesis_inside_fraction_argument")
                numerator = balance_fraction_argument(numerator)
            out.append(f"(({numerator})/({denominator}))")
            continue
        out.append(text[index])
        index += 1
    return "".join(out), warnings


def read_tex_argument(text: str, index: int) -> tuple[str, int]:
    while index < len(text) and text[index].isspace():
        index += 1
    if index < len(text) and text[index] == "{":
        return read_braced(text, index)
    if index < len(text):
        return text[index], index + 1
    return "", index


def read_braced(text: str, index: int) -> tuple[str, int]:
    assert text[index] == "{"
    depth = 1
    start = index + 1
    index += 1
    while index < len(text) and depth:
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start:index], index + 1
        index += 1
    return text[start:index], index


def balance_fraction_argument(value: str) -> str:
    if value.count(")") > value.count("("):
        extra = value.count(")") - value.count("(")
        for _ in range(extra):
            value = value.replace(")", "", 1) if value.startswith(")") else value[::-1].replace(")", "", 1)[::-1]
    return value


def parameter_names_for(factors: list[str]) -> tuple[str, ...]:
    return tuple(sorted(set(re.findall(r"A\d+", " ".join(factors))), key=parameter_sort_key))


def coefficient_domain_from_forms(forms: list[dict[str, Any]], algebraic_constants: list[str], parameters: list[str]) -> str:
    domains = {form.get("coefficient_domain") for form in forms}
    if parameters and algebraic_constants:
        return "Qbar(parameters)"
    if parameters:
        return "Q(parameters)"
    if algebraic_constants or "number_field" in domains:
        return "number_field"
    if domains:
        return "Q"
    return "unparsed"


def canonical_arrangement_signature(forms: list[dict[str, Any]]) -> str:
    vectors = [canonical_vector([sp.sympify(value) for value in form["coefficients"]]) for form in forms]
    return json.dumps(sorted(vectors), sort_keys=True)


def canonical_vector(coefficients: list[sp.Expr]) -> list[str]:
    nonzero = [value for value in coefficients if value != 0]
    if not nonzero:
        return [str(sp.Integer(0)) for _ in coefficients]
    scale = nonzero[0]
    normalized = [sp.cancel(value / scale) for value in coefficients]
    return [str(value) for value in normalized]


def classification_refs_for(blocks: list[dict[str, Any]], arrangement_id: str) -> list[str]:
    return [row["record_id"] for row in blocks if arrangement_id in row.get("raw_tex", "")]


def field_statement_refs(conditions: list[dict[str, Any]]) -> list[str]:
    return [row["condition_id"] for row in conditions if row.get("field_constraints")]


def galois_refs(conditions: list[dict[str, Any]]) -> list[str]:
    return [row["condition_id"] for row in conditions if "Galois" in row.get("raw_tex", "")]


def projective_refs(conditions: list[dict[str, Any]]) -> list[str]:
    return [row["condition_id"] for row in conditions if "projective" in row.get("raw_tex", "").lower()]


def code_provenance(code_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "code_block_id": row["code_block_id"],
            "source_file": row["source_file"],
            "source_lines": row["source_lines"],
            "function_definitions": row["function_definitions"],
            "ported_routines": ["IncidenceTable", "MinimalIncidenceTable", "InvariantPermutations", "Singularities", "ArrInvariants"],
            "implementation": "hodgecy.equivariant incidence/source-complex routines",
            "deviations": "Python/SymPy exact linear algebra replaces Magma minors and ideal arithmetic; ArrInvariants deformation/Hilbert-series component is not recomputed in this generic incidence pass.",
        }
        for row in code_blocks
    ]


def refine_historical_discrepancies(staged_records: list[dict[str, Any]], historical: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for record in staged_records:
        arrangement_id = record["arrangement_id"]
        old = historical.get(arrangement_id)
        status = "HISTORICAL_PARSER_ERROR"
        old_signature = None
        old_factor_count = len(old.get("linear_factor_texts") or []) if old else 0
        if record["validation_status"] != "STAGED_EXACT_8_FACTOR_PARSE":
            status = "AUTHORITATIVE_PARSE_UNRESOLVED"
        elif not old or old_factor_count != 8:
            status = "HISTORICAL_PARSER_ERROR"
        elif record["parameter_symbols"]:
            old_params = {str(value) for value in old.get("parameter_names") or []}
            new_params = set(record["parameter_symbols"])
            status = "PARAMETER_RENAMING_DIFFERENCE" if old_params != new_params else "TEXT_ONLY_DIFFERENCE"
        elif record["algebraic_constants"]:
            status = "ALGEBRAIC_CONSTANT_NORMALIZATION_DIFFERENCE"
        elif old and old_factor_count == 8:
            try:
                old_forms = []
                for index, factor in enumerate(old.get("linear_factor_texts") or []):
                    parsed = parse_linear_factor_text(str(factor), parameter_names=tuple(old.get("parameter_names") or []))
                    old_forms.append({"index": index, "coefficients": [str(value) for value in parsed.coefficients]})
                old_signature = canonical_arrangement_signature(old_forms)
                if old_signature == record["canonical_arrangement_signature"]:
                    old_ordered = ordered_signature(old_forms)
                    new_ordered = ordered_signature(record["linear_forms"])
                    status = "EXACT_CANONICAL_MATCH" if old_ordered == new_ordered else "FACTOR_ORDER_DIFFERENCE"
                elif sorted(str(f) for f in old.get("linear_factor_texts") or []) == sorted(record["canonical_eight_factors"]):
                    status = "TEXT_ONLY_DIFFERENCE"
                else:
                    status = "GENUINE_SUBSTANTIVE_DISCREPANCY"
            except Exception:  # noqa: BLE001
                status = "HISTORICAL_PARSER_ERROR"
        rows.append(
            {
                "arrangement_id": arrangement_id,
                "refined_classification": status,
                "historical_factor_count": old_factor_count,
                "authoritative_factor_count": len(record["canonical_eight_factors"]),
                "authoritative_parse_status": record["validation_status"],
                "canonical_signature_match": old_signature == record.get("canonical_arrangement_signature") if old_signature else False,
                "notes": "; ".join(record["parse_warnings"]),
            }
        )
        record["historical_discrepancy_status"] = status
    return rows


def ordered_signature(forms: list[dict[str, Any]]) -> str:
    return json.dumps([canonical_vector([sp.sympify(value) for value in form["coefficients"]]) for form in forms])


def reconstruct_incidence(staged_records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    incidence_rows = []
    incidence_payloads = []
    coverage_rows = []
    mismatch_rows = []
    for row_index, record in enumerate(staged_records, start=1):
        arrangement_id = record["arrangement_id"]
        if row_index == 1 or row_index % 25 == 0:
            print(f"  incidence {row_index}/455 CKC {arrangement_id}", flush=True)
        expected_inventory = record.get("table_derived_singularity_inventory")
        computed_inventory = None
        magma_inventory = None
        geometric_inventory = None
        magma_match = False
        geometric_match = False
        incidence_status = "PARSE_UNRESOLVED"
        exact_ready = False
        payload = None
        notes = list(record.get("parse_warnings") or [])
        if record["validation_status"] == "STAGED_EXACT_8_FACTOR_PARSE":
            forms = materialize_forms(record["linear_forms"])
            try:
                incidence = incidence_table_from_linear_forms_fast(forms)
                magma_strata = singularities_from_incidence_table(incidence)
                magma_inventory = normalize_inventory(magma_strata["inventory"])
                magma_match = magma_inventory == normalize_inventory(expected_inventory)
                geometric_strata = singular_strata_from_incidence_table(incidence, forms)
                geometric_inventory = normalize_inventory(geometric_strata["inventory"])
                geometric_match = geometric_inventory == normalize_inventory(expected_inventory)
                if record["parameter_symbols"]:
                    strata = magma_strata
                    computed_inventory = magma_inventory
                    match = magma_match
                    inventory_method = "ported_magma_singularities_from_incidence_table"
                else:
                    strata = geometric_strata
                    computed_inventory = geometric_inventory
                    match = geometric_match
                    inventory_method = "geometric_strata_from_exact_linear_forms"
                incidence_status = "MATCH_WITHOUT_EXTRA_CONSTRAINTS" if match else "STILL_MISMATCHED"
                payload = {
                    "arrangement_id": arrangement_id,
                    "incidence_table": [list(item) for item in incidence],
                    "linear_forms": record["linear_forms"],
                    "strata": strata,
                    "inventory_method": inventory_method,
                    "computed_inventory": computed_inventory,
                    "magma_strata": magma_strata,
                    "magma_inventory": magma_inventory,
                    "magma_inventory_match": magma_match,
                    "geometric_strata": geometric_strata,
                    "geometric_inventory": geometric_inventory,
                    "geometric_inventory_match": geometric_match,
                    "incidence_status": incidence_status,
                }
                if match:
                    try:
                        complex_ = source_complex_from_incidence(incidence, arrangement_id=arrangement_id, linear_forms=forms)
                        payload["source_complex"] = complex_.to_dict()
                        source_summary = {
                            "source_assembly_computation_status": "computed_from_authoritative_incidence",
                            **source_assembly_summary(complex_),
                        }
                        exact_ready = True
                    except Exception as exc:  # noqa: BLE001
                        source_summary = {"source_assembly_computation_status": "source_complex_computation_error"}
                        notes.append(f"source_complex_error:{exc}")
                else:
                    source_summary = {}
                    mismatch_rows.append(
                        mismatch_dossier(
                            record,
                            incidence,
                            computed_inventory,
                            expected_inventory,
                            notes,
                            magma_inventory=magma_inventory,
                            geometric_inventory=geometric_inventory,
                            magma_match=magma_match,
                            geometric_match=geometric_match,
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                incidence_status = "INCIDENCE_COMPUTATION_ERROR"
                notes.append(str(exc))
                source_summary = {}
                mismatch_rows.append(
                    mismatch_dossier(
                        record,
                        [],
                        computed_inventory,
                        expected_inventory,
                        notes,
                        magma_inventory=magma_inventory,
                        geometric_inventory=geometric_inventory,
                        magma_match=magma_match,
                        geometric_match=geometric_match,
                    )
                )
        else:
            source_summary = {}
            mismatch_rows.append(mismatch_dossier(record, [], computed_inventory, expected_inventory, notes))
        if payload:
            incidence_payloads.append(payload)
        incidence_rows.append(
            {
                "arrangement_id": arrangement_id,
                "exact_eight_factor_parse": record["validation_status"] == "STAGED_EXACT_8_FACTOR_PARSE",
                "coefficient_domain": record["coefficient_domain"],
                "parameter_count": len(record["parameter_symbols"]),
                "scoped_condition_count": len(record["parameter_condition_references"]),
                "generic_incidence_computed": payload is not None,
                "inventory_expected": expected_inventory,
                "inventory_computed": computed_inventory,
                "inventory_match": computed_inventory == normalize_inventory(expected_inventory) if computed_inventory is not None else False,
                "inventory_method": payload["inventory_method"] if payload else "",
                "magma_inventory_computed": magma_inventory,
                "magma_inventory_match": magma_match,
                "geometric_inventory_computed": geometric_inventory,
                "geometric_inventory_match": geometric_match,
                "incidence_status": incidence_status,
                "historical_payload_match_status": record["historical_discrepancy_status"],
                "exact_source_assembly_ready": exact_ready,
                "notes": "; ".join(notes),
            }
        )
        coverage_rows.append(
            {
                "arrangement_id": arrangement_id,
                "exact_source_assembly_ready": exact_ready,
                "incidence_status": incidence_status,
                **source_summary,
            }
        )
    return incidence_rows, incidence_payloads, coverage_rows, mismatch_rows


def incidence_table_from_linear_forms_fast(forms: list[dict[str, Any]]) -> list[tuple[int, int, int, int]]:
    matrix = sp.Matrix([[sp.sympify(value) for value in form["coefficients"]] for form in forms])
    incidences = []
    for subset in combinations(range(len(forms)), 4):
        minor = matrix.extract(subset, range(4)).det()
        if is_identically_zero(minor):
            incidences.append(tuple(int(index) for index in subset))  # type: ignore[arg-type]
    return sorted(incidences)


def singularities_from_incidence_table(incidence: list[tuple[int, int, int, int]]) -> dict[str, Any]:
    planes = set(range(8))
    incidence_sets = {frozenset(item) for item in incidence}
    fivefold_points = [
        tuple(sorted(point))
        for point in combinations(planes, 5)
        if all(frozenset(quad) in incidence_sets for quad in combinations(point, 4))
    ]
    fivefold_sets = [set(point) for point in fivefold_points]
    fourfold_points = [tuple(sorted(point)) for point in incidence if not any(set(point).issubset(fivefold) for fivefold in fivefold_sets)]
    triple_lines = [
        tuple(sorted(line))
        for line in combinations(planes, 3)
        if all(frozenset(quad) in incidence_sets for quad in combinations(planes - set(line), 1) for quad in [tuple(sorted((*line, quad[0])))])
    ]
    triple_line_sets = [set(line) for line in triple_lines]
    triple_points = [
        tuple(sorted(point))
        for point in combinations(planes, 3)
        if not any(set(point).issubset(set(quad)) for quad in incidence_sets)
    ]
    double_lines = [
        tuple(sorted(pair))
        for pair in combinations(planes, 2)
        if not any(set(pair).issubset(line) for line in triple_line_sets)
    ]
    fourfold_points_zero = []
    fourfold_points_one = []
    for point in fourfold_points:
        count = sum(1 for line in triple_line_sets if line.issubset(point))
        (fourfold_points_one if count == 1 else fourfold_points_zero).append(point)
    fivefold_points_zero = []
    fivefold_points_one = []
    fivefold_points_two = []
    for point in fivefold_points:
        count = sum(1 for line in triple_line_sets if line.issubset(point))
        if count == 2:
            fivefold_points_two.append(point)
        elif count == 1:
            fivefold_points_one.append(point)
        else:
            fivefold_points_zero.append(point)
    return {
        "triple_points": sorted(triple_points),
        "fourfold_points_zero": sorted(fourfold_points_zero),
        "fourfold_points_one": sorted(fourfold_points_one),
        "fivefold_points_zero": sorted(fivefold_points_zero),
        "fivefold_points_one": sorted(fivefold_points_one),
        "fivefold_points_two": sorted(fivefold_points_two),
        "double_lines": sorted(double_lines),
        "triple_lines": sorted(triple_lines),
        "inventory": {
            "p3": len(triple_points),
            "p4_0": len(fourfold_points_zero),
            "p4_1": len(fourfold_points_one),
            "p5_0": len(fivefold_points_zero),
            "p5_1": len(fivefold_points_one),
            "p5_2": len(fivefold_points_two),
            "l3": len(triple_lines),
            "double_lines": len(double_lines),
        },
    }


def materialize_forms(forms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{**form, "coefficients": [sp.sympify(value) for value in form["coefficients"]]} for form in forms]


def source_assembly_summary(complex_: Any) -> dict[str, Any]:
    algebra = complex_.algebra
    return {
        "rank_Q": algebra["rank_Q"],
        "rank_F2": algebra["rank_mod_p"]["2"],
        "smith_normal_form": algebra["smith_normal_form"],
        "automorphism_group_order": complex_.automorphism_group["order"],
        "plane_orbit_sizes": [len(orbit) for orbit in complex_.plane_orbits],
        "double_line_orbit_sizes": [len(orbit) for orbit in complex_.double_line_orbits],
        "multiple_point_orbit_sizes": [len(orbit) for orbit in complex_.multiple_point_orbits],
    }


def mismatch_dossier(
    record: dict[str, Any],
    incidence: list[Any],
    computed: dict[str, Any] | None,
    expected: dict[str, Any] | None,
    notes: list[str],
    *,
    magma_inventory: dict[str, Any] | None = None,
    geometric_inventory: dict[str, Any] | None = None,
    magma_match: bool = False,
    geometric_match: bool = False,
) -> dict[str, Any]:
    return {
        "arrangement_id": record["arrangement_id"],
        "exact_equation": record["canonical_equation_representation"],
        "eight_factors": record["canonical_eight_factors"],
        "parameter_domain": {
            "parameter_symbols": record["parameter_symbols"],
            "conditions": record["parameter_condition_references"],
            "condition_scope": record["parameter_condition_scope"],
        },
        "conditions": record["parameter_condition_references"],
        "determinant_polynomial_status": "not_serialized_in_compact_dossier",
        "computed_incidence": [list(item) for item in incidence],
        "expected_inventory": expected,
        "computed_inventory": computed,
        "magma_inventory": magma_inventory,
        "magma_inventory_match": magma_match,
        "geometric_inventory": geometric_inventory,
        "geometric_inventory_match": geometric_match,
        "source_context": {
            "pdf_pages": record["pdf_page_references"],
            "tex_source": record["tex_source_references"],
            "classification_refs": record["classification_incidence_context_references"],
        },
        "magma_comparison": "ported IncidenceTable/Singularities logic used through HodgeCY exact linear algebra",
        "issue_classification": classify_mismatch(record, computed, expected, notes, magma_match=magma_match, geometric_match=geometric_match),
        "notes": notes,
    }


def classify_mismatch(
    record: dict[str, Any],
    computed: dict[str, Any] | None,
    expected: dict[str, Any] | None,
    notes: list[str],
    *,
    magma_match: bool = False,
    geometric_match: bool = False,
) -> str:
    if record["validation_status"] != "STAGED_EXACT_8_FACTOR_PARSE":
        return "parser_error_or_authoritative_parse_unresolved"
    if magma_match and not geometric_match:
        return "magma_inventory_match_geometric_source_assembly_mismatch"
    if "possible_fraction_grouping_typo" in " ".join(notes):
        return "source_typo_or_fraction_grouping_ambiguity"
    if record["parameter_symbols"] and not record["parameter_condition_references"]:
        return "missing_parameter_relation_or_generic_family_mismatch"
    if record["parameter_symbols"]:
        return "special_realization_or_scoped_condition_insufficient"
    return "inventory_interpretation_or_parser_error"


def write_outputs(
    out_root: Path,
    staged_records: list[dict[str, Any]],
    staged_conditions: list[dict[str, Any]],
    parse_audit: list[dict[str, Any]],
    refined: list[dict[str, Any]],
    incidence_rows: list[dict[str, Any]],
    incidence_payloads: list[dict[str, Any]],
    coverage_rows: list[dict[str, Any]],
) -> None:
    write_jsonl(out_root / "ckc455_staged_records.jsonl", staged_records)
    write_parquet(out_root / "ckc455_staged_records.parquet", staged_records)
    write_parquet(out_root / "ckc_parameter_conditions_staged.parquet", staged_conditions)
    write_tsv(out_root / "equation_parse_audit.tsv", parse_audit)
    write_tsv(out_root / "historical_ckc_ingest_discrepancies_refined.tsv", refined)
    write_tsv(out_root / "ckc455_incidence_validation.tsv", incidence_rows)
    write_parquet(out_root / "ckc455_authoritative_incidence.parquet", incidence_payloads)
    write_tsv(out_root / "ckc455_source_assembly_coverage.tsv", coverage_rows)
    write_json(
        out_root / "staged_to_derived_manifest.json",
        {
            "schema": "hodgecy.ckc_authoritative_staged_to_derived_manifest.v1",
            "outputs": {
                "staged_records_jsonl": "ckc455_staged_records.jsonl",
                "staged_records_parquet": "ckc455_staged_records.parquet",
                "parameter_conditions": "ckc_parameter_conditions_staged.parquet",
                "parse_audit": "equation_parse_audit.tsv",
                "refined_discrepancies": "historical_ckc_ingest_discrepancies_refined.tsv",
                "incidence_validation": "ckc455_incidence_validation.tsv",
                "authoritative_incidence": "ckc455_authoritative_incidence.parquet",
                "source_assembly_coverage": "ckc455_source_assembly_coverage.tsv",
                "remaining_mismatch_dossiers": "remaining_mismatch_dossiers/",
            },
        },
    )


def build_summary(
    staged_records: list[dict[str, Any]],
    refined: list[dict[str, Any]],
    incidence_rows: list[dict[str, Any]],
    coverage_rows: list[dict[str, Any]],
    mismatch_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    refined_counts = count_by(refined, "refined_classification")
    incidence_counts = count_by(incidence_rows, "incidence_status")
    exact_ckc = sum(1 for row in coverage_rows if row["exact_source_assembly_ready"])
    by_id = {row["arrangement_id"]: row for row in incidence_rows}
    return {
        "CKC_STAGED_RECORDS": len(staged_records),
        "EXACT_8_FACTOR_PARSES": sum(1 for row in staged_records if row["validation_status"] == "STAGED_EXACT_8_FACTOR_PARSE"),
        "HISTORICAL_CANONICAL_MATCHES": refined_counts.get("EXACT_CANONICAL_MATCH", 0) + refined_counts.get("FACTOR_ORDER_DIFFERENCE", 0),
        "HISTORICAL_TRUE_SUBSTANTIVE_DISCREPANCIES": refined_counts.get("GENUINE_SUBSTANTIVE_DISCREPANCY", 0),
        "INCIDENCE_MATCH_WITHOUT_EXTRA_CONSTRAINTS": incidence_counts.get("MATCH_WITHOUT_EXTRA_CONSTRAINTS", 0),
        "INCIDENCE_MATCH_AFTER_SCOPED_CONSTRAINTS": incidence_counts.get("MATCH_AFTER_SCOPED_CONSTRAINTS", 0),
        "INCIDENCE_STILL_MISMATCHED": len([row for row in incidence_rows if row["incidence_status"] not in {"MATCH_WITHOUT_EXTRA_CONSTRAINTS", "MATCH_AFTER_SCOPED_CONSTRAINTS"}]),
        "MAGMA_INVENTORY_MATCHES": sum(1 for row in incidence_rows if row["magma_inventory_match"]),
        "GEOMETRIC_INVENTORY_MATCHES": sum(1 for row in incidence_rows if row["geometric_inventory_match"]),
        "EXACT_CKC_SOURCE_ASSEMBLIES": exact_ckc,
        "TOTAL_WITH_84A": exact_ckc + 1,
        "451_STATUS": status_for(by_id, "451"),
        "454_STATUS": status_for(by_id, "454"),
        "83_STATUS": status_for(by_id, "83"),
        "refined_discrepancy_counts": refined_counts,
        "incidence_status_counts": incidence_counts,
        "remaining_mismatches": [{"arrangement_id": row["arrangement_id"], "reason": row["issue_classification"]} for row in mismatch_rows],
    }


def write_reports(out_root: Path, summary: dict[str, Any], mismatch_rows: list[dict[str, Any]]) -> None:
    staging_lines = [
        "# CKC Authoritative Staging Report",
        "",
        f"- CKC staged records: {summary['CKC_STAGED_RECORDS']}",
        f"- Exact eight-factor parses: {summary['EXACT_8_FACTOR_PARSES']}",
        f"- Historical canonical matches: {summary['HISTORICAL_CANONICAL_MATCHES']}",
        f"- Historical true substantive discrepancies: {summary['HISTORICAL_TRUE_SUBSTANTIVE_DISCREPANCIES']}",
        "",
        "The staged records are sourced from the authoritative raw ingest, not the historical equation-only payload.",
    ]
    write_text(out_root / "authoritative_staging_report.md", "\n".join(staging_lines))
    lines = [
        "# CKC Incidence Reconstruction Report",
        "",
        f"CKC_STAGED_RECORDS = {summary['CKC_STAGED_RECORDS']}",
        f"EXACT_8_FACTOR_PARSES = {summary['EXACT_8_FACTOR_PARSES']}",
        f"HISTORICAL_CANONICAL_MATCHES = {summary['HISTORICAL_CANONICAL_MATCHES']}",
        f"HISTORICAL_TRUE_SUBSTANTIVE_DISCREPANCIES = {summary['HISTORICAL_TRUE_SUBSTANTIVE_DISCREPANCIES']}",
        f"INCIDENCE_MATCH_WITHOUT_EXTRA_CONSTRAINTS = {summary['INCIDENCE_MATCH_WITHOUT_EXTRA_CONSTRAINTS']}",
        f"INCIDENCE_MATCH_AFTER_SCOPED_CONSTRAINTS = {summary['INCIDENCE_MATCH_AFTER_SCOPED_CONSTRAINTS']}",
        f"INCIDENCE_STILL_MISMATCHED = {summary['INCIDENCE_STILL_MISMATCHED']}",
        f"MAGMA_INVENTORY_MATCHES = {summary['MAGMA_INVENTORY_MATCHES']}",
        f"GEOMETRIC_INVENTORY_MATCHES = {summary['GEOMETRIC_INVENTORY_MATCHES']}",
        f"EXACT_CKC_SOURCE_ASSEMBLIES = {summary['EXACT_CKC_SOURCE_ASSEMBLIES']}",
        f"TOTAL_WITH_84A = {summary['TOTAL_WITH_84A']}",
        f"451_STATUS = {summary['451_STATUS']}",
        f"454_STATUS = {summary['454_STATUS']}",
        f"83_STATUS = {summary['83_STATUS']}",
        "",
        "## Remaining Mismatches",
        "",
        "| CKC ID | reason | expected | primary computed | magma computed | geometric computed |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in mismatch_rows:
        lines.append(
            f"| {row['arrangement_id']} | {row['issue_classification']} | {cell(row['expected_inventory'])} | "
            f"{cell(row['computed_inventory'])} | {cell(row.get('magma_inventory'))} | {cell(row.get('geometric_inventory'))} |"
        )
    write_text(out_root / "incidence_reconstruction_report.md", "\n".join(lines))
    write_json(out_root / "staging_summary.json", summary)


def status_for(by_id: dict[str, dict[str, Any]], arrangement_id: str) -> str:
    row = by_id.get(arrangement_id)
    if not row:
        return "MISSING"
    return (
        f"{row['incidence_status']}; parse={row['exact_eight_factor_parse']}; "
        f"inventory_match={row['inventory_match']}; magma_match={row['magma_inventory_match']}; "
        f"geometric_match={row['geometric_inventory_match']}"
    )


def normalize_inventory(value: Any) -> dict[str, int] | None:
    parsed = parse_jsonish(value)
    if not parsed:
        return None
    return {key: int(parsed.get(key, parsed.get("triple_lines" if key == "l3" else key, 0)) or 0) for key in INVENTORY_KEYS}


def normalize_tex_math(raw_tex: str) -> str:
    return re.sub(r"\s+", " ", raw_tex.replace("\\not=", "!=").replace("\\neq", "!=")).strip()


def parameter_sort_key(value: str) -> int:
    match = re.search(r"\d+", value)
    return int(match.group(0)) if match else 999


def parse_jsonish(value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (dict, list)):
        return value
    text = str(value)
    if text in {"", "nan", "NaN", "None"}:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[str(row.get(key))] = counts.get(str(row.get(key)), 0) + 1
    return counts


def cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return str(value)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False, default=str) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: cell(row.get(field)) for field in fields})


def write_parquet(path: Path, rows: list[dict[str, Any]]) -> None:
    frame = pd.DataFrame(rows)
    for column in frame.columns:
        if frame[column].map(lambda value: isinstance(value, (dict, list, tuple))).any():
            frame[column] = frame[column].map(lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False, default=str) if isinstance(value, (dict, list, tuple)) else value)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


__all__ = ["run_authoritative_staging", "parse_tex_product", "top_level_tex_factors", "tex_factor_to_linear_text"]
