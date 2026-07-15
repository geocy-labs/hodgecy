"""Build theorem-ready equivariant signature values for CKC 239/240/241."""

from __future__ import annotations

from itertools import combinations
import json
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
BATCH_DIR = REPO_ROOT / "data" / "processed" / "equivariant_spectra" / "ckc_fixed_rational_batch"
SPECTRA_PATH = BATCH_DIR / "ckc_fixed_rational_spectra.json"
PAIRS_PATH = BATCH_DIR / "ckc_fixed_rational_differentiating_pairs.csv"
OUT_VALUES = BATCH_DIR / "ckc_239_240_241_theorem_values.json"
OUT_SUMMARY = BATCH_DIR / "theorem_summary_239_240_241.json"
PAPER_TABLE_CSV = REPO_ROOT / "paper" / "tables" / "table_ckc_239_240_241_equivariant_signature.csv"
PAPER_TABLE_TEX = REPO_ROOT / "paper" / "tables" / "table_ckc_239_240_241_equivariant_signature.tex"
TARGET_IDS = ["239", "240", "241"]


def _inventory_signature(item: dict) -> str:
    inventory = item["computed_inventory"]
    keys = ("p3", "p4_0", "p4_1", "p5_0", "p5_1", "p5_2", "l3")
    return ",".join(f"{key}={int(inventory.get(key, 0))}" for key in keys)


def _orbit_sizes(orbits: list) -> str:
    return ",".join(str(len(orbit)) for orbit in sorted(orbits, key=lambda orbit: (len(orbit), str(orbit))))


def _character_distribution(character: dict) -> str:
    distribution = character.get("value_distribution", {})
    return ",".join(f"{key}:{distribution[key]}" for key in sorted(distribution, key=lambda value: int(value)))


def _snf(item: dict) -> str:
    return ",".join(str(value) for value in item["smith_normal_form"])


def _signature_fields(item: dict) -> dict:
    return {
        "automorphism_group_order": item["automorphism_group_order"],
        "gluing_matrix_shape": "x".join(str(value) for value in item["gluing_matrix_shape"]),
        "rank_Q": item["rank_Q"],
        "rank_F2": item["rank_F2"],
        "kernel_dim_Q": item["kernel_dim_Q"],
        "cokernel_dim_Q": item["cokernel_dim_Q"],
        "smith_normal_form": _snf(item),
        "plane_orbits": _orbit_sizes(item["plane_orbits"]),
        "double_line_orbits": _orbit_sizes(item["double_line_orbits"]),
        "multiple_point_orbits": _orbit_sizes(item["multiple_point_orbits"]),
        "character_C1": _character_distribution(item["character_C1"]),
        "character_C0": _character_distribution(item["character_C0"]),
    }


def _differing_fields(left: dict, right: dict) -> list[str]:
    left_signature = _signature_fields(left)
    right_signature = _signature_fields(right)
    return [key for key in left_signature if left_signature[key] != right_signature[key]]


def main() -> None:
    spectra_payload = json.loads(SPECTRA_PATH.read_text(encoding="utf-8"))
    spectra = {item["arrangement_id"]: item for item in spectra_payload["spectra"] if item["arrangement_id"] in TARGET_IDS}
    missing = [arrangement_id for arrangement_id in TARGET_IDS if arrangement_id not in spectra]
    if missing:
        raise RuntimeError(f"Missing spectra for theorem targets: {missing}")

    records = []
    for arrangement_id in TARGET_IDS:
        item = spectra[arrangement_id]
        records.append(
            {
                "arrangement_id": arrangement_id,
                "inventory": _inventory_signature(item),
                **_signature_fields(item),
            }
        )

    table = pd.DataFrame(records)
    PAPER_TABLE_CSV.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(PAPER_TABLE_CSV, index=False)
    PAPER_TABLE_TEX.write_text(table.to_latex(index=False, escape=False), encoding="utf-8")

    pair_differences = {}
    for left_id, right_id in combinations(TARGET_IDS, 2):
        pair_differences[f"{left_id}_vs_{right_id}"] = _differing_fields(spectra[left_id], spectra[right_id])

    inventories = {_inventory_signature(item) for item in spectra.values()}
    same_inventory = len(inventories) == 1
    pairwise_all_equal = all(not fields for fields in pair_differences.values())

    theorem_values = {
        "arrangement_ids": TARGET_IDS,
        "records": records,
        "source_spectra": str(SPECTRA_PATH.relative_to(REPO_ROOT)),
        "source_pairs": str(PAIRS_PATH.relative_to(REPO_ROOT)),
        "paper_table_csv": str(PAPER_TABLE_CSV.relative_to(REPO_ROOT)),
        "paper_table_tex": str(PAPER_TABLE_TEX.relative_to(REPO_ROOT)),
    }
    OUT_VALUES.write_text(json.dumps(theorem_values, indent=2), encoding="utf-8")

    theorem_summary = {
        "arrangement_ids": TARGET_IDS,
        "same_inventory": same_inventory,
        "shared_inventory": next(iter(inventories)) if same_inventory else None,
        "pairwise_equivariant_signatures_all_equal": pairwise_all_equal,
        "differentiating_fields": pair_differences,
        "theorem_statement_ready": same_inventory and not pairwise_all_equal,
    }
    OUT_SUMMARY.write_text(json.dumps(theorem_summary, indent=2), encoding="utf-8")

    print("Built theorem-ready values for CKC 239/240/241:")
    for record in records:
        print(
            f"- {record['arrangement_id']}: |G|={record['automorphism_group_order']}, "
            f"rank_Q={record['rank_Q']}, rank_F2={record['rank_F2']}, "
            f"kernel={record['kernel_dim_Q']}, cokernel={record['cokernel_dim_Q']}"
        )
    print(f"Table: {PAPER_TABLE_CSV}")
    print(f"Summary: {OUT_SUMMARY}")


if __name__ == "__main__":
    main()
