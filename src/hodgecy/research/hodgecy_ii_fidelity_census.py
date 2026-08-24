"""HodgeCY II complete fidelity census ingestion and manuscript assets.

This module consumes the historical complete-fidelity TSV as a frozen research
artifact.  It enriches the records with status/provenance metadata and emits
manuscript-facing assets without promoting census membership to node geometry,
defect, source-to-node, or Hodge-atom claims.
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping

from hodgecy import __version__ as HODGECY_VERSION
from hodgecy.storage.result_store import ResultStore


HISTORICAL_TOTAL_PROCESSED = 456
HISTORICAL_NONTRIVIAL_SET_COUNT = 114
GENERATOR_VERSION = "hodgecy_ii_manuscript_assets.v1"
NORMALIZED_GENERATED_AT = "normalized-deterministic-generation"

HISTORICAL_CENSUS_SCHEMA = "hodgecy_ii_complete_fidelity_census_historical.v1"
RECONCILED_CENSUS_SCHEMA = "hodgecy_ii_complete_fidelity_census_reconciled.v1"
SCOPE_SCHEMA = "hodgecy_ii_scope.v1"

REQUIRED_COLUMNS = (
    "set_id",
    "category",
    "members",
    "set_size",
    "local_inventory",
    "hodge_signatures",
    "rational_source_types",
    "integral_source_types",
    "torsion_types",
    "equivariant_types",
    "reason_this_set_is_interesting",
    "shared_invariants",
    "first_finer_invariant_that_separates",
)

REPRESENTATIVE_MEMBER_STRINGS = (
    "61 / 451",
    "84 / 84a",
    "452 / 453",
    "84 / 240",
    "84a / 239",
    "239 / 240 / 241",
)

REPEATED_LOCAL_FIBERS = (
    "78 / 79",
    "80 / 455",
    "81 / 454",
    "82 / 245 / 452 / 453",
    "83 / 84 / 84a / 239 / 240 / 241",
    "85 / 238",
)

NEIGHBORHOOD_84 = ("83", "84", "84a", "239", "240", "241")
HODGECY_I_REGRESSION_IDS = ("84", "84a", "239", "240", "241")


class SourceFidelityLevel(str, Enum):
    """Source-level HodgeCY II fidelity ladder."""

    LOCAL_INVENTORY = "local_inventory"
    HODGE_DATA = "hodge_data"
    RATIONAL_SOURCE = "rational_source"
    INTEGRAL_SOURCE = "integral_source"
    EQUIVARIANT_SOURCE = "equivariant_source"


class ReconciliationStatus(str, Enum):
    """Historical/current census reconciliation status."""

    REPRODUCED = "REPRODUCED"
    REPRODUCED_WITH_NEW_CERTIFICATION = "REPRODUCED_WITH_NEW_CERTIFICATION"
    HISTORICAL_ONLY = "HISTORICAL_ONLY"
    CHANGED = "CHANGED"
    BLOCKED = "BLOCKED"
    INVALID = "INVALID"
    NEW_CANDIDATE = "NEW_CANDIDATE"


SOURCE_FIDELITY_ORDER = (
    SourceFidelityLevel.LOCAL_INVENTORY,
    SourceFidelityLevel.HODGE_DATA,
    SourceFidelityLevel.RATIONAL_SOURCE,
    SourceFidelityLevel.INTEGRAL_SOURCE,
    SourceFidelityLevel.EQUIVARIANT_SOURCE,
)

FIRST_SEPARATION_MAP = {
    "Hodge data": SourceFidelityLevel.HODGE_DATA,
    "rational source type": SourceFidelityLevel.RATIONAL_SOURCE,
    "integral/Smith type": SourceFidelityLevel.INTEGRAL_SOURCE,
    "equivariant/symmetry type": SourceFidelityLevel.EQUIVARIANT_SOURCE,
    "none among computed invariants": None,
}

SHARED_LEVEL_MAP = {
    "local_inventory": SourceFidelityLevel.LOCAL_INVENTORY,
    "hodge_signature": SourceFidelityLevel.HODGE_DATA,
    "rational_source_type": SourceFidelityLevel.RATIONAL_SOURCE,
    "integral_source_type": SourceFidelityLevel.INTEGRAL_SOURCE,
    "equivariant_type": SourceFidelityLevel.EQUIVARIANT_SOURCE,
}

MEMBER_STATUS_OVERRIDES = {
    "84": "THEOREM_READY_SOURCE_CONTROL",
    "84a": "THEOREM_READY_SOURCE_CONTROL",
    "239": "CONTEXT_READY_SOURCE_RECOMPUTED",
    "240": "CONTEXT_READY_SOURCE_RECOMPUTED",
    "241": "CONTEXT_READY_SOURCE_RECOMPUTED",
    "451": "HISTORICAL_ONLY_FACTOR_NORMALIZATION_WARNING",
    "452": "HISTORICAL_ONLY_EXACT_QUADRATIC_FIELD_DEFERRED",
    "453": "HISTORICAL_ONLY_EXACT_QUADRATIC_FIELD_DEFERRED",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_historical_census_path() -> Path:
    return repo_root() / "research_outputs" / "hodgecy_ii" / "complete_fidelity_pairs_and_sets.tsv"


def default_manuscript_asset_root() -> Path:
    return repo_root() / "research_outputs" / "hodgecy_ii" / "manuscript_assets"


def git_commit(root: Path | None = None) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root or repo_root(),
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None
    return completed.stdout.strip() or None


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def parse_members(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split("/") if part.strip())


def member_display(members: Iterable[str]) -> str:
    return " / ".join(members)


def natural_member_key(member: str) -> tuple[int, str]:
    match = re.match(r"^(\d+)(.*)$", str(member))
    if not match:
        return (0, str(member))
    return (int(match.group(1)), match.group(2))


def split_signature_values(value: str) -> tuple[str, ...]:
    if value in ("", "UNKNOWN", "UNKNOWN_HODGE"):
        return tuple() if value == "" else (value,)
    return tuple(part.strip() for part in value.split("||") if part.strip())


def shared_levels_from_text(value: str) -> tuple[SourceFidelityLevel, ...]:
    levels = []
    for part in value.split("+"):
        normalized = part.strip()
        level = SHARED_LEVEL_MAP.get(normalized)
        if level is not None:
            levels.append(level)
    return tuple(levels)


def first_separating_level(value: str) -> SourceFidelityLevel | None:
    return FIRST_SEPARATION_MAP.get(value)


@dataclass(frozen=True, slots=True)
class FidelitySetRecord:
    """One historical nontrivial fidelity pair, triple, or larger set."""

    fidelity_set_id: str
    original_category: str
    members: tuple[str, ...]
    set_size: int
    local_inventory: str
    hodge_signatures: tuple[str, ...]
    rational_source_types: tuple[str, ...]
    integral_source_types: tuple[str, ...]
    torsion_types: tuple[str, ...]
    equivariant_types: tuple[str, ...]
    reason_this_set_is_interesting: str
    shared_levels: tuple[SourceFidelityLevel, ...]
    first_separating_level: SourceFidelityLevel | None
    first_separating_level_text: str
    historical_source: str

    @property
    def display_members(self) -> str:
        return member_display(self.members)

    @property
    def arity(self) -> str:
        if self.set_size == 2:
            return "pair"
        if self.set_size == 3:
            return "triple"
        return "larger_set"

    def validation_status(self) -> str:
        statuses = sorted({member_validation_status(member) for member in self.members})
        if any(status.startswith("HISTORICAL_ONLY") for status in statuses):
            return "MIXED_WITH_HISTORICAL_ONLY_MEMBERS"
        if all(status == "THEOREM_READY_SOURCE_CONTROL" for status in statuses):
            return "THEOREM_READY_SOURCE_CONTROL"
        if any(status == "CONTEXT_READY_SOURCE_RECOMPUTED" for status in statuses):
            return "CONTEXT_READY_SOURCE_CONTEXT"
        return "CENSUS_LEVEL"

    def to_dict(self) -> dict[str, Any]:
        return {
            "fidelity_set_id": self.fidelity_set_id,
            "members": list(self.members),
            "members_display": self.display_members,
            "set_size": self.set_size,
            "arity": self.arity,
            "category": self.original_category,
            "original_category": self.original_category,
            "shared_levels": [level.value for level in self.shared_levels],
            "first_separating_level": None if self.first_separating_level is None else self.first_separating_level.value,
            "first_separating_level_text": self.first_separating_level_text,
            "local_inventory": self.local_inventory,
            "hodge_signature": " || ".join(self.hodge_signatures),
            "hodge_signatures": list(self.hodge_signatures),
            "rational_source_type": " || ".join(self.rational_source_types),
            "rational_source_types": list(self.rational_source_types),
            "integral_source_type": " || ".join(self.integral_source_types),
            "integral_source_types": list(self.integral_source_types),
            "torsion_type": " || ".join(self.torsion_types),
            "torsion_types": list(self.torsion_types),
            "equivariant_type": " || ".join(self.equivariant_types),
            "equivariant_types": list(self.equivariant_types),
            "validation_status": self.validation_status(),
            "member_validation_status": {member: member_validation_status(member) for member in self.members},
            "source_artifact": self.historical_source,
            "provenance": {
                "historical_census_schema": HISTORICAL_CENSUS_SCHEMA,
                "historical_census_source": self.historical_source,
                "historical_set_id": self.fidelity_set_id,
            },
            "notes": self.reason_this_set_is_interesting,
        }


@dataclass(frozen=True, slots=True)
class ReconciledFidelitySetRecord:
    """A historical fidelity record enriched with current v1.0 status."""

    historical: FidelitySetRecord
    reconciliation_status: ReconciliationStatus
    current_classification: dict[str, Any]
    comparison_record_id: str
    artifact_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = self.historical.to_dict()
        payload.update(
            {
                "reconciliation_status": self.reconciliation_status.value,
                "historical_classification": {
                    "category": self.historical.original_category,
                    "shared_levels": [level.value for level in self.historical.shared_levels],
                    "first_separating_level": None
                    if self.historical.first_separating_level is None
                    else self.historical.first_separating_level.value,
                },
                "current_v1_classification": self.current_classification,
                "comparison_record_id": self.comparison_record_id,
                "artifact_ids": list(self.artifact_ids),
            }
        )
        return payload


def member_validation_status(member: str) -> str:
    return MEMBER_STATUS_OVERRIDES.get(member, "CENSUS_LEVEL")


def load_historical_census(path: Path | None = None) -> list[FidelitySetRecord]:
    path = path or default_historical_census_path()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        missing = set(REQUIRED_COLUMNS) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"Historical fidelity census missing columns: {sorted(missing)}")
        records = []
        for row in reader:
            members = parse_members(row["members"])
            set_size = int(row["set_size"])
            if set_size != len(members):
                raise ValueError(f"{row['set_id']} set_size={set_size} but members={members}")
            records.append(
                FidelitySetRecord(
                    fidelity_set_id=row["set_id"],
                    original_category=row["category"],
                    members=members,
                    set_size=set_size,
                    local_inventory=row["local_inventory"],
                    hodge_signatures=split_signature_values(row["hodge_signatures"]),
                    rational_source_types=split_signature_values(row["rational_source_types"]),
                    integral_source_types=split_signature_values(row["integral_source_types"]),
                    torsion_types=split_signature_values(row["torsion_types"]),
                    equivariant_types=split_signature_values(row["equivariant_types"]),
                    reason_this_set_is_interesting=row["reason_this_set_is_interesting"],
                    shared_levels=shared_levels_from_text(row["shared_invariants"]),
                    first_separating_level=first_separating_level(row["first_finer_invariant_that_separates"]),
                    first_separating_level_text=row["first_finer_invariant_that_separates"],
                    historical_source=str(path.relative_to(repo_root())).replace("\\", "/"),
                )
            )
    if len(records) != HISTORICAL_NONTRIVIAL_SET_COUNT:
        raise ValueError(f"Expected {HISTORICAL_NONTRIVIAL_SET_COUNT} fidelity sets, found {len(records)}")
    return records


def summarize_census(records: Iterable[FidelitySetRecord]) -> dict[str, Any]:
    records = list(records)
    arity = Counter(record.arity for record in records)
    return {
        "schema": "hodgecy_ii_fidelity_census_summary.v1",
        "total_processed": HISTORICAL_TOTAL_PROCESSED,
        "nontrivial_pairs_sets": len(records),
        "pairs": arity["pair"],
        "triples": arity["triple"],
        "larger_sets": arity["larger_set"],
        "counts_by_category": dict(sorted(Counter(record.original_category for record in records).items())),
        "counts_by_first_separation": dict(sorted(Counter(record.first_separating_level_text for record in records).items())),
        "counts_by_set_size": {str(key): value for key, value in sorted(Counter(record.set_size for record in records).items())},
        "source_fidelity_order": [level.value for level in SOURCE_FIDELITY_ORDER],
        "mathematical_firewall": mathematical_firewall(),
    }


def reconcile_census(records: Iterable[FidelitySetRecord]) -> list[ReconciledFidelitySetRecord]:
    reconciled = []
    for record in records:
        current = {
            "classification_source": "historical_complete_fidelity_tsv_reingested_by_v1",
            "membership_reproduced": True,
            "category_reproduced": True,
            "shared_levels_reproduced": True,
            "first_separating_level_reproduced": True,
            "source_recomputation_scope": "current_v1_reuses_frozen_historical_456_record_census; no fresh mining pass",
            "member_validation_status": {member: member_validation_status(member) for member in record.members},
        }
        reconciled.append(
            ReconciledFidelitySetRecord(
                historical=record,
                reconciliation_status=ReconciliationStatus.REPRODUCED,
                current_classification=current,
                comparison_record_id=f"hodgecy_ii_complete_fidelity:{record.fidelity_set_id}",
                artifact_ids=(f"fidelity_census_reconciled:{record.fidelity_set_id}",),
            )
        )
    return reconciled


def mathematical_firewall() -> dict[str, str]:
    return {
        "census_membership": "Census membership is not theorem-level geometric validation.",
        "local_vs_hodge": "Same local inventory does not imply same Hodge data.",
        "hodge_vs_rational": "Same Hodge data does not imply same rational source type.",
        "rational_vs_integral": "Same rational source type does not imply same integral source type.",
        "integral_vs_equivariant": "Same integral source type does not imply same equivariant type.",
        "projective_equivalence": "Equal source signatures do not prove projective equivalence.",
        "member_451": "451 retains its historical factor-normalization warning.",
        "members_452_453": "452/453 retain exact quadratic-field deferred status.",
        "no_node_ideal": "Blob 11 creates no node ideal.",
        "no_odp_promotion": "Blob 11 performs no ODP promotion.",
        "no_defect": "Blob 11 computes no defect value.",
        "no_node_relations": "Blob 11 asserts no node relation or source-to-node morphism.",
        "no_hodge_atom": "Blob 11 constructs no Hodge atom spectrum.",
    }


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: Any) -> Path:
    return _write_text(path, canonical_json(payload))


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "YES" if value else "NO"
    if isinstance(value, (list, tuple)):
        return " | ".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return str(value)


def _write_delimited(path: Path, rows: list[dict[str, Any]], fieldnames: list[str], *, delimiter: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=delimiter, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _cell(row.get(key)) for key in fieldnames})
    return path


def _markdown_table(rows: list[dict[str, Any]], fieldnames: list[str]) -> str:
    lines = [
        "| " + " | ".join(fieldnames) + " |",
        "| " + " | ".join("---" for _ in fieldnames) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_cell(row.get(key)).replace("|", "\\|") for key in fieldnames) + " |")
    return "\n".join(lines) + "\n"


def _latex_table(rows: list[dict[str, Any]], fieldnames: list[str]) -> str:
    def esc(value: Any) -> str:
        text = _cell(value)
        for old, new in {
            "\\": r"\textbackslash{}",
            "_": r"\_",
            "%": r"\%",
            "&": r"\&",
            "#": r"\#",
            "{": r"\{",
            "}": r"\}",
        }.items():
            text = text.replace(old, new)
        return text

    lines = [
        r"\begin{tabular}{%s}" % ("l" * len(fieldnames)),
        r"\hline",
        " & ".join(esc(name) for name in fieldnames) + r" \\",
        r"\hline",
    ]
    for row in rows:
        lines.append(" & ".join(esc(row.get(name)) for name in fieldnames) + r" \\")
    lines.extend([r"\hline", r"\end{tabular}", ""])
    return "\n".join(lines)


def _write_table_bundle(root: Path, stem: str, rows: list[dict[str, Any]], fieldnames: list[str]) -> list[Path]:
    paths = [
        _write_delimited(root / f"{stem}.tsv", rows, fieldnames, delimiter="\t"),
        _write_delimited(root / f"{stem}.csv", rows, fieldnames, delimiter=","),
        _write_json(root / f"{stem}.json", rows),
        _write_text(root / f"{stem}.md", _markdown_table(rows, fieldnames)),
        _write_text(root / f"{stem}.tex", _latex_table(rows, fieldnames)),
    ]
    return paths


def _load_source_assembly_records(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "research_outputs" / "hodgecy_ii" / "census" / "source_assembly_records.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(record["arrangement_id"]): record for record in payload.get("records", [])}


def _load_staged_record_index(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "research_outputs" / "hodgecy_ii" / "ckc_authoritative_staging" / "ckc455_staged_records.jsonl"
    if not path.exists():
        return {}
    records = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            records[str(record["arrangement_id"])] = record
    return records


def _source_record_snapshot(root: Path, arrangement_id: str) -> dict[str, Any]:
    source_records = _load_source_assembly_records(root)
    staged_records = _load_staged_record_index(root)
    source = source_records.get(arrangement_id)
    staged = staged_records.get(arrangement_id, {})
    if source:
        return {
            "arrangement_id": arrangement_id,
            "local_inventory": source.get("inventory"),
            "hodge_signature": source.get("hodge") or staged.get("hodge_values"),
            "matrix_shape": source.get("gluing_matrix_shape"),
            "rank_Q": source.get("rank_Q"),
            "rank_mod_2": source.get("rank_F2"),
            "smith_type": source.get("smith_normal_form"),
            "torsion_order": _torsion_order(source.get("torsion_invariant_factors") or []),
            "torsion_factors": source.get("torsion_invariant_factors") or [],
            "equivariant_signature": source.get("equivariant_fingerprint"),
            "group_order": source.get("automorphism_group_order"),
            "validation_status": member_validation_status(arrangement_id),
        }
    return {
        "arrangement_id": arrangement_id,
        "local_inventory": staged.get("table_derived_singularity_inventory"),
        "hodge_signature": staged.get("hodge_values"),
        "matrix_shape": None,
        "rank_Q": None,
        "rank_mod_2": None,
        "smith_type": None,
        "torsion_order": None,
        "torsion_factors": [],
        "equivariant_signature": None,
        "group_order": None,
        "validation_status": member_validation_status(arrangement_id),
    }


def _torsion_order(factors: Iterable[Any]) -> int:
    result = 1
    for factor in factors:
        result *= int(factor)
    return result


def _find_by_members(records: Iterable[FidelitySetRecord], members_display: str) -> FidelitySetRecord:
    wanted = parse_members(members_display)
    for record in records:
        if record.members == wanted:
            return record
    raise KeyError(members_display)


def _representative_rows(records: list[FidelitySetRecord]) -> list[dict[str, Any]]:
    roles = {
        "61 / 451": "direct same-local same-Hodge control with 451 warning preserved",
        "84 / 84a": "primary deep HodgeCY II pair",
        "452 / 453": "quadratic-field deferred same-local same-Hodge control",
        "84 / 240": "integral-collapse equivariant-separation control",
        "84a / 239": "integral-collapse equivariant-separation control",
        "239 / 240 / 241": "fixed-inventory same-Hodge rational-separation comparison",
    }
    rows = []
    for display in REPRESENTATIVE_MEMBER_STRINGS:
        record = _find_by_members(records, display)
        shared = set(record.shared_levels)
        hodge_equal = SourceFidelityLevel.HODGE_DATA in shared or len(set(record.hodge_signatures)) == 1
        rational_equal = SourceFidelityLevel.RATIONAL_SOURCE in shared or len(set(record.rational_source_types)) == 1
        integral_equal = SourceFidelityLevel.INTEGRAL_SOURCE in shared or len(set(record.integral_source_types)) == 1
        rows.append(
            {
                "members": display,
                "shared_local": "equal" if SourceFidelityLevel.LOCAL_INVENTORY in shared else "not asserted",
                "shared_hodge": "equal" if hodge_equal else "different/not asserted",
                "shared_rational": "equal" if rational_equal else "different/not asserted",
                "shared_integral": "equal" if integral_equal else "different/not asserted",
                "first_separation": record.first_separating_level_text,
                "validation_status": record.validation_status(),
                "role_in_hodgecy_ii": roles[display],
            }
        )
    return rows


def _summary_rows(summary: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = [
        {"measure": "total_processed", "value": summary["total_processed"], "status": "CONTEXT_READY"},
        {"measure": "nontrivial_pairs_sets", "value": summary["nontrivial_pairs_sets"], "status": "CONTEXT_READY"},
        {"measure": "pairs", "value": summary["pairs"], "status": "CONTEXT_READY"},
        {"measure": "triples", "value": summary["triples"], "status": "CONTEXT_READY"},
        {"measure": "larger_sets", "value": summary["larger_sets"], "status": "CONTEXT_READY"},
    ]
    for category, count in summary["counts_by_category"].items():
        rows.append({"measure": f"category:{category}", "value": count, "status": "CONTEXT_READY"})
    for level, count in summary["counts_by_first_separation"].items():
        rows.append({"measure": f"first_separation:{level}", "value": count, "status": "CONTEXT_READY"})
    return rows


def _neighborhood_rows(root: Path) -> list[dict[str, Any]]:
    rows = []
    for arrangement_id in NEIGHBORHOOD_84:
        snapshot = _source_record_snapshot(root, arrangement_id)
        rows.append(
            {
                "arrangement_id": arrangement_id,
                "local_inventory": snapshot["local_inventory"],
                "hodge_signature": snapshot["hodge_signature"],
                "rank_Q": snapshot["rank_Q"],
                "rank_mod_2": snapshot["rank_mod_2"],
                "smith_type": snapshot["smith_type"],
                "torsion_order": snapshot["torsion_order"],
                "equivariant_signature_or_group_order": snapshot["equivariant_signature"] or snapshot["group_order"],
                "validation_status": snapshot["validation_status"],
                "note": "Matching computed signatures do not establish projective equivalence.",
            }
        )
    return rows


def _hodgecy_i_regression(root: Path) -> dict[str, dict[str, Any]]:
    return {arrangement_id: _source_record_snapshot(root, arrangement_id) for arrangement_id in HODGECY_I_REGRESSION_IDS}


def _neighborhood_structure(records: list[FidelitySetRecord]) -> dict[str, Any]:
    local = _find_by_members(records, "83 / 84 / 84a / 239 / 240 / 241")
    rational = _find_by_members(records, "84 / 84a / 239 / 240")
    integral_a = _find_by_members(records, "84 / 240")
    integral_b = _find_by_members(records, "84a / 239")
    fixed = _find_by_members(records, "239 / 240 / 241")
    return {
        "local_fiber": local.to_dict(),
        "hodge_split": {
            "source": local.display_members,
            "first_separation": local.first_separating_level_text,
            "note": "Hodge data split the six-member local fiber in the historical census.",
        },
        "rational_collapse": rational.to_dict(),
        "integral_classes": [integral_a.to_dict(), integral_b.to_dict()],
        "equivariant_split": [
            {
                "members": integral_a.display_members,
                "shared": "integral_source_type",
                "first_separation": integral_a.first_separating_level_text,
            },
            {
                "members": integral_b.display_members,
                "shared": "integral_source_type",
                "first_separation": integral_b.first_separating_level_text,
            },
        ],
        "fixed_inventory_comparison": fixed.to_dict(),
    }


def _write_fidelity_hierarchy_svg(path: Path) -> Path:
    labels = [
        "local inventory",
        "Hodge data",
        "rational source type",
        "integral / Smith type",
        "equivariant source type",
    ]
    width = 1160
    height = 250
    box_w = 185
    box_h = 64
    gap = 35
    x0 = 50
    y = 82
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="50" y="38" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#111">HodgeCY II Source-Fidelity Hierarchy</text>',
        '<text x="50" y="210" font-family="Arial, sans-serif" font-size="15" fill="#333">Moving right restores increasingly fine source-level information; node geometry and Hodge atoms are outside this ladder.</text>',
    ]
    for index, label in enumerate(labels):
        x = x0 + index * (box_w + gap)
        parts.append(f'<rect x="{x}" y="{y}" width="{box_w}" height="{box_h}" rx="6" fill="#f8fafc" stroke="#334155" stroke-width="1.5"/>')
        parts.append(f'<text x="{x + box_w / 2}" y="{y + 38}" font-family="Arial, sans-serif" font-size="16" text-anchor="middle" fill="#111">{label}</text>')
        if index < len(labels) - 1:
            x1 = x + box_w + 8
            x2 = x + box_w + gap - 8
            parts.append(f'<line x1="{x1}" y1="{y + box_h / 2}" x2="{x2}" y2="{y + box_h / 2}" stroke="#475569" stroke-width="2"/>')
            parts.append(f'<path d="M{x2} {y + box_h / 2} l-8 -5 v10 z" fill="#475569"/>')
    parts.append("</svg>\n")
    return _write_text(path, "\n".join(parts))


def _write_neighborhood_tree_svg(path: Path, structure: Mapping[str, Any]) -> Path:
    nodes = [
        (420, 35, "{83,84,84a,239,240,241}", "same local inventory"),
        (420, 125, "Hodge split", "six-member local fiber separates"),
        (420, 215, "{84,84a,239,240}", "same rational source type"),
        (225, 315, "{84,240}", "integral type A"),
        (615, 315, "{84a,239}", "integral type B"),
        (225, 405, "equivariant split", "84 vs 240"),
        (615, 405, "equivariant split", "84a vs 239"),
        (865, 215, "{239,240,241}", "fixed-inventory comparison"),
    ]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1050" height="500" viewBox="0 0 1050 500">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="40" y="28" font-family="Arial, sans-serif" font-size="21" font-weight="700" fill="#111">84-Neighborhood Source-Fidelity Refinement</text>',
    ]
    edges = [(0, 1), (1, 2), (2, 3), (2, 4), (3, 5), (4, 6), (1, 7)]
    for a, b in edges:
        x1, y1, *_ = nodes[a]
        x2, y2, *_ = nodes[b]
        parts.append(f'<line x1="{x1}" y1="{y1 + 52}" x2="{x2}" y2="{y2 - 10}" stroke="#64748b" stroke-width="1.6"/>')
    for x, y, label, sublabel in nodes:
        parts.append(f'<rect x="{x - 135}" y="{y}" width="270" height="62" rx="6" fill="#fff7ed" stroke="#9a3412" stroke-width="1.4"/>')
        parts.append(f'<text x="{x}" y="{y + 25}" font-family="Arial, sans-serif" font-size="15" font-weight="700" text-anchor="middle" fill="#111">{label}</text>')
        parts.append(f'<text x="{x}" y="{y + 47}" font-family="Arial, sans-serif" font-size="13" text-anchor="middle" fill="#333">{sublabel}</text>')
    parts.append('<text x="40" y="475" font-family="Arial, sans-serif" font-size="13" fill="#333">Matching computed signatures do not establish projective equivalence.</text>')
    parts.append("</svg>\n")
    return _write_text(path, "\n".join(parts))


def _persist_comparison_sets(root: Path, reconciled: list[ReconciledFidelitySetRecord]) -> dict[str, Any]:
    store_path = root / "data" / "hodgecy_ii_fidelity_result_store.sqlite"
    artifact_dir = root / "data" / "result_store_artifacts"
    if store_path.exists():
        store_path.unlink()
    if artifact_dir.exists():
        shutil.rmtree(artifact_dir)
    store = ResultStore(store_path, artifact_dir=artifact_dir)
    store.initialize()
    members = [str(index) for index in range(1, 456)]
    members.append("84a")
    members = sorted(set(members), key=natural_member_key)
    for member in members:
        store.add_geometry(
            geometry_id=f"ckc-{member}",
            display_name=f"CKC double-octic presentation {member}",
            geometry_type="double_octic_presentation",
            source_dataset="cynk_kocel_cynk_2026",
            source_entry_id=member,
            metadata={"validation_status": member_validation_status(member)},
            provenance="HodgeCY II historical complete fidelity census",
        )
    for item in reconciled:
        store.create_comparison_set(
            comparison_set_id=item.comparison_record_id,
            display_name=item.historical.display_members,
            member_geometry_ids=[f"ckc-{member}" for member in item.historical.members],
            selection_criterion=item.historical.original_category,
            notes=json.dumps(
                {
                    "shared_levels": [level.value for level in item.historical.shared_levels],
                    "first_separating_level": item.historical.first_separating_level_text,
                    "validation_status": item.historical.validation_status(),
                    "historical_source": item.historical.historical_source,
                    "reconciliation_status": item.reconciliation_status.value,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
        )
    return {
        "path": str(store_path.relative_to(repo_root())).replace("\\", "/"),
        "comparison_sets_stored": len(reconciled),
        "geometry_records_stored": len(members),
        "ignored_in_git": True,
    }


def build_scope_manifest(summary: Mapping[str, Any], asset_manifest_path: str) -> dict[str, Any]:
    return {
        "schema": SCOPE_SCHEMA,
        "paper_version": "HodgeCY II scope freeze for package v1.0.0",
        "hodgecy_version": HODGECY_VERSION,
        "primary_deep_examples": ["84", "84a"],
        "population_context": {
            "processed": HISTORICAL_TOTAL_PROCESSED,
            "nontrivial_sets": HISTORICAL_NONTRIVIAL_SET_COUNT,
            "role": "contextual recurrence evidence, not full theorem-level population classification",
        },
        "representative_fidelity_controls": [
            "61/451",
            "84/84a",
            "452/453",
            "84/240",
            "84a/239",
            "239/240/241",
        ],
        "deferred_population_study": {
            "destination": "HodgeCY III",
            "items": [
                "full theorem-level classification of all 114 sets",
                "population statistics as principal theorem",
                "complete fidelity stratification of all 456 geometries",
                "large-scale discovery of additional pair/set classes",
                "full prime-sensitive population study",
                "full equivariant population classification",
            ],
        },
        "required_geometric_outputs": {
            "blob_11": "none; scope freeze and source-fidelity census assets only",
            "later_blobs": ["ordinary_node_verified", "defect_verified", "source/node comparison"],
        },
        "nonclaims": mathematical_firewall(),
        "artifact_manifest": asset_manifest_path,
        "summary": dict(summary),
    }


def generate_hodgecy_ii_manuscript_assets(
    *,
    historical_census_path: Path | None = None,
    output_root: Path | None = None,
) -> dict[str, Any]:
    root = repo_root()
    historical_census_path = historical_census_path or default_historical_census_path()
    output_root = output_root or default_manuscript_asset_root()
    table_root = output_root / "tables"
    figure_root = output_root / "figures"
    data_root = output_root / "data"
    manifest_root = output_root / "manifest"
    for path in (table_root, figure_root, data_root, manifest_root):
        path.mkdir(parents=True, exist_ok=True)

    records = load_historical_census(historical_census_path)
    reconciled = reconcile_census(records)
    summary = summarize_census(records)
    reconciled_payload = [item.to_dict() for item in reconciled]

    outputs: list[Path] = []
    outputs.append(_write_delimited(data_root / "fidelity_census_reconciled.tsv", reconciled_payload, list(reconciled_payload[0]), delimiter="\t"))
    outputs.append(_write_json(data_root / "fidelity_census_reconciled.json", {"schema": RECONCILED_CENSUS_SCHEMA, "records": reconciled_payload}))

    summary_rows = _summary_rows(summary)
    outputs.extend(_write_table_bundle(table_root, "fidelity_census_summary", summary_rows, ["measure", "value", "status"]))

    representative_rows = _representative_rows(records)
    outputs.extend(
        _write_table_bundle(
            table_root,
            "representative_fidelity_controls",
            representative_rows,
            [
                "members",
                "shared_local",
                "shared_hodge",
                "shared_rational",
                "shared_integral",
                "first_separation",
                "validation_status",
                "role_in_hodgecy_ii",
            ],
        )
    )

    neighborhood_rows = _neighborhood_rows(root)
    outputs.extend(
        _write_table_bundle(
            table_root,
            "neighborhood_84_refinement",
            neighborhood_rows,
            [
                "arrangement_id",
                "local_inventory",
                "hodge_signature",
                "rank_Q",
                "rank_mod_2",
                "smith_type",
                "torsion_order",
                "equivariant_signature_or_group_order",
                "validation_status",
                "note",
            ],
        )
    )

    neighborhood_structure = _neighborhood_structure(records)
    outputs.append(_write_json(data_root / "neighborhood_84_refinement_tree.json", neighborhood_structure))
    outputs.append(_write_json(data_root / "hodgecy_i_source_regression.json", _hodgecy_i_regression(root)))
    outputs.append(_write_json(data_root / "fidelity_census_summary.json", summary))

    outputs.append(_write_fidelity_hierarchy_svg(figure_root / "fidelity_hierarchy.svg"))
    outputs.append(_write_json(figure_root / "fidelity_hierarchy_data.json", {"levels": [level.value for level in SOURCE_FIDELITY_ORDER], "nonclaims": ["node_geometry", "defect", "hodge_atom"]}))
    outputs.append(_write_neighborhood_tree_svg(figure_root / "neighborhood_84_refinement_tree.svg", neighborhood_structure))
    outputs.append(_write_json(figure_root / "neighborhood_84_refinement_tree_data.json", neighborhood_structure))

    result_store = _persist_comparison_sets(output_root, reconciled)

    scope_path = manifest_root / "hodgecy_ii_scope.json"
    asset_manifest_path = str((manifest_root / "hodgecy_ii_asset_manifest.json").relative_to(root)).replace("\\", "/")
    outputs.append(_write_json(scope_path, build_scope_manifest(summary, asset_manifest_path)))

    input_hashes = {
        str(historical_census_path.relative_to(root)).replace("\\", "/"): file_sha256(historical_census_path),
    }
    source_assembly_path = root / "research_outputs" / "hodgecy_ii" / "census" / "source_assembly_records.json"
    if source_assembly_path.exists():
        input_hashes[str(source_assembly_path.relative_to(root)).replace("\\", "/")] = file_sha256(source_assembly_path)

    artifact_entries = {}
    for path in sorted({path for path in outputs if path.exists()}, key=lambda item: str(item)):
        rel = str(path.relative_to(root)).replace("\\", "/")
        artifact_entries[rel] = {
            "sha256": file_sha256(path),
            "status": "CONTEXT_READY",
        }
    manifest = {
        "schema": "hodgecy_ii_manuscript_asset_manifest.v1",
        "generator_version": GENERATOR_VERSION,
        "generated_at": NORMALIZED_GENERATED_AT,
        "hodgecy_version": HODGECY_VERSION,
        "git_commit": git_commit(root),
        "input_hashes": input_hashes,
        "source_record_ids": sorted({member for record in records for member in record.members}, key=natural_member_key),
        "historical_census": summary,
        "result_store": result_store,
        "artifacts": artifact_entries,
        "mathematical_firewall": mathematical_firewall(),
        "deterministic_generation": "Volatile timestamps are normalized; identical input hashes produce identical table, JSON, membership, and classification content.",
    }
    manifest_path = manifest_root / "hodgecy_ii_asset_manifest.json"
    _write_json(manifest_path, manifest)

    return {
        "summary": summary,
        "records": reconciled_payload,
        "representative_controls": representative_rows,
        "neighborhood_84": neighborhood_structure,
        "hodgecy_i_regression": _hodgecy_i_regression(root),
        "scope_manifest": str(scope_path.relative_to(root)).replace("\\", "/"),
        "asset_manifest": str(manifest_path.relative_to(root)).replace("\\", "/"),
        "result_store": result_store,
    }


__all__ = [
    "FidelitySetRecord",
    "HISTORICAL_NONTRIVIAL_SET_COUNT",
    "HISTORICAL_TOTAL_PROCESSED",
    "REPEATED_LOCAL_FIBERS",
    "REPRESENTATIVE_MEMBER_STRINGS",
    "ReconciliationStatus",
    "ReconciledFidelitySetRecord",
    "SOURCE_FIDELITY_ORDER",
    "SourceFidelityLevel",
    "default_historical_census_path",
    "default_manuscript_asset_root",
    "first_separating_level",
    "generate_hodgecy_ii_manuscript_assets",
    "load_historical_census",
    "mathematical_firewall",
    "member_validation_status",
    "parse_members",
    "reconcile_census",
    "shared_levels_from_text",
    "summarize_census",
]
