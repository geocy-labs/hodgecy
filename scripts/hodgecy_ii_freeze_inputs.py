"""Freeze initial HodgeCY II 84/84a research inputs.

This script copies small, exact, repo-backed source facts into research
manifests and creates formal 28 x 4 block partitions. It does not promote the
current smoothing bridge records beyond their recorded verification status.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.research import beta_block_expansion_matrix  # noqa: E402


ARRANGEMENTS = ("84", "84a")
Q0 = "x^4 + 2*y^4 + 3*z^4 + 5*t^4 + x*y*z*t"
EPSILON = "1"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _spectrum_rows() -> dict[str, dict[str, str]]:
    path = REPO_ROOT / "data" / "processed" / "equivariant_spectra" / "fixed_equation_batch_001" / "spectrum_summary.csv"
    return {row["arrangement_id"]: row for row in _read_csv_rows(path)}


def _block_records(arrangement_id: str) -> list[dict[str, Any]]:
    path = REPO_ROOT / "data" / "processed" / f"smoothing_bridge_{arrangement_id}_double_lines.csv"
    rows = _read_csv_rows(path)
    blocks: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        block_id = f"{arrangement_id}_B{index:02d}"
        nodes = [f"{block_id}_n{node_index}" for node_index in range(1, 5)]
        blocks.append(
            {
                "block_id": block_id,
                "source_double_line_index": index,
                "line_key": row["line_key"],
                "plane_pairs": row["plane_pairs"].split(";"),
                "node_ids": nodes,
                "node_count": 4,
                "status": "formal_block_from_squarefree_quartic_restriction",
            }
        )
    return blocks


def _beta_summary(block_count: int) -> dict[str, Any]:
    matrix = beta_block_expansion_matrix(block_count, nodes_per_block=4)
    return {
        "matrix_shape": [int(matrix.rows), int(matrix.cols)],
        "rank_Q": int(matrix.rank()),
        "column_sums": [int(sum(matrix[row, col] for row in range(matrix.rows))) for col in range(matrix.cols)],
        "row_sums_all_one": all(int(sum(matrix[row, col] for col in range(matrix.cols))) == 1 for row in range(matrix.rows)),
        "smith_normal_form": [1 for _ in range(block_count)],
        "interpretation": "Formal block expansion beta_A: Z<double_lines> -> Z<formal_nodes>; no Hodge meaning assigned.",
    }


def _manifest(arrangement_id: str, spectrum: dict[str, str]) -> dict[str, Any]:
    theorem = _read_json(REPO_ROOT / "release" / "hodgecy-v0.2.0" / "arrangements" / arrangement_id / "theorem_summary.json")
    smoothing = _read_json(REPO_ROOT / "data" / "processed" / f"smoothing_verification_{arrangement_id}.json")
    source = _read_json(REPO_ROOT / "release" / "hodgecy-v0.2.0" / "arrangements" / arrangement_id / "source.json")
    lines = _read_json(REPO_ROOT / "release" / "hodgecy-v0.2.0" / "arrangements" / arrangement_id / "lines.json")
    points = _read_json(REPO_ROOT / "release" / "hodgecy-v0.2.0" / "arrangements" / arrangement_id / "points.json")
    matrix = _read_json(REPO_ROOT / "release" / "hodgecy-v0.2.0" / "arrangements" / arrangement_id / "matrix.json")
    orbit_data = _read_json(REPO_ROOT / "release" / "hodgecy-v0.2.0" / "arrangements" / arrangement_id / "orbit_data.json")
    blocks = _block_records(arrangement_id)
    return {
        "schema": "hodgecy_ii_frozen_input.v1",
        "arrangement_id": arrangement_id,
        "source_release": "hodgecy-v0.2.0",
        "current_repository_version": "1.0.0",
        "provenance": {
            "theorem_summary": f"release/hodgecy-v0.2.0/arrangements/{arrangement_id}/theorem_summary.json",
            "source": f"release/hodgecy-v0.2.0/arrangements/{arrangement_id}/source.json",
            "lines": f"release/hodgecy-v0.2.0/arrangements/{arrangement_id}/lines.json",
            "points": f"release/hodgecy-v0.2.0/arrangements/{arrangement_id}/points.json",
            "matrix": f"release/hodgecy-v0.2.0/arrangements/{arrangement_id}/matrix.json",
            "orbit_data": f"release/hodgecy-v0.2.0/arrangements/{arrangement_id}/orbit_data.json",
            "smoothing_verification": f"data/processed/smoothing_verification_{arrangement_id}.json",
            "equivariant_summary": "data/processed/equivariant_spectra/fixed_equation_batch_001/spectrum_summary.csv",
        },
        "arrangement_equation": source.get("source_equation", smoothing["arrangement_equation"]),
        "ordered_plane_factors": source["ordered_factor_list"],
        "exact_incidence_table": matrix["row_generators"],
        "local_inventory": theorem["local_inventory"],
        "hodge_numbers": theorem["hodge_data"],
        "source_assembly_matrix": matrix,
        "source_matrix_shape": theorem["matrix_shape"],
        "source_rational_rank": theorem["rank_Q"],
        "source_modular_ranks": {
            "F2": theorem["rank_mod_2"],
            "F3": theorem["rank_mod_3"],
        },
        "source_smith_normal_form": theorem["smith_normal_form"],
        "automorphism_data": {
            "order": theorem["automorphism_group_order"],
            "plane_orbit_sizes": theorem["plane_orbit_sizes"],
            "double_line_orbit_sizes": theorem["double_line_orbit_sizes"],
            "multiple_point_orbit_sizes": theorem["multiple_point_orbit_sizes"],
            "orbit_data": orbit_data,
            "character_C0_distribution": theorem["character_C0_distribution"],
            "character_C1_distribution": theorem["character_C1_distribution"],
        },
        "quartic_perturbation": {
            "Q0": Q0,
            "epsilon": EPSILON,
            "recorded_status": smoothing["verification_status"],
            "release_theorem_status": theorem["quartic_perturbation"]["status"],
            "ordinary_node_verified": bool(smoothing.get("ordinary_nodes") is True and theorem.get("ordinary_node_verified") is True),
            "notes": smoothing["notes"],
        },
        "degree_112_certificate": {
            "expected_node_count": smoothing["expected_node_count"],
            "double_line_count": smoothing["double_line_count"],
            "G1_avoids_multiple_points": smoothing["G1_avoids_multiple_points"],
            "G2_squarefree_on_double_lines": smoothing["G2_squarefree_on_double_lines"],
            "G3_global_singular_locus_checked": smoothing["G3_global_singular_locus_checked"],
            "singular_locus_length": smoothing["singular_locus_length"],
            "reduced": smoothing["reduced"],
            "ordinary_nodes": smoothing["ordinary_nodes"],
        },
        "formal_node_blocks": blocks,
        "beta_block_expansion": _beta_summary(len(blocks)),
        "fidelity_ladder_seed": {
            "source_F1": "local_inventory",
            "source_F2": "source_rational_rank",
            "source_F3": "source_smith_normal_form",
            "source_F4": "automorphism_orbit_and_character_data",
            "realized_status": "SOURCE_ONLY",
        },
        "hodge_atom_status": "UNRESOLVED",
        "terminology_guard": "This manifest is source and formal-node data only; it is not a Hodge atom spectrum.",
        "source_summary_row": spectrum,
    }


def main() -> None:
    research_dir = REPO_ROOT / "research" / "hodgecy_ii"
    output_dir = REPO_ROOT / "research_outputs" / "hodgecy_ii"
    manifests_dir = research_dir / "input_manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    spectrum = _spectrum_rows()

    manifest_paths: list[str] = []
    for arrangement_id in ARRANGEMENTS:
        manifest = _manifest(arrangement_id, spectrum[arrangement_id])
        manifest_path = manifests_dir / f"{arrangement_id}.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        manifest_paths.append(str(manifest_path.relative_to(REPO_ROOT)).replace("\\", "/"))

        arrangement_out = output_dir / arrangement_id
        arrangement_out.mkdir(parents=True, exist_ok=True)
        blocks = manifest["formal_node_blocks"]
        (arrangement_out / "node_blocks.json").write_text(json.dumps({"arrangement_id": arrangement_id, "blocks": blocks}, indent=2), encoding="utf-8")
        (arrangement_out / "validation_manifest.json").write_text(
            json.dumps(
                {
                    "arrangement_id": arrangement_id,
                    "node_scheme_status": manifest["quartic_perturbation"]["recorded_status"],
                    "ordinary_node_verified": manifest["quartic_perturbation"]["ordinary_node_verified"],
                    "block_count": len(blocks),
                    "node_count_formal": 4 * len(blocks),
                    "beta_block_expansion": manifest["beta_block_expansion"],
                    "promotion_policy": "Do not promote to ordinary_node_verified until exact reducedness, support, and Hessian certificates are ingested.",
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    table_dir = output_dir / "paper_tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    (table_dir / "table_84_84a_fidelity_ladder.tsv").write_text(
        "\n".join(
            [
                "level\t84\t84a\tstatus\tseparates",
                "F0_HODGE_NUMBERS\t(0,40,80)\t(0,40,80)\tCOMPUTATIONALLY_VERIFIED\tNO",
                "F1_LOCAL_ATOMS\t(16,10,0,0,0,0,0)\t(16,10,0,0,0,0,0)\tCOMPUTATIONALLY_VERIFIED\tNO",
                "F2_RATIONAL_RELATIONS\trank_Q=26\trank_Q=26\tCOMPUTATIONALLY_VERIFIED\tNO",
                "F3_INTEGRAL_RELATIONS\tSNF=(1^23,2,6,12)\tSNF=(1^21,2,4,4,4,12)\tCOMPUTATIONALLY_VERIFIED_SOURCE_ONLY\tYES",
                "F4_EQUIVARIANT_REALIZATION\tSOURCE_AUT_ORDER=6\tSOURCE_AUT_ORDER=24\tSOURCE_ONLY\tYES",
                "F5_LMHS_EXTENSION\tUNRESOLVED\tUNRESOLVED\tTHEORY_REQUIRED\tUNRESOLVED",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "hodgecy_ii_manifest.json").write_text(
        json.dumps(
            {
                "schema": "hodgecy_ii_manifest.v1",
                "node_verified_84": False,
                "node_verified_84a": False,
                "node_count_84": None,
                "node_count_84a": None,
                "block_count_84": 28,
                "block_count_84a": 28,
                "defect_verified_84": False,
                "defect_verified_84a": False,
                "defect_84": None,
                "defect_84a": None,
                "source_to_node_map_constructed": False,
                "comparison_kernel_data": None,
                "comparison_image_data": None,
                "comparison_cokernel_data": None,
                "rational_hodge_atom_comparison": "UNRESOLVED",
                "integral_hodge_atom_comparison": "UNRESOLVED",
                "equivariant_hodge_atom_comparison": "UNRESOLVED",
                "LMHS_comparison": "UNRESOLVED",
                "fidelity_depth_84_84a": "F3_INTEGRAL_RELATIONS_SOURCE_ONLY",
                "fidelity_result_class": "PARTIALLY_RESOLVED",
                "total_arrangements_scanned": 0,
                "clean_two_stratum_count": 0,
                "local_inventory_fiber_count": 0,
                "rational_collapse_pair_count": 0,
                "integral_collapse_equivariant_pair_count": 0,
                "hodge_equivalent_pair_count": 0,
                "additional_full_fidelity_witnesses": [],
                "theorem_ready_count": 0,
                "unresolved_count": 1,
                "tests_passed": None,
                "commits_created": [],
                "remote_branch": "research/hodgecy-ii-fidelity",
                "remote_verified": False,
                "input_manifests": manifest_paths,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
