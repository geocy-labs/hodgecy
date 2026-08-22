"""Build the HodgeCY II v1.0.0 relevant-universe deep dive.

This script supersedes the earlier fixed-equation pilot census without deleting
it.  It enumerates the released logical dataset inventory first, then assembles
all repo-local records relevant to double-octic/source-assembly/nodal-conifold
fidelity.  Source-assembly diagnostics remain source-level diagnostics.
"""

from __future__ import annotations

import csv
import argparse
import hashlib
import itertools
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
import sys
from typing import Any, Iterable

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.research.hodgecy_ii_census import (  # noqa: E402
    HODGE_KEYS,
    INVENTORY_KEYS,
    group_records,
    natural_arrangement_key,
    normalize_spectrum,
    stable_fingerprint,
    torsion_profile,
)
from hodgecy.research.full_corpus_context import FullCorpusContext  # noqa: E402

OUT_ROOT = REPO_ROOT / "research_outputs" / "hodgecy_ii"
UNIVERSE_DIR = OUT_ROOT / "universe"

DATASET_CENSUS = REPO_ROOT / "docs" / "corpus" / "current_dataset_census.tsv"
CORPUS_SUMMARY = REPO_ROOT / "docs" / "corpus" / "current_corpus_summary.json"
CKC_INDEX = REPO_ROOT / "data" / "raw" / "cynk_kocel_cynk_2026" / "ckc_equation_index_001_455.json"
CKC_FORGOTTEN_TABLE = REPO_ROOT / "data" / "raw" / "cynk_kocel_cynk_2026" / "ckc_forgotten_arrangements_table.json"
CYNK_MEYER_TABLE1 = REPO_ROOT / "data" / "raw" / "cynk_meyer_table1.csv"
CYNK_MEYER_FAMILIES = REPO_ROOT / "data" / "raw" / "cynk_meyer_families.json"
CYNK_MEYER_RIGID = REPO_ROOT / "data" / "raw" / "cynk_meyer_rigid_equations.json"
CKC_FIXED_SPECTRA = REPO_ROOT / "data" / "processed" / "equivariant_spectra" / "ckc_fixed_rational_batch" / "ckc_fixed_rational_spectra.json"
FIXED_BATCH_DIR = REPO_ROOT / "data" / "processed" / "equivariant_spectra" / "fixed_equation_batch_001"
GATE_A_INVENTORY = OUT_ROOT / "gate_a_artifact_inventory.json"
FAMILY_CANDIDATES = REPO_ROOT / "data" / "processed" / "family_candidates.csv"
CLUSTERS_BY_HODGE = REPO_ROOT / "data" / "processed" / "clusters_by_hodge.csv"
CLUSTERS_BY_SINGULARITY = REPO_ROOT / "data" / "processed" / "clusters_by_singularity.csv"

RELATIONSHIP_DATASETS = {
    "current_corpus_relationships",
    "wave2_source_relationships",
    "wave3_source_relationships",
    "wave4_source_relationships",
}

SPECIAL_FOCUS_IDS = {"84", "84a", "239", "240", "241"}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_tsv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: cell(row.get(key)) for key in fields})


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")


def write_parquet(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    for column in frame.columns:
        if frame[column].map(lambda value: isinstance(value, (dict, list, tuple))).any():
            frame[column] = frame[column].map(lambda value: json.dumps(value, sort_keys=True, default=str) if isinstance(value, (dict, list, tuple)) else value)
    frame.to_parquet(path, index=False)


def cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "YES" if value else "NO"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return str(value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def yes_no(value: bool) -> str:
    return "YES" if value else "NO"


def natural_key_text(value: str) -> str:
    n, suffix = natural_arrangement_key(value)
    return f"{n:04d}{suffix}"


def load_dataset_audit() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = read_tsv(DATASET_CENSUS)
    summary = read_json(CORPUS_SUMMARY)
    audit = []
    for row in rows:
        dataset_id = row["dataset_id"]
        text = " ".join(str(value).lower() for value in row.values())
        direct = any(token in text for token in ("double", "octic", "nodal", "conifold", "transition", "picard", "operator", "fibration", "torsion", "arithmetic"))
        relationship = dataset_id in RELATIONSHIP_DATASETS
        enriches = row["data_family"] in {"picard_fuchs", "k3_fibered", "topology", "relationships", "source_relationships"}
        audit.append(
            {
                **row,
                "dataset_entity_level": "DATASET",
                "row_level_inspected": "REPO_LOCAL" if dataset_id not in RELATIONSHIP_DATASETS else "PRODUCTION_ROOT_REQUIRED",
                "relevant_to_hodgecy_ii": yes_no(direct or relationship or enriches),
                "relevance_reason": dataset_relevance_reason(row, direct, relationship, enriches),
                "production_root_available": "REPO_LOCAL_NOT_APPLICABLE",
            }
        )
    return audit, summary


def dataset_relevance_reason(row: dict[str, str], direct: bool, relationship: bool, enriches: bool) -> str:
    if relationship:
        return "relationship_graph_required_for_recursive_universe_resolution"
    if direct:
        return "name_or_family_matches_double_octic_nodal_conifold_operator_fibration_topology_terms"
    if enriches:
        return "possible_operator_fibration_topological_or_arithmetic_enrichment"
    return "inspected_no_direct_repo_local_hodgecy_ii_link"


def ckc_entity_level(record: dict[str, Any]) -> str:
    if record.get("has_parameters"):
        return "PARAMETERIZED_FAMILY"
    if record.get("extraction_status") != "extracted":
        return "SOURCE_RECORD"
    return "PRESENTATION"


def ckc_presentation_kind(record: dict[str, Any]) -> str:
    if record.get("has_parameters"):
        return "eight_plane_arrangement_family"
    if record.get("fixed_equation_candidate"):
        return "eight_plane_arrangement_fixed_candidate"
    return "eight_plane_arrangement_source_record"


def equation_type(record: dict[str, Any]) -> str:
    equation = str(record.get("normalized_equation_text") or record.get("equation_text") or "")
    if record.get("extraction_status") != "extracted":
        return "partial_or_problematic_source_extraction"
    if record.get("has_parameters"):
        return "parameterized_family"
    if "sqrt" in equation or "√" in equation:
        return "fixed_algebraic"
    if record.get("fixed_equation_candidate"):
        return "fixed_rational"
    return "fixed_source_record"


def load_ckc_records() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    payload = read_json(CKC_INDEX)
    return payload, {str(row["arrangement_id"]): row for row in payload["records"]}


def load_table1_rows() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in read_csv(CYNK_MEYER_TABLE1):
        row = {key: parse_scalar(value) for key, value in row.items()}
        rows[str(row["arrangement"])] = row
    return rows


def load_ckc_forgotten_rows() -> dict[str, dict[str, Any]]:
    payload = read_json(CKC_FORGOTTEN_TABLE)
    rows = {}
    for row in payload["records"]:
        normalized = dict(row)
        normalized["source_dataset"] = "cynk_kocel_cynk_2026_forgotten_arrangements_table"
        normalized["source_reference"] = payload["source_reference"]
        normalized["validation_state"] = payload["validation_state"]
        rows[str(row["arrangement_id"])] = normalized
    return rows


def parse_scalar(value: str) -> Any:
    if value is None:
        return None
    text = str(value)
    if text == "":
        return None
    if text in {"True", "False"}:
        return text == "True"
    try:
        return int(text)
    except ValueError:
        return text


def load_source_assemblies() -> list[Any]:
    assemblies = []
    for item in read_json(CKC_FIXED_SPECTRA)["spectra"]:
        assemblies.append(normalize_spectrum(item, source_dataset="ckc_fixed_rational_batch"))
    for arrangement_id in ("84", "84a"):
        path = FIXED_BATCH_DIR / f"hodgecy_equivariant_spectrum_{arrangement_id}.json"
        if path.exists():
            assemblies.append(normalize_spectrum(read_json(path), source_dataset="fixed_equation_batch_001"))
    return sorted(assemblies, key=lambda record: natural_arrangement_key(record.arrangement_id))


def inventory_from_row(row: dict[str, Any] | None) -> dict[str, int] | None:
    if not row:
        return None
    try:
        return {key: int(row[key]) for key in INVENTORY_KEYS}
    except (KeyError, TypeError, ValueError):
        return None


def hodge_from_row(row: dict[str, Any] | None) -> dict[str, int] | None:
    if not row:
        return None
    try:
        return {key: int(row[key]) for key in HODGE_KEYS}
    except (KeyError, TypeError, ValueError):
        return None


def inventory_signature(inventory: dict[str, Any] | None) -> str | None:
    if not inventory:
        return None
    return ";".join(f"{key}={int(inventory.get(key, 0) or 0)}" for key in INVENTORY_KEYS)


def hodge_signature(hodge: dict[str, Any] | None) -> str | None:
    if not hodge:
        return None
    return ";".join(f"{key}={int(hodge.get(key, 0) or 0)}" for key in HODGE_KEYS)


def compact_snf(values: Iterable[Any] | None) -> str | None:
    if values is None:
        return None
    counts = Counter(int(value) for value in values)
    return ",".join(f"{value}^{count}" if count > 1 else str(value) for value, count in sorted(counts.items()))


def build_ckc_presentations(
    ckc_records: dict[str, dict[str, Any]],
    table1_rows: dict[str, dict[str, Any]],
    forgotten_rows: dict[str, dict[str, Any]],
    assembly_by_id: dict[str, Any],
) -> list[dict[str, Any]]:
    presentations = []
    for arrangement_id in sorted(ckc_records, key=natural_arrangement_key):
        record = ckc_records[arrangement_id]
        table_row = table1_rows.get(arrangement_id) or forgotten_rows.get(arrangement_id)
        assembly = assembly_by_id.get(arrangement_id)
        inventory = inventory_from_row(table_row)
        hodge = hodge_from_row(table_row)
        if assembly is not None:
            inventory = dict(zip(INVENTORY_KEYS, assembly.inventory, strict=True))
            if assembly.hodge:
                hodge = dict(zip(HODGE_KEYS, assembly.hodge, strict=True))
        presentations.append(
            {
                "universe_id": f"ckc:{arrangement_id}",
                "hodgecy_dataset_id": "cynk_kocel_cynk_2026",
                "source_dataset": "cynk_kocel_cynk_2026",
                "native_source_record_id": arrangement_id,
                "normalized_hodgecy_id": f"double_octic:ckc:{arrangement_id}",
                "entity_level": ckc_entity_level(record),
                "construction_family": "double_octic",
                "presentation_kind": ckc_presentation_kind(record),
                "source_citation": record.get("source_reference"),
                "source_equation": record.get("normalized_equation_text") or record.get("equation_text"),
                "family_equation": record.get("normalized_equation_text") if record.get("has_parameters") else None,
                "parameters": record.get("parameter_names") or [],
                "ckc_id": arrangement_id,
                "cynk_meyer_id": arrangement_id if arrangement_id in table1_rows else None,
                "external_corpus_id": None,
                "explicit_nodal_conifold_id": arrangement_id if arrangement_id in {"84", "84a"} else None,
                "known_crosswalks": ["ckc_to_cynk_meyer_table1"] if arrangement_id in table1_rows else [],
                "hodge": hodge,
                "topology": {"rigid": table_row.get("rigid"), "modular_form": table_row.get("modular_form")} if table_row else {},
                "incidence_data": {"status": "assembly_computed", "source": assembly.source_dataset} if assembly else {"status": "source_equation_available_or_family_unresolved"},
                "symmetry_data": {"incidence_group_order": assembly.automorphism_group_order} if assembly else {},
                "node_data": {"problem_7_10_level": "node_level_unresolved"},
                "operator_data": operator_labels(table_row),
                "fibration_data": {},
                "arithmetic_data": {"modular_form": table_row.get("modular_form")} if table_row and table_row.get("modular_form") else {},
                "transition_data": {},
                "local_inventory": inventory,
                "validation_provenance_status": ckc_validation_status(record, table_row, assembly),
                "source_availability": source_availability(record),
                "computation_availability": "source_assembly_computed" if assembly else "source_assembly_not_yet_computed",
                "identity_resolution_status": "presentation_level_only_geometry_identity_unresolved",
                "claim_level_firewall": "SOURCE_LEVEL_ONLY_UNLESS_NODE_COLUMNS_EXPLICITLY_CERTIFIED",
                "equation_type": equation_type(record),
            }
        )
    return presentations


def ckc_validation_status(record: dict[str, Any], table_row: dict[str, Any] | None, assembly: Any | None) -> str:
    states = [f"ckc_extraction={record.get('extraction_status')}", f"ckc_validation={record.get('validation_status')}"]
    if table_row:
        states.append("hodge_local_table_attached")
    if assembly:
        states.append("source_assembly_recomputed")
    return ";".join(states)


def source_availability(record: dict[str, Any]) -> str:
    factors = record.get("linear_factor_texts") or []
    if record.get("extraction_status") == "extracted" and len(factors) == 8:
        return "eight_plane_equation_or_family_available"
    return "partial_source_equation_requires_reconstruction"


def operator_labels(row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        return {}
    return {
        "hodgecy_role": row.get("hodgecy_role"),
        "family_operator_candidate": row.get("hodgecy_role") == "family_operator_candidate",
        "operator_data_needed": row.get("hodgecy_role") == "family_operator_candidate",
    }


def build_cynk_meyer_records(table1_rows: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    records = []
    for arrangement_id in sorted(table1_rows, key=natural_arrangement_key):
        row = table1_rows[arrangement_id]
        records.append(
            {
                "universe_id": f"cynk_meyer_table1:{arrangement_id}",
                "hodgecy_dataset_id": "double_octics",
                "source_dataset": "cynk_meyer_table1",
                "native_source_record_id": arrangement_id,
                "normalized_hodgecy_id": f"double_octic:cynk_meyer:{arrangement_id}",
                "entity_level": "SOURCE_RECORD",
                "construction_family": "double_octic",
                "presentation_kind": "cynk_meyer_hodge_local_table_row",
                "source_citation": "Cynk--Meyer double octic table encoded in HodgeCY v1.0.0",
                "source_equation": None,
                "family_equation": None,
                "parameters": [],
                "ckc_id": arrangement_id if arrangement_id != "84a" else None,
                "cynk_meyer_id": arrangement_id,
                "external_corpus_id": None,
                "explicit_nodal_conifold_id": arrangement_id if arrangement_id in {"84", "84a"} else None,
                "known_crosswalks": ["cynk_meyer_table1_to_ckc"] if arrangement_id != "84a" else ["supplemental_cynk_meyer_84a"],
                "hodge": hodge_from_row(row),
                "topology": {"rigid": row.get("rigid"), "modular_form": row.get("modular_form")},
                "incidence_data": {"local_inventory_source_reported": True},
                "symmetry_data": {},
                "node_data": {"problem_7_10_level": "node_level_unresolved"},
                "operator_data": operator_labels(row),
                "fibration_data": {},
                "arithmetic_data": {"modular_form": row.get("modular_form")} if row.get("modular_form") else {},
                "transition_data": {},
                "local_inventory": inventory_from_row(row),
                "validation_provenance_status": "source_reported_hodge_local_table",
                "source_availability": "hodge_local_table_row",
                "computation_availability": "source_assembly_requires_presentation_or_existing_spectrum",
                "identity_resolution_status": "source_row_attached_to_arrangement_label_not_geometry_collapsed",
                "claim_level_firewall": "SOURCE_LEVEL_OR_HODGE_TABLE_ONLY_NOT_HODGE_ATOM",
            }
        )
    return records


def build_equation_records() -> list[dict[str, Any]]:
    records = []
    for path, dataset, level in (
        (CYNK_MEYER_FAMILIES, "cynk_meyer_family_equations", "PARAMETERIZED_FAMILY"),
        (CYNK_MEYER_RIGID, "cynk_meyer_rigid_equations", "PRESENTATION"),
    ):
        if not path.exists():
            continue
        for row in read_json(path):
            arrangement_id = str(row.get("arrangement_id") or row.get("family_id"))
            records.append(
                {
                    "universe_id": f"{dataset}:{arrangement_id}",
                    "hodgecy_dataset_id": "double_octics",
                    "source_dataset": dataset,
                    "native_source_record_id": arrangement_id,
                    "normalized_hodgecy_id": f"double_octic:{dataset}:{arrangement_id}",
                    "entity_level": level,
                    "construction_family": "double_octic",
                    "presentation_kind": "plane_arrangement_equation",
                    "source_citation": "HodgeCY local Cynk--Meyer equation source",
                    "source_equation": row.get("equation"),
                    "family_equation": row.get("equation") if level == "PARAMETERIZED_FAMILY" else None,
                    "parameters": ["A", "B"] if "A" in str(row.get("equation")) or "B" in str(row.get("equation")) else [],
                    "ckc_id": arrangement_id,
                    "cynk_meyer_id": arrangement_id,
                    "known_crosswalks": ["equation_record_to_cynk_meyer_label"],
                    "hodge": {key: row[key] for key in HODGE_KEYS if key in row},
                    "topology": {},
                    "local_inventory": None,
                    "validation_provenance_status": str(row.get("notes") or "local_equation_source"),
                    "source_availability": "equation_available",
                    "computation_availability": "source_assembly_not_yet_computed_in_this_universe_run",
                    "identity_resolution_status": "presentation_or_family_level",
                    "claim_level_firewall": "SOURCE_LEVEL_ONLY",
                }
            )
    return records


def build_assembly_rows(assemblies: list[Any]) -> list[dict[str, Any]]:
    rows = []
    for record in assemblies:
        payload = record.to_dict()
        rows.append(
            {
                "universe_id": f"source_assembly:{record.arrangement_id}",
                "hodgecy_dataset_id": "derived_hodgecy_ii_source_assembly",
                "source_dataset": record.source_dataset,
                "native_source_record_id": record.arrangement_id,
                "normalized_hodgecy_id": f"double_octic:source_assembly:{record.arrangement_id}",
                "entity_level": "DERIVED_COMPUTATIONAL_OBJECT",
                "construction_family": "double_octic",
                "presentation_kind": "hodgecy_i_two_stratum_source_assembly",
                "ckc_id": record.arrangement_id if record.arrangement_id != "84a" else None,
                "cynk_meyer_id": record.arrangement_id,
                "known_crosswalks": ["assembly_to_arrangement_label"],
                "hodge": payload.get("hodge"),
                "topology": {},
                "local_inventory": payload.get("inventory"),
                "source_assembly": {
                    "regime": payload["regime"],
                    "gluing_matrix_shape": payload["gluing_matrix_shape"],
                    "rank_Q": payload["rank_Q"],
                    "rank_F2": payload["rank_F2"],
                    "kernel_dim_Q": payload["kernel_dim_Q"],
                    "cokernel_dim_Q": payload["cokernel_dim_Q"],
                    "smith_normal_form": payload["smith_normal_form"],
                    "torsion_primes": payload["torsion_primes"],
                },
                "symmetry_data": {
                    "incidence_group_order": payload["automorphism_group_order"],
                    "plane_orbit_sizes": payload["plane_orbit_sizes"],
                    "double_line_orbit_sizes": payload["double_line_orbit_sizes"],
                    "multiple_point_orbit_sizes": payload["multiple_point_orbit_sizes"],
                },
                "node_data": {"problem_7_10_level": "node_level_unresolved"},
                "validation_provenance_status": "source_assembly_computed_existing_artifact",
                "source_availability": "computed_from_existing_spectrum_artifact",
                "computation_availability": "source_assembly_available",
                "identity_resolution_status": "derived_from_source_presentation_not_geometry_collapsed",
                "claim_level_firewall": "SOURCE_ASSEMBLY_NOT_NODE_LMHS_OR_HODGE_ATOM",
                **payload,
                "inventory_signature": inventory_signature(payload.get("inventory")),
                "hodge_signature": hodge_signature(payload.get("hodge")),
                "smith_normal_form_compact": compact_snf(payload.get("smith_normal_form")),
            }
        )
    return rows


def build_node_links() -> list[dict[str, Any]]:
    links = []
    if GATE_A_INVENTORY.exists():
        for row in read_json(GATE_A_INVENTORY):
            for arrangement_id in str(row.get("arrangement", "")).split(","):
                arrangement_id = arrangement_id.strip()
                if not arrangement_id:
                    continue
                links.append(
                    {
                        "link_id": stable_fingerprint("node_link", {"artifact": row.get("artifact"), "arrangement": arrangement_id}),
                        "arrangement_id": arrangement_id,
                        "ckc_id": arrangement_id if arrangement_id != "84a" else None,
                        "cynk_meyer_id": arrangement_id,
                        "source_dataset": "explicit_nodal_conifold_corpus",
                        "artifact": row.get("artifact"),
                        "artifact_type": row.get("artifact_type"),
                        "claimed_result": row.get("claimed_result"),
                        "evidence_state": row.get("evidence_state"),
                        "machine_readable": row.get("machine_readable"),
                        "reproducible": row.get("reproducible"),
                        "node_level_status": "not_promoted_to_verified_node_relation_complex",
                        "problem_7_10_firewall": "source_to_node_comparison_requires_natural_comparison_map",
                    }
                )
    return links


def build_operator_links(table1_rows: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    links = []
    for arrangement_id, row in sorted(table1_rows.items(), key=lambda item: natural_arrangement_key(item[0])):
        if row.get("modular_form") or row.get("hodgecy_role") == "family_operator_candidate":
            links.append(
                {
                    "link_id": stable_fingerprint("operator_arithmetic", {"arrangement": arrangement_id, "role": row.get("hodgecy_role"), "modular": row.get("modular_form")}),
                    "arrangement_id": arrangement_id,
                    "ckc_id": arrangement_id if arrangement_id != "84a" else None,
                    "source_dataset": "double_octics",
                    "target_dataset": "picard_fuchs_or_arithmetic_registry",
                    "hodgecy_role": row.get("hodgecy_role"),
                    "modular_form": row.get("modular_form"),
                    "operator_join_status": "needed_or_source_label_only",
                    "claim_level": "source_reported_enrichment_not_forced_by_hodge_number",
                }
            )
    if FAMILY_CANDIDATES.exists():
        for row in read_csv(FAMILY_CANDIDATES):
            arrangement_id = str(row.get("arrangement"))
            links.append(
                {
                    "link_id": stable_fingerprint("family_operator_candidate", row),
                    "arrangement_id": arrangement_id,
                    "ckc_id": arrangement_id,
                    "source_dataset": "family_candidates",
                    "target_dataset": "picard_fuchs_cyo",
                    "hodgecy_role": row.get("hodgecy_role"),
                    "source_equation": row.get("equation"),
                    "operator_data_needed": row.get("operator_data_needed"),
                    "claim_level": "candidate_operator_route_unresolved",
                }
            )
    return links


def build_crosswalk(ckc_presentations: list[dict[str, Any]], table1_rows: dict[str, dict[str, Any]], forgotten_rows: dict[str, dict[str, Any]], assembly_rows: list[dict[str, Any]], node_links: list[dict[str, Any]], operator_links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    assembly_ids = {str(row["native_source_record_id"]) for row in assembly_rows}
    node_ids = {str(row["arrangement_id"]) for row in node_links}
    operator_ids = {str(row["arrangement_id"]) for row in operator_links}
    rows = []
    for row in ckc_presentations:
        arrangement_id = str(row["ckc_id"])
        table = table1_rows.get(arrangement_id) or forgotten_rows.get(arrangement_id)
        rows.append(
            {
                "ckc_id": arrangement_id,
                "hodgecy_universe_id": row["universe_id"],
                "entity_level": row["entity_level"],
                "equation_type": row["equation_type"],
                "source_extraction_status": row["source_availability"],
                "parameter_names": row["parameters"],
                "cynk_meyer_id": arrangement_id if arrangement_id in table1_rows else "",
                "cynk_meyer_table_present": yes_no(arrangement_id in table1_rows),
                "hodge_table_present": yes_no(bool(table)),
                "h12": (table or {}).get("h12"),
                "h11": (table or {}).get("h11"),
                "euler": (table or {}).get("euler"),
                "local_inventory": inventory_signature(inventory_from_row(table)),
                "source_assembly_present": yes_no(arrangement_id in assembly_ids),
                "explicit_nodal_conifold_link_present": yes_no(arrangement_id in node_ids),
                "operator_fibration_arithmetic_link_present": yes_no(arrangement_id in operator_ids),
                "relationship_graph_hits_repo_local": "PRODUCTION_ROOT_NOT_AVAILABLE",
                "identity_resolution_status": row["identity_resolution_status"],
                "claim_level_firewall": row["claim_level_firewall"],
            }
        )
    return rows


def source_presentations_for_pairwise(ckc_presentations: list[dict[str, Any]], table1_rows: dict[str, dict[str, Any]], assembly_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {str(row["ckc_id"]): dict(row) for row in ckc_presentations}
    if "84a" in table1_rows:
        row = table1_rows["84a"]
        by_id["84a"] = {
            "universe_id": "supplemental:84a",
            "ckc_id": None,
            "cynk_meyer_id": "84a",
            "native_source_record_id": "84a",
            "entity_level": "PRESENTATION",
            "construction_family": "double_octic",
            "presentation_kind": "supplemental_cynk_meyer_84a",
            "hodge": hodge_from_row(row),
            "local_inventory": inventory_from_row(row),
            "identity_resolution_status": "supplemental_non_ckc_presentation",
        }
    assembly_by_arr = {str(row["native_source_record_id"]): row for row in assembly_rows}
    presentations = []
    for arrangement_id, row in sorted(by_id.items(), key=lambda item: natural_arrangement_key(item[0])):
        assembly = assembly_by_arr.get(arrangement_id)
        inventory = row.get("local_inventory")
        hodge = row.get("hodge")
        if assembly:
            inventory = assembly.get("inventory") or inventory
            hodge = assembly.get("hodge") or hodge
        presentations.append(
            {
                "presentation_id": arrangement_id,
                "universe_id": row["universe_id"],
                "ckc_id": row.get("ckc_id"),
                "cynk_meyer_id": row.get("cynk_meyer_id"),
                "entity_level": row.get("entity_level"),
                "presentation_kind": row.get("presentation_kind"),
                "local_inventory": inventory,
                "local_signature": inventory_signature(inventory),
                "hodge": hodge,
                "hodge_signature": hodge_signature(hodge),
                "source_assembly_available": bool(assembly),
                "rational_signature": rational_signature(assembly),
                "integral_signature": integral_signature(assembly),
                "equivariant_signature": equivariant_signature(assembly),
                "identity_resolution_status": row.get("identity_resolution_status"),
                "claim_level_firewall": "SOURCE_PRESENTATION_PAIRWISE_COMPARISON_NOT_GEOMETRY_COLLAPSE",
            }
        )
    return presentations


def rational_signature(row: dict[str, Any] | None) -> str | None:
    if not row:
        return None
    payload = {
        "local": row.get("inventory"),
        "shape": row.get("gluing_matrix_shape"),
        "rank_Q": row.get("rank_Q"),
        "kernel_dim_Q": row.get("kernel_dim_Q"),
        "cokernel_dim_Q": row.get("cokernel_dim_Q"),
    }
    return stable_fingerprint("rational", payload)


def integral_signature(row: dict[str, Any] | None) -> str | None:
    if not row:
        return None
    payload = {"rational": rational_signature(row), "smith_normal_form": row.get("smith_normal_form")}
    return stable_fingerprint("integral", payload)


def equivariant_signature(row: dict[str, Any] | None) -> str | None:
    if not row:
        return None
    payload = {
        "integral": integral_signature(row),
        "automorphism_group_order": row.get("automorphism_group_order"),
        "plane_orbit_sizes": row.get("plane_orbit_sizes"),
        "double_line_orbit_sizes": row.get("double_line_orbit_sizes"),
        "multiple_point_orbit_sizes": row.get("multiple_point_orbit_sizes"),
    }
    return stable_fingerprint("equivariant", payload)


def build_pairwise_rows(presentations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for left, right in itertools.combinations(presentations, 2):
        both_assembly = left["source_assembly_available"] and right["source_assembly_available"]
        rows.append(
            {
                "left_id": left["presentation_id"],
                "right_id": right["presentation_id"],
                "left_universe_id": left["universe_id"],
                "right_universe_id": right["universe_id"],
                "comparison_level": "SOURCE_PRESENTATION",
                "ckc_pair": bool(left.get("ckc_id") and right.get("ckc_id")),
                "same_local_inventory": maybe_equal(left["local_signature"], right["local_signature"]),
                "same_hodge": maybe_equal(left["hodge_signature"], right["hodge_signature"]),
                "both_source_assembly_available": both_assembly,
                "same_rational_assembly": maybe_equal(left["rational_signature"], right["rational_signature"]) if both_assembly else None,
                "same_integral_assembly": maybe_equal(left["integral_signature"], right["integral_signature"]) if both_assembly else None,
                "same_equivariant_source": maybe_equal(left["equivariant_signature"], right["equivariant_signature"]) if both_assembly else None,
                "finer_source_difference_available": finer_difference(left, right),
                "node_level_result": "unresolved",
                "hodge_atom_result": "unresolved",
                "problem_7_10_firewall": "source_comparison_only",
            }
        )
    return rows


def maybe_equal(left: str | None, right: str | None) -> bool | None:
    if left is None or right is None:
        return None
    return left == right


def finer_difference(left: dict[str, Any], right: dict[str, Any]) -> bool | None:
    flags = [
        maybe_equal(left["rational_signature"], right["rational_signature"]),
        maybe_equal(left["integral_signature"], right["integral_signature"]),
        maybe_equal(left["equivariant_signature"], right["equivariant_signature"]),
    ]
    known = [flag for flag in flags if flag is not None]
    if not known:
        return None
    return any(flag is False for flag in known)


def group_nontrivial(rows: list[dict[str, Any]], key: str, *, require_key: bool = True) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        value = row.get(key)
        if value is None and require_key:
            continue
        grouped[str(value)].append(row)
    out = []
    for index, (signature, members) in enumerate(sorted(grouped.items(), key=lambda item: natural_key_text(item[1][0]["presentation_id"])), start=1):
        if len(members) <= 1:
            continue
        ids = [m["presentation_id"] for m in sorted(members, key=lambda item: natural_arrangement_key(item["presentation_id"]))]
        out.append({"set_id": f"{key}_{index:03d}", "signature": signature, "member_count": len(ids), "members": ids})
    return out


def build_discovery_sets(presentations: list[dict[str, Any]], assembly_rows: list[dict[str, Any]], node_links: list[dict[str, Any]]) -> dict[str, Any]:
    fixed_local_hodge = []
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in presentations:
        if row.get("local_signature") and row.get("hodge_signature"):
            groups[(row["local_signature"], row["hodge_signature"])].append(row)
    for index, ((local_sig, hodge_sig), members) in enumerate(sorted(groups.items(), key=lambda item: natural_key_text(item[1][0]["presentation_id"])), start=1):
        if len(members) <= 1:
            continue
        ids = [m["presentation_id"] for m in sorted(members, key=lambda item: natural_arrangement_key(item["presentation_id"]))]
        known_assembly_classes = sorted({m["integral_signature"] for m in members if m.get("integral_signature")})
        unresolved_count = sum(1 for m in members if not m.get("integral_signature"))
        if len(known_assembly_classes) > 1:
            finer_source_variation: bool | str = True
        elif unresolved_count:
            finer_source_variation = "UNKNOWN"
        else:
            finer_source_variation = False
        fixed_local_hodge.append(
            {
                "set_id": f"fixed_local_hodge_{index:03d}",
                "members": ids,
                "member_count": len(ids),
                "local_inventory": local_sig,
                "hodge": hodge_sig,
                "source_level_result": "same local source inventory and same ordinary Hodge data",
                "finer_source_variation": finer_source_variation,
                "source_assembly_classes": known_assembly_classes,
                "source_assembly_unresolved_members": unresolved_count,
                "node_level_result": "unresolved",
                "hodge_atom_result": "unresolved",
            }
        )

    local_sets = group_nontrivial(presentations, "local_signature")
    rational_groups = group_nontrivial([row for row in presentations if row.get("rational_signature")], "rational_signature")
    integral_groups = group_nontrivial([row for row in presentations if row.get("integral_signature")], "integral_signature")
    equivariant_groups = group_nontrivial([row for row in presentations if row.get("equivariant_signature")], "equivariant_signature")

    rational_collapse_integral = []
    by_rat: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in presentations:
        if row.get("rational_signature"):
            by_rat[row["rational_signature"]].append(row)
    for index, (signature, members) in enumerate(sorted(by_rat.items(), key=lambda item: natural_key_text(item[1][0]["presentation_id"])), start=1):
        integral_classes = sorted({m["integral_signature"] for m in members if m.get("integral_signature")})
        if len(members) > 1 and len(integral_classes) > 1:
            rational_collapse_integral.append(
                {
                    "set_id": f"rational_collapse_integral_{index:03d}",
                    "rational_signature": signature,
                    "members": [m["presentation_id"] for m in sorted(members, key=lambda item: natural_arrangement_key(item["presentation_id"]))],
                    "integral_signature_count": len(integral_classes),
                    "source_level_result": "same rational source assembly but different integral Smith data",
                    "node_level_result": "unresolved",
                }
            )

    integral_collapse_equivariant = []
    by_int: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in presentations:
        if row.get("integral_signature"):
            by_int[row["integral_signature"]].append(row)
    for index, (signature, members) in enumerate(sorted(by_int.items(), key=lambda item: natural_key_text(item[1][0]["presentation_id"])), start=1):
        eq_classes = sorted({m["equivariant_signature"] for m in members if m.get("equivariant_signature")})
        if len(members) > 1 and len(eq_classes) > 1:
            integral_collapse_equivariant.append(
                {
                    "set_id": f"integral_collapse_equivariant_{index:03d}",
                    "integral_signature": signature,
                    "members": [m["presentation_id"] for m in sorted(members, key=lambda item: natural_arrangement_key(item["presentation_id"]))],
                    "equivariant_signature_count": len(eq_classes),
                    "source_level_result": "same integral source assembly but different equivariant source data",
                    "node_level_result": "unresolved",
                }
            )

    problem_targets = build_problem_targets(presentations, node_links)
    unusual_prime_patterns = []
    for row in assembly_rows:
        torsion = torsion_profile(row.get("smith_normal_form") or [])
        if torsion["torsion_primes"]:
            unusual_prime_patterns.append(
                {
                    "arrangement_id": row["native_source_record_id"],
                    "torsion_primes": torsion["torsion_primes"],
                    "torsion_invariant_factors": torsion["torsion_invariant_factors"],
                    "smith_normal_form": row.get("smith_normal_form"),
                    "source_level_result": "source assembly has nontrivial torsion profile",
                }
            )

    return {
        "fixed_local_hodge_sets": fixed_local_hodge,
        "local_inventory_fidelity_sets": local_sets,
        "rational_collapse_integral_sets": rational_collapse_integral,
        "integral_collapse_equivariant_sets": integral_collapse_equivariant,
        "recurrent_assembly_types": {
            "rational": rational_groups,
            "integral": integral_groups,
            "equivariant": equivariant_groups,
        },
        "problem_7_10_candidate_sets": problem_targets,
        "unusual_prime_torsion_patterns": unusual_prime_patterns,
    }


def build_problem_targets(presentations: list[dict[str, Any]], node_links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    node_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for link in node_links:
        node_by_id[str(link["arrangement_id"])].append(link)
    by_id = {row["presentation_id"]: row for row in presentations}
    targets = []
    for arrangement_id in sorted(set(node_by_id) & set(by_id), key=natural_arrangement_key):
        row = by_id[arrangement_id]
        targets.append(
            {
                "target_id": f"problem_7_10:{arrangement_id}",
                "members": [arrangement_id],
                "source_assembly_available": row["source_assembly_available"],
                "explicit_nodal_model_available": True,
                "node_count_known": "degree112_claimed_but_ordinary_node_status_not_promoted" if arrangement_id in {"84", "84a"} else "unknown",
                "node_ideal_known": "certificate_artifacts_present_incomplete_for_promotion",
                "relation_data_known": "unresolved",
                "symmetry_compatible": "unresolved",
                "hodge_lmhs_information_available": "ordinary_hodge_available_lmhs_unresolved",
                "existing_transition_data": "artifact_links_present",
                "problem_7_10_firewall": "candidate_only_requires_natural_source_to_node_comparison_map",
                "artifact_count": len(node_by_id[arrangement_id]),
            }
        )
    return targets


def build_relationship_rows(universe_records: list[dict[str, Any]], node_links: list[dict[str, Any]], operator_links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in universe_records:
        ckc_id = row.get("ckc_id")
        cm_id = row.get("cynk_meyer_id")
        if ckc_id and cm_id:
            rows.append(rel_row(row["universe_id"], f"cynk_meyer_table1:{cm_id}", "source_crosswalk", "arrangement_label"))
        if row.get("entity_level") == "DERIVED_COMPUTATIONAL_OBJECT":
            rows.append(rel_row(row["universe_id"], f"ckc:{row.get('ckc_id') or row.get('cynk_meyer_id')}", "derived_from_source_presentation", "arrangement_label"))
    for link in node_links:
        rows.append(rel_row(f"ckc:{link.get('ckc_id') or link['arrangement_id']}", f"node_artifact:{link['link_id']}", "has_node_conifold_artifact", "artifact_inventory"))
    for link in operator_links:
        rows.append(rel_row(f"ckc:{link.get('ckc_id') or link['arrangement_id']}", f"operator_link:{link['link_id']}", "has_operator_fibration_arithmetic_enrichment", "source_label_or_role"))
    for dataset in sorted(RELATIONSHIP_DATASETS):
        rows.append(
            {
                "relationship_id": stable_fingerprint("relationship_unavailable", {"dataset": dataset}),
                "source_id": dataset,
                "target_id": "production_data_root",
                "relationship_type": "requires_production_root_inspection",
                "evidence_type": "environment_metadata",
                "claim_level": "unresolved",
                "join_state": "not_loaded",
                "directed": True,
            }
        )
    return rows


def rel_row(source: str, target: str, relationship_type: str, evidence: str) -> dict[str, Any]:
    payload = {"source_id": source, "target_id": target, "relationship_type": relationship_type, "evidence_type": evidence}
    return {
        "relationship_id": stable_fingerprint("universe_relationship", payload),
        **payload,
        "claim_level": "source_reported_or_computational",
        "join_state": "matched_repo_local",
        "directed": True,
    }


def build_reports(
    dataset_audit: list[dict[str, Any]],
    summary: dict[str, Any],
    denominators: dict[str, Any],
    discovery: dict[str, Any],
) -> None:
    universe_lines = [
        "# HodgeCY v1.0.0 Relevant Universe Report",
        "",
        "## Denominator Answer",
        "",
        f"- Is the complete HodgeCY II universe 455? **{denominators['IS_COMPLETE_HODGECY_II_UNIVERSE_455']}**.",
        "- The number 455 is the CKC-numbered subuniverse denominator only. HodgeCY v1.0.0 also contains Cynk-Meyer table records, supplemental 84a, source assemblies, node/conifold artifacts, and operator/arithmetic/fibration enrichment routes.",
        "- This report was generated in explicit `--repo-local` mode, so normalized production relationship parquet inspection is out of scope.",
        "",
        "## Counts",
        "",
    ]
    for key, value in denominators.items():
        universe_lines.append(f"- `{key}`: {value}")
    universe_lines.extend(
        [
            "",
            "## v1.0.0 Corpus Frame",
            "",
            f"- Logical datasets enumerated: {summary['logical_dataset_count']}",
            f"- Dataset/source instances: {summary['instance_count']}",
            f"- Physical sources: {summary['physical_source_count']}",
            f"- Query tables: {summary['query_table_count']}",
            f"- Relationship edges advertised by release summary: {summary['relationship_edge_count']}",
            f"- Source data records advertised by release summary: {summary['source_data_record_count']}",
            "",
            "## Relevant Dataset Inspection",
            "",
        ]
    )
    for row in dataset_audit:
        if row["relevant_to_hodgecy_ii"] == "YES":
            universe_lines.append(f"- `{row['dataset_id']}`: {row['relevance_reason']} ({row['row_level_inspected']})")
    universe_lines.extend(
        [
            "",
            "## Firewall",
            "",
            "All source assembly claims in this report are source-level claims. Node relations, vanishing-cycle lattices, LMHS, and genuine Hodge atom spectra remain unresolved unless explicitly certified in node-level columns.",
        ]
    )
    (OUT_ROOT / "hodgecy_v1_relevant_universe_report.md").write_text("\n".join(universe_lines) + "\n", encoding="utf-8")
    (UNIVERSE_DIR / "universe_summary.md").write_text("\n".join(universe_lines) + "\n", encoding="utf-8")

    fidelity_lines = [
        "# Partial Repo-Local Fidelity Discovery Report",
        "",
        "This PARTIAL_REPO_LOCAL report covers only the repo-local evidence loaded by `scripts/hodgecy_ii_universe_deep_dive.py --repo-local`. It is not a full-corpus exhaustive discovery report.",
        "",
        "## 84/84a-Like Sets: Same Local Source Inventory And Same Ordinary Hodge Data",
        "",
    ]
    append_sets(fidelity_lines, discovery["fixed_local_hodge_sets"])
    fidelity_lines.extend(["", "## 239/240/241-Like Sets: Repeated Local Inventory", ""])
    append_sets(fidelity_lines, discovery["local_inventory_fidelity_sets"])
    fidelity_lines.extend(["", "## Rational-Collapse / Integral-Separation Sets", ""])
    append_sets(fidelity_lines, discovery["rational_collapse_integral_sets"])
    fidelity_lines.extend(["", "## Integral-Collapse / Equivariant-Separation Sets", ""])
    append_sets(fidelity_lines, discovery["integral_collapse_equivariant_sets"])
    fidelity_lines.extend(["", "## Recurrent Rational Assembly Types", ""])
    append_sets(fidelity_lines, discovery["recurrent_assembly_types"]["rational"])
    fidelity_lines.extend(["", "## Recurrent Integral Assembly Types", ""])
    append_sets(fidelity_lines, discovery["recurrent_assembly_types"]["integral"])
    fidelity_lines.extend(["", "## Recurrent Equivariant Source Types", ""])
    append_sets(fidelity_lines, discovery["recurrent_assembly_types"]["equivariant"])
    fidelity_lines.extend(["", "## Unusual Prime/Torsion Patterns", ""])
    append_sets(fidelity_lines, discovery["unusual_prime_torsion_patterns"], member_key="arrangement_id")
    fidelity_lines.extend(["", "## Relevant Non-CKC Fidelity Examples", "", "- Supplemental Cynk-Meyer `84a` is present outside the CKC numbering and participates in the strongest fixed-local/Hodge source-level split found here."])
    fidelity_lines.extend(["", "## Possible Future Problem-7.10 Targets", ""])
    append_sets(fidelity_lines, discovery["problem_7_10_candidate_sets"])
    fidelity_lines.extend(
        [
            "",
            "## Emerging Structure",
            "",
            "The current repo-local evidence shows a hierarchy: local inventory can collapse multiple presentations, rational source assembly refines part of that collapse, integral Smith data refines more, and equivariant incidence data can still distinguish source presentations. The clearest source-level pattern remains the `84/84a/239/240/241` local fiber, with `84/84a` as the Hodge-refined source-level witness. This is not yet a node or LMHS statement.",
        ]
    )
    (OUT_ROOT / "exhaustive_fidelity_discovery_report.md").write_text("\n".join(fidelity_lines) + "\n", encoding="utf-8")

    notes = [
        "# HodgeCY II Discovery Notes",
        "",
        "- The older `research_outputs/hodgecy_ii/census` output is preserved as a fixed-equation pilot census.",
        "- The new universe pass does not use `census_eligible` as a scientific gate; every relevant CKC source row is represented with availability/provenance metadata.",
        "- `455` is valid for the CKC-numbered pairwise denominator, not for the complete v1.0.0 HodgeCY II research universe.",
        "- Production relationship traversal is handled by `scripts/hodgecy_full_corpus_doctor.py`; this repo-local notebook records those joins as out of scope.",
        "- Source assembly is kept separate from node/LMHS/Hodge-atom realization under the Problem 7.10 firewall.",
    ]
    (OUT_ROOT / "discovery_notes.md").write_text("\n".join(notes) + "\n", encoding="utf-8")


def append_sets(lines: list[str], sets: list[dict[str, Any]], *, member_key: str = "members") -> None:
    if not sets:
        lines.append("- None found in the repo-local evidence for this run.")
        return
    for item in sets:
        if member_key == "arrangement_id":
            member_text = str(item.get("arrangement_id"))
        else:
            members = item.get(member_key) or []
            member_text = ", ".join(str(member) for member in members)
        details = []
        for key in ("local_inventory", "hodge", "member_count", "integral_signature_count", "equivariant_signature_count", "source_level_result", "node_level_result"):
            if key in item:
                details.append(f"{key}={cell(item[key])}")
        lines.append(f"- `{item.get('set_id') or item.get('target_id') or item.get('arrangement_id')}`: {member_text}; " + "; ".join(details))


def compute_denominators(
    ckc_presentations: list[dict[str, Any]],
    cynk_records: list[dict[str, Any]],
    equation_records: list[dict[str, Any]],
    assembly_rows: list[dict[str, Any]],
    node_links: list[dict[str, Any]],
    operator_links: list[dict[str, Any]],
) -> dict[str, Any]:
    presentation_ids = {
        *(f"ckc:{row['ckc_id']}" for row in ckc_presentations),
        *(row["universe_id"] for row in equation_records),
        "supplemental:84a",
    }
    families = [row for row in ckc_presentations if row["entity_level"] == "PARAMETERIZED_FAMILY"]
    families.extend(row for row in equation_records if row["entity_level"] == "PARAMETERIZED_FAMILY")
    specializations = [row for row in ckc_presentations if row["entity_level"] == "PRESENTATION"]
    return {
        "TOTAL_RELEVANT_SOURCE_RECORDS": len(ckc_presentations) + len(cynk_records) + len(equation_records) + len(assembly_rows) + len(node_links) + len(operator_links),
        "DISTINCT_PRESENTATIONS": len(presentation_ids),
        "DISTINCT_PARAMETERIZED_FAMILIES": len(families),
        "DISTINCT_SPECIALIZATIONS": len(specializations),
        "DISTINCT_GEOMETRIES_WHERE_IDENTIFIABLE": "NOT_YET_RESOLVED",
        "CKC_NUMBERED_RECORDS": len(ckc_presentations),
        "CYNK_MEYER_RECORDS": len(cynk_records),
        "EXTERNAL_DOUBLE_OCTIC_RECORDS": len(ckc_presentations),
        "EXPLICIT_NODAL_CONIFOLD_RECORDS": len({row["arrangement_id"] for row in node_links}),
        "NODE_CONIFOLD_ARTIFACT_LINKS": len(node_links),
        "TRANSITION_RECORDS": 0,
        "OTHER_RELEVANT_RECORDS": len(equation_records) + len(assembly_rows) + len(operator_links),
        "UNRESOLVED_IDENTITY_RECORDS": len(ckc_presentations) + len(equation_records),
        "CKC_PAIRWISE_DENOMINATOR": 455,
        "CKC_PAIRWISE_COUNT": 103285,
        "COMPARABLE_SOURCE_PRESENTATION_COUNT_REPO_LOCAL": 456,
        "IS_COMPLETE_HODGECY_II_UNIVERSE_455": "NO",
    }


def run_repo_local() -> None:
    UNIVERSE_DIR.mkdir(parents=True, exist_ok=True)
    dataset_audit, corpus_summary = load_dataset_audit()
    ckc_payload, ckc_records = load_ckc_records()
    table1_rows = load_table1_rows()
    forgotten_rows = load_ckc_forgotten_rows()
    assemblies = load_source_assemblies()
    assembly_rows = build_assembly_rows(assemblies)
    assembly_by_id = {str(row["native_source_record_id"]): row for row in assembly_rows}

    ckc_presentations = build_ckc_presentations(ckc_records, table1_rows, forgotten_rows, {record.arrangement_id: record for record in assemblies})
    cynk_records = build_cynk_meyer_records(table1_rows)
    equation_records = build_equation_records()
    node_links = build_node_links()
    operator_links = build_operator_links(table1_rows)
    universe_records = [
        *({"universe_id": f"dataset:{row['dataset_id']}", **row} for row in dataset_audit),
        *ckc_presentations,
        *cynk_records,
        *equation_records,
        *assembly_rows,
    ]
    universe_relationships = build_relationship_rows(universe_records, node_links, operator_links)
    source_presentations = source_presentations_for_pairwise(ckc_presentations, table1_rows, assembly_rows)
    pairwise_rows = build_pairwise_rows(source_presentations)
    discovery = build_discovery_sets(source_presentations, assembly_rows, node_links)
    crosswalk = build_crosswalk(ckc_presentations, table1_rows, forgotten_rows, assembly_rows, node_links, operator_links)
    denominators = compute_denominators(ckc_presentations, cynk_records, equation_records, assembly_rows, node_links, operator_links)

    hodge_enrichments = []
    for arrangement_id, row in sorted(table1_rows.items(), key=lambda item: natural_arrangement_key(item[0])):
        hodge_enrichments.append({"arrangement_id": arrangement_id, "source_dataset": "cynk_meyer_table1", **{key: row.get(key) for key in (*INVENTORY_KEYS, *HODGE_KEYS, "rigid", "modular_form", "hodgecy_role")}})
    for arrangement_id, row in forgotten_rows.items():
        hodge_enrichments.append({"arrangement_id": arrangement_id, "source_dataset": "ckc_forgotten_arrangements_table", **row})

    output_paths = {
        "universe_records_jsonl": UNIVERSE_DIR / "universe_records.jsonl",
        "universe_records_parquet": UNIVERSE_DIR / "universe_records.parquet",
        "universe_relationships_tsv": UNIVERSE_DIR / "universe_relationships.tsv",
        "universe_manifest": UNIVERSE_DIR / "universe_manifest.json",
        "ckc455_crosswalk": OUT_ROOT / "ckc455_crosswalk.tsv",
        "all_source_presentations": OUT_ROOT / "all_source_presentations.parquet",
        "all_source_assembly_invariants": OUT_ROOT / "all_source_assembly_invariants.parquet",
        "all_source_symmetry_invariants": OUT_ROOT / "all_source_symmetry_invariants.parquet",
        "all_hodge_enrichments": OUT_ROOT / "all_hodge_enrichments.parquet",
        "all_node_conifold_links": OUT_ROOT / "all_node_conifold_links.parquet",
        "all_operator_fibration_arithmetic_links": OUT_ROOT / "all_operator_fibration_arithmetic_links.parquet",
        "all_pairwise_source_comparisons": OUT_ROOT / "all_pairwise_source_comparisons.parquet",
        "all_fixed_local_hodge_sets": OUT_ROOT / "all_fixed_local_hodge_sets.json",
        "all_local_inventory_fidelity_sets": OUT_ROOT / "all_local_inventory_fidelity_sets.json",
        "all_rational_collapse_integral_sets": OUT_ROOT / "all_rational_collapse_integral_sets.json",
        "all_integral_collapse_equivariant_sets": OUT_ROOT / "all_integral_collapse_equivariant_sets.json",
        "all_recurrent_assembly_types": OUT_ROOT / "all_recurrent_assembly_types.json",
        "all_problem_7_10_candidate_sets": OUT_ROOT / "all_problem_7_10_candidate_sets.json",
    }

    write_jsonl(output_paths["universe_records_jsonl"], universe_records)
    write_parquet(output_paths["universe_records_parquet"], universe_records)
    write_tsv(output_paths["universe_relationships_tsv"], universe_relationships)
    write_tsv(output_paths["ckc455_crosswalk"], crosswalk)
    write_parquet(output_paths["all_source_presentations"], source_presentations)
    write_parquet(output_paths["all_source_assembly_invariants"], assembly_rows)
    write_parquet(output_paths["all_source_symmetry_invariants"], [{key: row.get(key) for key in ("native_source_record_id", "automorphism_group_order", "plane_orbit_sizes", "double_line_orbit_sizes", "multiple_point_orbit_sizes", "equivariant_fingerprint", "claim_level_firewall")} for row in assembly_rows])
    write_parquet(output_paths["all_hodge_enrichments"], hodge_enrichments)
    write_parquet(output_paths["all_node_conifold_links"], node_links)
    write_parquet(output_paths["all_operator_fibration_arithmetic_links"], operator_links)
    write_parquet(output_paths["all_pairwise_source_comparisons"], pairwise_rows)
    write_json(output_paths["all_fixed_local_hodge_sets"], discovery["fixed_local_hodge_sets"])
    write_json(output_paths["all_local_inventory_fidelity_sets"], discovery["local_inventory_fidelity_sets"])
    write_json(output_paths["all_rational_collapse_integral_sets"], discovery["rational_collapse_integral_sets"])
    write_json(output_paths["all_integral_collapse_equivariant_sets"], discovery["integral_collapse_equivariant_sets"])
    write_json(output_paths["all_recurrent_assembly_types"], discovery["recurrent_assembly_types"])
    write_json(output_paths["all_problem_7_10_candidate_sets"], discovery["problem_7_10_candidate_sets"])

    manifest = {
        "schema": "hodgecy_ii_universe_deep_dive.v1",
        "corpus_summary": corpus_summary,
        "denominators": denominators,
        "dataset_audit_count": len(dataset_audit),
        "dataset_audit": dataset_audit,
        "ckc_index_summary": {key: ckc_payload.get(key) for key in ("total_expected_records", "records_loaded", "parser_coverage_complete", "full_validated_dataset_loaded", "validation_status")},
        "production_data_root": "PARTIAL_REPO_LOCAL_MODE_NOT_RECORDED",
        "production_relationship_tables_loaded": False,
        "problem_7_10_firewall": "source assembly is not node relation, LMHS, or Hodge atom realization without a natural comparison map",
        "outputs": {key: rel(path) for key, path in output_paths.items()},
        "output_sha256": {key: sha256_file(path) for key, path in output_paths.items() if path.exists()},
        "retired_filter_notice": "No new output uses census_eligible as a discovery gate; availability/provenance fields carry missingness.",
    }
    write_json(output_paths["universe_manifest"], manifest)
    build_reports(dataset_audit, corpus_summary, denominators, discovery)

    print("HodgeCY II universe deep dive complete:")
    print(f"- logical datasets audited: {len(dataset_audit)}")
    print(f"- CKC numbered records: {len(ckc_presentations)}")
    print(f"- repo-local comparable source presentations: {len(source_presentations)}")
    print(f"- pairwise comparisons: {len(pairwise_rows)}")
    print(f"- complete HodgeCY II universe is 455: {denominators['IS_COMPLETE_HODGECY_II_UNIVERSE_455']}")


def run_full_corpus_preflight(root: str | None = None) -> None:
    context = FullCorpusContext.open(root)
    context.assert_v1_ready()
    counts = context.summary_counts()
    print("HodgeCY II full-corpus context ready:")
    print(f"- logical datasets: {counts['logical_dataset_count']}")
    print(f"- dataset instances: {counts['instance_count']}")
    print(f"- physical sources: {counts['physical_source_count']}")
    print(f"- query tables: {counts['query_table_count']}")
    print(f"- relationship edges: {counts['relationship_edge_count']}")
    print("- discovery not run in activation/repair mode")


def main() -> None:
    parser = argparse.ArgumentParser(description="HodgeCY II universe entry point.")
    parser.add_argument("--root", default=None, help="Production HODGECY_DATA_ROOT for full-corpus mode.")
    parser.add_argument("--repo-local", action="store_true", help="Run the historical PARTIAL_REPO_LOCAL generator explicitly.")
    args = parser.parse_args()
    if args.repo_local:
        run_repo_local()
        return
    run_full_corpus_preflight(args.root)


if __name__ == "__main__":
    main()
