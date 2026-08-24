from __future__ import annotations

import pytest

from hodgecy.core import EvidenceStatus, ResultKind
from hodgecy.geometry import ideal_of_points
from hodgecy.relations import (
    GeometricRelationPresentationUnavailableError,
    IntegralRelationModelUnavailableError,
    NodeGeneratorModule,
    NodeRelationComplex,
    RelationRealizationKind,
    TargetModule,
    VerifiedNodeSupportRequiredError,
    begin_node_relation_run,
    evaluation_relation_from_hilbert,
    evaluation_relation_from_matrix,
    evaluation_relation_from_points,
    persist_node_relation_complex,
    unsupported_exceptional_curve_relation,
    unsupported_vanishing_cycle_relation,
)
from hodgecy.storage import ResultStore


VARS = ("x0", "x1", "x2")
VERIFIED_SUPPORT = {"certificate_type": "finite_reduced_odp_support", "evidence_status": "verified"}


def _node_module(rank: int = 3, *, ring: str = "QQ") -> NodeGeneratorModule:
    return NodeGeneratorModule.from_verified_support(
        geometry_id="fixture",
        node_scheme_id="fixture-nodes",
        ordered_node_ids=[f"p{i}" for i in range(rank)],
        node_scheme_certificate=VERIFIED_SUPPORT,
        coefficient_ring=ring,
    )


def _store(tmp_path) -> ResultStore:
    store = ResultStore(tmp_path / "results.sqlite")
    store.initialize()
    store.add_geometry(geometry_id="fixture", display_name="Fixture", geometry_type="synthetic")
    return store


def test_node_generator_module_requires_verified_ordered_support() -> None:
    module = _node_module(2)
    assert module.rank == 2
    assert module.evidence_status is EvidenceStatus.VERIFIED

    with pytest.raises(VerifiedNodeSupportRequiredError):
        NodeGeneratorModule.from_degree_only(geometry_id="fixture", degree=112)
    with pytest.raises(VerifiedNodeSupportRequiredError):
        NodeGeneratorModule.from_verified_support(
            geometry_id="fixture",
            node_scheme_id="bad",
            ordered_node_ids=["p0"],
            node_scheme_certificate={"status": "unknown"},
        )


def test_generic_rational_presentation_computes_kernel_with_homological_convention() -> None:
    node_module = _node_module(3)
    target = TargetModule("T", "QQ", 2)
    complex = NodeRelationComplex.from_presentation(
        node_module=node_module,
        target_module=target,
        realization_matrix=[[1, 0, 1], [0, 1, 1]],
        realization_kind=RelationRealizationKind.USER_SUPPLIED,
        certificate={"status": "verified"},
    )

    assert complex.image_rank == 2
    assert complex.relation_rank == 1
    assert complex.cokernel_dimension == 0
    assert complex.to_dict()["homological_convention"]["relation_module"] == "ker(rho)"


def test_evaluation_relation_uses_transpose_and_matches_cokernel_dimension() -> None:
    relation = evaluation_relation_from_matrix(
        [[1, 0, 0], [0, 1, 0], [1, 1, 0]],
        node_module=_node_module(3),
        degree=1,
        source_dimension=3,
        classical_defect=1,
    )

    assert relation.realization_kind is RelationRealizationKind.EVALUATION_CONDITION
    assert relation.realization_matrix == (("1", "0", "1"), ("0", "1", "1"), ("0", "0", "0"))
    assert relation.image_rank == 2
    assert relation.relation_rank == 1
    assert relation.certificate["relation_rank_identity"].startswith("dim ker(E^T)")


def test_point_evaluation_route_tracks_projective_trivialization() -> None:
    relation = evaluation_relation_from_points(
        [(1, 0, 0), (0, 1, 0), (1, 1, 0)],
        VARS,
        1,
        geometry_id="fixture",
        node_scheme_id="fixture-nodes",
        node_scheme_certificate=VERIFIED_SUPPORT,
    )

    assert relation.relation_rank == 1
    assert relation.target_module.rank == 3
    assert relation.certificate["trivialization"]["scaling_convention"] == "normalized projective coordinate representatives"


def test_hilbert_route_gives_rank_summary_without_claiming_matrix_basis() -> None:
    ideal = ideal_of_points([(1, 0, 0), (0, 1, 0), (1, 1, 0)], VARS)
    summary = evaluation_relation_from_hilbert(ideal, 1, node_scheme_id="fixture-nodes")

    assert summary.evaluation_rank == 2
    assert summary.relation_rank == 1
    assert summary.certificate["matrix_available"] is False


def test_basis_change_preserves_evaluation_relation_dimension() -> None:
    original = evaluation_relation_from_matrix(
        [[1, 0, 0], [0, 1, 0], [1, 1, 0]],
        node_module=_node_module(3),
        degree=1,
    )
    row_changed = evaluation_relation_from_matrix(
        [[1, 0, 0], [0, 1, 0], [2, 2, 0]],
        node_module=_node_module(3),
        degree=1,
    )

    assert original.relation_rank == row_changed.relation_rank == 1
    assert original.map_hash != row_changed.map_hash


def test_integral_presentation_requires_certificate_and_records_torsion() -> None:
    node_module = _node_module(2, ring="ZZ")
    target = TargetModule("T_Z", "ZZ", 2)
    with pytest.raises(IntegralRelationModelUnavailableError):
        NodeRelationComplex.from_presentation(
            node_module=node_module,
            target_module=target,
            realization_matrix=[[2, 0], [0, 1]],
            realization_kind=RelationRealizationKind.USER_SUPPLIED,
            certificate={"status": "verified"},
        )

    relation = NodeRelationComplex.from_presentation(
        node_module=node_module,
        target_module=target,
        realization_matrix=[[2, 0], [0, 1]],
        realization_kind=RelationRealizationKind.IMPORTED_CERTIFIED,
        certificate={"status": "verified", "integral_model_certified": True},
    )
    assert relation.relation_rank == 0
    assert relation.smith_normal_form == (1, 2)
    assert relation.torsion_type == (2,)


def test_same_matrix_different_realization_kind_is_a_different_complex() -> None:
    node_module = _node_module(2)
    target = TargetModule("T", "QQ", 2)
    left = NodeRelationComplex.from_presentation(
        node_module=node_module,
        target_module=target,
        realization_matrix=[[1, 0], [0, 1]],
        realization_kind=RelationRealizationKind.EVALUATION_CONDITION,
        certificate={"status": "verified"},
    )
    right = NodeRelationComplex.from_presentation(
        node_module=node_module,
        target_module=target,
        realization_matrix=[[1, 0], [0, 1]],
        realization_kind=RelationRealizationKind.VANISHING_CYCLE,
        certificate={"status": "verified"},
    )

    assert left.map_hash == right.map_hash
    assert left.complex_hash != right.complex_hash
    assert left.relation_rank == right.relation_rank == 0


def test_topological_relation_constructors_fail_clearly_without_topology() -> None:
    with pytest.raises(GeometricRelationPresentationUnavailableError):
        unsupported_vanishing_cycle_relation()
    with pytest.raises(GeometricRelationPresentationUnavailableError):
        unsupported_exceptional_curve_relation()


def test_node_relation_persistence_round_trip(tmp_path) -> None:
    store = _store(tmp_path)
    relation = evaluation_relation_from_matrix(
        [[1, 0, 0], [0, 1, 0], [1, 1, 0]],
        node_module=_node_module(3),
        degree=1,
    )
    run = begin_node_relation_run(store, "fixture", input_metadata=relation.to_dict())
    certificate, artifact, invariants = persist_node_relation_complex(store, run_id=run.run_id, complex=relation)
    store.complete_run(run.run_id)

    by_name = {item.invariant_name: item for item in store.get_invariants(geometry_id="fixture", result_kind=ResultKind.NODE_RELATION)}
    assert store.get_certificate(certificate.certificate_id).certificate_type == "node_relation_complex"
    assert artifact.role == "node_relation_complex"
    assert by_name["relation_realization_kind"].value == "evaluation_condition"
    assert by_name["relation_rank"].value == 1
    assert by_name["relation_snf"].evidence_status is EvidenceStatus.NOT_APPLICABLE
    assert {item.result_kind for item in invariants} == {ResultKind.NODE_RELATION}
