from __future__ import annotations

import pytest

from hodgecy.core.errors import ValidationError
from hodgecy.query import Aggregation, FieldRegistry, MaterializationPolicy, Q, QuerySpec, hodge_field


def test_predicate_sql_is_parameterized_and_validated() -> None:
    registry = FieldRegistry.from_schema(["h11", "h12", "euler"])
    predicate = (Q.hodge(1, 1) == 40) & (Q.col("euler") >= 0) & Q.col("h12").in_([0, 1])
    sql, params = predicate.compile_sql(registry)
    assert "?" in sql
    assert params == [40, 0, 0, 1]
    with pytest.raises(ValidationError):
        Q.col("h11; drop table datasets") == 1


def test_query_spec_serialization_and_stable_id() -> None:
    spec = (
        Q.dataset("ks_fixture")
        .where(Q.hodge(1, 1).between(1, 3) | ~Q.col("euler").is_null())
        .select(hodge_field(1, 1), "euler")
        .order_by("euler", descending=True)
        .group_by(hodge_field(1, 1))
        .aggregate(Aggregation("count", alias="n"))
    )
    restored = QuerySpec.from_dict(spec.to_dict())
    assert restored.to_dict() == spec.to_dict()
    assert restored.stable_id() == spec.stable_id()


def test_field_registry_hodge_projection_and_heavy_guard() -> None:
    registry = FieldRegistry.from_schema(["h11", "h12", "vertices"], heavy_fields=["vertices"])
    assert registry.resolve(hodge_field(1, 1)) == "h11"
    assert registry.resolve(hodge_field(2, 1)) == "h12"
    with pytest.raises(ValidationError):
        registry.projection(["vertices"])
    assert registry.projection(["vertices"], include_heavy=True) == ["vertices"]


def test_materialization_policy_roundtrip() -> None:
    policy = MaterializationPolicy(row_limit=2, allow_over_limit=True)
    assert MaterializationPolicy.from_dict(policy.to_dict()) == policy
