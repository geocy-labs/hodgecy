from __future__ import annotations

from hodgecy.operators.monodromy import MonodromyData, NilpotentProfile, operator_profile_placeholder
from hodgecy.operators.picard_fuchs import ConifoldPoint, PicardFuchsOperator


def test_operator_schema_dataclasses_instantiate() -> None:
    operator = PicardFuchsOperator(
        example_id="family-1",
        operator_label=None,
        order=None,
        coefficients=None,
        source=None,
    )
    point = ConifoldPoint(
        example_id="family-1",
        parameter_value=None,
        local_coordinate=None,
        multiplicity=None,
        source=None,
    )
    monodromy = MonodromyData(
        example_id="family-1",
        conifold_point=None,
        monodromy_matrix=None,
        nilpotent_matrix=None,
        rank_nilpotent=None,
        source=None,
    )
    nilpotent = NilpotentProfile(
        example_id="family-1",
        nilpotent_rank=None,
        nilpotent_index=None,
        is_conifold_type=None,
    )
    assert operator.status == "not_loaded"
    assert point.status == "candidate"
    assert monodromy.status == "not_computed"
    assert nilpotent.status == "not_computed"


def test_operator_profile_placeholder_is_not_computed() -> None:
    profile = operator_profile_placeholder("family-14")
    assert profile.example_id == "family-14"
    assert profile.operator_route_available is False
    assert profile.status == "not_computed"
