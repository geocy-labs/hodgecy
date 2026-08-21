from __future__ import annotations

from typing import Iterable

from hodgecy.storage import HodgeCYCatalog, TableKind


def register_relationship_parquet_source(
    catalog: HodgeCYCatalog,
    *,
    columnar_id: str,
    instance_id: str,
    source_id: str,
    relative_path: str,
    table_name: str,
    relationship_types: Iterable[str],
    endpoint_datasets: Iterable[str] = (),
    table_kind: TableKind = TableKind.RELATIONSHIP,
):
    return catalog.register_parquet_source(
        columnar_id=columnar_id,
        instance_id=instance_id,
        source_id=source_id,
        relative_path=relative_path,
        table_name=table_name,
        table_kind=table_kind,
        query_safe_columns=("relationship_id", "relationship_type", "source_id", "source_dataset", "target_id", "target_dataset", "evidence_type", "claim_level", "join_state", "directed", "source_record_id"),
        metadata={
            "relationship_types": sorted(set(relationship_types)),
            "endpoint_datasets": sorted(set(endpoint_datasets)),
            "relationship_schema": "relationship.v1",
        },
    )
