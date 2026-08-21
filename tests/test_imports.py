from __future__ import annotations


def test_package_imports() -> None:
    import hodgecy

    assert hodgecy.__version__ == "0.2.0"


def test_legacy_package_imports_remain_available() -> None:
    import hodgecy.arrangements
    import hodgecy.equivariant
    import hodgecy.smoothing
    import hodgecy.profiles
    import hodgecy.operators
    import hodgecy.reporting

    assert hodgecy.arrangements is not None
    assert hodgecy.equivariant is not None
    assert hodgecy.smoothing is not None
    assert hodgecy.profiles is not None
    assert hodgecy.operators is not None
    assert hodgecy.reporting is not None


def test_blob5_parser_adapter_imports() -> None:
    import hodgecy.datasets
    import hodgecy.parsers

    assert hodgecy.parsers.JsonlParser is not None
    assert hodgecy.datasets.FixtureDatasetAdapter is not None


def test_blob8_exact_algebra_imports() -> None:
    import hodgecy.algebra
    import hodgecy.assemblies
    import hodgecy.math

    assert hodgecy.algebra.ExactAlgebraOperation.RANK_Q.value == "rank_Q"
    assert hodgecy.assemblies.GluingComplexAssembly is not None
    assert hodgecy.math.BasisArray is not None

def test_blob7_relationship_and_geometry_imports() -> None:
    import hodgecy.geometry
    import hodgecy.relationships

    assert hodgecy.relationships.RelationshipType.FIBRATION_OF.value == "fibration_of"
    assert hodgecy.geometry.FibrationPayload is not None


def test_blob6_construction_adapter_imports() -> None:
    from hodgecy.datasets import (
        cicy3_adapter,
        cicy4_adapter,
        double_octic_adapter,
        ip_weight_adapter,
        picard_fuchs_adapter,
        weighted_p4_adapter,
    )

    assert cicy3_adapter is not None
    assert cicy4_adapter is not None
    assert weighted_p4_adapter is not None
    assert ip_weight_adapter is not None
    assert picard_fuchs_adapter is not None
    assert double_octic_adapter is not None
