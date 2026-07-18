"""Verify the HodgeCY v0.2.0 theorem-certificate release directory."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = REPO_ROOT / "release" / "hodgecy-v0.2.0"
TARGETS = ("84", "84a", "239", "240", "241")


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _matrix(path: Path) -> list[list[int]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [[int(value) for value in row] for row in csv.reader(handle)]


def _snf_rank_mod(snf: list[int], p: int) -> int:
    return sum(1 for value in snf if int(value) % p != 0)


def _reconstruct_from_supports(rows: int, cols: int, supports: list[dict[str, Any]]) -> list[list[int]]:
    matrix = [[0 for _ in range(cols)] for _ in range(rows)]
    for support in supports:
        col = int(support["column_index"])
        for row in support["support_row_indices"]:
            matrix[int(row)][col] = 1
    return matrix


def _verify_checksums() -> None:
    for line in (RELEASE_DIR / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, rel = line.split("  ", 1)
        actual = hashlib.sha256((RELEASE_DIR / rel).read_bytes()).hexdigest()
        if actual != expected:
            raise AssertionError(f"Checksum mismatch for {rel}")


def _verify_arrangement(arrangement_id: str) -> None:
    arr = RELEASE_DIR / "arrangements" / arrangement_id
    for name in (
        "source.json",
        "incidence_labeled.json",
        "incidence_minimal.json",
        "lines.json",
        "points.json",
        "matrix.csv",
        "matrix.json",
        "column_supports.json",
        "coefficient_invariants.json",
        "group_action.json",
        "orbit_data.json",
        "character_data.json",
        "theorem_summary.json",
    ):
        if not (arr / name).exists():
            raise AssertionError(f"Missing {arrangement_id}/{name}")

    matrix_payload = _load(arr / "matrix.json")
    matrix_csv = _matrix(arr / "matrix.csv")
    supports = _load(arr / "column_supports.json")["column_supports"]
    invariants = _load(arr / "coefficient_invariants.json")
    group = _load(arr / "group_action.json")
    orbit = _load(arr / "orbit_data.json")
    characters = _load(arr / "character_data.json")
    summary = _load(arr / "theorem_summary.json")

    if matrix_payload["shape"] != [26, 28]:
        raise AssertionError(f"{arrangement_id} matrix is not 26 x 28")
    if matrix_payload["matrix"] != matrix_csv:
        raise AssertionError(f"{arrangement_id} matrix.json and matrix.csv disagree")
    if _reconstruct_from_supports(26, 28, supports) != matrix_csv:
        raise AssertionError(f"{arrangement_id} support representation does not reconstruct matrix")

    snf = invariants["smith_normal_form"]
    if invariants["rank_Q"] != len([value for value in snf if int(value) != 0]):
        raise AssertionError(f"{arrangement_id} rational rank disagrees with Smith form")
    for prime in (2, 3):
        actual = int(invariants["tested_finite_field_ranks"][str(prime)])
        expected = _snf_rank_mod(snf, prime)
        if actual != expected:
            raise AssertionError(f"{arrangement_id} rank mod {prime} disagrees with Smith factors")

    if sum(orbit["plane_orbit_sizes"]) != 8:
        raise AssertionError(f"{arrangement_id} plane orbit sizes do not sum to 8")
    if sum(orbit["double_line_orbit_sizes"]) != 28:
        raise AssertionError(f"{arrangement_id} line orbit sizes do not sum to 28")
    if sum(orbit["multiple_point_orbit_sizes"]) != 26:
        raise AssertionError(f"{arrangement_id} point orbit sizes do not sum to 26")

    group_order = int(group["group_order"])
    for distribution_name in ("character_C1_distribution", "character_C0_distribution"):
        if sum(int(value) for value in characters[distribution_name].values()) != group_order:
            raise AssertionError(f"{arrangement_id} {distribution_name} does not sum to group order")
    if not all(item["commutes_with_differential"] for item in group["commutation_checks"]):
        raise AssertionError(f"{arrangement_id} has non-commuting group action")
    if arrangement_id in {"84", "84a"}:
        perturbation = summary["quartic_perturbation"]
        if perturbation["status"] != "degree112_certified":
            raise AssertionError(f"{arrangement_id} status was promoted or changed")
        if perturbation["ordinary_node_verified"] or perturbation["defect_verified"]:
            raise AssertionError(f"{arrangement_id} has forbidden promoted status")
        if perturbation["saturated_jacobian_scheme_dimension"] != 0 or perturbation["saturated_jacobian_scheme_degree"] != 112:
            raise AssertionError(f"{arrangement_id} degree-112 certificate data missing")


def main() -> None:
    if not RELEASE_DIR.exists():
        raise SystemExit("Release directory missing. Run scripts/build_v0_2_0_release.py first.")
    _verify_checksums()
    for arrangement_id in TARGETS:
        _verify_arrangement(arrangement_id)
    for rel in (
        "comparisons/comparison_84_84a.json",
        "comparisons/comparison_239_240_241.json",
        "MANIFEST.json",
        "SHA256SUMS",
    ):
        if not (RELEASE_DIR / rel).exists():
            raise AssertionError(f"Missing {rel}")
    print("HodgeCY v0.2.0 release verification passed.")


if __name__ == "__main__":
    main()
