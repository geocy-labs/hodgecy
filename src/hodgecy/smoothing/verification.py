"""Exact rational verification scaffolding for smoothing-bridge examples."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

import pandas as pd
import sympy as sp

from hodgecy.arrangements import arrangement_84, arrangement_84a, build_concurrency_profile
from hodgecy.arrangements.planes import PlaneArrangement


@dataclass(slots=True)
class LineGenericityCheck:
    line_id: str
    planes: tuple[str, str]
    parameter_polynomial: str
    degree: int
    discriminant: str | None
    has_four_simple_zeros: bool
    status: str
    reason: str | None = None


@dataclass(slots=True)
class MultiplePointCheck:
    point_id: str
    coordinates: tuple[int, int, int, int]
    q_value: str
    status: str


@dataclass(slots=True)
class SmoothingVerificationRecord:
    example_id: str
    source_arrangement: str
    arrangement_polynomial: str
    quartic_Q: str
    epsilon: int
    smoothing_polynomial: str
    singular_locus_generators: dict[str, str]
    expected_node_count: int
    plane_count: int
    double_line_count: int
    multiple_point_count: int
    q_avoids_all_multiple_points: bool
    q_multiple_point_violations: list[str]
    multiple_point_checks: list[MultiplePointCheck]
    all_double_lines_have_four_simple_zeros: bool
    line_checks: list[LineGenericityCheck]
    singular_locus_status: str
    singular_locus_reason: str
    hessian_status: str
    hessian_reason: str
    overall_status: str
    notes: str
    cas_followup: dict[str, str]


def _symbols():
    return sp.symbols("x y z t u")


def candidate_quartic() -> sp.Expr:
    x, y, z, t, _ = _symbols()
    return x**4 + 2 * y**4 + 3 * z**4 + 5 * t**4 + x * y * z * t


def epsilon_value() -> int:
    return 1


def arrangement_polynomial(arrangement: PlaneArrangement) -> sp.Expr:
    x, y, z, t, _ = _symbols()
    variables = [x, y, z, t]
    product = sp.Integer(1)
    for plane in arrangement.planes:
        linear = sum(sp.Integer(coefficient) * var for coefficient, var in zip(plane.coefficients, variables))
        product *= linear
    return sp.expand(product)


def smoothing_polynomial(arrangement: PlaneArrangement) -> sp.Expr:
    return sp.expand(arrangement_polynomial(arrangement) + epsilon_value() * candidate_quartic() ** 2)


def singular_locus_generators(arrangement: PlaneArrangement) -> dict[str, str]:
    x, y, z, t, _ = _symbols()
    polynomial = smoothing_polynomial(arrangement)
    return {
        "F": str(polynomial),
        "dF_dx": str(sp.expand(sp.diff(polynomial, x))),
        "dF_dy": str(sp.expand(sp.diff(polynomial, y))),
        "dF_dz": str(sp.expand(sp.diff(polynomial, z))),
        "dF_dt": str(sp.expand(sp.diff(polynomial, t))),
    }


def _line_basis(arrangement: PlaneArrangement, plane_a: str, plane_b: str) -> list[sp.Matrix]:
    label_to_plane = {plane.label: plane for plane in arrangement.planes}
    matrix = sp.Matrix([label_to_plane[plane_a].coefficients, label_to_plane[plane_b].coefficients])
    return matrix.nullspace()


def _parameter_polynomial_for_line(arrangement: PlaneArrangement, plane_a: str, plane_b: str) -> sp.Expr:
    x, y, z, t, u = _symbols()
    basis = _line_basis(arrangement, plane_a, plane_b)
    if len(basis) != 2:
        raise ValueError(f"Expected a 2-dimensional nullspace for line {plane_a}/{plane_b}.")
    substitutions = {
        x: basis[0][0] + u * basis[1][0],
        y: basis[0][1] + u * basis[1][1],
        z: basis[0][2] + u * basis[1][2],
        t: basis[0][3] + u * basis[1][3],
    }
    return sp.expand(candidate_quartic().subs(substitutions))


def line_genericity_check(arrangement: PlaneArrangement, line_id: str, planes: tuple[str, str]) -> LineGenericityCheck:
    _, _, _, _, u = _symbols()
    parameter_polynomial = _parameter_polynomial_for_line(arrangement, planes[0], planes[1])
    poly = sp.Poly(parameter_polynomial, u, domain="QQ")
    derivative = sp.diff(parameter_polynomial, u)
    gcd = sp.gcd(poly.as_expr(), derivative)
    discriminant = None
    if poly.degree() >= 1:
        try:
            discriminant = str(sp.factor(poly.discriminant()))
        except Exception:
            discriminant = None
    has_four_simple_zeros = poly.degree() == 4 and sp.Poly(gcd, u, domain="QQ").degree() == 0
    return LineGenericityCheck(
        line_id=line_id,
        planes=planes,
        parameter_polynomial=str(sp.expand(parameter_polynomial)),
        degree=poly.degree(),
        discriminant=discriminant,
        has_four_simple_zeros=has_four_simple_zeros,
        status="verified" if has_four_simple_zeros else "failed",
        reason=None if has_four_simple_zeros else "Restriction is not a squarefree quartic.",
    )


def verify_q_avoids_multiple_points(arrangement: PlaneArrangement) -> tuple[bool, list[str], list[MultiplePointCheck]]:
    x, y, z, t, _ = _symbols()
    quartic = candidate_quartic()
    profile = build_concurrency_profile(arrangement)
    violations: list[str] = []
    checks: list[MultiplePointCheck] = []
    for point in profile.multiple_points:
        value = sp.expand(quartic.subs({x: point.coordinates[0], y: point.coordinates[1], z: point.coordinates[2], t: point.coordinates[3]}))
        status = "verified"
        if value == 0:
            violations.append(point.point_id)
            status = "failed"
        checks.append(
            MultiplePointCheck(
                point_id=point.point_id,
                coordinates=point.coordinates,
                q_value=str(value),
                status=status,
            )
        )
    return len(violations) == 0, violations, checks


def build_smoothing_verification(arrangement: PlaneArrangement) -> SmoothingVerificationRecord:
    profile = build_concurrency_profile(arrangement)
    q_avoids, violations, multiple_point_checks = verify_q_avoids_multiple_points(arrangement)
    line_checks = [line_genericity_check(arrangement, line.line_id, line.planes) for line in profile.double_lines]
    all_simple = all(check.has_four_simple_zeros for check in line_checks)

    singular_locus_status = "partial"
    singular_locus_reason = (
        "Exact rational F and gradient generators are recorded, but the characteristic-zero projective "
        "scheme-length/reducedness verification is deferred to dedicated CAS scripts."
    )
    hessian_status = "partial"
    hessian_reason = (
        "Full Hessian rank-3 verification at every singular point remains queued until the singular-point set "
        "is certified by CAS."
    )
    overall_status = "partial" if q_avoids and all_simple else "failed_genericity"

    notes = (
        "Python-side verification establishes exact rational genericity for Q at the arrangement multiple points "
        "and along every double line. Zero-dimensionality, reducedness, and node-type verification remain partial."
    )
    cas_followup = {
        "macaulay2_script": "m2/verify_smoothing_bridge_genericity.m2",
        "singular_script": "singular/verify_smoothing_bridge_genericity.sing",
    }
    return SmoothingVerificationRecord(
        example_id=f"smoothing_bridge_{arrangement.arrangement_id}",
        source_arrangement=arrangement.arrangement_id,
        arrangement_polynomial=str(arrangement_polynomial(arrangement)),
        quartic_Q=str(candidate_quartic()),
        epsilon=epsilon_value(),
        smoothing_polynomial=str(smoothing_polynomial(arrangement)),
        singular_locus_generators=singular_locus_generators(arrangement),
        expected_node_count=112,
        plane_count=len(arrangement.planes),
        double_line_count=profile.double_line_count,
        multiple_point_count=sum(profile.multiple_point_count_by_multiplicity.values()),
        q_avoids_all_multiple_points=q_avoids,
        q_multiple_point_violations=violations,
        multiple_point_checks=multiple_point_checks,
        all_double_lines_have_four_simple_zeros=all_simple,
        line_checks=line_checks,
        singular_locus_status=singular_locus_status,
        singular_locus_reason=singular_locus_reason,
        hessian_status=hessian_status,
        hessian_reason=hessian_reason,
        overall_status=overall_status,
        notes=notes,
        cas_followup=cas_followup,
    )


def record_to_dict(record: SmoothingVerificationRecord) -> dict:
    return asdict(record)


def build_summary_frame(records: list[SmoothingVerificationRecord]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "example_id": record.example_id,
                "source_arrangement": record.source_arrangement,
                "expected_node_count": record.expected_node_count,
                "q_avoids_all_multiple_points": record.q_avoids_all_multiple_points,
                "all_double_lines_have_four_simple_zeros": record.all_double_lines_have_four_simple_zeros,
                "singular_locus_status": record.singular_locus_status,
                "hessian_status": record.hessian_status,
                "overall_status": record.overall_status,
                "notes": record.notes,
            }
            for record in records
        ]
    )


def write_default_verification_outputs(root: Path) -> list[SmoothingVerificationRecord]:
    processed = root / "data" / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    records = [build_smoothing_verification(arrangement_84()), build_smoothing_verification(arrangement_84a())]
    for record in records:
        output_path = processed / f"smoothing_verification_{record.source_arrangement}.json"
        temp_path = output_path.with_suffix(".json.tmp")
        temp_path.write_text(json.dumps(record_to_dict(record), indent=2), encoding="utf-8")
        temp_path.replace(output_path)
    summary_path = processed / "smoothing_verification_summary.csv"
    summary_temp_path = processed / "smoothing_verification_summary.csv.tmp"
    build_summary_frame(records).to_csv(summary_temp_path, index=False)
    summary_temp_path.replace(summary_path)
    return records
