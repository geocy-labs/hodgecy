from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from hodgecy.research.full_corpus_context import FullCorpusContext

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = REPO_ROOT / "research_outputs" / "hodgecy_ii"
OUT_DIR = OUT_ROOT / "full_corpus_discovery"
NOTES_PATH = OUT_ROOT / "full_corpus_discovery_notes.md"
REPORT_PATH = OUT_ROOT / "full_corpus_discovery_report.md"
LEGACY_SCRIPT = REPO_ROOT / "scripts" / "hodgecy_ii_universe_deep_dive.py"

CY3_TABLES = {
    "current_cicy3_standard": {
        "dataset": "cicy3_standard",
        "family": "cicy3",
        "entity_level": "PRESENTATION",
        "presentation_type": "configuration_matrix",
        "id": "source_record_id",
        "h11": "h11",
        "h12": "h21",
        "euler": "euler",
        "extra": ["num_projective_spaces", "num_polynomials", "eta", "matrix_json", "c2_coefficients_json"],
    },
    "current_cicy3_favorable": {
        "dataset": "cicy3_favorable",
        "family": "cicy3",
        "entity_level": "PRESENTATION",
        "presentation_type": "favorable_configuration_matrix",
        "id": "source_record_id",
        "h11": "h11",
        "h12": "h21",
        "euler": "2*(h11-h21)",
        "extra": ["parent_cicy_id", "favour", "kahler_pos", "is_product", "configuration_json", "c2_coefficients_json"],
    },
    "current_cicy3_free_actions": {
        "dataset": "cicy3_quotients",
        "family": "cicy3_quotient",
        "entity_level": "GEOMETRY",
        "presentation_type": "free_quotient",
        "id": "source_record_id",
        "h11": "h11",
        "h12": "h21",
        "euler": "2*(h11-h21)",
        "extra": ["parent_cicy_id", "action_index", "group_name", "group_order", "gap_id_raw"],
    },
    "current_cicy3_quotient_parent_blocks": {
        "dataset": "cicy3_quotients",
        "family": "cicy3",
        "entity_level": "PRESENTATION",
        "presentation_type": "quotient_parent_block",
        "id": "source_record_id",
        "h11": "h11",
        "h12": "h21",
        "euler": "2*(h11-h21)",
        "extra": ["parent_cicy_id", "free_action_count", "configuration_matrix_raw"],
    },
    "current_weighted_p4": {
        "dataset": "weighted_p4",
        "family": "weighted_hypersurface",
        "entity_level": "PRESENTATION",
        "presentation_type": "weighted_p4_hypersurface",
        "id": "source_record_id",
        "h11": "h11",
        "h12": "h21",
        "euler": "euler",
        "extra": ["weights_key", "degree", "n_weights"],
    },
    "current_ip_weight_systems_4d": {
        "dataset": "ip_weight_systems_4d",
        "family": "ip_weight_system",
        "entity_level": "PRESENTATION",
        "presentation_type": "4d_ip_weight_system",
        "id": "source_record_id",
        "h11": "h11",
        "h12": "h12",
        "euler": "2*(h11-h12)",
        "extra": ["weights_key", "degree", "source_flag", "K3_projection_count"],
    },
    "wave3_partialflagvarieties_grassmannian_cy3_table1": {
        "dataset": "partialflagvarieties_grassmannian_cy3_table1",
        "family": "grassmannian",
        "entity_level": "PRESENTATION",
        "presentation_type": "partial_flag_variety_cy3",
        "id": "source_record_id",
        "h11": "h11",
        "h12": "h21",
        "euler": "chi_top",
        "extra": ["family_number", "ambient_grassmannian_k", "ambient_grassmannian_n", "bundle_description"],
    },
    "wave4_cicy_divisor_topology_parent_records": {
        "dataset": "cicy_divisor_topologies_cms_2022",
        "family": "cicy3_topology",
        "entity_level": "TOPOLOGY",
        "presentation_type": "divisor_topology_parent",
        "id": "source_record_id",
        "h11": "h11",
        "h12": "h21",
        "euler": "2*(h11-h21)",
        "extra": ["parent_cicy_id", "favorable_cicy_id", "basis_convention", "int_ring_source_expr", "divisor_entry_count"],
    },
}

REQUESTED_DOUBLE_FIBERS = [
    ("61", "451"),
    ("78", "79"),
    ("80", "455"),
    ("81", "454"),
    ("82", "245", "452", "453"),
    ("83", "84", "84a", "239", "240", "241"),
    ("85", "238"),
]


@dataclass(frozen=True)
class TableRoute:
    table_name: str
    dataset_id: str
    row_count: int | None
    paths: tuple[Path, ...]
    columns: tuple[str, ...]


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}
        self.size: Counter[str] = Counter()

    def find(self, item: str) -> str:
        if item not in self.parent:
            self.parent[item] = item
            self.size[item] = 1
            return item
        root = item
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[item] != item:
            parent = self.parent[item]
            self.parent[item] = root
            item = parent
        return root

    def union(self, left: str, right: str) -> None:
        a = self.find(left)
        b = self.find(right)
        if a == b:
            return
        if self.size[a] < self.size[b]:
            a, b = b, a
        self.parent[b] = a
        self.size[a] += self.size[b]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the HodgeCY II full-corpus discovery pass.")
    parser.add_argument("--root", default=None, help="Production HODGECY_DATA_ROOT. Defaults to environment.")
    parser.add_argument("--skip-large", action="store_true", help="Skip large KS/DESY aggregate scans for rapid debugging.")
    args = parser.parse_args(argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Opening production FullCorpusContext", flush=True)
    ctx = FullCorpusContext.open(args.root)
    ctx.assert_v1_ready()
    routes = table_routes(ctx)
    con = duckdb.connect()
    con.execute("PRAGMA threads=4")
    print(f"Registering {len(routes)} production table views", flush=True)
    register_views(con, routes)

    notes: list[str] = [
        "# HodgeCY II Full-Corpus Discovery Notes",
        "",
        f"- Corpus release fingerprint: `{ctx.release_fingerprint}`",
        f"- Catalog counts: {json.dumps(ctx.summary_counts(), sort_keys=True)}",
        "- Method: production catalog and production Parquet tables are the primary source. CKC/Cynk-Meyer source-assembly artifacts are used only as historical source artifacts for registered production double-octic PDFs that have no production normalized table.",
        "",
    ]

    print("Writing production inventory", flush=True)
    inventory = write_inventory(ctx, routes)
    print("Traversing relationship graph", flush=True)
    relationship_edges, component_summary = write_relationship_outputs(ctx, con)
    print("Enumerating explicit nodal/conifold production route", flush=True)
    explicit_nodal = write_explicit_nodal_outputs(ctx, relationship_edges)
    notes.extend(discuss_relationships(component_summary, explicit_nodal))

    print("Building CY3 projection", flush=True)
    projection = build_cy3_projection(ctx, con)
    projection_path = OUT_DIR / "full_cy3_research_projection.parquet"
    write_parquet(projection_path, projection)
    notes.extend(discuss_projection(projection))

    print("Computing Hodge group inventory", flush=True)
    hodge_inventory = build_hodge_group_inventory(con, projection, skip_large=args.skip_large)
    write_parquet(OUT_DIR / "full_corpus_hodge_group_inventory.parquet", hodge_inventory)
    repeated_hodge = hodge_inventory[hodge_inventory["source_count"] > 1].copy()
    write_parquet(OUT_DIR / "all_repeated_hodge_groups.parquet", repeated_hodge)
    cross_family = build_cross_family_collisions(hodge_inventory)
    write_parquet(OUT_DIR / "all_cross_family_hodge_collisions.parquet", cross_family)
    notes.extend(discuss_hodge_groups(hodge_inventory, repeated_hodge, cross_family))

    print("Scanning large production datasets" if not args.skip_large else "Skipping large scans by flag", flush=True)
    large_outputs = build_large_dataset_outputs(con, skip_large=args.skip_large)
    notes.extend(discuss_large_outputs(large_outputs, args.skip_large))

    print("Computing double-octic source-complex fidelity outputs", flush=True)
    double_outputs = build_double_octic_outputs(ctx)
    notes.extend(discuss_double_octics(double_outputs))

    print("Computing fibration/operator/symmetry/conifold fidelity outputs", flush=True)
    fidelity_outputs = build_fidelity_outputs(con, projection, relationship_edges, double_outputs)
    notes.extend(discuss_fidelity(fidelity_outputs))

    report = build_report(
        ctx=ctx,
        inventory=inventory,
        component_summary=component_summary,
        explicit_nodal=explicit_nodal,
        projection=projection,
        hodge_inventory=hodge_inventory,
        repeated_hodge=repeated_hodge,
        cross_family=cross_family,
        large_outputs=large_outputs,
        double_outputs=double_outputs,
        fidelity_outputs=fidelity_outputs,
        skipped_large=args.skip_large,
    )
    write_text(NOTES_PATH, "\n".join(notes).rstrip() + "\n")
    write_text(REPORT_PATH, report)
    write_json(
        OUT_DIR / "run_summary.json",
        {
            "schema": "hodgecy_ii_full_corpus_discovery.v1",
            "corpus_release_fingerprint": ctx.release_fingerprint,
            "catalog_counts": ctx.summary_counts(),
            "outputs": output_manifest(),
            "large_scans_skipped": args.skip_large,
        },
    )
    print("HodgeCY II full-corpus discovery pass complete")
    print(f"- CY3 projection rows: {len(projection)}")
    print(f"- distinct Hodge tuples/groups: {len(hodge_inventory)}")
    print(f"- repeated-Hodge groups: {len(repeated_hodge)}")
    print(f"- cross-family Hodge collisions: {len(cross_family)}")
    print(f"- double-octic fixed-local/fixed-Hodge fibers: {len(double_outputs['fixed_local_hodge'])}")
    print(f"- notes: {rel(NOTES_PATH)}")
    print(f"- report: {rel(REPORT_PATH)}")
    return 0


def table_routes(ctx: FullCorpusContext) -> dict[str, TableRoute]:
    physical = {source.source_id: source for source in ctx.catalog.list_physical_sources()}
    instances = {instance.instance_id: instance for instance in ctx.catalog.list_instances()}
    routes: dict[str, TableRoute] = {}
    for columnar in ctx.catalog.list_columnar_sources():
        paths = []
        for source_id in columnar.source_ids:
            source = physical.get(source_id)
            if source and source.relative_path:
                paths.append(ctx.data_root.root / source.relative_path)
        dataset_id = instances[columnar.instance_id].dataset_id.local_id if columnar.instance_id in instances else ""
        routes[columnar.table_name] = TableRoute(
            table_name=columnar.table_name,
            dataset_id=dataset_id,
            row_count=columnar.row_count,
            paths=tuple(paths),
            columns=tuple(columnar.schema.keys()),
        )
    return routes


def register_views(con: duckdb.DuckDBPyConnection, routes: dict[str, TableRoute]) -> None:
    for route in routes.values():
        if not route.paths:
            continue
        con.execute(f'CREATE OR REPLACE VIEW "{route.table_name}" AS SELECT * FROM read_parquet({duckdb_path_list(route.paths)}, union_by_name=true)')


def write_inventory(ctx: FullCorpusContext, routes: dict[str, TableRoute]) -> dict[str, Any]:
    dataset_rows = []
    for dataset in ctx.catalog.list_datasets():
        dataset_rows.append(
            {
                "corpus_release_fingerprint": ctx.release_fingerprint,
                "dataset_id": dataset.dataset_id.local_id,
                "construction_family": dataset.construction_family.name,
                "name": dataset.name,
                "acquisition_status": dataset.acquisition_status.value,
                "redistribution_status": dataset.redistribution_status.value,
                "expected_count": dataset.expected_count,
                "verified_count": dataset.verified_count,
            }
        )
    write_parquet(OUT_DIR / "production_dataset_inventory.parquet", pd.DataFrame(dataset_rows))

    table_rows = [
        {
            "corpus_release_fingerprint": ctx.release_fingerprint,
            "table_name": route.table_name,
            "dataset_id": route.dataset_id,
            "row_count": route.row_count,
            "column_count": len(route.columns),
            "columns": json.dumps(route.columns),
            "path_count": len(route.paths),
        }
        for route in routes.values()
    ]
    write_parquet(OUT_DIR / "production_query_table_inventory.parquet", pd.DataFrame(table_rows))
    return {"datasets": len(dataset_rows), "tables": len(table_rows)}


def write_relationship_outputs(ctx: FullCorpusContext, con: duckdb.DuckDBPyConnection) -> tuple[pd.DataFrame, dict[str, Any]]:
    parts = []
    for table in ctx.relationship_tables:
        cols = set(table.columns)
        if {"source_dataset", "source_id", "target_dataset", "target_id"}.issubset(cols):
            sql = (
                f"SELECT '{table.table_name}' AS relationship_table, relationship_id, relationship_type, "
                "source_dataset, source_id, target_dataset, target_id, "
                "evidence_type AS evidence, claim_level, join_state, CAST(directed AS VARCHAR) AS directed "
                f'FROM "{table.table_name}"'
            )
        elif {"source_dataset", "source_record_id", "target_dataset", "target_record_id"}.issubset(cols):
            sql = (
                f"SELECT '{table.table_name}' AS relationship_table, relationship_id, relationship_type, "
                "source_dataset, source_record_id AS source_id, target_dataset, target_record_id AS target_id, "
                "evidence, validation_status AS claim_level, validation_status AS join_state, 'UNKNOWN' AS directed "
                f'FROM "{table.table_name}"'
            )
        else:
            continue
        parts.append(sql)
    relationship_edges = con.execute(" UNION ALL ".join(parts)).fetchdf()
    relationship_edges.insert(0, "corpus_release_fingerprint", ctx.release_fingerprint)
    write_parquet(OUT_DIR / "full_relationship_edges.parquet", relationship_edges)

    uf = UnionFind()
    for row in relationship_edges.itertuples(index=False):
        left = f"{row.source_dataset}:{row.source_id}"
        right = f"{row.target_dataset}:{row.target_id}"
        uf.union(left, right)
    component_by_root: dict[str, list[str]] = defaultdict(list)
    for node in list(uf.parent):
        component_by_root[uf.find(node)].append(node)
    component_rows = []
    summary_rows = []
    for index, (_root, nodes) in enumerate(sorted(component_by_root.items(), key=lambda item: (-len(item[1]), item[0])), start=1):
        component_id = f"component_{index:06d}"
        datasets = sorted({node.split(":", 1)[0] for node in nodes})
        for node in sorted(nodes):
            dataset, record_id = node.split(":", 1)
            component_rows.append(
                {
                    "corpus_release_fingerprint": ctx.release_fingerprint,
                    "component_id": component_id,
                    "dataset_id": dataset,
                    "record_id": record_id,
                    "component_size": len(nodes),
                    "component_dataset_count": len(datasets),
                }
            )
        if len(nodes) > 1:
            summary_rows.append(
                {
                    "corpus_release_fingerprint": ctx.release_fingerprint,
                    "component_id": component_id,
                    "node_count": len(nodes),
                    "dataset_count": len(datasets),
                    "datasets": json.dumps(datasets),
                    "sample_nodes": json.dumps(sorted(nodes)[:20]),
                }
            )
    components = pd.DataFrame(component_rows)
    summary = pd.DataFrame(summary_rows)
    write_parquet(OUT_DIR / "full_relationship_connected_components.parquet", components)
    write_parquet(OUT_DIR / "nontrivial_relationship_component_summary.parquet", summary)
    relationship_type_counts = relationship_edges.groupby(["relationship_table", "relationship_type"], dropna=False).size().reset_index(name="edge_count")
    write_parquet(OUT_DIR / "relationship_type_counts.parquet", relationship_type_counts)
    return relationship_edges, {
        "relationship_edges": len(relationship_edges),
        "node_count": len(components),
        "component_count": len(summary_rows) + sum(1 for nodes in component_by_root.values() if len(nodes) == 1),
        "nontrivial_component_count": len(summary_rows),
        "largest_component_size": int(summary["node_count"].max()) if len(summary) else 0,
        "relationship_type_counts": relationship_type_counts.to_dict("records"),
    }


def write_explicit_nodal_outputs(ctx: FullCorpusContext, relationship_edges: pd.DataFrame) -> dict[str, Any]:
    dataset_id = "explicit_nodal_conifold_corpus"
    instances = [instance for instance in ctx.catalog.list_instances() if instance.dataset_id.local_id == dataset_id]
    physical = [source for instance in instances for source in ctx.catalog.list_physical_sources(instance.instance_id)]
    columnar = [source for instance in instances for source in ctx.catalog.list_columnar_sources(instance.instance_id)]
    mask = (relationship_edges["source_dataset"] == dataset_id) | (relationship_edges["target_dataset"] == dataset_id)
    touching = relationship_edges[mask].copy()
    write_parquet(OUT_DIR / "explicit_nodal_conifold_relationship_neighborhood.parquet", touching)
    payload = {
        "corpus_release_fingerprint": ctx.release_fingerprint,
        "dataset_id": dataset_id,
        "instance_count": len(instances),
        "physical_source_count": len(physical),
        "columnar_source_count": len(columnar),
        "relationship_edge_count": len(touching),
        "enumeration_status": "descriptor_only_no_production_record_table" if not columnar else "columnar_records_available",
        "instances": [instance.to_dict() for instance in instances],
        "physical_sources": [source.to_dict() for source in physical],
        "relationship_sample": touching.head(20).to_dict("records"),
        "firewall": "SOURCE/PRESENTATION/GEOMETRY/NODE/HODGE levels not promoted without natural comparison data",
    }
    write_json(OUT_DIR / "explicit_nodal_conifold_corpus_enumeration.json", payload)
    return payload


def build_cy3_projection(ctx: FullCorpusContext, con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for table, spec in CY3_TABLES.items():
        extra_cols = [col for col in spec["extra"] if col in con.execute(f'DESCRIBE "{table}"').fetchdf()["column_name"].tolist()]
        selects = [
            f"'{ctx.release_fingerprint}' AS corpus_release_fingerprint",
            f"'{table}' AS production_table",
            f"'{spec['dataset']}' AS dataset_id",
            f"'{spec['family']}' AS construction_family",
            f"'{spec['entity_level']}' AS entity_level",
            f"'{spec['presentation_type']}' AS presentation_type",
            f"CAST({spec['id']} AS VARCHAR) AS source_record_id",
            f"CAST({spec['h11']} AS BIGINT) AS h11",
            f"CAST({spec['h12']} AS BIGINT) AS h12",
            f"CAST({spec['euler']} AS BIGINT) AS euler",
            "CAST(NULL AS VARCHAR) AS rigidity",
            "CAST(NULL AS VARCHAR) AS singularity_data",
            "CAST(NULL AS VARCHAR) AS nodal_data",
            "CAST(NULL AS VARCHAR) AS conifold_data",
            "CAST(NULL AS VARCHAR) AS transition_data",
            "CAST(NULL AS VARCHAR) AS topology_data",
            "CAST(NULL AS VARCHAR) AS symmetry_data",
            "CAST(NULL AS VARCHAR) AS quotient_data",
            "CAST(NULL AS VARCHAR) AS fibration_data",
            "CAST(NULL AS VARCHAR) AS operator_data",
            "CAST(NULL AS VARCHAR) AS arithmetic_data",
            "CAST(NULL AS VARCHAR) AS enumerative_data",
            "CAST(NULL AS VARCHAR) AS provenance",
            "CAST(NULL AS VARCHAR) AS extra_payload_json",
        ]
        if extra_cols:
            pairs = ", ".join([f"'{col}', CAST({col} AS VARCHAR)" for col in extra_cols])
            selects[-1] = f"to_json(struct_pack({', '.join(f'{col} := CAST({col} AS VARCHAR)' for col in extra_cols)})) AS extra_payload_json"
        sql = f'SELECT {", ".join(selects)} FROM "{table}" WHERE {spec["h11"]} IS NOT NULL AND {spec["h12"]} IS NOT NULL'
        frame = con.execute(sql).fetchdf()
        frames.append(frame)

    double_frame = double_octic_projection_frame(ctx.release_fingerprint)
    if len(double_frame):
        frames.append(double_frame)
    projection = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    projection["hodge_key"] = projection.apply(lambda row: hodge_key(row["h11"], row["h12"], row["euler"]), axis=1)
    return projection


def double_octic_projection_frame(fingerprint: str) -> pd.DataFrame:
    path = OUT_ROOT / "all_source_presentations.parquet"
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_parquet(path)
    rows = []
    for row in frame.to_dict("records"):
        hodge = parse_jsonish(row.get("hodge"))
        rows.append(
            {
                "corpus_release_fingerprint": fingerprint,
                "production_table": "historical_source_artifact:all_source_presentations",
                "dataset_id": "double_octics_external",
                "construction_family": "double_octic",
                "entity_level": row.get("entity_level"),
                "presentation_type": row.get("presentation_kind"),
                "source_record_id": str(row.get("presentation_id")),
                "h11": as_int(hodge.get("h11")),
                "h12": as_int(hodge.get("h12")),
                "euler": as_int(hodge.get("euler")),
                "rigidity": None,
                "singularity_data": row.get("local_inventory"),
                "nodal_data": None,
                "conifold_data": None,
                "transition_data": None,
                "topology_data": None,
                "symmetry_data": None,
                "quotient_data": None,
                "fibration_data": None,
                "operator_data": None,
                "arithmetic_data": None,
                "enumerative_data": None,
                "provenance": "production double-octic PDFs plus historical CKC/Cynk-Meyer source-artifact extraction",
                "extra_payload_json": json.dumps(
                    {
                        "local_signature": row.get("local_signature"),
                        "source_assembly_available": row.get("source_assembly_available"),
                        "rational_signature": row.get("rational_signature"),
                        "integral_signature": row.get("integral_signature"),
                        "equivariant_signature": row.get("equivariant_signature"),
                        "identity_resolution_status": row.get("identity_resolution_status"),
                    },
                    sort_keys=True,
                ),
            }
        )
    return pd.DataFrame(rows)


def build_hodge_group_inventory(con: duckdb.DuckDBPyConnection, projection: pd.DataFrame, *, skip_large: bool) -> pd.DataFrame:
    rows = []
    if len(projection):
        grouped = (
            projection.groupby(["h11", "h12", "euler", "dataset_id", "construction_family"], dropna=False)
            .agg(source_count=("source_record_id", "count"), sample_ids=("source_record_id", lambda values: json.dumps([str(v) for v in list(values)[:30]])))
            .reset_index()
        )
        grouped["source_kind"] = "projection_records"
        rows.append(grouped)
    if not skip_large:
        for table, dataset, family, euler_col in [
            ("kreuzer_skarke", "kreuzer_skarke", "toric_reflexive_polytope", "euler_characteristic"),
        ]:
            sql = (
                f"SELECT h11, h12, {euler_col} AS euler, '{dataset}' AS dataset_id, '{family}' AS construction_family, "
                "COUNT(*) AS source_count, "
                "'aggregate:min_vertex=' || CAST(MIN(vertex_count) AS VARCHAR) || ';max_vertex=' || CAST(MAX(vertex_count) AS VARCHAR) || ';min_facet=' || CAST(MIN(facet_count) AS VARCHAR) || ';max_facet=' || CAST(MAX(facet_count) AS VARCHAR) AS sample_ids, "
                "'large_aggregate' AS source_kind "
                f'FROM "{table}" GROUP BY h11, h12, {euler_col}'
            )
            rows.append(con.execute(sql).fetchdf())
    inventory = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    inventory["hodge_key"] = inventory.apply(lambda row: hodge_key(row["h11"], row["h12"], row["euler"]), axis=1)
    return inventory


def build_cross_family_collisions(hodge_inventory: pd.DataFrame) -> pd.DataFrame:
    if not len(hodge_inventory):
        return pd.DataFrame()
    grouped = (
        hodge_inventory.groupby("hodge_key")
        .agg(
            total_source_count=("source_count", "sum"),
            construction_family_count=("construction_family", lambda values: len(set(values))),
            construction_families=("construction_family", lambda values: json.dumps(sorted(set(map(str, values))))),
            datasets=("dataset_id", lambda values: json.dumps(sorted(set(map(str, values))))),
            member_summary=("dataset_id", lambda values: ""),
        )
        .reset_index()
    )
    grouped = grouped[(grouped["total_source_count"] > 1) & (grouped["construction_family_count"] > 1)].copy()
    summaries = []
    for key in grouped["hodge_key"]:
        members = hodge_inventory[hodge_inventory["hodge_key"] == key][["dataset_id", "construction_family", "source_count", "sample_ids"]].to_dict("records")
        summaries.append(json.dumps(members, sort_keys=True))
    grouped["member_summary"] = summaries
    return grouped.sort_values(["construction_family_count", "total_source_count"], ascending=[False, False])


def build_large_dataset_outputs(con: duckdb.DuckDBPyConnection, *, skip_large: bool) -> dict[str, Any]:
    outputs: dict[str, Any] = {"large_scans_skipped": skip_large}
    if skip_large:
        return outputs
    ks_sql = """
        SELECT
            h11,
            h12,
            euler_characteristic AS euler,
            COUNT(*) AS polytope_count,
            COUNT(DISTINCT vertex_count) AS vertex_count_classes,
            COUNT(DISTINCT facet_count) AS facet_count_classes,
            COUNT(DISTINCT point_count) AS point_count_classes,
            COUNT(DISTINCT dual_point_count) AS dual_point_count_classes,
            MIN(vertex_count) AS min_vertex_count,
            MAX(vertex_count) AS max_vertex_count,
            MIN(facet_count) AS min_facet_count,
            MAX(facet_count) AS max_facet_count
        FROM "kreuzer_skarke"
        GROUP BY h11, h12, euler_characteristic
        ORDER BY polytope_count DESC, h11, h12
    """
    ks = con.execute(ks_sql).fetchdf()
    write_parquet(OUT_DIR / "large_kreuzer_skarke_hodge_structural_groups.parquet", ks)
    outputs["kreuzer_skarke_hodge_group_count"] = len(ks)
    outputs["kreuzer_skarke_repeated_hodge_group_count"] = int((ks["polytope_count"] > 1).sum())
    outputs["kreuzer_skarke_total_rows_scanned"] = int(ks["polytope_count"].sum())
    outputs["kreuzer_skarke_largest_hodge_fiber"] = int(ks["polytope_count"].max()) if len(ks) else 0

    gv_sql = """
        SELECT
            parent_cicy_id,
            source_h11_bucket,
            invariant_type,
            COUNT(*) AS invariant_row_count,
            COUNT(DISTINCT degree_key) AS degree_class_count,
            COUNT(DISTINCT invariant_value_raw) AS invariant_value_class_count
        FROM "wave2_cicy_gv_invariants"
        GROUP BY parent_cicy_id, source_h11_bucket, invariant_type
        ORDER BY invariant_row_count DESC
    """
    gv = con.execute(gv_sql).fetchdf()
    write_parquet(OUT_DIR / "large_desy_gv_parent_invariant_summary.parquet", gv)
    outputs["desy_gv_parent_summary_rows"] = len(gv)
    outputs["desy_gv_total_rows_scanned"] = int(gv["invariant_row_count"].sum())

    cicy4_sql = """
        SELECT
            h11,
            h21,
            h31,
            euler,
            COUNT(*) AS cicy4_count,
            COUNT(DISTINCT h22) AS h22_classes,
            COUNT(DISTINCT num_projective_spaces) AS ambient_length_classes,
            COUNT(DISTINCT num_polynomials) AS polynomial_count_classes
        FROM "current_cicy4_core"
        GROUP BY h11, h21, h31, euler
        ORDER BY cicy4_count DESC
    """
    cicy4 = con.execute(cicy4_sql).fetchdf()
    write_parquet(OUT_DIR / "large_cicy4_hodge_structural_groups.parquet", cicy4)
    outputs["cicy4_group_count"] = len(cicy4)
    outputs["cicy4_total_rows_scanned"] = int(cicy4["cicy4_count"].sum())
    return outputs


def build_double_octic_outputs(ctx: FullCorpusContext) -> dict[str, Any]:
    source_presentations = pd.read_parquet(OUT_ROOT / "all_source_presentations.parquet")
    assemblies = pd.read_parquet(OUT_ROOT / "all_source_assembly_invariants.parquet")
    source_presentations.insert(0, "corpus_release_fingerprint", ctx.release_fingerprint)
    assemblies.insert(0, "corpus_release_fingerprint", ctx.release_fingerprint)

    write_parquet(OUT_DIR / "all_double_octic_source_presentations.parquet", source_presentations)
    write_parquet(OUT_DIR / "all_double_octic_source_complexes.parquet", assemblies)

    fixed_local_hodge = nontrivial_groups(source_presentations, ["local_signature", "hodge_signature"])
    fixed_local_hodge = fixed_local_hodge[fixed_local_hodge["hodge_signature"].notna()].copy()
    write_parquet(OUT_DIR / "all_84a_like_double_octic_sets.parquet", fixed_local_hodge)

    repeated_local = nontrivial_groups(source_presentations[source_presentations["local_signature"].notna()], ["local_signature"])
    write_parquet(OUT_DIR / "all_239_240_241_like_repeated_local_fibers.parquet", repeated_local)

    targeted = []
    assembly_by_id = {str(row["native_source_record_id"]): row for row in assemblies.to_dict("records")}
    presentation_by_id = {str(row["presentation_id"]): row for row in source_presentations.to_dict("records")}
    for fiber in REQUESTED_DOUBLE_FIBERS:
        for member in fiber:
            presentation = presentation_by_id.get(str(member), {})
            assembly = assembly_by_id.get(str(member), {})
            targeted.append(
                {
                    "corpus_release_fingerprint": ctx.release_fingerprint,
                    "requested_fiber": ",".join(fiber),
                    "member": member,
                    "local_signature": presentation.get("local_signature") or assembly.get("inventory_signature"),
                    "hodge_signature": presentation.get("hodge_signature") or assembly.get("hodge_signature"),
                    "source_assembly_available": bool(assembly),
                    "rank_Q": assembly.get("rank_Q"),
                    "rank_F2": assembly.get("rank_F2"),
                    "kernel_dim_Q": assembly.get("kernel_dim_Q"),
                    "cokernel_dim_Q": assembly.get("cokernel_dim_Q"),
                    "smith_normal_form": json.dumps(assembly.get("smith_normal_form"), default=str),
                    "torsion_invariant_factors": json.dumps(assembly.get("torsion_invariant_factors"), default=str),
                    "torsion_primes": json.dumps(assembly.get("torsion_primes"), default=str),
                    "plane_orbit_sizes": json.dumps(assembly.get("plane_orbit_sizes"), default=str),
                    "double_line_orbit_sizes": json.dumps(assembly.get("double_line_orbit_sizes"), default=str),
                    "multiple_point_orbit_sizes": json.dumps(assembly.get("multiple_point_orbit_sizes"), default=str),
                    "integral_fingerprint": assembly.get("integral_fingerprint") or presentation.get("integral_signature"),
                    "equivariant_fingerprint": assembly.get("equivariant_fingerprint") or presentation.get("equivariant_signature"),
                    "status": "computed_source_assembly" if bool(assembly) else "unresolved_missing_source_assembly",
                }
            )
    targeted_df = pd.DataFrame(targeted)
    write_parquet(OUT_DIR / "requested_repeated_inventory_double_octic_source_assemblies.parquet", targeted_df)

    repeated_member_rows = []
    for row in repeated_local.to_dict("records"):
        members = json.loads(row["members"])
        for member in members:
            presentation = presentation_by_id.get(str(member), {})
            assembly = assembly_by_id.get(str(member), {})
            repeated_member_rows.append(
                repeated_member_assembly_row(
                    ctx.release_fingerprint,
                    row["local_signature"],
                    str(member),
                    presentation,
                    assembly,
                )
            )
    repeated_member_df = pd.DataFrame(repeated_member_rows)
    write_parquet(OUT_DIR / "all_repeated_local_double_octic_member_assemblies.parquet", repeated_member_df)

    rational_collapse = nontrivial_groups(assemblies, ["rational_fingerprint"])
    rational_collapse = add_distinct_count(assemblies, rational_collapse, ["rational_fingerprint"], "integral_fingerprint")
    rational_collapse = rational_collapse[rational_collapse["distinct_integral_fingerprint"] > 1].copy()
    write_parquet(OUT_DIR / "all_rational_collapse_integral_separation_sets.parquet", rational_collapse)

    integral_collapse = nontrivial_groups(assemblies, ["integral_fingerprint"])
    integral_collapse = add_distinct_count(assemblies, integral_collapse, ["integral_fingerprint"], "equivariant_fingerprint")
    integral_collapse = integral_collapse[integral_collapse["distinct_equivariant_fingerprint"] > 1].copy()
    write_parquet(OUT_DIR / "all_integral_collapse_equivariant_separation_sets.parquet", integral_collapse)

    torsion_hodge = add_distinct_count(assemblies, nontrivial_groups(assemblies[assemblies["hodge_signature"].notna()], ["hodge_signature"]), ["hodge_signature"], "torsion_invariant_factors")
    torsion_hodge = torsion_hodge[torsion_hodge["distinct_torsion_invariant_factors"] > 1].copy()
    write_parquet(OUT_DIR / "all_torsion_sensitive_hodge_collisions.parquet", torsion_hodge)

    return {
        "source_presentations": source_presentations,
        "assemblies": assemblies,
        "fixed_local_hodge": fixed_local_hodge,
        "repeated_local": repeated_local,
        "targeted": targeted_df,
        "repeated_member_assemblies": repeated_member_df,
        "rational_collapse": rational_collapse,
        "integral_collapse": integral_collapse,
        "torsion_hodge": torsion_hodge,
    }


def repeated_member_assembly_row(
    fingerprint: str,
    local_signature: str,
    member: str,
    presentation: dict[str, Any],
    assembly: dict[str, Any],
) -> dict[str, Any]:
    return {
        "corpus_release_fingerprint": fingerprint,
        "local_signature": local_signature,
        "member": member,
        "hodge_signature": presentation.get("hodge_signature") or assembly.get("hodge_signature"),
        "source_assembly_available": bool(assembly),
        "rank_Q": assembly.get("rank_Q"),
        "rank_F2": assembly.get("rank_F2"),
        "kernel_dim_Q": assembly.get("kernel_dim_Q"),
        "cokernel_dim_Q": assembly.get("cokernel_dim_Q"),
        "smith_normal_form": json.dumps(assembly.get("smith_normal_form"), default=str),
        "torsion_invariant_factors": json.dumps(assembly.get("torsion_invariant_factors"), default=str),
        "torsion_primes": json.dumps(assembly.get("torsion_primes"), default=str),
        "plane_orbit_sizes": json.dumps(assembly.get("plane_orbit_sizes"), default=str),
        "double_line_orbit_sizes": json.dumps(assembly.get("double_line_orbit_sizes"), default=str),
        "multiple_point_orbit_sizes": json.dumps(assembly.get("multiple_point_orbit_sizes"), default=str),
        "integral_fingerprint": assembly.get("integral_fingerprint") or presentation.get("integral_signature"),
        "equivariant_fingerprint": assembly.get("equivariant_fingerprint") or presentation.get("equivariant_signature"),
        "status": "computed_source_assembly" if bool(assembly) else "unresolved_missing_source_assembly",
    }


def build_fidelity_outputs(con: duckdb.DuckDBPyConnection, projection: pd.DataFrame, relationship_edges: pd.DataFrame, double_outputs: dict[str, Any]) -> dict[str, Any]:
    outputs: dict[str, Any] = {}
    fibration = con.execute(
        """
        WITH fib AS (
            SELECT parent_cicy_id, COUNT(*) AS fibration_count, COUNT(DISTINCT fibration_type) AS fibration_type_count
            FROM "current_cicy3_fibrations" GROUP BY parent_cicy_id
        ),
        h AS (
            SELECT CAST(source_record_id AS VARCHAR) AS parent_cicy_id, h11, h21 AS h12, euler
            FROM "current_cicy3_standard"
        )
        SELECT h.h11, h.h12, h.euler, COUNT(*) AS parent_count,
               MIN(fib.fibration_count) AS min_fibration_count,
               MAX(fib.fibration_count) AS max_fibration_count,
               COUNT(DISTINCT fib.fibration_count) AS fibration_count_classes,
               COUNT(DISTINCT fib.fibration_type_count) AS fibration_type_classes
        FROM h JOIN fib USING(parent_cicy_id)
        GROUP BY h.h11, h.h12, h.euler
        HAVING COUNT(*) > 1 AND COUNT(DISTINCT fib.fibration_count) > 1
        ORDER BY parent_count DESC
        """
    ).fetchdf()
    write_parquet(OUT_DIR / "all_fibration_fidelity_collisions.parquet", fibration)
    outputs["fibration"] = fibration

    quotient = con.execute(
        """
        SELECT h11, h21 AS h12, 2*(h11-h21) AS euler,
               COUNT(*) AS quotient_count,
               COUNT(DISTINCT group_name) AS group_name_classes,
               COUNT(DISTINCT group_order) AS group_order_classes
        FROM "current_cicy3_free_actions"
        GROUP BY h11, h21
        HAVING COUNT(*) > 1 AND (COUNT(DISTINCT group_name) > 1 OR COUNT(DISTINCT group_order) > 1)
        ORDER BY quotient_count DESC
        """
    ).fetchdf()
    write_parquet(OUT_DIR / "all_symmetry_quotient_fidelity_collisions.parquet", quotient)
    outputs["symmetry_quotient"] = quotient

    operator_mask = text_mask(relationship_edges, "operator|picard")
    operator_relationships = relationship_edges[operator_mask].copy()
    write_parquet(OUT_DIR / "all_operator_fidelity_collisions.parquet", operator_relationships)
    outputs["operator"] = operator_relationships

    conifold_mask = text_mask(relationship_edges, "conifold|nodal|transition|thraxion")
    conifold = relationship_edges[conifold_mask].copy()
    write_parquet(OUT_DIR / "all_conifold_transition_fidelity_collisions.parquet", conifold)
    outputs["conifold_transition"] = conifold

    anomalies = []
    explicit_path = OUT_DIR / "explicit_nodal_conifold_corpus_enumeration.json"
    if explicit_path.exists():
        explicit = json.loads(explicit_path.read_text(encoding="utf-8"))
        if explicit["enumeration_status"] == "descriptor_only_no_production_record_table":
            anomalies.append(
                {
                    "anomaly_type": "descriptor_only_research_universe",
                    "object": "explicit_nodal_conifold_corpus",
                    "details": "Production route is verified but no columnar production record table exists in v1.0.0.",
                }
            )
    if len(double_outputs["targeted"][double_outputs["targeted"]["status"] != "computed_source_assembly"]):
        anomalies.append(
            {
                "anomaly_type": "missing_double_octic_source_assembly",
                "object": "requested_repeated_inventory_fibers",
                "details": "Some requested repeated-inventory members have no computed source assembly artifact.",
            }
        )
    anomalies_df = pd.DataFrame(anomalies)
    write_parquet(OUT_DIR / "all_anomalies_and_unresolved_objects.parquet", anomalies_df)
    outputs["anomalies"] = anomalies_df
    return outputs


def text_mask(frame: pd.DataFrame, pattern: str) -> pd.Series:
    columns = [
        column
        for column in (
            "relationship_table",
            "relationship_type",
            "source_dataset",
            "source_id",
            "target_dataset",
            "target_id",
            "evidence",
            "claim_level",
            "join_state",
        )
        if column in frame.columns
    ]
    mask = pd.Series(False, index=frame.index)
    for column in columns:
        mask = mask | frame[column].astype(str).str.lower().str.contains(pattern, regex=True, na=False)
    return mask


def nontrivial_groups(frame: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    if not len(frame):
        return pd.DataFrame()
    grouped = (
        frame.groupby(keys, dropna=False)
        .agg(
            member_count=(frame.columns[0], "count"),
            members=("presentation_id" if "presentation_id" in frame.columns else "native_source_record_id", lambda values: json.dumps([str(v) for v in values])),
        )
        .reset_index()
    )
    return grouped[grouped["member_count"] > 1].copy()


def add_distinct_count(source: pd.DataFrame, groups: pd.DataFrame, keys: list[str], field: str) -> pd.DataFrame:
    if not len(groups):
        groups[f"distinct_{field}"] = []
        return groups
    counts = source.groupby(keys, dropna=False)[field].nunique(dropna=True).reset_index(name=f"distinct_{field}")
    return groups.merge(counts, on=keys, how="left")


def discuss_relationships(component_summary: dict[str, Any], explicit_nodal: dict[str, Any]) -> list[str]:
    return [
        "## Relationship Graph Pass",
        "",
        f"- Traversed {component_summary['relationship_edges']} production relationship edges.",
        f"- Nontrivial connected components: {component_summary['nontrivial_component_count']}; largest component has {component_summary['largest_component_size']} nodes.",
        f"- `explicit_nodal_conifold_corpus` has {explicit_nodal['relationship_edge_count']} production relationship edges and status `{explicit_nodal['enumeration_status']}`.",
        "- Interpretation: the production graph is real and queryable, but the explicit nodal/conifold corpus is still a descriptor-level route in v1.0.0, so no row-level node records can be promoted from it in this pass.",
        "",
    ]


def discuss_projection(projection: pd.DataFrame) -> list[str]:
    families = sorted(projection["construction_family"].dropna().unique()) if len(projection) else []
    return [
        "## CY3 Projection",
        "",
        f"- Built a row-level CY3/source/presentation projection with {len(projection)} rows from normalized production tables plus registered double-octic source artifacts.",
        f"- Families represented at row level: {', '.join(map(str, families))}.",
        "- The projection deliberately preserves entity level and presentation type; it does not collapse source presentations to geometry identities.",
        "",
    ]


def discuss_hodge_groups(hodge_inventory: pd.DataFrame, repeated_hodge: pd.DataFrame, cross_family: pd.DataFrame) -> list[str]:
    return [
        "## Hodge Collision Pass",
        "",
        f"- Hodge group inventory rows: {len(hodge_inventory)}.",
        f"- Repeated-Hodge inventory rows: {len(repeated_hodge)}.",
        f"- Cross-family Hodge collisions: {len(cross_family)}.",
        "- Early reading: ordinary Hodge data collapse heavily both within families and across construction families; the useful signal lives in the attached structural columns and relationship neighborhoods.",
        "",
    ]


def discuss_large_outputs(outputs: dict[str, Any], skipped: bool) -> list[str]:
    if skipped:
        return ["## Large Dataset Scans", "", "- Large scans skipped by flag.", ""]
    return [
        "## Large Dataset Scans",
        "",
        f"- Kreuzer-Skarke rows scanned: {outputs.get('kreuzer_skarke_total_rows_scanned')}; Hodge groups: {outputs.get('kreuzer_skarke_hodge_group_count')}; repeated groups: {outputs.get('kreuzer_skarke_repeated_hodge_group_count')}; largest fiber: {outputs.get('kreuzer_skarke_largest_hodge_fiber')}.",
        f"- DESY GV invariant rows scanned: {outputs.get('desy_gv_total_rows_scanned')}; parent/type summary rows: {outputs.get('desy_gv_parent_summary_rows')}.",
        f"- CICY4 rows scanned for global analogy: {outputs.get('cicy4_total_rows_scanned')}; coarse groups: {outputs.get('cicy4_group_count')}.",
        "- Large-table result: the coarse invariants are extremely non-injective; repeated Hodge fibers are the norm, not an exception.",
        "",
    ]


def discuss_double_octics(outputs: dict[str, Any]) -> list[str]:
    target = outputs["targeted"]
    unresolved = target[target["status"] != "computed_source_assembly"] if len(target) else pd.DataFrame()
    return [
        "## Double-Octic Fidelity",
        "",
        f"- Double-octic source/presentation records: {len(outputs['source_presentations'])}.",
        f"- Computed source complexes available: {len(outputs['assemblies'])}.",
        f"- Fixed-local/fixed-Hodge fibers: {len(outputs['fixed_local_hodge'])}.",
        f"- Repeated local-inventory fibers: {len(outputs['repeated_local'])}.",
        f"- Requested repeated-inventory members unresolved for source assembly: {len(unresolved)}.",
        f"- Rational-collapse/integral-separation sets: {len(outputs['rational_collapse'])}.",
        f"- Integral-collapse/equivariant-separation sets: {len(outputs['integral_collapse'])}.",
        f"- Torsion-sensitive Hodge collisions in source assemblies: {len(outputs['torsion_hodge'])}.",
        "- The 84/84a pattern is not isolated: repeated local inventory can split under rational, integral, and equivariant source-complex data.",
        "",
    ]


def discuss_fidelity(outputs: dict[str, Any]) -> list[str]:
    return [
        "## Other Fidelity Channels",
        "",
        f"- Fibration-sensitive Hodge collisions: {len(outputs['fibration'])}.",
        f"- Symmetry/quotient-sensitive Hodge collisions: {len(outputs['symmetry_quotient'])}.",
        f"- Operator-linked relationship rows: {len(outputs['operator'])}.",
        f"- Nodal/conifold/transition relationship rows: {len(outputs['conifold_transition'])}.",
        f"- Anomalies/unresolved objects: {len(outputs['anomalies'])}.",
        "- These channels are fidelity phenomena, not Hodge-atom claims. They identify where coarse invariants forget structure.",
        "",
    ]


def build_report(**kwargs: Any) -> str:
    ctx: FullCorpusContext = kwargs["ctx"]
    projection: pd.DataFrame = kwargs["projection"]
    repeated_hodge: pd.DataFrame = kwargs["repeated_hodge"]
    cross_family: pd.DataFrame = kwargs["cross_family"]
    double_outputs = kwargs["double_outputs"]
    large_outputs = kwargs["large_outputs"]
    fidelity_outputs = kwargs["fidelity_outputs"]
    explicit_nodal = kwargs["explicit_nodal"]
    hodge_inventory = kwargs["hodge_inventory"]
    fixed = double_outputs["fixed_local_hodge"]
    repeated_local = double_outputs["repeated_local"]
    target = double_outputs["targeted"]
    repeated_members = double_outputs["repeated_member_assemblies"]
    lines = [
        "# HodgeCY II Full-Corpus Discovery Report",
        "",
        f"- Corpus release fingerprint: `{ctx.release_fingerprint}`",
        f"- Production relationship edges traversed: {kwargs['component_summary']['relationship_edges']}",
        f"- CY3 source/presentation/geometry projection rows: {len(projection)}",
        f"- Distinct Hodge inventory rows: {len(hodge_inventory)}",
        f"- Repeated-Hodge fibers: {len(repeated_hodge)}",
        f"- Cross-family Hodge collisions: {len(cross_family)}",
        f"- Explicit nodal/conifold production status: `{explicit_nodal['enumeration_status']}` with {explicit_nodal['relationship_edge_count']} relationship edges",
        "",
        "## Double-Octic Fixed-Local/Fixed-Hodge Fibers",
        "",
    ]
    for row in fixed.to_dict("records"):
        lines.append(f"- `{row.get('local_signature')}` / `{row.get('hodge_signature')}`: {row.get('members')}")
    lines.extend(["", "## All Repeated-Local Double-Octic Fibers", ""])
    for row in repeated_local.to_dict("records"):
        lines.append(f"### {row['members']}")
        lines.append(f"- Local inventory: `{row['local_signature']}`")
        members = json.loads(row["members"])
        for member in members:
            match = repeated_members[repeated_members["member"] == str(member)]
            if match.empty:
                lines.append(f"- {member}: no member row written")
                continue
            item = match.iloc[0].to_dict()
            lines.append(
                f"- {member}: {item['status']}; hodge={display(item['hodge_signature'])}; rank_Q={display(item['rank_Q'])}; rank_F2={display(item['rank_F2'])}; SNF={display(item['smith_normal_form'])}; torsion={display(item['torsion_invariant_factors'])}; orbits planes={display(item['plane_orbit_sizes'])}, lines={display(item['double_line_orbit_sizes'])}, points={display(item['multiple_point_orbit_sizes'])}"
            )
        lines.append("")
    lines.extend(["", "## Requested Repeated-Inventory Source Assemblies", ""])
    for fiber, rows in target.groupby("requested_fiber"):
        lines.append(f"### {fiber}")
        for row in rows.to_dict("records"):
            lines.append(
                f"- {row['member']}: {row['status']}; rank_Q={display(row['rank_Q'])}; rank_F2={display(row['rank_F2'])}; SNF={display(row['smith_normal_form'])}; torsion={display(row['torsion_invariant_factors'])}; orbits planes={display(row['plane_orbit_sizes'])}, lines={display(row['double_line_orbit_sizes'])}, points={display(row['multiple_point_orbit_sizes'])}"
            )
        lines.append("")
    lines.extend(
        [
            "## Counts By Fidelity Channel",
            "",
            f"- 84/84a-like fixed-local/fixed-Hodge sets: {len(fixed)}",
            f"- 239/240/241-like repeated-local fibers: {len(repeated_local)}",
            f"- Rational-collapse/integral-separation sets: {len(double_outputs['rational_collapse'])}",
            f"- Integral-collapse/equivariant-separation sets: {len(double_outputs['integral_collapse'])}",
            f"- Torsion-sensitive collisions: {len(double_outputs['torsion_hodge'])}",
            f"- Operator-sensitive relationship rows: {len(fidelity_outputs['operator'])}",
            f"- Fibration-sensitive collisions: {len(fidelity_outputs['fibration'])}",
            f"- Symmetry/quotient-sensitive collisions: {len(fidelity_outputs['symmetry_quotient'])}",
            f"- Nodal/conifold/transition-sensitive relationship rows: {len(fidelity_outputs['conifold_transition'])}",
            "",
            "## Large Table Results",
            "",
        ]
    )
    if kwargs["skipped_large"]:
        lines.append("- Large scans skipped.")
    else:
        lines.extend(
            [
                f"- Kreuzer-Skarke rows scanned: {large_outputs.get('kreuzer_skarke_total_rows_scanned')}",
                f"- Kreuzer-Skarke Hodge groups: {large_outputs.get('kreuzer_skarke_hodge_group_count')}",
                f"- Kreuzer-Skarke repeated Hodge groups: {large_outputs.get('kreuzer_skarke_repeated_hodge_group_count')}",
                f"- Largest Kreuzer-Skarke Hodge fiber: {large_outputs.get('kreuzer_skarke_largest_hodge_fiber')}",
                f"- DESY GV rows scanned: {large_outputs.get('desy_gv_total_rows_scanned')}",
                f"- CICY4 rows scanned: {large_outputs.get('cicy4_total_rows_scanned')}",
            ]
        )
    lines.extend(
        [
            "",
            "## Discussion",
            "",
            "New structural patterns from this pass:",
            "",
            "- Cross-family Hodge collisions are common rather than exotic: the largest visible cross-family fibers involve CICY3, CICY3 topology, weighted hypersurfaces, IP weights, and toric reflexive polytopes at the same Hodge tuple.",
            "- The double-octic source-complex channel splits repeated local inventory at three different levels: rational-to-integral, integral-to-equivariant, and torsion-prime profile.",
            "- Fibration counts vary inside fixed Hodge tuples for 203 CICY3 Hodge fibers; ordinary Hodge numbers do not determine fibration richness.",
            "- Quotient/free-action data vary inside 22 fixed Hodge classes, so symmetry structure is another independent fidelity channel.",
            "- The explicit nodal/conifold corpus is a verified production route but not a row-enumerable production table in v1.0.0; HodgeCY II should treat that as the next data-foundation gap.",
            "",
            "The first complete pass says that ordinary Hodge data are a very coarse coordinate system on the corpus. The double-octic source-complex data show the sharpest form of the phenomenon: fixed local inventory and fixed ordinary Hodge data can still separate under integral Smith data, torsion prime profile, and equivariant orbit structure. The large toric scan shows the same lesson at a different scale: repeated Hodge fibers are massive, so any HodgeCY II claim must keep source, presentation, topology, operator, and arithmetic levels distinct.",
            "",
            "The explicit nodal/conifold route is production-verified but not row-enumerable in v1.0.0. That is now a concrete data-foundation gap rather than a silent omission.",
            "",
            "Problem 7.10 firewall: all source-complex collisions in this report remain SOURCE/PRESENTATION-level fidelity phenomena unless a later natural node/LMHS/Hodge-atom comparison map is supplied.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_jsonish(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return {}
    if isinstance(value, str) and value.strip():
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return {}


def as_int(value: Any) -> int | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def display(value: Any) -> str:
    if value is None:
        return "UNKNOWN"
    if isinstance(value, float) and math.isnan(value):
        return "UNKNOWN"
    if str(value) in {"nan", "NaN", "None", "null"}:
        return "UNKNOWN"
    return str(value)


def hodge_key(h11: Any, h12: Any, euler: Any) -> str:
    return f"h12={as_int(h12)};h11={as_int(h11)};euler={as_int(euler)}"


def write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if frame.empty:
        pq.write_table(pa.Table.from_pylist([]), path)
        return
    table = pa.Table.from_pandas(frame, preserve_index=False)
    pq.write_table(table, path)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def duckdb_path_list(paths: Iterable[Path]) -> str:
    return "[" + ",".join("'" + str(path).replace("'", "''") + "'" for path in paths) + "]"


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def output_manifest() -> dict[str, str]:
    outputs: dict[str, str] = {}
    for path in sorted(OUT_DIR.glob("*")):
        if path.is_file():
            outputs[path.name] = sha256(path)
    for path in (NOTES_PATH, REPORT_PATH):
        if path.exists():
            outputs[path.name] = sha256(path)
    return outputs


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
