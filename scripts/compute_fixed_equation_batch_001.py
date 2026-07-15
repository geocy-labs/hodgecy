"""Compute equivariant incidence-gluing spectra for CKC fixed batch 001.

Batch 001 is deliberately conservative: it ingests only currently repo-backed
CKC records that are validated, fixed representatives with no parameters. The
current machine-readable CKC data contain 84 and 84a in that category; 83 is
parameterized/provisional and is reported as excluded.
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


RAW_CONTROL_PATH = REPO_ROOT / "data" / "raw" / "cynk_kocel_cynk_2026" / "control_triple_83_84_84a.json"
BATCH_METADATA_PATH = REPO_ROOT / "data" / "raw" / "cynk_kocel_cynk_2026" / "fixed_equation_batch_001.json"
OUT_DIR = REPO_ROOT / "data" / "processed" / "equivariant_spectra" / "fixed_equation_batch_001"


def _load_control_records() -> list[dict[str, Any]]:
    payload = json.loads(RAW_CONTROL_PATH.read_text(encoding="utf-8"))
    return list(payload["records"])


def _load_batch_metadata() -> dict[str, Any]:
    return json.loads(BATCH_METADATA_PATH.read_text(encoding="utf-8"))


def _is_batch_record(record: dict[str, Any], batch_ids: set[str]) -> bool:
    return (
        str(record.get("arrangement_id")) in batch_ids
        and record.get("representative_status") == "validated"
        and record.get("parameter_status") == "fixed_representative"
        and not record.get("parameter_choice")
    )


def _skip_reason(record: dict[str, Any], batch_ids: set[str]) -> str:
    reasons = []
    if str(record.get("arrangement_id")) not in batch_ids:
        reasons.append("not_in_batch_metadata")
    if record.get("representative_status") != "validated":
        reasons.append(f"representative_status={record.get('representative_status')}")
    if record.get("parameter_status") != "fixed_representative":
        reasons.append(f"parameter_status={record.get('parameter_status')}")
    if record.get("parameter_choice"):
        reasons.append("parameter_choice_present")
    return "; ".join(reasons) or "not_selected"


def _inventory_signature(item: dict[str, Any]) -> str:
    inventory = item.get("computed_inventory") or {}
    keys = ("p3", "p4_0", "p4_1", "p5_0", "p5_1", "p5_2", "l3")
    return ";".join(f"{key}={int(inventory.get(key, 0))}" for key in keys)


def _hodge_signature(item: dict[str, Any]) -> str:
    hodge = item.get("hodge_data_if_known") or {}
    return ";".join(f"{key}={hodge.get(key)}" for key in ("h12", "h11", "euler"))


def _orbit_sizes(orbits: list[Any]) -> str:
    return ",".join(str(len(orbit)) for orbit in sorted(orbits, key=lambda orbit: (len(orbit), str(orbit))))


def _snf(item: dict[str, Any]) -> str:
    return ",".join(str(value) for value in (item.get("smith_normal_form") or []))


def _character_signature(character: dict[str, Any]) -> str:
    distribution = character.get("value_distribution", {})
    return ";".join(f"{key}:{distribution[key]}" for key in sorted(distribution, key=str))


def _equivariant_signature(item: dict[str, Any]) -> str:
    payload = {
        "automorphism_group_order": item["automorphism_group_order"],
        "rank_Q": item["rank_Q"],
        "rank_F2": item["rank_F2"],
        "smith_normal_form": _snf(item),
        "plane_orbit_sizes": _orbit_sizes(item["plane_orbits"]),
        "double_line_orbit_sizes": _orbit_sizes(item["double_line_orbits"]),
        "multiple_point_orbit_sizes": _orbit_sizes(item["multiple_point_orbits"]),
        "character_C1": _character_signature(item["character_C1"]),
        "character_C0": _character_signature(item["character_C0"]),
    }
    return json.dumps(payload, sort_keys=True)


def _summary_row(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "arrangement_id": item["arrangement_id"],
        "representative_status": item["representative_status"],
        "source_reference": item["source_reference"],
        "local_inventory_signature": _inventory_signature(item),
        "hodge_signature": _hodge_signature(item),
        "h12": (item.get("hodge_data_if_known") or {}).get("h12"),
        "h11": (item.get("hodge_data_if_known") or {}).get("h11"),
        "euler": (item.get("hodge_data_if_known") or {}).get("euler"),
        "incidence_table_size": len(item["incidence_table"]),
        "automorphism_group_order": item["automorphism_group_order"],
        "gluing_matrix_shape": "x".join(str(value) for value in item["gluing_matrix_shape"]),
        "rank_Q": item["rank_Q"],
        "rank_F2": item["rank_F2"],
        "kernel_dim_Q": item["kernel_dim_Q"],
        "cokernel_dim_Q": item["cokernel_dim_Q"],
        "smith_normal_form": _snf(item),
        "plane_orbit_sizes": _orbit_sizes(item["plane_orbits"]),
        "double_line_orbit_sizes": _orbit_sizes(item["double_line_orbits"]),
        "multiple_point_orbit_sizes": _orbit_sizes(item["multiple_point_orbits"]),
        "character_C1_distribution": item["character_C1"]["value_distribution"],
        "character_C0_distribution": item["character_C0"]["value_distribution"],
        "equivariant_signature": _equivariant_signature(item),
    }


def _difference_summary(left: dict[str, Any], right: dict[str, Any]) -> str:
    comparisons = [
        ("automorphism_group_order", left["automorphism_group_order"], right["automorphism_group_order"]),
        ("rank_Q", left["rank_Q"], right["rank_Q"]),
        ("rank_F2", left["rank_F2"], right["rank_F2"]),
        ("smith_normal_form", _snf(left), _snf(right)),
        ("plane_orbits", _orbit_sizes(left["plane_orbits"]), _orbit_sizes(right["plane_orbits"])),
        ("double_line_orbits", _orbit_sizes(left["double_line_orbits"]), _orbit_sizes(right["double_line_orbits"])),
        ("multiple_point_orbits", _orbit_sizes(left["multiple_point_orbits"]), _orbit_sizes(right["multiple_point_orbits"])),
        ("character_C1", _character_signature(left["character_C1"]), _character_signature(right["character_C1"])),
        ("character_C0", _character_signature(left["character_C0"]), _character_signature(right["character_C0"])),
    ]
    return "; ".join(name for name, left_value, right_value in comparisons if left_value != right_value)


def _write_markdown_table(df: pd.DataFrame, path: Path) -> None:
    headers = [str(column) for column in df.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in df.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    batch_metadata = _load_batch_metadata()
    batch_ids = {str(item) for item in batch_metadata["arrangement_ids"]}
    all_records = _load_control_records()
    selected_records = [record for record in all_records if _is_batch_record(record, batch_ids)]
    skipped_records = [
        {"arrangement_id": str(record.get("arrangement_id")), "reason": _skip_reason(record, batch_ids)}
        for record in all_records
        if not _is_batch_record(record, batch_ids)
    ]

    spectra = []
    for record in selected_records:
        spectrum = spectrum_to_dict(build_equivariant_spectrum(record))
        spectra.append(spectrum)
        arrangement_id = spectrum["arrangement_id"]
        (OUT_DIR / f"hodgecy_equivariant_spectrum_{arrangement_id}.json").write_text(
            json.dumps(spectrum, indent=2),
            encoding="utf-8",
        )

    summary_rows = [_summary_row(item) for item in spectra]
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(OUT_DIR / "spectrum_summary.csv", index=False)
    _write_markdown_table(summary_df.drop(columns=["equivariant_signature"]), OUT_DIR / "spectrum_summary.md")

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in summary_rows:
        grouped.setdefault((row["local_inventory_signature"], row["hodge_signature"]), []).append(row)

    cluster_rows = []
    pair_rows = []
    cluster_payload = {
        "batch_id": batch_metadata["batch_id"],
        "source": batch_metadata["source"],
        "source_reference": batch_metadata["source_reference"],
        "selection_rule": batch_metadata["selection_rule"],
        "coverage": {
            "total_control_records": len(all_records),
            "selected_fixed_equation_records": len(selected_records),
            "selected_arrangement_ids": [item["arrangement_id"] for item in spectra],
            "skipped_records": skipped_records,
            "coverage_note": batch_metadata["coverage_note"],
        },
        "clusters": [],
    }

    spectra_by_id = {item["arrangement_id"]: item for item in spectra}
    for index, ((inventory_signature, hodge_signature), members) in enumerate(sorted(grouped.items()), start=1):
        cluster_id = f"fixed_equation_batch_001_cluster_{index:03d}"
        member_ids = [member["arrangement_id"] for member in members]
        signatures = sorted({member["equivariant_signature"] for member in members})
        equivariant_data_varies = len(signatures) > 1
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
                "plane_orbit_sizes": " | ".join(member["plane_orbit_sizes"] for member in members),
                "double_line_orbit_sizes": " | ".join(member["double_line_orbit_sizes"] for member in members),
                "multiple_point_orbit_sizes": " | ".join(member["multiple_point_orbit_sizes"] for member in members),
            }
        )
        cluster_payload["clusters"].append(
            {
                "cluster_id": cluster_id,
                "members": member_ids,
                "local_inventory_signature": inventory_signature,
                "hodge_signature": hodge_signature,
                "equivariant_data_varies": equivariant_data_varies,
                "member_summaries": members,
            }
        )

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
                    "left_smith_normal_form": _snf(left),
                    "right_smith_normal_form": _snf(right),
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
    cluster_df.to_csv(OUT_DIR / "clusters_by_inventory_hodge.csv", index=False)
    pair_df.to_csv(OUT_DIR / "differentiating_pairs_same_inventory_hodge.csv", index=False)
    _write_markdown_table(cluster_df, OUT_DIR / "clusters_by_inventory_hodge.md")
    _write_markdown_table(pair_df, OUT_DIR / "differentiating_pairs_same_inventory_hodge.md")
    (OUT_DIR / "clusters_by_inventory_hodge.json").write_text(json.dumps(cluster_payload, indent=2), encoding="utf-8")

    report = {
        "batch_id": batch_metadata["batch_id"],
        "selected_count": len(selected_records),
        "selected_arrangement_ids": [item["arrangement_id"] for item in spectra],
        "skipped_records": skipped_records,
        "cluster_count": len(cluster_rows),
        "differentiating_pair_count": len(pair_rows),
        "outputs": {
            "summary_csv": "spectrum_summary.csv",
            "summary_md": "spectrum_summary.md",
            "clusters_csv": "clusters_by_inventory_hodge.csv",
            "clusters_json": "clusters_by_inventory_hodge.json",
            "differentiating_pairs_csv": "differentiating_pairs_same_inventory_hodge.csv",
            "differentiating_pairs_md": "differentiating_pairs_same_inventory_hodge.md",
        },
    }
    (OUT_DIR / "batch_manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("Computed CKC fixed-equation batch 001:")
    print(f"- selected records: {len(selected_records)}")
    print(f"- skipped records: {len(skipped_records)}")
    print(f"- clusters: {len(cluster_rows)}")
    print(f"- differentiating pairs: {len(pair_rows)}")
    print(f"Output directory: {OUT_DIR}")


if __name__ == "__main__":
    main()
