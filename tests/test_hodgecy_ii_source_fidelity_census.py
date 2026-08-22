from __future__ import annotations

import csv
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CENSUS_DIR = REPO_ROOT / "research_outputs" / "hodgecy_ii" / "census"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def test_source_fidelity_census_denominators_are_explicit() -> None:
    summary = _json(CENSUS_DIR / "census_summary.json")
    manifest = _json(CENSUS_DIR / "source_fidelity_census_manifest.json")

    assert summary["total_ckc_types"] == 455
    assert summary["source_records_loaded"] == 455
    assert summary["source_record_coverage_audited"] == 455
    assert summary["census_eligible"] == 13
    assert summary["ckc_index_census_eligible"] == 12
    assert summary["supplemental_control_census_eligible"] == 1
    assert summary["supplemental_control_arrangement_ids"] == ["84a"]
    assert summary["ineligible_source_records"] == 443
    assert summary["raw_parser_coverage_complete"] is True
    assert summary["raw_full_validated_dataset_loaded"] is False
    assert summary["terminology_guard"] == "source_fidelity_census_only_not_node_or_hodge_atom_realization"
    assert manifest["summary"]["census_eligible"] == 13


def test_source_fidelity_census_coverage_does_not_promote_raw_455_records() -> None:
    rows = _tsv(CENSUS_DIR / "ckc_coverage_audit.tsv")
    eligible = {row["arrangement_id"] for row in rows if row["census_eligible"] == "YES"}

    assert len(rows) == 455
    assert eligible == {"1", "3", "19", "32", "69", "84", "93", "238", "239", "240", "241", "245"}
    assert rows[450]["arrangement_id"] == "451"
    assert rows[450]["equation_type"] == "partial_or_problematic_extraction"
    assert rows[451]["arrangement_id"] == "452"
    assert rows[451]["census_eligible"] == "NO"
    assert rows[451]["exclusion_reason"] == "raw_pdf_extraction_not_promoted_to_recomputed_source_complex"


def test_source_assembly_records_have_stable_signature_layers() -> None:
    rows = _tsv(CENSUS_DIR / "source_assembly_records.tsv")
    by_id = {row["arrangement_id"]: row for row in rows}

    assert len(rows) == 13
    assert by_id["84"]["hodge_signature"] == "h12=0;h11=40;euler=80"
    assert by_id["84a"]["hodge_signature"] == "h12=0;h11=40;euler=80"
    assert by_id["239"]["hodge_signature"] == ""
    assert by_id["241"]["rank_Q"] == "24"
    for row in rows:
        for key in ("local_fingerprint", "rational_fingerprint", "integral_fingerprint", "equivariant_fingerprint"):
            kind, digest = row[key].split(":", maxsplit=1)
            assert kind
            assert len(digest) == 64
            int(digest, 16)


def test_source_fidelity_recovery_witnesses_are_reported() -> None:
    local_to_rational = _tsv(CENSUS_DIR / "table_local_collapse_rational_recovery.tsv")
    rational_to_integral = _tsv(CENSUS_DIR / "table_rational_collapse_integral_recovery.tsv")
    hodge_to_integral = _tsv(CENSUS_DIR / "table_hodge_collapse_assembly_recovery.tsv")

    assert len(local_to_rational) == 1
    assert local_to_rational[0]["members"] == "84,84a,239,240,241"
    assert local_to_rational[0]["target_signature_count"] == "2"
    assert "241" in local_to_rational[0]["target_classes"]

    assert len(rational_to_integral) == 1
    assert rational_to_integral[0]["members"] == "84,84a,239,240"
    assert rational_to_integral[0]["target_signature_count"] == "2"
    assert "84,240" in rational_to_integral[0]["target_classes"]
    assert "84a,239" in rational_to_integral[0]["target_classes"]

    assert len(hodge_to_integral) == 1
    assert hodge_to_integral[0]["members"] == "84,84a"
    assert hodge_to_integral[0]["hodge_signature"] == "h12=0;h11=40;euler=80"


def test_strict_equivariant_layer_separates_recurrent_integral_types() -> None:
    summary = _json(CENSUS_DIR / "census_summary.json")
    recurrent_integral = _tsv(CENSUS_DIR / "recurrent_integral_assembly_types.tsv")
    recurrent_equivariant = _tsv(CENSUS_DIR / "recurrent_equivariant_signatures.tsv")
    integral_to_equivariant = _tsv(CENSUS_DIR / "table_integral_collapse_equivariant_recovery.tsv")

    assert summary["integral_signature_count"] == 11
    assert summary["equivariant_signature_count"] == 13
    assert summary["recurrent_integral_assembly_type_count"] == 2
    assert summary["recurrent_equivariant_signature_count"] == 0
    assert {row["members"] for row in recurrent_integral} == {"84,240", "84a,239"}
    assert recurrent_equivariant == []
    assert {row["members"] for row in integral_to_equivariant} == {"84,240", "84a,239"}
