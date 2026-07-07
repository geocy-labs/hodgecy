from __future__ import annotations

import json
from pathlib import Path

from hodgecy.smoothing import build_reviewer_v4_audit, write_reviewer_v4_audit


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_reviewer_v4_audit_writes_machine_readable_outputs() -> None:
    outputs = write_reviewer_v4_audit(repo_root())
    for path in outputs.values():
        assert path.exists()


def test_reviewer_v4_audit_claim_support_is_conservative() -> None:
    audit = build_reviewer_v4_audit(repo_root())
    claims = {claim.claim_id: claim for claim in audit.claims}
    assert claims["char0_degree_112"].repo_backed is True
    assert claims["reduced_true"].repo_backed is False
    assert claims["hessian_rank_3"].repo_backed is False
    assert claims["hilbert_degree_8_equals_105"].repo_backed is False
    assert claims["defect_equals_7"].repo_backed is False
    assert audit.promotion_recommendation == "remain_genericity_verified"


def test_reviewer_v4_degree_output_matches_claimed_112() -> None:
    outputs = write_reviewer_v4_audit(repo_root())
    payload = json.loads(outputs["degree_json"].read_text(encoding="utf-8"))
    assert payload["84"]["degree"] == 112
    assert payload["84a"]["degree"] == 112
