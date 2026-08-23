from __future__ import annotations

from hodgecy.research.ckc_authoritative_staging import parse_tex_product, tex_factor_to_linear_text, top_level_tex_factors


def test_tex_factor_parser_respects_fraction_braces_for_451() -> None:
    raw = r"(x + \frac{\sqrt{-3} - 1}2y)xy(y + t)(x + t)(-x + -\frac{\sqrt{-3} + 1}2y + \frac{\sqrt{-3} - 1)}2z - t)z(z + t)"

    parsed = parse_tex_product(raw, arrangement_id="451")

    assert parsed["top_level_factor_count"] == 8
    assert parsed["ast_status"] == "parsed"
    assert any("unbalanced_parenthesis_inside_fraction_argument" in warning for warning in parsed["parse_warnings"])


def test_tex_factor_to_linear_text_handles_frac_sqrt_and_parameters() -> None:
    text, warnings = tex_factor_to_linear_text(r"(\frac32(\sqrt{-3} + 1)A_{0}x + \frac{\sqrt{-3} + 3}2y + 3t)")

    assert warnings == []
    assert "sqrt(-3)" in text
    assert "A0*x" in text
    assert "3*t" in text


def test_top_level_tex_factors_handles_ordinary_ckc_product() -> None:
    factors = top_level_tex_factors(r"xy(A_{0}x + A_{1}y)(x + z)z(y + t)t(x + y + z + t)")

    assert factors == ["x", "y", r"(A_{0}x + A_{1}y)", "(x + z)", "z", "(y + t)", "t", "(x + y + z + t)"]
