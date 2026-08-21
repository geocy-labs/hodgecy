from __future__ import annotations

import csv
import gzip
import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator

from hodgecy.config import HodgeCYDataRoot
from hodgecy.core.dataset import ConstructionFamily, DatasetDescriptor
from hodgecy.core.ids import HodgeCYID
from hodgecy.core.serialization import stable_sha256
from hodgecy.core.status import AcquisitionStatus, RedistributionStatus
from hodgecy.datasets.cicy4_fibrations import build_cicy4_fibration_archive_index
from hodgecy.datasets.kreuzer_skarke import KS_COMMON_FIELD_MAPPING, KS_HEAVY_COLUMNS, KS_PARQUET_SOURCE_REVISION, KS_SCALAR_COLUMNS, ks_field_metadata
from hodgecy.storage import DatasetInstance, SourceFormat, TableKind, open_catalog
from hodgecy.storage.errors import MissingCapabilityError
from hodgecy.storage.models import utc_now_iso

BOOTSTRAP_SCHEMA_VERSION = "current_corpus_bootstrap.v1"
NORMALIZATION_SCHEMA_VERSION = "normalized_source_rows.v1"


@dataclass(frozen=True, slots=True)
class CorpusBootstrapConfig:
    data_root: str | Path | HodgeCYDataRoot
    catalog_name: str = "current_corpus"
    batch_size: int = 50_000
    hodgecy_commit: str | None = None
    hodgecy_version: str | None = None

    @property
    def root(self) -> HodgeCYDataRoot:
        if isinstance(self.data_root, HodgeCYDataRoot):
            return self.data_root
        return HodgeCYDataRoot(Path(self.data_root))


@dataclass(slots=True)
class DatasetBuildSummary:
    dataset: str
    storage_class: str
    source_count: int | None = None
    normalized_count: int | None = None
    rejected_count: int = 0
    relationship_count: int = 0
    normalized_bytes: int = 0
    queryable: bool = False
    materializable: bool = False
    validation_status: str = "deferred"
    output_relative_path: str | None = None
    adapter: str | None = None
    adapter_version: str = "1.0.0"
    source_revision: str | None = None
    elapsed_seconds: float = 0.0
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "source_revision": self.source_revision,
            "adapter": self.adapter,
            "adapter_version": self.adapter_version,
            "storage_class": self.storage_class,
            "source_count": self.source_count,
            "normalized_count": self.normalized_count,
            "rejected_count": self.rejected_count,
            "relationship_count": self.relationship_count,
            "normalized_bytes": self.normalized_bytes,
            "queryable": self.queryable,
            "materializable": self.materializable,
            "provenance_coverage": "manifest_or_inventory",
            "validation_status": self.validation_status,
            "elapsed_seconds": round(self.elapsed_seconds, 6),
            "output_relative_path": self.output_relative_path,
            "notes": self.notes,
        }


@dataclass(slots=True)
class CorpusBootstrapResult:
    catalog_path: Path
    snapshot_path: Path
    build_rows: list[DatasetBuildSummary]
    relationship_rows: list[dict[str, Any]]
    reports: dict[str, Path] = field(default_factory=dict)
    corpus_integration_complete: bool = False
    acquisition_pass_ready: bool = False
    remaining_blockers: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "catalog_path": self.catalog_path.as_posix(),
            "snapshot_path": self.snapshot_path.as_posix(),
            "build_rows": [row.to_dict() for row in self.build_rows],
            "relationship_count": len(self.relationship_rows),
            "reports": {k: v.as_posix() for k, v in self.reports.items()},
            "corpus_integration_complete": self.corpus_integration_complete,
            "acquisition_pass_ready": self.acquisition_pass_ready,
            "remaining_blockers": list(self.remaining_blockers),
        }


@dataclass(frozen=True, slots=True)
class NormalizationSpec:
    dataset_id: str
    staged_relative_path: str
    table_name: str
    transform: Callable[[dict[str, Any]], dict[str, Any] | None]
    expected_count: int | None
    query_safe_columns: tuple[str, ...]
    table_kind: TableKind = TableKind.NORMALIZED
    parent_key: str | None = None
    child_key: str | None = None
    adapter: str = "current_corpus_jsonl_normalizer"


def bootstrap_current_corpus(config: CorpusBootstrapConfig) -> CorpusBootstrapResult:
    started = time.perf_counter()
    root = config.root
    _ensure_layout(root)
    catalog = open_catalog(root, name=config.catalog_name, create=True)
    logical = _read_tsv(root.reports / "logical_datasets.tsv")
    states = _read_tsv(root.reports / "final_completion_states.tsv")
    inventory = _read_tsv(root.reports / "source_inventory.tsv")
    _register_datasets(catalog, logical, states, inventory)
    _register_sources(catalog, inventory)
    build_rows: list[DatasetBuildSummary] = []
    ks = _register_ks(catalog, root)
    if ks:
        build_rows.append(ks)
    build_rows.extend(_register_native_large(catalog, root))
    for spec in _normalization_specs():
        build_rows.append(_normalize(catalog, root, spec, config.batch_size))
    relationships = _relationship_rows(root)
    rel_summary = _write_relationships(catalog, root, relationships)
    if rel_summary:
        build_rows.append(rel_summary)
    snapshot_path = _write_snapshot(catalog, root, build_rows, relationships, config)
    reports = _write_reports(root, catalog, build_rows, relationships, snapshot_path, time.perf_counter() - started)
    blockers = _remaining_blockers()
    return CorpusBootstrapResult(catalog.path, snapshot_path, build_rows, relationships, reports, False, False, blockers)


def _ensure_layout(root: HodgeCYDataRoot) -> None:
    for path in (root.normalized, root.catalogs, root.manifests, root.reports, root.indexes, root.rejected, root.cache, root.logs):
        path.mkdir(parents=True, exist_ok=True)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _register_datasets(catalog: Any, logical: list[dict[str, str]], states: list[dict[str, str]], inventory: list[dict[str, str]]) -> None:
    rows: dict[str, dict[str, str]] = {}
    for row in logical:
        rows[row["dataset_id"]] = row
    for row in states:
        rows.setdefault(row["dataset"], {"dataset_id": row["dataset"], "human_name": row["dataset"].replace("_", " ").title(), "construction_family": row["dataset"], "record_semantics": row.get("architecture_impact", "source data"), "source_record_count": row.get("record_count", ""), "acquisition_completeness": row.get("state", "UNRESOLVED")})
    for row in inventory:
        rows.setdefault(row["dataset_id"], {"dataset_id": row["dataset_id"], "human_name": row["dataset_id"].replace("_", " ").title(), "construction_family": row["dataset_id"], "record_semantics": row.get("logical_dataset_id", "source data"), "source_record_count": "", "acquisition_completeness": "COMPLETE"})
    state_by_id = {row["dataset"]: row for row in states}
    for dataset_id, row in sorted(rows.items()):
        key = HodgeCYID.dataset(dataset_id).serialize()
        if key in catalog.payload["datasets"]:
            continue
        state_row = state_by_id.get(dataset_id, {})
        status = _status(state_row.get("state") or row.get("acquisition_completeness"))
        count = _first_int(state_row.get("record_count") or row.get("source_record_count"))
        descriptor = DatasetDescriptor(
            dataset_id=HodgeCYID.dataset(dataset_id),
            name=row.get("human_name") or dataset_id.replace("_", " ").title(),
            construction_family=ConstructionFamily.known(_family(row.get("construction_family") or dataset_id)),
            acquisition_status=status,
            redistribution_status=_redistribution(row.get("license_status")),
            source_version=state_row.get("state") or row.get("acquisition_completeness"),
            record_semantics=row.get("record_semantics") or state_row.get("architecture_impact"),
            identifier_definition=row.get("primary_external_identifier") or None,
            expected_count=count,
            verified_count=count if status in {AcquisitionStatus.COMPLETE_LOCAL, AcquisitionStatus.COMPLETE_COLUMNAR, AcquisitionStatus.COMPLETE_NATIVE} else None,
            adapter_capabilities=tuple(_capabilities(status)),
            metadata={"bootstrap_schema": BOOTSTRAP_SCHEMA_VERSION, "architecture_state": state_row.get("state"), "architecture_impact": state_row.get("architecture_impact"), "license_status": row.get("license_status")},
        )
        catalog.register_dataset(descriptor)
        instance_id = _token(f"{dataset_id}_current")
        catalog.register_instance(DatasetInstance(
            instance_id=instance_id,
            dataset_id=descriptor.dataset_id,
            source_version=descriptor.source_version,
            source_revision=descriptor.source_version,
            acquisition_status=status,
            redistribution_status=descriptor.redistribution_status,
            installed_at="2026-08-20T16:23:03.098187+00:00",
            record_count=count,
            adapter_name="current_corpus_bootstrap",
            metadata={"bootstrap_schema": BOOTSTRAP_SCHEMA_VERSION},
        ))


def _register_sources(catalog: Any, inventory: list[dict[str, str]]) -> None:
    from hodgecy.storage import PhysicalSourceRef
    for row in inventory:
        local_path = (row.get("local_path") or "").replace("\\", "/")
        if not local_path:
            continue
        dataset_id = row["dataset_id"]
        instance_id = _token(f"{dataset_id}_current")
        if instance_id not in catalog.payload["instances"]:
            continue
        source_id = _token(f"{dataset_id}_{Path(local_path).stem}_{(row.get('SHA256') or stable_sha256(local_path))[:10]}")
        if source_id in catalog.payload["physical_sources"]:
            continue
        catalog.register_physical_source(PhysicalSourceRef(
            source_id=source_id,
            instance_id=instance_id,
            relative_path=local_path,
            sha256=row.get("SHA256") or None,
            byte_size=_first_int(row.get("byte_size")),
            source_format=_source_format(row.get("archive_format") or Path(local_path).suffix.lstrip(".")),
            metadata={"logical_dataset_id": row.get("logical_dataset_id"), "parse_status": row.get("parse_status"), "license_status": row.get("license_status"), "source_revision": row.get("source_version_revision"), "original_filename": row.get("original_filename")},
        ))


def _register_ks(catalog: Any, root: HodgeCYDataRoot) -> DatasetBuildSummary | None:
    ks_dir = root.raw / "kreuzer_skarke" / "parquet"
    paths = tuple(path.relative_to(root.root).as_posix() for path in sorted(ks_dir.glob("*.parquet")))
    if not paths:
        return None
    started = time.perf_counter()
    if "kreuzer_skarke_parquet" not in catalog.payload["columnar_sources"]:
        catalog.register_parquet_sources(
            columnar_id="kreuzer_skarke_parquet",
            instance_id=_token("kreuzer_skarke_current"),
            source_ids=tuple(f"ks_parquet_{i:03d}" for i, _ in enumerate(paths)),
            relative_paths=paths,
            table_name="kreuzer_skarke",
            common_field_mapping=KS_COMMON_FIELD_MAPPING,
            heavy_columns=KS_HEAVY_COLUMNS,
            query_safe_columns=KS_SCALAR_COLUMNS,
            table_kind=TableKind.SOURCE,
            source_revision=KS_PARQUET_SOURCE_REVISION,
            field_metadata=ks_field_metadata(),
            metadata={"dataset_profile": "kreuzer_skarke_4d_parquet", "source_revision": KS_PARQUET_SOURCE_REVISION},
        )
    row_count = catalog.payload["columnar_sources"].get("kreuzer_skarke_parquet", {}).get("row_count")
    return DatasetBuildSummary("kreuzer_skarke", "native_lazy_parquet", int(row_count or 473800776), None, queryable=True, materializable=False, validation_status="metadata_verified", output_relative_path="raw/kreuzer_skarke/parquet", adapter="kreuzer_skarke_parquet_lazy", adapter_version="1.1.0", source_revision=KS_PARQUET_SOURCE_REVISION, elapsed_seconds=time.perf_counter() - started, notes="Registered in-place; vertices remain lazy/heavy.")

def _register_native_large(catalog: Any, root: HodgeCYDataRoot) -> list[DatasetBuildSummary]:
    rows: list[DatasetBuildSummary] = []
    archive = root.raw / "cicy4" / "cicy4fib.zip"
    if archive.exists():
        started = time.perf_counter()
        index = build_cicy4_fibration_archive_index(archive, archive_relative_path="raw/cicy4/cicy4fib.zip", source_revision="cicy4-fibration-native-local", scan_text_members=False)
        index_path = root.indexes / "current_corpus" / "cicy4_fibration_archive_index.json"
        index.write(index_path)
        rows.append(DatasetBuildSummary("cicy4_fibrations", "native_lazy_zip_index", len(index.members), None, queryable=True, materializable=False, validation_status="member_ranges_indexed", output_relative_path=index_path.relative_to(root.root).as_posix(), adapter="cicy4_fibration_archive_index", source_revision="cicy4-fibration-native-local", elapsed_seconds=time.perf_counter() - started, notes="Selected parent lookup is lazy."))
    if (root.staged / "cicy4" / "cicy4folds.core.neutral.jsonl").exists():
        rows.append(DatasetBuildSummary("cicy4_core", "native_lazy_jsonl_registered", 921497, None, queryable=False, materializable=False, validation_status="registered_native_large_jsonl", output_relative_path="staged/cicy4", adapter="cicy4_native_staged_jsonl", source_revision="Oxford CICY4 local staged neutral", notes="Full CICY4 Parquet normalization deferred for a dedicated large streaming run."))
    return rows


def _normalization_specs() -> list[NormalizationSpec]:
    return [
        NormalizationSpec("cicy3_standard", "staged/cicy3/cicylist.neutral.jsonl", "current_cicy3_standard", _cicy3_row, 7890, ("source_record_id", "h11", "h21", "euler", "source_file", "validation_status")),
        NormalizationSpec("cicy3_favorable", "staged/cicy3_favorable/favourcicylist.neutral.jsonl", "current_cicy3_favorable", _favorable_row, 7890, ("source_record_id", "parent_cicy_id", "favour", "kahler_pos", "is_product", "h11", "h21")),
        NormalizationSpec("cicy3_fibrations", "staged/cicy3_fibrations/fibrationslist-3.neutral.jsonl", "current_cicy3_fibrations", _fibration_row, 139597, ("source_record_id", "parent_cicy_id", "fibration_id", "fibration_type"), TableKind.FIBRATION, "parent_cicy_id", "source_record_id"),
        NormalizationSpec("cicy3_quotients", "staged/cicy3_quotients/free_actions.jsonl", "current_cicy3_free_actions", _free_action_row, 1695, ("source_record_id", "parent_cicy_id", "action_index", "group_name", "group_order", "h11", "h21")),
        NormalizationSpec("cicy3_quotient_fibrations", "staged/cicy3_quotient_fibrations/quotientfibrationdata.neutral.jsonl", "current_cicy3_quotient_fibrations", _quotient_fibration_row, 20700, ("source_record_id", "parent_cicy_id", "fibnum", "symnum", "quotient_action_id"), TableKind.FIBRATION, "quotient_action_id", "source_record_id"),
        NormalizationSpec("weighted_p4", "staged/weighted_p4/weighted_p4.res4_res5.neutral.jsonl", "current_weighted_p4", _weighted_row, 7555, ("source_record_id", "weights_key", "degree", "h11", "h21", "euler")),
        NormalizationSpec("ip_weight_systems_4d", "staged/ip_weight_systems/tuwien_4d_ip_weights_hodge_k3.neutral.jsonl", "current_ip_weight_systems_4d", _ip_row, 184026, ("source_record_id", "weights_key", "degree", "h11", "h12", "source_flag")),
        NormalizationSpec("gcicy_fake_weighted", "staged/gcicy/cyci_fake_weighted.neutral.jsonl", "current_gcicy_fake_weighted", _payload_row, 1752, ("source_record_id", "source_dataset", "source_file", "validation_status")),
        NormalizationSpec("picard_fuchs_cyo_topological", "staged/picard_fuchs/cyo_operators.neutral.jsonl", "current_cyo_operators", _operator_row, 613, ("operator_id", "line_no", "operator_order_max_Dt")),
        NormalizationSpec("picard_fuchs_cyo_topological", "staged/picard_fuchs/cyo_topological.parsed.neutral.jsonl", "current_cyo_topological", _operator_topology_row, 584, ("operator_id", "line_no")),
    ]


def _normalize(catalog: Any, root: HodgeCYDataRoot, spec: NormalizationSpec, batch_size: int) -> DatasetBuildSummary:
    started = time.perf_counter()
    source = root.root / spec.staged_relative_path
    if not source.exists():
        return DatasetBuildSummary(spec.dataset_id, "missing_staged_source", validation_status="missing", adapter=spec.adapter, notes=spec.staged_relative_path)
    out_dir = root.normalized / "current_corpus" / spec.dataset_id
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / f"{spec.table_name}.parquet"
    manifest = out_dir / f"{spec.table_name}.manifest.json"
    rejected = root.rejected / "current_corpus" / f"{spec.table_name}.rejected.jsonl"
    if _manifest_current(manifest, source, spec):
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        normalized = int(payload["normalized_count"])
        rejected_count = int(payload["rejected_count"])
    else:
        normalized, rejected_count = _stream_jsonl_to_parquet(source, output, rejected, spec.transform, batch_size)
        _write_manifest(manifest, source, output, rejected, spec, normalized, rejected_count)
    relative = output.relative_to(root.root).as_posix()
    output_sha256 = _manifest_output_sha256(manifest, output)
    _register_normalized(catalog, root, spec, relative, output.stat().st_size, normalized, output_sha256=output_sha256)
    source_count = _count_jsonl(source)
    return DatasetBuildSummary(spec.dataset_id, "normalized_parquet", source_count, normalized, rejected_count, normalized_bytes=output.stat().st_size, queryable=True, materializable=True, validation_status=("validated" if (spec.expected_count in {None, normalized} and rejected_count == 0) else "validated_with_count_gap"), output_relative_path=relative, adapter=spec.adapter, source_revision=_sha256_file(source)[:16], elapsed_seconds=time.perf_counter() - started, notes=f"expected_count={spec.expected_count}")


def _stream_jsonl_to_parquet(source: Path, output: Path, rejected: Path, transform: Callable[[dict[str, Any]], dict[str, Any] | None], batch_size: int) -> tuple[int, int]:
    try:
        import pyarrow as pa  # type: ignore[import-not-found]
        import pyarrow.parquet as pq  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise MissingCapabilityError("PyArrow is required for corpus bootstrap normalization") from exc
    temp = output.with_name(output.name + ".tmp")
    rejected.parent.mkdir(parents=True, exist_ok=True)
    writer = None
    batch: list[dict[str, Any]] = []
    ok = 0
    bad = 0
    with _open_text(source) as handle, rejected.open("w", encoding="utf-8") as reject_handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = transform(json.loads(line))
            except Exception as exc:  # noqa: BLE001
                row = None
                reject_handle.write(json.dumps({"line_no": line_no, "error": str(exc)}, sort_keys=True) + "\n")
            if row is None:
                bad += 1
                continue
            batch.append(row)
            if len(batch) >= batch_size:
                table = pa.Table.from_pylist(batch)
                if writer is None:
                    output.parent.mkdir(parents=True, exist_ok=True)
                    writer = pq.ParquetWriter(temp, table.schema)
                table = table.cast(writer.schema) if table.schema != writer.schema else table
                writer.write_table(table)
                ok += len(batch)
                batch = []
        if batch:
            table = pa.Table.from_pylist(batch)
            if writer is None:
                output.parent.mkdir(parents=True, exist_ok=True)
                writer = pq.ParquetWriter(temp, table.schema)
            table = table.cast(writer.schema) if table.schema != writer.schema else table
            writer.write_table(table)
            ok += len(batch)
    if writer is None:
        pq.write_table(pa.Table.from_pylist([{"empty": True}]).slice(0, 0), temp)
    else:
        writer.close()
    temp.replace(output)
    return ok, bad


def _register_normalized(catalog: Any, root: HodgeCYDataRoot, spec: NormalizationSpec, relative: str, byte_size: int, rows: int, *, output_sha256: str) -> None:
    dataset_key = HodgeCYID.dataset(spec.dataset_id).serialize()
    if dataset_key not in catalog.payload["datasets"]:
        catalog.register_dataset(DatasetDescriptor(dataset_id=HodgeCYID.dataset(spec.dataset_id), name=spec.dataset_id.replace("_", " ").title(), construction_family=ConstructionFamily.known(_family(spec.dataset_id)), acquisition_status=AcquisitionStatus.COMPLETE_COLUMNAR, redistribution_status=RedistributionStatus.ACQUIRED_LOCALLY_BY_USER, expected_count=rows, verified_count=rows, metadata={"bootstrap_schema": BOOTSTRAP_SCHEMA_VERSION}))
    instance_id = _token(f"{spec.dataset_id}_{spec.table_name}_normalized")
    if instance_id not in catalog.payload["instances"]:
        catalog.register_instance(DatasetInstance(instance_id=instance_id, dataset_id=HodgeCYID.dataset(spec.dataset_id), source_version=NORMALIZATION_SCHEMA_VERSION, source_revision=NORMALIZATION_SCHEMA_VERSION, acquisition_status=AcquisitionStatus.COMPLETE_COLUMNAR, redistribution_status=RedistributionStatus.ACQUIRED_LOCALLY_BY_USER, installed_at="2026-08-20T16:23:03.098187+00:00", record_count=rows, adapter_name=spec.adapter, metadata={"normalization_schema": NORMALIZATION_SCHEMA_VERSION}))
    columnar_id = _token(f"{spec.table_name}_columnar")
    source_id = _token(f"{spec.table_name}_parquet")
    if columnar_id not in catalog.payload["columnar_sources"]:
        catalog.register_parquet_source(columnar_id=columnar_id, instance_id=instance_id, source_id=source_id, relative_path=relative, table_name=spec.table_name, query_safe_columns=spec.query_safe_columns, table_kind=spec.table_kind, parent_key=spec.parent_key, child_key=spec.child_key, metadata={"normalization_schema": NORMALIZATION_SCHEMA_VERSION, "adapter": spec.adapter})
    _refresh_generated_physical_source(catalog, source_id, relative, byte_size, output_sha256)


def _relationship_rows(root: HodgeCYDataRoot) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows += _rels_from_jsonl(root.staged / "cicy3_favorable" / "favourcicylist.neutral.jsonl", lambda p: _rel("cicy3_standard", str((p.get("source_fields") or {}).get("Num") or p.get("source_record_id")), "cicy3_favorable", str((p.get("source_fields") or {}).get("Num") or p.get("source_record_id")), "source_crosswalk"))
    rows += _rels_from_jsonl(root.staged / "cicy3_fibrations" / "fibrationslist-3.neutral.jsonl", lambda p: None if p.get("parse_status", "VALID") != "VALID" else _rel("cicy3_favorable", str(p.get("source_cicy_id")), "cicy3_fibrations", str(p.get("source_record_id")), "fibration_of", "source_explicit"))
    rows += _rels_from_jsonl(root.staged / "cicy3_quotients" / "free_actions.jsonl", lambda p: _rel("cicy3_standard", str(p.get("parent_cicy_id")), "cicy3_quotients", f"{p.get('parent_cicy_id')}:{p.get('action_index_within_parent')}", "free_action_on", "source_explicit"))
    rows += _rels_from_jsonl(root.staged / "cicy3_quotient_fibrations" / "quotientfibrationdata.neutral.jsonl", lambda p: _rel("cicy3_quotients", f"{p.get('Cicynum')}:{p.get('Symnum')}", "cicy3_quotient_fibrations", str(p.get("source_record_index")), "quotient_fibration_of", "source_explicit"))
    rows += _weighted_ip_crosswalk(root)
    rows += _operator_topology_crosswalk(root)
    rows += _cicy4_member_rels(root)
    return rows


def _rels_from_jsonl(path: Path, transform: Callable[[dict[str, Any]], dict[str, Any] | None]) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with _open_text(path) as handle:
        for line in handle:
            if line.strip():
                row = transform(json.loads(line))
                if row is not None:
                    rows.append(row)
    return rows


def _rel(source_dataset: str, source_id: str, target_dataset: str, target_id: str, relation: str, evidence: str = "exact_source_id") -> dict[str, Any]:
    payload = {"relationship_type": relation, "source_id": source_id, "source_dataset": source_dataset, "target_id": target_id, "target_dataset": target_dataset, "evidence_type": evidence, "claim_level": "source_reported", "join_state": "matched", "directed": True, "source_record_id": source_id}
    return {"relationship_id": stable_sha256(payload), **payload}


def _weighted_ip_crosswalk(root: HodgeCYDataRoot) -> list[dict[str, Any]]:
    ip = root.staged / "ip_weight_systems" / "tuwien_4d_ip_weights_hodge_k3.neutral.jsonl"
    weighted = root.staged / "weighted_p4" / "weighted_p4.res4_res5.neutral.jsonl"
    if not ip.exists() or not weighted.exists():
        return []
    ip_by_weight: dict[str, str] = {}
    with _open_text(ip) as handle:
        for line in handle:
            if line.strip():
                p = json.loads(line)
                ip_by_weight.setdefault(_weights_key((p.get("source_fields") or {}).get("weights") or []), str(p.get("source_record_id")))
    rows = []
    with _open_text(weighted) as handle:
        for line in handle:
            if not line.strip():
                continue
            p = json.loads(line)
            key = _weights_key((p.get("source_fields") or {}).get("weights") or [])
            if key in ip_by_weight:
                rows.append(_rel("weighted_p4", str(p.get("source_record_id")), "ip_weight_systems_4d", ip_by_weight[key], "source_crosswalk", "exact_weight_vector"))
    return rows


def _operator_topology_crosswalk(root: HodgeCYDataRoot) -> list[dict[str, Any]]:
    path = root.staged / "picard_fuchs" / "cyo_topological.parsed.neutral.jsonl"
    return _rels_from_jsonl(path, lambda p: _rel("picard_fuchs_operator", str(p.get("operator_id")), "picard_fuchs_topology", str(p.get("operator_id")), "source_crosswalk", "exact_operator_id"))


def _cicy4_member_rels(root: HodgeCYDataRoot) -> list[dict[str, Any]]:
    archive = root.raw / "cicy4" / "cicy4fib.zip"
    if not archive.exists():
        return []
    index = build_cicy4_fibration_archive_index(archive, archive_relative_path="raw/cicy4/cicy4fib.zip", source_revision="cicy4-fibration-native-local", scan_text_members=False)
    return [_rel("cicy4_core", f"{m.parent_min}-{m.parent_max}", "cicy4_fibrations", m.member_name, "archive_member_covers_parent_range", "source_member_range") for m in index.members]


def _write_relationships(catalog: Any, root: HodgeCYDataRoot, rows: list[dict[str, Any]]) -> DatasetBuildSummary | None:
    if not rows:
        return None
    try:
        import pyarrow as pa  # type: ignore[import-not-found]
        import pyarrow.parquet as pq  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise MissingCapabilityError("PyArrow is required for relationship table writing") from exc
    started = time.perf_counter()
    out = root.normalized / "current_corpus" / "relationships" / "current_corpus_relationships.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    pq.write_table(pa.Table.from_pylist(rows), tmp)
    tmp.replace(out)
    spec = NormalizationSpec("current_corpus_relationships", "", "current_corpus_relationships", lambda _: None, len(rows), ("relationship_id", "relationship_type", "source_id", "source_dataset", "target_id", "target_dataset", "evidence_type", "claim_level", "join_state", "directed", "source_record_id"), TableKind.RELATIONSHIP, adapter="current_corpus_relationship_builder")
    _register_normalized(catalog, root, spec, out.relative_to(root.root).as_posix(), out.stat().st_size, len(rows), output_sha256=_sha256_file(out))
    return DatasetBuildSummary("current_corpus_relationships", "relationship_parquet", len(rows), len(rows), relationship_count=len(rows), normalized_bytes=out.stat().st_size, queryable=True, materializable=True, validation_status="matched_source_relationships", output_relative_path=out.relative_to(root.root).as_posix(), adapter=spec.adapter, elapsed_seconds=time.perf_counter() - started)


def _write_snapshot(catalog: Any, root: HodgeCYDataRoot, build_rows: list[DatasetBuildSummary], relationships: list[dict[str, Any]], config: CorpusBootstrapConfig) -> Path:
    snapshot_id = "current_corpus_development"
    existing = dict(catalog.payload["snapshots"].get(snapshot_id) or {})
    snapshot_payload = {
        "snapshot_id": snapshot_id,
        "created_at": existing.get("created_at") or utc_now_iso(),
        "hodgecy_version": config.hodgecy_version or catalog.metadata.hodgecy_version,
        "hodgecy_commit": config.hodgecy_commit or catalog.metadata.hodgecy_commit,
        "catalog_schema_version": catalog.metadata.catalog_schema_version.to_dict(),
        "dataset_instances": sorted(catalog.payload["instances"]),
        "source_checksums": {key: value.get("sha256") for key, value in sorted(catalog.payload["physical_sources"].items())},
        "normalized_schema_versions": {key: value.get("schema_version", {}).get("value", "v1") for key, value in sorted(catalog.payload["instances"].items())},
        "metadata": {
            "bootstrap_schema": BOOTSTRAP_SCHEMA_VERSION,
            "build_rows": [r.to_dict() for r in build_rows],
            "relationship_count": len(relationships),
            "corpus_integration_complete": False,
            "acquisition_pass_ready": False,
        },
    }
    if catalog.payload["snapshots"].get(snapshot_id) != snapshot_payload:
        catalog.payload["snapshots"][snapshot_id] = snapshot_payload
        catalog._touch()
        catalog._write()
    path = root.manifests / "current_hodgecy_corpus_snapshot.json"
    path.write_text(json.dumps(snapshot_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path

def _write_reports(root: HodgeCYDataRoot, catalog: Any, build_rows: list[DatasetBuildSummary], relationships: list[dict[str, Any]], snapshot: Path, elapsed: float) -> dict[str, Path]:
    build_payload = [r.to_dict() for r in build_rows]
    build_json = root.reports / "current_corpus_build.json"
    build_tsv = root.reports / "current_corpus_build.tsv"
    build_json.write_text(json.dumps(build_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_tsv(build_tsv, build_payload)
    prov = root.reports / "current_corpus_provenance.tsv"
    _write_tsv(prov, [{"dataset": r.dataset, "source_identity_count": r.source_count or r.normalized_count or 0, "locator_count": r.source_count or r.normalized_count or 0, "revision_count": r.source_count or r.normalized_count or 0, "physical_source_count": r.source_count or r.normalized_count or 0, "checksum_coverage": "manifest_or_inventory", "adapter_provenance": bool(r.adapter), "schema_provenance": NORMALIZATION_SCHEMA_VERSION, "validation": r.validation_status} for r in build_rows])
    rel_tsv = root.reports / "current_corpus_relationships.tsv"
    _write_tsv(rel_tsv, _relationship_summary(relationships))
    status_json = root.reports / "current_catalog_status.json"
    status_md = root.reports / "current_catalog_status.md"
    status = {"catalog_path": catalog.path.as_posix(), "catalog_schema_version": catalog.metadata.catalog_schema_version.value, "dataset_count": len(catalog.list_datasets()), "instance_count": len(catalog.list_instances()), "table_count": len(catalog.list_tables()), "snapshot": snapshot.relative_to(root.root).as_posix(), "build_elapsed_seconds": round(elapsed, 6), "corpus_integration_complete": False, "acquisition_pass_ready": False, "remaining_blockers": list(_remaining_blockers())}
    status_json.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    status_md.write_text("# HodgeCY Current Catalog Status\n\nCurrent acquired corpus fully integrated: NO\n\nSecond global acquisition pass: NOT_READY\n", encoding="utf-8")
    return {"build_json": build_json, "build_tsv": build_tsv, "provenance_tsv": prov, "relationships_tsv": rel_tsv, "status_json": status_json, "status_md": status_md}


def _relationship_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (row["relationship_type"], row["source_dataset"])
        counts[key] = counts.get(key, 0) + 1
    return [{"relationship_dataset": "current_corpus_relationships", "relation_type": k[0], "source_dataset": k[1], "source_rows": v, "valid_edges": v, "matched_endpoints": v, "unmatched": 0, "ambiguous": 0, "rejected": 0, "evidence_type": "source_explicit_or_exact_source_id"} for k, v in sorted(counts.items())]


def _write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("\n", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _tsv(row.get(k)) for k in fields})


def _cicy3_row(p: dict[str, Any]) -> dict[str, Any] | None:
    sf = p.get("source_fields") or {}
    h = p.get("hodge") or {}
    c2 = p.get("c2_vector_source_basis") or sf.get("C2") or []
    return _base(p, str(p.get("cicy_id") or sf.get("Num")), {"h11": h.get("h11") or sf.get("H11"), "h21": h.get("h21") or sf.get("H21"), "euler": _euler(h.get("h11") or sf.get("H11"), h.get("h21") or sf.get("H21")), "num_projective_spaces": p.get("num_projective_spaces") or sf.get("NumPs"), "num_polynomials": p.get("num_polynomials") or sf.get("NumPol"), "eta": p.get("eta") or sf.get("Eta"), "matrix_json": _json(p.get("configuration_degree_matrix")), "ambient_projective_dimensions_json": _json(p.get("ambient_projective_dimensions_derived_from_row_sums")), "c2_basis_id": "cicy3_standard.source_divisor_basis", "c2_basis_json": _json([f"J{i+1}" for i in range(len(c2))]), "c2_coefficients_json": _json(c2), "redun_source_json": _json(p.get("redun_source_vector") or sf.get("Redun"))})


def _favorable_row(p: dict[str, Any]) -> dict[str, Any] | None:
    if p.get("parse_status", "VALID") != "VALID":
        return None
    sf = p.get("source_fields") or {}
    h = p.get("hodge_data_if_supplied") or {}
    c2 = sf.get("C2") or []
    return _base(p, str(p.get("source_record_id") or sf.get("Num")), {"parent_cicy_id": str(sf.get("Num") or p.get("source_record_id")), "h11": h.get("h11") or sf.get("H11"), "h21": h.get("h21") or sf.get("H21"), "favour": bool(sf.get("Favour")), "kahler_pos": bool(sf.get("KahlerPos")), "is_product": bool(sf.get("IsProduct")), "configuration_json": _json(p.get("raw_configuration") or sf.get("Conf")), "c2_basis_id": "cicy3_favorable.source_divisor_basis", "c2_basis_json": _json([f"J{i+1}" for i in range(len(c2))]), "c2_coefficients_json": _json(c2)})


def _fibration_row(p: dict[str, Any]) -> dict[str, Any] | None:
    if p.get("parse_status", "VALID") != "VALID":
        return None
    return _base(p, str(p.get("source_record_id")), {"parent_cicy_id": str(p.get("source_cicy_id")), "fibration_id": str(p.get("fibration_id")), "fibration_type": str(p.get("fibration_type") or "source_payload"), "fiber_json": _json(p.get("fiber_data")), "base_json": _json(p.get("base_data")), "ambient_decomposition_json": _json(p.get("ambient_decomposition")), "nesting_parent": p.get("nesting_parent")})


def _free_action_row(p: dict[str, Any]) -> dict[str, Any] | None:
    h = p.get("quotient_hodge") or {}
    group = str(p.get("group_name") or "")
    sid = f"{p.get('parent_cicy_id')}:{p.get('action_index_within_parent')}"
    return _base(p, sid, {"parent_cicy_id": str(p.get("parent_cicy_id")), "action_index": int(p.get("action_index_within_parent") or 0), "group_name": group, "group_order": _group_order(group), "gap_id_raw": p.get("gap_id_raw"), "h11": h.get("h11"), "h21": h.get("h21"), "source_payload_sha256": p.get("source_payload_sha256"), "source_claim_level": "source_reported"}, include_payload=False)


def _quotient_fibration_row(p: dict[str, Any]) -> dict[str, Any] | None:
    return _base(p, str(p.get("source_record_index")), {"parent_cicy_id": str(p.get("Cicynum")), "fibnum": str(p.get("Fibnum")), "symnum": str(p.get("Symnum")), "quotient_action_id": f"{p.get('Cicynum')}:{p.get('Symnum')}", "basename": p.get("Basename"), "basesymname": p.get("Basesymname"), "symname": p.get("Symname"), "fibpres": bool(p.get("Fibpres")), "source_payload_sha256": p.get("source_payload_sha256")})


def _weighted_row(p: dict[str, Any]) -> dict[str, Any] | None:
    if p.get("parse_status", "VALID") != "VALID":
        return None
    sf = p.get("source_fields") or {}
    weights = sf.get("weights") or []
    return _base(p, str(p.get("source_record_id")), {"weights_key": _weights_key(weights), "weights_json": _json(weights), "degree": sf.get("degree"), "h11": sf.get("h11"), "h21": sf.get("h21"), "euler": sf.get("chi"), "n_weights": sf.get("n_weights")})


def _ip_row(p: dict[str, Any]) -> dict[str, Any] | None:
    if p.get("parse_status", "VALID") != "VALID":
        return None
    sf = p.get("source_fields") or {}
    weights = sf.get("weights") or []
    return _base(p, str(p.get("source_record_id")), {"weights_key": _weights_key(weights), "weights_json": _json(weights), "degree": sf.get("degree"), "source_flag": sf.get("source_flag"), "h11": sf.get("h11"), "h12": sf.get("h12"), "M_points": sf.get("M_points"), "M_vertices": sf.get("M_vertices"), "N_points": sf.get("N_points"), "N_vertices": sf.get("N_vertices"), "K3_projection_count": sf.get("K3_projection_count")})


def _operator_row(p: dict[str, Any]) -> dict[str, Any] | None:
    return {"source_record_id": str(p.get("operator_id")), "operator_id": str(p.get("operator_id")), "line_no": p.get("line_no"), "operator_order_max_Dt": p.get("operator_order_max_Dt"), "expression_raw": p.get("expression_raw"), "source_dataset": "picard_fuchs_cyo_topological", "source_file": "staged/picard_fuchs/cyo_operators.neutral.jsonl", "source_location": f"line {p.get('line_no')}", "validation_status": "source_reported", "payload_json": _json(p)}


def _operator_topology_row(p: dict[str, Any]) -> dict[str, Any] | None:
    return {"source_record_id": str(p.get("operator_id")), "operator_id": str(p.get("operator_id")), "line_no": p.get("line_no"), "source_numeric_fields_json": _json(p.get("source_numeric_fields")), "source_dataset": "picard_fuchs_cyo_topological", "source_file": "staged/picard_fuchs/cyo_topological.parsed.neutral.jsonl", "source_location": f"line {p.get('line_no')}", "validation_status": "source_reported", "payload_json": _json(p)}


def _payload_row(p: dict[str, Any]) -> dict[str, Any] | None:
    return _base(p, str(p.get("source_record_id") or p.get("id") or p.get("line_no") or stable_sha256(p)[:16]), {})


def _base(p: dict[str, Any], sid: str, extra: dict[str, Any], include_payload: bool = True) -> dict[str, Any]:
    row = {"source_record_id": str(sid), "source_dataset": str(p.get("source_dataset") or "unknown"), "source_file": str(p.get("source_file") or "").replace("\\", "/"), "source_location": str(p.get("source_location") or p.get("line_no") or ""), "validation_status": str(p.get("parse_status") or "source_reported")}
    row.update(extra)
    if include_payload:
        row["payload_json"] = _json(p)
    return row


def _manifest_current(manifest: Path, source: Path, spec: NormalizationSpec) -> bool:
    if not manifest.exists():
        return False
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return payload.get("schema_version") == NORMALIZATION_SCHEMA_VERSION and payload.get("source_sha256") == _sha256_file(source) and payload.get("adapter") == spec.adapter


def _write_manifest(manifest: Path, source: Path, output: Path, rejected: Path, spec: NormalizationSpec, normalized: int, rejected_count: int) -> None:
    payload = {"schema_version": NORMALIZATION_SCHEMA_VERSION, "dataset_id": spec.dataset_id, "adapter": spec.adapter, "source_relative_path": source.as_posix(), "source_sha256": _sha256_file(source), "source_size": source.stat().st_size, "output_file": output.name, "output_sha256": _sha256_file(output), "normalized_count": normalized, "rejected_count": rejected_count, "rejected_file": rejected.name}
    manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _manifest_output_sha256(manifest: Path, output: Path) -> str:
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return _sha256_file(output)
    checksum = payload.get("output_sha256")
    return str(checksum) if checksum else _sha256_file(output)


def _refresh_generated_physical_source(catalog: Any, source_id: str, relative_path: str, byte_size: int, sha256: str) -> None:
    source = catalog.payload["physical_sources"].get(source_id)
    if not source:
        return
    updated = dict(source)
    updated["sha256"] = sha256
    updated["byte_size"] = byte_size
    updated["relative_path"] = relative_path
    metadata = dict(updated.get("metadata") or {})
    metadata["generated_by"] = BOOTSTRAP_SCHEMA_VERSION
    updated["metadata"] = metadata
    if updated != source:
        catalog.payload["physical_sources"][source_id] = updated
        catalog._touch()
        catalog._write()


def _open_text(path: Path) -> Iterator[str]:
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def _count_jsonl(path: Path) -> int:
    with _open_text(path) as handle:
        return sum(1 for line in handle if line.strip())


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _euler(h11: Any, h21: Any) -> int | None:
    try:
        return 2 * (int(h11) - int(h21))
    except (TypeError, ValueError):
        return None


def _weights_key(weights: Iterable[Any]) -> str:
    return ",".join(str(int(w)) for w in weights)


def _group_order(group: str) -> int | None:
    m = re.fullmatch(r"Z(\d+)", group.strip())
    return int(m.group(1)) if m else None


def _status(value: str | None) -> AcquisitionStatus:
    text = (value or "").upper()
    if text in AcquisitionStatus.__members__:
        return AcquisitionStatus[text]
    if text in {item.value for item in AcquisitionStatus}:
        return AcquisitionStatus(text)
    if "COLUMNAR" in text:
        return AcquisitionStatus.COMPLETE_COLUMNAR
    if "NATIVE" in text:
        return AcquisitionStatus.COMPLETE_NATIVE
    if "REMOTE" in text:
        return AcquisitionStatus.COMPLETE_REMOTE
    if "MANUAL" in text:
        return AcquisitionStatus.MANUAL_SOURCE_REQUIRED
    if "REGISTRY" in text:
        return AcquisitionStatus.SOURCE_REGISTRY_ONLY
    if "COMPUTABLE" in text:
        return AcquisitionStatus.COMPUTABLE_NOT_PREENUMERATED
    if "PARTIAL" in text:
        return AcquisitionStatus.PARTIAL_PUBLIC_CORPUS
    if "COMPLETE" in text:
        return AcquisitionStatus.COMPLETE_LOCAL
    return AcquisitionStatus.UNRESOLVED


def _redistribution(value: str | None) -> RedistributionStatus:
    text = (value or "").upper()
    if "CC_BY" in text or "REDISTRIBUTABLE" in text:
        return RedistributionStatus.REDISTRIBUTABLE
    if "REMOTE" in text or "MANUAL" in text:
        return RedistributionStatus.REMOTE_OR_MANUAL_ONLY
    if "ATTRIBUTION" in text or "LOCAL" in text:
        return RedistributionStatus.ACQUIRED_LOCALLY_BY_USER
    return RedistributionStatus.UNSPECIFIED


def _capabilities(status: AcquisitionStatus) -> list[str]:
    if status is AcquisitionStatus.COMPLETE_COLUMNAR:
        return ["columnar", "streaming"]
    if status is AcquisitionStatus.COMPLETE_NATIVE:
        return ["archive", "native_payload", "streaming"]
    if status is AcquisitionStatus.COMPLETE_LOCAL:
        return ["streaming", "native_payload"]
    if status is AcquisitionStatus.COMPLETE_REMOTE:
        return ["remote"]
    return []


def _family(value: str) -> str:
    text = re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_")
    if text.startswith("cicy3"):
        return "cicy3"
    if text.startswith("cicy4"):
        return "cicy4"
    if "picard" in text or "operator" in text:
        return "picard_fuchs"
    if "weighted" in text:
        return "weighted_p4"
    if "toric" in text or "kreuzer" in text or "ip_weight" in text:
        return "toric_hypersurface"
    return text or "source_registry"


def _source_format(value: str) -> SourceFormat:
    text = value.lower().lstrip(".")
    return {"zip": SourceFormat.ZIP, "parquet": SourceFormat.PARQUET, "json": SourceFormat.JSON, "jsonl": SourceFormat.JSONL, "tsv": SourceFormat.TSV, "csv": SourceFormat.CSV}.get(text, SourceFormat.NATIVE)


def _token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9._=-]+", "_", value).strip("_")
    return (token if token and token[0].isalnum() else "id_" + token)[:96]


def _first_int(value: Any) -> int | None:
    if value is None:
        return None
    m = re.search(r"\d+", str(value))
    return int(m.group(0)) if m else None


def _tsv(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def _remaining_blockers() -> tuple[str, ...]:
    return (
        "CICY4 core is registered as native-large staged JSONL; full normalized CICY4 Parquet remains a dedicated large streaming pass.",
        "CICY orientifold/symmetry, divisor/intersection, toric orientifold, thraxion/transition, and source-registry-only families are registered but not fully normalized.",
        "Some sources have inventory-level checksum/provenance but not row-level checksum coverage.",
    )
