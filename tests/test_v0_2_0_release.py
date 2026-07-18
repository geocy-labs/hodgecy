"""Regression tests for the v0.2.0 theorem-certificate release."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = REPO_ROOT / "release" / "hodgecy-v0.2.0"


def _load(arrangement_id: str, name: str):
    return json.loads((RELEASE_DIR / "arrangements" / arrangement_id / name).read_text(encoding="utf-8"))


def _matrix(arrangement_id: str) -> list[list[int]]:
    with (RELEASE_DIR / "arrangements" / arrangement_id / "matrix.csv").open(newline="", encoding="utf-8") as handle:
        return [[int(value) for value in row] for row in csv.reader(handle)]


def test_release_builder_and_verifier_run() -> None:
    subprocess.run([sys.executable, "scripts/build_v0_2_0_release.py"], cwd=REPO_ROOT, check=True)
    subprocess.run([sys.executable, "scripts/verify_v0_2_0_release.py"], cwd=REPO_ROOT, check=True)


def test_theorem_values_for_release_targets() -> None:
    expected = {
        "239": {"rank_Q": 26, "rank_mod_2": 21, "kernel_dim_Q": 2, "cokernel_dim_Q": 0, "smith_tail": [2, 4, 4, 4, 12], "group": 24, "orbits": ([4, 4], [4, 6, 6, 12], [4, 4, 6, 12])},
        "240": {"rank_Q": 26, "rank_mod_2": 23, "kernel_dim_Q": 2, "cokernel_dim_Q": 0, "smith_tail": [2, 6, 12], "group": 6, "orbits": ([1, 1, 3, 3], [1, 3, 3, 3, 3, 3, 3, 3, 6], [1, 1, 3, 3, 3, 3, 3, 3, 6])},
        "241": {"rank_Q": 24, "rank_mod_2": 24, "rank_mod_3": 19, "kernel_dim_Q": 4, "cokernel_dim_Q": 2, "smith_tail": [3, 3, 3, 3, 3], "group": 32, "orbits": ([8], [4, 8, 16], [2, 8, 16])},
        "84": {"rank_Q": 26, "rank_mod_2": 23, "smith_tail": [2, 6, 12], "group": 6, "orbits": ([1, 1, 3, 3], [1, 3, 3, 3, 3, 3, 3, 3, 6], [1, 1, 3, 3, 3, 3, 3, 3, 6])},
        "84a": {"rank_Q": 26, "rank_mod_2": 21, "smith_tail": [2, 4, 4, 4, 12], "group": 24, "orbits": ([4, 4], [4, 6, 6, 12], [4, 4, 6, 12])},
    }
    for arrangement_id, values in expected.items():
        summary = _load(arrangement_id, "theorem_summary.json")
        assert summary["local_inventory"] == [16, 10, 0, 0, 0, 0, 0]
        assert summary["matrix_shape"] == [26, 28]
        assert summary["rank_Q"] == values["rank_Q"]
        assert summary["rank_mod_2"] == values["rank_mod_2"]
        if "rank_mod_3" in values:
            assert summary["rank_mod_3"] == values["rank_mod_3"]
        if "kernel_dim_Q" in values:
            assert summary["kernel_dim_Q"] == values["kernel_dim_Q"]
        if "cokernel_dim_Q" in values:
            assert summary["cokernel_dim_Q"] == values["cokernel_dim_Q"]
        assert summary["smith_normal_form"][-len(values["smith_tail"]):] == values["smith_tail"]
        assert summary["automorphism_group_order"] == values["group"]
        assert summary["plane_orbit_sizes"] == values["orbits"][0]
        assert summary["double_line_orbit_sizes"] == values["orbits"][1]
        assert summary["multiple_point_orbit_sizes"] == values["orbits"][2]


def test_supports_reconstruct_matrices_exactly() -> None:
    for arrangement_id in ("84", "84a", "239", "240", "241"):
        matrix = _matrix(arrangement_id)
        supports = _load(arrangement_id, "column_supports.json")["column_supports"]
        reconstructed = [[0 for _ in range(28)] for _ in range(26)]
        for support in supports:
            col = int(support["column_index"])
            for row in support["support_row_indices"]:
                reconstructed[int(row)][col] = 1
        assert reconstructed == matrix


def test_84_84a_statuses_not_promoted() -> None:
    for arrangement_id in ("84", "84a"):
        perturbation = _load(arrangement_id, "theorem_summary.json")["quartic_perturbation"]
        assert perturbation["status"] == "degree112_certified"
        assert perturbation["saturated_jacobian_scheme_dimension"] == 0
        assert perturbation["saturated_jacobian_scheme_degree"] == 112
        assert perturbation["ordinary_node_verified"] is False
        assert perturbation["defect_verified"] is False
