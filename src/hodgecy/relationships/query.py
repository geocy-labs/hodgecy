from __future__ import annotations

from typing import Any

from hodgecy.query import Q, QuerySpec


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

    def has_relation(self, source_id: str, *, relationship_type: str | None = None) -> bool:
        return self.relations_from(source_id, relationship_type=relationship_type).count() > 0

    def relation_count(self, source_id: str, *, relationship_type: str | None = None) -> int:
        return self.relations_from(source_id, relationship_type=relationship_type).count()

    def related_records(self, source_id: str, *, relationship_type: str | None = None) -> Any:
        spec = QuerySpec(table=self.table).where(Q.col("source_id") == source_id).select("target_id", "target_dataset", "relationship_type")
        if relationship_type is not None:
            spec = spec.where(Q.col("relationship_type") == relationship_type)
        return self.catalog.query(spec)
