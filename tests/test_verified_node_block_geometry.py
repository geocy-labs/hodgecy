from __future__ import annotations

from hodgecy.arrangements import arrangement_84, arrangement_84a
from hodgecy.geometry.verified_node_blocks import build_node_block_certification, promotion_from_equal_length_subscheme


def test_equal_length_reduced_subscheme_promotes() -> None:
    status, reason = promotion_from_equal_length_subscheme(
        predicted_degree=112,
        ambient_degree=112,
        predicted_reduced=True,
        containment_verified=True,
        ambient_reduced=True,
    )

    assert status == "ordinary_node_verified"
    assert "Equal-length" in reason


def test_strict_smaller_subscheme_does_not_promote() -> None:
    status, reason = promotion_from_equal_length_subscheme(
        predicted_degree=108,
        ambient_degree=112,
        predicted_reduced=True,
        containment_verified=True,
        ambient_reduced=True,
    )

    assert status == "UNKNOWN"
    assert "differ" in reason


def test_nonreduced_ambient_doubled_point_does_not_falsely_promote() -> None:
    status, reason = promotion_from_equal_length_subscheme(
        predicted_degree=112,
        ambient_degree=112,
        predicted_reduced=True,
        containment_verified=True,
        ambient_reduced=False,
    )

    assert status == "UNKNOWN"
    assert "nonreduced" in reason


def test_84_and_84a_have_several_disjoint_reduced_blocks_without_promotion() -> None:
    for arrangement in (arrangement_84(), arrangement_84a()):
        cert = build_node_block_certification(arrangement)
        step_statuses = {step.certificate_type: step.status for step in cert.certificate_steps}

        assert len(cert.blocks) == 28
        assert sum(block.degree for block in cert.blocks) == 112
        assert all(block.reduced for block in cert.blocks)
        assert step_statuses["block_disjointness"] == "VERIFIED"
        assert step_statuses["global_block_scheme"] == "VERIFIED"
        assert step_statuses["block_jacobian_containment"] == "VERIFIED"
        assert step_statuses["saturated_jacobian_ideal"] == "UNKNOWN"
        assert cert.promotion_status == "UNKNOWN"
