from __future__ import annotations

import json
import shutil
from zipfile import ZipFile

import pytest

pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")

from hodgecy.core.dataset import ConstructionFamily, DatasetDescriptor
from hodgecy.core.ids import HodgeCYID
from hodgecy.core.status import AcquisitionStatus, RedistributionStatus
from hodgecy.datasets.cicy4_fibrations import build_cicy4_fibration_archive_index, iter_member_lines, read_cicy4_fibration_archive_index
from hodgecy.datasets.kreuzer_skarke import register_kreuzer_skarke_parquet_source
from hodgecy.query import MaterializationPolicy, Q, QuerySpec
from hodgecy.relationships import RelationshipQueryService, register_relationship_parquet_source
from hodgecy.storage import DatasetInstance, TableKind, build_parquet_metadata_cache, open_catalog, read_parquet_metadata_cache
from hodgecy.storage.errors import MaterializationLimitError, StorageError


def _write_partitioned_ks_fixture(root):
    raw = root / "raw" / "ks_fixture"
    raw.mkdir(parents=True)
    rows = [
        {"vertices": [[1, 0], [0, 1]], "vertex_count": 2, "facet_count": 3, "point_count": 4, "dual_point_count": 5, "h11": 1, "h12": 101, "euler_characteristic": -200},
        {"vertices": [[1, 1]], "vertex_count": 1, "facet_count": 4, "point_count": 6, "dual_point_count": 7, "h11": 2, "h12": 90, "euler_characteristic": -176},
        {"vertices": [[2, 0], [0, 2]], "vertex_count": 2, "facet_count": 5, "point_count": 8, "dual_point_count": 9, "h11": 1, "h12": 101, "euler_characteristic": -200},
        {"vertices": [[3, 0]], "vertex_count": 1, "facet_count": 6, "point_count": 10, "dual_point_count": 11, "h11": 3, "h12": 75, "euler_characteristic": -144},
        {"vertices": [[4, 0], [0, 4]], "vertex_count": 2, "facet_count": 7, "point_count": 12, "dual_point_count": 13, "h11": 4, "h12": 60, "euler_characteristic": -112},
    ]
    paths = []
    for index, chunk in enumerate((rows[:3], rows[3:])):
        path = raw / f"part-{index}.parquet"
        pq.write_table(pa.Table.from_pylist(chunk), path, row_group_size=2)
        paths.append(f"raw/ks_fixture/part-{index}.parquet")
    return tuple(paths)


def _catalog_with_blob11_ks(root):
    relative_paths = _write_partitioned_ks_fixture(root)
    catalog = open_catalog(root, create=True)
    register_kreuzer_skarke_parquet_source(catalog, relative_paths=relative_paths)
    return catalog, relative_paths


def test_ks_default_projection_excludes_vertices_and_plan_tracks_pushdown(tmp_path) -> None:
    catalog, _ = _catalog_with_blob11_ks(tmp_path)
    result = catalog.query(
        QuerySpec(datasets=("kreuzer_skarke",), fields=("h11", "h12", "euler_characteristic"))
        .where(Q.col("h11") == 1)
    )

    plan = result.explain()
    assert plan["projected_columns"] == ["h11", "h12", "euler_characteristic"]
    assert plan["heavy_columns_requested"] is False
    assert plan["predicate_pushdown"] is True
    assert plan["partition_count"] == 2
    assert plan["row_group_count"] == 3
    assert "vertices" not in result.schema()

    batches = list(result.iter_batches(batch_size=1))
    assert len(batches) >= 2
    assert all(batch.num_rows <= 1 for batch in batches)
    assert all("vertices" not in batch.schema.names for batch in batches)
    assert sum(batch.num_rows for batch in batches) == 2


def test_ks_heavy_materialization_requires_explicit_opt_in_and_limit(tmp_path) -> None:
    catalog, _ = _catalog_with_blob11_ks(tmp_path)
    with pytest.raises(Exception):
        catalog.query(QuerySpec(datasets=("kreuzer_skarke",), fields=("vertices",)))

    heavy = catalog.query(QuerySpec(
        datasets=("kreuzer_skarke",),
        fields=("vertices",),
        include_heavy=True,
        materialization_policy=MaterializationPolicy(row_limit=10, heavy_row_limit=1),
    ))
    assert heavy.head(1).column_names == ["vertices"]
    with pytest.raises(MaterializationLimitError):
        heavy.take(2)
    assert heavy.take(2, allow_over_limit=True).num_rows == 2
    assert heavy.explain()["heavy_columns_requested"] is True


def test_parquet_metadata_cache_invalidates_on_revision_change(tmp_path) -> None:
    _, relative_paths = _catalog_with_blob11_ks(tmp_path)
    paths = [tmp_path / path for path in relative_paths]
    cache_path = tmp_path / "cache" / "ks_metadata.json"
    payload = build_parquet_metadata_cache(paths, cache_path, data_root=tmp_path, source_revision="fixture-a", source_checksum="sha-a")
    assert payload["inspection"]["file_count"] == 2
    assert read_parquet_metadata_cache(cache_path, paths, source_revision="fixture-a", source_checksum="sha-a")["schema_version"].endswith("v1")
    with pytest.raises(StorageError):
        read_parquet_metadata_cache(cache_path, paths, source_revision="fixture-b", source_checksum="sha-a")


def test_data_root_move_preserves_relative_source_resolution(tmp_path) -> None:
    root1 = tmp_path / "root1"
    root2 = tmp_path / "root2"
    catalog, _ = _catalog_with_blob11_ks(root1)
    assert catalog.query(QuerySpec(datasets=("kreuzer_skarke",), fields=("h11",)).where(Q.col("h12") == 101)).count() == 2
    shutil.copytree(root1, root2)
    moved = open_catalog(root2, read_only=True)
    moved_result = moved.query(QuerySpec(datasets=("kreuzer_skarke",), fields=("h11",)).where(Q.col("h12") == 101))
    assert moved_result.count() == 2
    assert all("root1" not in path for path in moved_result.provenance["source_relative_paths"])


def test_cicy4_fibration_archive_index_locates_and_streams_selected_member(tmp_path) -> None:
    archive_path = tmp_path / "raw" / "cicy4_fibrations.zip"
    archive_path.parent.mkdir(parents=True)
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("fib_1_3.jsonl", "\n".join(json.dumps({"parent_id": item, "fibration_id": f"f{item}"}) for item in (1, 2, 3)))
        archive.writestr("fib_4_5.jsonl", "\n".join(json.dumps({"parent_id": item, "fibration_id": f"f{item}"}) for item in (4, 5)))
    index = build_cicy4_fibration_archive_index(
        archive_path,
        archive_relative_path="raw/cicy4_fibrations.zip",
        source_revision="fixture-rev",
        scan_text_members=False,
    )
    assert [member.member_name for member in index.locate_parent(2)] == ["fib_1_3.jsonl"]
    assert index.locator_for_parent(5)[0].archive_relative_path == "raw/cicy4_fibrations.zip"
    assert len(list(iter_member_lines(archive_path, "fib_4_5.jsonl"))) == 2
    cache = tmp_path / "indexes" / "cicy4_fibrations.json"
    index.write(cache)
    assert read_cicy4_fibration_archive_index(cache).locate_parent(4)[0].member_name == "fib_4_5.jsonl"


def test_relationship_counts_remain_backend_filtered(tmp_path) -> None:
    raw = tmp_path / "raw" / "relationships"
    raw.mkdir(parents=True)
    path = raw / "relationships.parquet"
    pq.write_table(pa.table({
        "relationship_id": ["r1", "r2", "r3"],
        "relationship_type": ["fibration_of", "fibration_of", "mirror_of"],
        "source_id": ["p1", "p1", "p2"],
        "source_dataset": ["cicy4", "cicy4", "cicy4"],
        "target_id": ["f1", "f2", "m2"],
        "target_dataset": ["fib", "fib", "mirror"],
        "evidence_type": ["source", "source", "source"],
        "claim_level": ["source_reported", "source_reported", "candidate"],
        "join_state": ["matched", "matched", "matched"],
        "directed": [True, True, False],
        "source_record_id": ["p1", "p1", "p2"],
    }), path)
    catalog = open_catalog(tmp_path, create=True)
    descriptor = catalog.register_dataset(DatasetDescriptor(
        dataset_id=HodgeCYID.dataset("relationship_scale_fixture"),
        name="Relationship scale fixture",
        construction_family=ConstructionFamily.known("cicy"),
        acquisition_status=AcquisitionStatus.COMPLETE_COLUMNAR,
        redistribution_status=RedistributionStatus.REDISTRIBUTABLE,
    ))
    catalog.register_instance(DatasetInstance(
        instance_id="relationship_scale_fixture_v1",
        dataset_id=descriptor.dataset_id,
        source_version="fixture-v1",
        acquisition_status=AcquisitionStatus.COMPLETE_COLUMNAR,
        redistribution_status=RedistributionStatus.REDISTRIBUTABLE,
        record_count=3,
    ))
    register_relationship_parquet_source(
        catalog,
        columnar_id="relationship_scale_columnar",
        instance_id="relationship_scale_fixture_v1",
        source_id="relationship_scale_parquet",
        relative_path="raw/relationships/relationships.parquet",
        table_name="relationship_scale",
        relationship_types=("fibration_of", "mirror_of"),
    )
    service = RelationshipQueryService(catalog, table="relationship_scale")
    counts = service.parent_child_counts(relationship_type="fibration_of")
    assert counts.column("source_id").to_pylist() == ["p1"]
    assert service.bounded_frontier("p1", relationship_type="fibration_of", row_limit=2).count() == 2
