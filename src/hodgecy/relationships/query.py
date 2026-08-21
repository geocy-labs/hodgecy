from __future__ import annotations

from typing import Any

from hodgecy.query import Aggregation, MaterializationPolicy, Q, QuerySpec


class RelationshipQueryService:
    def __init__(self, catalog: Any, *, table: str) -> None:
        self.catalog = catalog
        self.table = table

    def relations_from(self, source_id: str, *, relationship_type: str | None = None) -> Any:
        spec = QuerySpec(table=self.table).where(Q.col("source_id") == source_id)
        if relationship_type is not None:
            spec = spec.where(Q.col("relationship_type") == relationship_type)
        return self.catalog.query(spec)

    def relations_to(self, target_id: str, *, relationship_type: str | None = None) -> Any:
        spec = QuerySpec(table=self.table).where(Q.col("target_id") == target_id)
        if relationship_type is not None:
            spec = spec.where(Q.col("relationship_type") == relationship_type)
        return self.catalog.query(spec)

    def by_type(self, relationship_type: str, *, fields: tuple[str, ...] = ()) -> Any:
        spec = QuerySpec(table=self.table, fields=fields).where(Q.col("relationship_type") == relationship_type)
        return self.catalog.query(spec)

    def has_relation(self, source_id: str, *, relationship_type: str | None = None) -> bool:
        return self.relations_from(source_id, relationship_type=relationship_type).count() > 0

    def relation_count(self, source_id: str, *, relationship_type: str | None = None) -> int:
        return self.relations_from(source_id, relationship_type=relationship_type).count()

    def related_records(self, source_id: str, *, relationship_type: str | None = None) -> Any:
        spec = QuerySpec(table=self.table).where(Q.col("source_id") == source_id).select("target_id", "target_dataset", "relationship_type")
        if relationship_type is not None:
            spec = spec.where(Q.col("relationship_type") == relationship_type)
        return self.catalog.query(spec)

    def parent_child_counts(self, *, parent_field: str = "source_id", relationship_type: str | None = None) -> Any:
        spec = QuerySpec(table=self.table).group_by(parent_field).aggregate(Aggregation("count"))
        if relationship_type is not None:
            spec = spec.where(Q.col("relationship_type") == relationship_type)
        return self.catalog.query(spec).aggregate()

    def bounded_frontier(self, source_id: str, *, relationship_type: str | None = None, depth: int = 1, row_limit: int = 10_000) -> Any:
        if depth != 1:
            from hodgecy.storage.errors import MaterializationLimitError
            raise MaterializationLimitError("Relationship traversal currently requires explicit single-depth batches")
        spec = QuerySpec(
            table=self.table,
            fields=("source_id", "target_id", "target_dataset", "relationship_type"),
            materialization_policy=MaterializationPolicy(row_limit=row_limit),
        ).where(Q.col("source_id") == source_id)
        if relationship_type is not None:
            spec = spec.where(Q.col("relationship_type") == relationship_type)
        return self.catalog.query(spec)
