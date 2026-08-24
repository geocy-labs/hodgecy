"""Generate Blob 13 block-scheme Hilbert/evaluation assets for 84 and 84a."""

from __future__ import annotations

import csv
import json
import subprocess
from hashlib import sha256
from pathlib import Path
import sys
from time import perf_counter
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy import __version__ as HODGECY_VERSION  # noqa: E402
from hodgecy.geometry.block_evaluation import (  # noqa: E402
    EXPECTED_BLOB12_BLOCK_HASHES,
    BlockEvaluationResult,
    compare_block_evaluation_results,
    compute_block_evaluation_result,
    evaluation_firewall,
    load_blob12_block_scheme,
)


RUN_ROOT = REPO_ROOT / "research_outputs" / "hodgecy_ii" / "evaluation_blob13"
ASSET_ROOT = REPO_ROOT / "research_outputs" / "hodgecy_ii" / "manuscript_assets"
TABLE_ROOT = ASSET_ROOT / "tables"
DATA_ROOT = ASSET_ROOT / "data"
FIGURE_ROOT = ASSET_ROOT / "figures"
MANIFEST_ROOT = ASSET_ROOT / "manifest"
DEGREES = tuple(range(0, 9))
SOURCE_VALUES = {
    "84": {"rank_Q": 26, "rank_mod_2": 23, "SNF": "(1^23,2,6,12)"},
    "84a": {"rank_Q": 26, "rank_mod_2": 21, "SNF": "(1^21,2,4,4,4,12)"},
}


def stable_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str | None:
    try:
        completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True, capture_output=True, text=True)
    except Exception:
        return None
    return completed.stdout.strip()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stable_json(payload), encoding="utf-8")


def write_table(path: Path, rows: list[dict[str, Any]], delimiter: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows: list[dict[str, Any]], columns: list[str] | None = None) -> str:
    columns = columns or list(rows[0])
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = ["| " + " | ".join(str(row[column]) for column in columns) + " |" for row in rows]
    return "\n".join([header, sep, *body]) + "\n"


def latex_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    lines = ["\\begin{tabular}{" + "l" * len(columns) + "}", " & ".join(_tex(item) for item in columns) + r" \\", "\\hline"]
    for row in rows:
        lines.append(" & ".join(_tex(row[column]) for column in columns) + r" \\")
    lines.append("\\end{tabular}")
    return "\n".join(lines) + "\n"


def _tex(value: Any) -> str:
    return str(value).replace("_", "\\_").replace("%", "\\%")


def result_table_rows(results: dict[str, BlockEvaluationResult]) -> list[dict[str, Any]]:
    left = results["84"]
    right = results["84a"]

    def cmp(a: Any, b: Any) -> str:
        return "equal" if a == b else "different"

    rows = [
        ("block scheme degree", left.scheme_degree, right.scheme_degree, "exact block result"),
        ("H_B(8)", left.H_B_8, right.H_B_8, "exact block result"),
        ("eval source dim", left.evaluation_source_dimension, right.evaluation_source_dimension, "exact block result"),
        ("eval target length", left.evaluation_target_length, right.evaluation_target_length, "exact block result"),
        ("eval rank", left.evaluation_rank, right.evaluation_rank, "exact block result"),
        ("eval kernel dim", left.evaluation_kernel_dimension, right.evaluation_kernel_dimension, "exact block result"),
        ("eval cokernel dim", left.evaluation_cokernel_dimension, right.evaluation_cokernel_dimension, "exact block result"),
        ("block evaluation deficiency", left.block_evaluation_deficiency, right.block_evaluation_deficiency, "exact block result"),
        ("eval relation dim", left.evaluation_relation_dimension, right.evaluation_relation_dimension, "exact block rank summary"),
        ("conditional classical defect", left.conditional_classical_defect_value, right.conditional_classical_defect_value, "conditional on ordinary-node gate"),
        ("verified classical defect", "UNKNOWN", "UNKNOWN", "not promoted"),
    ]
    return [
        {
            "invariant": invariant,
            "84": value_84,
            "84a": value_84a,
            "comparison": cmp(value_84, value_84a),
            "claim_layer": layer,
        }
        for invariant, value_84, value_84a, layer in rows
    ]


def hilbert_rows(result: BlockEvaluationResult) -> list[dict[str, Any]]:
    return [
        {
            "arrangement": result.arrangement_id,
            "d": value.degree,
            "dim_S_d": value.dim_S_d,
            "dim_I_B_d": value.dim_I_B_d,
            "H_B_d": value.H_B_d,
            "matrix_shape": f"{value.evaluation_matrix_shape[0]}x{value.evaluation_matrix_shape[1]}",
            "matrix_rank": value.evaluation_rank,
            "matrix_hash": value.matrix_hash,
        }
        for value in result.hilbert_table.values
    ]


def validation_rows(results: dict[str, BlockEvaluationResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for arrangement_id, result in results.items():
        status_items = {
            "source assembly": "VERIFIED",
            "degree-112 historical certificate": "HISTORICAL_CERTIFIED",
            "verified block scheme": "VERIFIED",
            "block->singular containment": "VERIFIED",
            "ordinary_node_verified": "UNKNOWN",
            "block Hilbert function": "VERIFIED",
            "critical-degree evaluation": "VERIFIED",
            "block evaluation deficiency": "VERIFIED",
            "classical defect": "UNKNOWN",
            "integral evaluation relation complex": "UNKNOWN",
            "defect": "UNKNOWN",
        }
        rows.extend({"arrangement": arrangement_id, "layer": key, "status": value} for key, value in status_items.items())
    return rows


def write_hilbert_assets(results: dict[str, BlockEvaluationResult]) -> list[Path]:
    paths: list[Path] = []
    for result in results.values():
        rows = hilbert_rows(result)
        base = RUN_ROOT / result.arrangement_id
        write_json(base / "block_evaluation_result.json", result.to_dict())
        write_json(base / "block_evaluation_certificates.json", list(result.certificates))
        write_table(base / "block_hilbert_function.tsv", rows, "\t")
        write_table(base / "block_hilbert_function.csv", rows, ",")
        (base / "block_hilbert_function.md").write_text(f"# {result.arrangement_id} Block Hilbert Function\n\n" + markdown_table(rows), encoding="utf-8")
        paths.extend(
            [
                base / "block_evaluation_result.json",
                base / "block_evaluation_certificates.json",
                base / "block_hilbert_function.tsv",
                base / "block_hilbert_function.csv",
                base / "block_hilbert_function.md",
            ]
        )
    return paths


def write_table_ii_5(results: dict[str, BlockEvaluationResult]) -> list[Path]:
    rows = result_table_rows(results)
    paths = [
        TABLE_ROOT / "block_evaluation_comparison_84_84a.tsv",
        TABLE_ROOT / "block_evaluation_comparison_84_84a.csv",
        TABLE_ROOT / "block_evaluation_comparison_84_84a.json",
        TABLE_ROOT / "block_evaluation_comparison_84_84a.md",
        TABLE_ROOT / "block_evaluation_comparison_84_84a.tex",
    ]
    write_table(paths[0], rows, "\t")
    write_table(paths[1], rows, ",")
    write_json(paths[2], rows)
    paths[3].write_text("# Table II.5. Hilbert / Evaluation Comparison\n\n" + markdown_table(rows), encoding="utf-8")
    paths[4].write_text(latex_table(rows, list(rows[0])), encoding="utf-8")
    return paths


def write_figures(results: dict[str, BlockEvaluationResult]) -> list[Path]:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    profile_path = FIGURE_ROOT / "hilbert_profile_comparison.svg"
    profile_data = FIGURE_ROOT / "hilbert_profile_comparison_data.json"
    relation_path = FIGURE_ROOT / "evaluation_relation_diagram.svg"
    relation_data = FIGURE_ROOT / "evaluation_relation_diagram_data.json"
    profile_svg(results, profile_path)
    relation_svg(results, relation_path)
    write_json(
        profile_data,
        {
            "schema": "hodgecy_ii_hilbert_profile_comparison.v1",
            "degrees": list(DEGREES),
            "profiles": {key: [value.H_B_d for value in result.hilbert_table.values] for key, result in results.items()},
            "critical_degree": 8,
        },
    )
    write_json(
        relation_data,
        {
            "schema": "hodgecy_ii_evaluation_relation_diagram.v1",
            "results": {
                key: {
                    "rank": result.evaluation_rank,
                    "kernel_dimension": result.evaluation_kernel_dimension,
                    "cokernel_dimension": result.evaluation_cokernel_dimension,
                    "relation_dimension": result.evaluation_relation_dimension,
                }
                for key, result in results.items()
            },
        },
    )
    return [profile_path, profile_data, relation_path, relation_data]


def profile_svg(results: dict[str, BlockEvaluationResult], path: Path) -> None:
    width, height = 760, 360
    margin = 54
    max_h = max(value.H_B_d for result in results.values() for value in result.hilbert_table.values)
    colors = {"84": "#0f6b8f", "84a": "#b15d22"}

    def xy(degree: int, value: int) -> tuple[float, float]:
        x = margin + degree * ((width - 2 * margin) / 8)
        y = height - margin - value * ((height - 2 * margin) / max_h)
        return x, y

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fff" />',
        '<text x="40" y="32" font-family="Arial, sans-serif" font-size="18" font-weight="700">Figure II.4. Block-scheme Hilbert profiles</text>',
        f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="#222" />',
        f'<line x1="{margin}" y1="{height-margin}" x2="{margin}" y2="{margin}" stroke="#222" />',
    ]
    for d in DEGREES:
        x, _ = xy(d, 0)
        lines.append(f'<text x="{x}" y="{height-28}" font-family="Arial" font-size="11" text-anchor="middle">{d}</text>')
    for y_value in (0, 28, 56, 84, 112):
        _, y = xy(0, min(y_value, max_h))
        lines.append(f'<text x="44" y="{y+4}" font-family="Arial" font-size="11" text-anchor="end">{y_value}</text>')
    crit_x, _ = xy(8, 0)
    lines.append(f'<line x1="{crit_x}" y1="{margin}" x2="{crit_x}" y2="{height-margin}" stroke="#777" stroke-dasharray="4 4" />')
    lines.append(f'<text x="{crit_x-6}" y="{margin+14}" font-family="Arial" font-size="11" text-anchor="end">d=8</text>')
    for arrangement_id, result in results.items():
        points = [xy(value.degree, value.H_B_d) for value in result.hilbert_table.values]
        path_d = " ".join(("M" if i == 0 else "L") + f" {x:.2f} {y:.2f}" for i, (x, y) in enumerate(points))
        lines.append(f'<path d="{path_d}" fill="none" stroke="{colors[arrangement_id]}" stroke-width="2.2" />')
        for x, y in points:
            lines.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.5" fill="{colors[arrangement_id]}" />')
        lx, ly = points[-1]
        lines.append(f'<text x="{lx-8:.2f}" y="{ly-10:.2f}" font-family="Arial" font-size="12" fill="{colors[arrangement_id]}" text-anchor="end">{arrangement_id}</text>')
    lines.append('<text x="370" y="344" font-family="Arial" font-size="12" text-anchor="middle">degree d</text>')
    lines.append('<text x="20" y="190" font-family="Arial" font-size="12" transform="rotate(-90 20 190)" text-anchor="middle">H_B(d)</text>')
    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def relation_svg(results: dict[str, BlockEvaluationResult], path: Path) -> None:
    width, height = 860, 320
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fff" />',
        '<text x="40" y="34" font-family="Arial, sans-serif" font-size="18" font-weight="700">Figure II.5. Degree-8 evaluation relation summary</text>',
    ]
    y = 82
    for arrangement_id, result in results.items():
        lines.extend(
            [
                f'<text x="40" y="{y+8}" font-family="Arial" font-size="16" font-weight="700">{arrangement_id}</text>',
                f'<rect x="125" y="{y-22}" width="120" height="44" rx="5" fill="#eef6ff" stroke="#4d6f8f" />',
                f'<text x="185" y="{y+4}" font-family="Arial" font-size="14" text-anchor="middle">QQ^165</text>',
                f'<line x1="250" y1="{y}" x2="388" y2="{y}" stroke="#333" stroke-width="1.5" />',
                f'<polygon points="388,{y} 378,{y-6} 378,{y+6}" fill="#333" />',
                f'<text x="319" y="{y-10}" font-family="Arial" font-size="12" text-anchor="middle">E_8 rank {result.evaluation_rank}</text>',
                f'<rect x="400" y="{y-22}" width="120" height="44" rx="5" fill="#f1f8ee" stroke="#5d8f4d" />',
                f'<text x="460" y="{y+4}" font-family="Arial" font-size="14" text-anchor="middle">QQ^112</text>',
                f'<line x1="525" y1="{y}" x2="663" y2="{y}" stroke="#777" stroke-width="1.5" stroke-dasharray="4 3" />',
                f'<polygon points="663,{y} 653,{y-6} 653,{y+6}" fill="#777" />',
                f'<text x="594" y="{y-10}" font-family="Arial" font-size="12" text-anchor="middle">dual rank summary</text>',
                f'<rect x="675" y="{y-22}" width="132" height="44" rx="5" fill="#fff3cf" stroke="#b98712" />',
                f'<text x="741" y="{y-2}" font-family="Arial" font-size="12" text-anchor="middle">dim ker(E_8^T)</text>',
                f'<text x="741" y="{y+14}" font-family="Arial" font-size="14" font-weight="700" text-anchor="middle">{result.evaluation_relation_dimension}</text>',
                f'<text x="125" y="{y+42}" font-family="Arial" font-size="12">kernel dim {result.evaluation_kernel_dimension}; cokernel/deficiency {result.evaluation_cokernel_dimension}</text>',
            ]
        )
        y += 112
    lines.append('<text x="40" y="292" font-family="Arial" font-size="12" fill="#555">No explicit point matrix or integral evaluation lattice is constructed.</text>')
    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_reports(results: dict[str, BlockEvaluationResult], comparison: Any) -> list[Path]:
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "hodgecy_ii_block_evaluation_blob13.v1",
        "hodgecy_version": HODGECY_VERSION,
        "results": {key: value.to_dict() for key, value in results.items()},
        "comparison": comparison.to_dict(),
        "source_values_retained_for_blob14": SOURCE_VALUES,
        "firewall": evaluation_firewall(),
    }
    paths = [
        RUN_ROOT / "hodgecy_ii_block_evaluation_blob13.json",
        RUN_ROOT / "hodgecy_ii_block_evaluation_blob13.md",
        RUN_ROOT / "hodgecy_ii_84_84a_evaluation_comparison.json",
        RUN_ROOT / "hodgecy_ii_84_84a_evaluation_comparison.md",
    ]
    write_json(paths[0], payload)
    paths[1].write_text(report_markdown(results, comparison), encoding="utf-8")
    write_json(paths[2], {"comparison": comparison.to_dict(), "results": {key: value.to_dict() for key, value in results.items()}})
    paths[3].write_text(comparison_markdown(results, comparison), encoding="utf-8")
    return paths


def report_markdown(results: dict[str, BlockEvaluationResult], comparison: Any) -> str:
    lines = ["# HodgeCY II Block Evaluation - Blob 13", ""]
    for arrangement_id, result in results.items():
        values = ", ".join(str(value.H_B_d) for value in result.hilbert_table.values)
        lines.extend(
            [
                f"## {arrangement_id}",
                f"- block ideal hash: `{result.block_scheme_hash}`",
                f"- Hilbert range: `{DEGREES[0]}..{DEGREES[-1]}`",
                f"- Hilbert values: `{values}`",
                f"- H_B(8): `{result.H_B_8}`",
                f"- evaluation rank: `{result.evaluation_rank}`",
                f"- block evaluation deficiency: `{result.block_evaluation_deficiency}`",
                f"- evaluation relation dimension: `{result.evaluation_relation_dimension}`",
                f"- conditional classical defect: `{result.conditional_classical_defect_value}`",
                "- actual classical defect: `UNKNOWN`",
                "",
            ]
        )
    lines.extend(["## Comparison", f"- first Hilbert-profile difference: `{comparison.first_hilbert_difference}`", f"- descriptive case: `{comparison.descriptive_case}`", ""])
    return "\n".join(lines)


def comparison_markdown(results: dict[str, BlockEvaluationResult], comparison: Any) -> str:
    rows = result_table_rows(results)
    return "# HodgeCY II 84/84a Evaluation Comparison\n\n" + markdown_table(rows) + f"\nDescriptive case: `{comparison.descriptive_case}`\n"


def update_validation_assets(results: dict[str, BlockEvaluationResult]) -> list[Path]:
    rows = validation_rows(results)
    paths = [
        DATA_ROOT / "validation_status_84_84a.tsv",
        DATA_ROOT / "validation_status_84_84a.json",
        DATA_ROOT / "validation_status_84_84a.md",
    ]
    write_table(paths[0], rows, "\t")
    write_json(paths[1], rows)
    paths[2].write_text("# 84/84a Validation Status Matrix\n\n" + markdown_table(rows), encoding="utf-8")
    return paths


def update_scope_manifest(results: dict[str, BlockEvaluationResult], comparison: Any) -> Path:
    path = MANIFEST_ROOT / "hodgecy_ii_scope.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["required_geometric_outputs"]["blob_13"] = {
        "block_hilbert_function": "VERIFIED",
        "critical_degree_block_evaluation": "VERIFIED",
        "block_evaluation_deficiency": "VERIFIED",
        "classical_defect": "UNKNOWN",
        "computed_range": [DEGREES[0], DEGREES[-1]],
        "descriptive_case": comparison.descriptive_case,
    }
    payload["nonclaims"]["no_defect"] = (
        "Blob 13 computes exact degree-8 block-scheme evaluation deficiencies for 84/84a, "
        "but verified classical defect remains UNKNOWN until ordinary-node prerequisites are satisfied."
    )
    payload["geometric_status_blob_13"] = {
        key: {
            "H_B_8": result.H_B_8,
            "evaluation_rank": result.evaluation_rank,
            "block_evaluation_deficiency": result.block_evaluation_deficiency,
            "evaluation_relation_dimension": result.evaluation_relation_dimension,
            "conditional_classical_defect_value": result.conditional_classical_defect_value,
            "actual_classical_defect": "UNKNOWN",
        }
        for key, result in results.items()
    }
    write_json(path, payload)
    return path


def update_asset_manifest(paths: list[Path]) -> Path:
    path = MANIFEST_ROOT / "hodgecy_ii_asset_manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    artifacts = payload.setdefault("artifacts", {})
    for artifact_path in paths:
        rel = artifact_path.relative_to(REPO_ROOT).as_posix()
        artifacts[rel] = {"sha256": file_sha256(artifact_path), "status": "BLOB13_READY"}
    scope = MANIFEST_ROOT / "hodgecy_ii_scope.json"
    artifacts[scope.relative_to(REPO_ROOT).as_posix()] = {"sha256": file_sha256(scope), "status": "CONTEXT_READY"}
    payload["blob_13_block_evaluation"] = {
        "table_ii_5": "research_outputs/hodgecy_ii/manuscript_assets/tables/block_evaluation_comparison_84_84a.tsv",
        "figure_ii_4": "research_outputs/hodgecy_ii/manuscript_assets/figures/hilbert_profile_comparison.svg",
        "figure_ii_5": "research_outputs/hodgecy_ii/manuscript_assets/figures/evaluation_relation_diagram.svg",
        "classical_defect": "UNKNOWN",
    }
    write_json(path, payload)
    return path


def main() -> None:
    start = perf_counter()
    commit = git_commit()
    results: dict[str, BlockEvaluationResult] = {}
    for arrangement_id in ("84", "84a"):
        scheme_path = REPO_ROOT / "research_outputs" / "hodgecy_ii" / "node_block_blob12" / arrangement_id / "node_block_certificate.json"
        scheme = load_blob12_block_scheme(scheme_path, expected_hash=EXPECTED_BLOB12_BLOCK_HASHES[arrangement_id])
        results[arrangement_id] = compute_block_evaluation_result(scheme, degrees=DEGREES, git_commit=commit)
    comparison = compare_block_evaluation_results(results["84"], results["84a"])
    artifact_paths: list[Path] = []
    artifact_paths.extend(write_hilbert_assets(results))
    artifact_paths.extend(write_reports(results, comparison))
    artifact_paths.extend(write_table_ii_5(results))
    artifact_paths.extend(write_figures(results))
    artifact_paths.extend(update_validation_assets(results))
    scope_path = update_scope_manifest(results, comparison)
    manifest_path = update_asset_manifest([*artifact_paths, scope_path])
    print("HodgeCY II Blob 13 block evaluation assets generated")
    print(f"- 84 H_B(8): {results['84'].H_B_8}, deficiency: {results['84'].block_evaluation_deficiency}")
    print(f"- 84a H_B(8): {results['84a'].H_B_8}, deficiency: {results['84a'].block_evaluation_deficiency}")
    print(f"- first Hilbert difference: {comparison.first_hilbert_difference}")
    print(f"- descriptive case: {comparison.descriptive_case}")
    print(f"- table II.5: {(TABLE_ROOT / 'block_evaluation_comparison_84_84a.tsv').relative_to(REPO_ROOT).as_posix()}")
    print(f"- figure II.4: {(FIGURE_ROOT / 'hilbert_profile_comparison.svg').relative_to(REPO_ROOT).as_posix()}")
    print(f"- figure II.5: {(FIGURE_ROOT / 'evaluation_relation_diagram.svg').relative_to(REPO_ROOT).as_posix()}")
    print(f"- scope manifest: {scope_path.relative_to(REPO_ROOT).as_posix()}")
    print(f"- asset manifest: {manifest_path.relative_to(REPO_ROOT).as_posix()}")
    print(f"- total generation seconds: {perf_counter() - start:.3f}")


if __name__ == "__main__":
    main()
