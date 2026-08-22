"""Build the HodgeCY II source-fidelity census.

This census audits all 455 raw CKC source records but classifies only the
source assemblies already reconstructed by committed spectrum artifacts.
It does not resume Gate A, node verification, defect computation, or Hodge atom
realization.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.research.hodgecy_ii_census import (  # noqa: E402
    HODGE_KEYS,
    INVENTORY_KEYS,
    SourceAssemblyRecord,
    group_records,
    natural_arrangement_key,
    normalize_spectrum,
)


INDEX_PATH = REPO_ROOT / "data" / "raw" / "cynk_kocel_cynk_2026" / "ckc_equation_index_001_455.json"
TABLE1_PATH = REPO_ROOT / "data" / "raw" / "cynk_meyer_table1.csv"
CKC_FIXED_SPECTRA_PATH = (
    REPO_ROOT
    / "data"
    / "processed"
    / "equivariant_spectra"
    / "ckc_fixed_rational_batch"
    / "ckc_fixed_rational_spectra.json"
)
FIXED_BATCH_DIR = REPO_ROOT / "data" / "processed" / "equivariant_spectra" / "fixed_equation_batch_001"
OUT_DIR = REPO_ROOT / "research_outputs" / "hodgecy_ii" / "census"
TOP_REPORT = REPO_ROOT / "research_outputs" / "hodgecy_ii" / "source_fidelity_census_report.md"
HODGECY_II_MANIFEST = REPO_ROOT / "research_outputs" / "hodgecy_ii" / "hodgecy_ii_manifest.json"
THEOREM_CANDIDATES = REPO_ROOT / "research_outputs" / "hodgecy_ii" / "theorem_candidates.md"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_tsv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _cell(row.get(key)) for key in fieldnames})


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "YES" if value else "NO"
    if isinstance(value, (list, tuple)):
        return ",".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return str(value)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_hodge_rows() -> dict[str, dict[str, Any]]:
    if not TABLE1_PATH.exists():
        return {}
    with TABLE1_PATH.open(newline="", encoding="utf-8") as handle:
        return {str(row["arrangement"]): row for row in csv.DictReader(handle)}


def _load_source_records() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    payload = _read_json(INDEX_PATH)
    records = {str(record["arrangement_id"]): record for record in payload["records"]}
    return payload, records


def _load_source_assemblies() -> list[SourceAssemblyRecord]:
    spectra = []
    fixed_payload = _read_json(CKC_FIXED_SPECTRA_PATH)
    for item in fixed_payload["spectra"]:
        spectra.append(normalize_spectrum(item, source_dataset="ckc_fixed_rational_batch"))
    for arrangement_id in ("84", "84a"):
        item = _read_json(FIXED_BATCH_DIR / f"hodgecy_equivariant_spectrum_{arrangement_id}.json")
        spectra.append(normalize_spectrum(item, source_dataset="fixed_equation_batch_001"))
    return sorted(spectra, key=lambda record: natural_arrangement_key(record.arrangement_id))


def _equation_type(record: dict[str, Any]) -> str:
    text = str(record.get("normalized_equation_text") or record.get("equation_text") or "")
    has_algebraic = "sqrt" in text or "âˆš" in text or "√" in text
    if record.get("extraction_status") != "extracted":
        return "partial_or_problematic_extraction"
    if record.get("has_parameters"):
        return "parameterized"
    if has_algebraic:
        return "fixed_algebraic"
    if record.get("fixed_equation_candidate"):
        return "fixed_rational"
    return "unclassified_fixed_source"


def _coverage_rows(
    index_payload: dict[str, Any],
    source_records: dict[str, dict[str, Any]],
    hodge_rows: dict[str, dict[str, Any]],
    assemblies: list[SourceAssemblyRecord],
) -> list[dict[str, Any]]:
    eligible = {record.arrangement_id: record for record in assemblies}
    rows = []
    for arrangement_id in sorted(source_records, key=natural_arrangement_key):
        source = source_records[arrangement_id]
        assembly = eligible.get(arrangement_id)
        equation_present = source.get("extraction_status") == "extracted" and len(source.get("linear_factor_texts") or []) == 8
        hodge_present = arrangement_id in hodge_rows or (assembly is not None and assembly.hodge is not None)
        if assembly is not None:
            exclusion_reason = ""
            validation_tier = assembly.validation_tier
        else:
            validation_tier = "S0_UNVALIDATED_SOURCE_RECORD"
            exclusion_reason = "raw_pdf_extraction_not_promoted_to_recomputed_source_complex"
        rows.append(
            {
                "arrangement_id": arrangement_id,
                "source_record_present": True,
                "equation_present": equation_present,
                "equation_type": _equation_type(source),
                "source_extraction_status": source.get("extraction_status"),
                "source_validation_status": source.get("validation_status"),
                "linear_factor_count": len(source.get("linear_factor_texts") or []),
                "has_parameters": bool(source.get("has_parameters")),
                "incidence_table_present": assembly is not None,
                "local_inventory_constructible": "YES" if assembly is not None else ("SOURCE_TABLE_ONLY" if arrangement_id in hodge_rows else "NO"),
                "two_stratum_constructible": assembly is not None,
                "group_constructible": assembly is not None,
                "hodge_data_available": hodge_present,
                "hodge_data_source": "source_spectrum_or_cynk_meyer_table1" if hodge_present else "",
                "triple_line_count": assembly.inventory[-1] if assembly is not None else hodge_rows.get(arrangement_id, {}).get("l3", ""),
                "validation_tier": validation_tier,
                "census_eligible": assembly is not None,
                "exclusion_reason": exclusion_reason,
                "parser_coverage_complete": bool(index_payload.get("parser_coverage_complete")),
                "full_validated_dataset_loaded": bool(index_payload.get("full_validated_dataset_loaded")),
            }
        )
    return rows


def _inventory_string(record: SourceAssemblyRecord) -> str:
    return ";".join(f"{key}={value}" for key, value in zip(INVENTORY_KEYS, record.inventory, strict=True))


def _hodge_string(record: SourceAssemblyRecord) -> str:
    if record.hodge is None:
        return ""
    return ";".join(f"{key}={value}" for key, value in zip(HODGE_KEYS, record.hodge, strict=True))


def _hodge_fiber_string(records: Iterable[SourceAssemblyRecord]) -> str:
    values = sorted({_hodge_string(record) or "UNKNOWN" for record in records})
    return " | ".join(values)


def _snf_string(record: SourceAssemblyRecord) -> str:
    counts: dict[int, int] = {}
    for value in record.smith_normal_form:
        counts[value] = counts.get(value, 0) + 1
    return ",".join(f"{value}^{count}" if count > 1 else str(value) for value, count in sorted(counts.items()))


def _member_ids(records: Iterable[SourceAssemblyRecord]) -> str:
    return ",".join(record.arrangement_id for record in sorted(records, key=lambda record: natural_arrangement_key(record.arrangement_id)))


def _assembly_rows(assemblies: list[SourceAssemblyRecord]) -> list[dict[str, Any]]:
    rows = []
    for record in assemblies:
        payload = record.to_dict()
        rows.append(
            {
                **payload,
                "inventory_signature": _inventory_string(record),
                "hodge_signature": _hodge_string(record),
                "smith_normal_form_compact": _snf_string(record),
            }
        )
    return rows


def _fiber_rows(grouped: dict[str, list[SourceAssemblyRecord]], *, prefix: str) -> list[dict[str, Any]]:
    rows = []
    for index, (fingerprint, members) in enumerate(grouped.items(), start=1):
        first = members[0]
        rows.append(
            {
                "fiber_id": f"{prefix}_{index:03d}",
                "fingerprint": fingerprint,
                "member_count": len(members),
                "members": _member_ids(members),
                "regime": first.regime,
                "inventory_signature": _inventory_string(first),
                "hodge_signature": _hodge_fiber_string(members),
                "rank_Q_values": sorted({record.rank_Q for record in members}),
                "rank_F2_values": sorted({record.rank_F2 for record in members}),
                "integral_signature_count": len({record.integral_fingerprint for record in members}),
                "equivariant_signature_count": len({record.equivariant_fingerprint for record in members}),
                "automorphism_group_orders": sorted({record.automorphism_group_order for record in members}),
            }
        )
    return rows


def _signature_classes(members: list[SourceAssemblyRecord], attr: str) -> list[dict[str, Any]]:
    grouped = group_records(members, attr)
    classes = []
    for fingerprint, records in grouped.items():
        first = records[0]
        classes.append(
            {
                "fingerprint": fingerprint,
                "members": [record.arrangement_id for record in records],
                "member_count": len(records),
                "rank_Q": first.rank_Q,
                "rank_F2": first.rank_F2,
                "smith_normal_form": list(first.smith_normal_form),
                "automorphism_group_order": first.automorphism_group_order,
            }
        )
    return classes


def _collapse_rows(
    grouped: dict[str, list[SourceAssemblyRecord]],
    *,
    source_level: str,
    target_level: str,
    target_attr: str,
) -> list[dict[str, Any]]:
    rows = []
    for index, (fingerprint, members) in enumerate(grouped.items(), start=1):
        classes = _signature_classes(members, target_attr)
        if len(classes) <= 1:
            continue
        first = members[0]
        rows.append(
            {
                "fiber_id": f"{source_level}_to_{target_level}_{index:03d}",
                "source_level": source_level,
                "target_level": target_level,
                "source_fingerprint": fingerprint,
                "member_count": len(members),
                "members": _member_ids(members),
                "inventory_signature": _inventory_string(first),
                "hodge_signature": _hodge_fiber_string(members),
                "target_signature_count": len(classes),
                "target_classes": "; ".join(f"{item['fingerprint']}[{','.join(item['members'])}]" for item in classes),
                "recovery_status": f"{target_level}_separates_{source_level}_fiber",
            }
        )
    return rows


def _recurrent_rows(grouped: dict[str, list[SourceAssemblyRecord]], *, signature_kind: str) -> list[dict[str, Any]]:
    rows = []
    for index, (fingerprint, members) in enumerate(grouped.items(), start=1):
        if len(members) <= 1:
            continue
        first = members[0]
        rows.append(
            {
                "recurrent_type_id": f"{signature_kind}_recurrent_{index:03d}",
                "signature_kind": signature_kind,
                "fingerprint": fingerprint,
                "member_count": len(members),
                "members": _member_ids(members),
                "inventory_signature": _inventory_string(first),
                "hodge_signature": _hodge_fiber_string(members),
                "rank_Q": first.rank_Q,
                "rank_F2": first.rank_F2,
                "smith_normal_form": _snf_string(first),
                "automorphism_group_order": first.automorphism_group_order,
            }
        )
    return rows


def _prime_rows(assemblies: list[SourceAssemblyRecord]) -> list[dict[str, Any]]:
    rows = []
    for record in assemblies:
        torsion = record.torsion
        rows.append(
            {
                "arrangement_id": record.arrangement_id,
                "regime": record.regime,
                "rank_Q": record.rank_Q,
                "rank_F2": record.rank_F2,
                "known_modular_ranks": {"2": record.rank_F2},
                "smith_normal_form": _snf_string(record),
                "torsion_invariant_factors": torsion["torsion_invariant_factors"],
                "torsion_primes": torsion["torsion_primes"],
                "p_primary_exponents": torsion["p_primary_exponents"],
                "prime_sensitive": bool(torsion["torsion_primes"]),
            }
        )
    return rows


def _summary(
    index_payload: dict[str, Any],
    coverage_rows: list[dict[str, Any]],
    assemblies: list[SourceAssemblyRecord],
    local_fibers: list[dict[str, Any]],
    hodge_refined_fibers: list[dict[str, Any]],
    local_to_rational: list[dict[str, Any]],
    rational_to_integral: list[dict[str, Any]],
    integral_to_equivariant: list[dict[str, Any]],
    hodge_to_integral: list[dict[str, Any]],
    recurrent_rational: list[dict[str, Any]],
    recurrent_integral: list[dict[str, Any]],
    recurrent_equivariant: list[dict[str, Any]],
) -> dict[str, Any]:
    index_eligible_ids = [str(row["arrangement_id"]) for row in coverage_rows if row["census_eligible"]]
    index_eligible = set(index_eligible_ids)
    supplemental_eligible_ids = [record.arrangement_id for record in assemblies if record.arrangement_id not in index_eligible]
    return {
        "schema": "hodgecy_ii_source_fidelity_census.v1",
        "terminology_guard": "source_fidelity_census_only_not_node_or_hodge_atom_realization",
        "total_ckc_types": int(index_payload["total_expected_records"]),
        "source_records_loaded": int(index_payload["records_loaded"]),
        "source_record_coverage_audited": len(coverage_rows),
        "raw_parser_coverage_complete": bool(index_payload["parser_coverage_complete"]),
        "raw_full_validated_dataset_loaded": bool(index_payload["full_validated_dataset_loaded"]),
        "census_eligible": len(assemblies),
        "ckc_index_census_eligible": len(index_eligible_ids),
        "supplemental_control_census_eligible": len(supplemental_eligible_ids),
        "supplemental_control_arrangement_ids": supplemental_eligible_ids,
        "ineligible_source_records": len(coverage_rows) - len(index_eligible_ids),
        "eligible_arrangement_ids": [record.arrangement_id for record in assemblies],
        "hodge_table_linked_eligible_count": sum(record.hodge is not None for record in assemblies),
        "source_recomputed_without_hodge_count": sum(record.hodge is None for record in assemblies),
        "clean_two_stratum_count": sum(record.regime == "CLEAN_TWO_STRATUM" for record in assemblies),
        "truncated_two_stratum_count": sum(record.regime == "TRUNCATED_TWO_STRATUM" for record in assemblies),
        "local_inventory_fiber_count": len(local_fibers),
        "nontrivial_local_inventory_fiber_count": sum(int(row["member_count"]) > 1 for row in local_fibers),
        "hodge_refined_fiber_count": len(hodge_refined_fibers),
        "nontrivial_hodge_refined_fiber_count": sum(int(row["member_count"]) > 1 for row in hodge_refined_fibers),
        "rational_signature_count": len({record.rational_fingerprint for record in assemblies}),
        "integral_signature_count": len({record.integral_fingerprint for record in assemblies}),
        "equivariant_signature_count": len({record.equivariant_fingerprint for record in assemblies}),
        "local_collapse_rational_recovery_fiber_count": len(local_to_rational),
        "rational_collapse_integral_recovery_fiber_count": len(rational_to_integral),
        "integral_collapse_equivariant_recovery_fiber_count": len(integral_to_equivariant),
        "hodge_collapse_assembly_recovery_fiber_count": len(hodge_to_integral),
        "recurrent_rational_assembly_type_count": len(recurrent_rational),
        "recurrent_integral_assembly_type_count": len(recurrent_integral),
        "recurrent_equivariant_signature_count": len(recurrent_equivariant),
        "known_witnesses": {
            "same_hodge_local_rational_integral_split": ["84", "84a"],
            "same_local_rational_split": ["84", "84a", "239", "240", "241"],
            "recurrent_integral_signatures": [row["members"] for row in recurrent_integral],
            "recurrent_equivariant_signatures": [row["members"] for row in recurrent_equivariant],
        },
    }


def _write_markdown(summary: dict[str, Any], local_to_rational: list[dict[str, Any]], rational_to_integral: list[dict[str, Any]]) -> None:
    lines = [
        "# HodgeCY II Source-Fidelity Census",
        "",
        "This is a source-level census of committed double-octic assembly data. It does not claim node, defect, LMHS, or genuine Hodge-atom realization.",
        "",
        "## Denominators",
        "",
        f"- CKC source types audited: {summary['total_ckc_types']}",
        f"- Raw CKC source records loaded: {summary['source_records_loaded']}",
        f"- Source-computable census-eligible assemblies: {summary['census_eligible']}",
        f"- Census-eligible assemblies inside the numbered CKC index: {summary['ckc_index_census_eligible']}",
        f"- Supplemental validated control assemblies: {summary['supplemental_control_census_eligible']} ({','.join(summary['supplemental_control_arrangement_ids'])})",
        f"- Ineligible raw source records: {summary['ineligible_source_records']}",
        f"- Raw extraction parser coverage complete: {summary['raw_parser_coverage_complete']}",
        f"- Full validated CKC dataset loaded: {summary['raw_full_validated_dataset_loaded']}",
        "",
        "## Fidelity Counts",
        "",
        f"- Clean two-stratum eligible assemblies: {summary['clean_two_stratum_count']}",
        f"- Truncated two-stratum eligible assemblies: {summary['truncated_two_stratum_count']}",
        f"- Local inventory fibers: {summary['local_inventory_fiber_count']}",
        f"- Rational signatures: {summary['rational_signature_count']}",
        f"- Integral signatures: {summary['integral_signature_count']}",
        f"- Equivariant signatures: {summary['equivariant_signature_count']}",
        "",
        "## Recovery Witnesses",
        "",
        f"- Local-to-rational recovery fibers: {summary['local_collapse_rational_recovery_fiber_count']}",
        f"- Rational-to-integral recovery fibers: {summary['rational_collapse_integral_recovery_fiber_count']}",
        f"- Integral-to-equivariant recovery fibers: {summary['integral_collapse_equivariant_recovery_fiber_count']}",
        f"- Hodge-refined source assembly recovery fibers: {summary['hodge_collapse_assembly_recovery_fiber_count']}",
        "",
        "The central local fiber is `84,84a,239,240,241`: arrangement 241 is separated at rational rank, while 84/84a/239/240 require integral refinement. The hodge-linked pair `84,84a` remains the committed witness that identical Hodge and local data can separate at source-level integral assembly.",
        "",
        "## Source Tables",
        "",
        "- `census/ckc_coverage_audit.tsv` audits all 455 raw CKC source records.",
        "- `census/source_assembly_records.tsv` lists the 13 eligible normalized source assemblies.",
        "- `census/table_local_collapse_rational_recovery.tsv` and `census/table_rational_collapse_integral_recovery.tsv` give the main refinement witnesses.",
        "",
    ]
    if local_to_rational:
        row = local_to_rational[0]
        lines.extend(
            [
                "## Local-to-Rational Witness",
                "",
                f"- Members: `{row['members']}`",
                f"- Target classes: `{row['target_signature_count']}`",
                "",
            ]
        )
    if rational_to_integral:
        row = rational_to_integral[0]
        lines.extend(
            [
                "## Rational-to-Integral Witness",
                "",
                f"- Members: `{row['members']}`",
                f"- Target classes: `{row['target_signature_count']}`",
                "",
            ]
        )
    report = "\n".join(lines)
    (OUT_DIR / "census_summary.md").write_text(report, encoding="utf-8")
    TOP_REPORT.write_text(report, encoding="utf-8")


def _write_structural_observations(summary: dict[str, Any]) -> None:
    lines = [
        "# Structural Observations",
        "",
        "- The committed census substrate is 13 source-recomputed assemblies out of 455 CKC source records.",
        "- The raw 455-record extraction is useful as an audit denominator, but remains explicitly unvalidated as a source-complex substrate.",
        "- The clean two-stratum part contains the five-member local fiber `84,84a,239,240,241`.",
        "- In that fiber, `241` is rationally separated; `84,84a,239,240` are rationally collapsed and integrally refined.",
        "- The `84,84a` pair is the current Hodge-refined source-level witness: same Hodge triple, same local inventory, same rational rank, different Smith normal form.",
        "- Recurrent source assembly signatures appear only as source-level recurrence and are not promoted to geometric realization.",
        "",
        f"Manifest schema: `{summary['schema']}`.",
    ]
    (OUT_DIR / "structural_observations.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _update_research_manifest(summary: dict[str, Any]) -> None:
    manifest = _read_json(HODGECY_II_MANIFEST)
    manifest.update(
        {
            "total_arrangements_scanned": summary["source_record_coverage_audited"],
            "source_fidelity_census_total_ckc_types": summary["total_ckc_types"],
            "source_fidelity_census_eligible": summary["census_eligible"],
            "source_fidelity_census_ineligible": summary["ineligible_source_records"],
            "source_fidelity_census_report": "research_outputs/hodgecy_ii/source_fidelity_census_report.md",
            "source_fidelity_census_manifest": "research_outputs/hodgecy_ii/census/source_fidelity_census_manifest.json",
            "clean_two_stratum_count": summary["clean_two_stratum_count"],
            "local_inventory_fiber_count": summary["local_inventory_fiber_count"],
            "rational_collapse_pair_count": summary["rational_collapse_integral_recovery_fiber_count"],
            "integral_collapse_equivariant_pair_count": summary["integral_collapse_equivariant_recovery_fiber_count"],
            "hodge_equivalent_pair_count": summary["hodge_collapse_assembly_recovery_fiber_count"],
            "additional_full_fidelity_witnesses": summary["known_witnesses"]["recurrent_equivariant_signatures"],
        }
    )
    HODGECY_II_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _update_theorem_candidates(summary: dict[str, Any]) -> None:
    marker = "## SOURCE-FIDELITY CENSUS CHECKPOINT"
    text = THEOREM_CANDIDATES.read_text(encoding="utf-8")
    text = text.replace("- Complete double-octic source-assembly fiber scan.\n", "")
    text = text.split(marker)[0].rstrip()
    addition = f"""

{marker}

- Source-level CKC audit complete for {summary['total_ckc_types']} raw source records, with {summary['census_eligible']} committed source-recomputed assemblies classified.
- The census is a computational observation only: it is not a node, defect, LMHS, or Hodge-atom realization result.
- Current source-level recovery witnesses include the local fiber `84,84a,239,240,241` and the Hodge-refined integral split `84,84a`.
"""
    THEOREM_CANDIDATES.write_text(text + addition, encoding="utf-8")


def _manifest(output_paths: list[Path], summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "hodgecy_ii_source_fidelity_census_manifest.v1",
        "summary": summary,
        "outputs": {
            str(path.relative_to(REPO_ROOT)).replace("\\", "/"): _sha256_file(path)
            for path in sorted(output_paths, key=lambda path: str(path))
            if path.exists()
        },
        "source_inputs": {
            str(INDEX_PATH.relative_to(REPO_ROOT)).replace("\\", "/"): _sha256_file(INDEX_PATH),
            str(TABLE1_PATH.relative_to(REPO_ROOT)).replace("\\", "/"): _sha256_file(TABLE1_PATH),
            str(CKC_FIXED_SPECTRA_PATH.relative_to(REPO_ROOT)).replace("\\", "/"): _sha256_file(CKC_FIXED_SPECTRA_PATH),
            str((FIXED_BATCH_DIR / "hodgecy_equivariant_spectrum_84.json").relative_to(REPO_ROOT)).replace("\\", "/"): _sha256_file(FIXED_BATCH_DIR / "hodgecy_equivariant_spectrum_84.json"),
            str((FIXED_BATCH_DIR / "hodgecy_equivariant_spectrum_84a.json").relative_to(REPO_ROOT)).replace("\\", "/"): _sha256_file(FIXED_BATCH_DIR / "hodgecy_equivariant_spectrum_84a.json"),
        },
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index_payload, source_records = _load_source_records()
    hodge_rows = _load_hodge_rows()
    assemblies = _load_source_assemblies()

    coverage = _coverage_rows(index_payload, source_records, hodge_rows, assemblies)
    assembly_rows = _assembly_rows(assemblies)

    local_groups = group_records(assemblies, "local_fingerprint")
    rational_groups = group_records(assemblies, "rational_fingerprint")
    integral_groups = group_records(assemblies, "integral_fingerprint")
    equivariant_groups = group_records(assemblies, "equivariant_fingerprint")
    hodge_known = [record for record in assemblies if record.hodge is not None]
    hodge_refined_groups = group_records(hodge_known, "hodge_refined_fingerprint")

    local_fibers = _fiber_rows(local_groups, prefix="local_fiber")
    hodge_refined_fibers = _fiber_rows(hodge_refined_groups, prefix="hodge_refined_fiber")
    nontrivial_fibers = [row for row in local_fibers if int(row["member_count"]) > 1]
    table_fidelity_fibers = local_fibers
    table_hodge_refined_fibers = hodge_refined_fibers

    local_to_rational = _collapse_rows(local_groups, source_level="local", target_level="rational", target_attr="rational_fingerprint")
    rational_to_integral = _collapse_rows(rational_groups, source_level="rational", target_level="integral", target_attr="integral_fingerprint")
    integral_to_equivariant = _collapse_rows(integral_groups, source_level="integral", target_level="equivariant", target_attr="equivariant_fingerprint")
    hodge_to_integral = _collapse_rows(hodge_refined_groups, source_level="hodge_refined", target_level="integral", target_attr="integral_fingerprint")

    recurrent_rational = _recurrent_rows(rational_groups, signature_kind="rational")
    recurrent_integral = _recurrent_rows(integral_groups, signature_kind="integral")
    recurrent_equivariant = _recurrent_rows(equivariant_groups, signature_kind="equivariant")
    recurrent_all = [*recurrent_rational, *recurrent_integral, *recurrent_equivariant]
    recurrent_fields = [
        "recurrent_type_id",
        "signature_kind",
        "fingerprint",
        "member_count",
        "members",
        "inventory_signature",
        "hodge_signature",
        "rank_Q",
        "rank_F2",
        "smith_normal_form",
        "automorphism_group_order",
    ]
    prime_profiles = _prime_rows(assemblies)
    prime_sensitive = [row for row in prime_profiles if row["prime_sensitive"]]

    summary = _summary(
        index_payload,
        coverage,
        assemblies,
        local_fibers,
        hodge_refined_fibers,
        local_to_rational,
        rational_to_integral,
        integral_to_equivariant,
        hodge_to_integral,
        recurrent_rational,
        recurrent_integral,
        recurrent_equivariant,
    )

    output_paths = [
        OUT_DIR / "ckc_coverage_audit.tsv",
        OUT_DIR / "source_assembly_records.tsv",
        OUT_DIR / "source_assembly_records.json",
        OUT_DIR / "local_inventory_fibers.tsv",
        OUT_DIR / "local_inventory_fibers.json",
        OUT_DIR / "nontrivial_fidelity_fibers.tsv",
        OUT_DIR / "table_fidelity_fibers.tsv",
        OUT_DIR / "table_hodge_refined_fidelity_fibers.tsv",
        OUT_DIR / "table_local_collapse_rational_recovery.tsv",
        OUT_DIR / "table_rational_collapse_integral_recovery.tsv",
        OUT_DIR / "table_integral_collapse_equivariant_recovery.tsv",
        OUT_DIR / "table_hodge_collapse_assembly_recovery.tsv",
        OUT_DIR / "table_recurrent_assembly_types.tsv",
        OUT_DIR / "recurrent_rational_assembly_types.tsv",
        OUT_DIR / "recurrent_integral_assembly_types.tsv",
        OUT_DIR / "recurrent_equivariant_signatures.tsv",
        OUT_DIR / "prime_sensitive_profiles.tsv",
        OUT_DIR / "table_prime_sensitive_fibers.tsv",
        OUT_DIR / "fidelity_refinement_trees.json",
        OUT_DIR / "census_summary.json",
        OUT_DIR / "census_summary.md",
        OUT_DIR / "structural_observations.md",
        OUT_DIR / "figure_local_fiber_size_histogram.tsv",
        OUT_DIR / "figure_refinement_counts.tsv",
        OUT_DIR / "figure_torsion_prime_distribution.tsv",
        TOP_REPORT,
    ]

    _write_tsv(output_paths[0], coverage, list(coverage[0]))
    _write_tsv(output_paths[1], assembly_rows, list(assembly_rows[0]))
    _write_json(output_paths[2], {"schema": "hodgecy_ii_source_assembly_records.v1", "records": [record.to_dict() for record in assemblies]})
    _write_tsv(output_paths[3], local_fibers, list(local_fibers[0]))
    _write_json(output_paths[4], {"schema": "hodgecy_ii_local_inventory_fibers.v1", "fibers": local_fibers})
    _write_tsv(output_paths[5], nontrivial_fibers, list(local_fibers[0]))
    _write_tsv(output_paths[6], table_fidelity_fibers, list(local_fibers[0]))
    _write_tsv(output_paths[7], table_hodge_refined_fibers, list(hodge_refined_fibers[0]))
    _write_tsv(output_paths[8], local_to_rational, list(local_to_rational[0]))
    _write_tsv(output_paths[9], rational_to_integral, list(rational_to_integral[0]))
    _write_tsv(
        output_paths[10],
        integral_to_equivariant,
        ["fiber_id", "source_level", "target_level", "source_fingerprint", "member_count", "members", "inventory_signature", "hodge_signature", "target_signature_count", "target_classes", "recovery_status"],
    )
    _write_tsv(output_paths[11], hodge_to_integral, list(hodge_to_integral[0]))
    _write_tsv(output_paths[12], recurrent_all, recurrent_fields)
    _write_tsv(output_paths[13], recurrent_rational, recurrent_fields)
    _write_tsv(output_paths[14], recurrent_integral, recurrent_fields)
    _write_tsv(output_paths[15], recurrent_equivariant, recurrent_fields)
    _write_tsv(output_paths[16], prime_profiles, list(prime_profiles[0]))
    _write_tsv(output_paths[17], prime_sensitive, list(prime_profiles[0]))
    _write_json(
        output_paths[18],
        {
            "schema": "hodgecy_ii_fidelity_refinement_trees.v1",
            "local_to_rational": local_to_rational,
            "rational_to_integral": rational_to_integral,
            "integral_to_equivariant": integral_to_equivariant,
            "hodge_refined_to_integral": hodge_to_integral,
        },
    )
    _write_json(output_paths[19], summary)
    _write_markdown(summary, local_to_rational, rational_to_integral)
    _write_structural_observations(summary)

    histogram: dict[int, int] = {}
    for row in local_fibers:
        size = int(row["member_count"])
        histogram[size] = histogram.get(size, 0) + 1
    _write_tsv(output_paths[22], [{"fiber_size": size, "fiber_count": count} for size, count in sorted(histogram.items())], ["fiber_size", "fiber_count"])
    _write_tsv(
        output_paths[23],
        [
            {"level": "local", "signature_count": summary["local_inventory_fiber_count"]},
            {"level": "rational", "signature_count": summary["rational_signature_count"]},
            {"level": "integral", "signature_count": summary["integral_signature_count"]},
            {"level": "equivariant", "signature_count": summary["equivariant_signature_count"]},
        ],
        ["level", "signature_count"],
    )
    prime_counts: dict[int, int] = {}
    for row in prime_profiles:
        for prime in row["torsion_primes"]:
            prime_counts[int(prime)] = prime_counts.get(int(prime), 0) + 1
    _write_tsv(output_paths[24], [{"prime": prime, "assembly_count": count} for prime, count in sorted(prime_counts.items())], ["prime", "assembly_count"])

    manifest_path = OUT_DIR / "source_fidelity_census_manifest.json"
    _write_json(manifest_path, _manifest(output_paths, summary))
    _update_research_manifest(summary)
    _update_theorem_candidates(summary)

    print("HodgeCY II source-fidelity census complete:")
    print(f"- CKC source records audited: {summary['total_ckc_types']}")
    print(f"- census-eligible source assemblies: {summary['census_eligible']}")
    print(f"- local fibers: {summary['local_inventory_fiber_count']}")
    print(f"- rational/integral/equivariant signatures: {summary['rational_signature_count']}/{summary['integral_signature_count']}/{summary['equivariant_signature_count']}")
    print(f"- report: {TOP_REPORT}")


if __name__ == "__main__":
    main()
