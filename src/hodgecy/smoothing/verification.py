"""Verification workflow for smoothing-bridge examples."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
from functools import lru_cache
from pathlib import Path
import time

import pandas as pd
import sympy as sp

from hodgecy.arrangements import arrangement_84, arrangement_84a, build_concurrency_profile
from hodgecy.arrangements.planes import PlaneArrangement
from hodgecy.smoothing.reviewer_v4_audit import build_reviewer_v4_audit

ALLOWED_VERIFICATION_STATUSES = {
    "queued",
    "genericity_verified",
    "degree112_certified",
    "ordinary_node_verified",
    "defect_verified",
    "failed",
}


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
class FiniteFieldCheck:
    prime: int
    dimension: int | None
    length: int | None
    reduced: bool | None
    ordinary_nodes: bool | None
    hessian_rank_distribution: dict[str, int]
    status: str
    notes: str
    rational_projective_point_count: int | None = None


@dataclass(slots=True)
class SmoothingVerificationRecord:
    arrangement: str
    arrangement_equation: str
    quartic_Q: str
    epsilon: str
    verification_status: str
    G1_avoids_multiple_points: bool
    G2_squarefree_on_double_lines: bool
    G3_global_singular_locus_checked: bool
    singular_locus_dimension: int | None
    singular_locus_length: int | None
    reduced: bool | None
    ordinary_nodes: bool | None
    hessian_rank_distribution: dict[str, int]
    finite_field_checks: list[FiniteFieldCheck]
    cas_scripts: dict[str, str]
    notes: str
    example_id: str
    source_arrangement: str
    arrangement_polynomial: str
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


@dataclass(slots=True)
class VerificationWriteResult:
    logical_path: str
    actual_path: str
    status: str
    notes: str | None = None


@dataclass(slots=True)
class VerificationRunResult:
    records: list[SmoothingVerificationRecord]
    write_results: list[VerificationWriteResult]
    summary_path: str


def _symbols():
    return sp.symbols("x y z t u")


def arrangement_lookup() -> dict[str, PlaneArrangement]:
    return {"84": arrangement_84(), "84a": arrangement_84a()}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@lru_cache(maxsize=4)
def _reviewer_v4_claim_support(root: str) -> dict[str, bool]:
    audit = build_reviewer_v4_audit(Path(root))
    return {claim.claim_id: claim.repo_backed for claim in audit.claims}


def candidate_quartic() -> sp.Expr:
    x, y, z, t, _ = _symbols()
    return x**4 + 2 * y**4 + 3 * z**4 + 5 * t**4 + x * y * z * t


def candidate_quartic_str() -> str:
    return "x^4 + 2*y^4 + 3*z^4 + 5*t^4 + x*y*z*t"


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


def _projective_points_over_fp(prime: int) -> list[tuple[int, int, int, int]]:
    points: list[tuple[int, int, int, int]] = []
    for a in range(prime):
        for b in range(prime):
            for c in range(prime):
                points.append((1, a, b, c))
    for b in range(prime):
        for c in range(prime):
            points.append((0, 1, b, c))
    for c in range(prime):
        points.append((0, 0, 1, c))
    points.append((0, 0, 0, 1))
    return points


def _matrix_rank_mod_prime(matrix_rows: list[list[int]], prime: int) -> int:
    rows = [[entry % prime for entry in row] for row in matrix_rows]
    row_count = len(rows)
    col_count = len(rows[0]) if rows else 0
    rank = 0
    pivot_row = 0
    for col in range(col_count):
        pivot = None
        for row in range(pivot_row, row_count):
            if rows[row][col] % prime != 0:
                pivot = row
                break
        if pivot is None:
            continue
        rows[pivot_row], rows[pivot] = rows[pivot], rows[pivot_row]
        inv = pow(rows[pivot_row][col], -1, prime)
        rows[pivot_row] = [(value * inv) % prime for value in rows[pivot_row]]
        for row in range(row_count):
            if row == pivot_row or rows[row][col] % prime == 0:
                continue
            factor = rows[row][col] % prime
            rows[row] = [(left - factor * right) % prime for left, right in zip(rows[row], rows[pivot_row])]
        rank += 1
        pivot_row += 1
        if pivot_row == row_count:
            break
    return rank


def _run_finite_field_checks(
    arrangement: PlaneArrangement,
    max_seconds: int | None,
) -> list[FiniteFieldCheck]:
    x, y, z, t, _ = _symbols()
    polynomial = smoothing_polynomial(arrangement)
    generators = [polynomial] + [sp.expand(sp.diff(polynomial, variable)) for variable in (x, y, z, t)]
    hessian = [[sp.expand(sp.diff(sp.diff(polynomial, left), right)) for right in (x, y, z, t)] for left in (x, y, z, t)]
    deadline = None if max_seconds is None else time.monotonic() + max_seconds
    checks: list[FiniteFieldCheck] = []
    for prime in (13, 17, 19):
        if deadline is not None and time.monotonic() >= deadline:
            checks.append(
                FiniteFieldCheck(
                    prime=prime,
                    dimension=None,
                    length=None,
                    reduced=None,
                    ordinary_nodes=None,
                    hessian_rank_distribution={},
                    status="failed",
                    notes="Skipped because the finite-field budget was exhausted before this prime was reached.",
                )
            )
            continue
        singular_points: list[tuple[int, int, int, int]] = []
        for point in _projective_points_over_fp(prime):
            substitutions = {x: point[0], y: point[1], z: point[2], t: point[3]}
            if all(int(generator.subs(substitutions)) % prime == 0 for generator in generators):
                singular_points.append(point)
        rank_distribution: dict[str, int] = {}
        for point in singular_points:
            substitutions = {x: point[0], y: point[1], z: point[2], t: point[3]}
            matrix_rows = [
                [int(entry.subs(substitutions)) % prime for entry in row]
                for row in hessian
            ]
            rank = _matrix_rank_mod_prime(matrix_rows, prime)
            rank_distribution[str(rank)] = rank_distribution.get(str(rank), 0) + 1
        checks.append(
            FiniteFieldCheck(
                prime=prime,
                dimension=None,
                length=None,
                reduced=None,
                ordinary_nodes=(rank_distribution == {"3": len(singular_points)}) if singular_points else None,
                hessian_rank_distribution=rank_distribution,
                status="partial",
                notes=(
                    "Exhaustive projective F_p-rational singular-point scan completed. "
                    "This is a rational-point sanity check only; no characteristic-zero or scheme-length promotion is claimed."
                ),
                rational_projective_point_count=len(singular_points),
            )
        )
    return checks


def _run_char0_checks(arrangement: PlaneArrangement, max_seconds: int | None) -> tuple[bool, str]:
    _ = (arrangement, max_seconds)
    return False, (
        "Characteristic-zero checks are intentionally not run by default in this workflow. "
        "The repository ships exact Macaulay2 and Singular handoff scripts, but no local CAS executable was invoked here."
    )


def _derive_verified_status(base_status: str, repo_root: Path) -> str:
    if base_status != "genericity_verified":
        return base_status
    claim_support = _reviewer_v4_claim_support(str(repo_root))
    degree112 = claim_support.get("char0_degree_112", False)
    reduced = claim_support.get("reduced_true", False)
    hessian = claim_support.get("hessian_rank_3", False)
    defect = claim_support.get("defect_equals_7", False)
    hilbert = claim_support.get("hilbert_degree_8_equals_105", False)

    if degree112 and reduced and hessian and defect and hilbert:
        return "defect_verified"
    if degree112 and reduced and hessian:
        return "ordinary_node_verified"
    if degree112:
        return "degree112_certified"
    return "genericity_verified"


def _build_notes(
    verification_status: str,
    finite_field_checks: list[FiniteFieldCheck],
    char0_note: str | None,
) -> str:
    if verification_status == "defect_verified":
        return (
            "Ordinary-node certification is in place and the defect certificate is also repo-backed: "
            "the singular locus has certified degree 112, reducedness and Hessian rank-3 certificates exist, "
            "and the defect/Hilbert-function claims are machine-backed."
        )
    if verification_status == "ordinary_node_verified":
        return "Verified: reduced zero-dimensional singular locus of length 112; Hessian rank 3 at all singular points."
    if verification_status == "degree112_certified":
        return (
            "Genericity verified and char-0 degree 112 is certificate-backed for the explicit Q, "
            "but reducedness, Hessian rank-3, and defect certificates are not yet machine-backed."
        )
    if verification_status == "genericity_verified" and finite_field_checks:
        partial_primes = ", ".join(str(check.prime) for check in finite_field_checks if check.status != "failed")
        return (
            "Genericity verified: explicit Q avoids all multiple points and is squarefree on all 28 double lines; "
            f"optional finite-field sanity checks were recorded at p={partial_primes}, but no promotion beyond genericity is claimed."
        )
    if verification_status == "genericity_verified":
        return (
            "Genericity verified: explicit Q avoids all multiple points and is squarefree on all 28 double lines; "
            "global singular-locus length/reducedness/Hessian checks remain queued."
        )
    if verification_status == "failed":
        return "Verification failed: at least one required genericity condition did not hold for the explicit Q."
    return char0_note or "Verification queued."


def build_smoothing_verification(
    arrangement: PlaneArrangement,
    *,
    repo_root: Path | None = None,
    finite_field_checks: bool = False,
    char0_checks: bool = False,
    max_seconds: int | None = None,
) -> SmoothingVerificationRecord:
    root = repo_root or _repo_root()
    profile = build_concurrency_profile(arrangement)
    q_avoids, violations, multiple_point_checks = verify_q_avoids_multiple_points(arrangement)
    line_checks = [line_genericity_check(arrangement, line.line_id, line.planes) for line in profile.double_lines]
    all_simple = all(check.has_four_simple_zeros for check in line_checks)

    verification_status = "genericity_verified" if q_avoids and all_simple else "failed"
    singular_locus_status = "queued"
    singular_locus_reason = "Global singular-locus verification is not attempted in the default workflow."
    hessian_status = "queued"
    hessian_reason = "Global Hessian-rank verification is not attempted in the default workflow."

    finite_field_results: list[FiniteFieldCheck] = []
    if finite_field_checks and verification_status != "failed":
        finite_field_results = _run_finite_field_checks(arrangement, max_seconds=max_seconds)

    char0_note = None
    if char0_checks and verification_status != "failed":
        char0_checked, char0_note = _run_char0_checks(arrangement, max_seconds=max_seconds)
        if char0_checked:
            verification_status = "ordinary_node_verified"

    verification_status = _derive_verified_status(verification_status, root)

    notes = _build_notes(verification_status, finite_field_results, char0_note)
    cas_followup = {
        "macaulay2": "m2/verify_smoothing_bridge_genericity.m2",
        "singular": "singular/verify_smoothing_bridge_genericity.sing",
    }
    return SmoothingVerificationRecord(
        arrangement=arrangement.arrangement_id,
        arrangement_equation=str(arrangement_polynomial(arrangement)),
        quartic_Q=candidate_quartic_str(),
        epsilon=str(epsilon_value()),
        verification_status=verification_status,
        G1_avoids_multiple_points=q_avoids,
        G2_squarefree_on_double_lines=all_simple,
        G3_global_singular_locus_checked=(verification_status in {"ordinary_node_verified", "defect_verified"}),
        singular_locus_dimension=None,
        singular_locus_length=None,
        reduced=None,
        ordinary_nodes=None,
        hessian_rank_distribution={},
        finite_field_checks=finite_field_results,
        cas_scripts=cas_followup,
        notes=notes,
        example_id=f"smoothing_bridge_{arrangement.arrangement_id}",
        source_arrangement=arrangement.arrangement_id,
        arrangement_polynomial=str(arrangement_polynomial(arrangement)),
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
    )


def record_to_dict(record: SmoothingVerificationRecord) -> dict:
    return asdict(record)


def build_summary_frame(records: list[SmoothingVerificationRecord]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "example_id": record.example_id,
                "source_arrangement": record.source_arrangement,
                "verification_status": record.verification_status,
                "expected_node_count": record.expected_node_count,
                "double_line_count": record.double_line_count,
                "G1_avoids_multiple_points": record.G1_avoids_multiple_points,
                "G2_squarefree_on_double_lines": record.G2_squarefree_on_double_lines,
                "G3_global_singular_locus_checked": record.G3_global_singular_locus_checked,
                "notes": record.notes,
            }
            for record in records
        ]
    )


def _safe_write_text(path: Path, text: str, *, force: bool) -> VerificationWriteResult:
    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    fallback_dir = path.parents[2] / "paper" / "tables"
    if path.exists() and not force:
        fallback = fallback_dir / f"{path.stem}.fallback_existing_{timestamp}{path.suffix}"
        fallback.write_text(text, encoding="utf-8")
        return VerificationWriteResult(str(path), str(fallback), "fallback_existing", "Primary output existed and --force was not used.")
    if path.exists() and force:
        try:
            path.write_text(text, encoding="utf-8")
            return VerificationWriteResult(str(path), str(path), "replaced_direct")
        except OSError:
            pass

    temp_path = path.with_name(f"{path.name}.tmp")
    try:
        temp_path.write_text(text, encoding="utf-8")
        temp_path.replace(path)
        return VerificationWriteResult(str(path), str(path), "replaced")
    except OSError as exc:
        fallback = fallback_dir / f"{path.stem}.fallback_locked_{timestamp}{path.suffix}"
        try:
            fallback.write_text(text, encoding="utf-8")
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            return VerificationWriteResult(str(path), str(fallback), "fallback_locked", str(exc))
        except OSError as fallback_exc:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            if path.exists():
                return VerificationWriteResult(
                    str(path),
                    str(path),
                    "reused_existing_locked",
                    f"Primary and fallback writes were blocked; existing artifact was left in place. Primary error: {exc}. Fallback error: {fallback_exc}.",
                )
            raise


def run_verification_workflow(
    root: Path,
    *,
    out_dir: Path | None = None,
    arrangements: list[str] | None = None,
    force: bool = False,
    finite_field_checks: bool = False,
    char0_checks: bool = False,
    max_seconds: int | None = None,
) -> VerificationRunResult:
    target_dir = out_dir or (root / "data" / "processed")
    arrangement_ids = arrangements or ["84", "84a"]
    records = [
        build_smoothing_verification(
            arrangement_lookup()[arrangement_id],
            repo_root=root,
            finite_field_checks=finite_field_checks,
            char0_checks=char0_checks,
            max_seconds=max_seconds,
        )
        for arrangement_id in arrangement_ids
    ]
    write_results: list[VerificationWriteResult] = []
    for record in records:
        write_results.append(
            _safe_write_text(
                target_dir / f"smoothing_verification_{record.source_arrangement}.json",
                json.dumps(record_to_dict(record), indent=2),
                force=force,
            )
        )
    summary_text = build_summary_frame(records).to_csv(index=False)
    summary_write = _safe_write_text(target_dir / "smoothing_verification_summary.csv", summary_text, force=force)
    write_results.append(summary_write)
    return VerificationRunResult(records=records, write_results=write_results, summary_path=summary_write.actual_path)


def write_default_verification_outputs(
    root: Path,
    *,
    out_dir: Path | None = None,
    arrangements: list[str] | None = None,
    force: bool = True,
    finite_field_checks: bool = False,
    char0_checks: bool = False,
    max_seconds: int | None = None,
) -> list[SmoothingVerificationRecord]:
    result = run_verification_workflow(
        root,
        out_dir=out_dir,
        arrangements=arrangements,
        force=force,
        finite_field_checks=finite_field_checks,
        char0_checks=char0_checks,
        max_seconds=max_seconds,
    )
    return result.records
