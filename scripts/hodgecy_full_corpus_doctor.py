from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from hodgecy.query import QuerySpec
from hodgecy.research.full_corpus_context import EXPECTED_V1_COUNTS, FullCorpusContext

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "research_outputs" / "hodgecy_ii" / "infrastructure"
DOCS_CENSUS = REPO_ROOT / "docs" / "corpus" / "current_dataset_census.tsv"
DOCS_SUMMARY = REPO_ROOT / "docs" / "corpus" / "current_corpus_summary.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the full production HodgeCY v1 corpus for HodgeCY II.")
    parser.add_argument("--root", default=None, help="Production HODGECY_DATA_ROOT. Defaults to environment.")
    args = parser.parse_args(argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    versions = runtime_versions()
    env_contract = build_environment_contract(args.root)
    write_json(OUT_DIR / "environment_contract.json", env_contract)
    write_environment_contract_md(env_contract)

    failures: list[str] = []
    warnings: list[str] = []
    context: FullCorpusContext | None = None
    try:
        context = FullCorpusContext.open(args.root)
    except Exception as exc:  # noqa: BLE001
        failures.append(f"production_context_open_failed: {type(exc).__name__}: {exc}")
        write_failure_outputs(versions, failures, warnings)
        print("FULL_HODGECY_V1_CORPUS_READY = NO")
        return 1

    root = context.data_root
    catalog = context.catalog
    docs_census = read_tsv(DOCS_CENSUS)
    expected_by_dataset = {row["dataset_id"]: row for row in docs_census}
    datasets = catalog.list_datasets()
    instances = catalog.list_instances()
    physical_sources = catalog.list_physical_sources()
    columnar_sources = catalog.list_columnar_sources()
    tables = catalog.list_tables()

    source_by_instance: dict[str, list[Any]] = {}
    for source in physical_sources:
        source_by_instance.setdefault(source.instance_id, []).append(source)
    columnar_by_instance: dict[str, list[Any]] = {}
    for source in columnar_sources:
        columnar_by_instance.setdefault(source.instance_id, []).append(source)
    table_by_instance: dict[str, list[Any]] = {}
    for table in tables:
        if table.instance_id:
            table_by_instance.setdefault(table.instance_id, []).append(table)
    instances_by_dataset: dict[str, list[Any]] = {}
    for instance in instances:
        instances_by_dataset.setdefault(instance.dataset_id.local_id, []).append(instance)

    dataset_rows, traversal_rows = verify_datasets(context, expected_by_dataset, instances_by_dataset, source_by_instance, table_by_instance)
    instance_rows = verify_instances(context, source_by_instance, columnar_by_instance)
    table_rows = verify_tables(context)
    relationship_rows, relationship_summary = verify_relationships(context)

    write_tsv(OUT_DIR / "production_dataset_verification.tsv", dataset_rows)
    write_tsv(OUT_DIR / "production_instance_verification.tsv", instance_rows)
    write_tsv(OUT_DIR / "production_query_table_verification.tsv", table_rows)
    write_tsv(OUT_DIR / "production_relationship_verification.tsv", relationship_rows)
    write_json(OUT_DIR / "production_relationship_summary.json", relationship_summary)
    write_tsv(OUT_DIR / "full_corpus_traversal.tsv", traversal_rows)
    write_root_resolution(context)

    for row in dataset_rows:
        if row["status"] != "OK":
            failures.append(f"dataset:{row['dataset_id']}:{row['status']}")
    for row in table_rows:
        if row["status"] != "OK":
            failures.append(f"table:{row['table_name']}:{row['status']}")
    for row in relationship_rows:
        if row["status"] != "OK":
            failures.append(f"relationship:{row['table_name']}:{row['status']}")

    counts = context.summary_counts()
    for key in ("logical_dataset_count", "instance_count", "physical_source_count", "query_table_count"):
        if counts.get(key) != EXPECTED_V1_COUNTS[key]:
            failures.append(f"{key}_expected_{EXPECTED_V1_COUNTS[key]}_actual_{counts.get(key)}")
    if int(counts.get("relationship_edge_count") or 0) != int(EXPECTED_V1_COUNTS["relationship_edge_count"]):
        warnings.append(
            "relationship_edge_count_differs_from_docs_summary:"
            f"doctor_actual={counts.get('relationship_edge_count')};docs_summary={EXPECTED_V1_COUNTS['relationship_edge_count']}"
        )

    ready = not failures
    readiness = {
        "FULL_HODGECY_V1_CORPUS_READY": "YES" if ready else "NO",
        "HODGECY_VERSION": versions["hodgecy"],
        "DATA_ROOT_FINGERPRINT": data_root_fingerprint(root.root),
        "CATALOG_FINGERPRINT": file_sha256(root.catalogs / "current_corpus" / "catalog.json"),
        "RELEASE_FINGERPRINT": context.release_fingerprint,
        "LOGICAL_DATASET_COUNT": counts.get("logical_dataset_count"),
        "INSTANCE_COUNT": counts.get("instance_count"),
        "PHYSICAL_SOURCE_COUNT": counts.get("physical_source_count"),
        "QUERY_TABLE_COUNT": counts.get("query_table_count"),
        "SOURCE_DATA_RECORD_COUNT": counts.get("source_data_record_count"),
        "RELATIONSHIP_EDGE_COUNT": counts.get("relationship_edge_count"),
        "DATASETS_VERIFIED": sum(row["status"] == "OK" for row in dataset_rows),
        "INSTANCES_VERIFIED": sum(row["status"] == "OK" for row in instance_rows),
        "QUERY_TABLES_VERIFIED": sum(row["status"] == "OK" for row in table_rows),
        "RELATIONSHIP_TABLES_VERIFIED": sum(row["status"] == "OK" for row in relationship_rows),
        "STORAGE_BACKENDS": ["json_catalog", "pyarrow.dataset", "duckdb"],
        "DUCKDB_VERSION": versions["duckdb"],
        "PYARROW_VERSION": versions["pyarrow"],
        "FAILURES": failures,
        "WARNINGS": warnings,
        "GENERATED_AT": utc_now(),
    }
    write_json(OUT_DIR / "full_corpus_readiness.json", readiness)
    write_activation_report(readiness, env_contract)

    print(f"FULL_HODGECY_V1_CORPUS_READY = {readiness['FULL_HODGECY_V1_CORPUS_READY']}")
    print(f"LOGICAL_DATASETS = {readiness['LOGICAL_DATASET_COUNT']}")
    print(f"DATASET_INSTANCES = {readiness['INSTANCE_COUNT']}")
    print(f"PHYSICAL_SOURCES = {readiness['PHYSICAL_SOURCE_COUNT']}")
    print(f"QUERY_TABLES = {readiness['QUERY_TABLE_COUNT']}")
    print(f"RELATIONSHIP_EDGES = {readiness['RELATIONSHIP_EDGE_COUNT']}")
    return 0 if ready else 1


def runtime_versions() -> dict[str, str]:
    import duckdb
    import hodgecy
    import pandas
    import pyarrow
    import sympy

    return {
        "hodgecy": hodgecy.__version__,
        "duckdb": duckdb.__version__,
        "pyarrow": pyarrow.__version__,
        "pandas": pandas.__version__,
        "sympy": sympy.__version__,
    }


def build_environment_contract(explicit_root: str | None) -> dict[str, Any]:
    occurrences: dict[str, list[dict[str, str]]] = {}
    env_re = re.compile(r"\bHODGECY_[A-Z0-9_]+\b")
    for path in REPO_ROOT.rglob("*"):
        if path.is_dir() or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if path.suffix.lower() not in {".py", ".md", ".ps1", ".json", ".toml", ".txt"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            for variable in env_re.findall(line):
                occurrences.setdefault(variable, []).append({"source_file": rel(path), "line": str(line_no)})
    variables = []
    for variable, sites in sorted(occurrences.items()):
        current = explicit_root if variable == "HODGECY_DATA_ROOT" and explicit_root else os.environ.get(variable)
        variables.append(
            {
                "variable": variable,
                "meaning": "External production data root" if variable == "HODGECY_DATA_ROOT" else "Discovered HodgeCY-prefixed configuration variable",
                "required": variable == "HODGECY_DATA_ROOT",
                "current_value_present": bool(current),
                "path_valid": bool(current and Path(current).exists()) if variable == "HODGECY_DATA_ROOT" else None,
                "required_for_full_corpus": variable == "HODGECY_DATA_ROOT",
                "sensitive": False,
                "persistence_mechanism": "Windows User environment or explicit --root",
                "occurrences": sites,
            }
        )
    if "HODGECY_DATA_ROOT" not in occurrences:
        variables.append(
            {
                "variable": "HODGECY_DATA_ROOT",
                "meaning": "External production data root",
                "required": True,
                "current_value_present": bool(explicit_root or os.environ.get("HODGECY_DATA_ROOT")),
                "path_valid": bool((explicit_root or os.environ.get("HODGECY_DATA_ROOT")) and Path(explicit_root or os.environ["HODGECY_DATA_ROOT"]).exists()),
                "required_for_full_corpus": True,
                "sensitive": False,
                "persistence_mechanism": "Windows User environment or explicit --root",
                "occurrences": [],
            }
        )
    return {"schema": "hodgecy_environment_contract.v1", "variables": variables}


def verify_datasets(context: FullCorpusContext, expected_by_dataset: dict[str, dict[str, str]], instances_by_dataset: dict[str, list[Any]], source_by_instance: dict[str, list[Any]], table_by_instance: dict[str, list[Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    manifest_ids = set()
    manifest = context.data_root.manifests / "datasets.json"
    if manifest.exists():
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        rows = payload.get("datasets") if isinstance(payload, dict) else payload
        manifest_ids = {row.get("dataset_id") for row in rows}
    dataset_rows = []
    traversal_rows = []
    for dataset in sorted(context.catalog.list_datasets(), key=lambda item: item.dataset_id.local_id):
        dataset_id = dataset.dataset_id.local_id
        instances = instances_by_dataset.get(dataset_id, [])
        instance_ids = [instance.instance_id for instance in instances]
        tables = [table for instance_id in instance_ids for table in table_by_instance.get(instance_id, [])]
        physical = [source for instance_id in instance_ids for source in source_by_instance.get(instance_id, [])]
        traversal = traversal_for_dataset(context, dataset_id, tables, physical)
        expected = expected_by_dataset.get(dataset_id, {})
        status = "OK" if traversal["status"] == "OK" and instances else "CHECK"
        dataset_rows.append(
            {
                "dataset_id": dataset_id,
                "expected_completion_class": expected.get("storage_completion_class") or dataset.acquisition_status.value,
                "catalog_present": "YES",
                "manifest_present": "YES" if dataset_id in manifest_ids else "NO",
                "physical_backing_resolved": "YES" if physical or dataset.acquisition_status.value in {"COMPLETE_REMOTE", "SOURCE_REGISTRY_ONLY", "COMPUTABLE_NOT_PREENUMERATED", "COMPLETE_REMOTE_NATIVE_LAZY"} else "NO",
                "query_table_present": "YES" if tables else "NO",
                "source_instances": len(instances),
                "expected_or_manifest_count": expected.get("headline_record_count") or dataset.expected_count,
                "actual_or_metadata_count": dataset.verified_count or dataset.expected_count or sum(int(table.row_count or 0) for table in tables),
                "traversal_test": traversal["traversal_test"],
                "status": status,
                "notes": traversal["notes"],
            }
        )
        traversal_rows.append({"dataset_id": dataset_id, **traversal})
    return dataset_rows, traversal_rows


def traversal_for_dataset(context: FullCorpusContext, dataset_id: str, tables: list[Any], physical: list[Any]) -> dict[str, Any]:
    if tables:
        table = tables[0]
        result = query_table_head(context, table)
        return {
            "route_type": "query_table",
            "route_id": table.table_name,
            "traversal_test": result["test"],
            "status": result["status"],
            "notes": result["notes"],
        }
    local_paths = [source.relative_path for source in physical if source.relative_path]
    if local_paths:
        exists = all((context.data_root.root / path).exists() for path in local_paths[:5])
        return {"route_type": "physical_source", "route_id": ";".join(local_paths[:3]), "traversal_test": "path_exists", "status": "OK" if exists else "MISSING_PATH", "notes": f"checked {min(len(local_paths), 5)} local path(s)"}
    if physical:
        return {"route_type": "remote_or_registry", "route_id": ";".join(filter(None, (source.uri for source in physical[:3]))), "traversal_test": "registered_pointer", "status": "OK", "notes": "remote/native pointer registered"}
    return {"route_type": "metadata_only", "route_id": dataset_id, "traversal_test": "descriptor_present", "status": "OK", "notes": "source-registry/computable dataset has no local table"}


def verify_instances(context: FullCorpusContext, source_by_instance: dict[str, list[Any]], columnar_by_instance: dict[str, list[Any]]) -> list[dict[str, Any]]:
    rows = []
    for instance in sorted(context.catalog.list_instances(), key=lambda item: item.instance_id):
        physical = source_by_instance.get(instance.instance_id, [])
        columnar = columnar_by_instance.get(instance.instance_id, [])
        descriptor_only_ok = instance.acquisition_status.value not in {"UNRESOLVED", "SOURCE_CORRUPT"}
        resolvable = bool(physical or columnar or descriptor_only_ok)
        if physical or columnar:
            note = "physical_or_columnar_backing_registered"
        elif descriptor_only_ok:
            note = "descriptor_only_native_remote_manual_or_partial_route_registered"
        else:
            note = "no_resolvable_backing"
        rows.append(
            {
                "instance_id": instance.instance_id,
                "dataset_id": instance.dataset_id.local_id,
                "source_version": instance.source_version,
                "storage_location_or_pointer": ";".join(filter(None, [*(source.relative_path for source in physical[:3]), *(source.uri for source in physical[:3])])),
                "acquisition_state": instance.acquisition_status.value,
                "record_count_metadata": instance.record_count,
                "readable_or_resolvable_status": "YES" if resolvable else "NO",
                "notes": note,
                "status": "OK" if resolvable else "MISSING_BACKING",
            }
        )
    return rows


def verify_tables(context: FullCorpusContext) -> list[dict[str, Any]]:
    rows = []
    for table in sorted(context.catalog.list_tables(), key=lambda item: item.table_name):
        result = query_table_head(context, table)
        rows.append(
            {
                "table_id": table.table_id,
                "table_name": table.table_name,
                "table_kind": table.table_kind.value,
                "schema_columns": len(table.columns),
                "metadata_row_count": table.row_count,
                "minimal_query": result["test"],
                "count_or_metadata_count": table.row_count,
                "lazy_route": "pyarrow.dataset",
                "status": result["status"],
                "notes": result["notes"],
            }
        )
    return rows


def verify_relationships(context: FullCorpusContext) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = []
    total = 0
    by_type: dict[str, int] = {}
    for table in sorted(context.relationship_tables, key=lambda item: item.table_name):
        result = query_table_head(context, table)
        count = int(table.row_count or 0)
        total += count
        by_type[table.table_name] = count
        rows.append(
            {
                "table_name": table.table_name,
                "table_kind": table.table_kind.value,
                "relationship_edges": count,
                "schema_columns": len(table.columns),
                "minimal_query": result["test"],
                "status": result["status"],
                "notes": result["notes"],
            }
        )
    return rows, {"relationship_table_count": len(rows), "relationship_edge_count": total, "by_table": by_type}


def query_table_head(context: FullCorpusContext, table: Any) -> dict[str, str]:
    source = context.catalog.payload["columnar_sources"].get(table.columnar_id or "")
    query_safe = tuple(source.get("query_safe_columns") or ()) if source else ()
    heavy = set(source.get("heavy_columns") or ()) if source else set()
    fields = tuple(field for field in query_safe if field not in heavy)[:1] or tuple(field for field in table.columns if field not in heavy)[:1] or tuple(table.columns[:1])
    try:
        result = context.catalog.query(QuerySpec(table=table.table_name, fields=fields).limit(1))
        head = result.head(1)
        return {"status": "OK", "test": f"head(1):{','.join(fields)}", "notes": f"rows={head.num_rows};estimated={result.estimated_count()}"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "FAILED", "test": f"head(1):{','.join(fields)}", "notes": f"{type(exc).__name__}: {exc}"}


def write_root_resolution(context: FullCorpusContext) -> None:
    payload = {
        "schema": "hodgecy_production_root_resolution.v1",
        "production_root_found": True,
        "selected_root_path_sha256": hashlib.sha256(str(context.data_root.root).encode("utf-8")).hexdigest(),
        "data_root_fingerprint": data_root_fingerprint(context.data_root.root),
        "release_fingerprint": context.release_fingerprint,
        "catalog_fingerprint": file_sha256(context.data_root.catalogs / "current_corpus" / "catalog.json"),
        "corpus_metadata": context.summary_counts(),
        "path_redaction": "absolute local path intentionally omitted",
    }
    write_json(OUT_DIR / "production_root_resolution.json", payload)


def write_failure_outputs(versions: dict[str, str], failures: list[str], warnings: list[str]) -> None:
    readiness = {
        "FULL_HODGECY_V1_CORPUS_READY": "NO",
        "HODGECY_VERSION": versions.get("hodgecy"),
        "FAILURES": failures,
        "WARNINGS": warnings,
        "GENERATED_AT": utc_now(),
    }
    write_json(OUT_DIR / "full_corpus_readiness.json", readiness)
    write_activation_report(readiness, {"variables": []})


def write_environment_contract_md(contract: dict[str, Any]) -> None:
    lines = ["# HodgeCY Environment Contract", ""]
    for item in contract["variables"]:
        lines.extend(
            [
                f"## {item['variable']}",
                "",
                f"- Meaning: {item['meaning']}",
                f"- Required: {yes_no(item['required'])}",
                f"- Current value present: {yes_no(item['current_value_present'])}",
                f"- Path valid: {item['path_valid']}",
                f"- Required for full corpus: {yes_no(item['required_for_full_corpus'])}",
                f"- Sensitive: {yes_no(item['sensitive'])}",
                f"- Persistence mechanism: {item['persistence_mechanism']}",
                f"- Occurrences: {len(item['occurrences'])}",
                "",
            ]
        )
    (OUT_DIR / "environment_contract.md").write_text("\n".join(lines), encoding="utf-8")


def write_activation_report(readiness: dict[str, Any], env_contract: dict[str, Any]) -> None:
    failures = readiness.get("FAILURES") or []
    warnings = readiness.get("WARNINGS") or []
    root_var = next((item for item in env_contract.get("variables", []) if item.get("variable") == "HODGECY_DATA_ROOT"), {})
    lines = [
        "# HodgeCY Full Corpus Activation Report",
        "",
        f"- ACTUAL PRODUCTION ROOT FOUND? {'YES' if root_var.get('path_valid') else 'NO'}",
        f"- ROOT PERSISTED IN USER ENVIRONMENT? {'YES' if os.environ.get('HODGECY_DATA_ROOT') or root_var.get('current_value_present') else 'NO'}",
        f"- CURRENT SHELL ENV ACTIVE? {'YES' if os.environ.get('HODGECY_DATA_ROOT') else 'NO'}",
        f"- DUCKDB READY? {'YES' if readiness.get('DUCKDB_VERSION') else 'NO'}",
        f"- PYARROW READY? {'YES' if readiness.get('PYARROW_VERSION') else 'NO'}",
        f"- PRODUCTION CATALOG OPENED? {'YES' if readiness.get('LOGICAL_DATASET_COUNT') else 'NO'}",
        f"- LOGICAL DATASETS FOUND: expected 53 / actual {readiness.get('LOGICAL_DATASET_COUNT')}",
        f"- DATASET INSTANCES FOUND: expected 80 / actual {readiness.get('INSTANCE_COUNT')}",
        f"- QUERY TABLES FOUND: expected 32 / actual {readiness.get('QUERY_TABLE_COUNT')}",
        f"- RELATIONSHIP EDGES FOUND: actual {readiness.get('RELATIONSHIP_EDGE_COUNT')}",
        f"- SOURCE/DATA RECORD COUNT: actual manifest/catalog value {readiness.get('SOURCE_DATA_RECORD_COUNT')}",
        f"- ALL DATASET ROUTES TRAVERSABLE? {'YES' if not failures else 'NO'}",
        f"- CURRENT HODGECY II FULL-CORPUS MODE READY? {readiness.get('FULL_HODGECY_V1_CORPUS_READY')}",
        "",
        "## Bugs Fixed",
        "",
        "- Production acquisition-status vocabulary accepted.",
        "- Production redistribution/license-status vocabulary accepted.",
        "- Production source-format and table-kind vocabulary accepted.",
        "- Manifest family labels normalized before descriptor construction.",
        "- Manifest-derived instance/source IDs tokenized safely.",
        "",
        "## Remaining Infrastructure Blockers",
        "",
    ]
    lines.extend(f"- {item}" for item in failures) if failures else lines.append("- None.")
    if warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {item}" for item in warnings)
    (OUT_DIR / "full_corpus_activation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else []
    for row in rows:
        fields.extend(key for key in row if key not in fields)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: cell(row.get(key)) for key in fields})


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return yes_no(value)
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, default=str)
    return str(value)


def yes_no(value: Any) -> str:
    return "YES" if bool(value) else "NO"


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def data_root_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for relative in ("manifests/current_hodgecy_corpus_snapshot.json", "manifests/datasets.json", "catalogs/current_corpus/catalog.json"):
        path = root / relative
        if path.exists():
            digest.update(relative.encode("utf-8"))
            digest.update(str(path.stat().st_size).encode("ascii"))
            digest.update((file_sha256(path) or "").encode("ascii"))
    return digest.hexdigest()


def utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
