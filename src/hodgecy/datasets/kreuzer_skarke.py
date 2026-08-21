from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from hodgecy.core.dataset import ConstructionFamily, DatasetDescriptor
from hodgecy.core.ids import HodgeCYID
from hodgecy.core.status import AcquisitionStatus, RedistributionStatus
from hodgecy.query import MaterializationPolicy, Q, QuerySpec
from hodgecy.query.fields import FieldMetadata, FieldWeight
from hodgecy.storage import DatasetInstance, HodgeCYCatalog, TableKind

ADAPTER_VERSION = "1.1.0"
KS_PARQUET_SOURCE_REVISION = "60c0e119a03608418df538191f65da3f43b5b819"
KS_EXPECTED_ROW_COUNT = 473_800_776
KS_EXPECTED_FILE_COUNT = 30
KS_EXPECTED_BYTE_SIZE = 15_773_290_651
KS_TABLE_NAME = "kreuzer_skarke"
KS_DATASET_ID = "kreuzer_skarke"
KS_INSTANCE_ID = "kreuzer_skarke_parquet_60c0e119"
KS_SCALAR_COLUMNS = (
    "vertex_count",
    "facet_count",
    "point_count",
    "dual_point_count",
    "h11",
    "h12",
    "euler_characteristic",
)
KS_HEAVY_COLUMNS = ("vertices",)
KS_COLUMNS = KS_HEAVY_COLUMNS + KS_SCALAR_COLUMNS
KS_COMMON_FIELD_MAPPING = {"h^(1,1)": "h11", "h^(1,2)": "h12", "h^(2,1)": "h12", "euler": "euler_characteristic"}


@dataclass(frozen=True, slots=True)
class KreuzerSkarkeRowReference:
    relative_path: str
    row_group: int | None = None
    row_offset: int | None = None
    source_revision: str = KS_PARQUET_SOURCE_REVISION

    def to_dict(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "row_group": self.row_group,
            "row_offset": self.row_offset,
            "source_revision": self.source_revision,
            "reference_kind": "parquet_row_locator",
        }


def kreuzer_skarke_descriptor() -> DatasetDescriptor:
    return DatasetDescriptor(
        dataset_id=HodgeCYID.dataset(KS_DATASET_ID),
        name="Kreuzer-Skarke reflexive 4-polytopes",
        construction_family=ConstructionFamily.known("toric_hypersurface"),
        acquisition_status=AcquisitionStatus.COMPLETE_COLUMNAR,
        redistribution_status=RedistributionStatus.ACQUIRED_LOCALLY_BY_USER,
        source_version=KS_PARQUET_SOURCE_REVISION,
        record_semantics="columnar polytope source presentation",
        identifier_definition="distribution locator; not a stable geometry identity",
        expected_count=KS_EXPECTED_ROW_COUNT,
        adapter_capabilities=("columnar", "streaming"),
        metadata={
            "row_count": KS_EXPECTED_ROW_COUNT,
            "parquet_files": KS_EXPECTED_FILE_COUNT,
            "bytes": KS_EXPECTED_BYTE_SIZE,
            "heavy_columns": list(KS_HEAVY_COLUMNS),
        },
    )


def ks_field_metadata() -> dict[str, dict[str, Any]]:
    return {
        "vertices": FieldMetadata(
            "vertices",
            weight=FieldWeight.NESTED,
            indexable=False,
            projection_safe=False,
            materialization_only=True,
            description="Nested vertex payload; load only for explicit selected materialization.",
        ).to_dict(),
        "vertex_count": FieldMetadata("vertex_count", indexable=True, projection_safe=True).to_dict(),
        "facet_count": FieldMetadata("facet_count", indexable=True, projection_safe=True).to_dict(),
        "point_count": FieldMetadata("point_count", indexable=True, projection_safe=True).to_dict(),
        "dual_point_count": FieldMetadata("dual_point_count", indexable=True, projection_safe=True).to_dict(),
        "h11": FieldMetadata("h11", indexable=True, projection_safe=True).to_dict(),
        "h12": FieldMetadata("h12", indexable=True, projection_safe=True).to_dict(),
        "euler_characteristic": FieldMetadata("euler_characteristic", indexable=True, projection_safe=True).to_dict(),
    }


def default_ks_projection() -> tuple[str, ...]:
    return KS_SCALAR_COLUMNS


def ks_query(*, include_vertices: bool = False, row_limit: int = 100_000) -> QuerySpec:
    fields = KS_COLUMNS if include_vertices else KS_SCALAR_COLUMNS
    return QuerySpec(
        datasets=(KS_DATASET_ID,),
        fields=fields,
        include_heavy=include_vertices,
        materialization_policy=MaterializationPolicy(row_limit=row_limit, heavy_row_limit=1),
    )


def register_kreuzer_skarke_parquet_source(
    catalog: HodgeCYCatalog,
    *,
    relative_paths: Iterable[str],
    instance_id: str = KS_INSTANCE_ID,
    table_name: str = KS_TABLE_NAME,
    source_revision: str = KS_PARQUET_SOURCE_REVISION,
):
    descriptor = catalog.register_dataset(kreuzer_skarke_descriptor())
    catalog.register_instance(DatasetInstance(
        instance_id=instance_id,
        dataset_id=descriptor.dataset_id,
        source_version=source_revision,
        source_revision=source_revision,
        acquisition_status=AcquisitionStatus.COMPLETE_COLUMNAR,
        redistribution_status=RedistributionStatus.ACQUIRED_LOCALLY_BY_USER,
        record_count=KS_EXPECTED_ROW_COUNT,
        adapter_name="kreuzer_skarke_parquet",
        metadata={"expected_file_count": KS_EXPECTED_FILE_COUNT, "adapter_version": ADAPTER_VERSION},
    ))
    rels = tuple(relative_paths)
    return catalog.register_parquet_sources(
        columnar_id="kreuzer_skarke_parquet",
        instance_id=instance_id,
        source_ids=tuple(f"ks_parquet_{index:03d}" for index, _ in enumerate(rels)),
        relative_paths=rels,
        table_name=table_name,
        common_field_mapping=KS_COMMON_FIELD_MAPPING,
        heavy_columns=KS_HEAVY_COLUMNS,
        query_safe_columns=KS_SCALAR_COLUMNS,
        table_kind=TableKind.SOURCE,
        source_revision=source_revision,
        field_metadata=ks_field_metadata(),
        metadata={
            "dataset_profile": "kreuzer_skarke_4d_parquet",
            "source_revision": source_revision,
            "column_weight_bytes": {"vertices": 50, **{column: 1 for column in KS_SCALAR_COLUMNS}},
        },
    )


def hodge_pair_filter(h11: int | None = None, h12: int | None = None) -> QuerySpec:
    spec = ks_query()
    if h11 is not None:
        spec = spec.where(Q.col("h11") == h11)
    if h12 is not None:
        spec = spec.where(Q.col("h12") == h12)
    return spec
