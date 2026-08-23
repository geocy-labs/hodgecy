"""Exact linear-form parsing for double-octic plane arrangements."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

import sympy as sp

VARIABLES = ("x", "y", "z", "t")
_SQRT_RE = re.compile(r"\u221a\s*([+-]?\d+)")


@dataclass(frozen=True, slots=True)
class ParsedLinearFactor:
    coefficients: tuple[sp.Expr, sp.Expr, sp.Expr, sp.Expr]
    normalized_factor: str
    coefficient_domain: str


def parse_linear_factor_text(factor: str, *, parameter_names: list[str] | tuple[str, ...] = ()) -> ParsedLinearFactor:
    """Parse one exact linear factor into coefficients of x,y,z,t.

    The CKC equation index stores compact PDF-extracted factors such as
    ``A0x+A1y`` and ``32(sqrt(-3)+1)A0t``.  This parser keeps arithmetic exact and
    treats listed parameter names as symbols.
    """

    text = _normalize_factor_text(factor)
    terms = _split_terms(text)
    coeffs = {variable: sp.Integer(0) for variable in VARIABLES}
    for term in terms:
        coeff_text, variable = _split_variable_term(term)
        coeffs[variable] += _parse_coefficient(coeff_text, parameter_names=parameter_names)
    coefficients = tuple(sp.simplify(coeffs[variable]) for variable in VARIABLES)
    return ParsedLinearFactor(coefficients, text, _coefficient_domain(coefficients, parameter_names))


def linear_forms_from_factor_texts(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Return zero-based linear-form records from raw CKC factor strings."""

    parameter_names = tuple(str(name) for name in (record.get("parameter_names") or []))
    factors = list(record.get("linear_factor_texts") or [])
    if len(factors) != 8:
        raise ValueError(f"Expected 8 linear factors, found {len(factors)}.")
    forms = []
    for index, factor in enumerate(factors):
        parsed = parse_linear_factor_text(str(factor), parameter_names=parameter_names)
        forms.append(
            {
                "index": index,
                "label": f"p{index + 1}",
                "coefficients": list(parsed.coefficients),
                "equation": parsed.normalized_factor,
                "coefficient_domain": parsed.coefficient_domain,
            }
        )
    return forms


def _normalize_factor_text(factor: str) -> str:
    text = str(factor).strip()
    text = text.replace("\u2212", "-").replace("\u2013", "-")
    text = re.sub(r"\s+", "", text)
    text = _strip_outer_parentheses(text)
    text = _SQRT_RE.sub(lambda match: f"sqrt({match.group(1)})", text)
    text = text.replace("^", "**")
    return text


def _strip_outer_parentheses(text: str) -> str:
    while text.startswith("(") and text.endswith(")") and _outer_parentheses_wrap(text):
        text = text[1:-1]
    return text


def _outer_parentheses_wrap(text: str) -> bool:
    depth = 0
    for index, char in enumerate(text):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0 and index != len(text) - 1:
                return False
        if depth < 0:
            return False
    return depth == 0


def _split_terms(text: str) -> list[str]:
    terms = []
    start = 0
    depth = 0
    for index, char in enumerate(text):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char in "+-" and depth == 0 and index > start:
            terms.append(text[start:index])
            start = index
    terms.append(text[start:])
    return [term for term in terms if term and term not in {"+", "-"}]


def _split_variable_term(term: str) -> tuple[str, str]:
    depth = 0
    variable_index: int | None = None
    for index in range(len(term) - 1, -1, -1):
        char = term[index]
        if char == ")":
            depth += 1
        elif char == "(":
            depth -= 1
        elif depth == 0 and char in VARIABLES:
            variable_index = index
            break
    if variable_index is None:
        raise ValueError(f"linear term has no projective variable: {term!r}")
    variable = term[variable_index]
    coeff_text = term[:variable_index] + term[variable_index + 1 :]
    coeff_text = coeff_text.rstrip("*")
    if coeff_text in {"", "+"}:
        coeff_text = "1"
    elif coeff_text == "-":
        coeff_text = "-1"
    return coeff_text, variable


def _parse_coefficient(text: str, *, parameter_names: tuple[str, ...]) -> sp.Expr:
    normalized = _insert_multiplication(text, parameter_names=parameter_names)
    local_dict = {name: sp.Symbol(name) for name in parameter_names}
    local_dict.update({"sqrt": sp.sqrt, "I": sp.I})
    return sp.sympify(normalized, locals=local_dict)


def _insert_multiplication(text: str, *, parameter_names: tuple[str, ...]) -> str:
    tokens = _tokenize_coefficient(text, parameter_names=parameter_names)
    out: list[str] = []
    previous_kind: str | None = None
    for kind, token in tokens:
        if previous_kind in {"atom", "close"} and kind in {"atom", "open", "func"}:
            out.append("*")
        out.append(token)
        previous_kind = kind
    return "".join(out)


def _tokenize_coefficient(text: str, *, parameter_names: tuple[str, ...]) -> list[tuple[str, str]]:
    names = sorted(set(parameter_names), key=len, reverse=True)
    tokens: list[tuple[str, str]] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char in "+-*/,":
            tokens.append(("op", char))
            index += 1
            continue
        if char == "(":
            tokens.append(("open", char))
            index += 1
            continue
        if char == ")":
            tokens.append(("close", char))
            index += 1
            continue
        if text.startswith("sqrt", index):
            tokens.append(("func", "sqrt"))
            index += 4
            continue
        matched = next((name for name in names if text.startswith(name, index)), None)
        if matched:
            tokens.append(("atom", matched))
            index += len(matched)
            continue
        if char.isdigit():
            end = index + 1
            while end < len(text) and text[end].isdigit():
                end += 1
            tokens.append(("atom", text[index:end]))
            index = end
            continue
        if char.isalpha():
            end = index + 1
            while end < len(text) and text[end].isalnum():
                end += 1
            tokens.append(("atom", text[index:end]))
            index = end
            continue
        raise ValueError(f"unsupported coefficient character {char!r} in {text!r}")
    return tokens


def _coefficient_domain(coefficients: tuple[sp.Expr, ...], parameter_names: tuple[str, ...]) -> str:
    has_parameters = any(expr.free_symbols for expr in coefficients)
    has_algebraic = any(expr.has(sp.sqrt(2)) or expr.has(sp.I) or _has_nonrational_number(expr) for expr in coefficients)
    if has_parameters and has_algebraic:
        return "Qbar(parameters)"
    if has_parameters:
        return "Q(parameters)"
    if has_algebraic:
        return "number_field"
    return "Q"


def _has_nonrational_number(expr: sp.Expr) -> bool:
    for atom in expr.atoms(sp.Pow):
        if atom.exp == sp.Rational(1, 2):
            return True
    return False
