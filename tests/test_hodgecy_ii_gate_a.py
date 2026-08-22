from __future__ import annotations

import csv
import json
from pathlib import Path

from hodgecy.research import GATE_A_REQUIRED_COMPONENTS, GateAEvidenceState, gate_a_promotion_decision


REPO_ROOT = Path(__file__).resolve().parents[1]
GATE_A_ROOT = REPO_ROOT / "research_outputs" / "hodgecy_ii"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_gate_a_input_identity_hashes_are_frozen_for_both_arrangements() -> None:
    summary = _json(GATE_A_ROOT / "gate_a_reconciliation_summary.json")

    assert summary["input_identities"]["84"]["quartic_sha256"] == summary["input_identities"]["84a"]["quartic_sha256"]
    assert summary["input_identities"]["84"]["branch_polynomial_sha256"] != summary["input_identities"]["84a"]["branch_polynomial_sha256"]
    for arrangement_id in ("84", "84a"):
        identity = _json(GATE_A_ROOT / arrangement_id / "jacobian_input.json")
        assert identity["Q0"] == "x^4 + 2*y^4 + 3*z^4 + 5*t^4 + x*y*z*t"
        assert identity["epsilon"] == "1"
        assert set(identity["jacobian_generators"]) == {"F", "dF_dx", "dF_dy", "dF_dz", "dF_dt"}


def test_gate_a_artifact_inventory_marks_no_artifact_sufficient_for_promotion() -> None:
    with (GATE_A_ROOT / "gate_a_artifact_inventory.tsv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    assert rows
    assert all(row["sufficient_for_status"] == "NO" for row in rows)
    assert {row["evidence_state"] for row in rows} >= {
        GateAEvidenceState.REPRODUCIBLE_BUT_INCOMPLETE.value,
        GateAEvidenceState.LOG_ONLY.value,
    }


def test_gate_a_certificate_parsing_keeps_support_radical_hessian_unresolved() -> None:
    for arrangement_id in ("84", "84a"):
        support = _json(GATE_A_ROOT / arrangement_id / "support_certificate.json")
        radicality = _json(GATE_A_ROOT / arrangement_id / "radicality_certificate.json")
        hessian = _json(GATE_A_ROOT / arrangement_id / "local_hessian_certificate.json")

        assert support["block_count"] == 28
        assert support["formal_node_count"] == 112
        assert support["support_verified"] is False
        assert radicality["radical_verified"] is False
        assert hessian["branch_quadratic_rank_3_verified"] is False
        assert hessian["double_cover_quadratic_rank_4_verified"] is False


def test_gate_a_promotion_logic_requires_every_required_component() -> None:
    passed = {component: True for component in GATE_A_REQUIRED_COMPONENTS}
    passed["radicality"] = False

    decision = gate_a_promotion_decision(
        "84",
        current_status="degree112_certified",
        passed_components=passed,
        component_evidence={"radicality": GateAEvidenceState.LOG_ONLY},
    )

    assert decision.can_promote is False
    assert decision.promoted_status == "degree112_certified"
    assert "radicality" in decision.missing_components


def test_gate_a_summary_blocks_defect_and_source_to_node_gates() -> None:
    summary = _json(GATE_A_ROOT / "gate_a_reconciliation_summary.json")
    manifest = _json(GATE_A_ROOT / "hodgecy_ii_manifest.json")

    assert summary["raw_stronger_logs_reconciled"] is True
    assert summary["gate_a_complete"] is False
    assert manifest["node_verified_84"] is False
    assert manifest["node_verified_84a"] is False
    assert manifest["ready_for_defect_gate"] is False
    assert manifest["ready_for_source_to_node_gate"] is False
    for arrangement_id in ("84", "84a"):
        assert summary["decisions"][arrangement_id]["promoted_status"] == "degree112_certified"
        assert "frozen_exact_node_ideal" in summary["decisions"][arrangement_id]["missing_components"]
