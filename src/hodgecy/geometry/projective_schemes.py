"""Finite projective-scheme ideals and Hilbert functions.

Blob 6 keeps this layer deliberately narrow: exact homogeneous ideals over QQ,
Groebner initial monomials, standard-monomial Hilbert functions, and explicit
provenance for how a scheme ideal was obtained.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from itertools import product
from math import comb
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Iterable, Sequence

import sympy as sp

from hodgecy.core.results import ComparisonState, EvidenceStatus, ResultKind
from hodgecy.core.serialization import canonical_json, stable_sha256
from hodgecy.geometry.singularities import ProjectivePoint, SingularSchemeResult
from hodgecy.storage import ArtifactRecord, CertificateRecord, CalculationRun, ResultStore


class IdealSource(str, Enum):
    JACOBIAN = "jacobian"
    EXPLICIT = "explicit"
    POINT_INTERSECTION = "point_intersection"
    IMPORTED = "imported"


class SchemeSupportStatus(str, Enum):
    CANDIDATE = "candidate"
    COMPLETE = "complete"
    CERTIFIED_SUPPORT = "certified_support"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class IdealComparisonState(str, Enum):
    EQUAL = "equal"
    DIFFERENT = "different"
    UNKNOWN = "unknown"


class ExactSchemeIdealUnavailableError(ValueError):
    """Raised when Blob 5 data do not contain enough exact ideal information."""


@dataclass(frozen=True, slots=True)
class ProjectiveSchemeIdeal:
    variables: tuple[str, ...]
    homogeneous_generators: tuple[str, ...]
    geometry_id: str | None = None
    base_field: str = "QQ"
    ideal_source: IdealSource = IdealSource.EXPLICIT
    is_saturated: bool | None = None
    scheme_dimension: int | None = None
    scheme_degree: int | None = None
    support_cardinality: int | None = None
    support_status: SchemeSupportStatus = SchemeSupportStatus.UNKNOWN
    evidence_status: EvidenceStatus = EvidenceStatus.COMPUTED
    provenance: str | None = None
    certificates: tuple[dict[str, Any], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "ideal_source", IdealSource(self.ideal_source))
        object.__setattr__(self, "support_status", SchemeSupportStatus(self.support_status))
        object.__setattr__(self, "evidence_status", EvidenceStatus(self.evidence_status))
        self.validate()

    @property
    def ambient_dimension(self) -> int:
        return len(self.variables) - 1

    @property
    def symbols(self) -> tuple[sp.Symbol, ...]:
        return sp.symbols(" ".join(self.variables))

    @property
    def generator_exprs(self) -> tuple[sp.Expr, ...]:
        locals_map = {name: symbol for name, symbol in zip(self.variables, self.symbols)}
        return tuple(sp.expand(sp.sympify(generator, locals=locals_map)) for generator in self.homogeneous_generators)

    @property
    def ideal_hash(self) -> str:
        return stable_sha256(
            {
                "base_field": self.base_field,
                "variables": self.variables,
                "generators": [canonical_expr(generator) for generator in self.generator_exprs],
                "ideal_source": self.ideal_source.value,
            }
        )

    def validate(self) -> None:
        if self.base_field != "QQ":
            raise ValueError(f"Unsupported exact base field for Blob 6: {self.base_field!r}")
        if len(self.variables) < 2:
            raise ValueError("A projective scheme ideal requires at least two homogeneous variables.")
        if not self.homogeneous_generators:
            raise ValueError("A projective scheme ideal requires at least one homogeneous generator.")
        _ = self.generator_exprs
        for generator in self.generator_exprs:
            if not is_homogeneous(generator, self.symbols):
                raise ValueError(f"Projective ideal generator is not homogeneous: {generator}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "geometry_id": self.geometry_id,
            "base_field": self.base_field,
            "variables": list(self.variables),
            "homogeneous_generators": list(self.homogeneous_generators),
            "ambient_dimension": self.ambient_dimension,
            "ideal_source": self.ideal_source.value,
            "is_saturated": self.is_saturated,
            "scheme_dimension": self.scheme_dimension,
            "scheme_degree": self.scheme_degree,
            "support_cardinality": self.support_cardinality,
            "support_status": self.support_status.value,
            "evidence_status": self.evidence_status.value,
            "provenance": self.provenance,
            "certificates": list(self.certificates),
            "ideal_hash": self.ideal_hash,
        }

    @classmethod
    def from_singular_scheme(cls, result: SingularSchemeResult, *, variables: Sequence[str]) -> "ProjectiveSchemeIdeal":
        if not result.singular_ideal_generators:
            raise ExactSchemeIdealUnavailableError("SingularSchemeResult does not include exact homogeneous ideal generators.")
        if result.evidence_status not in {EvidenceStatus.VERIFIED, EvidenceStatus.COMPUTED}:
            raise ExactSchemeIdealUnavailableError("SingularSchemeResult is not an exact computed/verified ideal source.")
        return cls(
            geometry_id=result.geometry_id,
            variables=tuple(str(item) for item in variables),
            homogeneous_generators=tuple(result.singular_ideal_generators),
            ideal_source=IdealSource.JACOBIAN,
            is_saturated=None,
            scheme_dimension=result.dimension,
            scheme_degree=result.degree,
            support_cardinality=result.support_cardinality if result.is_complete else None,
            support_status=SchemeSupportStatus.CERTIFIED_SUPPORT if result.is_complete else SchemeSupportStatus.UNKNOWN,
            evidence_status=result.evidence_status,
            provenance="converted from Blob 5 SingularSchemeResult",
            certificates=result.certificates,
        )


@dataclass(frozen=True, slots=True)
class GroebnerBasisData:
    ideal_hash: str
    variables: tuple[str, ...]
    basis_generators: tuple[str, ...]
    leading_monomials: tuple[tuple[int, ...], ...]
    term_order: str
    backend: str
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ideal_hash": self.ideal_hash,
            "variables": list(self.variables),
            "basis_generators": list(self.basis_generators),
            "leading_monomials": [list(item) for item in self.leading_monomials],
            "term_order": self.term_order,
            "backend": self.backend,
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True, slots=True)
class HilbertFunctionValue:
    degree: int
    dim_S_d: int
    dim_I_d: int
    dim_quotient_d: int
    evidence_status: EvidenceStatus
    method: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "degree": self.degree,
            "dim_S_d": self.dim_S_d,
            "dim_I_d": self.dim_I_d,
            "dim_quotient_d": self.dim_quotient_d,
            "evidence_status": self.evidence_status.value,
            "method": self.method,
        }


@dataclass(frozen=True, slots=True)
class HilbertFunctionTable:
    ideal_hash: str
    values: tuple[HilbertFunctionValue, ...]
    ambient_dimension: int
    scheme_dimension: int | None
    scheme_degree: int | None
    observed_constant_tail: dict[str, Any] | None
    certified_stabilization_degree: int | None
    backend: str
    term_order: str
    evidence_status: EvidenceStatus
    certificate: dict[str, Any] = field(default_factory=dict)

    def value_at(self, degree: int) -> int | None:
        for value in self.values:
            if value.degree == degree:
                return value.dim_quotient_d
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ideal_hash": self.ideal_hash,
            "values": [value.to_dict() for value in self.values],
            "ambient_dimension": self.ambient_dimension,
            "scheme_dimension": self.scheme_dimension,
            "scheme_degree": self.scheme_degree,
            "observed_constant_tail": self.observed_constant_tail,
            "certified_stabilization_degree": self.certified_stabilization_degree,
            "backend": self.backend,
            "term_order": self.term_order,
            "evidence_status": self.evidence_status.value,
            "certificate": self.certificate,
        }


@dataclass(frozen=True, slots=True)
class HilbertComparisonResult:
    state: ComparisonState
    first_differing_degree: int | None
    compared_degrees: tuple[int, ...]
    left_values: dict[int, int | None]
    right_values: dict[int, int | None]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "first_differing_degree": self.first_differing_degree,
            "compared_degrees": list(self.compared_degrees),
            "left_values": {str(k): v for k, v in self.left_values.items()},
            "right_values": {str(k): v for k, v in self.right_values.items()},
            "reason": self.reason,
        }


def is_homogeneous(expression: sp.Expr, variables: Sequence[sp.Symbol]) -> bool:
    if expression == 0:
        return True
    poly = sp.Poly(expression, *variables, domain="QQ")
    degrees = {sum(monomial) for monomial, coeff in zip(poly.monoms(), poly.coeffs()) if coeff != 0}
    return len(degrees) <= 1


def point_ideal(point: ProjectivePoint | Sequence[Any], variables: Sequence[str]) -> ProjectiveSchemeIdeal:
    projective_point = point if isinstance(point, ProjectivePoint) else ProjectivePoint.from_iterable(point)
    coords = projective_point.coordinates
    if len(coords) != len(variables):
        raise ValueError("Point coordinate count must match the declared variables.")
    pivot_index = next(index for index, value in enumerate(coords) if value != 0)
    generators = []
    pivot_var = variables[pivot_index]
    pivot_value = coords[pivot_index]
    for index, (variable, value) in enumerate(zip(variables, coords)):
        if index == pivot_index:
            continue
        generators.append(canonical_expr(pivot_value * sp.Symbol(variable) - value * sp.Symbol(pivot_var)))
    return ProjectiveSchemeIdeal(
        variables=tuple(variables),
        homogeneous_generators=tuple(generators),
        ideal_source=IdealSource.POINT_INTERSECTION,
        is_saturated=True,
        scheme_dimension=0,
        scheme_degree=1,
        support_cardinality=1,
        support_status=SchemeSupportStatus.CERTIFIED_SUPPORT,
        evidence_status=EvidenceStatus.VERIFIED,
        provenance=f"homogeneous ideal of projective point {projective_point.point_id}",
    )


def ideal_of_points(
    points: Iterable[ProjectivePoint | Sequence[Any]],
    variables: Sequence[str],
    *,
    support_status: SchemeSupportStatus = SchemeSupportStatus.CANDIDATE,
    geometry_id: str | None = None,
) -> ProjectiveSchemeIdeal:
    unique = _unique_points(points)
    if not unique:
        raise ValueError("Cannot build an ideal from an empty point set.")
    ideals = [point_ideal(point, variables) for point in unique]
    generators = tuple(ideals[0].homogeneous_generators)
    for ideal in ideals[1:]:
        generators = _intersect_homogeneous_ideals(generators, ideal.homogeneous_generators, tuple(variables))
    return ProjectiveSchemeIdeal(
        geometry_id=geometry_id,
        variables=tuple(variables),
        homogeneous_generators=generators,
        ideal_source=IdealSource.POINT_INTERSECTION,
        is_saturated=True,
        scheme_dimension=0,
        scheme_degree=len(unique),
        support_cardinality=len(unique),
        support_status=support_status,
        evidence_status=EvidenceStatus.VERIFIED if support_status is SchemeSupportStatus.CERTIFIED_SUPPORT else EvidenceStatus.COMPUTED,
        provenance="exact intersection of homogeneous projective point ideals",
        certificates=(
            {
                "certificate_type": "point_intersection_ideal",
                "point_count": len(unique),
                "support_status": support_status.value,
                "warning": "candidate point-set ideal is not automatically a complete singular-scheme ideal",
            },
        ),
    )


def groebner_basis_data(ideal: ProjectiveSchemeIdeal, *, order: str = "grevlex") -> GroebnerBasisData:
    basis = sp.groebner(ideal.generator_exprs, *ideal.symbols, order=order, domain=ideal.base_field)
    basis_generators = tuple(canonical_expr(poly.as_expr()) for poly in basis.polys)
    leading = tuple(tuple(int(exp) for exp in poly.LM(order=basis.order)) for poly in basis.polys)
    payload = {
        "ideal_hash": ideal.ideal_hash,
        "variables": ideal.variables,
        "basis_generators": basis_generators,
        "leading_monomials": leading,
        "term_order": order,
        "backend": "sympy.groebner",
    }
    return GroebnerBasisData(
        ideal_hash=ideal.ideal_hash,
        variables=ideal.variables,
        basis_generators=basis_generators,
        leading_monomials=leading,
        term_order=order,
        backend="sympy.groebner",
        content_hash=stable_sha256(payload),
    )


def hilbert_function(ideal: ProjectiveSchemeIdeal, degree: int, *, order: str = "grevlex") -> HilbertFunctionValue:
    if degree < 0:
        raise ValueError("Hilbert function degree must be nonnegative.")
    gb = groebner_basis_data(ideal, order=order)
    dim_s = comb(ideal.ambient_dimension + degree, ideal.ambient_dimension)
    quotient = count_standard_monomials(ideal.ambient_dimension + 1, degree, gb.leading_monomials)
    return HilbertFunctionValue(
        degree=degree,
        dim_S_d=dim_s,
        dim_I_d=dim_s - quotient,
        dim_quotient_d=quotient,
        evidence_status=EvidenceStatus.VERIFIED,
        method="standard monomial count from exact Groebner initial ideal over QQ",
    )


def hilbert_function_range(ideal: ProjectiveSchemeIdeal, *, start: int = 0, stop: int, order: str = "grevlex") -> HilbertFunctionTable:
    if start < 0 or stop < start:
        raise ValueError("Require 0 <= start <= stop for Hilbert function range.")
    gb = groebner_basis_data(ideal, order=order)
    values = tuple(
        _hilbert_value_from_groebner(ideal, degree, gb)
        for degree in range(start, stop + 1)
    )
    observed_tail = _observed_constant_tail(values, ideal.scheme_degree)
    certified = None
    certificate: dict[str, Any] = {
        "certificate_type": "hilbert_function",
        "coefficient_field": ideal.base_field,
        "term_order": order,
        "backend": gb.backend,
        "ideal_hash": ideal.ideal_hash,
        "algorithm": "count degree-d monomials not divisible by initial monomial ideal",
        "groebner_basis_hash": gb.content_hash,
        "stabilization_note": "constant tails are observed over the requested range only unless certified_stabilization_degree is non-null",
    }
    if observed_tail is not None and ideal.scheme_dimension == 0 and ideal.scheme_degree is not None and observed_tail["value"] == ideal.scheme_degree:
        certificate["degree_consistency_observed"] = True
    return HilbertFunctionTable(
        ideal_hash=ideal.ideal_hash,
        values=values,
        ambient_dimension=ideal.ambient_dimension,
        scheme_dimension=ideal.scheme_dimension,
        scheme_degree=ideal.scheme_degree,
        observed_constant_tail=observed_tail,
        certified_stabilization_degree=certified,
        backend=gb.backend,
        term_order=order,
        evidence_status=EvidenceStatus.VERIFIED,
        certificate=certificate,
    )


def hilbert_polynomial(ideal: ProjectiveSchemeIdeal) -> str | None:
    if ideal.scheme_dimension == 0 and ideal.scheme_degree is not None:
        return str(ideal.scheme_degree)
    return None


def compare_hilbert_functions(left: HilbertFunctionTable, right: HilbertFunctionTable) -> HilbertComparisonResult:
    degrees = tuple(sorted({value.degree for value in left.values} & {value.degree for value in right.values}))
    left_values = {degree: left.value_at(degree) for degree in degrees}
    right_values = {degree: right.value_at(degree) for degree in degrees}
    for degree in degrees:
        if left_values[degree] != right_values[degree]:
            return HilbertComparisonResult(
                ComparisonState.DIFFERENT,
                degree,
                degrees,
                left_values,
                right_values,
                f"Hilbert functions first differ at degree {degree}",
            )
    if not degrees:
        return HilbertComparisonResult(ComparisonState.UNKNOWN, None, degrees, left_values, right_values, "no overlapping degrees were available")
    return HilbertComparisonResult(ComparisonState.EQUAL, None, degrees, left_values, right_values, "Hilbert functions agree on the compared degree range")


def compare_ideals(left: ProjectiveSchemeIdeal, right: ProjectiveSchemeIdeal, *, order: str = "grevlex") -> dict[str, Any]:
    if left.variables != right.variables or left.base_field != right.base_field:
        return {"state": IdealComparisonState.UNKNOWN.value, "reason": "ideals use different variables or base fields"}
    left_gb = groebner_basis_data(left, order=order)
    right_gb = groebner_basis_data(right, order=order)
    left_basis = tuple(canonical_expr(item) for item in left_gb.basis_generators)
    right_basis = tuple(canonical_expr(item) for item in right_gb.basis_generators)
    state = IdealComparisonState.EQUAL if left_basis == right_basis else IdealComparisonState.DIFFERENT
    return {
        "state": state.value,
        "reason": "reduced Groebner bases match" if state is IdealComparisonState.EQUAL else "reduced Groebner bases differ",
        "term_order": order,
        "left_groebner_hash": left_gb.content_hash,
        "right_groebner_hash": right_gb.content_hash,
    }


def persist_hilbert_table(
    store: ResultStore,
    *,
    run_id: str,
    ideal: ProjectiveSchemeIdeal,
    table: HilbertFunctionTable,
) -> tuple[CertificateRecord, ArtifactRecord, tuple[Any, ...]]:
    run = store.get_run(run_id)
    payload = {
        "ideal": ideal.to_dict(),
        "hilbert_table": table.to_dict(),
        "firewall": {
            "hilbert_function_is_not_node_relation_lattice": True,
            "equal_hilbert_functions_do_not_imply_equal_schemes": True,
            "eventual_hilbert_value_does_not_imply_reducedness": True,
            "no_classical_defect_asserted": True,
        },
    }
    certificate = store.record_certificate(
        certificate_type="node_scheme_hilbert_function",
        subject_type="geometry",
        subject_id=run.geometry_id,
        method="hodgecy.geometry.projective_schemes",
        evidence=payload,
        generated_by_run_id=run_id,
        notes="Blob 6 Hilbert table; no critical-degree defect is asserted.",
    )
    with TemporaryDirectory() as tmp:
        artifact_path = Path(tmp) / "hilbert_table.json"
        artifact_path.write_text(canonical_json(table.to_dict()) + "\n", encoding="utf-8")
        artifact = store.attach_artifact(
            run_id=run_id,
            role="hilbert_function_table",
            artifact_type="json",
            source_path=artifact_path,
            storage_format="json",
            coefficient_ring=ideal.base_field,
            metadata={"ideal_hash": ideal.ideal_hash, "term_order": table.term_order},
        )
    invariants = []
    invariants.append(
        store.record_invariant(
            run_id=run_id,
            name="scheme_ideal_hash",
            value=ideal.ideal_hash,
            result_kind=ResultKind.NODE_GEOMETRY,
            evidence_status=ideal.evidence_status,
            method="hodgecy.geometry.projective_schemes",
            certificate_id=certificate.certificate_id,
            notes="hash of homogeneous scheme ideal generators and provenance",
        )
    )
    invariants.append(
        store.record_invariant(
            run_id=run_id,
            name="hilbert_function_table",
            value=table.to_dict(),
            result_kind=ResultKind.NODE_GEOMETRY,
            evidence_status=table.evidence_status,
            method="standard monomial count from exact Groebner initial ideal",
            certificate_id=certificate.certificate_id,
            notes=f"artifact_id={artifact.artifact_id}; Blob 6 does not compute defect",
        )
    )
    invariants.append(
        store.record_invariant(
            run_id=run_id,
            name="hilbert_polynomial",
            value=hilbert_polynomial(ideal),
            result_kind=ResultKind.NODE_GEOMETRY,
            evidence_status=EvidenceStatus.VERIFIED if hilbert_polynomial(ideal) is not None else EvidenceStatus.UNKNOWN,
            method="zero-dimensional Hilbert polynomial rule" if hilbert_polynomial(ideal) is not None else None,
            certificate_id=certificate.certificate_id,
            notes="For zero-dimensional schemes the Hilbert polynomial is the scheme degree; this does not imply reducedness.",
        )
    )
    return certificate, artifact, tuple(invariants)


def begin_hilbert_run(store: ResultStore, geometry_id: str, *, input_metadata: Any, parameters: Any | None = None, notes: str | None = None) -> CalculationRun:
    return store.begin_run(
        geometry_id=geometry_id,
        calculation_type="node_scheme_hilbert_blob6",
        input_metadata=input_metadata,
        parameters=parameters,
        backend="hodgecy.geometry.projective_schemes",
        coefficient_ring="QQ",
        notes=notes,
    )


def count_standard_monomials(variable_count: int, degree: int, leading_monomials: Sequence[Sequence[int]]) -> int:
    return sum(
        1
        for monomial in monomials_of_degree(variable_count, degree)
        if not any(_monomial_divides(leading, monomial) for leading in leading_monomials)
    )


def monomials_of_degree(variable_count: int, degree: int) -> tuple[tuple[int, ...], ...]:
    if variable_count == 1:
        return ((degree,),)
    monomials = []
    for first in range(degree + 1):
        for rest in monomials_of_degree(variable_count - 1, degree - first):
            monomials.append((first,) + rest)
    return tuple(monomials)


def canonical_expr(expression: Any) -> str:
    return str(sp.factor(sp.expand(sp.sympify(expression))))


def _hilbert_value_from_groebner(ideal: ProjectiveSchemeIdeal, degree: int, gb: GroebnerBasisData) -> HilbertFunctionValue:
    dim_s = comb(ideal.ambient_dimension + degree, ideal.ambient_dimension)
    quotient = count_standard_monomials(ideal.ambient_dimension + 1, degree, gb.leading_monomials)
    return HilbertFunctionValue(
        degree=degree,
        dim_S_d=dim_s,
        dim_I_d=dim_s - quotient,
        dim_quotient_d=quotient,
        evidence_status=EvidenceStatus.VERIFIED,
        method="standard monomial count from exact Groebner initial ideal over QQ",
    )


def _observed_constant_tail(values: Sequence[HilbertFunctionValue], scheme_degree: int | None) -> dict[str, Any] | None:
    if len(values) < 2:
        return None
    tail_value = values[-1].dim_quotient_d
    start = values[-1].degree
    for value in reversed(values[:-1]):
        if value.dim_quotient_d != tail_value:
            break
        start = value.degree
    if start == values[-1].degree:
        return None
    return {
        "start_degree": start,
        "stop_degree": values[-1].degree,
        "value": tail_value,
        "matches_scheme_degree": None if scheme_degree is None else tail_value == scheme_degree,
        "certified": False,
    }


def _intersect_homogeneous_ideals(left: Sequence[str], right: Sequence[str], variables: tuple[str, ...]) -> tuple[str, ...]:
    t = sp.Symbol("__hodgecy_t")
    symbols = tuple(sp.Symbol(name) for name in variables)
    locals_map = {name: symbol for name, symbol in zip(variables, symbols)}
    left_exprs = [sp.sympify(generator, locals=locals_map) for generator in left]
    right_exprs = [sp.sympify(generator, locals=locals_map) for generator in right]
    generators = [sp.expand(t * generator) for generator in left_exprs] + [sp.expand((1 - t) * generator) for generator in right_exprs]
    groebner = sp.groebner(generators, t, *symbols, order="lex", domain="QQ")
    eliminated = [poly.as_expr() for poly in groebner.polys if not poly.as_expr().has(t)]
    if not eliminated:
        raise ValueError("Ideal intersection produced no homogeneous generators.")
    return tuple(canonical_expr(generator) for generator in eliminated)


def _unique_points(points: Iterable[ProjectivePoint | Sequence[Any]]) -> tuple[ProjectivePoint, ...]:
    unique: dict[str, ProjectivePoint] = {}
    for point in points:
        projective = point if isinstance(point, ProjectivePoint) else ProjectivePoint.from_iterable(point)
        unique[projective.point_id] = projective
    return tuple(unique[key] for key in sorted(unique))


def _monomial_divides(left: Sequence[int], right: Sequence[int]) -> bool:
    return all(a <= b for a, b in zip(left, right))
