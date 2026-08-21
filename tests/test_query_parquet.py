from __future__ import annotations

import pytest

pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")

from hodgecy.core.dataset import ConstructionFamily, DatasetDescriptor
from hodgecy.core.ids import HodgeCYID
from hodgecy.core.status import AcquisitionStatus, RedistributionStatus
from hodgecy.query import Aggregation, MaterializationPolicy, Q, QuerySpec
from hodgecy.storage import DatasetInstance, open_catalog
from hodgecy.storage.errors import MaterializationLimitError


def _make_parquet_fixture(tmp_path):
    raw_dir = tmp_path / "raw" / "ks_fixture"
    raw_dir.mkdir(parents=True)
    path = raw_dir / "polytopes.parquet"
    table = pa.table({
        "source_record_id": ["r1", "r2", "r3"],
        "h11": [1, 2, 2],
        "h12": [3, 2, 1],
        "euler": [-4, 0, 2],
        "vertex_count": [5, 6, 7],
        "facet_count": [8, 9, 10],
        "point_count": [11, 12, 13],
        "dual_point_count": [14, 15, 16],
        "vertices": [[[1, 0], [0, 1]], [[1, 1]], [[2, 0], [0, 2]]],
    })
    pq.write_table(table, path)
    return path


def _catalog_with_fixture(tmp_path):
    _make_parquet_fixture(tmp_path)
    catalog = open_catalog(tmp_path, create=True)
    descriptor = catalog.register_dataset(DatasetDescriptor(
        dataset_id=HodgeCYID.dataset("ks_fixture"),
        name="KS fixture",
        construction_family=ConstructionFamily.known("toric_hypersurface"),
        acquisition_status=AcquisitionStatus.COMPLETE_COLUMNAR,
        redistribution_status=RedistributionStatus.REDISTRIBUTABLE,
        expected_count=3,
        verified_count=3,
    ))
    catalog.register_instance(DatasetInstance(
        instance_id="ks_fixture_v1",
        dataset_id=descriptor.dataset_id,
        source_version="fixture-v1",
        acquisition_status=AcquisitionStatus.COMPLETE_COLUMNAR,
        redistribution_status=RedistributionStatus.REDISTRIBUTABLE,
        record_count=3,
    ))
    catalog.register_parquet_source(
        columnar_id="ks_fixture_columnar",
        instance_id="ks_fixture_v1",
        source_id="ks_fixture_parquet",
        relative_path="raw/ks_fixture/polytopes.parquet",
        table_name="ks_polytopes_fixture",
        common_field_mapping={"h^(1,1)": "h11", "h^(2,1)": "h12"},
        heavy_columns=("vertices",),
        query_safe_columns=("source_record_id", "h11", "h12", "euler", "vertex_count", "facet_count", "point_count", "dual_point_count"),
    )
    return catalog


def test_parquet_registration_query_projection_and_count(tmp_path) -> None:
    catalog = _catalog_with_fixture(tmp_path)
    columnar = catalog.list_columnar_sources()[0]
    assert columnar.row_count == 3
    assert "vertices" in columnar.heavy_columns

    result = catalog.query(Q.dataset("ks_fixture").where(Q.hodge(1, 1) == 2).select("source_record_id", "h11", "euler"))
    assert result.estimated_count() == 3
    assert result.count() == 2
    assert result.head(1).num_rows == 1
    batches = list(result.iter_batches(batch_size=1))
    assert sum(batch.num_rows for batch in batches) == 2
    assert "vertices" not in result.projected_fields


def test_materialization_limit_refuses_large_collect(tmp_path) -> None:
    catalog = _catalog_with_fixture(tmp_path)
    spec = QuerySpec(datasets=("ks_fixture",), fields=("h11",), materialization_policy=MaterializationPolicy(row_limit=1))
    result = catalog.query(spec)
    with pytest.raises(MaterializationLimitError):
        result.to_pandas()
    assert len(result.to_pandas(allow_over_limit=True)) == 3
    with pytest.raises(MaterializationLimitError):
        list(result)


def test_hodge_projection_and_heavy_column_opt_in(tmp_path) -> None:
    catalog = _catalog_with_fixture(tmp_path)
    result = catalog.query(Q.dataset("ks_fixture").where_hodge(h11=1).select("h^(1,1)", "h^(2,1)"))
    table = result.to_arrow()
    assert table.column_names == ["h11", "h12"]
    heavy = catalog.query(QuerySpec(datasets=("ks_fixture",), fields=("vertices",), include_heavy=True))
    assert heavy.head(1).column_names == ["vertices"]


def test_one_to_many_fibration_table_registration(tmp_path) -> None:
    raw_dir = tmp_path / "raw" / "fibrations"
    raw_dir.mkdir(parents=True)
    path = raw_dir / "fibrations.parquet"
    table = pa.table({"parent_id": ["p1", "p1", "p2", "p3"], "fibration_id": ["f1", "f2", "f3", "f4"], "fiber_dim": [1, 2, 1, 1]})
    pq.write_table(table, path)
    catalog = _catalog_with_fixture(tmp_path)
    catalog.register_parquet_source(
        columnar_id="fibration_fixture_columnar",
        instance_id="ks_fixture_v1",
        source_id="fibration_fixture_parquet",
        relative_path="raw/fibrations/fibrations.parquet",
        table_name="fibration_fixture",
        query_safe_columns=("parent_id", "fibration_id", "fiber_dim"),
    )
    result = catalog.query(QuerySpec(table="fibration_fixture", fields=("parent_id", "fibration_id")).where(Q.col("parent_id") == "p1"))
    assert result.count() == 2


def test_limit_order_and_grouped_count_execute(tmp_path) -> None:
    catalog = _catalog_with_fixture(tmp_path)
    ordered = catalog.query(QuerySpec(datasets=("ks_fixture",), fields=("h11", "euler")).order_by("euler", descending=True).limit(2))
    table = ordered.to_arrow()
    assert table.num_rows == 2
    assert table.column("euler").to_pylist() == [2, 0]

    grouped = catalog.query(QuerySpec(datasets=("ks_fixture",)).group_by("h11").aggregate(Aggregation("count")))
    grouped_table = grouped.aggregate()
    assert set(grouped_table.column("h11").to_pylist()) == {1, 2}
