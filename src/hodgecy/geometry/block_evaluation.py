"""Exact block-scheme Hilbert and evaluation calculations.

Blob 13 works with the frozen Blob 12 block decomposition rather than a newly
constructed global intersection ideal.  For each degree ``d`` it computes the
rank of the exact map

    S_d -> direct_sum_i (S / I_{B_i})_d

over QQ.  Because Blob 12 certifies the blocks are reduced and pairwise
disjoint, this rank is the Hilbert value of the verified block scheme.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from math import comb
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable, Sequence

import sympy as sp

from hodgecy import __version__ as HODGECY_VERSION
from hodgecy.core.results import EvidenceStatus
from hodgecy.core.serialization import stable_sha256
from hodgecy.geometry.defects import DefectConvention, resolve_critical_degree
from hodgecy.geometry.projective_schemes import monomials_of_degree

VARIABLES = ("x", "y", "z", "t")
EXPECTED_BLOB12_BLOCK_HASHES = {
    "84": "428406a6d72603cea07594fbbeac4aacdd35ed7437a203a77751d7e16a6b5eb7",
    "84a": "3aa8cec40c439677fe6774549169d4e5507afc02b10df102b475def647d93e98",
}


@dataclass(frozen=True, slots=True)
class BlockIdealInput:
    block_id: str
    ideal_generators: tuple[str, ...]
    parameter_polynomial: str | None
    degree: int
    reduced: bool
    status: str

    @classmethod
    def from_blob12_block(cls, payload: dict[str, Any]) -> "BlockIdealInput":
        return cls(
            block_id=str(payload["block_id"]),
            ideal_generators=tuple(str(item) for item in payload["ideal_generators"]),
            parameter_polynomial=None if payload.get("parameter_polynomial") is None else str(payload["parameter_polynomial"]),
            degree=int(payload["degree"]),
            reduced=bool(payload["reduced"]),
            status=str(payload["status"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LoadedBlockScheme:
    arrangement_id: str
    block_scheme_hash: str
    certificate_path: str
    certificate_file_sha256: str
    variables: tuple[str, ...]
    base_field: str
    blocks: tuple[BlockIdealInput, ...]
    scheme_dimension: int
    scheme_degree: int
    reduced: bool
    block_jacobian_containment: str
    ordinary_node_verified: str
    final_saturated_node_ideal: str
    classical_defect: str
    validation_status: dict[str, str]
    blob12_certificate: dict[str, Any] = field(repr=False)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["blob12_certificate"] = self.blob12_certificate
        return payload


@dataclass(frozen=True, slots=True)
class BlockGroebnerData:
    block_id: str
    leading_monomials: tuple[tuple[int, ...], ...]
    basis_generators: tuple[str, ...]
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LineQuotientData:
    block_id: str
    coordinate_polynomials: tuple[str, str, str, str]
    parameter_polynomial: str
    basis_powers: tuple[int, ...]
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BlockHilbertValue:
    degree: int
    dim_S_d: int
    dim_I_B_d: int
    H_B_d: int
    target_quotient_dimension: int
    evaluation_matrix_shape: tuple[int, int]
    evaluation_rank: int
    matrix_hash: str
    evidence_status: EvidenceStatus
    method: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence_status"] = self.evidence_status.value
        payload["evaluation_matrix_shape"] = list(self.evaluation_matrix_shape)
        return payload


@dataclass(frozen=True, slots=True)
class BlockHilbertTable:
    arrangement_id: str
    block_scheme_hash: str
    values: tuple[BlockHilbertValue, ...]
    backend: str
    base_field: str
    evidence_status: EvidenceStatus
    observed_constant_tail: dict[str, Any] | None
    certified_stabilization_degree: int | None
    groebner_cache_hash: str
    certificate: dict[str, Any]

    def value_at(self, degree: int) -> int | None:
        for value in self.values:
            if value.degree == degree:
                return value.H_B_d
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "arrangement_id": self.arrangement_id,
            "block_scheme_hash": self.block_scheme_hash,
            "values": [value.to_dict() for value in self.values],
            "backend": self.backend,
            "base_field": self.base_field,
            "evidence_status": self.evidence_status.value,
            "observed_constant_tail": self.observed_constant_tail,
            "certified_stabilization_degree": self.certified_stabilization_degree,
            "groebner_cache_hash": self.groebner_cache_hash,
            "certificate": self.certificate,
        }


@dataclass(frozen=True, slots=True)
class BlockEvaluationResult:
    arrangement_id: str
    block_scheme_hash: str
    scheme_degree: int
    critical_degree: dict[str, Any]
    hilbert_table: BlockHilbertTable
    H_B_8: int
    evaluation_source_dimension: int
    evaluation_target_length: int
    evaluation_rank: int
    evaluation_kernel_dimension: int
    evaluation_cokernel_dimension: int
    block_evaluation_deficiency: int
    evaluation_relation_dimension: int
    explicit_evaluation_matrix_constructed: bool
    explicit_dual_relation_map_constructed: bool
    explicit_point_evaluation: str
    integral_evaluation_relation_complex: str
    conditional_classical_defect_value: int
    actual_classical_defect: None
    actual_classical_defect_status: EvidenceStatus
    evidence_status: EvidenceStatus
    certificates: tuple[dict[str, Any], ...]
    timings: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "arrangement_id": self.arrangement_id,
            "block_scheme_hash": self.block_scheme_hash,
            "scheme_degree": self.scheme_degree,
            "critical_degree": self.critical_degree,
            "hilbert_table": self.hilbert_table.to_dict(),
            "H_B_8": self.H_B_8,
            "evaluation_source_dimension": self.evaluation_source_dimension,
            "evaluation_target_length": self.evaluation_target_length,
            "evaluation_rank": self.evaluation_rank,
            "evaluation_kernel_dimension": self.evaluation_kernel_dimension,
            "evaluation_cokernel_dimension": self.evaluation_cokernel_dimension,
            "block_evaluation_deficiency": self.block_evaluation_deficiency,
            "evaluation_relation_dimension": self.evaluation_relation_dimension,
            "explicit_evaluation_matrix_constructed": self.explicit_evaluation_matrix_constructed,
            "explicit_dual_relation_map_constructed": self.explicit_dual_relation_map_constructed,
            "explicit_point_evaluation": self.explicit_point_evaluation,
            "integral_evaluation_relation_complex": self.integral_evaluation_relation_complex,
            "conditional_classical_defect_value": self.conditional_classical_defect_value,
            "actual_classical_defect": self.actual_classical_defect,
            "actual_classical_defect_status": self.actual_classical_defect_status.value,
            "evidence_status": self.evidence_status.value,
            "certificates": list(self.certificates),
            "timings": self.timings,
        }


@dataclass(frozen=True, slots=True)
class BlockEvaluationComparison:
    left_arrangement: str
    right_arrangement: str
    compared_degrees: tuple[int, ...]
    first_hilbert_difference: int | None
    hilbert_profile_state: str
    critical_values_agree: bool
    evaluation_ranks_agree: bool
    evaluation_deficiencies_agree: bool
    relation_dimensions_agree: bool
    descriptive_case: str
    firewall: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["compared_degrees"] = list(self.compared_degrees)
        return payload


def load_blob12_block_scheme(path: str | Path, *, expected_hash: str | None = None) -> LoadedBlockScheme:
    certificate_path = Path(path)
    payload = _read_json(certificate_path)
    arrangement_id = str(payload["arrangement_id"])
    expected = expected_hash or EXPECTED_BLOB12_BLOCK_HASHES.get(arrangement_id)
    block_hash = str(payload["block_scheme_hash"])
    if expected is not None and block_hash != expected:
        raise ValueError(f"Blob 12 block hash mismatch for {arrangement_id}: expected {expected}, got {block_hash}")
    if str(payload["backend"]["base_field"]) != "QQ":
        raise ValueError(f"Unsupported block base field for {arrangement_id}: {payload['backend']['base_field']!r}")
    blocks = tuple(BlockIdealInput.from_blob12_block(item) for item in payload["blocks"])
    if len(blocks) != 28:
        raise ValueError(f"Expected 28 Blob 12 blocks for {arrangement_id}, got {len(blocks)}")
    if any(block.status != "VERIFIED" or not block.reduced for block in blocks):
        raise ValueError(f"Blob 12 block reducedness certificate is incomplete for {arrangement_id}")
    scheme_degree = sum(block.degree for block in blocks)
    if scheme_degree != 112:
        raise ValueError(f"Expected degree 112 for {arrangement_id}, got {scheme_degree}")
    statuses = {str(step["certificate_type"]): str(step["status"]) for step in payload["certificate_steps"]}
    if statuses.get("global_block_scheme") != "VERIFIED":
        raise ValueError(f"Blob 12 global block scheme is not verified for {arrangement_id}")
    if statuses.get("block_jacobian_containment") != "VERIFIED":
        raise ValueError(f"Blob 12 block-to-Jacobian containment is not verified for {arrangement_id}")
    for block in blocks:
        _validate_homogeneous_generators(block.ideal_generators)
    return LoadedBlockScheme(
        arrangement_id=arrangement_id,
        block_scheme_hash=block_hash,
        certificate_path=certificate_path.as_posix(),
        certificate_file_sha256=file_sha256(certificate_path),
        variables=VARIABLES,
        base_field="QQ",
        blocks=blocks,
        scheme_dimension=0,
        scheme_degree=scheme_degree,
        reduced=True,
        block_jacobian_containment=statuses.get("block_jacobian_containment", "UNKNOWN"),
        ordinary_node_verified=str(payload["validation_status"].get("ordinary_node_verified", "UNKNOWN")),
        final_saturated_node_ideal=statuses.get("frozen_node_ideal", "UNKNOWN"),
        classical_defect="UNKNOWN",
        validation_status={str(key): str(value) for key, value in payload["validation_status"].items()},
        blob12_certificate=payload,
    )


def compute_block_hilbert_table(
    scheme: LoadedBlockScheme,
    *,
    degrees: Iterable[int],
    order: str = "grevlex",
) -> tuple[BlockHilbertTable, dict[str, float]]:
    timings: dict[str, float] = {}
    start = perf_counter()
    symbols = _symbols()
    line_quotients = tuple(_line_quotient_data(block, symbols=symbols) for block in scheme.blocks)
    timings["line_quotient_preparation_seconds"] = perf_counter() - start
    values: list[BlockHilbertValue] = []
    for degree in tuple(degrees):
        degree_start = perf_counter()
        values.append(_hilbert_value_from_line_quotients(scheme, line_quotients, degree, symbols=symbols))
        timings[f"hilbert_degree_{degree}_seconds"] = perf_counter() - degree_start
    values_tuple = tuple(values)
    cache_hash = stable_sha256([item.to_dict() for item in line_quotients])
    certificate = {
        "certificate_type": "block_hilbert_function",
        "block_ideal_hash": scheme.block_scheme_hash,
        "blob12_reducedness_certificate": True,
        "scheme_degree": scheme.scheme_degree,
        "backend": "sympy exact line quotient remainders+sympy.Matrix.rank",
        "sympy_version": sp.__version__,
        "base_field": "QQ",
        "algorithm": "rank of S_d -> direct sum QQ[u]/(Q0|_L) degree-d block quotient components",
        "hodgecy_version": HODGECY_VERSION,
        "firewall": evaluation_firewall(),
    }
    return (
        BlockHilbertTable(
            arrangement_id=scheme.arrangement_id,
            block_scheme_hash=scheme.block_scheme_hash,
            values=values_tuple,
            backend="sympy exact line quotient remainders+sympy.Matrix.rank",
            base_field="QQ",
            evidence_status=EvidenceStatus.VERIFIED,
            observed_constant_tail=_observed_constant_tail(values_tuple, scheme.scheme_degree),
            certified_stabilization_degree=None,
            groebner_cache_hash=cache_hash,
            certificate=certificate,
        ),
        timings,
    )


def compute_block_evaluation_result(
    scheme: LoadedBlockScheme,
    *,
    degrees: Iterable[int] = range(0, 9),
    order: str = "grevlex",
    git_commit: str | None = None,
) -> BlockEvaluationResult:
    run_start = perf_counter()
    table_start = perf_counter()
    table, timings = compute_block_hilbert_table(scheme, degrees=degrees, order=order)
    timings["hilbert_table_seconds"] = perf_counter() - table_start
    critical_start = perf_counter()
    critical = resolve_critical_degree(
        DefectConvention.NODAL_DOUBLE_SOLID_CLEMENS_CYNK,
        ambient_base="P^3",
        ambient_dimension=3,
        cover_degree=2,
        branch_degree=8,
        characteristic=0,
    )
    timings["critical_degree_seconds"] = perf_counter() - critical_start
    degree = critical.critical_degree
    h_value = table.value_at(degree)
    if h_value is None:
        raise ValueError(f"Hilbert table for {scheme.arrangement_id} does not include critical degree {degree}")
    source_dimension = critical.source_dimension
    target_length = scheme.scheme_degree
    rank = h_value
    kernel_dimension = source_dimension - rank
    cokernel_dimension = target_length - rank
    deficiency = cokernel_dimension
    prerequisites = {
        "finite_singular_scheme": True,
        "complete_support": False,
        "reducedness": True,
        "ordinary_node_classification": scheme.ordinary_node_verified == "VERIFIED",
        "exact_node_ideal": scheme.final_saturated_node_ideal == "VERIFIED",
        "applicable_double_solid_model": True,
        "certified_critical_degree_rule": True,
        "exact_evaluation_or_hilbert_computation": True,
    }
    certificates = (
        {
            "certificate_type": "critical_degree_block_evaluation",
            "critical_degree_certificate": critical.certificate,
            "block_ideal_hash": scheme.block_scheme_hash,
            "scheme_degree": scheme.scheme_degree,
            "H_B_8": h_value,
            "hodgecy_version": HODGECY_VERSION,
            "git_commit": git_commit,
        },
        {
            "certificate_type": "block_evaluation_rank",
            "block_ideal_hash": scheme.block_scheme_hash,
            "degree": degree,
            "rank_identity": "rank(E_8) = H_B(8)",
            "evaluation_rank": rank,
            "source_dimension": source_dimension,
            "target_length": target_length,
            "backend": table.backend,
            "hodgecy_version": HODGECY_VERSION,
            "git_commit": git_commit,
        },
        {
            "certificate_type": "block_evaluation_deficiency",
            "block_ideal_hash": scheme.block_scheme_hash,
            "degree": degree,
            "epsilon_B": deficiency,
            "terminology": "degree-8 block-scheme evaluation deficiency",
            "classical_defect_status": EvidenceStatus.UNKNOWN.value,
            "firewall": evaluation_firewall(),
            "hodgecy_version": HODGECY_VERSION,
            "git_commit": git_commit,
        },
        {
            "certificate_type": "evaluation_relation_dimension",
            "block_ideal_hash": scheme.block_scheme_hash,
            "relation_dimension": deficiency,
            "identity": "dim ker(E_8^T) = target_length - rank(E_8)",
            "explicit_dual_matrix_constructed": False,
            "integral_evaluation_relation_complex": "UNKNOWN",
            "firewall": evaluation_firewall(),
            "hodgecy_version": HODGECY_VERSION,
            "git_commit": git_commit,
        },
        {
            "certificate_type": "conditional_defect",
            "block_ideal_hash": scheme.block_scheme_hash,
            "conditional_classical_defect_value": deficiency,
            "condition": "only if the verified block scheme is identified with the full ordinary-node scheme under the HodgeCY defect hypotheses",
            "actual_classical_defect": None,
            "actual_classical_defect_status": EvidenceStatus.UNKNOWN.value,
            "prerequisites": prerequisites,
            "firewall": evaluation_firewall(),
            "hodgecy_version": HODGECY_VERSION,
            "git_commit": git_commit,
        },
    )
    timings["degree_8_evaluation_seconds"] = 0.0
    timings["relation_analysis_seconds"] = 0.0
    timings["total_seconds"] = perf_counter() - run_start
    return BlockEvaluationResult(
        arrangement_id=scheme.arrangement_id,
        block_scheme_hash=scheme.block_scheme_hash,
        scheme_degree=scheme.scheme_degree,
        critical_degree=critical.to_dict(),
        hilbert_table=table,
        H_B_8=h_value,
        evaluation_source_dimension=source_dimension,
        evaluation_target_length=target_length,
        evaluation_rank=rank,
        evaluation_kernel_dimension=kernel_dimension,
        evaluation_cokernel_dimension=cokernel_dimension,
        block_evaluation_deficiency=deficiency,
        evaluation_relation_dimension=deficiency,
        explicit_evaluation_matrix_constructed=False,
        explicit_dual_relation_map_constructed=False,
        explicit_point_evaluation="NOT_REQUIRED",
        integral_evaluation_relation_complex="UNKNOWN",
        conditional_classical_defect_value=deficiency,
        actual_classical_defect=None,
        actual_classical_defect_status=EvidenceStatus.UNKNOWN,
        evidence_status=EvidenceStatus.VERIFIED,
        certificates=certificates,
        timings=timings,
    )


def compare_block_evaluation_results(left: BlockEvaluationResult, right: BlockEvaluationResult) -> BlockEvaluationComparison:
    degrees = tuple(sorted({value.degree for value in left.hilbert_table.values} & {value.degree for value in right.hilbert_table.values}))
    first_difference = None
    for degree in degrees:
        if left.hilbert_table.value_at(degree) != right.hilbert_table.value_at(degree):
            first_difference = degree
            break
    deficiencies_agree = left.block_evaluation_deficiency == right.block_evaluation_deficiency
    if not deficiencies_agree:
        descriptive_case = "Case A - Critical evaluation separation"
    elif first_difference is not None:
        descriptive_case = "Case B - Critical collapse, lower/higher Hilbert separation"
    else:
        descriptive_case = "Case C - Hilbert collapse over computed range"
    return BlockEvaluationComparison(
        left_arrangement=left.arrangement_id,
        right_arrangement=right.arrangement_id,
        compared_degrees=degrees,
        first_hilbert_difference=first_difference,
        hilbert_profile_state="DIFFERENT" if first_difference is not None else "EQUAL through computed range",
        critical_values_agree=left.H_B_8 == right.H_B_8,
        evaluation_ranks_agree=left.evaluation_rank == right.evaluation_rank,
        evaluation_deficiencies_agree=deficiencies_agree,
        relation_dimensions_agree=left.evaluation_relation_dimension == right.evaluation_relation_dimension,
        descriptive_case=descriptive_case,
        firewall=evaluation_firewall(),
    )


def evaluation_firewall() -> dict[str, bool]:
    return {
        "block_evaluation_deficiency_is_not_automatically_classical_defect": True,
        "equal_evaluation_deficiencies_do_not_imply_equal_block_schemes": True,
        "equal_hilbert_functions_do_not_imply_isomorphic_schemes": True,
        "different_hilbert_functions_do_not_explain_source_smith_difference": True,
        "evaluation_relation_dimension_is_not_source_kernel_rank": True,
        "no_source_to_evaluation_morphism_inferred": True,
        "no_integral_evaluation_lattice_fabricated": True,
        "no_vanishing_cycle_relation_constructed": True,
        "no_exceptional_curve_relation_constructed": True,
        "no_picard_lefschetz_calculation": True,
        "no_hodge_atom_spectrum_constructed": True,
    }


def file_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def _symbols() -> tuple[sp.Symbol, ...]:
    return sp.symbols(" ".join(VARIABLES))


def _validate_homogeneous_generators(generators: Sequence[str]) -> None:
    symbols = _symbols()
    locals_map = dict(zip(VARIABLES, symbols))
    for generator in generators:
        expression = sp.expand(sp.sympify(generator, locals=locals_map))
        poly = sp.Poly(expression, *symbols, domain="QQ")
        degrees = {sum(monomial) for monomial, coeff in zip(poly.monoms(), poly.coeffs()) if coeff != 0}
        if len(degrees) > 1:
            raise ValueError(f"Block ideal generator is not homogeneous: {generator}")


def _block_groebner_data(block: BlockIdealInput, basis: Any, *, order: str) -> BlockGroebnerData:
    basis_generators = tuple(str(sp.factor(poly.as_expr())) for poly in basis.polys)
    leading = tuple(tuple(int(exp) for exp in poly.LM(order=basis.order)) for poly in basis.polys)
    payload = {
        "block_id": block.block_id,
        "basis_generators": basis_generators,
        "leading_monomials": leading,
        "order": order,
        "backend": "sympy.groebner",
    }
    return BlockGroebnerData(block.block_id, leading, basis_generators, stable_sha256(payload))


def _hilbert_value_from_line_quotients(
    scheme: LoadedBlockScheme,
    line_quotients: Sequence[LineQuotientData],
    degree: int,
    *,
    symbols: Sequence[sp.Symbol],
) -> BlockHilbertValue:
    if degree < 0:
        raise ValueError("Hilbert degree must be nonnegative.")
    domain_basis = monomials_of_degree(len(symbols), degree)
    u = sp.Symbol("u")
    target_powers_by_block = [tuple(power for power in quotient.basis_powers if power <= degree) for quotient in line_quotients]
    quotient_runtime = []
    for quotient in line_quotients:
        coords = tuple(sp.Poly(sp.sympify(item, locals={"u": u}), u, domain="QQ") for item in quotient.coordinate_polynomials)
        powers = tuple(tuple(coord ** exponent for exponent in range(degree + 1)) for coord in coords)
        q_poly = sp.Poly(sp.sympify(quotient.parameter_polynomial, locals={"u": u}), u, domain="QQ")
        quotient_runtime.append((powers, q_poly))
    columns: list[list[sp.Expr]] = []
    for monomial in domain_basis:
        column: list[sp.Expr] = []
        for (powers, q_poly), target_powers in zip(quotient_runtime, target_powers_by_block):
            poly = sp.Poly(1, u, domain="QQ")
            for coord_index, exponent in enumerate(monomial):
                poly *= powers[coord_index][int(exponent)]
            poly = poly.rem(q_poly)
            column.extend(poly.coeff_monomial(u ** power) for power in target_powers)
        columns.append(column)
    matrix = sp.Matrix.hstack(*(sp.Matrix(column) for column in columns)) if columns else sp.zeros(0, 0)
    rank = _exact_matrix_rank(matrix)
    dim_s = comb(degree + len(symbols) - 1, len(symbols) - 1)
    target_dim = sum(len(item) for item in target_powers_by_block)
    matrix_hash = stable_sha256(
        {
            "arrangement_id": scheme.arrangement_id,
            "degree": degree,
            "domain_basis": [list(item) for item in domain_basis],
            "target_powers_by_block": [list(item) for item in target_powers_by_block],
            "matrix": [[str(matrix[row, col]) for col in range(matrix.cols)] for row in range(matrix.rows)],
        }
    )
    return BlockHilbertValue(
        degree=degree,
        dim_S_d=dim_s,
        dim_I_B_d=dim_s - rank,
        H_B_d=rank,
        target_quotient_dimension=target_dim,
        evaluation_matrix_shape=(target_dim, dim_s),
        evaluation_rank=rank,
        matrix_hash=matrix_hash,
        evidence_status=EvidenceStatus.VERIFIED,
        method="rank of exact direct-sum line quotient matrix over QQ",
    )


def _line_quotient_data(block: BlockIdealInput, *, symbols: Sequence[sp.Symbol]) -> LineQuotientData:
    if block.parameter_polynomial is None:
        raise ValueError(f"Block {block.block_id} does not include a frozen parameter polynomial.")
    linears = []
    locals_map = dict(zip(VARIABLES, symbols))
    for generator in block.ideal_generators:
        expression = sp.expand(sp.sympify(generator, locals=locals_map))
        if sp.Poly(expression, *symbols, domain="QQ").total_degree() == 1:
            linears.append(expression)
    if len(linears) < 2:
        raise ValueError(f"Block {block.block_id} does not include two linear line equations.")
    matrix = sp.Matrix([[sp.Poly(linear, *symbols, domain="QQ").coeff_monomial(symbol) for symbol in symbols] for linear in linears[:2]])
    basis = matrix.nullspace()
    if len(basis) != 2:
        raise ValueError(f"Block {block.block_id} line equations do not define a projective line.")
    u = sp.Symbol("u")
    coords = tuple(sp.expand(basis[0][index] + u * basis[1][index]) for index in range(4))
    q_poly = sp.Poly(sp.sympify(block.parameter_polynomial, locals={"u": u}), u, domain="QQ")
    if q_poly.degree() != block.degree:
        raise ValueError(f"Block {block.block_id} parameter polynomial degree mismatch.")
    content = {
        "block_id": block.block_id,
        "coordinate_polynomials": [str(item) for item in coords],
        "parameter_polynomial": str(q_poly.as_expr()),
        "basis_powers": list(range(block.degree)),
    }
    return LineQuotientData(
        block_id=block.block_id,
        coordinate_polynomials=tuple(str(item) for item in coords),
        parameter_polynomial=str(q_poly.as_expr()),
        basis_powers=tuple(range(block.degree)),
        content_hash=stable_sha256(content),
    )


def _groebner_from_block(block: BlockIdealInput, *, symbols: Sequence[sp.Symbol], order: str) -> sp.GroebnerBasis:
    locals_map = dict(zip(VARIABLES, symbols))
    expressions = [sp.expand(sp.sympify(generator, locals=locals_map)) for generator in block.ideal_generators]
    return sp.groebner(expressions, *symbols, order=order, domain="QQ")


def _exact_matrix_rank(matrix: sp.Matrix) -> int:
    try:
        return int(matrix.to_DM().rank())
    except Exception:
        return int(matrix.rank())


def _monomial_expr(symbols: Sequence[sp.Symbol], monomial: Sequence[int]) -> sp.Expr:
    expr = sp.Integer(1)
    for symbol, exponent in zip(symbols, monomial):
        expr *= symbol ** int(exponent)
    return expr


def _observed_constant_tail(values: Sequence[BlockHilbertValue], scheme_degree: int) -> dict[str, Any] | None:
    if len(values) < 2:
        return None
    tail = values[-1].H_B_d
    start = values[-1].degree
    for value in reversed(values[:-1]):
        if value.H_B_d != tail:
            break
        start = value.degree
    if start == values[-1].degree:
        return None
    return {
        "start_degree": start,
        "stop_degree": values[-1].degree,
        "value": tail,
        "matches_scheme_degree": tail == scheme_degree,
        "certified": False,
    }


def _monomial_divides(left: Sequence[int], right: Sequence[int]) -> bool:
    return all(a <= b for a, b in zip(left, right))
