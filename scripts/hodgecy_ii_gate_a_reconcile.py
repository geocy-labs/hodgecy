"""Reconcile HodgeCY II Gate A ordinary-node evidence for 84 and 84a.

The script inventories historical stronger-claim artifacts, freezes exact input
identity records, and writes conservative certificate-status files. It does not
promote `ordinary_node_verified` unless every required certificate component is
present.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.research import GateAEvidenceState, gate_a_promotion_decision  # noqa: E402
from hodgecy.smoothing.verification import (  # noqa: E402
    arrangement_lookup,
    arrangement_polynomial,
    candidate_quartic,
    candidate_quartic_str,
    epsilon_value,
    singular_locus_generators,
    smoothing_polynomial,
)

ARRANGEMENTS = ("84", "84a")
OUT_DIR = REPO_ROOT / "research_outputs" / "hodgecy_ii"
RESEARCH_DIR = REPO_ROOT / "research" / "hodgecy_ii"

INVENTORY_FIELDS = (
    "arrangement",
    "artifact",
    "artifact_type",
    "originating_command",
    "software",
    "software_version",
    "input_equation_hash",
    "quartic_hash",
    "claimed_result",
    "machine_readable",
    "reproducible",
    "sufficient_for_status",
    "evidence_state",
    "notes",
)


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_tsv(path: Path, rows: list[dict[str, Any]], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def input_identity(arrangement_id: str) -> dict[str, Any]:
    arrangement = arrangement_lookup()[arrangement_id]
    arrangement_expr = str(arrangement_polynomial(arrangement))
    q0_expr = str(candidate_quartic())
    f_expr = str(smoothing_polynomial(arrangement))
    jacobian = singular_locus_generators(arrangement)
    identity = {
        "arrangement_id": arrangement_id,
        "coefficient_field": "QQ",
        "variables": ["x", "y", "z", "t"],
        "monomial_order": "dp",
        "arrangement_polynomial": arrangement_expr,
        "Q0": candidate_quartic_str(),
        "epsilon": str(epsilon_value()),
        "branch_polynomial": f_expr,
        "jacobian_generators": jacobian,
    }
    identity["hashes"] = {
        "arrangement_polynomial_sha256": stable_hash(arrangement_expr),
        "quartic_sha256": stable_hash(q0_expr),
        "branch_polynomial_sha256": stable_hash(f_expr),
        "jacobian_generators_sha256": stable_hash(jacobian),
    }
    return identity


def singular_candidate_script(identity: dict[str, Any]) -> str:
    generators = identity["jacobian_generators"]
    return "\n".join(
        [
            "// HodgeCY II Gate A candidate Jacobian input.",
            "// This is not a verified frozen radical node ideal.",
            'LIB "modstd.lib";',
            'ring R = 0, (x,y,z,t), dp;',
            f"poly F = {generators['F'].replace('**', '^')};",
            "ideal J = jacob(F);",
            "ideal sJ = modStd(J);",
            '"dim(cone) ="; dim(sJ);',
            '"degree ="; mult(sJ);',
            "quit;",
            "",
        ]
    )


def known_artifacts() -> list[dict[str, str]]:
    return [
        {
            "artifact": "data/processed/smoothing_verification_{arr}.json",
            "artifact_type": "processed_json",
            "originating_command": "python scripts/verify_smoothing_bridge_84_84a.py --force",
            "software": "Python/SymPy",
            "claimed_result": "G1/G2 exact genericity; degree112_certified status with reducedness/Hessian pending",
            "machine_readable": "YES",
            "reproducible": "YES",
            "sufficient_for_status": "NO",
            "evidence_state": GateAEvidenceState.REPRODUCIBLE_BUT_INCOMPLETE.value,
            "notes": "Exact genericity is useful, but ordinary-node fields are null.",
        },
        {
            "artifact": "data/processed/cas_certificates/reviewer_v4_degree_outputs.json",
            "artifact_type": "processed_json",
            "originating_command": "historical Singular modStd run",
            "software": "Singular",
            "claimed_result": "dim(cone)=1 and degree=112",
            "machine_readable": "YES",
            "reproducible": "PARTIAL",
            "sufficient_for_status": "NO",
            "evidence_state": GateAEvidenceState.REPRODUCIBLE_BUT_INCOMPLETE.value,
            "notes": "Backs degree only; not radicality/support/Hessian.",
        },
        {
            "artifact": "data/raw/hodgecy_v4_full/hodgecy_v4/scripts/nodes_q_{arr}.sing",
            "artifact_type": "cas_script",
            "originating_command": "Singular nodes_q_{arr}.sing",
            "software": "Singular",
            "claimed_result": "char-0 degree computation input",
            "machine_readable": "YES",
            "reproducible": "YES_IF_SINGULAR_AVAILABLE",
            "sufficient_for_status": "NO",
            "evidence_state": GateAEvidenceState.REPRODUCIBLE_BUT_INCOMPLETE.value,
            "notes": "Script computes standard basis degree, not radicality or Hessian rank.",
        },
        {
            "artifact": "data/raw/hodgecy_v4_full/hodgecy_v4/outputs/out{arr_label}.txt",
            "artifact_type": "cas_output_log",
            "originating_command": "Singular nodes_q_{arr}.sing",
            "software": "Singular",
            "claimed_result": "dim(cone)=1 and degree=112",
            "machine_readable": "PARTIAL",
            "reproducible": "YES_IF_SINGULAR_AVAILABLE",
            "sufficient_for_status": "NO",
            "evidence_state": GateAEvidenceState.REPRODUCIBLE_BUT_INCOMPLETE.value,
            "notes": "Machine-parsable degree output, but incomplete for promotion.",
        },
        {
            "artifact": "data/raw/hodgecy_v4_full/hodgecy_v4/scripts/nodes_84.sing",
            "artifact_type": "cas_script",
            "originating_command": "Singular nodes_84.sing",
            "software": "Singular",
            "claimed_result": "expected support comparison route for 84",
            "machine_readable": "YES",
            "reproducible": "UNKNOWN",
            "sufficient_for_status": "NO",
            "evidence_state": GateAEvidenceState.REPRODUCIBLE_BUT_INCOMPLETE.value,
            "notes": "Only present for 84; output not bundled as certificate-grade equality/radical/Hessian data.",
        },
        {
            "artifact": "data/raw/updated-files/COMPUTATION_LOG.md",
            "artifact_type": "prose_log",
            "originating_command": "historical manual computation log",
            "software": "mixed",
            "claimed_result": "ordinary-node and defect completion claimed in prose",
            "machine_readable": "NO",
            "reproducible": "NO",
            "sufficient_for_status": "NO",
            "evidence_state": GateAEvidenceState.LOG_ONLY.value,
            "notes": "Stronger than committed status; reconciled as log-only for reducedness/Hessian.",
        },
        {
            "artifact": "data/raw/updated-files/hodgecy_v4_inserts.tex",
            "artifact_type": "manuscript_insert",
            "originating_command": "historical manuscript draft",
            "software": "none",
            "claimed_result": "verified node theorem draft",
            "machine_readable": "NO",
            "reproducible": "NO",
            "sufficient_for_status": "NO",
            "evidence_state": GateAEvidenceState.LOG_ONLY.value,
            "notes": "Mathematical prose cannot replace certificate-grade CAS artifacts.",
        },
        {
            "artifact": "release/hodgecy-v0.2.0/arrangements/{arr}/theorem_summary.json",
            "artifact_type": "release_json",
            "originating_command": "python scripts/build_v0_2_0_release.py",
            "software": "Python",
            "claimed_result": "degree112_certified; ordinary_node_verified=false",
            "machine_readable": "YES",
            "reproducible": "YES",
            "sufficient_for_status": "NO",
            "evidence_state": GateAEvidenceState.REPRODUCIBLE_BUT_INCOMPLETE.value,
            "notes": "Canonical released status explicitly blocks ordinary-node promotion.",
        },
        {
            "artifact": "singular/smoothing_bridge_node_check.sing",
            "artifact_type": "template",
            "originating_command": "not executed",
            "software": "Singular",
            "claimed_result": "none",
            "machine_readable": "YES",
            "reproducible": "NO_OUTPUT",
            "sufficient_for_status": "NO",
            "evidence_state": GateAEvidenceState.UNKNOWN.value,
            "notes": "Handoff template only.",
        },
        {
            "artifact": "m2/smoothing_bridge_node_check.m2",
            "artifact_type": "template",
            "originating_command": "not executed",
            "software": "Macaulay2",
            "claimed_result": "none",
            "machine_readable": "YES",
            "reproducible": "NO_OUTPUT",
            "sufficient_for_status": "NO",
            "evidence_state": GateAEvidenceState.UNKNOWN.value,
            "notes": "Handoff template only.",
        },
    ]


def artifact_path(template: str, arrangement_id: str) -> Path:
    arr_label = "84a" if arrangement_id == "84a" else "84"
    output_label = "84a" if arrangement_id == "84a" else "84"
    value = template.format(arr=arr_label, arr_label=output_label)
    return REPO_ROOT / value


def inventory_rows(identities: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for arrangement_id in ARRANGEMENTS:
        hashes = identities[arrangement_id]["hashes"]
        for artifact in known_artifacts():
            path = artifact_path(artifact["artifact"], arrangement_id)
            if "{arr}" not in artifact["artifact"] and "{arr_label}" not in artifact["artifact"] and rows and rows[-1].get("artifact") == artifact["artifact"]:
                continue
            state = artifact["evidence_state"]
            notes = artifact["notes"]
            if not path.exists():
                state = GateAEvidenceState.UNKNOWN.value
                notes = f"Missing artifact at audit time: {notes}"
            rows.append(
                {
                    "arrangement": arrangement_id if ("{arr}" in artifact["artifact"] or "{arr_label}" in artifact["artifact"]) else "84,84a",
                    "artifact": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                    "artifact_type": artifact["artifact_type"],
                    "originating_command": artifact["originating_command"].format(arr=arrangement_id),
                    "software": artifact["software"],
                    "software_version": "unavailable_in_current_environment",
                    "input_equation_hash": hashes["branch_polynomial_sha256"],
                    "quartic_hash": hashes["quartic_sha256"],
                    "claimed_result": artifact["claimed_result"],
                    "machine_readable": artifact["machine_readable"],
                    "reproducible": artifact["reproducible"],
                    "sufficient_for_status": artifact["sufficient_for_status"],
                    "evidence_state": state,
                    "notes": f"{notes} file_sha256={file_hash(path) or 'missing'}",
                }
            )
    return rows


def component_decision(arrangement_id: str) -> dict[str, Any]:
    smoothing = read_json(REPO_ROOT / "data" / "processed" / f"smoothing_verification_{arrangement_id}.json")
    theorem = read_json(REPO_ROOT / "release" / "hodgecy-v0.2.0" / "arrangements" / arrangement_id / "theorem_summary.json")
    degree_outputs = read_json(REPO_ROOT / "data" / "processed" / "cas_certificates" / "reviewer_v4_degree_outputs.json")
    passed = {
        "saturated_jacobian_scheme": bool(degree_outputs[arrangement_id]["dimension"] == 1),
        "zero_dimensionality": bool(degree_outputs[arrangement_id]["dimension"] == 1 and theorem["quartic_perturbation"]["saturated_jacobian_scheme_dimension"] == 0),
        "degree_112": bool(degree_outputs[arrangement_id]["degree"] == 112 and smoothing["expected_node_count"] == 112),
        "support_matches_28x4_blocks": False,
        "radicality": False,
        "geometric_support_count_112": False,
        "branch_quadratic_rank_3": False,
        "double_cover_quadratic_rank_4": False,
        "frozen_exact_node_ideal": False,
        "reproducible_cas_metadata": False,
    }
    evidence = {
        "saturated_jacobian_scheme": GateAEvidenceState.REPRODUCIBLE_BUT_INCOMPLETE,
        "zero_dimensionality": GateAEvidenceState.REPRODUCIBLE_BUT_INCOMPLETE,
        "degree_112": GateAEvidenceState.REPRODUCIBLE_BUT_INCOMPLETE,
        "support_matches_28x4_blocks": GateAEvidenceState.LOG_ONLY,
        "radicality": GateAEvidenceState.LOG_ONLY,
        "geometric_support_count_112": GateAEvidenceState.LOG_ONLY,
        "branch_quadratic_rank_3": GateAEvidenceState.LOG_ONLY,
        "double_cover_quadratic_rank_4": GateAEvidenceState.LOG_ONLY,
        "frozen_exact_node_ideal": GateAEvidenceState.UNKNOWN,
        "reproducible_cas_metadata": GateAEvidenceState.REPRODUCIBLE_BUT_INCOMPLETE,
    }
    notes = {
        "saturated_jacobian_scheme": "Historical Singular degree output exists, but no frozen saturated ideal generators are present.",
        "zero_dimensionality": "Cone dimension 1 corresponds to projective dimension 0 for the historical run.",
        "degree_112": "Machine-readable historical degree output records 112.",
        "support_matches_28x4_blocks": "Formal 28 x 4 blocks exist, but no radical/equality certificate with the Jacobian support is present.",
        "radicality": "Reducedness is asserted in prose only.",
        "geometric_support_count_112": "No exact geometric support decomposition or component count is bundled.",
        "branch_quadratic_rank_3": "No per-component Hessian minor/rank certificate is bundled.",
        "double_cover_quadratic_rank_4": "No exact double-cover quadratic-rank certificate is bundled.",
        "frozen_exact_node_ideal": "No canonical radical node ideal artifact exists yet.",
        "reproducible_cas_metadata": "CAS executable/version is unavailable in this environment; historical script/output lacks full metadata.",
    }
    decision = gate_a_promotion_decision(
        arrangement_id,
        current_status=smoothing["verification_status"],
        passed_components=passed,
        component_evidence=evidence,
        component_notes=notes,
    )
    return decision.to_dict()


def write_arrangement_outputs(arrangement_id: str, identity: dict[str, Any], decision: dict[str, Any]) -> None:
    out = OUT_DIR / arrangement_id
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "jacobian_input.json", identity)
    (out / "candidate_jacobian_input.sing").write_text(singular_candidate_script(identity), encoding="utf-8")
    candidate_hash = file_hash(out / "candidate_jacobian_input.sing")
    status_payload = {
        "arrangement_id": arrangement_id,
        "status": "blocked",
        "ordinary_node_verified": False,
        "candidate_jacobian_input": "candidate_jacobian_input.sing",
        "candidate_jacobian_input_sha256": candidate_hash,
        "frozen_node_ideal": None,
        "reason": "No certificate-grade radical node ideal, support equality, or Hessian-rank certificate is present.",
        "missing_components": decision["missing_components"],
    }
    write_json(out / "frozen_node_ideal_status.json", status_payload)
    write_json(
        out / "support_certificate.json",
        {
            "arrangement_id": arrangement_id,
            "status": "UNRESOLVED",
            "block_count": 28,
            "formal_node_count": 112,
            "support_verified": False,
            "evidence_state": GateAEvidenceState.LOG_ONLY.value,
            "notes": "Formal blocks are available, but equality with the saturated Jacobian support is not certificate-grade.",
        },
    )
    write_json(
        out / "radicality_certificate.json",
        {
            "arrangement_id": arrangement_id,
            "status": "UNRESOLVED",
            "radical_verified": False,
            "evidence_state": GateAEvidenceState.LOG_ONLY.value,
            "notes": "Reducedness/radicality is asserted in historical prose only.",
        },
    )
    write_json(
        out / "local_hessian_certificate.json",
        {
            "arrangement_id": arrangement_id,
            "status": "UNRESOLVED",
            "branch_quadratic_rank_3_verified": False,
            "double_cover_quadratic_rank_4_verified": False,
            "evidence_state": GateAEvidenceState.LOG_ONLY.value,
            "notes": "No exact per-point or per-component Hessian minor certificate is bundled.",
        },
    )
    validation_path = out / "validation_manifest.json"
    validation = read_json(validation_path)
    validation.update(
        {
            "gate_a_reconciled": True,
            "support_verified": False,
            "radical_verified": False,
            "hessian_verified": False,
            "frozen_node_ideal": None,
            "gate_a_status": decision["promoted_status"],
            "gate_a_blockers": decision["missing_components"],
        }
    )
    write_json(validation_path, validation)


def update_research_manifest(decisions: dict[str, dict[str, Any]]) -> None:
    path = OUT_DIR / "hodgecy_ii_manifest.json"
    manifest = read_json(path)
    manifest.update(
        {
            "node_verified_84": False,
            "node_verified_84a": False,
            "node_count_84": None,
            "node_count_84a": None,
            "block_count_84": 28,
            "block_count_84a": 28,
            "support_verified_84": False,
            "support_verified_84a": False,
            "radical_verified_84": False,
            "radical_verified_84a": False,
            "hessian_verified_84": False,
            "hessian_verified_84a": False,
            "frozen_node_ideal_84": None,
            "frozen_node_ideal_84a": None,
            "gate_a_complete": False,
            "gate_a_blockers": {
                "84": decisions["84"]["missing_components"],
                "84a": decisions["84a"]["missing_components"],
            },
            "gate_a_reconciliation": "research_outputs/hodgecy_ii/gate_a_reconciliation_summary.json",
            "ready_for_defect_gate": False,
            "ready_for_source_to_node_gate": False,
        }
    )
    write_json(path, manifest)


def update_report() -> None:
    path = OUT_DIR / "hodgecy_ii_computational_report.md"
    text = path.read_text(encoding="utf-8")
    marker = "\n## Gate A Reconciliation\n"
    addition = """\n## Gate A Reconciliation\n\nHistorical stronger-claim artifacts were inventoried and reconciled. The only machine-readable certificate-level progress currently present is the historical Singular-backed degree output: both arrangements have cone dimension 1 and degree 112 for the Jacobian standard-basis computation. This supports `degree112_certified` but is not sufficient for `ordinary_node_verified`.\n\nThe following required components remain unresolved for both 84 and 84a:\n\n- support equality between the saturated Jacobian scheme and the predicted 28 x 4 block union\n- radicality / reducedness as a machine-readable exact certificate\n- geometric support count as 112 distinct points over Qbar\n- branch quadratic rank 3 at every support component\n- double-cover quadratic rank 4 at every support component\n- frozen exact radical node ideal\n- reproducible CAS metadata with executable/version in the current environment\n\nNo defect, source-to-node, or Hodge-atom gate was attempted in this pass. Gate A remains incomplete and the status for both arrangements remains `degree112_certified`.\n"""
    if marker in text:
        text = text.split(marker)[0].rstrip() + addition
    else:
        text = text.rstrip() + addition
    path.write_text(text, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    identities = {arrangement_id: input_identity(arrangement_id) for arrangement_id in ARRANGEMENTS}
    decisions = {arrangement_id: component_decision(arrangement_id) for arrangement_id in ARRANGEMENTS}

    for arrangement_id, identity in identities.items():
        write_arrangement_outputs(arrangement_id, identity, decisions[arrangement_id])

    rows = inventory_rows(identities)
    write_tsv(OUT_DIR / "gate_a_artifact_inventory.tsv", rows, INVENTORY_FIELDS)
    write_json(OUT_DIR / "gate_a_artifact_inventory.json", rows)

    raw_rows = [
        {
            "arrangement": "84,84a",
            "artifact": "data/raw/updated-files/COMPUTATION_LOG.md",
            "claim": "ordinary-node and defect completion",
            "same_inputs": "PLAUSIBLE_Q0_EPSILON_MATCH",
            "machine_readable": "NO",
            "reconciliation": "LOG_ONLY_NOT_PROMOTION_READY",
            "notes": "Prose claims are stronger than committed certificate fields.",
        },
        {
            "arrangement": "84,84a",
            "artifact": "data/raw/updated-files/hodgecy_v4_inserts.tex",
            "claim": "verified 112-node theorem draft",
            "same_inputs": "PLAUSIBLE_Q0_EPSILON_MATCH",
            "machine_readable": "NO",
            "reconciliation": "LOG_ONLY_NOT_PROMOTION_READY",
            "notes": "Manuscript theorem prose requires certificate-grade backing before status promotion.",
        },
        {
            "arrangement": "84,84a",
            "artifact": "data/processed/cas_certificates/reviewer_v4_claims.json",
            "claim": "degree backed; reducedness/Hessian log-only",
            "same_inputs": "YES",
            "machine_readable": "YES",
            "reconciliation": "AGREES_WITH_BLOCKED_STATUS",
            "notes": "This audit is the controlling reconciliation input for this checkpoint.",
        },
    ]
    write_tsv(
        OUT_DIR / "gate_a_raw_log_reconciliation.tsv",
        raw_rows,
        ("arrangement", "artifact", "claim", "same_inputs", "machine_readable", "reconciliation", "notes"),
    )
    write_json(
        OUT_DIR / "gate_a_reconciliation_summary.json",
        {
            "schema": "hodgecy_ii_gate_a_reconciliation.v1",
            "singular_available": shutil.which("Singular") is not None,
            "macaulay2_available": shutil.which("M2") is not None,
            "sage_available": shutil.which("sage") is not None,
            "input_identities": {
                arrangement_id: identities[arrangement_id]["hashes"] for arrangement_id in ARRANGEMENTS
            },
            "decisions": decisions,
            "gate_a_complete": False,
            "ready_for_defect_gate": False,
            "ready_for_source_to_node_gate": False,
            "raw_stronger_logs_reconciled": True,
        },
    )
    update_research_manifest(decisions)
    update_report()


if __name__ == "__main__":
    main()
