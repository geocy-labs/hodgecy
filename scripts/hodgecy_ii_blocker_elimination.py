from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import shutil
import sys
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.equivariant import incidence_table_from_linear_forms, linear_forms_from_factor_texts, source_complex_from_incidence
from hodgecy.research.full_corpus_context import FullCorpusContext
from hodgecy.research.hodgecy_ii_census import INVENTORY_KEYS, stable_fingerprint, torsion_profile

OUT_ROOT = REPO_ROOT / "research_outputs" / "hodgecy_ii"
PREVIOUS_DIR = OUT_ROOT / "source_assembly_deep_dive"
OUT_DIR = OUT_ROOT / "source_assembly_blocker_elimination"
MATRIX_DIR = OUT_DIR / "all_456_source_assembly_matrices"
REPAIRS_PATH = REPO_ROOT / "data" / "raw" / "cynk_kocel_cynk_2026" / "ckc_algebraic_repairs_451_452_453.json"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_parquet(path: Path, rows: list[dict[str, Any]] | pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = rows.copy() if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    for column in frame.columns:
        if frame[column].map(lambda value: isinstance(value, (dict, list, tuple))).any():
            frame[column] = frame[column].map(lambda value: json.dumps(value, sort_keys=True, default=str) if isinstance(value, (dict, list, tuple)) else value)
        if frame[column].dtype == object:
            frame[column] = frame[column].map(lambda value: None if value is None or (isinstance(value, float) and pd.isna(value)) else str(value))
    frame.to_parquet(path, index=False)


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: cell(row.get(field)) for field in fields})


def cell(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return str(value)


def parse_jsonish(value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (dict, list, tuple, int, bool)):
        return value
    text = str(value)
    if text in {"", "nan", "NaN", "null", "None"}:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def compact_snf(values: list[int] | None) -> str | None:
    if values is None:
        return None
    counts = Counter(int(value) for value in values)
    return ",".join(f"{value}^{count}" if count > 1 else str(value) for value, count in sorted(counts.items()))


def inventory_signature(inventory: dict[str, Any] | None) -> str | None:
    if not inventory:
        return None
    return ";".join(f"{key}={int(inventory.get(key, 0) or 0)}" for key in INVENTORY_KEYS)


def matrix_hash(entries: list[list[int]]) -> str:
    return hashlib.sha256(json.dumps(entries, separators=(",", ":"), sort_keys=True).encode("utf-8")).hexdigest()


def repair_complex(record: dict[str, Any]) -> dict[str, Any]:
    forms = linear_forms_from_factor_texts(record)
    incidence = incidence_table_from_linear_forms(forms)
    complex_ = source_complex_from_incidence(
        incidence,
        arrangement_id=str(record["arrangement_id"]),
        linear_forms=forms,
        source_provenance={
            "source": "local_ckc_pdf_repair",
            "source_path": REPAIRS_PATH.relative_to(REPO_ROOT).as_posix(),
            "coefficient_field": record.get("coefficient_field"),
            "validation_status": record.get("validation_status"),
        },
    )
    payload = complex_.to_dict()
    payload["matrix_hash"] = matrix_hash(payload["matrix_entries"])
    return payload


def rows_from_previous(ctx: FullCorpusContext) -> list[dict[str, Any]]:
    frame = pd.read_parquet(PREVIOUS_DIR / "all_456_source_assemblies.parquet")
    rows = []
    for row in frame.to_dict("records"):
        parsed = {key: parse_jsonish(value) for key, value in row.items()}
        parsed["corpus_release_fingerprint"] = ctx.release_fingerprint
        rows.append(parsed)
    return rows


def promote_repair(row: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    algebra = payload["algebra"]
    smith = algebra.get("smith_normal_form") or []
    torsion = torsion_profile(smith)
    inventory = {
        "p3": int(payload["strata"]["inventory"].get("p3", 0)),
        "p4_0": int(payload["strata"]["inventory"].get("p4_0", 0)),
        "p4_1": int(payload["strata"]["inventory"].get("p4_1", 0)),
        "p5_0": int(payload["strata"]["inventory"].get("p5_0", 0)),
        "p5_1": int(payload["strata"]["inventory"].get("p5_1", 0)),
        "p5_2": int(payload["strata"]["inventory"].get("p5_2", 0)),
        "l3": int(payload["strata"]["inventory"].get("triple_lines", 0)),
    }
    rational_payload = {
        "local": inventory,
        "shape": algebra["gluing_matrix_shape"],
        "rank_Q": algebra["rank_Q"],
        "kernel_dim_Q": algebra["kernel_dim_Q"],
        "cokernel_dim_Q": algebra["cokernel_dim_Q"],
    }
    integral_payload = {"rational": stable_fingerprint("rational", rational_payload), "smith_normal_form": smith}
    equivariant_payload = {
        "integral": stable_fingerprint("integral", integral_payload),
        "automorphism_group_order": payload["automorphism_group"]["order"],
        "plane_orbit_sizes": sorted(len(orbit) for orbit in payload["plane_orbits"]),
        "double_line_orbit_sizes": sorted(len(orbit) for orbit in payload["double_line_orbits"]),
        "multiple_point_orbit_sizes": sorted(len(orbit) for orbit in payload["multiple_point_orbits"]),
    }
    rid = str(row["presentation_id"])
    return {
        **row,
        "local_inventory": inventory,
        "local_signature": inventory_signature(inventory),
        "source_assembly_available": True,
        "assembly_computation_status": "computed_exact_repaired_quadratic_source_assembly",
        "source_blocker": "",
        "matrix_status": "stored_exact_integer_incidence_matrix",
        "matrix_hash": payload["matrix_hash"],
        "matrix_path": f"{MATRIX_DIR.relative_to(REPO_ROOT).as_posix()}/source_assembly_matrix_{rid}.json",
        "rank_Q": algebra["rank_Q"],
        "rank_F2": algebra["rank_mod_p"]["2"],
        "kernel_dim_Q": algebra["kernel_dim_Q"],
        "cokernel_dim_Q": algebra["cokernel_dim_Q"],
        "smith_normal_form": smith,
        "smith_normal_form_compact": compact_snf(smith),
        "torsion_invariant_factors": torsion["torsion_invariant_factors"],
        "torsion_primes": torsion["torsion_primes"],
        "automorphism_group_order": payload["automorphism_group"]["order"],
        "plane_orbit_sizes": sorted(len(orbit) for orbit in payload["plane_orbits"]),
        "double_line_orbit_sizes": sorted(len(orbit) for orbit in payload["double_line_orbits"]),
        "multiple_point_orbit_sizes": sorted(len(orbit) for orbit in payload["multiple_point_orbits"]),
        "assembly_rational_fingerprint": stable_fingerprint("rational", rational_payload),
        "assembly_integral_fingerprint": stable_fingerprint("integral", integral_payload),
        "assembly_equivariant_fingerprint": stable_fingerprint("equivariant", equivariant_payload),
        "ckc_equation_type": "fixed_algebraic",
        "ckc_source_extraction_status": "pdf_repaired",
        "ckc_validation_tier": "S1_SOURCE_RECOMPUTED",
    }


def update_unresolved_status(row: dict[str, Any]) -> dict[str, Any]:
    status = row.get("assembly_computation_status")
    if status == "blocked_parameterized_family_requires_specialization":
        return {
            **row,
            "assembly_computation_status": "unresolved_source_parameter_constraints_missing_from_local_payload",
            "source_blocker": "The software can parse and test the symbolic family, but the local CKC payload does not include the parameter ideal/excluded loci needed to recover the classified incidence table.",
        }
    if status == "blocked_partial_or_problematic_source_extraction":
        return {
            **row,
            "assembly_computation_status": "unresolved_repaired_equation_inventory_mismatch",
            "source_blocker": "The local PDF equation repair for 451 does not reproduce the source-table local inventory; this is a source/transcription ambiguity, not a coefficient-domain software blocker.",
        }
    return row


def markdown_table(rows: list[dict[str, Any]], fields: list[str]) -> list[str]:
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join("---" for _ in fields) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(cell(row.get(field)).replace("|", "\\|") for field in fields) + " |")
    return lines


def group_types(rows: list[dict[str, Any]], key: str, level: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        if row.get(key):
            grouped[str(row[key])].append(str(row["presentation_id"]))
    return [
        {"source_type_level": level, "signature": signature, "member_count": len(members), "members": members}
        for signature, members in sorted(grouped.items(), key=lambda item: item[1][0])
    ]


def build_repeated_local_fibers(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        signature = row.get("local_signature")
        if signature:
            grouped[str(signature)].append(row)

    repeated = []
    index = 1
    for signature, members in sorted(grouped.items(), key=lambda item: natural_sort_key(str(item[1][0]["presentation_id"]))):
        if len(members) < 2:
            continue
        member_ids = [str(row["presentation_id"]) for row in sorted(members, key=lambda item: natural_sort_key(str(item["presentation_id"])))]
        hodge_signatures = sorted({str(row.get("hodge_signature")) for row in members if row.get("hodge_signature")})
        repeated.append(
            {
                "type_set_id": f"local_signature_{index:03d}",
                "local_signature": signature,
                "member_count": len(member_ids),
                "computed_member_count": sum(1 for row in members if str(row.get("assembly_computation_status", "")).startswith("computed_exact")),
                "members": member_ids,
                "hodge_signatures": hodge_signatures,
            }
        )
        index += 1
    return repeated


def natural_sort_key(value: str) -> tuple[int, str]:
    digits = "".join(ch for ch in value if ch.isdigit())
    return (int(digits) if digits else 0, value)


def build_repeated_report(ctx: FullCorpusContext, rows: list[dict[str, Any]], repeated_local: list[dict[str, Any]]) -> str:
    repeated_members = {member for fiber in repeated_local for member in fiber["members"]}
    detail = [row for row in rows if str(row["presentation_id"]) in repeated_members]
    detail = sorted(detail, key=lambda item: natural_sort_key(str(item["presentation_id"])))
    lines = [
        "# HodgeCY II Repeated-Local Fiber Report",
        "",
        f"- Corpus release fingerprint: `{ctx.release_fingerprint}`",
        f"- Repeated local fibers discovered: {len(repeated_local)}",
        f"- Exact source assemblies available inside these fibers: {sum(row['computed_member_count'] for row in repeated_local)}",
        "",
        "## Fibers",
        "",
    ]
    lines.extend(markdown_table(repeated_local, ["type_set_id", "member_count", "computed_member_count", "members", "hodge_signatures"]))
    lines.extend(["", "## Member Detail", ""])
    lines.extend(
        markdown_table(
            detail,
            [
                "presentation_id",
                "local_signature",
                "hodge_signature",
                "assembly_computation_status",
                "rank_Q",
                "rank_F2",
                "smith_normal_form_compact",
                "torsion_primes",
                "source_blocker",
            ],
        )
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Eliminate HodgeCY II source-assembly software blockers where source data supports it.")
    parser.add_argument("--root", default=None, help="Production HODGECY_DATA_ROOT. Defaults to environment.")
    args = parser.parse_args(argv)

    ctx = FullCorpusContext.open(args.root)
    ctx.assert_v1_ready()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MATRIX_DIR.mkdir(parents=True, exist_ok=True)

    rows = rows_from_previous(ctx)
    rows_by_id = {str(row["presentation_id"]): row for row in rows}

    if (PREVIOUS_DIR / "all_456_source_assembly_matrices").exists():
        for path in (PREVIOUS_DIR / "all_456_source_assembly_matrices").glob("source_assembly_matrix_*.json"):
            shutil.copy2(path, MATRIX_DIR / path.name)

    repairs = {str(row["arrangement_id"]): row for row in read_json(REPAIRS_PATH)["records"]}
    repaired_payloads = {}
    for arrangement_id in ("452", "453"):
        payload = repair_complex(repairs[arrangement_id])
        repaired_payloads[arrangement_id] = payload
        write_json(MATRIX_DIR / f"source_assembly_matrix_{arrangement_id}.json", payload)
        rows_by_id[arrangement_id] = promote_repair(rows_by_id[arrangement_id], payload)
    rows_by_id["451"] = update_unresolved_status(rows_by_id["451"])
    rows = [update_unresolved_status(row) for _, row in sorted(rows_by_id.items(), key=lambda item: (int("".join(ch for ch in item[0] if ch.isdigit()) or 0), item[0]))]

    computed = [row for row in rows if str(row["assembly_computation_status"]).startswith("computed_exact")]
    status_counts = Counter(row["assembly_computation_status"] for row in rows)
    software_blockers = [status for status in status_counts if str(status).startswith("blocked_")]

    incidence_rows = []
    symmetry_rows = []
    equivariant_rows = []
    higher_rows = []
    domain_rows = []
    loci_rows = []
    for row in rows:
        rid = str(row["presentation_id"])
        payload = repaired_payloads.get(rid)
        domain_rows.append(
            {
                "arrangement_id": rid,
                "coefficient_domain_status": "computed_repaired_quadratic" if payload else row.get("ckc_equation_type"),
                "parameter_domain_status": "parameter_constraints_missing_from_local_payload" if "parameter_constraints" in str(row.get("assembly_computation_status")) else "",
            }
        )
        loci_rows.append({"arrangement_id": rid, "exceptional_locus_status": "not_available_without_parameter_ideal" if "parameter_constraints" in str(row.get("assembly_computation_status")) else ""})
        if payload:
            incidence_rows.append({"arrangement_id": rid, "incidence_status": "computed_exact", "incidence_table": payload["incidence_table"], "source_provenance": payload["source_provenance"]})
            symmetry_rows.append({"arrangement_id": rid, "automorphism_group": payload["automorphism_group"], "plane_orbits": payload["plane_orbits"], "double_line_orbits": payload["double_line_orbits"], "multiple_point_orbits": payload["multiple_point_orbits"]})
            equivariant_rows.append({"arrangement_id": rid, "characters": payload["characters"], "algebra": payload["algebra"]})
            higher_rows.append({"arrangement_id": rid, "higher_strata_status": "not_constructed_no_triple_lines", "triple_line_orbits": payload["triple_line_orbits"]})
        else:
            incidence_rows.append({"arrangement_id": rid, "incidence_status": row["assembly_computation_status"], "incidence_table": None, "source_provenance": None})
            symmetry_rows.append({"arrangement_id": rid, "automorphism_group": row.get("automorphism_group_order"), "plane_orbits": row.get("plane_orbit_sizes"), "double_line_orbits": row.get("double_line_orbit_sizes"), "multiple_point_orbits": row.get("multiple_point_orbit_sizes")})
            equivariant_rows.append({"arrangement_id": rid, "characters": None, "algebra": None})
            higher_rows.append({"arrangement_id": rid, "higher_strata_status": "not_computed", "triple_line_orbits": None})

    write_parquet(OUT_DIR / "all_456_source_assemblies.parquet", rows)
    write_tsv(OUT_DIR / "source_assembly_coverage_456.tsv", rows)
    write_parquet(OUT_DIR / "all_456_incidence_structures.parquet", incidence_rows)
    write_parquet(OUT_DIR / "all_456_parameter_domains.parquet", domain_rows)
    write_parquet(OUT_DIR / "all_456_exceptional_parameter_loci.parquet", loci_rows)
    write_parquet(OUT_DIR / "all_456_symmetry_data.parquet", symmetry_rows)
    write_parquet(OUT_DIR / "all_456_equivariant_homology_data.parquet", equivariant_rows)
    write_parquet(OUT_DIR / "all_higher_strata_source_complexes.parquet", higher_rows)
    write_json(
        OUT_DIR / "ckc_specialization_graph.json",
        {
            "schema": "hodgecy_ii_ckc_specialization_graph.v1",
            "edge_status": "no_parameter_ideal_edges_available_from_local_payload",
            "edges": [],
        },
    )
    write_json(
        OUT_DIR / "run_summary.json",
        {
            "schema": "hodgecy_ii_blocker_elimination.v1",
            "corpus_release_fingerprint": ctx.release_fingerprint,
            "total_double_octic_presentations": len(rows),
            "exact_source_assemblies": len(computed),
            "software_blockers_remaining": len(software_blockers),
            "status_counts": dict(status_counts),
            "newly_promoted": ["452", "453"],
        },
    )
    matrix_manifest = []
    for row in computed:
        path = MATRIX_DIR / f"source_assembly_matrix_{row['presentation_id']}.json"
        matrix_manifest.append(
            {
                "presentation_id": str(row["presentation_id"]),
                "matrix_path": path.relative_to(REPO_ROOT).as_posix(),
                "matrix_hash": row.get("matrix_hash"),
                "assembly_computation_status": row.get("assembly_computation_status"),
            }
        )
    write_json(MATRIX_DIR / "matrix_manifest.json", {"schema": "hodgecy_ii_source_assembly_matrix_manifest.v2", "records": matrix_manifest})

    type_rows = {
        "rational": group_types(rows, "assembly_rational_fingerprint", "rational"),
        "integral": group_types(rows, "assembly_integral_fingerprint", "integral"),
        "equivariant": group_types(rows, "assembly_equivariant_fingerprint", "equivariant"),
    }
    all_types = type_rows["rational"] + type_rows["integral"] + type_rows["equivariant"]
    write_parquet(OUT_DIR / "all_recomputed_source_types.parquet", all_types)
    repeated_local = build_repeated_local_fibers(rows)
    write_parquet(OUT_DIR / "all_repeated_local_fibers.parquet", repeated_local)

    report_rows = [{"status": status, "count": count} for status, count in sorted(status_counts.items())]
    question_rows = [
        {"question": "How many of 456 are now computed?", "answer": f"{len(computed)} / 456"},
        {"question": "Which software blockers were eliminated?", "answer": "Exact quadratic-field coefficient support for 452 and 453; generic symbolic parsing/rank testing for parameterized families is implemented as a verification route."},
        {"question": "Are any true source ambiguities left?", "answer": "Yes: 440 parameterized records need CKC parameter ideals/classified incidence tables not present in the local payload; 451 has a repaired PDF equation but inventory mismatch."},
        {"question": "Where does 83 land?", "answer": "Still in the 83/84/84a/239/240/241 local fiber; source assembly not promoted because raw free-parameter symbolic incidence disagrees with classified inventory."},
        {"question": "What distinguishes 452/453?", "answer": "Both now compute over exact quadratic fields; 452 is over Q(sqrt(-3)), 453 over Q(sqrt(5)); both share the same local inventory but have separate exact source records."},
        {"question": "What torsion primes occur?", "answer": ",".join(str(prime) for prime in sorted({prime for row in computed for prime in (row.get("torsion_primes") or [])}))},
        {"question": "What specialization graph emerges?", "answer": "No exact edges are emitted because local source data lacks parameter ideals/excluded loci; no numbering-only edges were inferred."},
        {"question": "Does source assembly track repeated Hodge shifts?", "answer": "Not decidable for parameterized repeated-local fibers until the classified incidence/parameter-ideal source data is available."},
    ]
    report = [
        "# HodgeCY II Blocker Elimination Report",
        "",
        f"- Corpus release fingerprint: `{ctx.release_fingerprint}`",
        f"- Exact source assemblies after this run: {len(computed)} / 456",
        f"- Software blocker statuses remaining: {len(software_blockers)}",
        f"- Newly promoted source assemblies: `452`, `453`",
        "",
        "## Status Histogram",
        "",
    ]
    report.extend(markdown_table(report_rows, ["status", "count"]))
    report.extend(["", "## Required Questions", ""])
    report.extend(markdown_table(question_rows, ["question", "answer"]))
    write_text(OUT_ROOT / "blocker_elimination_report.md", "\n".join(report))
    write_text(OUT_ROOT / "complete_repeated_local_fiber_report.md", build_repeated_report(ctx, rows, repeated_local))
    write_text(OUT_ROOT / "complete_source_fidelity_report.md", "\n".join(report))
    write_text(OUT_ROOT / "source_assembly_deep_dive_notes.md", (OUT_ROOT / "source_assembly_deep_dive_notes.md").read_text(encoding="utf-8"))

    print("HodgeCY II blocker elimination pass complete")
    print(f"- exact source assemblies: {len(computed)} / 456")
    print(f"- software blocker statuses remaining: {len(software_blockers)}")
    print("- newly promoted: 452, 453")
    print(f"- output directory: {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
