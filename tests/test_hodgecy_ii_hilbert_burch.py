from __future__ import annotations

import json
from pathlib import Path

from hodgecy.arrangements import arrangement_84, arrangement_84a
from hodgecy.geometry.hilbert_burch import (
    block_hilbert_value,
    line_skeleton_hilbert_value,
    verify_arrangement_skeleton,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_84_and_84a_satisfy_hilbert_burch_line_skeleton_hypotheses() -> None:
    for arrangement in (arrangement_84(), arrangement_84a()):
        result = verify_arrangement_skeleton(arrangement)

        assert result.pair_count == 28
        assert result.pairwise_independent is True
        assert result.triple_rank_distribution == {"3": 56}
        assert result.no_three_planes_contain_a_line is True
        assert result.maximal_minors_match_generators is True
        assert result.syzygies_verified is True
        assert result.ideal_equality_status == "PROVED_BY_VERIFIED_CODIMENSION_TWO_STAR_CONFIGURATION_THEOREM"
        assert result.ideal_saturation_status == "PROVED_BY_PERFECT_HEIGHT_TWO_POSITIVE_DIMENSION_QUOTIENT"


def test_hilbert_burch_formula_gives_verified_block_profile_and_tail() -> None:
    assert [line_skeleton_hilbert_value(8, degree) for degree in range(0, 6)] == [1, 4, 10, 20, 35, 56]
    assert [block_hilbert_value(8, 4, degree) for degree in range(0, 13)] == [
        1,
        4,
        10,
        20,
        34,
        52,
        74,
        92,
        105,
        112,
        112,
        112,
        112,
    ]
    assert 112 - block_hilbert_value(8, 4, 8) == 7


def test_hilbert_burch_evidence_is_firewalled() -> None:
    payload = json.loads(
        (
            repo_root()
            / "research_outputs"
            / "hodgecy_ii"
            / "final"
            / "theorem_evidence"
            / "hilbert_burch_block_theorem.json"
        ).read_text(encoding="utf-8")
    )

    assert payload["status"] == "PROVED_WITH_STATED_HYPOTHESES"
    assert payload["primary_arrangements"]["84"]["quartic_block"]["h1_i_b_8_dimension"] == 7
    assert payload["primary_arrangements"]["84a"]["quartic_block"]["formula_matches_existing_block_computation"] is True
    assert payload["firewall"]["classical_defect_promoted"] is False
    assert payload["firewall"]["source_to_evaluation_map_constructed"] is False
    assert payload["control_examples"]["239"]["quartic_block"]["status"] == "NOT_APPLICABLE"
