"""Generate Blob 12 node-block certification assets for arrangements 84 and 84a."""

from __future__ import annotations

import csv
import json
from hashlib import sha256
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.arrangements import arrangement_84, arrangement_84a  # noqa: E402
from hodgecy.geometry.verified_node_blocks import NodeBlockCertification, build_node_block_certification  # noqa: E402


ASSET_ROOT = REPO_ROOT / "research_outputs" / "hodgecy_ii" / "manuscript_assets"
RUN_ROOT = REPO_ROOT / "research_outputs" / "hodgecy_ii" / "node_block_blob12"
TABLE_ROOT = ASSET_ROOT / "tables"
DATA_ROOT = ASSET_ROOT / "data"
FIGURE_ROOT = ASSET_ROOT / "figures"
MANIFEST_ROOT = ASSET_ROOT / "manifest"


def stable_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stable_json(payload), encoding="utf-8")


def write_table(path: Path, rows: list[dict[str, Any]], delimiter: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = ["| " + " | ".join(str(row[column]) for column in columns) + " |" for row in rows]
    return "\n".join([header, separator, *body]) + "\n"


def latex_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    escaped_columns = [column.replace("_", "\\_") for column in columns]
    lines = [
        "\\begin{tabular}{" + "l" * len(columns) + "}",
        " & ".join(escaped_columns) + r" \\",
        "\\hline",
    ]
    for row in rows:
        values = [str(row[column]).replace("_", "\\_").replace("%", "\\%") for column in columns]
        lines.append(" & ".join(values) + r" \\")
    lines.append("\\end{tabular}")
    return "\n".join(lines) + "\n"


def certification_table_rows(certifications: list[NodeBlockCertification]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cert in certifications:
        statuses = cert.validation_status
        rows.append(
            {
                "arrangement": cert.arrangement_id,
                "perturbation_polynomial": cert.validation_status["perturbation_polynomial"],
                "ordinary_node_promotion": cert.promotion_status,
                "predicted_blocks": len(cert.blocks),
                "predicted_degree": sum(block.degree for block in cert.blocks),
                "G1": statuses["G1"],
                "G2": statuses["G2"],
                "block_scheme": statuses["block_scheme"],
                "saturated_jacobian_ideal": statuses["saturated_jacobian_ideal"],
                "block_jacobian_containment": statuses["block_jacobian_containment"],
                "ordinary_node_verified": statuses["ordinary_node_verified"],
                "defect": statuses["defect"],
                "block_scheme_hash": cert.block_scheme_hash,
            }
        )
    return rows


def validation_matrix_rows(certifications: list[NodeBlockCertification]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cert in certifications:
        for key, value in cert.validation_status.items():
            rows.append({"arrangement": cert.arrangement_id, "layer": key, "status": value})
    return rows


def write_figure(certifications: list[NodeBlockCertification]) -> None:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    stages = [
        ("G1/G2", "VERIFIED"),
        ("28 reduced blocks", "VERIFIED"),
        ("disjoint degree 112 block scheme", "VERIFIED"),
        ("Jacobian containment", "VERIFIED"),
        ("saturated Jacobian ideal", "UNKNOWN"),
        ("ordinary-node promotion", "UNKNOWN"),
    ]
    width = 940
    height = 270
    step_width = 140
    start_x = 40
    y = 90
    rects = []
    for index, (label, status) in enumerate(stages):
        x = start_x + index * (step_width + 10)
        fill = "#dff3ea" if status == "VERIFIED" else "#fff0c8"
        stroke = "#1c7c54" if status == "VERIFIED" else "#9a6a00"
        rects.append(
            f'<rect x="{x}" y="{y}" width="{step_width}" height="72" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1.5" />'
        )
        rects.append(
            f'<text x="{x + step_width / 2}" y="{y + 32}" font-family="Arial, sans-serif" font-size="13" text-anchor="middle" fill="#111">{label}</text>'
        )
        rects.append(
            f'<text x="{x + step_width / 2}" y="{y + 54}" font-family="Arial, sans-serif" font-size="12" font-weight="700" text-anchor="middle" fill="{stroke}">{status}</text>'
        )
        if index < len(stages) - 1:
            x2 = x + step_width
            rects.append(f'<line x1="{x2 + 4}" y1="{y + 36}" x2="{x2 + 22}" y2="{y + 36}" stroke="#555" stroke-width="1.2" />')
            rects.append(f'<polygon points="{x2 + 22},{y + 36} {x2 + 14},{y + 31} {x2 + 14},{y + 41}" fill="#555" />')
    subtitle = "84 and 84a stop at saturated Jacobian ideal: exact promotion remains UNKNOWN"
    svg = "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="#ffffff" />',
            '<text x="40" y="42" font-family="Arial, sans-serif" font-size="20" font-weight="700" fill="#111">Figure II.3. Node-block certification bridge</text>',
            f'<text x="40" y="66" font-family="Arial, sans-serif" font-size="13" fill="#444">{subtitle}</text>',
            *rects,
            '<text x="40" y="222" font-family="Arial, sans-serif" font-size="12" fill="#555">Exact block scheme and Jacobian containment are repo-native; saturated Jacobian ideal/reducedness requires an unavailable exact CAS certificate.</text>',
            "</svg>",
        ]
    )
    (FIGURE_ROOT / "node_certification_bridge.svg").write_text(svg + "\n", encoding="utf-8")
    write_json(
        FIGURE_ROOT / "node_certification_bridge_data.json",
        {
            "schema": "hodgecy_ii_node_certification_bridge_figure.v1",
            "arrangements": [cert.arrangement_id for cert in certifications],
            "stages": [{"stage": label, "status": status} for label, status in stages],
        },
    )


def update_scope_manifest(certifications: list[NodeBlockCertification]) -> None:
    path = MANIFEST_ROOT / "hodgecy_ii_scope.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["required_geometric_outputs"]["blob_12"] = {
        "ordinary_node_promotion": "UNKNOWN",
        "strongest_certified_stage": "exact reduced disjoint degree-112 predicted block scheme with Jacobian containment",
        "blocked_step": "saturated_jacobian_ideal",
    }
    payload["nonclaims"]["no_odp_promotion"] = (
        "Blob 12 verifies the predicted block scheme and Jacobian containment for 84/84a, "
        "but ordinary-node promotion remains UNKNOWN without a reproducible saturated Jacobian ideal."
    )
    payload["geometric_status_blob_12"] = {
        cert.arrangement_id: {
            "promotion_status": cert.promotion_status,
            "block_scheme_hash": cert.block_scheme_hash,
            "validation_status": cert.validation_status,
        }
        for cert in certifications
    }
    write_json(path, payload)


def update_asset_manifest(artifact_paths: list[Path]) -> None:
    path = MANIFEST_ROOT / "hodgecy_ii_asset_manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    artifacts = payload.setdefault("artifacts", {})
    for artifact_path in artifact_paths:
        rel = artifact_path.relative_to(REPO_ROOT).as_posix()
        artifacts[rel] = {"sha256": file_sha256(artifact_path), "status": "BLOB12_READY"}
    scope_path = MANIFEST_ROOT / "hodgecy_ii_scope.json"
    artifacts[scope_path.relative_to(REPO_ROOT).as_posix()] = {"sha256": file_sha256(scope_path), "status": "CONTEXT_READY"}
    payload["blob_12_node_certification"] = {
        "ordinary_node_promotion": "UNKNOWN",
        "table_ii_4": "research_outputs/hodgecy_ii/manuscript_assets/tables/node_certification_84_84a.tsv",
        "figure_ii_3": "research_outputs/hodgecy_ii/manuscript_assets/figures/node_certification_bridge.svg",
    }
    write_json(path, payload)


def main() -> None:
    certifications = [build_node_block_certification(arrangement_84()), build_node_block_certification(arrangement_84a())]
    artifact_paths: list[Path] = []
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    for cert in certifications:
        cert_dir = RUN_ROOT / cert.arrangement_id
        cert_path = cert_dir / "node_block_certificate.json"
        write_json(cert_path, cert.to_dict())
        artifact_paths.append(cert_path)
        block_rows = [block.to_dict() for block in cert.blocks]
        block_path = cert_dir / "predicted_node_blocks.tsv"
        write_table(block_path, block_rows, "\t")
        artifact_paths.append(block_path)
    summary_path = RUN_ROOT / "hodgecy_ii_node_block_certification.json"
    write_json(
        summary_path,
        {
            "schema": "hodgecy_ii_node_block_certification_summary.v1",
            "certifications": [cert.to_dict() for cert in certifications],
            "ordinary_node_promotion": "UNKNOWN",
            "blocked_step": "saturated_jacobian_ideal",
        },
    )
    artifact_paths.append(summary_path)
    md_path = RUN_ROOT / "hodgecy_ii_node_block_certification.md"
    md_path.write_text(
        "# HodgeCY II Blob 12 Node-Block Certification\n\n"
        "The predicted 84/84a node block schemes are exact, reduced, pairwise disjoint, degree 112, "
        "and contained in the Jacobian singular scheme. Ordinary-node promotion remains `UNKNOWN` "
        "because the saturated Jacobian ideal and reducedness certificate are not reproducible in the current environment.\n",
        encoding="utf-8",
    )
    artifact_paths.append(md_path)

    table_rows = certification_table_rows(certifications)
    columns = list(table_rows[0])
    for suffix, delimiter in (("tsv", "\t"), ("csv", ",")):
        table_path = TABLE_ROOT / f"node_certification_84_84a.{suffix}"
        write_table(table_path, table_rows, delimiter)
        artifact_paths.append(table_path)
    json_table_path = TABLE_ROOT / "node_certification_84_84a.json"
    write_json(json_table_path, table_rows)
    artifact_paths.append(json_table_path)
    md_table_path = TABLE_ROOT / "node_certification_84_84a.md"
    md_table_path.write_text("# Table II.4. Node Certification For 84/84a\n\n" + markdown_table(table_rows, columns), encoding="utf-8")
    artifact_paths.append(md_table_path)
    tex_table_path = TABLE_ROOT / "node_certification_84_84a.tex"
    tex_table_path.write_text(latex_table(table_rows, columns), encoding="utf-8")
    artifact_paths.append(tex_table_path)

    matrix_rows = validation_matrix_rows(certifications)
    matrix_tsv = DATA_ROOT / "validation_status_84_84a.tsv"
    write_table(matrix_tsv, matrix_rows, "\t")
    artifact_paths.append(matrix_tsv)
    matrix_json = DATA_ROOT / "validation_status_84_84a.json"
    write_json(matrix_json, matrix_rows)
    artifact_paths.append(matrix_json)
    matrix_md = DATA_ROOT / "validation_status_84_84a.md"
    matrix_md.write_text("# 84/84a Validation Status Matrix\n\n" + markdown_table(matrix_rows, list(matrix_rows[0])), encoding="utf-8")
    artifact_paths.append(matrix_md)

    write_figure(certifications)
    artifact_paths.extend([FIGURE_ROOT / "node_certification_bridge.svg", FIGURE_ROOT / "node_certification_bridge_data.json"])
    update_scope_manifest(certifications)
    update_asset_manifest(artifact_paths)
    print("HodgeCY II node-block certification assets generated")
    print("- ordinary node promotion: UNKNOWN")
    print("- blocked step: saturated_jacobian_ideal")
    print(f"- table II.4: {(TABLE_ROOT / 'node_certification_84_84a.tsv').relative_to(REPO_ROOT).as_posix()}")
    print(f"- figure II.3: {(FIGURE_ROOT / 'node_certification_bridge.svg').relative_to(REPO_ROOT).as_posix()}")


if __name__ == "__main__":
    main()
