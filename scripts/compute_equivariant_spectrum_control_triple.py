"""Compute additive equivariant HodgeCY spectra for the 83/84/84a control triple."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.equivariant import build_equivariant_spectrum, spectrum_to_dict  # noqa: E402


RAW_PATH = REPO_ROOT / "data" / "raw" / "cynk_kocel_cynk_2026" / "control_triple_83_84_84a.json"
OUT_DIR = REPO_ROOT / "data" / "processed" / "equivariant_spectra"
PAPER_TABLE_DIR = REPO_ROOT / "paper" / "tables"


def _load_records() -> list[dict]:
    payload = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    return list(payload["records"])


def _p4_graph_summary(arrangement_id: str) -> dict | None:
    path = REPO_ROOT / "data" / "processed" / "paper_figures" / f"fig_concurrency_graph_{arrangement_id}_metadata.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _perturbation_status(arrangement_id: str) -> str | None:
    path = REPO_ROOT / "data" / "processed" / f"smoothing_verification_{arrangement_id}.json"
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("verification_status")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _orbit_summary(orbits: list) -> str:
    sizes = sorted(len(orbit) for orbit in orbits)
    return ",".join(str(size) for size in sizes)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PAPER_TABLE_DIR.mkdir(parents=True, exist_ok=True)
    spectra = []
    for record in _load_records():
        arrangement_id = str(record["arrangement_id"])
        spectrum = build_equivariant_spectrum(
            record,
            p4_graph_summary_if_available=_p4_graph_summary(arrangement_id),
            perturbation_status_if_available=_perturbation_status(arrangement_id),
        )
        payload = spectrum_to_dict(spectrum)
        _write_json(OUT_DIR / f"hodgecy_equivariant_spectrum_{arrangement_id}.json", payload)
        spectra.append(payload)

    summary = pd.DataFrame(
        [
            {
                "arrangement_id": item["arrangement_id"],
                "representative_status": item["representative_status"],
                "inventory_matches_expected": item["inventory_matches_expected"],
                "incidence_table_size": len(item["incidence_table"]),
                "automorphism_group_order": item["automorphism_group_order"],
                "gluing_matrix_shape": "x".join(str(value) for value in item["gluing_matrix_shape"]),
                "rank_Q": item["rank_Q"],
                "rank_F2": item["rank_F2"],
                "kernel_dim_Q": item["kernel_dim_Q"],
                "cokernel_dim_Q": item["cokernel_dim_Q"],
                "smith_normal_form": ",".join(str(value) for value in (item["smith_normal_form"] or [])),
                "perturbation_status_if_available": item["perturbation_status_if_available"],
                "notes": item["notes"],
            }
            for item in spectra
        ]
    )
    summary_path = OUT_DIR / "hodgecy_equivariant_spectrum_control_triple_summary.csv"
    summary.to_csv(summary_path, index=False)

    equivariant_table = summary[
        [
            "arrangement_id",
            "representative_status",
            "inventory_matches_expected",
            "incidence_table_size",
            "automorphism_group_order",
            "gluing_matrix_shape",
            "rank_Q",
            "kernel_dim_Q",
            "cokernel_dim_Q",
        ]
    ]
    equivariant_table.to_csv(PAPER_TABLE_DIR / "table_equivariant_spectrum_control_triple.csv", index=False)
    (PAPER_TABLE_DIR / "table_equivariant_spectrum_control_triple.tex").write_text(equivariant_table.to_latex(index=False), encoding="utf-8")

    gluing_table = pd.DataFrame(
        [
            {
                "arrangement_id": item["arrangement_id"],
                "representative_status": item["representative_status"],
                "gluing_matrix_shape": "x".join(str(value) for value in item["gluing_matrix_shape"]),
                "rank_Q": item["rank_Q"],
                "rank_F2": item["rank_F2"],
                "kernel_dim_Q": item["kernel_dim_Q"],
                "cokernel_dim_Q": item["cokernel_dim_Q"],
                "row_degree_distribution": item["row_degree_distribution"],
                "column_degree_distribution": item["column_degree_distribution"],
            }
            for item in spectra
        ]
    )
    gluing_table.to_csv(PAPER_TABLE_DIR / "table_gluing_complex_control_triple.csv", index=False)
    (PAPER_TABLE_DIR / "table_gluing_complex_control_triple.tex").write_text(gluing_table.to_latex(index=False, escape=False), encoding="utf-8")

    orbit_table = pd.DataFrame(
        [
            {
                "arrangement_id": item["arrangement_id"],
                "plane_orbit_sizes": _orbit_summary(item["plane_orbits"]),
                "double_line_orbit_sizes": _orbit_summary(item["double_line_orbits"]),
                "multiple_point_orbit_sizes": _orbit_summary(item["multiple_point_orbits"]),
                "character_C1_distribution": item["character_C1"]["value_distribution"],
                "character_C0_distribution": item["character_C0"]["value_distribution"],
            }
            for item in spectra
        ]
    )
    orbit_table.to_csv(PAPER_TABLE_DIR / "table_automorphism_orbits_control_triple.csv", index=False)
    (PAPER_TABLE_DIR / "table_automorphism_orbits_control_triple.tex").write_text(orbit_table.to_latex(index=False, escape=False), encoding="utf-8")

    print("Computed equivariant spectra:")
    for item in spectra:
        print(
            f"- {item['arrangement_id']}: incidence={len(item['incidence_table'])}, "
            f"|G|={item['automorphism_group_order']}, matrix={item['gluing_matrix_shape']}, rank_Q={item['rank_Q']}"
        )
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
