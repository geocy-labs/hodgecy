from __future__ import annotations

from hodgecy.core import EvidenceStatus, ResultKind
from hodgecy.geometry import (
    DoubleCoverModel,
    PointClassification,
    ProjectiveHypersurface,
    ProjectivePoint,
    analyze_projective_singular_scheme,
    begin_node_geometry_run,
    certify_double_cover_odp,
    classify_affine_hypersurface_point,
    classify_projective_hypersurface_point,
    global_finite_reduced_odp_certificate,
    normalize_projective_coordinates,
    persist_singular_scheme_result,
    unique_projective_points,
)
from hodgecy.storage import ResultStore


def _store(tmp_path) -> ResultStore:
    store = ResultStore(tmp_path / "results.sqlite")
    store.initialize()
    store.add_geometry(geometry_id="fixture", display_name="Fixture", geometry_type="synthetic")
    return store


def test_exact_jacobian_ideal_creation_retains_F_and_derivatives() -> None:
    surface = ProjectiveHypersurface(("x0", "x1", "x2"), "x0*x1")
    generators = surface.singular_ideal_generators()
    assert [str(item) for item in generators] == ["x0*x1", "x1", "x0", "0"]


def test_affine_smooth_point_is_not_odp() -> None:
    certificate = classify_affine_hypersurface_point("x + y**2", ("x", "y"), (0, 0))
    assert certificate.classification is PointClassification.SMOOTH
    assert not certificate.ordinary_double_point


def test_projective_affine_chart_hessian_certifies_odp() -> None:
    surface = ProjectiveHypersurface(("x0", "x1", "x2", "x3"), "x1**2 + x2**2 + x3**2")
    certificate = classify_projective_hypersurface_point(surface, (1, 0, 0, 0))
    assert certificate.projective_chart == "x0"
    assert certificate.hessian_rank == 3
    assert certificate.classification is PointClassification.ORDINARY_DOUBLE_POINT


def test_degenerate_non_morse_singularity_is_not_odp() -> None:
    surface = ProjectiveHypersurface(("x0", "x1", "x2", "x3"), "x0*x1**2 + x0*x2**2 + x3**3")
    certificate = classify_projective_hypersurface_point(surface, (1, 0, 0, 0))
    assert certificate.classification is PointClassification.DEGENERATE_CRITICAL_POINT
    assert certificate.hessian_rank == 2


def test_projective_chart_prevents_homogeneous_hessian_misread() -> None:
    surface = ProjectiveHypersurface(("x0", "x1", "x2"), "x0*x1")
    certificate = classify_projective_hypersurface_point(surface, (0, 0, 1))
    assert certificate.projective_chart == "x2"
    assert certificate.ambient_local_dimension == 2
    assert certificate.hessian_rank == 2
    assert certificate.classification is PointClassification.ORDINARY_DOUBLE_POINT


def test_projective_singular_scheme_solves_zero_dimensional_support() -> None:
    surface = ProjectiveHypersurface(("x0", "x1", "x2"), "x0*x1")
    scheme = analyze_projective_singular_scheme(surface)
    assert scheme.is_zero_dimensional is True
    assert scheme.dimension == 0
    assert scheme.degree == 1
    assert scheme.support_cardinality == 1
    assert scheme.support[0].coordinates == (0, 0, 1)
    assert scheme.is_reduced is True


def test_positive_dimensional_singular_scheme_does_not_claim_finite_support() -> None:
    surface = ProjectiveHypersurface(("x0", "x1", "x2"), "x0**2")
    scheme = analyze_projective_singular_scheme(surface)
    assert scheme.is_zero_dimensional is False
    assert scheme.is_complete is False
    assert scheme.degree is None


def test_projective_point_normalization_and_duplicate_removal_are_exact() -> None:
    assert normalize_projective_coordinates((2, 4, 6, 8)) == (1, 2, 3, 4)
    points = unique_projective_points([ProjectivePoint.from_iterable((1, 2, 3, 4)), (2, 4, 6, 8)])
    assert len(points) == 1
    assert points[0].point_id == "1:2:3:4"


def test_incomplete_candidate_support_does_not_pass_completeness() -> None:
    surface = ProjectiveHypersurface(("x0", "x1"), "x0**3*x1**3")
    scheme = analyze_projective_singular_scheme(surface, candidate_points=[(1, 0)])
    candidate_certificate = classify_projective_hypersurface_point(surface, (1, 0))
    assert candidate_certificate.classification is PointClassification.DEGENERATE_CRITICAL_POINT
    assert scheme.support_cardinality == 2
    assert scheme.candidate_support_complete is False
    assert scheme.is_reduced is False


def test_global_certificate_requires_every_prerequisite() -> None:
    surface = ProjectiveHypersurface(("x0", "x1"), "x0**3*x1**3")
    scheme = analyze_projective_singular_scheme(surface)
    certs = [classify_projective_hypersurface_point(surface, point) for point in scheme.support]
    global_cert = global_finite_reduced_odp_certificate(scheme, certs)
    assert global_cert.evidence_status is EvidenceStatus.UNKNOWN
    assert global_cert.reduced is False


def test_reducedness_unknown_is_preserved_when_chart_overlap_blocks_certificate() -> None:
    surface = ProjectiveHypersurface(("x0", "x1"), "(x0 - x1)**2")
    scheme = analyze_projective_singular_scheme(surface)
    assert scheme.support_cardinality == 1
    assert scheme.support[0].coordinates == (1, 1)
    assert scheme.is_reduced is None


def test_double_cover_local_model_certifies_total_space_odp() -> None:
    model = DoubleCoverModel(("x", "y", "z"), "x**2 + y**2 + z**2")
    certificate = certify_double_cover_odp(model, (0, 0, 0))
    assert certificate["verified"] is True
    assert certificate["branch_singularity_classification"] == "ORDINARY_DOUBLE_POINT"
    assert certificate["double_cover_total_space_classification"] == "ORDINARY_DOUBLE_POINT"
    assert certificate["total_space_hessian_rank"] == 4


def test_fixed_parameter_status_is_not_generic_parameter_status() -> None:
    surface = ProjectiveHypersurface(
        ("x0", "x1", "x2"),
        "x0*x1",
        parameter_specialization={"epsilon": "1", "generic_parameter_verified": "false"},
    )
    assert surface.parameter_specialization["epsilon"] == "1"
    assert surface.parameter_specialization["generic_parameter_verified"] == "false"


def test_node_geometry_persistence_round_trip_and_firewall(tmp_path) -> None:
    store = _store(tmp_path)
    surface = ProjectiveHypersurface(("x0", "x1", "x2"), "x0*x1", geometry_id="fixture")
    scheme = analyze_projective_singular_scheme(surface)
    point_certificates = [classify_projective_hypersurface_point(surface, point) for point in scheme.support]
    run = begin_node_geometry_run(store, "fixture", input_metadata=surface.to_dict())
    certificate, invariants = persist_singular_scheme_result(store, run_id=run.run_id, scheme=scheme, point_certificates=point_certificates)
    store.complete_run(run.run_id)

    restored_certificate = store.get_certificate(certificate.certificate_id)
    by_name = {item.invariant_name: item for item in store.get_invariants(geometry_id="fixture")}
    assert restored_certificate.evidence["global_certificate"]["evidence_status"] == "verified"
    assert by_name["singular_scheme_degree"].value == 1
    assert by_name["finite_reduced_odp_scheme"].evidence_status is EvidenceStatus.VERIFIED
    assert {item.result_kind for item in invariants} == {ResultKind.NODE_GEOMETRY}
    assert not store.get_invariants(geometry_id="fixture", result_kind=ResultKind.NODE_RELATION)
