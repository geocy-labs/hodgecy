"""Exact singular-scheme and ordinary-double-point checks.

The backend in this module is intentionally small. It uses SymPy over QQ for
supported exact fixtures, decomposes projective calculations into affine
charts, and keeps candidate-point, support-completeness, reducedness, and ODP
claims as separate certificate levels.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from itertools import product
from pathlib import Path
from typing import Any, Iterable, Sequence

import sympy as sp

from hodgecy.core.results import EvidenceStatus, ResultKind
from hodgecy.storage import CertificateRecord, CalculationRun, ResultStore


class PointClassification(str, Enum):
    SMOOTH = "SMOOTH"
    SINGULAR_UNCLASSIFIED = "SINGULAR_UNCLASSIFIED"
    ORDINARY_DOUBLE_POINT = "ORDINARY_DOUBLE_POINT"
    DEGENERATE_CRITICAL_POINT = "DEGENERATE_CRITICAL_POINT"
    UNKNOWN = "UNKNOWN"


class CompletenessStatus(str, Enum):
    VERIFIED = "verified"
    FAILED = "failed"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class ProjectivePoint:
    coordinates: tuple[sp.Expr, ...]

    def __post_init__(self) -> None:
        normalized = normalize_projective_coordinates(self.coordinates)
        object.__setattr__(self, "coordinates", normalized)

    @classmethod
    def from_iterable(cls, coordinates: Iterable[Any]) -> "ProjectivePoint":
        return cls(tuple(sp.sympify(item) for item in coordinates))

    @property
    def point_id(self) -> str:
        return ":".join(_expr_key(item) for item in self.coordinates)

    def to_dict(self) -> dict[str, Any]:
        return {
            "coordinates": [_expr_key(item) for item in self.coordinates],
            "point_id": self.point_id,
        }


@dataclass(frozen=True, slots=True)
class ProjectiveHypersurface:
    variables: tuple[str, ...]
    homogeneous_polynomial: str
    geometry_id: str | None = None
    coefficient_ring: str = "QQ"
    projective_weights: tuple[int, ...] | None = None
    parameter_specialization: dict[str, str] = field(default_factory=dict)
    model_notes: str | None = None

    @property
    def symbols(self) -> tuple[sp.Symbol, ...]:
        return sp.symbols(" ".join(self.variables))

    @property
    def polynomial(self) -> sp.Expr:
        locals_map = {name: symbol for name, symbol in zip(self.variables, self.symbols)}
        return sp.expand(sp.sympify(self.homogeneous_polynomial, locals=locals_map))

    def singular_ideal_generators(self) -> tuple[sp.Expr, ...]:
        poly = self.polynomial
        return (poly,) + tuple(sp.expand(sp.diff(poly, var)) for var in self.symbols)

    def validate_homogeneous(self) -> None:
        poly = sp.Poly(self.polynomial, *self.symbols, domain=self.coefficient_ring)
        degrees = {sum(monomial) for monomial, coeff in zip(poly.monoms(), poly.coeffs()) if coeff != 0}
        if len(degrees) > 1:
            raise ValueError("ProjectiveHypersurface polynomial must be homogeneous.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "geometry_id": self.geometry_id,
            "variables": list(self.variables),
            "homogeneous_polynomial": self.homogeneous_polynomial,
            "coefficient_ring": self.coefficient_ring,
            "projective_weights": None if self.projective_weights is None else list(self.projective_weights),
            "parameter_specialization": dict(self.parameter_specialization),
            "model_notes": self.model_notes,
        }


@dataclass(frozen=True, slots=True)
class DoubleCoverModel:
    base_variables: tuple[str, ...]
    branch_polynomial: str
    cover_variable: str = "w"
    coefficient_ring: str = "QQ"
    parameter_specialization: dict[str, str] = field(default_factory=dict)
    theorem_note: str = "For char 0 local models w^2 = F(u), a nondegenerate branch Hessian gives a nondegenerate total-space Hessian for w^2 - F."

    @property
    def symbols(self) -> tuple[sp.Symbol, ...]:
        return sp.symbols(" ".join((self.cover_variable,) + self.base_variables))

    @property
    def base_symbols(self) -> tuple[sp.Symbol, ...]:
        return sp.symbols(" ".join(self.base_variables))

    @property
    def branch_expr(self) -> sp.Expr:
        locals_map = {name: symbol for name, symbol in zip(self.base_variables, self.base_symbols)}
        return sp.expand(sp.sympify(self.branch_polynomial, locals=locals_map))

    def total_space_polynomial(self) -> sp.Expr:
        cover_symbol = sp.Symbol(self.cover_variable)
        return sp.expand(cover_symbol**2 - self.branch_expr)


@dataclass(frozen=True, slots=True)
class PointSingularityCertificate:
    point_id: str
    exact_coordinates: tuple[str, ...]
    projective_chart: str | None
    F_value: str
    gradient_values: tuple[str, ...]
    hessian_matrix: tuple[tuple[str, ...], ...]
    hessian_rank: int | None
    hessian_determinant: str | None
    ambient_local_dimension: int
    classification: PointClassification
    method: str
    evidence_status: EvidenceStatus
    notes: str | None = None

    @property
    def ordinary_double_point(self) -> bool:
        return self.classification is PointClassification.ORDINARY_DOUBLE_POINT

    def to_dict(self) -> dict[str, Any]:
        return {
            "point_id": self.point_id,
            "exact_coordinates": list(self.exact_coordinates),
            "projective_chart": self.projective_chart,
            "F_value": self.F_value,
            "gradient_values": list(self.gradient_values),
            "hessian_matrix": [list(row) for row in self.hessian_matrix],
            "hessian_rank": self.hessian_rank,
            "hessian_determinant": self.hessian_determinant,
            "ambient_local_dimension": self.ambient_local_dimension,
            "classification": self.classification.value,
            "ordinary_double_point": self.ordinary_double_point,
            "method": self.method,
            "evidence_status": self.evidence_status.value,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class SingularSchemeResult:
    geometry_id: str | None
    singular_ideal_generators: tuple[str, ...]
    dimension: int | None
    degree: int | None
    support: tuple[ProjectivePoint, ...]
    is_zero_dimensional: bool | None
    is_reduced: bool | None
    is_complete: bool | None
    candidate_support_complete: bool | None
    backend: str
    evidence_status: EvidenceStatus
    certificates: tuple[dict[str, Any], ...] = ()
    chart_reports: tuple[dict[str, Any], ...] = ()
    notes: str | None = None

    @property
    def support_cardinality(self) -> int:
        return len(self.support)

    def to_dict(self) -> dict[str, Any]:
        return {
            "geometry_id": self.geometry_id,
            "singular_ideal_generators": list(self.singular_ideal_generators),
            "dimension": self.dimension,
            "degree": self.degree,
            "support": [point.to_dict() for point in self.support],
            "support_cardinality": self.support_cardinality,
            "is_zero_dimensional": self.is_zero_dimensional,
            "is_reduced": self.is_reduced,
            "is_complete": self.is_complete,
            "candidate_support_complete": self.candidate_support_complete,
            "backend": self.backend,
            "evidence_status": self.evidence_status.value,
            "certificates": list(self.certificates),
            "chart_reports": list(self.chart_reports),
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class FiniteReducedODPSchemeCertificate:
    geometry_id: str | None
    zero_dimensional: bool | None
    support_complete: bool | None
    reduced: bool | None
    every_support_point_odp: bool | None
    evidence_status: EvidenceStatus
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "geometry_id": self.geometry_id,
            "zero_dimensional": self.zero_dimensional,
            "support_complete": self.support_complete,
            "reduced": self.reduced,
            "every_support_point_odp": self.every_support_point_odp,
            "evidence_status": self.evidence_status.value,
            "reason": self.reason,
        }


def normalize_projective_coordinates(coordinates: Sequence[Any]) -> tuple[sp.Expr, ...]:
    values = tuple(sp.simplify(sp.sympify(item)) for item in coordinates)
    if not values or all(value == 0 for value in values):
        raise ValueError("Projective point cannot have all coordinates zero.")
    pivot = next(value for value in values if value != 0)
    return tuple(sp.simplify(value / pivot) for value in values)


def unique_projective_points(points: Iterable[ProjectivePoint | Sequence[Any]]) -> tuple[ProjectivePoint, ...]:
    unique: dict[str, ProjectivePoint] = {}
    for point in points:
        normalized = point if isinstance(point, ProjectivePoint) else ProjectivePoint.from_iterable(point)
        unique[normalized.point_id] = normalized
    return tuple(unique[key] for key in sorted(unique))


def classify_affine_hypersurface_point(
    polynomial: Any,
    variables: Sequence[Any],
    point: Sequence[Any],
    *,
    method: str = "exact affine Hessian over QQ",
    point_id: str | None = None,
    projective_chart: str | None = None,
    exact_coordinates: Sequence[str] | None = None,
) -> PointSingularityCertificate:
    symbols = tuple(sp.Symbol(str(var)) for var in variables)
    locals_map = {str(symbol): symbol for symbol in symbols}
    poly = sp.expand(sp.sympify(polynomial, locals=locals_map))
    coords = tuple(sp.simplify(sp.sympify(item)) for item in point)
    substitutions = dict(zip(symbols, coords))
    f_value = sp.simplify(poly.subs(substitutions))
    gradient = tuple(sp.simplify(sp.diff(poly, symbol).subs(substitutions)) for symbol in symbols)
    hessian = tuple(
        tuple(sp.simplify(sp.diff(sp.diff(poly, left), right).subs(substitutions)) for right in symbols)
        for left in symbols
    )
    matrix = sp.Matrix(hessian)
    hessian_rank = int(matrix.rank()) if symbols else 0
    determinant = sp.simplify(matrix.det()) if matrix.rows == matrix.cols else None
    singular = f_value == 0 and all(value == 0 for value in gradient)
    if not singular:
        classification = PointClassification.SMOOTH
    elif determinant is not None and determinant != 0 and hessian_rank == len(symbols):
        classification = PointClassification.ORDINARY_DOUBLE_POINT
    elif determinant == 0 or hessian_rank < len(symbols):
        classification = PointClassification.DEGENERATE_CRITICAL_POINT
    else:
        classification = PointClassification.SINGULAR_UNCLASSIFIED
    return PointSingularityCertificate(
        point_id=point_id or ",".join(_expr_key(item) for item in coords),
        exact_coordinates=tuple(exact_coordinates or tuple(_expr_key(item) for item in coords)),
        projective_chart=projective_chart,
        F_value=_expr_key(f_value),
        gradient_values=tuple(_expr_key(item) for item in gradient),
        hessian_matrix=tuple(tuple(_expr_key(item) for item in row) for row in hessian),
        hessian_rank=hessian_rank,
        hessian_determinant=None if determinant is None else _expr_key(determinant),
        ambient_local_dimension=len(symbols),
        classification=classification,
        method=method,
        evidence_status=EvidenceStatus.VERIFIED,
    )


def classify_projective_hypersurface_point(
    hypersurface: ProjectiveHypersurface,
    point: Sequence[Any] | ProjectivePoint,
    *,
    chart_index: int | None = None,
) -> PointSingularityCertificate:
    hypersurface.validate_homogeneous()
    projective_point = point if isinstance(point, ProjectivePoint) else ProjectivePoint.from_iterable(point)
    symbols = hypersurface.symbols
    if len(projective_point.coordinates) != len(symbols):
        raise ValueError("Point coordinate count must match hypersurface variables.")
    chart = chart_index
    if chart is None:
        chart = next(index for index, value in enumerate(projective_point.coordinates) if value != 0)
    if projective_point.coordinates[chart] == 0:
        raise ValueError("Chosen projective chart does not contain the point.")

    normalized_for_chart = tuple(sp.simplify(value / projective_point.coordinates[chart]) for value in projective_point.coordinates)
    local_symbols = tuple(sp.Symbol(str(symbol)) for index, symbol in enumerate(symbols) if index != chart)
    substitutions = {}
    local_point = []
    local_iter = iter(local_symbols)
    for index, symbol in enumerate(symbols):
        if index == chart:
            substitutions[symbol] = sp.Integer(1)
        else:
            local_symbol = next(local_iter)
            substitutions[symbol] = local_symbol
            local_point.append(normalized_for_chart[index])
    local_polynomial = sp.expand(hypersurface.polynomial.subs(substitutions))
    homogeneous_subs = dict(zip(symbols, projective_point.coordinates))
    homogeneous_f_value = sp.simplify(hypersurface.polynomial.subs(homogeneous_subs))
    homogeneous_gradient = tuple(sp.simplify(sp.diff(hypersurface.polynomial, symbol).subs(homogeneous_subs)) for symbol in symbols)

    certificate = classify_affine_hypersurface_point(
        local_polynomial,
        local_symbols,
        local_point,
        method="exact projective affine-chart Hessian over QQ",
        point_id=projective_point.point_id,
        projective_chart=str(symbols[chart]),
        exact_coordinates=tuple(_expr_key(item) for item in projective_point.coordinates),
    )
    if homogeneous_f_value != 0 or any(value != 0 for value in homogeneous_gradient):
        return PointSingularityCertificate(
            point_id=certificate.point_id,
            exact_coordinates=certificate.exact_coordinates,
            projective_chart=certificate.projective_chart,
            F_value=_expr_key(homogeneous_f_value),
            gradient_values=tuple(_expr_key(item) for item in homogeneous_gradient),
            hessian_matrix=certificate.hessian_matrix,
            hessian_rank=certificate.hessian_rank,
            hessian_determinant=certificate.hessian_determinant,
            ambient_local_dimension=certificate.ambient_local_dimension,
            classification=PointClassification.SMOOTH,
            method=certificate.method,
            evidence_status=certificate.evidence_status,
            notes="Projective F or gradient is nonzero; local Hessian is not promoted to singular classification.",
        )
    return PointSingularityCertificate(
        point_id=certificate.point_id,
        exact_coordinates=certificate.exact_coordinates,
        projective_chart=certificate.projective_chart,
        F_value=_expr_key(homogeneous_f_value),
        gradient_values=tuple(_expr_key(item) for item in homogeneous_gradient),
        hessian_matrix=certificate.hessian_matrix,
        hessian_rank=certificate.hessian_rank,
        hessian_determinant=certificate.hessian_determinant,
        ambient_local_dimension=certificate.ambient_local_dimension,
        classification=certificate.classification,
        method=certificate.method,
        evidence_status=certificate.evidence_status,
        notes=certificate.notes,
    )


def analyze_projective_singular_scheme(
    hypersurface: ProjectiveHypersurface,
    *,
    candidate_points: Iterable[Sequence[Any] | ProjectivePoint] | None = None,
) -> SingularSchemeResult:
    hypersurface.validate_homogeneous()
    symbols = hypersurface.symbols
    support_hits: list[ProjectivePoint] = []
    chart_reports: list[dict[str, Any]] = []
    total_degree = 0
    all_charts_zero_dimensional = True
    all_charts_solved = True
    duplicate_hits = False

    for chart_index, chart_symbol in enumerate(symbols):
        local_symbols = tuple(sp.Symbol(str(symbol)) for index, symbol in enumerate(symbols) if index != chart_index)
        substitutions: dict[sp.Symbol, sp.Expr] = {}
        local_iter = iter(local_symbols)
        for index, symbol in enumerate(symbols):
            if index == chart_index:
                substitutions[symbol] = sp.Integer(1)
            else:
                substitutions[symbol] = next(local_iter)
        local_polynomial = sp.expand(hypersurface.polynomial.subs(substitutions))
        generators = (local_polynomial,) + tuple(sp.expand(sp.diff(local_polynomial, symbol)) for symbol in local_symbols)
        try:
            groebner = sp.groebner(generators, *local_symbols, domain=hypersurface.coefficient_ring)
        except Exception as exc:
            all_charts_zero_dimensional = False
            all_charts_solved = False
            chart_reports.append({"chart": str(chart_symbol), "status": "backend_error", "reason": str(exc)})
            continue
        if _is_unit_ideal(groebner):
            chart_reports.append({"chart": str(chart_symbol), "status": "empty", "degree": 0, "support": []})
            continue
        if not groebner.is_zero_dimensional:
            all_charts_zero_dimensional = False
            all_charts_solved = False
            chart_reports.append({"chart": str(chart_symbol), "status": "positive_dimensional", "is_zero_dimensional": False})
            continue
        degree = _zero_dimensional_degree(groebner, local_symbols)
        if degree is not None:
            total_degree += degree
        try:
            local_solutions = sp.solve_poly_system(generators, *local_symbols)
        except NotImplementedError as exc:
            all_charts_solved = False
            local_solutions = []
            chart_reports.append({"chart": str(chart_symbol), "status": "zero_dimensional_unsolved", "degree": degree, "reason": str(exc)})
        else:
            chart_points = []
            for solution in local_solutions or []:
                coords: list[sp.Expr] = []
                solution_iter = iter(solution)
                for index in range(len(symbols)):
                    coords.append(sp.Integer(1) if index == chart_index else sp.simplify(next(solution_iter)))
                point = ProjectivePoint(tuple(coords))
                if any(existing.point_id == point.point_id for existing in support_hits):
                    duplicate_hits = True
                support_hits.append(point)
                chart_points.append(point.to_dict())
            chart_reports.append({"chart": str(chart_symbol), "status": "zero_dimensional_solved", "degree": degree, "support": chart_points})

    support = unique_projective_points(support_hits)
    candidate_support_complete = None
    if candidate_points is not None:
        candidate_support = unique_projective_points(candidate_points)
        if not all_charts_zero_dimensional or not all_charts_solved:
            candidate_support_complete = None
        else:
            candidate_support_complete = {point.point_id for point in candidate_support} == {point.point_id for point in support}

    if not all_charts_zero_dimensional:
        dimension = None
        degree = None
        is_complete = False
        evidence_status = EvidenceStatus.COMPUTED
        reduced = None
    else:
        dimension = 0
        degree = total_degree
        is_complete = all_charts_solved
        evidence_status = EvidenceStatus.VERIFIED if all_charts_solved else EvidenceStatus.COMPUTED
        if not all_charts_solved or duplicate_hits:
            reduced = None
        else:
            reduced = degree == len(support)
    certificates = (
        {
            "certificate_type": "projective_chart_singular_scheme",
            "zero_dimensional": all_charts_zero_dimensional,
            "support_complete": is_complete,
            "reducedness_method": "degree_equals_distinct_support_after_exact_chart_solve" if reduced is not None else "not_certified",
            "euler_relation_convention": "F is retained explicitly with affine-chart derivatives even though homogeneous F is redundant in characteristic zero.",
        },
    )
    return SingularSchemeResult(
        geometry_id=hypersurface.geometry_id,
        singular_ideal_generators=tuple(_expr_key(item) for item in hypersurface.singular_ideal_generators()),
        dimension=dimension,
        degree=degree,
        support=support,
        is_zero_dimensional=all_charts_zero_dimensional,
        is_reduced=reduced,
        is_complete=is_complete,
        candidate_support_complete=candidate_support_complete,
        backend="sympy.projective_affine_charts.QQ",
        evidence_status=evidence_status,
        certificates=certificates,
        chart_reports=tuple(chart_reports),
        notes="Projective origin is excluded by affine-chart cover.",
    )


def certify_double_cover_odp(
    model: DoubleCoverModel,
    branch_point: Sequence[Any],
    *,
    branch_certificate: PointSingularityCertificate | None = None,
) -> dict[str, Any]:
    base_symbols = model.base_symbols
    cover_symbol = sp.Symbol(model.cover_variable)
    all_symbols = (cover_symbol,) + base_symbols
    total_polynomial = model.total_space_polynomial()
    point = (sp.Integer(0),) + tuple(sp.sympify(item) for item in branch_point)
    total_certificate = classify_affine_hypersurface_point(
        total_polynomial,
        all_symbols,
        point,
        method="exact double-cover total-space Hessian over QQ",
    )
    branch = branch_certificate or classify_affine_hypersurface_point(
        model.branch_expr,
        base_symbols,
        branch_point,
        method="exact branch Hessian over QQ",
    )
    verified = branch.ordinary_double_point and total_certificate.ordinary_double_point
    return {
        "certificate_type": "double_cover_odp",
        "branch_singularity_classification": branch.classification.value,
        "double_cover_total_space_classification": total_certificate.classification.value,
        "total_space_hessian_rank": total_certificate.hessian_rank,
        "total_space_hessian_determinant": total_certificate.hessian_determinant,
        "evidence_status": EvidenceStatus.VERIFIED.value if verified else EvidenceStatus.COMPUTED.value,
        "verified": verified,
        "method": "explicit local equation G(w,u)=w^2-F(u), char 0 Hessian test including w direction",
        "theorem_note": model.theorem_note,
        "branch_certificate": branch.to_dict(),
        "total_space_certificate": total_certificate.to_dict(),
        "parameter_specialization": dict(model.parameter_specialization),
    }


def global_finite_reduced_odp_certificate(
    scheme: SingularSchemeResult,
    point_certificates: Sequence[PointSingularityCertificate],
) -> FiniteReducedODPSchemeCertificate:
    every_odp = bool(point_certificates) and len(point_certificates) == scheme.support_cardinality and all(item.ordinary_double_point for item in point_certificates)
    prerequisites = {
        "zero_dimensional": scheme.is_zero_dimensional is True,
        "support_complete": scheme.is_complete is True,
        "reduced": scheme.is_reduced is True,
        "every_support_point_odp": every_odp,
    }
    if all(prerequisites.values()):
        return FiniteReducedODPSchemeCertificate(
            scheme.geometry_id,
            True,
            True,
            True,
            True,
            EvidenceStatus.VERIFIED,
            "zero-dimensional, complete, reduced, and every support point has nondegenerate affine-chart Hessian",
        )
    return FiniteReducedODPSchemeCertificate(
        scheme.geometry_id,
        scheme.is_zero_dimensional,
        scheme.is_complete,
        scheme.is_reduced,
        every_odp,
        EvidenceStatus.UNKNOWN,
        "global finite reduced ODP certificate withheld because at least one prerequisite is not verified",
    )


def persist_singular_scheme_result(
    store: ResultStore,
    *,
    run_id: str,
    scheme: SingularSchemeResult,
    point_certificates: Sequence[PointSingularityCertificate] = (),
) -> tuple[CertificateRecord, tuple[Any, ...]]:
    run = store.get_run(run_id)
    global_cert = global_finite_reduced_odp_certificate(scheme, point_certificates)
    certificate = store.record_certificate(
        certificate_type="finite_reduced_odp_scheme",
        subject_type="geometry",
        subject_id=run.geometry_id,
        method="hodgecy.geometry.singularities",
        evidence={
            "scheme": scheme.to_dict(),
            "point_certificates": [item.to_dict() for item in point_certificates],
            "global_certificate": global_cert.to_dict(),
        },
        generated_by_run_id=run_id,
        notes=global_cert.reason,
    )
    invariants = []
    rows = (
        ("singular_scheme_dimension", scheme.dimension, _status_for_known(scheme.dimension, scheme.evidence_status)),
        ("singular_scheme_degree", scheme.degree, _status_for_known(scheme.degree, scheme.evidence_status)),
        ("singular_support_cardinality", scheme.support_cardinality if scheme.is_complete else None, EvidenceStatus.VERIFIED if scheme.is_complete else EvidenceStatus.UNKNOWN),
        ("singular_scheme_reduced", scheme.is_reduced, _bool_status(scheme.is_reduced)),
        ("singular_support_complete", scheme.is_complete, _bool_status(scheme.is_complete)),
        ("candidate_support_complete", scheme.candidate_support_complete, _bool_status(scheme.candidate_support_complete)),
        ("pointwise_odp_verified_count", sum(1 for item in point_certificates if item.ordinary_double_point), EvidenceStatus.VERIFIED if point_certificates else EvidenceStatus.UNKNOWN),
        ("all_points_odp", global_cert.every_support_point_odp if point_certificates else None, EvidenceStatus.VERIFIED if global_cert.every_support_point_odp else EvidenceStatus.UNKNOWN),
        ("finite_reduced_odp_scheme", global_cert.evidence_status is EvidenceStatus.VERIFIED, global_cert.evidence_status),
    )
    for name, value, status in rows:
        invariants.append(
            store.record_invariant(
                run_id=run_id,
                name=name,
                value=value,
                result_kind=ResultKind.NODE_GEOMETRY,
                evidence_status=status,
                method="hodgecy.geometry.singularities",
                certificate_id=certificate.certificate_id,
                notes="Blob 5 node-geometry invariant; no node-relation, defect, or Hodge-atom promotion.",
            )
        )
    return certificate, tuple(invariants)


def begin_node_geometry_run(store: ResultStore, geometry_id: str, *, input_metadata: Any, parameters: Any | None = None, notes: str | None = None) -> CalculationRun:
    return store.begin_run(
        geometry_id=geometry_id,
        calculation_type="node_geometry_singular_scheme_odp",
        input_metadata=input_metadata,
        parameters=parameters,
        backend="hodgecy.geometry.singularities",
        coefficient_ring="QQ",
        notes=notes,
    )


def _zero_dimensional_degree(groebner: Any, variables: Sequence[sp.Symbol]) -> int | None:
    leading_monomials = [tuple(int(exp) for exp in poly.LM(order=groebner.order)) for poly in groebner.polys]
    if any(all(exp == 0 for exp in monomial) for monomial in leading_monomials):
        return 0
    bounds: list[int] = []
    for index in range(len(variables)):
        pure_powers = [
            monomial[index]
            for monomial in leading_monomials
            if monomial[index] > 0 and all(exp == 0 for pos, exp in enumerate(monomial) if pos != index)
        ]
        if not pure_powers:
            return None
        bounds.append(min(pure_powers))
    degree = 0
    for exponents in product(*(range(bound) for bound in bounds)):
        if not any(_monomial_divides(leading, exponents) for leading in leading_monomials):
            degree += 1
    return degree


def _monomial_divides(left: Sequence[int], right: Sequence[int]) -> bool:
    return all(a <= b for a, b in zip(left, right))


def _is_unit_ideal(groebner: Any) -> bool:
    return any(all(int(exp) == 0 for exp in poly.LM(order=groebner.order)) for poly in groebner.polys)


def _status_for_known(value: Any, status: EvidenceStatus) -> EvidenceStatus:
    return EvidenceStatus.UNKNOWN if value is None else status


def _bool_status(value: bool | None) -> EvidenceStatus:
    if value is None:
        return EvidenceStatus.UNKNOWN
    return EvidenceStatus.VERIFIED


def _expr_key(value: Any) -> str:
    return str(sp.simplify(value))
