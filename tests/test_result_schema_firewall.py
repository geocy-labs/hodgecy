from __future__ import annotations

import json

import pytest

from hodgecy.core import (
    BaseSpectrum,
    ComparisonState,
    ConifoldAtomSpectrum,
    EvidenceStatus,
    MathematicalPromotionError,
    NodeGeometryResult,
    NodeRelationResult,
    ResultKind,
    ResultMetadata,
    ResultValue,
    SmoothHodgeAtomSpectrum,
    SourceAssemblyResult,
    SourceAssemblySpectrum,
    ValidationError,
    canonical_json,
    promote_source_to_conifold_atom,
    promote_source_to_node_relation,
    promote_source_to_smooth_hodge_atom,
)


def source_result(geometry_id: str = "geometry-A") -> SourceAssemblyResult:
    return SourceAssemblyResult(
        metadata=ResultMetadata(
            geometry_id=geometry_id,
            result_kind=ResultKind.SOURCE_ASSEMBLY,
            evidence_status=EvidenceStatus.COMPUTED,
            method="synthetic source-complex rank computation",
            notes="source-level fixture only",
        ),
        values={
            "rank": ResultValue(
                value=7,
                status=EvidenceStatus.COMPUTED,
                method="rank over Q",
                provenance="unit-test fixture",
            )
        },
        payload={"matrix_shape": [28, 7]},
    )


def test_result_kinds_remain_distinct() -> None:
    source = source_result()
    node_geometry = NodeGeometryResult(ResultMetadata("geometry-A", ResultKind.NODE_GEOMETRY))
    node_relation = NodeRelationResult(ResultMetadata("geometry-A", ResultKind.NODE_RELATION))
    conifold = ConifoldAtomSpectrum(ResultMetadata("geometry-A", ResultKind.CONIFOLD_ATOM))
    smooth = SmoothHodgeAtomSpectrum(ResultMetadata("geometry-A", ResultKind.SMOOTH_HODGE_ATOM))

    assert source.kind is ResultKind.SOURCE_ASSEMBLY
    assert node_geometry.kind is ResultKind.NODE_GEOMETRY
    assert node_relation.kind is ResultKind.NODE_RELATION
    assert conifold.kind is ResultKind.CONIFOLD_ATOM
    assert smooth.kind is ResultKind.SMOOTH_HODGE_ATOM
    assert len({item.kind for item in (source, node_geometry, node_relation, conifold, smooth)}) == 5


def test_spectrum_types_are_not_interchangeable() -> None:
    source_spectrum = SourceAssemblySpectrum(ResultMetadata("geometry-A", ResultKind.SOURCE_ASSEMBLY))
    conifold = ConifoldAtomSpectrum(ResultMetadata("geometry-A", ResultKind.CONIFOLD_ATOM))
    smooth = SmoothHodgeAtomSpectrum(ResultMetadata("geometry-A", ResultKind.SMOOTH_HODGE_ATOM))

    assert isinstance(source_spectrum, BaseSpectrum)
    assert isinstance(conifold, BaseSpectrum)
    assert isinstance(smooth, BaseSpectrum)
    assert type(source_spectrum) is not type(conifold)
    assert type(conifold) is not type(smooth)
    assert source_spectrum.kind is not conifold.kind
    assert conifold.kind is not smooth.kind


def test_wrong_kind_for_result_class_is_rejected() -> None:
    with pytest.raises(ValidationError):
        NodeRelationResult(ResultMetadata("geometry-A", ResultKind.SOURCE_ASSEMBLY))


def test_all_evidence_states_are_serialized() -> None:
    assert {status.value for status in EvidenceStatus} == {
        "computed",
        "verified",
        "imported",
        "assumed",
        "conjectural",
        "unknown",
        "not_applicable",
    }
    for status in EvidenceStatus:
        value = ResultValue(value=None, status=status, notes=f"{status.value} fixture")
        assert ResultValue.from_dict(value.to_dict()) == value


def test_unknown_value_keeps_explanatory_metadata() -> None:
    value = ResultValue(
        value=None,
        status=EvidenceStatus.UNKNOWN,
        method=None,
        provenance="future Blob 2 registry slot",
        notes="node relation SNF has not been computed",
    )
    payload = value.to_dict()
    assert payload["value"] is None
    assert payload["status"] == "unknown"
    assert payload["notes"] == "node relation SNF has not been computed"


def test_source_data_cannot_promote_to_stronger_levels_without_certification() -> None:
    source = source_result()
    with pytest.raises(MathematicalPromotionError, match="node_relation"):
        promote_source_to_node_relation(source)
    with pytest.raises(MathematicalPromotionError, match="conifold_atom"):
        promote_source_to_conifold_atom(source)
    with pytest.raises(MathematicalPromotionError, match="smooth_hodge_atom"):
        promote_source_to_smooth_hodge_atom(source)


def test_non_verified_certification_does_not_promote() -> None:
    source = source_result()
    computed_only = ResultValue(
        value={"comparison_map_rank": 7},
        status=EvidenceStatus.COMPUTED,
        method="source-level calculation",
        notes="not a certified source-to-node theorem",
    )
    with pytest.raises(MathematicalPromotionError):
        promote_source_to_node_relation(source, certification=computed_only)


def test_verified_certification_is_explicit_when_future_code_supplies_it() -> None:
    source = source_result()
    certification = ResultValue(
        value={"comparison_morphism": "synthetic theorem-backed fixture"},
        status=EvidenceStatus.VERIFIED,
        method="independent source-to-node certificate",
        provenance="unit-test fixture",
        notes="demonstrates explicit API, not current production mathematics",
    )
    promoted = promote_source_to_node_relation(source, certification=certification)

    assert promoted.kind is ResultKind.NODE_RELATION
    assert promoted.metadata.evidence_status is EvidenceStatus.VERIFIED
    assert promoted.payload["certification"]["status"] == "verified"


def test_result_serialization_round_trip_is_json_compatible() -> None:
    source = source_result("geometry-B")
    payload = source.to_dict()
    encoded = canonical_json(payload)
    decoded = json.loads(encoded)
    restored = SourceAssemblyResult.from_dict(decoded)

    assert restored == source
    assert restored.kind is ResultKind.SOURCE_ASSEMBLY
    assert restored.metadata.geometry_id == "geometry-B"


def test_comparison_state_has_unknown_and_incomparable() -> None:
    assert ComparisonState.UNKNOWN.value == "unknown"
    assert ComparisonState.INCOMPARABLE.value == "incomparable"
    assert ComparisonState.UNKNOWN is not ComparisonState.DIFFERENT
