from __future__ import annotations

import json
from pathlib import Path

from hodgecy.equivariant import (
    build_gluing_matrix,
    cokernel_dimension_Q,
    incidence_table_from_linear_forms,
    kernel_dimension_Q,
    parse_linear_forms_from_record,
    rank_mod_p,
    rank_over_Q,
    singular_strata_from_incidence_table,
    smith_normal_form_invariants,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def control_records() -> dict[str, dict]:
    path = repo_root() / "data" / "raw" / "cynk_kocel_cynk_2026" / "control_triple_83_84_84a.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(record["arrangement_id"]): record for record in payload["records"]}


def matrix_for(arrangement_id: str):
    forms = parse_linear_forms_from_record(control_records()[arrangement_id])
    table = incidence_table_from_linear_forms(forms)
    strata = singular_strata_from_incidence_table(table, forms)
    return build_gluing_matrix(strata["double_lines"], strata["multiple_points"])


def test_84_and_84a_gluing_matrix_shapes_match_known_p3_p4_counts() -> None:
    matrix_84 = matrix_for("84")
    matrix_84a = matrix_for("84a")
    assert matrix_84.shape == (26, 28)
    assert matrix_84a.shape == (26, 28)
    assert rank_over_Q(matrix_84) == 26
    assert rank_over_Q(matrix_84a) == 26
    assert rank_mod_p(matrix_84, p=2) == 23
    assert rank_mod_p(matrix_84a, p=2) == 21
    assert kernel_dimension_Q(matrix_84) == 2
    assert cokernel_dimension_Q(matrix_84a) == 0


def test_smith_normal_form_is_computed_for_control_matrix() -> None:
    invariants = smith_normal_form_invariants(matrix_for("84"))
    assert invariants is not None
    assert len(invariants) == 26
