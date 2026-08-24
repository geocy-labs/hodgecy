from __future__ import annotations

import json
from pathlib import Path

from hodgecy.research import GATE_A_REQUIRED_COMPONENTS, GateAEvidenceState, gate_a_promotion_decision


REPO_ROOT = Path(__file__).resolve().parents[1]
FINAL_ROOT = REPO_ROOT / "research_outputs" / "hodgecy_ii" / "final"
THEOREM_EVIDENCE_ROOT = FINAL_ROOT / "theorem_evidence"
ASSET_ROOT = REPO_ROOT / "research_outputs" / "hodgecy_ii" / "manuscript_assets"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_final_block_geometry_identity_hashes_are_frozen_for_both_arrangements() -> None:
    certificate = _json(THEOREM_EVIDENCE_ROOT / "block_geometry" / "block_geometry_certification_84_84a.json")
    by_arrangement = {item["arrangement_id"]: item for item in certificate["certifications"]}

    assert set(by_arrangement) == {"84", "84a"}
    assert certificate["ordinary_node_promotion"] == "UNKNOWN"
    assert certificate["blocked_step"] == "saturated_jacobian_ideal"
    assert by_arrangement["84"]["block_scheme_hash"] != by_arrangement["84a"]["block_scheme_hash"]

    for arrangement_id, item in by_arrangement.items():
        assert item["validation_status"]["block_scheme"] == "VERIFIED"
        assert item["validation_status"]["ordinary_node_verified"] == "UNKNOWN"
        assert item["validation_status"]["saturated_jacobian_ideal"] == "UNKNOWN"
        assert item["promotion_status"] == "UNKNOWN"
        assert item["backend"]["saturated_jacobian_reproducible_in_current_environment"] is False
        assert len(item["blocks"]) == 28
        assert sum(block["degree"] for block in item["blocks"]) == 112
        assert all(block["status"] == "VERIFIED" for block in item["blocks"])
        assert all(block["reduced"] is True for block in item["blocks"])


def test_final_theorem_evidence_manifests_resolve_block_geometry_and_evaluation() -> None:
    for arrangement_id in ("84", "84a"):
        manifest = _json(THEOREM_EVIDENCE_ROOT / arrangement_id / "manifest.json")
        block_path = REPO_ROOT / manifest["block_scheme"]["path"]
        evaluation_path = REPO_ROOT / manifest["evaluation_result"]["path"]
        hilbert_path = REPO_ROOT / manifest["hilbert_table"]["path"]

        assert block_path.exists()
        assert evaluation_path.exists()
        assert hilbert_path.exists()
        assert "final/theorem_evidence" in manifest["block_scheme"]["path"].replace("\\", "/")
        assert manifest["evaluation_result"]["H_B_8"] == 105
        assert manifest["evaluation_result"]["deficiency"] == 7
        assert manifest["source_signature"]["validation_status"] == "THEOREM_READY_SOURCE_CONTROL"


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


def test_final_status_matrix_blocks_defect_and_source_to_node_gates() -> None:
    final_results = _json(FINAL_ROOT / "hodgecy_ii_final_results.json")
    rows = _json(ASSET_ROOT / "tables" / "final_evidence_status_matrix.json")
    by_statement = {row["statement"]: row for row in rows}

    assert final_results["block_geometry_results"]["84"]["ordinary_node_status"] == "UNKNOWN"
    assert final_results["block_geometry_results"]["84a"]["ordinary_node_status"] == "UNKNOWN"
    assert final_results["evaluation_results"]["84"]["actual_classical_defect"] == "UNKNOWN"
    assert final_results["evaluation_results"]["84a"]["actual_classical_defect"] == "UNKNOWN"
    assert final_results["comparison_results"]["source_to_evaluation_chain_map"] == "unknown"
    assert by_statement["full ordinary-node promotion"]["status"] == "OPEN"
    assert by_statement["frozen saturated node ideal"]["status"] == "OPEN"
    assert by_statement["classical defect=7"]["status"] == "CONDITIONAL"
    assert by_statement["source-to-evaluation morphism"]["status"] == "OPEN"
