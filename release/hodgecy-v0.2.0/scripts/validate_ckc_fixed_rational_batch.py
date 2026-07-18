"""Validate fixed rational CKC equation candidates and compute spectra."""

from __future__ import annotations

from itertools import combinations
import csv
import json
from pathlib import Path
import re
import sys
from typing import Any

import pandas as pd
import sympy as sp

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.equivariant import (  # noqa: E402
    build_gluing_matrix,
    character_C0,
    character_C1,
    character_kernel_cokernel_placeholder,
    cokernel_dimension_Q,
    incidence_table_from_linear_forms,
    invariant_permutations,
    kernel_dimension_Q,
    orbit_decomposition,
    permutation_group_summary,
    rank_mod_p,
    rank_over_Q,
    singular_strata_from_incidence_table,
    smith_normal_form_invariants,
)


INDEX_PATH = REPO_ROOT / "data" / "raw" / "cynk_kocel_cynk_2026" / "ckc_equation_index_001_455.json"
TABLE1_PATH = REPO_ROOT / "data" / "raw" / "cynk_meyer_table1.csv"
OUT_DIR = REPO_ROOT / "data" / "processed" / "equivariant_spectra" / "ckc_fixed_rational_batch"
PAPER_TABLE_DIR = REPO_ROOT / "paper" / "tables"

RATIONAL_CANDIDATES = ["1", "3", "19", "32", "69", "93", "238", "239", "240", "241", "245"]
ALGEBRAIC_CANDIDATES = ["452", "453"]
EXPECTED_CANDIDATES = [*RATIONAL_CANDIDATES, *ALGEBRAIC_CANDIDATES]


def _load_index() -> dict[str, Any]:
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def _load_hodge_data() -> dict[str, dict[str, Any]]:
    if not TABLE1_PATH.exists():
        return {}
    with TABLE1_PATH.open(newline="", encoding="utf-8") as handle:
        return {str(row["arrangement"]): row for row in csv.DictReader(handle)}


def _strip_outer_parentheses(text: str) -> str:
    if text.startswith("(") and text.endswith(")"):
        return text[1:-1]
    return text


def _coefficients_from_factor(factor: str) -> list[sp.Rational]:
    """Parse a rational linear factor into coefficients of x,y,z,t."""
    factor = _strip_outer_parentheses(factor)
    if "√" in factor or "sqrt" in factor:
        raise ValueError("algebraic coefficient detected")
    text = factor.replace("-", "+-")
    if text.startswith("+"):
        text = text[1:]
    terms = [term for term in text.split("+") if term]
    coeffs = {variable: sp.Rational(0) for variable in "xyzt"}
    for term in terms:
        match = re.fullmatch(r"([+-]?\d*)?([xyzt])", term)
        if not match:
            raise ValueError(f"unsupported linear term: {term!r} in factor {factor!r}")
        raw_coeff, variable = match.groups()
        if raw_coeff in ("", "+", None):
            coeff = sp.Rational(1)
        elif raw_coeff == "-":
            coeff = sp.Rational(-1)
        else:
            coeff = sp.Rational(int(raw_coeff))
        coeffs[variable] += coeff
    return [coeffs[variable] for variable in "xyzt"]


def _record_from_extracted(record: dict[str, Any]) -> dict[str, Any]:
    linear_forms = []
    for index, factor in enumerate(record["linear_factor_texts"], start=1):
        linear_forms.append(
            {
                "label": f"p{index}",
                "coefficients": [str(value) for value in _coefficients_from_factor(factor)],
                "equation": factor,
            }
        )
    return {
        "arrangement_id": record["arrangement_id"],
        "source": "CKC Section 6.1 raw PDF extraction, rational fixed candidate",
        "representative_status": "raw_extracted",
        "parameter_choice": None,
        "source_equation": record["equation_text"],
        "source_reference": record["source_reference"],
        "linear_forms": linear_forms,
    }


def _line_action(line: tuple[int, ...], permutation: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(sorted(permutation[index] for index in line))


def _point_action(point: tuple[int, ...], permutation: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(sorted(permutation[index] for index in point))


def _computed_inventory(inventory: dict[str, int]) -> dict[str, int]:
    return {
        "p3": int(inventory.get("p3", 0)),
        "p4_0": int(inventory.get("p4_0", 0)),
        "p4_1": int(inventory.get("p4_1", 0)),
        "p5_0": int(inventory.get("p5_0", 0)),
        "p5_1": int(inventory.get("p5_1", 0)),
        "p5_2": int(inventory.get("p5_2", 0)),
        "l3": int(inventory.get("triple_lines", 0)),
    }


def _hodge_for(arrangement_id: str, hodge_rows: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    row = hodge_rows.get(arrangement_id)
    if not row:
        return None
    return {
        "h12": int(row["h12"]),
        "h11": int(row["h11"]),
        "euler": int(row["euler"]),
        "source": "data/raw/cynk_meyer_table1.csv",
        "validation_status": "table_lookup_not_newly_validated",
    }


def _build_validated_spectrum(record: dict[str, Any], hodge_rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    linear_forms = [
        {
            "index": index,
            "label": form["label"],
            "coefficients": [sp.Rational(value) for value in form["coefficients"]],
            "equation": form["equation"],
        }
        for index, form in enumerate(record["linear_forms"])
    ]
    incidence_table = incidence_table_from_linear_forms(linear_forms)
    strata = singular_strata_from_incidence_table(incidence_table, linear_forms)
    permutations = invariant_permutations(incidence_table)
    group_summary = permutation_group_summary(permutations)
    matrix = build_gluing_matrix(strata["double_lines"], strata["multiple_points"])
    double_line_items = [tuple(line["planes"]) for line in strata["double_lines"]]
    multiple_point_items = [tuple(point["planes"]) for point in strata["multiple_points"]]
    return {
        "arrangement_id": record["arrangement_id"],
        "validation_status": "validated_combinatorial",
        "source": record["source"],
        "source_reference": record["source_reference"],
        "source_equation": record["source_equation"],
        "linear_forms": record["linear_forms"],
        "incidence_table": [list(item) for item in incidence_table],
        "singularity_inventory": strata["inventory"],
        "computed_inventory": _computed_inventory(strata["inventory"]),
        "hodge_data_if_available": _hodge_for(record["arrangement_id"], hodge_rows),
        "automorphism_group_order": group_summary["order"],
        "invariant_permutations": group_summary["all_permutations"],
        "plane_orbits": orbit_decomposition(list(range(8)), permutations),
        "double_line_orbits": [[list(item) for item in orbit] for orbit in orbit_decomposition(double_line_items, permutations, _line_action)],
        "multiple_point_orbits": [[list(item) for item in orbit] for orbit in orbit_decomposition(multiple_point_items, permutations, _point_action)],
        "gluing_matrix_shape": [int(matrix.rows), int(matrix.cols)],
        "rank_Q": rank_over_Q(matrix),
        "rank_F2": rank_mod_p(matrix, p=2),
        "kernel_dim_Q": kernel_dimension_Q(matrix),
        "cokernel_dim_Q": cokernel_dimension_Q(matrix),
        "smith_normal_form": smith_normal_form_invariants(matrix),
        "character_C1": character_C1(strata["double_lines"], permutations),
        "character_C0": character_C0(strata["multiple_points"], permutations),
        "character_kernel_cokernel": character_kernel_cokernel_placeholder(matrix, permutations),
        "notes": "Combinatorial/incidence validation from raw CKC PDF extraction. Does not validate smoothing or newly prove Hodge data.",
    }


def _inventory_signature(item: dict[str, Any]) -> str:
    inventory = item.get("computed_inventory") or {}
    return ";".join(f"{key}={int(inventory.get(key, 0))}" for key in ("p3", "p4_0", "p4_1", "p5_0", "p5_1", "p5_2", "l3"))


def _hodge_signature(item: dict[str, Any]) -> str:
    hodge = item.get("hodge_data_if_available") or {}
    return ";".join(f"{key}={hodge.get(key)}" for key in ("h12", "h11", "euler"))


def _orbit_sizes(orbits: list[Any]) -> str:
    return ",".join(str(len(orbit)) for orbit in sorted(orbits, key=lambda orbit: (len(orbit), str(orbit))))


def _snf(item: dict[str, Any]) -> str:
    return ",".join(str(value) for value in (item.get("smith_normal_form") or []))


def _equivariant_signature(item: dict[str, Any]) -> str:
    payload = {
        "automorphism_group_order": item["automorphism_group_order"],
        "gluing_matrix_shape": item["gluing_matrix_shape"],
        "rank_Q": item["rank_Q"],
        "rank_F2": item["rank_F2"],
        "kernel_dim_Q": item["kernel_dim_Q"],
        "cokernel_dim_Q": item["cokernel_dim_Q"],
        "smith_normal_form": item["smith_normal_form"],
        "plane_orbit_sizes": _orbit_sizes(item["plane_orbits"]),
        "double_line_orbit_sizes": _orbit_sizes(item["double_line_orbits"]),
        "multiple_point_orbit_sizes": _orbit_sizes(item["multiple_point_orbits"]),
    }
    return json.dumps(payload, sort_keys=True)


def _summary_row(item: dict[str, Any]) -> dict[str, Any]:
    hodge = item.get("hodge_data_if_available") or {}
    return {
        "arrangement_id": item["arrangement_id"],
        "validation_status": item["validation_status"],
        "inventory_signature": _inventory_signature(item),
        "hodge_signature": _hodge_signature(item),
        "h12": hodge.get("h12"),
        "h11": hodge.get("h11"),
        "euler": hodge.get("euler"),
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
        "equivariant_gluing_signature": _equivariant_signature(item),
    }


def _difference_summary(left: dict[str, Any], right: dict[str, Any]) -> str:
    checks = [
        ("automorphism_group_order", left["automorphism_group_order"], right["automorphism_group_order"]),
        ("gluing_matrix_shape", left["gluing_matrix_shape"], right["gluing_matrix_shape"]),
        ("rank_Q", left["rank_Q"], right["rank_Q"]),
        ("rank_F2", left["rank_F2"], right["rank_F2"]),
        ("kernel_dim_Q", left["kernel_dim_Q"], right["kernel_dim_Q"]),
        ("cokernel_dim_Q", left["cokernel_dim_Q"], right["cokernel_dim_Q"]),
        ("smith_normal_form", _snf(left), _snf(right)),
        ("plane_orbits", _orbit_sizes(left["plane_orbits"]), _orbit_sizes(right["plane_orbits"])),
        ("double_line_orbits", _orbit_sizes(left["double_line_orbits"]), _orbit_sizes(right["double_line_orbits"])),
        ("multiple_point_orbits", _orbit_sizes(left["multiple_point_orbits"]), _orbit_sizes(right["multiple_point_orbits"])),
    ]
    return "; ".join(name for name, left_value, right_value in checks if left_value != right_value)


def _write_tables(summary_rows: list[dict[str, Any]], spectra: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    clusters = []
    pairs = []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in summary_rows:
        grouped.setdefault(row["inventory_signature"], []).append(row)

    spectra_by_id = {item["arrangement_id"]: item for item in spectra}
    for index, (inventory_signature, members) in enumerate(sorted(grouped.items()), start=1):
        cluster_id = f"ckc_fixed_rational_inventory_cluster_{index:03d}"
        signatures = sorted({member["equivariant_gluing_signature"] for member in members})
        clusters.append(
            {
                "cluster_id": cluster_id,
                "cluster_type": "singularity_inventory",
                "member_count": len(members),
                "members": ",".join(member["arrangement_id"] for member in members),
                "inventory_signature": inventory_signature,
                "hodge_signatures": " | ".join(sorted({member["hodge_signature"] for member in members})),
                "equivariant_data_varies": len(signatures) > 1,
                "automorphism_group_orders": ",".join(str(member["automorphism_group_order"]) for member in members),
                "rank_Q_values": ",".join(str(member["rank_Q"]) for member in members),
                "rank_F2_values": ",".join(str(member["rank_F2"]) for member in members),
            }
        )
        for left_row, right_row in combinations(members, 2):
            if left_row["equivariant_gluing_signature"] == right_row["equivariant_gluing_signature"]:
                continue
            left = spectra_by_id[left_row["arrangement_id"]]
            right = spectra_by_id[right_row["arrangement_id"]]
            pairs.append(
                {
                    "cluster_id": cluster_id,
                    "left_arrangement": left["arrangement_id"],
                    "right_arrangement": right["arrangement_id"],
                    "shared_inventory": inventory_signature,
                    "left_hodge": _hodge_signature(left),
                    "right_hodge": _hodge_signature(right),
                    "left_automorphism_group_order": left["automorphism_group_order"],
                    "right_automorphism_group_order": right["automorphism_group_order"],
                    "left_rank_Q": left["rank_Q"],
                    "right_rank_Q": right["rank_Q"],
                    "left_rank_F2": left["rank_F2"],
                    "right_rank_F2": right["rank_F2"],
                    "differences": _difference_summary(left, right),
                }
            )
    return clusters, pairs


def _write_latex(df: pd.DataFrame, path: Path) -> None:
    path.write_text(df.to_latex(index=False, escape=False), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PAPER_TABLE_DIR.mkdir(parents=True, exist_ok=True)
    index = _load_index()
    records = {str(record["arrangement_id"]): record for record in index["records"]}
    hodge_rows = _load_hodge_data()
    spectra = []
    validation_records = []

    for arrangement_id in RATIONAL_CANDIDATES:
        source = records[arrangement_id]
        try:
            if len(source["linear_factor_texts"]) != 8:
                raise ValueError(f"expected 8 linear factors, found {len(source['linear_factor_texts'])}")
            parsed_record = _record_from_extracted(source)
            spectrum = _build_validated_spectrum(parsed_record, hodge_rows)
            spectra.append(spectrum)
            validation_records.append({"arrangement_id": arrangement_id, "validation_status": "validated_combinatorial", "notes": ""})
        except Exception as exc:  # noqa: BLE001
            validation_records.append({"arrangement_id": arrangement_id, "validation_status": "computation_failed", "notes": str(exc)})

    for arrangement_id in ALGEBRAIC_CANDIDATES:
        validation_records.append(
            {
                "arrangement_id": arrangement_id,
                "validation_status": "skipped_algebraic_coefficients",
                "notes": "Requires exact quadratic-field coefficient support.",
            }
        )

    summary_rows = [_summary_row(item) for item in spectra]
    clusters, pairs = _write_tables(summary_rows, spectra)

    summary_df = pd.DataFrame(summary_rows)
    cluster_df = pd.DataFrame(clusters)
    pair_df = pd.DataFrame(pairs)
    summary_df.to_csv(OUT_DIR / "ckc_fixed_rational_spectrum_summary.csv", index=False)
    cluster_df.to_csv(OUT_DIR / "ckc_fixed_rational_clusters.csv", index=False)
    pair_df.to_csv(OUT_DIR / "ckc_fixed_rational_differentiating_pairs.csv", index=False)
    (OUT_DIR / "ckc_fixed_rational_spectra.json").write_text(json.dumps({"spectra": spectra}, indent=2), encoding="utf-8")
    (OUT_DIR / "ckc_fixed_rational_clusters.json").write_text(json.dumps({"clusters": clusters}, indent=2), encoding="utf-8")
    report = {
        "rational_fixed_candidates_attempted": RATIONAL_CANDIDATES,
        "algebraic_fixed_candidates": ALGEBRAIC_CANDIDATES,
        "validation_records": validation_records,
        "validated_combinatorial": [record["arrangement_id"] for record in validation_records if record["validation_status"] == "validated_combinatorial"],
        "failed": [record for record in validation_records if record["validation_status"] in {"parse_failed", "computation_failed"}],
        "skipped_algebraic": [record["arrangement_id"] for record in validation_records if record["validation_status"] == "skipped_algebraic_coefficients"],
        "cluster_count": len(clusters),
        "differentiating_pair_count": len(pairs),
        "notes": "Combinatorial/incidence validation only. The full CKC dataset is not marked validated.",
    }
    (OUT_DIR / "ckc_fixed_rational_validation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    paper_summary_cols = [
        "arrangement_id",
        "validation_status",
        "inventory_signature",
        "hodge_signature",
        "automorphism_group_order",
        "gluing_matrix_shape",
        "rank_Q",
        "rank_F2",
        "kernel_dim_Q",
        "cokernel_dim_Q",
    ]
    paper_cluster_cols = [
        "cluster_id",
        "member_count",
        "members",
        "inventory_signature",
        "equivariant_data_varies",
        "automorphism_group_orders",
        "rank_Q_values",
        "rank_F2_values",
    ]
    paper_pair_cols = [
        "left_arrangement",
        "right_arrangement",
        "shared_inventory",
        "left_automorphism_group_order",
        "right_automorphism_group_order",
        "left_rank_Q",
        "right_rank_Q",
        "left_rank_F2",
        "right_rank_F2",
        "differences",
    ]
    summary_df[paper_summary_cols].to_csv(PAPER_TABLE_DIR / "table_ckc_fixed_rational_spectrum_summary.csv", index=False)
    _write_latex(summary_df[paper_summary_cols], PAPER_TABLE_DIR / "table_ckc_fixed_rational_spectrum_summary.tex")
    cluster_df[paper_cluster_cols].to_csv(PAPER_TABLE_DIR / "table_ckc_fixed_rational_clusters.csv", index=False)
    _write_latex(cluster_df[paper_cluster_cols], PAPER_TABLE_DIR / "table_ckc_fixed_rational_clusters.tex")
    pair_df[paper_pair_cols].to_csv(PAPER_TABLE_DIR / "table_ckc_fixed_rational_differentiating_pairs.csv", index=False)
    _write_latex(pair_df[paper_pair_cols], PAPER_TABLE_DIR / "table_ckc_fixed_rational_differentiating_pairs.tex")

    print("CKC fixed rational validation complete:")
    print(f"- attempted rational candidates: {', '.join(RATIONAL_CANDIDATES)}")
    print(f"- validated_combinatorial: {', '.join(report['validated_combinatorial'])}")
    print(f"- failed: {len(report['failed'])}")
    print(f"- skipped algebraic: {', '.join(report['skipped_algebraic'])}")
    print(f"- clusters: {len(clusters)}")
    print(f"- differentiating pairs: {len(pairs)}")
    print(f"Output directory: {OUT_DIR}")


if __name__ == "__main__":
    main()
