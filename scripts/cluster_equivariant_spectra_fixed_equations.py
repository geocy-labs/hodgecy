"""Cluster equivariant incidence-gluing spectra for fixed CKC equations.

This script is intentionally additive. It only uses currently ingested
Cynk--Kocel--Cynk records whose representatives are fixed, validated, and
non-parameterized. Parameterized/provisional records are reported as skipped
rather than silently mixed into paper-facing fixed-equation clusters.
"""

from __future__ import annotations

from itertools import combinations
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.equivariant import build_equivariant_spectrum, spectrum_to_dict  # noqa: E402


RAW_PATH = REPO_ROOT / "data" / "raw" / "cynk_kocel_cynk_2026" / "control_triple_83_84_84a.json"
OUT_DIR = REPO_ROOT / "data" / "processed" / "equivariant_spectra"
PAPER_TABLE_DIR = REPO_ROOT / "paper" / "tables"

SUMMARY_CSV = OUT_DIR / "fixed_equation_equivariant_spectrum_summary.csv"
CLUSTERS_JSON = OUT_DIR / "fixed_equation_equivariant_clusters.json"
CLUSTER_MEMBERS_CSV = OUT_DIR / "fixed_equation_equivariant_cluster_members.csv"
DIFFERENTIATING_PAIRS_CSV = OUT_DIR / "fixed_equation_equivariant_differentiating_pairs.csv"

PAPER_CLUSTER_CSV = PAPER_TABLE_DIR / "table_fixed_equation_equivariant_clusters.csv"
PAPER_CLUSTER_TEX = PAPER_TABLE_DIR / "table_fixed_equation_equivariant_clusters.tex"
PAPER_PAIRS_CSV = PAPER_TABLE_DIR / "table_fixed_equation_equivariant_differentiating_pairs.csv"
PAPER_PAIRS_TEX = PAPER_TABLE_DIR / "table_fixed_equation_equivariant_differentiating_pairs.tex"


def _load_records() -> list[dict[str, Any]]:
    payload = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    return list(payload["records"])


def _is_fixed_non_parameterized(record: dict[str, Any]) -> bool:
    return (
        record.get("representative_status") == "validated"
        and record.get("parameter_status") == "fixed_representative"
        and not record.get("parameter_choice")
    )


def _skip_reason(record: dict[str, Any]) -> str:
    reasons = []
    if record.get("representative_status") != "validated":
        reasons.append(f"representative_status={record.get('representative_status')}")
    if record.get("parameter_status") != "fixed_representative":
        reasons.append(f"parameter_status={record.get('parameter_status')}")
    if record.get("parameter_choice"):
        reasons.append("parameter_choice_present")
    return "; ".join(reasons) or "not_fixed_non_parameterized"


def _inventory_signature(item: dict[str, Any]) -> str:
    inventory = item.get("computed_inventory") or {}
    keys = ("p3", "p4_0", "p4_1", "p5_0", "p5_1", "p5_2", "l3")
    return ";".join(f"{key}={int(inventory.get(key, 0))}" for key in keys)


def _hodge_signature(item: dict[str, Any]) -> str:
    hodge = item.get("hodge_data_if_known") or {}
    keys = ("h12", "h11", "euler")
    return ";".join(f"{key}={hodge.get(key)}" for key in keys)


def _orbit_sizes(orbits: list[Any]) -> str:
    return ",".join(str(len(orbit)) for orbit in sorted(orbits, key=lambda orbit: (len(orbit), str(orbit))))


def _snf_signature(item: dict[str, Any]) -> str:
    return ",".join(str(value) for value in (item.get("smith_normal_form") or []))


def _character_signature(character: dict[str, Any]) -> str:
    distribution = character.get("value_distribution", {})
    return ";".join(f"{key}:{distribution[key]}" for key in sorted(distribution, key=str))


def _equivariant_signature(item: dict[str, Any]) -> str:
    parts = {
        "group_order": item["automorphism_group_order"],
        "rank_Q": item["rank_Q"],
        "rank_F2": item["rank_F2"],
        "snf": _snf_signature(item),
        "plane_orbits": _orbit_sizes(item["plane_orbits"]),
        "double_line_orbits": _orbit_sizes(item["double_line_orbits"]),
        "multiple_point_orbits": _orbit_sizes(item["multiple_point_orbits"]),
        "character_C1": _character_signature(item["character_C1"]),
        "character_C0": _character_signature(item["character_C0"]),
    }
    return json.dumps(parts, sort_keys=True)


def _difference_summary(left: dict[str, Any], right: dict[str, Any]) -> str:
    checks = [
        ("automorphism_group_order", left["automorphism_group_order"], right["automorphism_group_order"]),
        ("rank_Q", left["rank_Q"], right["rank_Q"]),
        ("rank_F2", left["rank_F2"], right["rank_F2"]),
        ("smith_normal_form", _snf_signature(left), _snf_signature(right)),
        ("plane_orbits", _orbit_sizes(left["plane_orbits"]), _orbit_sizes(right["plane_orbits"])),
        ("double_line_orbits", _orbit_sizes(left["double_line_orbits"]), _orbit_sizes(right["double_line_orbits"])),
        ("multiple_point_orbits", _orbit_sizes(left["multiple_point_orbits"]), _orbit_sizes(right["multiple_point_orbits"])),
        ("character_C1", _character_signature(left["character_C1"]), _character_signature(right["character_C1"])),
        ("character_C0", _character_signature(left["character_C0"]), _character_signature(right["character_C0"])),
    ]
    return "; ".join(name for name, left_value, right_value in checks if left_value != right_value)


def _summary_row(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "arrangement_id": item["arrangement_id"],
        "representative_status": item["representative_status"],
        "parameter_status": "fixed_representative",
        "local_inventory_signature": _inventory_signature(item),
        "hodge_signature": _hodge_signature(item),
        "incidence_table_size": len(item["incidence_table"]),
        "automorphism_group_order": item["automorphism_group_order"],
        "gluing_matrix_shape": "x".join(str(value) for value in item["gluing_matrix_shape"]),
        "rank_Q": item["rank_Q"],
        "rank_F2": item["rank_F2"],
        "kernel_dim_Q": item["kernel_dim_Q"],
        "cokernel_dim_Q": item["cokernel_dim_Q"],
        "smith_normal_form": _snf_signature(item),
        "plane_orbit_sizes": _orbit_sizes(item["plane_orbits"]),
        "double_line_orbit_sizes": _orbit_sizes(item["double_line_orbits"]),
        "multiple_point_orbit_sizes": _orbit_sizes(item["multiple_point_orbits"]),
        "character_C1_distribution": item["character_C1"]["value_distribution"],
        "character_C0_distribution": item["character_C0"]["value_distribution"],
        "equivariant_signature": _equivariant_signature(item),
    }


def _latex_table(df: pd.DataFrame, path: Path) -> None:
    path.write_text(df.to_latex(index=False, escape=False), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PAPER_TABLE_DIR.mkdir(parents=True, exist_ok=True)

    all_records = _load_records()
    fixed_records = [record for record in all_records if _is_fixed_non_parameterized(record)]
    skipped_records = [
        {"arrangement_id": str(record.get("arrangement_id")), "reason": _skip_reason(record)}
        for record in all_records
        if not _is_fixed_non_parameterized(record)
    ]

    spectra = [spectrum_to_dict(build_equivariant_spectrum(record)) for record in fixed_records]
    summary_rows = [_summary_row(item) for item in spectra]
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(SUMMARY_CSV, index=False)

    cluster_rows = []
    pair_rows = []
    clusters_payload: dict[str, Any] = {
        "source": str(RAW_PATH.relative_to(REPO_ROOT)),
        "coverage": {
            "total_ingested_records": len(all_records),
            "fixed_non_parameterized_records": len(fixed_records),
            "skipped_records": skipped_records,
            "notes": (
                "This batch covers currently ingested fixed, validated, non-parameterized CKC records only. "
                "Full 455-type CKC coverage requires additional raw equation ingestion."
            ),
        },
        "clusters": [],
    }

    if summary_rows:
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for item in summary_rows:
            grouped.setdefault((item["local_inventory_signature"], item["hodge_signature"]), []).append(item)

        for index, ((inventory_signature, hodge_signature), members) in enumerate(sorted(grouped.items()), start=1):
            equivariant_signatures = sorted({member["equivariant_signature"] for member in members})
            cluster_id = f"fixed_local_hodge_cluster_{index:03d}"
            member_ids = [member["arrangement_id"] for member in members]
            equivariant_data_varies = len(equivariant_signatures) > 1
            cluster_rows.append(
                {
                    "cluster_id": cluster_id,
                    "member_count": len(members),
                    "members": ",".join(member_ids),
                    "local_inventory_signature": inventory_signature,
                    "hodge_signature": hodge_signature,
                    "equivariant_data_varies": equivariant_data_varies,
                    "automorphism_group_orders": ",".join(str(member["automorphism_group_order"]) for member in members),
                    "rank_Q_values": ",".join(str(member["rank_Q"]) for member in members),
                    "rank_F2_values": ",".join(str(member["rank_F2"]) for member in members),
                    "smith_normal_forms": " | ".join(member["smith_normal_form"] for member in members),
                }
            )
            clusters_payload["clusters"].append(
                {
                    "cluster_id": cluster_id,
                    "members": member_ids,
                    "local_inventory_signature": inventory_signature,
                    "hodge_signature": hodge_signature,
                    "equivariant_data_varies": equivariant_data_varies,
                    "member_summaries": members,
                }
            )

            if len(members) > 1:
                spectra_by_id = {item["arrangement_id"]: item for item in spectra}
                for left_row, right_row in combinations(members, 2):
                    if left_row["equivariant_signature"] == right_row["equivariant_signature"]:
                        continue
                    left = spectra_by_id[left_row["arrangement_id"]]
                    right = spectra_by_id[right_row["arrangement_id"]]
                    pair_rows.append(
                        {
                            "cluster_id": cluster_id,
                            "left_arrangement": left["arrangement_id"],
                            "right_arrangement": right["arrangement_id"],
                            "shared_local_inventory": inventory_signature,
                            "shared_hodge": hodge_signature,
                            "left_automorphism_group_order": left["automorphism_group_order"],
                            "right_automorphism_group_order": right["automorphism_group_order"],
                            "left_rank_Q": left["rank_Q"],
                            "right_rank_Q": right["rank_Q"],
                            "left_rank_F2": left["rank_F2"],
                            "right_rank_F2": right["rank_F2"],
                            "left_smith_normal_form": _snf_signature(left),
                            "right_smith_normal_form": _snf_signature(right),
                            "left_plane_orbit_sizes": _orbit_sizes(left["plane_orbits"]),
                            "right_plane_orbit_sizes": _orbit_sizes(right["plane_orbits"]),
                            "left_double_line_orbit_sizes": _orbit_sizes(left["double_line_orbits"]),
                            "right_double_line_orbit_sizes": _orbit_sizes(right["double_line_orbits"]),
                            "left_multiple_point_orbit_sizes": _orbit_sizes(left["multiple_point_orbits"]),
                            "right_multiple_point_orbit_sizes": _orbit_sizes(right["multiple_point_orbits"]),
                            "differences": _difference_summary(left, right),
                        }
                    )

    cluster_df = pd.DataFrame(cluster_rows)
    pair_df = pd.DataFrame(pair_rows)
    cluster_df.to_csv(CLUSTER_MEMBERS_CSV, index=False)
    pair_df.to_csv(DIFFERENTIATING_PAIRS_CSV, index=False)
    CLUSTERS_JSON.write_text(json.dumps(clusters_payload, indent=2), encoding="utf-8")

    paper_cluster_cols = [
        "cluster_id",
        "members",
        "local_inventory_signature",
        "hodge_signature",
        "equivariant_data_varies",
        "automorphism_group_orders",
        "rank_Q_values",
        "rank_F2_values",
    ]
    paper_pair_cols = [
        "left_arrangement",
        "right_arrangement",
        "shared_hodge",
        "left_automorphism_group_order",
        "right_automorphism_group_order",
        "left_rank_Q",
        "right_rank_Q",
        "left_rank_F2",
        "right_rank_F2",
        "differences",
    ]
    cluster_df[paper_cluster_cols].to_csv(PAPER_CLUSTER_CSV, index=False)
    _latex_table(cluster_df[paper_cluster_cols], PAPER_CLUSTER_TEX)
    pair_df[paper_pair_cols].to_csv(PAPER_PAIRS_CSV, index=False)
    _latex_table(pair_df[paper_pair_cols], PAPER_PAIRS_TEX)

    print("Clustered fixed non-parameterized equivariant spectra:")
    print(f"- ingested records: {len(all_records)}")
    print(f"- included fixed records: {len(fixed_records)}")
    print(f"- skipped records: {len(skipped_records)}")
    print(f"- local/Hodge clusters: {len(cluster_rows)}")
    print(f"- differentiating pairs: {len(pair_rows)}")
    print(f"Summary: {SUMMARY_CSV}")
    print(f"Pairs: {DIFFERENTIATING_PAIRS_CSV}")


if __name__ == "__main__":
    main()
