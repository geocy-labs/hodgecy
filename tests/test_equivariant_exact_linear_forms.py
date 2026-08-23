from __future__ import annotations

import json
from pathlib import Path

import sympy as sp

from hodgecy.equivariant import (
    incidence_table_from_linear_forms,
    linear_forms_from_factor_texts,
    parse_linear_factor_text,
    parse_linear_forms_from_record,
    singular_strata_from_incidence_table,
    source_complex_from_incidence,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ckc_records() -> dict[str, dict]:
    path = repo_root() / "data" / "raw" / "cynk_kocel_cynk_2026" / "ckc_equation_index_001_455.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(record["arrangement_id"]): record for record in payload["records"]}


def algebraic_repairs() -> dict[str, dict]:
    path = repo_root() / "data" / "raw" / "cynk_kocel_cynk_2026" / "ckc_algebraic_repairs_451_452_453.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(record["arrangement_id"]): record for record in payload["records"]}


def test_parameterized_factor_parser_keeps_exact_symbols() -> None:
    parsed = parse_linear_factor_text("(A0x+A1y-A1z)", parameter_names=("A0", "A1"))
    A0, A1 = sp.symbols("A0 A1")
    assert parsed.coefficients == (A0, A1, -A1, 0)
    assert parsed.coefficient_domain == "Q(parameters)"


def test_quadratic_factor_parser_keeps_exact_radicals() -> None:
    parsed = parse_linear_factor_text("((sqrt(-3)+3)/2*x+y+(sqrt(-3)+3)/2*z)")
    assert parsed.coefficients[0] == sp.Rational(3, 2) + sp.sqrt(-3) / 2
    assert parsed.coefficients[1] == 1
    assert parsed.coefficients[2] == sp.Rational(3, 2) + sp.sqrt(-3) / 2
    assert parsed.coefficient_domain == "number_field"


def test_raw_ckc_rational_record_reproduces_known_1_inventory() -> None:
    forms = parse_linear_forms_from_record(ckc_records()["1"])
    table = incidence_table_from_linear_forms(forms)
    strata = singular_strata_from_incidence_table(table, forms)
    assert strata["inventory"]["p3"] == 4
    assert strata["inventory"]["p4_0"] == 5
    assert strata["inventory"]["double_lines"] == 16


def test_parameterized_record_symbolic_incidence_is_a_verification_route() -> None:
    forms = linear_forms_from_factor_texts(ckc_records()["78"])
    table = incidence_table_from_linear_forms(forms)
    strata = singular_strata_from_incidence_table(table, forms)
    assert strata["inventory"]["p3"] == 22
    assert strata["inventory"]["p4_0"] == 4
    assert strata["inventory"]["double_lines"] == 25


def test_source_complex_from_incidence_builds_without_coefficients() -> None:
    forms = parse_linear_forms_from_record(ckc_records()["1"])
    table = incidence_table_from_linear_forms(forms)
    complex_ = source_complex_from_incidence(table, arrangement_id="1", linear_forms=forms)
    assert complex_.algebra["gluing_matrix_shape"] == [13, 16]
    assert complex_.algebra["rank_Q"] == 13


def test_repaired_452_and_453_quadratic_equations_match_source_inventory() -> None:
    expected = {
        "452": {"p3": 20, "p4_0": 9, "p4_1": 0, "p5_0": 0, "p5_1": 0, "p5_2": 0, "triple_lines": 0},
        "453": {"p3": 20, "p4_0": 9, "p4_1": 0, "p5_0": 0, "p5_1": 0, "p5_2": 0, "triple_lines": 0},
    }
    for arrangement_id in ("452", "453"):
        record = algebraic_repairs()[arrangement_id]
        forms = linear_forms_from_factor_texts(record)
        table = incidence_table_from_linear_forms(forms)
        strata = singular_strata_from_incidence_table(table, forms)
        for key, value in expected[arrangement_id].items():
            assert strata["inventory"][key] == value
