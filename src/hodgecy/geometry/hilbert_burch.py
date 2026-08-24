"""Hilbert-Burch verifier for the HodgeCY II eight-plane block profile."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations
from math import comb
from pathlib import Path
from typing import Any, Sequence

import sympy as sp

from hodgecy import __version__ as HODGECY_VERSION
from hodgecy.arrangements import arrangement_84, arrangement_84a
from hodgecy.arrangements.planes import Plane, PlaneArrangement
from hodgecy.core.serialization import stable_sha256
from hodgecy.geometry.block_evaluation import compute_block_evaluation_result, load_blob12_block_scheme
from hodgecy.geometry.verified_node_blocks import plane_linear_forms
from hodgecy.smoothing.verification import candidate_quartic, line_genericity_check

VARIABLES = ("x", "y", "z", "t")
PRIMARY_ARRANGEMENTS = ("84", "84a")
CONTROL_ARRANGEMENTS = ("239", "240", "241")
THEOREM_EVIDENCE_DIR = Path("research_outputs/hodgecy_ii/final/theorem_evidence")


@dataclass(frozen=True, slots=True)
class ArrangementSkeletonVerification:
    arrangement_id: str
    plane_equations: tuple[str, ...]
    plane_hash: str
    pair_count: int
    pairwise_independent: bool
    triple_rank_condition: bool
    triple_rank_distribution: dict[str, int]
    no_three_planes_contain_a_line: bool
    height_status: str
    hilbert_burch_matrix_shape: tuple[int, int]
    maximal_minors_match_generators: bool
    syzygies_verified: bool
    ideal_equality_status: str
    ideal_saturation_status: str
    line_skeleton_resolution: str
    line_skeleton_hilbert_series: str
    line_skeleton_hilbert_function_0_12: tuple[int, ...]
    line_skeleton_degree: int
    reducedness_status: str
    embedded_components_status: str
    theorem_hypotheses_status: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["hilbert_burch_matrix_shape"] = list(self.hilbert_burch_matrix_shape)
        payload["line_skeleton_hilbert_function_0_12"] = list(self.line_skeleton_hilbert_function_0_12)
        return payload


@dataclass(frozen=True, slots=True)
class BlockTheoremVerification:
    arrangement_id: str
    quartic: str | None
    quartic_regular_status: str
    quartic_regular_reason: str
    line_restrictions_checked: int
    squarefree_degree_four_restrictions: bool
    block_resolution: str | None
    block_hilbert_series: str | None
    theoretical_hilbert_function_0_12: tuple[int, ...] | None
    observed_block_hilbert_function_0_8: tuple[int, ...] | None
    formula_matches_existing_block_computation: bool | None
    stabilization_degree: int | None
    h1_i_b_8_dimension: int | None
    evaluation_deficiency_explanation_status: str
    classical_defect_status: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.theoretical_hilbert_function_0_12 is not None:
            payload["theoretical_hilbert_function_0_12"] = list(self.theoretical_hilbert_function_0_12)
        if self.observed_block_hilbert_function_0_8 is not None:
            payload["observed_block_hilbert_function_0_8"] = list(self.observed_block_hilbert_function_0_8)
        return payload


def build_hilbert_burch_block_theorem_evidence(repo_root: Path) -> dict[str, Any]:
    """Build deterministic evidence for the 84/84a Hilbert-Burch explanation."""
    primary = {arrangement_id: _verify_primary_arrangement(_primary_arrangement(arrangement_id), repo_root) for arrangement_id in PRIMARY_ARRANGEMENTS}
    controls = {arrangement_id: _verify_control_arrangement(arrangement_id, repo_root) for arrangement_id in CONTROL_ARRANGEMENTS}
    theorem_status = _overall_theorem_status(primary)
    return {
        "schema": "hodgecy_ii_hilbert_burch_block_theorem.v1",
        "hodgecy_version": HODGECY_VERSION,
        "status": theorem_status,
        "supported_statement": _supported_statement(),
        "proof_obligations_open": _proof_obligations_open(),
        "primary_arrangements": primary,
        "control_examples": controls,
        "general_formula": {
            "status": "PROVED_WITH_HYPOTHESES",
            "hypotheses": [
                "S = k[x0,x1,x2,x3].",
                "L_1,...,L_s are distinct linear forms.",
                "Every pair has rank 2.",
                "Every triple has rank at least 3; equivalently no three planes contain a line.",
                "Q has degree q and is a non-zero-divisor on S/I_C.",
            ],
            "line_skeleton_resolution": "0 -> S(-s)^(s-1) -> S(-(s-1))^s -> I_C -> 0",
            "line_skeleton_hilbert_series": "(1 - s*t^(s-1) + (s-1)*t^s)/(1-t)^4",
            "block_hilbert_series": "(1-t^q)*(1 - s*t^(s-1) + (s-1)*t^s)/(1-t)^4",
        },
        "firewall": {
            "ordinary_node_verified_promoted": False,
            "classical_defect_promoted": False,
            "full_singular_scheme_equals_block_scheme_claimed": False,
            "source_to_evaluation_map_constructed": False,
            "evaluation_relations_identified_with_hodge_atoms": False,
            "vanishing_cycle_or_lmhs_claimed": False,
            "integral_evaluation_lattice_constructed": False,
        },
        "content_hash": stable_sha256(
            {
                "primary": primary,
                "controls": controls,
                "statement": _supported_statement(),
                "firewall_version": 1,
            }
        ),
    }


def write_hilbert_burch_evidence(repo_root: Path) -> tuple[Path, Path, dict[str, Any]]:
    payload = build_hilbert_burch_block_theorem_evidence(repo_root)
    target_dir = repo_root / THEOREM_EVIDENCE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    json_path = target_dir / "hilbert_burch_block_theorem.json"
    md_path = target_dir / "hilbert_burch_block_theorem.md"
    import json

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_evidence_markdown(payload), encoding="utf-8")
    return json_path, md_path, payload


def line_skeleton_hilbert_value(s: int, degree: int) -> int:
    return _binom(degree + 3, 3) - s * _binom(degree - s + 4, 3) + (s - 1) * _binom(degree - s + 3, 3)


def block_hilbert_value(s: int, q: int, degree: int) -> int:
    return line_skeleton_hilbert_value(s, degree) - line_skeleton_hilbert_value(s, degree - q)


def _verify_primary_arrangement(arrangement: PlaneArrangement, repo_root: Path) -> dict[str, Any]:
    skeleton = verify_arrangement_skeleton(arrangement)
    block = verify_arrangement_block_theorem(arrangement, repo_root)
    return {"line_skeleton": skeleton.to_dict(), "quartic_block": block.to_dict()}


def verify_arrangement_skeleton(arrangement: PlaneArrangement) -> ArrangementSkeletonVerification:
    forms = tuple(str(sp.factor(form)) for form in plane_linear_forms(arrangement).values())
    s = len(forms)
    pairwise = _pairwise_independent(arrangement)
    triple_distribution = _triple_rank_distribution(arrangement)
    triple_condition = all(int(rank) >= 3 for rank in triple_distribution)
    minors_ok, syzygies_ok = _verify_hilbert_burch_minors_and_syzygies(arrangement)
    hypotheses_ok = pairwise and triple_condition and minors_ok and syzygies_ok
    hilbert_values = tuple(line_skeleton_hilbert_value(s, degree) for degree in range(13))
    return ArrangementSkeletonVerification(
        arrangement_id=arrangement.arrangement_id,
        plane_equations=forms,
        plane_hash=stable_sha256(forms),
        pair_count=comb(s, 2),
        pairwise_independent=pairwise,
        triple_rank_condition=triple_condition,
        triple_rank_distribution=triple_distribution,
        no_three_planes_contain_a_line=triple_condition,
        height_status="PROVED" if pairwise else "OPEN",
        hilbert_burch_matrix_shape=(s, s - 1),
        maximal_minors_match_generators=minors_ok,
        syzygies_verified=syzygies_ok,
        ideal_equality_status="PROVED_BY_VERIFIED_CODIMENSION_TWO_STAR_CONFIGURATION_THEOREM" if hypotheses_ok else "OPEN",
        ideal_saturation_status="PROVED_BY_PERFECT_HEIGHT_TWO_POSITIVE_DIMENSION_QUOTIENT" if hypotheses_ok else "OPEN",
        line_skeleton_resolution=f"0 -> S(-{s})^{s - 1} -> S(-{s - 1})^{s} -> I_C -> 0",
        line_skeleton_hilbert_series=f"(1 - {s}*t^{s - 1} + {s - 1}*t^{s})/(1-t)^4",
        line_skeleton_hilbert_function_0_12=hilbert_values,
        line_skeleton_degree=comb(s, 2),
        reducedness_status="PROVED_AS_INTERSECTION_OF_DISTINCT_LINE_PRIMES" if hypotheses_ok else "OPEN",
        embedded_components_status="PROVED_NONE_BY_SATURATED_UNMIXED_PERFECT_IDEAL" if hypotheses_ok else "OPEN",
        theorem_hypotheses_status="VERIFIED" if hypotheses_ok else "OPEN",
    )


def verify_arrangement_block_theorem(arrangement: PlaneArrangement, repo_root: Path) -> BlockTheoremVerification:
    profile_checks = [line_genericity_check(arrangement, line_id=f"L{index:02d}", planes=(left.label, right.label)) for index, (left, right) in enumerate(combinations(arrangement.planes, 2), start=1)]
    squarefree = all(check.has_four_simple_zeros and check.degree == 4 for check in profile_checks)
    observed: tuple[int, ...] | None = None
    matches: bool | None = None
    if arrangement.arrangement_id in PRIMARY_ARRANGEMENTS:
        cert_path = repo_root / THEOREM_EVIDENCE_DIR / "block_geometry" / arrangement.arrangement_id / "node_block_certificate.json"
        scheme = load_blob12_block_scheme(cert_path)
        existing = compute_block_evaluation_result(scheme, degrees=range(0, 9))
        observed = tuple(value.H_B_d for value in existing.hilbert_table.values)
        matches = observed == tuple(block_hilbert_value(8, 4, degree) for degree in range(9))
    theoretical = tuple(block_hilbert_value(8, 4, degree) for degree in range(13))
    h1 = 112 - block_hilbert_value(8, 4, 8)
    return BlockTheoremVerification(
        arrangement_id=arrangement.arrangement_id,
        quartic=str(candidate_quartic()),
        quartic_regular_status="PROVED" if squarefree else "OPEN",
        quartic_regular_reason=(
            "Q restricts to a nonzero squarefree quartic on every associated line prime of the reduced line skeleton."
            if squarefree
            else "At least one line restriction failed to certify a nonzero squarefree quartic."
        ),
        line_restrictions_checked=len(profile_checks),
        squarefree_degree_four_restrictions=squarefree,
        block_resolution="0 -> S(-12)^7 -> S(-11)^8 + S(-8)^7 -> S(-7)^8 + S(-4) -> S -> S/I_B -> 0"
        if squarefree
        else None,
        block_hilbert_series="(1-t^4)*(1 - 8*t^7 + 7*t^8)/(1-t)^4" if squarefree else None,
        theoretical_hilbert_function_0_12=theoretical if squarefree else None,
        observed_block_hilbert_function_0_8=observed,
        formula_matches_existing_block_computation=matches,
        stabilization_degree=9 if squarefree else None,
        h1_i_b_8_dimension=h1 if squarefree else None,
        evaluation_deficiency_explanation_status="PROVED_FOR_VERIFIED_BLOCK_SCHEME" if squarefree and matches else "OPEN",
        classical_defect_status="CONDITIONAL_NOT_PROMOTED",
    )


def _verify_control_arrangement(arrangement_id: str, repo_root: Path) -> dict[str, Any]:
    source_path = repo_root / "release" / "hodgecy-v0.2.0" / "arrangements" / arrangement_id / "source.json"
    summary_path = repo_root / "release" / "hodgecy-v0.2.0" / "arrangements" / arrangement_id / "theorem_summary.json"
    arrangement = _load_arrangement_from_source(source_path)
    skeleton = verify_arrangement_skeleton(arrangement)
    import json

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    return {
        "line_skeleton": skeleton.to_dict(),
        "quartic_block": {
            "status": "NOT_APPLICABLE",
            "reason": "Exact control arrangement planes are available, but quartic_perturbation is null in the release theorem summary.",
            "quartic_perturbation": summary.get("quartic_perturbation"),
        },
    }


def _verify_hilbert_burch_minors_and_syzygies(arrangement: PlaneArrangement) -> tuple[bool, bool]:
    symbols = sp.symbols(" ".join(VARIABLES))
    forms = tuple(plane_linear_forms(arrangement).values())
    s = len(forms)
    product = sp.prod(forms)
    generators = tuple(sp.expand(product / form) for form in forms)
    matrix = sp.zeros(s, s - 1)
    for index in range(s - 1):
        matrix[index, index] = forms[index]
        matrix[s - 1, index] = -forms[s - 1]
    minors_ok = True
    for deleted_row in range(s):
        submatrix = matrix.copy()
        submatrix.row_del(deleted_row)
        determinant = sp.expand(submatrix.det())
        if sp.expand(determinant - generators[deleted_row]) != 0 and sp.expand(determinant + generators[deleted_row]) != 0:
            minors_ok = False
            break
    syzygies_ok = all(sp.expand(forms[index] * generators[index] - forms[-1] * generators[-1]) == 0 for index in range(s - 1))
    return bool(minors_ok), bool(syzygies_ok and all(sp.Poly(generator, *symbols, domain="QQ").total_degree() == s - 1 for generator in generators))


def _primary_arrangement(arrangement_id: str) -> PlaneArrangement:
    if arrangement_id == "84":
        return arrangement_84()
    if arrangement_id == "84a":
        return arrangement_84a()
    raise ValueError(f"Unsupported primary arrangement: {arrangement_id}")


def _load_arrangement_from_source(path: Path) -> PlaneArrangement:
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    planes = [
        Plane(
            label=str(item["label"]),
            coefficients=tuple(int(coefficient) for coefficient in item["coefficients"]),  # type: ignore[arg-type]
            equation=str(item["equation"]),
        )
        for item in payload["ordered_factor_list"]
    ]
    return PlaneArrangement(arrangement_id=str(payload["arrangement_id"]), planes=planes, source=path.as_posix())


def _pairwise_independent(arrangement: PlaneArrangement) -> bool:
    return all(sp.Matrix([left.coefficients, right.coefficients]).rank() == 2 for left, right in combinations(arrangement.planes, 2))


def _triple_rank_distribution(arrangement: PlaneArrangement) -> dict[str, int]:
    distribution: dict[str, int] = {}
    for triple in combinations(arrangement.planes, 3):
        rank = str(sp.Matrix([plane.coefficients for plane in triple]).rank())
        distribution[rank] = distribution.get(rank, 0) + 1
    return dict(sorted(distribution.items()))


def _binom(n: int, k: int) -> int:
    return 0 if n < k or n < 0 else comb(n, k)


def _overall_theorem_status(primary: dict[str, Any]) -> str:
    for payload in primary.values():
        skeleton = payload["line_skeleton"]
        block = payload["quartic_block"]
        if skeleton["theorem_hypotheses_status"] != "VERIFIED":
            return "PARTIALLY_VERIFIED"
        if block["evaluation_deficiency_explanation_status"] != "PROVED_FOR_VERIFIED_BLOCK_SCHEME":
            return "PARTIALLY_VERIFIED"
    return "PROVED_WITH_STATED_HYPOTHESES"


def _supported_statement() -> str:
    return (
        "For the frozen 84 and 84a eight-plane arrangements, the ideal generated by the sevenfold products F/L_i "
        "is the saturated reduced codimension-two line-skeleton ideal because the verified no-three-planes-on-a-line "
        "hypothesis makes the codimension-two star-configuration theorem applicable. Its Hilbert-Burch resolution is "
        "0 -> S(-8)^7 -> S(-7)^8 -> I_C -> 0. The frozen quartic Q is a non-zero-divisor on S/I_C, so the verified "
        "block scheme B = C cap V(Q) has mapping-cone resolution "
        "0 -> S(-12)^7 -> S(-11)^8 + S(-8)^7 -> S(-7)^8 + S(-4) -> S -> S/I_B -> 0, "
        "Hilbert series (1-t^4)(1-8t^7+7t^8)/(1-t)^4, Hilbert function "
        "1,4,10,20,34,52,74,92,105,112,112,..., and dim H^1(P^3,I_B(8)) = 7. "
        "This proves the structural explanation only for the verified block scheme, not the classical nodal defect."
    )


def _proof_obligations_open() -> list[str]:
    return [
        "The final saturated Jacobian/full singular scheme is still not identified with the block scheme.",
        "Ordinary-node promotion remains open.",
        "The classical nodal defect remains conditional.",
        "No source-to-evaluation, vanishing-cycle, LMHS, MHM, or Hodge-atom morphism is constructed.",
        "No integral evaluation-relation lattice is constructed.",
    ]


def _evidence_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Hilbert-Burch Block Theorem Evidence",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Supported Statement",
        "",
        payload["supported_statement"],
        "",
        "## 84 / 84a Results",
        "",
        "| arrangement | line ideal | Q regular | H_B(0..8) | H^1(I_B(8)) | classical defect |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for arrangement_id in PRIMARY_ARRANGEMENTS:
        result = payload["primary_arrangements"][arrangement_id]
        skeleton = result["line_skeleton"]
        block = result["quartic_block"]
        lines.append(
            "| "
            + " | ".join(
                [
                    arrangement_id,
                    skeleton["ideal_equality_status"],
                    block["quartic_regular_status"],
                    ",".join(str(item) for item in block["observed_block_hilbert_function_0_8"]),
                    str(block["h1_i_b_8_dimension"]),
                    block["classical_defect_status"],
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Open Obligations",
            "",
            *[f"- {item}" for item in payload["proof_obligations_open"]],
            "",
            "## Firewall",
            "",
            "| claim | asserted |",
            "| --- | --- |",
        ]
    )
    for claim, asserted in payload["firewall"].items():
        lines.append(f"| {claim} | {asserted} |")
    lines.append("")
    return "\n".join(lines)
