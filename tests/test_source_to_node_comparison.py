from __future__ import annotations

import pytest

from hodgecy.core import EvidenceStatus, ResultKind
from hodgecy.relations import (
    ChainMapVerificationError,
    ComparisonMorphismKind,
    FeasibilityState,
    NodeGeneratorModule,
    NodeRelationComplex,
    RelationRealizationKind,
    SourceGeneratorAssignment,
    SourceToNodeChainMap,
    SourceTwoTermComplex,
    TargetModule,
    assignment_matrix,
    begin_source_to_node_run,
    compare_chain_maps,
    conditional_defect_feasibility_for_source_h1,
    h1_rank_feasibility,
    persist_source_to_node_chain_map,
)
from hodgecy.storage import ResultStore


VERIFIED_SUPPORT = {"certificate_type": "finite_support", "status": "verified"}


def _node_module(rank: int, *, ring: str = "QQ") -> NodeGeneratorModule:
    return NodeGeneratorModule.from_verified_support(
        geometry_id="fixture",
        node_scheme_id="fixture-nodes",
        ordered_node_ids=[f"n{i}" for i in range(rank)],
        node_scheme_certificate=VERIFIED_SUPPORT,
        coefficient_ring=ring,
    )


def _node_complex(matrix, *, kind=RelationRealizationKind.EVALUATION_CONDITION, ring: str = "QQ") -> NodeRelationComplex:
    rows = len(matrix)
    cols = len(matrix[0]) if matrix else 0
    return NodeRelationComplex.from_presentation(
        node_module=_node_module(cols, ring=ring),
        target_module=TargetModule("node-target", ring, rows),
        realization_matrix=matrix,
        realization_kind=kind,
        certificate={"status": "verified", "integral_model_certified": ring == "ZZ"},
    )


def _store(tmp_path) -> ResultStore:
    store = ResultStore(tmp_path / "results.sqlite")
    store.initialize()
    store.add_geometry(geometry_id="fixture", display_name="Fixture", geometry_type="synthetic")
    return store


def test_source_two_term_complex_records_homological_convention() -> None:
    source = SourceTwoTermComplex.from_matrix([[1, 0]], complex_id="src")

    assert source.c1_rank == 2
    assert source.c0_rank == 1
    assert source.h1_rank_q == 1
    assert source.h0_rank_q == 0
    assert source.to_dict()["homological_convention"]["H1"] == "ker(d_src)"


def test_identity_chain_map_has_full_h1_survival_and_h0_map() -> None:
    source = SourceTwoTermComplex.from_matrix([[0, 0]], complex_id="src")
    node = _node_complex([[0, 0]])
    chain_map = SourceToNodeChainMap.from_matrices(
        source_complex=source,
        node_complex=node,
        degree_1_map=[[1, 0], [0, 1]],
        degree_0_map=[[1]],
        construction_kind=ComparisonMorphismKind.USER_SUPPLIED,
        certificate={"status": "verified"},
    )

    assert chain_map.H1.induced_rank == 2
    assert chain_map.H1.kernel_rank == 0
    assert chain_map.H0.induced_rank == 1
    assert chain_map.survival_profile.injective is True
    assert chain_map.survival_profile.surjective is True
    assert chain_map.survival_profile.isomorphism is True


def test_zero_chain_map_kills_all_source_h1_classes() -> None:
    source = SourceTwoTermComplex.from_matrix([[0, 0]], complex_id="src")
    node = _node_complex([[0, 0]])
    chain_map = SourceToNodeChainMap.from_matrices(
        source_complex=source,
        node_complex=node,
        degree_1_map=[[0, 0], [0, 0]],
        degree_0_map=[[0]],
        construction_kind=ComparisonMorphismKind.USER_SUPPLIED,
        certificate={"status": "verified"},
    )

    assert chain_map.H1.induced_rank == 0
    assert chain_map.H1.kernel_rank == 2
    assert chain_map.survival_profile.surviving_rank == 0
    assert chain_map.survival_profile.injective is False


def test_noncommuting_square_fails_exactly() -> None:
    source = SourceTwoTermComplex.from_matrix([[1, 0]], complex_id="src")
    node = _node_complex([[1, 0]])

    with pytest.raises(ChainMapVerificationError):
        SourceToNodeChainMap.from_matrices(
            source_complex=source,
            node_complex=node,
            degree_1_map=[[0, 1], [1, 0]],
            degree_0_map=[[1]],
            construction_kind=ComparisonMorphismKind.USER_SUPPLIED,
            certificate={"status": "verified"},
        )


def test_partial_survival_computes_killed_and_surviving_ranks() -> None:
    source = SourceTwoTermComplex.from_matrix([[0, 0]], complex_id="src")
    node = _node_complex([[1, 0]])
    chain_map = SourceToNodeChainMap.from_matrices(
        source_complex=source,
        node_complex=node,
        degree_1_map=[[0, 0], [1, 0]],
        degree_0_map=[[0]],
        construction_kind=ComparisonMorphismKind.USER_SUPPLIED,
        certificate={"status": "verified"},
    )

    assert chain_map.survival_profile.source_h1_rank == 2
    assert chain_map.survival_profile.target_h1_rank == 1
    assert chain_map.survival_profile.killed_rank == 1
    assert chain_map.survival_profile.surviving_rank == 1


def test_combination_records_dependencies_among_surviving_images() -> None:
    source = SourceTwoTermComplex.from_matrix([[0, 0]], complex_id="src")
    node = _node_complex([[1, 0]])
    chain_map = SourceToNodeChainMap.from_matrices(
        source_complex=source,
        node_complex=node,
        degree_1_map=[[0, 0], [1, 1]],
        degree_0_map=[[0]],
        construction_kind=ComparisonMorphismKind.USER_SUPPLIED,
        certificate={"status": "verified"},
    )

    assert chain_map.H1.induced_rank == 1
    assert chain_map.H1.dependency_basis != ()
    assert chain_map.H1.kernel_rank == 1


def test_equal_h1_dimensions_do_not_determine_map_behavior() -> None:
    source = SourceTwoTermComplex.from_matrix([[0]], complex_id="src")
    node = _node_complex([[0]])
    zero = SourceToNodeChainMap.from_matrices(
        source_complex=source,
        node_complex=node,
        degree_1_map=[[0]],
        degree_0_map=[[0]],
        construction_kind=ComparisonMorphismKind.USER_SUPPLIED,
        certificate={"status": "verified"},
    )
    iso = SourceToNodeChainMap.from_matrices(
        source_complex=source,
        node_complex=node,
        degree_1_map=[[1]],
        degree_0_map=[[1]],
        construction_kind=ComparisonMorphismKind.USER_SUPPLIED,
        certificate={"status": "verified"},
    )

    assert zero.H1.source_rank == iso.H1.source_rank == zero.H1.target_rank == iso.H1.target_rank == 1
    assert zero.survival_profile.isomorphism is False
    assert iso.survival_profile.isomorphism is True


def test_rational_and_integral_comparisons_remain_distinct() -> None:
    source_q = SourceTwoTermComplex.from_matrix([[0]], complex_id="src-q", coefficient_ring="QQ")
    node_q = _node_complex([[0]], ring="QQ")
    rational = SourceToNodeChainMap.from_matrices(
        source_complex=source_q,
        node_complex=node_q,
        degree_1_map=[["1/2"]],
        degree_0_map=[[1]],
        construction_kind=ComparisonMorphismKind.USER_SUPPLIED,
        certificate={"status": "verified"},
    )
    source_z = SourceTwoTermComplex.from_matrix([[0]], complex_id="src-z", coefficient_ring="ZZ")
    node_z = _node_complex([[0]], ring="ZZ")
    integral = SourceToNodeChainMap.from_matrices(
        source_complex=source_z,
        node_complex=node_z,
        degree_1_map=[[2]],
        degree_0_map=[[1]],
        construction_kind=ComparisonMorphismKind.USER_SUPPLIED,
        certificate={"status": "verified", "integral_model_certified": True},
    )

    assert rational.survival_profile.coefficient_ring == "QQ"
    assert integral.survival_profile.coefficient_ring == "ZZ"
    assert rational.survival_profile.torsion is None
    assert integral.survival_profile.torsion == (2,)


def test_integral_h0_map_records_cokernel_structures_where_supported() -> None:
    source = SourceTwoTermComplex.from_matrix([[2]], complex_id="src-z", coefficient_ring="ZZ")
    node = _node_complex([[4]], ring="ZZ")
    chain_map = SourceToNodeChainMap.from_matrices(
        source_complex=source,
        node_complex=node,
        degree_1_map=[[1]],
        degree_0_map=[[2]],
        construction_kind=ComparisonMorphismKind.USER_SUPPLIED,
        certificate={"status": "verified", "integral_model_certified": True},
    )

    assert chain_map.H0.source_rank == 0
    assert chain_map.H0.certificate["source_cokernel_structure"]["torsion_invariant_factors"] == [2]
    assert chain_map.H0.certificate["target_cokernel_structure"]["torsion_invariant_factors"] == [4]


def test_target_relation_kind_is_preserved_in_chain_map_hash() -> None:
    source = SourceTwoTermComplex.from_matrix([[0]], complex_id="src")
    eval_target = _node_complex([[0]], kind=RelationRealizationKind.EVALUATION_CONDITION)
    van_target = _node_complex([[0]], kind=RelationRealizationKind.VANISHING_CYCLE)
    eval_map = SourceToNodeChainMap.from_matrices(
        source_complex=source,
        node_complex=eval_target,
        degree_1_map=[[1]],
        degree_0_map=[[1]],
        construction_kind=ComparisonMorphismKind.USER_SUPPLIED,
        certificate={"status": "verified"},
    )
    van_map = SourceToNodeChainMap.from_matrices(
        source_complex=source,
        node_complex=van_target,
        degree_1_map=[[1]],
        degree_0_map=[[1]],
        construction_kind=ComparisonMorphismKind.USER_SUPPLIED,
        certificate={"status": "verified"},
    )

    assert eval_map.node_complex.realization_kind is RelationRealizationKind.EVALUATION_CONDITION
    assert van_map.node_complex.realization_kind is RelationRealizationKind.VANISHING_CYCLE
    assert eval_map.chain_map_hash != van_map.chain_map_hash


def test_feasibility_obstruction_does_not_construct_morphism() -> None:
    impossible = h1_rank_feasibility(source_h1_rank=2, target_h1_rank=1)
    possible = h1_rank_feasibility(source_h1_rank=2, target_h1_rank=2)
    unknown = h1_rank_feasibility(source_h1_rank=2, target_h1_rank=None)

    assert impossible.injective is FeasibilityState.IMPOSSIBLE
    assert impossible.surjective is FeasibilityState.POSSIBLE
    assert possible.isomorphism is FeasibilityState.POSSIBLE
    assert unknown.evidence_status is EvidenceStatus.UNKNOWN
    assert "feasibility is not existence" in impossible.reason.lower()


def test_generator_assignments_build_degree_map_matrix() -> None:
    assignments = [
        SourceGeneratorAssignment.from_terms("a", [("n0", 1), ("n1", -2)], geometric_justification="synthetic"),
        SourceGeneratorAssignment.from_terms("b", [("n1", 3)]),
    ]

    matrix = assignment_matrix(assignments, source_basis=("a", "b"), target_basis=("n0", "n1"))
    assert matrix == (("1", "0"), ("-2", "3"))


def test_compare_chain_maps_uses_explicit_f1_f0_equality_only() -> None:
    source = SourceTwoTermComplex.from_matrix([[0]], complex_id="src")
    node = _node_complex([[0]])
    first = SourceToNodeChainMap.from_matrices(
        source_complex=source,
        node_complex=node,
        degree_1_map=[[1]],
        degree_0_map=[[1]],
        construction_kind=ComparisonMorphismKind.USER_SUPPLIED,
        certificate={"status": "verified"},
    )
    second = SourceToNodeChainMap.from_matrices(
        source_complex=source,
        node_complex=node,
        degree_1_map=[[0]],
        degree_0_map=[[0]],
        construction_kind=ComparisonMorphismKind.USER_SUPPLIED,
        certificate={"status": "verified"},
    )

    assert compare_chain_maps(first, first)["equal"] is True
    assert compare_chain_maps(first, second)["equal"] is False


def test_persistence_records_chain_map_certificate_and_survival(tmp_path) -> None:
    store = _store(tmp_path)
    source = SourceTwoTermComplex.from_matrix([[0]], complex_id="src")
    node = _node_complex([[0]])
    chain_map = SourceToNodeChainMap.from_matrices(
        source_complex=source,
        node_complex=node,
        degree_1_map=[[1]],
        degree_0_map=[[1]],
        construction_kind=ComparisonMorphismKind.USER_SUPPLIED,
        certificate={"status": "verified"},
    )
    run = begin_source_to_node_run(store, "fixture", input_metadata=chain_map.to_dict())
    certificate, artifact, invariants = persist_source_to_node_chain_map(store, run_id=run.run_id, chain_map=chain_map)
    store.complete_run(run.run_id)

    by_name = {item.invariant_name: item for item in store.get_invariants(geometry_id="fixture", result_kind=ResultKind.NODE_RELATION)}
    assert store.get_certificate(certificate.certificate_id).certificate_type == "source_to_node_chain_map"
    assert artifact.role == "source_to_node_chain_map"
    assert by_name["chain_map_verified"].value is True
    assert by_name["H1_induced_rank"].value == 1
    assert by_name["surviving_rank"].value == 1
    assert {item.result_kind for item in invariants} == {ResultKind.NODE_RELATION}


def test_conditional_defect_feasibility_for_84_style_source_h1() -> None:
    conditions = conditional_defect_feasibility_for_source_h1(2)

    assert conditions[0]["condition"] == "defect = 0"
    assert conditions[0]["implication"] == "any induced H1 map is zero"
    assert conditions[1]["condition"] == "defect = 1"
    assert conditions[1]["injective"] is False
    assert conditions[2]["existence_statement"] is False
