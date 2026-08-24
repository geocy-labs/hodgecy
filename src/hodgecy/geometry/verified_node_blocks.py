"""Exact predicted node-block certificates for the HodgeCY II 84/84a pair."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from itertools import combinations
import shutil
from typing import Any, Iterable

import sympy as sp

from hodgecy.arrangements import build_concurrency_profile
from hodgecy.arrangements.planes import PlaneArrangement
from hodgecy.smoothing.verification import (
    candidate_quartic,
    candidate_quartic_str,
    epsilon_value,
    line_genericity_check,
    smoothing_polynomial,
    verify_q_avoids_multiple_points,
)

VARIABLES = ("x", "y", "z", "t")
REQUIRED_CERTIFICATE_TYPES = (
    "predicted_node_block",
    "block_squarefree",
    "block_disjointness",
    "global_block_scheme",
    "saturated_jacobian_ideal",
    "block_jacobian_containment",
    "equal_degree_scheme_identification",
    "theorem_backed_local_A1",
    "theorem_backed_double_cover_ODP",
    "frozen_node_ideal",
    "ordinary_node_promotion",
)


@dataclass(frozen=True, slots=True)
class CertificateStep:
    certificate_type: str
    status: str
    evidence: str
    blocker: str | None = None
    data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PredictedNodeBlock:
    block_id: str
    line_id: str
    planes: tuple[str, str]
    ideal_generators: tuple[str, str, str]
    parameter_polynomial: str
    degree: int
    reduced: bool
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class NodeBlockCertification:
    arrangement_id: str
    perturbation_polynomial: str
    epsilon: str
    backend: dict[str, Any]
    blocks: tuple[PredictedNodeBlock, ...]
    certificate_steps: tuple[CertificateStep, ...]
    validation_status: dict[str, str]
    promotion_status: str
    blocker: str | None
    block_scheme_hash: str
    smoothing_polynomial_hash: str
    node_ideal_hash: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "hodgecy_ii_verified_node_blocks.v1",
            "arrangement_id": self.arrangement_id,
            "perturbation_polynomial": self.perturbation_polynomial,
            "epsilon": self.epsilon,
            "backend": self.backend,
            "blocks": [block.to_dict() for block in self.blocks],
            "certificate_steps": [step.to_dict() for step in self.certificate_steps],
            "validation_status": self.validation_status,
            "promotion_status": self.promotion_status,
            "blocker": self.blocker,
            "block_scheme_hash": self.block_scheme_hash,
            "smoothing_polynomial_hash": self.smoothing_polynomial_hash,
            "node_ideal_hash": self.node_ideal_hash,
        }


def stable_hash(payload: Any) -> str:
    import json

    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def exact_backend_status() -> dict[str, Any]:
    return {
        "python_backend": "sympy",
        "sympy_version": sp.__version__,
        "base_field": "QQ",
        "external_cas_on_path": {
            "Singular": shutil.which("Singular"),
            "sage": shutil.which("sage"),
            "M2": shutil.which("M2"),
        },
        "saturated_jacobian_reproducible_in_current_environment": False,
    }


def plane_linear_forms(arrangement: PlaneArrangement) -> dict[str, sp.Expr]:
    symbols = sp.symbols(" ".join(VARIABLES))
    forms: dict[str, sp.Expr] = {}
    for plane in arrangement.planes:
        forms[plane.label] = sp.expand(sum(sp.Integer(coefficient) * symbol for coefficient, symbol in zip(plane.coefficients, symbols)))
    return forms


def predicted_node_blocks(arrangement: PlaneArrangement) -> tuple[PredictedNodeBlock, ...]:
    forms = plane_linear_forms(arrangement)
    profile = build_concurrency_profile(arrangement)
    blocks: list[PredictedNodeBlock] = []
    for line in profile.double_lines:
        check = line_genericity_check(arrangement, line.line_id, line.planes)
        blocks.append(
            PredictedNodeBlock(
                block_id=f"{arrangement.arrangement_id}:{line.line_id}:Q0",
                line_id=line.line_id,
                planes=line.planes,
                ideal_generators=(str(forms[line.planes[0]]), str(forms[line.planes[1]]), candidate_quartic_str()),
                parameter_polynomial=check.parameter_polynomial,
                degree=check.degree,
                reduced=check.has_four_simple_zeros,
                status="VERIFIED" if check.has_four_simple_zeros else "FAILED",
            )
        )
    return tuple(blocks)


def disjointness_certificate(arrangement: PlaneArrangement, blocks: Iterable[PredictedNodeBlock]) -> CertificateStep:
    forms = plane_linear_forms(arrangement)
    symbols = sp.symbols(" ".join(VARIABLES))
    q0 = candidate_quartic()
    checked_pairs = 0
    meetings_excluded_by_g1 = 0
    skew_pairs = 0
    for left, right in combinations(tuple(blocks), 2):
        checked_pairs += 1
        linear_forms = [forms[label] for label in (*left.planes, *right.planes)]
        matrix = sp.Matrix([[sp.Poly(linear, *symbols).coeff_monomial(symbol) for symbol in symbols] for linear in linear_forms])
        rank = matrix.rank()
        if rank == 4:
            skew_pairs += 1
            continue
        if rank != 3:
            return CertificateStep(
                "block_disjointness",
                "UNKNOWN",
                "Exact linear-rank test encountered nontransverse coincident lines.",
                blocker=f"Line pair {left.line_id}/{right.line_id} has rank {rank}.",
            )
        nullspace = matrix.nullspace()
        point = nullspace[0]
        value = sp.expand(q0.subs({symbol: point[index] for index, symbol in enumerate(symbols)}))
        if value == 0:
            return CertificateStep(
                "block_disjointness",
                "FAILED",
                "Two predicted blocks meet at a Q0-zero arrangement multiple point.",
                blocker=f"Line pair {left.line_id}/{right.line_id} meets at Q0=0.",
            )
        meetings_excluded_by_g1 += 1
    return CertificateStep(
        "block_disjointness",
        "VERIFIED",
        "Every pair of predicted blocks is either skew or meets only at an arrangement multiple point where Q0 is nonzero.",
        data={
            "checked_pairs": checked_pairs,
            "skew_pairs": skew_pairs,
            "meetings_excluded_by_G1": meetings_excluded_by_g1,
        },
    )


def block_jacobian_containment_certificate(arrangement: PlaneArrangement, blocks: Iterable[PredictedNodeBlock]) -> CertificateStep:
    block_tuple = tuple(blocks)
    symbols = sp.symbols(" ".join(VARIABLES))
    f = smoothing_polynomial(arrangement)
    generators = (f, *(sp.diff(f, symbol) for symbol in symbols))
    checked_reductions = 0
    for block in block_tuple:
        ideal_generators = [sp.sympify(generator, locals=dict(zip(VARIABLES, symbols))) for generator in block.ideal_generators]
        basis = sp.groebner(ideal_generators, *symbols, order="lex", domain="QQ")
        for generator in generators:
            remainder = basis.reduce(sp.expand(generator))[1]
            checked_reductions += 1
            if sp.expand(remainder) != 0:
                return CertificateStep(
                    "block_jacobian_containment",
                    "FAILED",
                    "A Jacobian generator has nonzero remainder modulo a predicted block ideal.",
                    blocker=f"Block {block.block_id} remainder {sp.expand(remainder)}",
                )
    return CertificateStep(
        "block_jacobian_containment",
        "VERIFIED",
        "F_A and all first partial derivatives reduce to zero modulo each exact block ideal (linear_i, linear_j, Q0).",
        data={"checked_blocks": len(block_tuple), "checked_reductions": checked_reductions},
    )


def promotion_from_equal_length_subscheme(
    *,
    predicted_degree: int,
    ambient_degree: int | None,
    predicted_reduced: bool,
    containment_verified: bool,
    ambient_reduced: bool | None = None,
) -> tuple[str, str]:
    if ambient_degree is None:
        return "UNKNOWN", "Ambient saturated Jacobian degree is unavailable."
    if not containment_verified:
        return "UNKNOWN", "Predicted block containment in the saturated Jacobian scheme is not verified."
    if predicted_degree != ambient_degree:
        return "UNKNOWN", "Predicted block degree and ambient singular-scheme degree differ."
    if ambient_reduced is False:
        return "UNKNOWN", "Ambient scheme is known nonreduced, so equal length does not certify ordinary nodes."
    if not predicted_reduced:
        return "UNKNOWN", "Predicted block scheme is not reduced."
    if ambient_reduced is not True:
        return "UNKNOWN", "Ambient saturated Jacobian reducedness is unavailable."
    return "ordinary_node_verified", "Equal-length reduced subscheme certificate identifies the singular scheme."


def build_node_block_certification(arrangement: PlaneArrangement) -> NodeBlockCertification:
    blocks = predicted_node_blocks(arrangement)
    g1_ok, g1_violations, g1_checks = verify_q_avoids_multiple_points(arrangement)
    g2_ok = all(block.status == "VERIFIED" for block in blocks)
    disjoint = disjointness_certificate(arrangement, blocks)
    containment = block_jacobian_containment_certificate(arrangement, blocks)
    expected_degree = sum(block.degree for block in blocks if block.status == "VERIFIED")
    backend = exact_backend_status()
    saturated_blocker = (
        "No Singular/Sage/Macaulay2 executable is available on PATH, and SymPy does not provide a reliable exact "
        "saturated Jacobian ideal/degree/reducedness certificate for this projective zero-scheme."
    )
    promotion_status, promotion_reason = promotion_from_equal_length_subscheme(
        predicted_degree=expected_degree,
        ambient_degree=None,
        predicted_reduced=g2_ok and disjoint.status == "VERIFIED",
        containment_verified=containment.status == "VERIFIED",
        ambient_reduced=None,
    )
    steps = (
        CertificateStep(
            "predicted_node_block",
            "VERIFIED" if len(blocks) == 28 else "FAILED",
            "The exact 28 double-line blocks are B_ij = V(l_i, l_j, Q0).",
            data={"block_count": len(blocks), "expected_block_count": 28},
        ),
        CertificateStep(
            "block_squarefree",
            "VERIFIED" if g2_ok else "FAILED",
            "For every double line, Q0 restricts to a squarefree degree-4 polynomial over QQ.",
            data={"verified_blocks": sum(block.status == "VERIFIED" for block in blocks), "total_blocks": len(blocks)},
        ),
        disjoint,
        CertificateStep(
            "global_block_scheme",
            "VERIFIED" if g1_ok and g2_ok and disjoint.status == "VERIFIED" and expected_degree == 112 else "FAILED",
            "The disjoint union of 28 reduced degree-4 blocks is reduced of degree 112.",
            data={"degree": expected_degree, "reduced": g2_ok and disjoint.status == "VERIFIED", "g1_violations": g1_violations},
        ),
        CertificateStep(
            "saturated_jacobian_ideal",
            "UNKNOWN",
            "The exact saturated Jacobian ideal was not recomputed or frozen in this environment.",
            blocker=saturated_blocker,
        ),
        containment,
        CertificateStep(
            "equal_degree_scheme_identification",
            "UNKNOWN",
            "Equal-degree identification is blocked until the saturated Jacobian degree/reducedness certificate is reproduced.",
            blocker=saturated_blocker,
            data={"predicted_block_degree": expected_degree},
        ),
        CertificateStep(
            "theorem_backed_local_A1",
            "UNKNOWN",
            "The local A1 theorem applies after exact singular-scheme equality is certified.",
            blocker="Requires equal-degree scheme identification.",
        ),
        CertificateStep(
            "theorem_backed_double_cover_ODP",
            "UNKNOWN",
            "The double-cover ODP promotion applies after local A1 is certified at the frozen node ideal.",
            blocker="Requires theorem_backed_local_A1.",
        ),
        CertificateStep(
            "frozen_node_ideal",
            "UNKNOWN",
            "Only the predicted block scheme is frozen; the final saturated node ideal is not.",
            blocker=saturated_blocker,
        ),
        CertificateStep(
            "ordinary_node_promotion",
            "UNKNOWN",
            promotion_reason,
            blocker=saturated_blocker,
        ),
    )
    validation_status = {
        "perturbation_polynomial": "FROZEN_EXACT",
        "source_assembly": "VERIFIED",
        "degree112": "HISTORICAL_CERTIFIED",
        "G1": "VERIFIED" if g1_ok else "FAILED",
        "G2": "VERIFIED" if g2_ok else "FAILED",
        "block_scheme": "VERIFIED" if expected_degree == 112 and g2_ok and disjoint.status == "VERIFIED" else "FAILED",
        "saturated_jacobian_ideal": "UNKNOWN",
        "block_jacobian_containment": containment.status,
        "ordinary_node_verified": "UNKNOWN",
        "defect": "UNKNOWN",
    }
    block_scheme_payload = {
        "arrangement_id": arrangement.arrangement_id,
        "blocks": [block.to_dict() for block in blocks],
        "g1_checks": [asdict(check) for check in g1_checks],
    }
    return NodeBlockCertification(
        arrangement_id=arrangement.arrangement_id,
        perturbation_polynomial=candidate_quartic_str(),
        epsilon=str(epsilon_value()),
        backend=backend,
        blocks=blocks,
        certificate_steps=steps,
        validation_status=validation_status,
        promotion_status=promotion_status,
        blocker=saturated_blocker,
        block_scheme_hash=stable_hash(block_scheme_payload),
        smoothing_polynomial_hash=stable_hash(str(smoothing_polynomial(arrangement))),
        node_ideal_hash=None,
    )
