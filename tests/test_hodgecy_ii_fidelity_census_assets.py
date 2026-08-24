from __future__ import annotations

import csv
import json
import re
import sqlite3
from pathlib import Path

from hodgecy.research.hodgecy_ii_fidelity_census import (
    HISTORICAL_NONTRIVIAL_SET_COUNT,
    HISTORICAL_TOTAL_PROCESSED,
    REPEATED_LOCAL_FIBERS,
    SOURCE_FIDELITY_ORDER,
    SourceFidelityLevel,
    first_separating_level,
    generate_hodgecy_ii_manuscript_assets,
    load_historical_census,
    mathematical_firewall,
    member_validation_status,
    parse_members,
    reconcile_census,
    shared_levels_from_text,
    summarize_census,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = REPO_ROOT / "research_outputs" / "hodgecy_ii" / "manuscript_assets"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _ensure_assets() -> dict:
    return generate_hodgecy_ii_manuscript_assets()


def test_historical_census_parser_preserves_counts_memberships_and_levels() -> None:
    records = load_historical_census()
    by_members = {record.display_members: record for record in records}
    summary = summarize_census(records)

    assert summary["total_processed"] == HISTORICAL_TOTAL_PROCESSED == 456
    assert summary["nontrivial_pairs_sets"] == HISTORICAL_NONTRIVIAL_SET_COUNT == 114
    assert summary["pairs"] == 57
    assert summary["triples"] == 13
    assert summary["larger_sets"] == 44
    assert SOURCE_FIDELITY_ORDER == (
        SourceFidelityLevel.LOCAL_INVENTORY,
        SourceFidelityLevel.HODGE_DATA,
        SourceFidelityLevel.RATIONAL_SOURCE,
        SourceFidelityLevel.INTEGRAL_SOURCE,
        SourceFidelityLevel.EQUIVARIANT_SOURCE,
    )
    assert parse_members("84 / 84a / 239") == ("84", "84a", "239")
    assert shared_levels_from_text("local_inventory + hodge_signature") == (
        SourceFidelityLevel.LOCAL_INVENTORY,
        SourceFidelityLevel.HODGE_DATA,
    )
    assert first_separating_level("integral/Smith type") is SourceFidelityLevel.INTEGRAL_SOURCE

    for members in ["61 / 451", "84 / 84a", "452 / 453", "84 / 240", "84a / 239", "239 / 240 / 241"]:
        assert members in by_members
    for members in REPEATED_LOCAL_FIBERS:
        assert members in by_members
    assert "238 / 239 / 240 / 241" not in by_members


def test_reconciliation_preserves_validation_status_and_firewall() -> None:
    records = load_historical_census()
    reconciled = reconcile_census(records)
    by_members = {item.historical.display_members: item for item in reconciled}
    firewall = mathematical_firewall()

    assert len(reconciled) == 114
    assert {item.reconciliation_status.value for item in reconciled} == {"REPRODUCED"}
    assert member_validation_status("451") == "HISTORICAL_ONLY_FACTOR_NORMALIZATION_WARNING"
    assert member_validation_status("452") == "HISTORICAL_ONLY_EXACT_QUADRATIC_FIELD_DEFERRED"
    assert member_validation_status("453") == "HISTORICAL_ONLY_EXACT_QUADRATIC_FIELD_DEFERRED"
    assert by_members["61 / 451"].historical.validation_status() == "MIXED_WITH_HISTORICAL_ONLY_MEMBERS"
    assert by_members["452 / 453"].historical.validation_status() == "MIXED_WITH_HISTORICAL_ONLY_MEMBERS"
    assert by_members["84 / 84a"].historical.validation_status() == "THEOREM_READY_SOURCE_CONTROL"
    assert "not theorem-level geometric validation" in firewall["census_membership"]
    assert "No final saturated node ideal certificate is claimed" in firewall["no_node_ideal"]
    assert "No Hodge atom spectrum is constructed" in firewall["no_hodge_atom"]


def test_asset_generation_tables_figures_manifests_and_persistence() -> None:
    result = _ensure_assets()
    summary = result["summary"]
    manifest = _json(REPO_ROOT / result["asset_manifest"])
    scope = _json(REPO_ROOT / result["scope_manifest"])
    reconciled = _json(ASSET_ROOT / "data" / "fidelity_census_reconciled.json")["records"]

    assert summary["total_processed"] == 456
    assert summary["nontrivial_pairs_sets"] == 114
    assert len(reconciled) == 114
    assert scope["primary_deep_examples"] == ["84", "84a"]
    assert scope["population_context"]["nontrivial_sets"] == 114
    assert scope["deferred_population_study"]["destination"] == "HodgeCY III"
    assert manifest["historical_census"]["pairs"] == 57
    assert manifest["result_store"]["comparison_sets_stored"] == 114
    assert manifest["deterministic_generation"].startswith("Volatile timestamps are normalized")

    for relative in [
        "tables/fidelity_census_summary.tsv",
        "tables/fidelity_census_summary.csv",
        "tables/fidelity_census_summary.json",
        "tables/fidelity_census_summary.md",
        "tables/fidelity_census_summary.tex",
        "tables/representative_fidelity_controls.tsv",
        "tables/neighborhood_84_refinement.tsv",
        "figures/fidelity_hierarchy.svg",
        "figures/neighborhood_84_refinement_tree.svg",
        "data/fidelity_census_reconciled.tsv",
        "data/fidelity_census_reconciled.json",
        "manifest/hodgecy_ii_scope.json",
        "manifest/hodgecy_ii_asset_manifest.json",
    ]:
        assert (ASSET_ROOT / relative).exists()

    store_path = ASSET_ROOT / "data" / "hodgecy_ii_fidelity_result_store.sqlite"
    with sqlite3.connect(store_path) as conn:
        comparison_count = conn.execute("SELECT COUNT(*) FROM comparison_sets").fetchone()[0]
        geometry_count = conn.execute("SELECT COUNT(*) FROM geometries").fetchone()[0]
    assert comparison_count == 114
    assert geometry_count >= 456


def test_representative_controls_and_84_neighborhood_assets_are_status_aware() -> None:
    _ensure_assets()
    controls = {row["members"]: row for row in _tsv(ASSET_ROOT / "tables" / "representative_fidelity_controls.tsv")}
    neighborhood = {row["arrangement_id"]: row for row in _tsv(ASSET_ROOT / "tables" / "neighborhood_84_refinement.tsv")}
    tree = _json(ASSET_ROOT / "data" / "neighborhood_84_refinement_tree.json")

    assert controls["61 / 451"]["first_separation"] == "rational source type"
    assert controls["61 / 451"]["validation_status"] == "MIXED_WITH_HISTORICAL_ONLY_MEMBERS"
    assert controls["84 / 84a"]["shared_rational"] == "equal"
    assert controls["84 / 84a"]["first_separation"] == "integral/Smith type"
    assert controls["452 / 453"]["shared_rational"] == "equal"
    assert controls["452 / 453"]["validation_status"] == "MIXED_WITH_HISTORICAL_ONLY_MEMBERS"
    assert controls["84 / 240"]["shared_integral"] == "equal"
    assert controls["84 / 240"]["first_separation"] == "equivariant/symmetry type"
    assert controls["84a / 239"]["shared_integral"] == "equal"
    assert controls["239 / 240 / 241"]["first_separation"] == "rational source type"

    assert tree["local_fiber"]["members_display"] == "83 / 84 / 84a / 239 / 240 / 241"
    assert tree["rational_collapse"]["members_display"] == "84 / 84a / 239 / 240"
    assert {item["members_display"] for item in tree["integral_classes"]} == {"84 / 240", "84a / 239"}
    assert neighborhood["84"]["rank_Q"] == "26"
    assert neighborhood["84a"]["rank_mod_2"] == "21"
    assert neighborhood["239"]["validation_status"] == "CONTEXT_READY_SOURCE_RECOMPUTED"
    assert neighborhood["83"]["validation_status"] == "CENSUS_LEVEL"
    assert "do not establish projective equivalence" in neighborhood["84"]["note"]


def test_hodgecy_i_source_regression_records_are_present() -> None:
    _ensure_assets()
    regression = _json(ASSET_ROOT / "data" / "hodgecy_i_source_regression.json")

    assert set(regression) == {"84", "84a", "239", "240", "241"}
    assert regression["84"]["local_inventory"] == regression["84a"]["local_inventory"]
    assert regression["84"]["matrix_shape"] == [26, 28]
    assert regression["84a"]["matrix_shape"] == [26, 28]
    assert regression["239"]["smith_type"] == regression["84a"]["smith_type"]
    assert regression["240"]["smith_type"] == regression["84"]["smith_type"]
    assert regression["241"]["rank_Q"] == 24
    assert regression["241"]["rank_mod_2"] == 24


def test_asset_regeneration_is_semantically_deterministic() -> None:
    _ensure_assets()
    watched = [
        ASSET_ROOT / "tables" / "fidelity_census_summary.tsv",
        ASSET_ROOT / "tables" / "representative_fidelity_controls.tsv",
        ASSET_ROOT / "data" / "fidelity_census_reconciled.json",
        ASSET_ROOT / "figures" / "fidelity_hierarchy.svg",
    ]
    before = {path: path.read_bytes() for path in watched}
    _ensure_assets()
    after = {path: path.read_bytes() for path in watched}
    assert before == after


def test_readme_and_docs_index_links_are_local_and_present() -> None:
    _ensure_assets()
    for path in [REPO_ROOT / "README.md", REPO_ROOT / "docs" / "README.md"]:
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if "://" in target:
                continue
            local_target = target.split("#", maxsplit=1)[0]
            if not local_target:
                continue
            assert (path.parent / local_target).resolve().exists(), f"{path} links to missing {target}"
