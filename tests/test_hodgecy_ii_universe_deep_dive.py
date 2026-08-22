from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = REPO_ROOT / "research_outputs" / "hodgecy_ii"
SCRIPT_PATH = REPO_ROOT / "scripts" / "hodgecy_ii_universe_deep_dive.py"


spec = importlib.util.spec_from_file_location("hodgecy_ii_universe_deep_dive", SCRIPT_PATH)
assert spec is not None
assert spec.loader is not None
deep_dive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deep_dive)


def test_universe_deep_dive_outputs_and_denominators() -> None:
    deep_dive.run_repo_local()

    manifest = json.loads((OUT_ROOT / "universe" / "universe_manifest.json").read_text(encoding="utf-8"))
    denominators = manifest["denominators"]

    assert manifest["corpus_summary"]["logical_dataset_count"] == 53
    assert denominators["IS_COMPLETE_HODGECY_II_UNIVERSE_455"] == "NO"
    assert denominators["CKC_NUMBERED_RECORDS"] == 455
    assert denominators["CKC_PAIRWISE_COUNT"] == 103285
    assert denominators["COMPARABLE_SOURCE_PRESENTATION_COUNT_REPO_LOCAL"] == 456
    assert "source assembly is not node relation" in manifest["problem_7_10_firewall"]


def test_ckc_crosswalk_and_pairwise_scope() -> None:
    deep_dive.run_repo_local()

    with (OUT_ROOT / "ckc455_crosswalk.tsv").open("r", encoding="utf-8", newline="") as handle:
        crosswalk = list(csv.DictReader(handle, delimiter="\t"))
    assert len(crosswalk) == 455

    pairwise = pd.read_parquet(OUT_ROOT / "all_pairwise_source_comparisons.parquet")
    assert len(pairwise) == 103740
    assert int(pairwise["ckc_pair"].sum()) == 103285

    focus = pairwise[
        ((pairwise["left_id"] == "84") & (pairwise["right_id"] == "84a"))
        | ((pairwise["left_id"] == "239") & (pairwise["right_id"] == "240"))
    ]
    assert not focus.empty
    assert set(focus["node_level_result"]) == {"unresolved"}
    assert set(focus["hodge_atom_result"]) == {"unresolved"}


def test_no_census_eligible_field_in_new_machine_records() -> None:
    deep_dive.run_repo_local()

    universe_rows = pd.read_parquet(OUT_ROOT / "universe" / "universe_records.parquet")
    presentation_rows = pd.read_parquet(OUT_ROOT / "all_source_presentations.parquet")

    assert "census_eligible" not in universe_rows.columns
    assert "census_eligible" not in presentation_rows.columns
    assert "claim_level_firewall" in presentation_rows.columns


def test_discovery_sets_include_core_witnesses() -> None:
    deep_dive.run_repo_local()

    fixed = json.loads((OUT_ROOT / "all_fixed_local_hodge_sets.json").read_text(encoding="utf-8"))
    local = json.loads((OUT_ROOT / "all_local_inventory_fidelity_sets.json").read_text(encoding="utf-8"))
    rational = json.loads((OUT_ROOT / "all_rational_collapse_integral_sets.json").read_text(encoding="utf-8"))
    problem = json.loads((OUT_ROOT / "all_problem_7_10_candidate_sets.json").read_text(encoding="utf-8"))

    assert any(set(item["members"]) == {"84", "84a"} for item in fixed)
    unresolved_pairs = {tuple(item["members"]): item for item in fixed}
    assert unresolved_pairs[("61", "451")]["finer_source_variation"] == "UNKNOWN"
    assert unresolved_pairs[("452", "453")]["finer_source_variation"] == "UNKNOWN"
    assert any({"84", "84a", "239", "240", "241"}.issubset(set(item["members"])) for item in local)
    assert any({"84", "84a", "239", "240"}.issubset(set(item["members"])) for item in rational)
    assert {target["members"][0] for target in problem} == {"84", "84a"}
