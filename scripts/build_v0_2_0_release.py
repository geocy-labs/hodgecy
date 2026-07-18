"""Build the HodgeCY v0.2.0 theorem-certificate release directory.

The release bundle is generated from repository source records and the existing
equivariant/smoothing verification code paths. It intentionally does not
promote 84/84a beyond degree112_certified.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import tomllib
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sympy as sp

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from hodgecy.equivariant import (  # noqa: E402
    build_gluing_matrix,
    incidence_table_from_linear_forms,
    invariant_permutations,
    minimal_incidence_table,
    parse_linear_forms_from_record,
    rank_mod_p,
    rank_over_Q,
    singular_strata_from_incidence_table,
    smith_normal_form_invariants,
    spectrum_to_dict,
)
from hodgecy.equivariant.spectrum import build_equivariant_spectrum  # noqa: E402

from validate_ckc_fixed_rational_batch import (  # noqa: E402
    _build_validated_spectrum,
    _load_hodge_data,
    _load_index,
    _record_from_extracted,
)

TARGETS = ("84", "84a", "239", "240", "241")
RELEASE_VERSION = "v0.2.0"
PACKAGE_VERSION = "0.2.0"
RELEASE_NAME = f"hodgecy-{RELEASE_VERSION}"
RELEASE_DIR = REPO_ROOT / "release" / RELEASE_NAME
ARCHIVE_PATH = REPO_ROOT / "release" / f"{RELEASE_NAME}-theorem-certificates.zip"
SOURCE_ARCHIVE_PATH = REPO_ROOT / "release" / f"{RELEASE_NAME}-source.zip"
TAG_TARGET_NOTE = "Resolve the tagged release commit with: git rev-parse v0.2.0^{}"

EXPECTED: dict[str, dict[str, Any]] = {
    "239": {
        "inventory": (16, 10, 0, 0, 0, 0, 0),
        "shape": (26, 28),
        "rank_Q": 26,
        "rank_mod": {2: 21},
        "kernel_dim_Q": 2,
        "cokernel_dim_Q": 0,
        "smith": [1] * 21 + [2, 4, 4, 4, 12],
        "group_order": 24,
        "plane_orbits": (4, 4),
        "line_orbits": (4, 6, 6, 12),
        "point_orbits": (4, 4, 6, 12),
    },
    "240": {
        "inventory": (16, 10, 0, 0, 0, 0, 0),
        "shape": (26, 28),
        "rank_Q": 26,
        "rank_mod": {2: 23},
        "kernel_dim_Q": 2,
        "cokernel_dim_Q": 0,
        "smith": [1] * 23 + [2, 6, 12],
        "group_order": 6,
        "plane_orbits": (1, 1, 3, 3),
        "line_orbits": (1, 3, 3, 3, 3, 3, 3, 3, 6),
        "point_orbits": (1, 1, 3, 3, 3, 3, 3, 3, 6),
    },
    "241": {
        "inventory": (16, 10, 0, 0, 0, 0, 0),
        "shape": (26, 28),
        "rank_Q": 24,
        "rank_mod": {2: 24, 3: 19},
        "kernel_dim_Q": 4,
        "cokernel_dim_Q": 2,
        "smith": [1] * 19 + [3, 3, 3, 3, 3],
        "group_order": 32,
        "plane_orbits": (8,),
        "line_orbits": (4, 8, 16),
        "point_orbits": (2, 8, 16),
    },
    "84": {
        "inventory": (16, 10, 0, 0, 0, 0, 0),
        "hodge": (0, 40, 80),
        "shape": (26, 28),
        "rank_Q": 26,
        "rank_mod": {2: 23},
        "smith": [1] * 23 + [2, 6, 12],
        "group_order": 6,
        "plane_orbits": (1, 1, 3, 3),
        "line_orbits": (1, 3, 3, 3, 3, 3, 3, 3, 6),
        "point_orbits": (1, 1, 3, 3, 3, 3, 3, 3, 6),
        "perturbation_status": "degree112_certified",
        "saturated_jacobian_scheme_dimension": 0,
        "saturated_jacobian_scheme_degree": 112,
    },
    "84a": {
        "inventory": (16, 10, 0, 0, 0, 0, 0),
        "hodge": (0, 40, 80),
        "shape": (26, 28),
        "rank_Q": 26,
        "rank_mod": {2: 21},
        "smith": [1] * 21 + [2, 4, 4, 4, 12],
        "group_order": 24,
        "plane_orbits": (4, 4),
        "line_orbits": (4, 6, 6, 12),
        "point_orbits": (4, 4, 6, 12),
        "perturbation_status": "degree112_certified",
        "saturated_jacobian_scheme_dimension": 0,
        "saturated_jacobian_scheme_degree": 112,
    },
}


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, sp.Integer):
        return int(value)
    if isinstance(value, sp.Rational):
        return str(value)
    raise TypeError(f"Object is not JSON serializable: {value!r}")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _run(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, check=check)


def _git_output(args: list[str]) -> str:
    completed = _run(["git", *args], check=False)
    return (completed.stdout or completed.stderr).strip()


def _load_version() -> str:
    payload = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = payload["project"]["version"]
    if version != PACKAGE_VERSION:
        raise RuntimeError(f"pyproject version {version!r} does not match {PACKAGE_VERSION!r}.")
    return version


def _control_records() -> dict[str, dict[str, Any]]:
    payload = json.loads((REPO_ROOT / "data/raw/cynk_kocel_cynk_2026/control_triple_83_84_84a.json").read_text(encoding="utf-8"))
    return {str(record["arrangement_id"]): record for record in payload["records"]}


def _build_target_spectrum(arrangement_id: str) -> dict[str, Any]:
    if arrangement_id in {"84", "84a"}:
        spectrum = spectrum_to_dict(build_equivariant_spectrum(_control_records()[arrangement_id]))
        spectrum["perturbation_status_if_available"] = "degree112_certified"
        return spectrum
    records = {str(record["arrangement_id"]): record for record in _load_index()["records"]}
    parsed = _record_from_extracted(records[arrangement_id])
    return _build_validated_spectrum(parsed, _load_hodge_data())


def _record_for_strata(spectrum: dict[str, Any]) -> dict[str, Any]:
    return {"linear_forms": spectrum["linear_forms"]}


def _strata_and_matrix(spectrum: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], sp.Matrix]:
    linear_forms = parse_linear_forms_from_record(_record_for_strata(spectrum))
    incidence = incidence_table_from_linear_forms(linear_forms)
    strata = singular_strata_from_incidence_table(incidence, linear_forms)
    matrix = build_gluing_matrix(strata["double_lines"], strata["multiple_points"])
    return strata["double_lines"], strata["multiple_points"], matrix


def _inventory_tuple(spectrum: dict[str, Any]) -> tuple[int, int, int, int, int, int, int]:
    inventory = spectrum["computed_inventory"]
    return tuple(int(inventory[key]) for key in ("p3", "p4_0", "p4_1", "p5_0", "p5_1", "p5_2", "l3"))


def _orbit_sizes(orbits: list[Any]) -> tuple[int, ...]:
    return tuple(sorted(len(orbit) for orbit in orbits))


def _character_distribution(character: dict[str, Any]) -> dict[str, int]:
    return {str(key): int(value) for key, value in character.get("value_distribution", {}).items()}


def _canonical_abelian_group(snf: list[int], rows: int, rank: int) -> dict[str, Any]:
    free_rank = rows - rank
    torsion = [int(value) for value in snf if int(value) > 1]
    pieces = []
    if free_rank == 1:
        pieces.append("Z")
    elif free_rank > 1:
        pieces.append(f"Z^{free_rank}")
    counts = Counter(torsion)
    for value in sorted(counts):
        count = counts[value]
        if count == 1:
            pieces.append(f"Z/{value}Z")
        else:
            pieces.append(f"(Z/{value}Z)^{count}")
    return {"free_rank": free_rank, "torsion_factors": torsion, "canonical": " + ".join(pieces) if pieces else "0"}


def _line_action(line: tuple[int, ...], permutation: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(sorted(permutation[index] for index in line))


def _point_action(point: tuple[int, ...], permutation: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(sorted(permutation[index] for index in point))


def _induced_permutation(items: list[tuple[int, ...]], permutation: tuple[int, ...], action) -> list[int]:
    index = {item: idx for idx, item in enumerate(items)}
    return [index[action(item, permutation)] for item in items]


def _commutes(matrix: list[list[int]], row_perm: list[int], col_perm: list[int]) -> bool:
    for row, values in enumerate(matrix):
        for col, value in enumerate(values):
            if int(value) != int(matrix[row_perm[row]][col_perm[col]]):
                return False
    return True


def _write_arrangement_release(arrangement_id: str, spectrum: dict[str, Any]) -> dict[str, Any]:
    expected = EXPECTED[arrangement_id]
    arr_dir = RELEASE_DIR / "arrangements" / arrangement_id
    arr_dir.mkdir(parents=True, exist_ok=True)

    linear_forms = parse_linear_forms_from_record(_record_for_strata(spectrum))
    incidence = incidence_table_from_linear_forms(linear_forms)
    minimal = minimal_incidence_table(incidence)
    double_lines, multiple_points, matrix = _strata_and_matrix(spectrum)
    matrix_rows = [[int(matrix[row, col]) for col in range(matrix.cols)] for row in range(matrix.rows)]
    line_items = [tuple(line["planes"]) for line in double_lines]
    point_items = [tuple(point["planes"]) for point in multiple_points]
    permutations = [tuple(perm) for perm in spectrum["invariant_permutations"]]
    line_perms = [_induced_permutation(line_items, perm, _line_action) for perm in permutations]
    point_perms = [_induced_permutation(point_items, perm, _point_action) for perm in permutations]
    commutation = [
        {
            "plane_permutation": list(perm),
            "line_permutation": line_perms[index],
            "point_permutation": point_perms[index],
            "commutes_with_differential": _commutes(matrix_rows, point_perms[index], line_perms[index]),
        }
        for index, perm in enumerate(permutations)
    ]
    if not all(item["commutes_with_differential"] for item in commutation):
        raise RuntimeError(f"Group action does not commute with d_A for arrangement {arrangement_id}.")

    rank_q = rank_over_Q(matrix)
    rank_mod = {str(prime): rank_mod_p(matrix, prime) for prime in (2, 3)}
    snf = smith_normal_form_invariants(matrix) or []
    invariants = {
        "rank_Q": rank_q,
        "tested_finite_field_ranks": rank_mod,
        "kernel_dim_Q": int(matrix.cols - rank_q),
        "cokernel_dim_Q": int(matrix.rows - rank_q),
        "smith_normal_form": snf,
        "integral_kernel_rank": int(matrix.cols - rank_q),
        "integral_cokernel_decomposition": _canonical_abelian_group(snf, int(matrix.rows), rank_q),
    }

    column_supports = [
        {
            "column_index": col,
            "line_id": double_lines[col]["line_id"],
            "planes": double_lines[col]["planes"],
            "support_row_indices": [row for row in range(matrix.rows) if matrix_rows[row][col] == 1],
            "support_point_ids": [multiple_points[row]["point_id"] for row in range(matrix.rows) if matrix_rows[row][col] == 1],
        }
        for col in range(matrix.cols)
    ]

    source = {
        "arrangement_id": arrangement_id,
        "source": spectrum.get("source"),
        "source_reference": spectrum.get("source_reference"),
        "source_equation": spectrum.get("source_equation"),
        "ordered_factor_list": spectrum["linear_forms"],
        "validation_status": spectrum.get("validation_status", spectrum.get("representative_status")),
        "representative_status": spectrum.get("representative_status"),
        "hodge_data_if_known": spectrum.get("hodge_data_if_available") or spectrum.get("hodge_data_if_known"),
    }
    if arrangement_id in {"84", "84a"}:
        degree_outputs = json.loads((REPO_ROOT / "data/processed/cas_certificates/reviewer_v4_degree_outputs.json").read_text(encoding="utf-8"))
        cone_dim = int(degree_outputs[arrangement_id]["dimension"])
        source["quartic_perturbation"] = {
            "status": "degree112_certified",
            "quartic_Q": "x^4 + 2*y^4 + 3*z^4 + 5*t^4 + x*y*z*t",
            "epsilon": "1",
            "saturated_jacobian_cone_dimension": cone_dim,
            "saturated_jacobian_scheme_dimension": cone_dim - 1,
            "saturated_jacobian_scheme_degree": int(degree_outputs[arrangement_id]["degree"]),
            "ordinary_node_verified": False,
            "defect_verified": False,
        }

    labeled_incidence = {
        "arrangement_id": arrangement_id,
        "plane_labels": [form["label"] for form in spectrum["linear_forms"]],
        "incidence_table_zero_based": [list(item) for item in incidence],
        "incidence_table_labeled": [[spectrum["linear_forms"][index]["label"] for index in item] for item in incidence],
    }
    matrix_payload = {
        "arrangement_id": arrangement_id,
        "shape": [int(matrix.rows), int(matrix.cols)],
        "row_generators": multiple_points,
        "column_generators": double_lines,
        "matrix": matrix_rows,
    }
    group_action = {
        "arrangement_id": arrangement_id,
        "group_order": len(permutations),
        "plane_permutations": [list(perm) for perm in permutations],
        "induced_line_permutations": line_perms,
        "induced_point_permutations": point_perms,
        "commutation_checks": commutation,
    }
    orbit_data = {
        "plane_orbits": spectrum["plane_orbits"],
        "double_line_orbits": spectrum["double_line_orbits"],
        "multiple_point_orbits": spectrum["multiple_point_orbits"],
        "plane_orbit_sizes": list(_orbit_sizes(spectrum["plane_orbits"])),
        "double_line_orbit_sizes": list(_orbit_sizes(spectrum["double_line_orbits"])),
        "multiple_point_orbit_sizes": list(_orbit_sizes(spectrum["multiple_point_orbits"])),
    }
    character_data = {
        "character_C1": spectrum["character_C1"],
        "character_C0": spectrum["character_C0"],
        "character_C1_distribution": _character_distribution(spectrum["character_C1"]),
        "character_C0_distribution": _character_distribution(spectrum["character_C0"]),
    }

    theorem_summary = {
        "release_version": RELEASE_VERSION,
        "arrangement_id": arrangement_id,
        "local_inventory": _inventory_tuple(spectrum),
        "hodge_data": source.get("hodge_data_if_known"),
        "matrix_shape": [int(matrix.rows), int(matrix.cols)],
        "rank_Q": invariants["rank_Q"],
        "rank_mod_2": invariants["tested_finite_field_ranks"]["2"],
        "rank_mod_3": invariants["tested_finite_field_ranks"]["3"],
        "kernel_dim_Q": invariants["kernel_dim_Q"],
        "cokernel_dim_Q": invariants["cokernel_dim_Q"],
        "smith_normal_form": snf,
        "integral_kernel_rank": invariants["integral_kernel_rank"],
        "integral_cokernel_decomposition": invariants["integral_cokernel_decomposition"],
        "automorphism_group_order": len(permutations),
        "plane_orbit_sizes": orbit_data["plane_orbit_sizes"],
        "double_line_orbit_sizes": orbit_data["double_line_orbit_sizes"],
        "multiple_point_orbit_sizes": orbit_data["multiple_point_orbit_sizes"],
        "character_C1_distribution": character_data["character_C1_distribution"],
        "character_C0_distribution": character_data["character_C0_distribution"],
        "quartic_perturbation": source.get("quartic_perturbation"),
        "ordinary_node_verified": False,
        "defect_verified": False,
    }

    _assert_expected(arrangement_id, theorem_summary)

    _write_json(arr_dir / "source.json", source)
    _write_json(arr_dir / "incidence_labeled.json", labeled_incidence)
    _write_json(arr_dir / "incidence_minimal.json", {"arrangement_id": arrangement_id, "minimal_incidence_table": [list(item) for item in minimal]})
    _write_json(arr_dir / "lines.json", {"arrangement_id": arrangement_id, "double_lines": double_lines})
    _write_json(arr_dir / "points.json", {"arrangement_id": arrangement_id, "multiple_points": multiple_points})
    _write_json(arr_dir / "matrix.json", matrix_payload)
    _write_json(arr_dir / "column_supports.json", {"arrangement_id": arrangement_id, "column_supports": column_supports})
    _write_json(arr_dir / "coefficient_invariants.json", invariants)
    _write_json(arr_dir / "group_action.json", group_action)
    _write_json(arr_dir / "orbit_data.json", orbit_data)
    _write_json(arr_dir / "character_data.json", character_data)
    _write_json(arr_dir / "theorem_summary.json", theorem_summary)
    with (arr_dir / "matrix.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerows(matrix_rows)
    return theorem_summary


def _assert_expected(arrangement_id: str, summary: dict[str, Any]) -> None:
    expected = EXPECTED[arrangement_id]
    checks = {
        "local_inventory": tuple(summary["local_inventory"]),
        "matrix_shape": tuple(summary["matrix_shape"]),
        "rank_Q": summary["rank_Q"],
        "kernel_dim_Q": summary["kernel_dim_Q"],
        "cokernel_dim_Q": summary["cokernel_dim_Q"],
        "smith_normal_form": summary["smith_normal_form"],
        "automorphism_group_order": summary["automorphism_group_order"],
        "plane_orbit_sizes": tuple(summary["plane_orbit_sizes"]),
        "double_line_orbit_sizes": tuple(summary["double_line_orbit_sizes"]),
        "multiple_point_orbit_sizes": tuple(summary["multiple_point_orbit_sizes"]),
    }
    expected_map = {
        "local_inventory": expected["inventory"],
        "matrix_shape": expected["shape"],
        "rank_Q": expected["rank_Q"],
        "kernel_dim_Q": expected.get("kernel_dim_Q", summary["kernel_dim_Q"]),
        "cokernel_dim_Q": expected.get("cokernel_dim_Q", summary["cokernel_dim_Q"]),
        "smith_normal_form": expected["smith"],
        "automorphism_group_order": expected["group_order"],
        "plane_orbit_sizes": expected["plane_orbits"],
        "double_line_orbit_sizes": expected["line_orbits"],
        "multiple_point_orbit_sizes": expected["point_orbits"],
    }
    for key, actual in checks.items():
        if actual != expected_map[key]:
            raise RuntimeError(f"{arrangement_id} {key} mismatch: {actual!r} != {expected_map[key]!r}")
    for prime, rank in expected.get("rank_mod", {}).items():
        if summary[f"rank_mod_{prime}"] != rank:
            raise RuntimeError(f"{arrangement_id} rank_mod_{prime} mismatch: {summary[f'rank_mod_{prime}']} != {rank}")
    if "hodge" in expected:
        hodge = summary["hodge_data"] or {}
        actual_hodge = (int(hodge["h12"]), int(hodge["h11"]), int(hodge["euler"]))
        if actual_hodge != expected["hodge"]:
            raise RuntimeError(f"{arrangement_id} hodge mismatch: {actual_hodge!r} != {expected['hodge']!r}")
    if "perturbation_status" in expected:
        perturbation = summary["quartic_perturbation"] or {}
        if perturbation.get("status") != expected["perturbation_status"]:
            raise RuntimeError(f"{arrangement_id} perturbation status mismatch")
        if perturbation.get("saturated_jacobian_scheme_dimension") != expected["saturated_jacobian_scheme_dimension"]:
            raise RuntimeError(f"{arrangement_id} saturated Jacobian scheme dimension mismatch")
        if perturbation.get("saturated_jacobian_scheme_degree") != expected["saturated_jacobian_scheme_degree"]:
            raise RuntimeError(f"{arrangement_id} saturated Jacobian scheme degree mismatch")


def _write_comparisons(summaries: dict[str, dict[str, Any]]) -> None:
    comp_dir = RELEASE_DIR / "comparisons"
    comp_dir.mkdir(parents=True, exist_ok=True)
    comparison_84 = {
        "release_version": RELEASE_VERSION,
        "arrangements": ["84", "84a"],
        "same_local_inventory": summaries["84"]["local_inventory"] == summaries["84a"]["local_inventory"],
        "same_hodge_data": summaries["84"]["hodge_data"] == summaries["84a"]["hodge_data"],
        "different_equivariant_source_assembly": summaries["84"]["smith_normal_form"] != summaries["84a"]["smith_normal_form"],
        "differentiating_fields": _diff_fields(summaries["84"], summaries["84a"]),
    }
    comparison_239 = {
        "release_version": RELEASE_VERSION,
        "arrangements": ["239", "240", "241"],
        "same_local_inventory": len({tuple(summaries[item]["local_inventory"]) for item in ("239", "240", "241")}) == 1,
        "pairwise_equivariant_signatures_all_equal": False,
        "differentiating_fields": {
            "239_vs_240": _diff_fields(summaries["239"], summaries["240"]),
            "239_vs_241": _diff_fields(summaries["239"], summaries["241"]),
            "240_vs_241": _diff_fields(summaries["240"], summaries["241"]),
        },
    }
    _write_json(comp_dir / "comparison_84_84a.json", comparison_84)
    _write_json(comp_dir / "comparison_239_240_241.json", comparison_239)


def _diff_fields(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    fields = [
        "rank_Q",
        "rank_mod_2",
        "rank_mod_3",
        "kernel_dim_Q",
        "cokernel_dim_Q",
        "smith_normal_form",
        "integral_cokernel_decomposition",
        "automorphism_group_order",
        "plane_orbit_sizes",
        "double_line_orbit_sizes",
        "multiple_point_orbit_sizes",
        "character_C1_distribution",
        "character_C0_distribution",
    ]
    return [field for field in fields if left.get(field) != right.get(field)]


def _copy_manuscript_assets() -> None:
    out = RELEASE_DIR / "manuscript_assets"
    out.mkdir(parents=True, exist_ok=True)
    for rel in (
        "paper/tables/table_ckc_239_240_241_equivariant_signature.csv",
        "paper/tables/table_ckc_239_240_241_equivariant_signature.tex",
        "paper/tables/table_smoothing_bridge_profiles.csv",
        "paper/tables/table_smoothing_bridge_profiles.tex",
        "paper/figures/fig_smoothing_bridge_schematic.pdf",
        "paper/figures/fig_smoothing_bridge_schematic.png",
    ):
        src = REPO_ROOT / rel
        if src.exists():
            dest = out / rel.replace("/", "__")
            shutil.copy2(src, dest)


def _copy_release_scripts() -> None:
    out = RELEASE_DIR / "scripts"
    out.mkdir(parents=True, exist_ok=True)
    for rel in (
        "scripts/reproduce_release.sh",
        "scripts/verify_release.sh",
        "scripts/build_v0_2_0_release.py",
        "scripts/verify_v0_2_0_release.py",
        "scripts/validate_ckc_fixed_rational_batch.py",
        "scripts/build_ckc_239_240_241_theorem_values.py",
        "scripts/generate_paper_assets.py",
        "scripts/verify_smoothing_bridge_84_84a.py",
    ):
        src = REPO_ROOT / rel
        if src.exists():
            shutil.copy2(src, out / Path(rel).name)


def _write_environment() -> None:
    env = RELEASE_DIR / "environment"
    env.mkdir(parents=True, exist_ok=True)
    (env / "python-version.txt").write_text(sys.version + "\n", encoding="utf-8")
    (env / "platform.txt").write_text(platform.platform() + "\n" + platform.machine() + "\n", encoding="utf-8")
    dependency_names = ["hodgecy", "pandas", "sympy", "pytest", "networkx", "matplotlib", "setuptools", "pip"]
    dependency_lines = []
    for name in dependency_names:
        if name == "hodgecy":
            dependency_lines.append(f"hodgecy=={PACKAGE_VERSION} (pyproject.toml)")
            continue
        try:
            dependency_lines.append(f"{name}=={importlib.metadata.version(name)}")
        except importlib.metadata.PackageNotFoundError:
            dependency_lines.append(f"{name} not installed")
    (env / "dependencies.txt").write_text("\n".join(dependency_lines) + "\n", encoding="utf-8")
    shutil.copy2(env / "dependencies.txt", env / "requirements-lock.txt")
    (env / "git-status.txt").write_text(
        "Release certificates are generated before the final release commit is tagged.\n"
        "Run git status --short after checkout to inspect the live tree.\n",
        encoding="utf-8",
    )
    (env / "git-commit.txt").write_text(
        f"release_tag: {RELEASE_VERSION}\n"
        f"generation_source_commit: {_git_output(['rev-parse', 'HEAD'])}\n"
        f"tag_target_commit: {TAG_TARGET_NOTE}\n",
        encoding="utf-8",
    )
    (env / "git-describe.txt").write_text(
        f"release_tag: {RELEASE_VERSION}\n"
        f"generation_source_describe: {_git_output(['describe', '--tags', '--always', '--dirty'])}\n"
        f"tag_target_describe: resolve from the checked-out release tag\n",
        encoding="utf-8",
    )
    captured_summary = REPO_ROOT / "data" / "processed" / "release_test_summary_v0_2_0.txt"
    if captured_summary.exists():
        (env / "test-summary.txt").write_text(captured_summary.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        (env / "test-summary.txt").write_text(
            "Run python -m pytest -q and scripts/verify_release.sh before tagging. "
            "No final test-summary capture file was present when this release bundle was built.\n",
            encoding="utf-8",
        )


def _write_release_docs() -> None:
    commit = _git_output(["rev-parse", "HEAD"])
    date = datetime.now(timezone.utc).date().isoformat()
    root_release_notes = f"""# HodgeCY {RELEASE_VERSION}

Release date: {date}

Generation source commit recorded during preparation: `{commit}`

Tagged release commit: resolve with `git rev-parse {RELEASE_VERSION}^{{}}` after
checking out the published tag.

## Scientific scope

This theorem-bearing release supports the HodgeCY I source-assembly certificate layer for arrangements 84, 84a, 239, 240, and 241.

## Principal outputs

- Exact incidence and source-assembly matrix certificates for each arrangement.
- Rational and finite-field ranks, Smith normal forms, and integral cokernel decompositions.
- Incidence-preserving automorphism actions, orbit data, and permutation-character distributions.
- Comparison certificates for 84/84a and 239/240/241.

## Status of 84 and 84a

Arrangements 84 and 84a remain `degree112_certified`. Exact G1/G2 genericity and characteristic-zero degree-112 saturated Jacobian certificates are repo-backed. This release does not claim `ordinary_node_verified` or `defect_verified`; reducedness, Hessian-rank, defect, and mixed-Hodge-theoretic realization remain pending.
"""
    root_repro = f"""# HodgeCY {RELEASE_VERSION} Reproducibility

## Commands

```bash
python scripts/validate_ckc_fixed_rational_batch.py
python scripts/build_ckc_239_240_241_theorem_values.py
python scripts/build_v0_2_0_release.py
python scripts/verify_v0_2_0_release.py
python -m pytest -q
```

The shell wrapper `scripts/reproduce_release.sh` runs the same release path.

## Matrix support format

Each `column_supports.json` lists the row indices and point labels where a given double-line column has entry 1. The verifier reconstructs the full 26 x 28 integral matrix from these supports and compares it entrywise with `matrix.json` and `matrix.csv`.

## Validation statuses

The 84/84a smoothing status is `degree112_certified`; ordinary-node and defect verification are intentionally not promoted in this release.
"""
    (REPO_ROOT / "RELEASE_NOTES.md").write_text(root_release_notes, encoding="utf-8")
    (REPO_ROOT / "REPRODUCIBILITY.md").write_text(root_repro, encoding="utf-8")
    (RELEASE_DIR / "RELEASE_NOTES.md").write_text(root_release_notes, encoding="utf-8")
    (RELEASE_DIR / "REPRODUCIBILITY.md").write_text(root_repro, encoding="utf-8")
    (RELEASE_DIR / "README.md").write_text(
        f"# HodgeCY {RELEASE_VERSION} theorem certificates\n\n"
        "This directory is generated by `python scripts/build_v0_2_0_release.py`.\n"
        "It contains theorem-bearing source assembly certificates for arrangements "
        "84, 84a, 239, 240, and 241.\n",
        encoding="utf-8",
    )


def _write_citation_and_zenodo() -> None:
    version = _load_version()
    date = datetime.now(timezone.utc).date().isoformat()
    commit = _git_output(["rev-parse", "HEAD"])
    citation = f"""cff-version: 1.2.0
title: "HodgeCY: Computational Hodge Atom Profiles and Source Assembly Spectra for Double-Octic Calabi--Yau Threefolds"
message: "If you use this software, please cite the HodgeCY software release."
type: software
authors:
  - family-names: Rahman
    given-names: Abdul
version: "{version}"
date-released: "{date}"
repository-code: "https://github.com/geocy-labs/hodgecy"
license: MIT
abstract: "Computational certificates for Hodge atom profiles and source assembly spectra of double-octic Calabi--Yau threefold arrangements."
preferred-citation:
  type: software
  title: "HodgeCY: Computational Hodge Atom Profiles and Source Assembly Spectra for Double-Octic Calabi--Yau Threefolds"
  authors:
    - family-names: Rahman
      given-names: Abdul
  version: "{version}"
  year: 2026
  doi: "10.5281/zenodo.21429481"
  notes: "HodgeCY v0.2.0 Zenodo DOI: 10.5281/zenodo.21429481. Generation source commit {commit}; tagged release commit is resolved from {RELEASE_VERSION}."
"""
    (REPO_ROOT / "CITATION.cff").write_text(citation, encoding="utf-8")
    zenodo = {
        "title": "HodgeCY: Computational Hodge Atom Profiles and Source Assembly Spectra for Double-Octic Calabi--Yau Threefolds",
        "version": RELEASE_VERSION,
        "creators": [{"name": "Rahman, Abdul", "affiliation": "GeoCY Labs"}],
        "description": "Theorem-bearing source assembly certificates for selected double-octic arrangements in the HodgeCY I manuscript.",
        "publication_date": date,
        "license": "MIT",
        "upload_type": "software",
        "access_right": "open",
        "keywords": [
            "Calabi--Yau threefolds",
            "double octics",
            "Hodge atom profiles",
            "source assembly complexes",
            "Smith normal form",
            "hyperplane arrangements",
            "automorphism groups",
            "computational algebraic geometry",
        ],
        "related_identifiers": [
            {"identifier": "https://github.com/geocy-labs/hodgecy", "relation": "isSupplementTo", "scheme": "url"},
            {"identifier": "10.5281/zenodo.21429481", "relation": "isVersionOf", "scheme": "doi"},
        ],
        "notes": f"HodgeCY v0.2.0 Zenodo DOI: 10.5281/zenodo.21429481. Prepared from generation source commit {commit}. Tagged release commit is resolved from {RELEASE_VERSION}.",
    }
    _write_json(REPO_ROOT / ".zenodo.json", zenodo)


def _update_readme() -> None:
    readme = REPO_ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    marker = "## HodgeCY v0.2.0 theorem-certificate release"
    section = f"""

{marker}

The v0.2.0 release-preparation layer generates theorem-bearing source assembly
certificates for arrangements 84, 84a, 239, 240, and 241. The certificates live
under `release/hodgecy-v0.2.0/` after running:

```bash
python scripts/build_v0_2_0_release.py
python scripts/verify_v0_2_0_release.py
```

Zenodo DOI: `10.5281/zenodo.21429481`. The 84/84a smoothing status
remains `degree112_certified`; this release does not promote
`ordinary_node_verified` or `defect_verified`.
"""
    if marker not in text:
        readme.write_text(text.rstrip() + section + "\n", encoding="utf-8")


def _manifest_and_checksums() -> None:
    files = []
    for path in sorted(RELEASE_DIR.rglob("*")):
        if not path.is_file() or path.name in {"MANIFEST.json", "SHA256SUMS"}:
            continue
        rel = path.relative_to(RELEASE_DIR).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        files.append({"path": rel, "sha256": digest, "bytes": path.stat().st_size})
    manifest = {
        "release_version": RELEASE_VERSION,
        "package_version": PACKAGE_VERSION,
        "release_tag": RELEASE_VERSION,
        "generation_source_commit": _git_output(["rev-parse", "HEAD"]),
        "tag_target_commit": TAG_TARGET_NOTE,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "theorem_arrangements": list(TARGETS),
        "files": files,
    }
    _write_json(RELEASE_DIR / "MANIFEST.json", manifest)
    lines = [f"{item['sha256']}  {item['path']}" for item in files]
    (RELEASE_DIR / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _make_archives() -> dict[str, str]:
    ARCHIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    for archive in (ARCHIVE_PATH, SOURCE_ARCHIVE_PATH):
        if archive.exists():
            archive.unlink()
    with zipfile.ZipFile(ARCHIVE_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(RELEASE_DIR.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(RELEASE_DIR.parent))
    _run(["git", "archive", "--format=zip", f"--output={SOURCE_ARCHIVE_PATH}", "HEAD"], check=True)
    return {
        ARCHIVE_PATH.name: hashlib.sha256(ARCHIVE_PATH.read_bytes()).hexdigest(),
        SOURCE_ARCHIVE_PATH.name: hashlib.sha256(SOURCE_ARCHIVE_PATH.read_bytes()).hexdigest(),
    }


def main() -> None:
    _load_version()
    if RELEASE_DIR.exists():
        shutil.rmtree(RELEASE_DIR)
    RELEASE_DIR.mkdir(parents=True)
    summaries = {}
    for arrangement_id in TARGETS:
        summaries[arrangement_id] = _write_arrangement_release(arrangement_id, _build_target_spectrum(arrangement_id))
    _write_comparisons(summaries)
    _copy_manuscript_assets()
    _copy_release_scripts()
    _write_environment()
    _write_release_docs()
    _write_citation_and_zenodo()
    _update_readme()
    _manifest_and_checksums()
    archive_checksums = _make_archives()
    _write_json(RELEASE_DIR / "archive_checksums.json", archive_checksums)
    _manifest_and_checksums()
    print(f"Built {RELEASE_NAME}")
    print(f"Release directory: {RELEASE_DIR.relative_to(REPO_ROOT)}")
    print(f"Archive: {ARCHIVE_PATH.relative_to(REPO_ROOT)}")
    print(f"Source archive: {SOURCE_ARCHIVE_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
