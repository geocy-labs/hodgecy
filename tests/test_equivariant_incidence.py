from __future__ import annotations

import json
from pathlib import Path

from hodgecy.equivariant import (
    apply_permutation_to_incidence_table,
    incidence_table_from_linear_forms,
    invariant_permutations,
    minimal_incidence_table,
    parse_linear_forms_from_record,
    singular_strata_from_incidence_table,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def control_records() -> dict[str, dict]:
    path = repo_root() / "data" / "raw" / "cynk_kocel_cynk_2026" / "control_triple_83_84_84a.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(record["arrangement_id"]): record for record in payload["records"]}


def test_incidence_table_is_stable_under_sorting_for_84() -> None:
    forms = parse_linear_forms_from_record(control_records()["84"])
    table = incidence_table_from_linear_forms(forms)
    scrambled = list(reversed(table)) + [table[0]]
    assert minimal_incidence_table(scrambled) == table
    assert len(table) == 10


def test_invariant_permutations_preserve_84a_incidence_table() -> None:
    forms = parse_linear_forms_from_record(control_records()["84a"])
    table = incidence_table_from_linear_forms(forms)
    permutations = invariant_permutations(table)
    assert len(permutations) == 24
    for permutation in permutations:
        assert apply_permutation_to_incidence_table(table, permutation) == table


def test_singular_strata_recover_known_84_inventory() -> None:
    forms = parse_linear_forms_from_record(control_records()["84"])
    table = incidence_table_from_linear_forms(forms)
    strata = singular_strata_from_incidence_table(table, forms)
    assert strata["inventory"]["p3"] == 16
    assert strata["inventory"]["p4_0"] == 10
    assert strata["inventory"]["double_lines"] == 28
    assert strata["inventory"]["triple_lines"] == 0
