from __future__ import annotations

from hodgecy.profiles.atom_profile import HodgeCYAtomProfile, profile_from_defect, to_dict


def test_atom_profile_dataclass_instantiates() -> None:
    profile = HodgeCYAtomProfile(
        example_id="cm-atom",
        source_dataset="cynk_meyer",
        node_count=8,
        classical_defect=2,
        flexible_formal_rank=8,
        flexible_realized_rank=6,
        relation_rank=2,
        block_count=2,
        block_profile=[3, 5],
    )
    assert profile.example_id == "cm-atom"
    assert profile.operator_route_available is False


def test_profile_from_defect_sets_ranks_consistently() -> None:
    profile = profile_from_defect(
        example_id="cm-84",
        node_count=10,
        classical_defect=3,
        block_profile=[4, 6],
        source_dataset="cynk_meyer",
    )
    assert profile.flexible_formal_rank == 10
    assert profile.relation_rank == 3
    assert profile.flexible_realized_rank == 7
    assert profile.block_count == 2
    payload = to_dict(profile)
    assert payload["example_id"] == "cm-84"
