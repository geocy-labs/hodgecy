"""Production-corpus context helpers for HodgeCY II infrastructure work."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hodgecy import open_data_root
from hodgecy.config import HodgeCYDataRoot
from hodgecy.storage import HodgeCYCatalog, open_catalog


EXPECTED_V1_COUNTS = {
    "logical_dataset_count": 53,
    "instance_count": 80,
    "physical_source_count": 187,
    "query_table_count": 32,
    "source_data_record_count": 574_616_978,
    "relationship_edge_count": 241_798,
}


@dataclass(frozen=True, slots=True)
class FullCorpusContext:
    """Read-only handle to the production HodgeCY v1 corpus."""

    data_root: HodgeCYDataRoot
    catalog: HodgeCYCatalog
    corpus_metadata: dict[str, Any]
    release_fingerprint: str

    @classmethod
    def open(cls, root: str | Path | None = None, *, catalog_name: str = "current_corpus") -> "FullCorpusContext":
        data_root = open_data_root(root, require_exists=True)
        catalog = open_catalog(data_root, name=catalog_name, read_only=True)
        metadata = _load_corpus_metadata(data_root, catalog)
        return cls(
            data_root=data_root,
            catalog=catalog,
            corpus_metadata=metadata,
            release_fingerprint=_release_fingerprint(data_root, catalog),
        )

    @property
    def logical_dataset_count(self) -> int:
        return len(self.catalog.list_datasets())

    @property
    def instance_count(self) -> int:
        return len(self.catalog.list_instances())

    @property
    def physical_source_count(self) -> int:
        return len(self.catalog.list_physical_sources())

    @property
    def query_table_count(self) -> int:
        return len(self.catalog.list_tables())

    @property
    def relationship_tables(self) -> list[Any]:
        relationship_dataset_ids = {
            "current_corpus_relationships",
            "wave2_source_relationships",
            "wave3_source_relationships",
            "wave4_source_relationships",
        }
        instance_by_id = {instance.instance_id: instance for instance in self.catalog.list_instances()}
        tables = []
        for table in self.catalog.list_tables():
            kind = table.table_kind.value
            instance = instance_by_id.get(table.instance_id or "")
            dataset_id = None if instance is None else instance.dataset_id.local_id
            if kind in {"relationship", "relationships"} or dataset_id in relationship_dataset_ids:
                tables.append(table)
        return tables

    def summary_counts(self) -> dict[str, Any]:
        relationship_edges = sum(int(table.row_count or 0) for table in self.relationship_tables)
        return {
            "logical_dataset_count": self.logical_dataset_count,
            "instance_count": self.instance_count,
            "physical_source_count": self.physical_source_count,
            "query_table_count": self.query_table_count,
            "relationship_edge_count": relationship_edges,
            "source_data_record_count": self.corpus_metadata.get("source_data_record_count")
            or self.corpus_metadata.get("source_data_records_after"),
        }

    def assert_v1_ready(self) -> None:
        counts = self.summary_counts()
        for key in ("logical_dataset_count", "instance_count", "physical_source_count", "query_table_count"):
            expected = EXPECTED_V1_COUNTS[key]
            if counts.get(key) != expected:
                raise RuntimeError(f"Production corpus count mismatch for {key}: expected {expected}, got {counts.get(key)}")


def _load_corpus_metadata(root: HodgeCYDataRoot, catalog: HodgeCYCatalog) -> dict[str, Any]:
    status_path = root.reports / "current_catalog_final_status.json"
    snapshot_path = root.manifests / "current_hodgecy_corpus_snapshot.json"
    metadata: dict[str, Any] = {}
    if snapshot_path.exists():
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        metadata.update(snapshot.get("metadata") or {})
        metadata.update(snapshot.get("wave4_final_counts") or {})
    if status_path.exists():
        status = json.loads(status_path.read_text(encoding="utf-8"))
        metadata.update(status)
    metadata.setdefault("logical_dataset_count", len(catalog.payload.get("datasets", {})))
    metadata.setdefault("instance_count", len(catalog.payload.get("instances", {})))
    metadata.setdefault("physical_source_count", len(catalog.payload.get("physical_sources", {})))
    metadata.setdefault("query_table_count", len(catalog.payload.get("tables", {})))
    wave4 = catalog.payload.get("metadata", {}).get("wave4_permanent_ingest") or {}
    if wave4.get("source_data_records_after") is not None:
        metadata.setdefault("source_data_record_count", wave4["source_data_records_after"])
    return metadata


def _release_fingerprint(root: HodgeCYDataRoot, catalog: HodgeCYCatalog) -> str:
    digest = hashlib.sha256()
    for relative in (
        "manifests/current_hodgecy_corpus_snapshot.json",
        "manifests/datasets.json",
        "catalogs/current_corpus/catalog.json",
    ):
        path = root.root / relative
        if path.exists():
            digest.update(relative.encode("utf-8"))
            digest.update(path.read_bytes())
    digest.update(str(len(catalog.payload.get("datasets", {}))).encode("ascii"))
    digest.update(str(len(catalog.payload.get("instances", {}))).encode("ascii"))
    digest.update(str(len(catalog.payload.get("physical_sources", {}))).encode("ascii"))
    digest.update(str(len(catalog.payload.get("tables", {}))).encode("ascii"))
    return digest.hexdigest()
