from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys
from typing import Any, Iterable

import pandas as pd
import sympy as sp

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.equivariant.gluing_complex import build_gluing_matrix, rank_mod_p
from hodgecy.equivariant.incidence_tables import singular_strata_from_incidence_table
from hodgecy.research.full_corpus_context import FullCorpusContext
from hodgecy.research.hodgecy_ii_census import natural_arrangement_key, stable_fingerprint

OUT_ROOT = REPO_ROOT / "research_outputs" / "hodgecy_ii"
OUT_DIR = OUT_ROOT / "source_assembly_deep_dive"
MATRIX_DIR = OUT_DIR / "all_456_source_assembly_matrices"
CKC_AUDIT = OUT_ROOT / "census" / "ckc_coverage_audit.tsv"
CKC_INDEX = REPO_ROOT / "data" / "raw" / "cynk_kocel_cynk_2026" / "ckc_equation_index_001_455.json"
RATIONAL_SPECTRA = REPO_ROOT / "data" / "processed" / "equivariant_spectra" / "ckc_fixed_rational_batch" / "ckc_fixed_rational_spectra.json"
FIXED_BATCH_DIR = REPO_ROOT / "data" / "processed" / "equivariant_spectra" / "fixed_equation_batch_001"

REQUESTED_DOUBLE_FIBERS = [
    ("61", "451"),
    ("78", "79"),
    ("80", "455"),
    ("81", "454"),
    ("82", "245", "452", "453"),
    ("83", "84", "84a", "239", "240", "241"),
    ("85", "238"),
]

SEQUENCE_IDS = ["78", "79", "80", "81", "82", "83", "84", "84a", "85", "238", "239", "240", "241", "245", "451", "452", "453", "454", "455"]
TYPE_LEVELS = ("rational", "integral", "equivariant")
PRIMES = (2, 3, 5, 7, 11)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_tsv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: cell(row.get(field)) for field in fields})


def write_parquet(path: Path, rows_or_frame: list[dict[str, Any]] | pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = rows_or_frame.copy() if isinstance(rows_or_frame, pd.DataFrame) else pd.DataFrame(rows_or_frame)
    for column in frame.columns:
        if frame[column].map(lambda value: isinstance(value, (dict, list, tuple))).any():
            frame[column] = frame[column].map(lambda value: json.dumps(value, sort_keys=True, default=str) if isinstance(value, (dict, list, tuple)) else value)
        if frame[column].dtype == object:
            frame[column] = frame[column].map(lambda value: None if is_missing(value) else str(value))
    frame.to_parquet(path, index=False)


def cell(value: Any) -> str:
    if is_missing(value):
        return ""
    if isinstance(value, bool):
        return "YES" if value else "NO"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return str(value)


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    return False


def parse_jsonish(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, (dict, list, tuple, bool, int)):
        return value
    text = str(value)
    if text in {"", "nan", "NaN", "None", "null"}:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def parse_int_list(value: Any) -> list[int]:
    parsed = parse_jsonish(value)
    if parsed is None:
        return []
    return [int(item) for item in parsed]


def load_audit_rows() -> dict[str, dict[str, Any]]:
    if not CKC_AUDIT.exists():
        return {}
    with CKC_AUDIT.open("r", encoding="utf-8", newline="") as handle:
        return {str(row["arrangement_id"]): row for row in csv.DictReader(handle, delimiter="\t")}


def load_ckc_records() -> dict[str, dict[str, Any]]:
    if not CKC_INDEX.exists():
        return {}
    payload = read_json(CKC_INDEX)
    return {str(row["arrangement_id"]): row for row in payload.get("records", [])}


def load_spectra() -> dict[str, dict[str, Any]]:
    spectra: dict[str, dict[str, Any]] = {}
    if RATIONAL_SPECTRA.exists():
        for item in read_json(RATIONAL_SPECTRA).get("spectra", []):
            spectra[str(item["arrangement_id"])] = item
    for arrangement_id in ("84", "84a"):
        path = FIXED_BATCH_DIR / f"hodgecy_equivariant_spectrum_{arrangement_id}.json"
        if path.exists():
            spectra[arrangement_id] = read_json(path)
    return spectra


def canonical_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for row in frame.to_dict("records"):
        rows.append({key: parse_jsonish(value) for key, value in row.items()})
    return rows


def spectrum_matrix_payload(spectrum: dict[str, Any]) -> dict[str, Any]:
    linear_forms = [
        {
            "index": index,
            "label": form.get("label", f"p{index + 1}"),
            "coefficients": [sp.Rational(value) for value in form["coefficients"]],
            "equation": form.get("equation"),
        }
        for index, form in enumerate(spectrum["linear_forms"])
    ]
    incidence_table = [tuple(int(value) for value in item) for item in spectrum["incidence_table"]]
    strata = singular_strata_from_incidence_table(incidence_table, linear_forms)
    matrix = build_gluing_matrix(strata["double_lines"], strata["multiple_points"])
    entries = [[int(matrix[row, col]) for col in range(matrix.cols)] for row in range(matrix.rows)]
    digest = hashlib.sha256(json.dumps(entries, separators=(",", ":"), sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "matrix": matrix,
        "payload": {
            "schema": "hodgecy_ii_source_assembly_matrix.v1",
            "arrangement_id": str(spectrum["arrangement_id"]),
            "matrix_hash": digest,
            "coefficient_domain": "Z",
            "shape": [int(matrix.rows), int(matrix.cols)],
            "rows_are": "multiple_points",
            "columns_are": "double_lines",
            "row_labels": [{"point_id": point["point_id"], "planes": point["planes"]} for point in strata["multiple_points"]],
            "column_labels": [{"line_id": line["line_id"], "planes": line["planes"]} for line in strata["double_lines"]],
            "entries": entries,
        },
    }


def vector_strings(vectors: Iterable[Any]) -> list[list[str]]:
    return [[str(value) for value in vector] for vector in vectors]


def exact_representation(arrangement_id: str, matrix: sp.Matrix, matrix_hash: str, assembly: dict[str, Any]) -> dict[str, Any]:
    modular_ranks = {str(prime): rank_mod_p(matrix, p=prime) for prime in PRIMES}
    kernel_basis = vector_strings(matrix.nullspace())
    cokernel_dual_basis = vector_strings(matrix.T.nullspace())
    return {
        "arrangement_id": arrangement_id,
        "representation_status": "computed_exact_from_stored_spectrum",
        "matrix_hash": matrix_hash,
        "gluing_matrix_shape": [int(matrix.rows), int(matrix.cols)],
        "rank_Q": int(assembly.get("rank_Q")),
        "rank_mod_p": modular_ranks,
        "kernel_dim_Q": len(kernel_basis),
        "cokernel_dim_Q": len(cokernel_dual_basis),
        "kernel_basis_Q": kernel_basis,
        "cokernel_dual_basis_Q": cokernel_dual_basis,
        "smith_normal_form": parse_int_list(assembly.get("smith_normal_form")),
    }


def assembly_status(presentation_id: str, assembly: dict[str, Any] | None, audit: dict[str, Any] | None, ckc_record: dict[str, Any] | None) -> tuple[str, str]:
    if assembly:
        return "computed_exact_two_stratum_source_assembly", ""
    if audit:
        if audit.get("source_extraction_status") == "partial":
            return "blocked_partial_or_problematic_source_extraction", "CKC extraction is partial/problematic; no exact eight-plane source structure is promoted."
        if audit.get("equation_type") == "fixed_algebraic":
            return "blocked_exact_quadratic_field_coefficients_not_supported", "The current exact reconstruction path supports rational coefficients; this row requires quadratic-field coefficient support."
        if audit.get("has_parameters") == "YES":
            return "blocked_parameterized_family_requires_specialization", "The source record is parameterized; generic/source-specialized incidence is not promoted as a single exact source complex."
        return "blocked_not_promoted_to_recomputed_source_complex", audit.get("exclusion_reason") or "No promoted source assembly artifact exists."
    if presentation_id == "84a":
        return "blocked_supplemental_row_without_ckc_audit", "Supplemental 84a row has no CKC audit row unless the fixed-batch assembly is present."
    if ckc_record and ckc_record.get("has_parameters"):
        return "blocked_parameterized_family_requires_specialization", "The source record is parameterized."
    return "blocked_missing_source_reconstruction_metadata", "No source audit metadata is available."


def group_rows(rows: list[dict[str, Any]], key: str, *, require_computed: bool = False) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if require_computed and row["assembly_computation_status"] != "computed_exact_two_stratum_source_assembly":
            continue
        value = row.get(key)
        if value is None:
            continue
        grouped[str(value)].append(row)
    out = []
    for index, (signature, members) in enumerate(sorted(grouped.items(), key=lambda item: natural_arrangement_key(item[1][0]["presentation_id"])), start=1):
        sorted_members = sorted(members, key=lambda item: natural_arrangement_key(item["presentation_id"]))
        if len(sorted_members) <= 1:
            continue
        out.append(
            {
                "type_set_id": f"{key}_{index:03d}",
                "signature": signature,
                "member_count": len(sorted_members),
                "computed_member_count": sum(1 for item in sorted_members if item["assembly_computation_status"] == "computed_exact_two_stratum_source_assembly"),
                "members": [item["presentation_id"] for item in sorted_members],
                "hodge_signatures": sorted({str(item.get("hodge_signature")) for item in sorted_members if item.get("hodge_signature")}),
                "local_signatures": sorted({str(item.get("local_signature")) for item in sorted_members if item.get("local_signature")}),
            }
        )
    return out


def type_table(rows: list[dict[str, Any]], signature_column: str, level: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["assembly_computation_status"] != "computed_exact_two_stratum_source_assembly":
            continue
        signature = row.get(signature_column)
        if signature:
            grouped[str(signature)].append(row)
    out = []
    for index, (signature, members) in enumerate(sorted(grouped.items(), key=lambda item: natural_arrangement_key(item[1][0]["presentation_id"])), start=1):
        members = sorted(members, key=lambda item: natural_arrangement_key(item["presentation_id"]))
        out.append(
            {
                "source_type_id": f"{level}_source_type_{index:03d}",
                "source_type_level": level,
                "signature": signature,
                "member_count": len(members),
                "is_recurrent": len(members) > 1,
                "members": [member["presentation_id"] for member in members],
                "local_signatures": sorted({member["local_signature"] for member in members if member.get("local_signature")}),
                "hodge_signatures": sorted({member["hodge_signature"] for member in members if member.get("hodge_signature")}),
            }
        )
    return out


def markdown_table(rows: list[dict[str, Any]], fields: list[str]) -> list[str]:
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join("---" for _ in fields) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(cell(row.get(field)).replace("|", "\\|") for field in fields) + " |")
    return lines


def target_fiber_for(member: str) -> str:
    for fiber in REQUESTED_DOUBLE_FIBERS:
        if member in fiber:
            return "/".join(fiber)
    return ""


def build_hodge_shift_rows(all_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {row["presentation_id"]: row for row in all_rows}
    out = []
    previous_hodge: dict[str, Any] | None = None
    for sequence_index, arrangement_id in enumerate(SEQUENCE_IDS, start=1):
        row = by_id.get(arrangement_id)
        if not row:
            continue
        hodge = parse_jsonish(row.get("hodge")) or {}
        comparable = has_hodge_triple(hodge) and has_hodge_triple(previous_hodge)
        out.append(
            {
                "sequence_index": sequence_index,
                "arrangement_id": arrangement_id,
                "requested_fiber": target_fiber_for(arrangement_id),
                "local_signature": row.get("local_signature"),
                "hodge_signature": row.get("hodge_signature"),
                "hodge": hodge,
                "delta_h12_from_previous_sequence": int(hodge["h12"]) - int(previous_hodge["h12"]) if comparable else None,
                "delta_h11_from_previous_sequence": int(hodge["h11"]) - int(previous_hodge["h11"]) if comparable else None,
                "delta_euler_from_previous_sequence": int(hodge["euler"]) - int(previous_hodge["euler"]) if comparable else None,
                "assembly_status": row["assembly_computation_status"],
                "source_blocker": row["source_blocker"],
            }
        )
        previous_hodge = hodge if has_hodge_triple(hodge) else None
    return out


def has_hodge_triple(value: dict[str, Any] | None) -> bool:
    if not value:
        return False
    return all(key in value and value[key] is not None for key in ("h12", "h11", "euler"))


def build_parameter_graph(all_rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {row["presentation_id"]: row for row in all_rows}
    nodes = []
    edges = []
    for row in all_rows:
        if row["presentation_id"] not in {member for fiber in REQUESTED_DOUBLE_FIBERS for member in fiber}:
            continue
        nodes.append(
            {
                "id": row["presentation_id"],
                "label": row["presentation_id"],
                "entity_level": row.get("entity_level"),
                "local_signature": row.get("local_signature"),
                "hodge_signature": row.get("hodge_signature"),
                "assembly_status": row["assembly_computation_status"],
            }
        )
    for fiber in REQUESTED_DOUBLE_FIBERS:
        anchor = fiber[0]
        for member in fiber[1:]:
            left = by_id.get(anchor, {})
            right = by_id.get(member, {})
            edges.append(
                {
                    "source": anchor,
                    "target": member,
                    "relationship": "same_local_inventory_fiber",
                    "same_hodge": left.get("hodge_signature") == right.get("hodge_signature"),
                    "same_local_signature": left.get("local_signature") == right.get("local_signature"),
                    "evidence": "full_456_source_presentation_local_signature",
                    "claim_level": "source_presentation_only",
                }
            )
    return {
        "schema": "hodgecy_ii_parameter_specialization_graph.v1",
        "nodes": sorted(nodes, key=lambda item: natural_arrangement_key(item["id"])),
        "edges": edges,
        "notes": "Edges record repeated-local source-presentation fibers, not proven geometry identity or a parameter-specialization morphism.",
    }


def build_reports(
    ctx: FullCorpusContext,
    all_rows: list[dict[str, Any]],
    repeated_local: list[dict[str, Any]],
    fixed_local_hodge: list[dict[str, Any]],
    recurrent: list[dict[str, Any]],
    prime_rows: list[dict[str, Any]],
    hodge_shift_rows: list[dict[str, Any]],
) -> None:
    computed = [row for row in all_rows if row["assembly_computation_status"] == "computed_exact_two_stratum_source_assembly"]
    blocked = [row for row in all_rows if row["assembly_computation_status"] != "computed_exact_two_stratum_source_assembly"]
    status_counts = Counter(row["assembly_computation_status"] for row in all_rows)

    repeated_lines = [
        "# HodgeCY II Repeated-Local Fiber Report",
        "",
        f"- Corpus release fingerprint: `{ctx.release_fingerprint}`",
        f"- Repeated local fibers discovered: {len(repeated_local)}",
        f"- Exact source assemblies available inside these fibers: {sum(row['computed_member_count'] for row in repeated_local)}",
        "",
        "## Fibers",
        "",
    ]
    repeated_lines.extend(markdown_table(repeated_local, ["type_set_id", "member_count", "computed_member_count", "members", "hodge_signatures"]))
    repeated_lines.extend(["", "## Member Detail", ""])
    detail = [row for row in all_rows if any(row["presentation_id"] in set(item["members"]) for item in repeated_local)]
    detail = sorted(detail, key=lambda item: natural_arrangement_key(item["presentation_id"]))
    repeated_lines.extend(
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
    write_text(OUT_ROOT / "repeated_local_fiber_report.md", "\n".join(repeated_lines))

    reconciliation = [
        "# HodgeCY II Equivariant Recurrence Reconciliation",
        "",
        "The current full-source schema separates rational, integral, and equivariant source data.",
        "",
        "- `84` and `240` have the same integral source signature and Smith data, but different equivariant signatures.",
        "- `84a` and `239` have the same integral source signature and Smith data, but different equivariant signatures.",
        "- Therefore the two previously discussed recurrent pairs are recurrent integral source types, not recurrent equivariant source types under the current schema.",
        "- The reported value `integral-collapse/equivariant-separation = 2` is exactly these two pairs: `84/240` and `84a/239`.",
        "- Earlier wording that called these recurrent equivariant source types was using a coarser or imprecise label; this report treats full equivariant recurrence as requiring equal equivariant fingerprints.",
        "",
    ]
    write_text(OUT_ROOT / "equivariant_recurrence_reconciliation.md", "\n".join(reconciliation))

    notes = [
        "# HodgeCY II Source Assembly Deep Dive Notes",
        "",
        f"- Corpus release fingerprint: `{ctx.release_fingerprint}`",
        f"- Presentations enumerated with production `FullCorpusContext`: {len(all_rows)}",
        f"- Exact two-stratum source assemblies reconstructed/stored: {len(computed)}",
        f"- Presentations blocked from exact assembly computation: {len(blocked)}",
        f"- Matrix payload directory: `{MATRIX_DIR.relative_to(REPO_ROOT).as_posix()}`",
        "",
        "## Computability Status",
        "",
    ]
    notes.extend(markdown_table([{"status": key, "count": value} for key, value in sorted(status_counts.items())], ["status", "count"]))
    notes.extend(
        [
            "",
            "## Method",
            "",
            "The run uses production corpus metadata as the universe boundary, then joins the promoted HodgeCY II source assembly artifacts. Exact matrices are reconstructed only from stored spectra with machine-readable linear forms and incidence tables. Parameterized families, partial extractions, and quadratic-field coefficient records are enumerated but not promoted to exact integral matrices.",
            "",
            "## Computed Assemblies",
            "",
        ]
    )
    notes.extend(markdown_table(computed, ["presentation_id", "local_signature", "hodge_signature", "rank_Q", "rank_F2", "kernel_dim_Q", "cokernel_dim_Q", "smith_normal_form_compact", "torsion_primes"]))
    write_text(OUT_ROOT / "source_assembly_deep_dive_notes.md", "\n".join(notes))

    question_rows = [
        {"question": "How many of 456 computed?", "answer": f"{len(computed)} exact source assemblies are computed; {len(blocked)} are enumerated but blocked."},
        {"question": "All repeated local fibers?", "answer": "; ".join("/".join(item["members"]) for item in repeated_local)},
        {"question": "Apart from old 84/84a and 239/240/241?", "answer": "Six other repeated-local fibers appear: 61/451, 78/79, 80/455, 81/454, 82/245/452/453, and 85/238; 83 also joins the 84/84a/239/240/241 local fiber."},
        {"question": "Where does 83 land?", "answer": "83 lands in the repeated-local fiber 83/84/84a/239/240/241, but it has no promoted exact source assembly."},
        {"question": "What about 452 and 453?", "answer": "452 and 453 share the 82/245 local fiber and the same ordinary Hodge signature with each other, but both are blocked by quadratic-field exact coefficient support."},
        {"question": "What about 61 and 451?", "answer": "61 and 451 share local and ordinary Hodge signatures; 61 is parameterized and 451 is a partial/problematic extraction, so neither has a promoted source assembly."},
        {"question": "Are 84/240 and 84a/239 equivariantly equivalent?", "answer": "No under the current full equivariant fingerprint. They are integral-collapse/equivariant-separation pairs."},
        {"question": "Why did the previous report say 2 cases?", "answer": "The two cases are exactly 84/240 and 84a/239: same integral type, different equivariant type."},
        {"question": "Hodge-shift relation?", "answer": "The 78-85 and 238-245/451-455 rows show repeated local inventories can preserve Euler while shifting h11/h12; the output TSV records exact adjacent deltas."},
        {"question": "Sequence relationships?", "answer": "The graph JSON records repeated-local edges among the seven fibers only; it does not assert geometry identity or a proven specialization morphism."},
        {"question": "Torsion primes?", "answer": "Computed source assemblies show torsion at primes 2, 3, and 5; 241 is pure 3-primary in the computed subset."},
        {"question": "Recurrent source types?", "answer": f"{sum(1 for row in recurrent if row['member_count'] > 1)} recurrent type rows are emitted across local/rational/integral/equivariant levels."},
        {"question": "Simplest combinatorial predictors?", "answer": "Local inventory predicts the seven broad repeated fibers; rank, Smith data, and orbit sizes split the computed members further."},
        {"question": "New structure?", "answer": "The main new structure is a full 456-row computability frontier plus the explicit reconciliation that the apparent equivariant recurrences are integral recurrences with equivariant separation."},
    ]
    structural = [
        "# HodgeCY II Source Assembly Structural Report",
        "",
        f"- Corpus release fingerprint: `{ctx.release_fingerprint}`",
        f"- Total double-octic presentations: {len(all_rows)}",
        f"- Exact computed assemblies: {len(computed)}",
        f"- Blocked/unresolved assemblies: {len(blocked)}",
        f"- Repeated-local fibers: {len(repeated_local)}",
        f"- Fixed local+Hodge fibers: {len(fixed_local_hodge)}",
        "",
        "## Required Questions",
        "",
    ]
    structural.extend(markdown_table(question_rows, ["question", "answer"]))
    structural.extend(["", "## Hodge Shift Rows", ""])
    structural.extend(markdown_table(hodge_shift_rows, ["sequence_index", "arrangement_id", "requested_fiber", "hodge_signature", "delta_h12_from_previous_sequence", "delta_h11_from_previous_sequence", "delta_euler_from_previous_sequence", "assembly_status"]))
    structural.extend(["", "## Prime-Sensitive Computed Assemblies", ""])
    structural.extend(markdown_table(prime_rows, ["arrangement_id", "torsion_primes", "rank_mod_p", "smith_normal_form_compact"]))
    write_text(OUT_ROOT / "source_assembly_structural_report.md", "\n".join(structural))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Complete HodgeCY II source assembly deep-dive audit.")
    parser.add_argument("--root", default=None, help="Production HODGECY_DATA_ROOT. Defaults to environment.")
    args = parser.parse_args(argv)

    ctx = FullCorpusContext.open(args.root)
    ctx.assert_v1_ready()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MATRIX_DIR.mkdir(parents=True, exist_ok=True)

    presentations = canonical_rows(pd.read_parquet(OUT_ROOT / "all_source_presentations.parquet"))
    assemblies = canonical_rows(pd.read_parquet(OUT_ROOT / "all_source_assembly_invariants.parquet"))
    audit_by_id = load_audit_rows()
    ckc_by_id = load_ckc_records()
    spectra_by_id = load_spectra()
    assembly_by_id = {str(row["native_source_record_id"]): row for row in assemblies}

    matrix_manifest = []
    exact_rows_by_id: dict[str, dict[str, Any]] = {}
    for arrangement_id, assembly in sorted(assembly_by_id.items(), key=lambda item: natural_arrangement_key(item[0])):
        spectrum = spectra_by_id.get(arrangement_id)
        if not spectrum:
            matrix_manifest.append({"arrangement_id": arrangement_id, "matrix_status": "missing_spectrum_payload"})
            continue
        matrix_bundle = spectrum_matrix_payload(spectrum)
        payload = matrix_bundle["payload"]
        path = MATRIX_DIR / f"source_assembly_matrix_{arrangement_id}.json"
        write_json(path, payload)
        exact_rows_by_id[arrangement_id] = exact_representation(arrangement_id, matrix_bundle["matrix"], payload["matrix_hash"], assembly)
        matrix_manifest.append(
            {
                "arrangement_id": arrangement_id,
                "matrix_status": "stored_exact_integer_incidence_matrix",
                "matrix_hash": payload["matrix_hash"],
                "matrix_path": path.relative_to(REPO_ROOT).as_posix(),
                "shape": payload["shape"],
            }
        )

    all_rows = []
    for presentation in sorted(presentations, key=lambda row: natural_arrangement_key(str(row["presentation_id"]))):
        pid = str(presentation["presentation_id"])
        assembly = assembly_by_id.get(pid)
        audit = audit_by_id.get(pid)
        ckc_record = ckc_by_id.get(pid)
        status, blocker = assembly_status(pid, assembly, audit, ckc_record)
        exact = exact_rows_by_id.get(pid)
        row = {
            "corpus_release_fingerprint": ctx.release_fingerprint,
            **presentation,
            "presentation_id": pid,
            "assembly_computation_status": status,
            "source_blocker": blocker,
            "matrix_status": "stored_exact_integer_incidence_matrix" if exact else ("not_applicable_uncomputed" if not assembly else "missing_spectrum_payload"),
            "matrix_hash": exact.get("matrix_hash") if exact else None,
            "matrix_path": f"{MATRIX_DIR.relative_to(REPO_ROOT).as_posix()}/source_assembly_matrix_{pid}.json" if exact else None,
            "rank_Q": assembly.get("rank_Q") if assembly else None,
            "rank_F2": assembly.get("rank_F2") if assembly else None,
            "kernel_dim_Q": assembly.get("kernel_dim_Q") if assembly else None,
            "cokernel_dim_Q": assembly.get("cokernel_dim_Q") if assembly else None,
            "smith_normal_form": assembly.get("smith_normal_form") if assembly else None,
            "smith_normal_form_compact": assembly.get("smith_normal_form_compact") if assembly else None,
            "torsion_invariant_factors": assembly.get("torsion_invariant_factors") if assembly else None,
            "torsion_primes": assembly.get("torsion_primes") if assembly else None,
            "automorphism_group_order": assembly.get("automorphism_group_order") if assembly else None,
            "plane_orbit_sizes": assembly.get("plane_orbit_sizes") if assembly else None,
            "double_line_orbit_sizes": assembly.get("double_line_orbit_sizes") if assembly else None,
            "multiple_point_orbit_sizes": assembly.get("multiple_point_orbit_sizes") if assembly else None,
            "assembly_rational_fingerprint": assembly.get("rational_fingerprint") if assembly else None,
            "assembly_integral_fingerprint": assembly.get("integral_fingerprint") if assembly else None,
            "assembly_equivariant_fingerprint": assembly.get("equivariant_fingerprint") if assembly else None,
            "ckc_equation_type": audit.get("equation_type") if audit else None,
            "ckc_source_extraction_status": audit.get("source_extraction_status") if audit else None,
            "ckc_has_parameters": audit.get("has_parameters") if audit else None,
            "ckc_validation_tier": audit.get("validation_tier") if audit else None,
        }
        all_rows.append(row)

    computed_rows = [row for row in all_rows if row["assembly_computation_status"] == "computed_exact_two_stratum_source_assembly"]
    exact_rows = []
    for row in all_rows:
        exact = exact_rows_by_id.get(row["presentation_id"])
        if exact:
            exact_rows.append({**exact, "source_blocker": ""})
        else:
            exact_rows.append(
                {
                    "arrangement_id": row["presentation_id"],
                    "representation_status": "not_computed",
                    "matrix_hash": None,
                    "gluing_matrix_shape": None,
                    "rank_Q": None,
                    "rank_mod_p": None,
                    "kernel_dim_Q": None,
                    "cokernel_dim_Q": None,
                    "kernel_basis_Q": None,
                    "cokernel_dual_basis_Q": None,
                    "smith_normal_form": None,
                    "source_blocker": row["source_blocker"],
                }
            )

    symmetry_rows = [
        {
            "arrangement_id": row["presentation_id"],
            "symmetry_status": "computed_exact_from_stored_spectrum" if row["automorphism_group_order"] is not None else "not_computed",
            "automorphism_group_order": row["automorphism_group_order"],
            "plane_orbit_sizes": row["plane_orbit_sizes"],
            "double_line_orbit_sizes": row["double_line_orbit_sizes"],
            "multiple_point_orbit_sizes": row["multiple_point_orbit_sizes"],
            "source_blocker": row["source_blocker"],
        }
        for row in all_rows
    ]

    combinatorial_rows = [
        {
            "arrangement_id": row["presentation_id"],
            "entity_level": row["entity_level"],
            "presentation_kind": row["presentation_kind"],
            "local_inventory": row["local_inventory"],
            "local_signature": row["local_signature"],
            "hodge": row["hodge"],
            "hodge_signature": row["hodge_signature"],
            "ckc_equation_type": row["ckc_equation_type"],
            "ckc_has_parameters": row["ckc_has_parameters"],
            "ckc_validation_tier": row["ckc_validation_tier"],
            "assembly_computation_status": row["assembly_computation_status"],
            "source_blocker": row["source_blocker"],
        }
        for row in all_rows
    ]

    repeated_local = group_rows(all_rows, "local_signature")
    fixed_local_hodge = []
    keyed: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in all_rows:
        if row.get("local_signature") and row.get("hodge_signature"):
            keyed[(row["local_signature"], row["hodge_signature"])].append(row)
    for index, ((local_sig, hodge_sig), members) in enumerate(sorted(keyed.items(), key=lambda item: natural_arrangement_key(item[1][0]["presentation_id"])), start=1):
        if len(members) <= 1:
            continue
        members = sorted(members, key=lambda item: natural_arrangement_key(item["presentation_id"]))
        fixed_local_hodge.append(
            {
                "fiber_id": f"fixed_local_hodge_{index:03d}",
                "local_signature": local_sig,
                "hodge_signature": hodge_sig,
                "member_count": len(members),
                "computed_member_count": sum(1 for member in members if member["assembly_computation_status"] == "computed_exact_two_stratum_source_assembly"),
                "members": [member["presentation_id"] for member in members],
                "source_assembly_classes": sorted({member["assembly_integral_fingerprint"] for member in members if member.get("assembly_integral_fingerprint")}),
            }
        )

    rational_types = type_table(all_rows, "assembly_rational_fingerprint", "rational")
    integral_types = type_table(all_rows, "assembly_integral_fingerprint", "integral")
    equivariant_types = type_table(all_rows, "assembly_equivariant_fingerprint", "equivariant")
    recurrent = [
        {"recurrent_level": "local", **row}
        for row in repeated_local
    ] + [
        {"recurrent_level": level, **row}
        for level, rows in (("rational", rational_types), ("integral", integral_types), ("equivariant", equivariant_types))
        for row in rows
        if row["member_count"] > 1
    ]

    prime_rows = []
    for row in computed_rows:
        exact = exact_rows_by_id[row["presentation_id"]]
        prime_rows.append(
            {
                "arrangement_id": row["presentation_id"],
                "torsion_primes": row["torsion_primes"],
                "rank_mod_p": exact["rank_mod_p"],
                "rank_Q": row["rank_Q"],
                "rank_F2": row["rank_F2"],
                "smith_normal_form_compact": row["smith_normal_form_compact"],
                "prime_sensitive_signature": stable_fingerprint("prime_sensitive", {"torsion_primes": row["torsion_primes"], "rank_mod_p": exact["rank_mod_p"]}),
            }
        )

    hodge_shift_rows = build_hodge_shift_rows(all_rows)
    parameter_graph = build_parameter_graph(all_rows)

    write_json(MATRIX_DIR / "matrix_manifest.json", {"schema": "hodgecy_ii_source_assembly_matrix_manifest.v1", "records": matrix_manifest})
    write_parquet(OUT_DIR / "all_456_source_assemblies.parquet", all_rows)
    write_parquet(OUT_DIR / "all_456_source_symmetry.parquet", symmetry_rows)
    write_parquet(OUT_DIR / "all_456_kernel_cokernel_representations.parquet", exact_rows)
    write_parquet(OUT_DIR / "all_456_combinatorial_features.parquet", combinatorial_rows)
    write_parquet(OUT_DIR / "all_repeated_local_fibers.parquet", repeated_local)
    write_parquet(OUT_DIR / "all_fixed_local_hodge_fibers.parquet", fixed_local_hodge)
    write_parquet(OUT_DIR / "all_rational_source_types.parquet", rational_types)
    write_parquet(OUT_DIR / "all_integral_source_types.parquet", integral_types)
    write_parquet(OUT_DIR / "all_equivariant_source_types.parquet", equivariant_types)
    write_parquet(OUT_DIR / "all_prime_sensitive_types.parquet", prime_rows)
    write_parquet(OUT_DIR / "all_recurrent_source_types.parquet", recurrent)
    write_tsv(OUT_DIR / "hodge_shift_comparison.tsv", hodge_shift_rows)
    write_json(OUT_DIR / "parameter_specialization_graph.json", parameter_graph)
    write_json(
        OUT_DIR / "run_summary.json",
        {
            "schema": "hodgecy_ii_complete_source_assembly_deep_dive.v1",
            "corpus_release_fingerprint": ctx.release_fingerprint,
            "presentation_count": len(all_rows),
            "computed_exact_source_assembly_count": len(computed_rows),
            "blocked_source_assembly_count": len(all_rows) - len(computed_rows),
            "repeated_local_fiber_count": len(repeated_local),
            "fixed_local_hodge_fiber_count": len(fixed_local_hodge),
            "matrix_manifest": (MATRIX_DIR / "matrix_manifest.json").relative_to(REPO_ROOT).as_posix(),
        },
    )
    build_reports(ctx, all_rows, repeated_local, fixed_local_hodge, recurrent, prime_rows, hodge_shift_rows)

    print("HodgeCY II complete source assembly deep dive complete")
    print(f"- presentations enumerated: {len(all_rows)}")
    print(f"- exact source assemblies computed/stored: {len(computed_rows)}")
    print(f"- blocked/unresolved presentations: {len(all_rows) - len(computed_rows)}")
    print(f"- repeated local fibers: {len(repeated_local)}")
    print(f"- output directory: {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
