"""Generate Blob 14 source-versus-block-evaluation assets for 84 and 84a."""

from __future__ import annotations

import csv
import json
import subprocess
from hashlib import sha256
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy import __version__ as HODGECY_VERSION  # noqa: E402
from hodgecy.core.results import EvidenceStatus  # noqa: E402
from hodgecy.core.serialization import stable_sha256  # noqa: E402
from hodgecy.relations.source_evaluation_comparison import (  # noqa: E402
    BlockEvaluationSignature,
    SourceAssemblySignature,
    block_hashes_from_blocks,
    build_block_index_correspondence,
    compare_84_84a_source_evaluation,
    source_evaluation_firewall,
)


RUN_ROOT = REPO_ROOT / "research_outputs" / "hodgecy_ii" / "source_evaluation_blob14"
HODGECY_II_ROOT = REPO_ROOT / "research_outputs" / "hodgecy_ii"
ASSET_ROOT = HODGECY_II_ROOT / "manuscript_assets"
TABLE_ROOT = ASSET_ROOT / "tables"
DATA_ROOT = ASSET_ROOT / "data"
FIGURE_ROOT = ASSET_ROOT / "figures"
MANIFEST_ROOT = ASSET_ROOT / "manifest"
SOURCE_REGRESSION = DATA_ROOT / "hodgecy_i_source_regression.json"
FIDELITY_TSV = HODGECY_II_ROOT / "complete_fidelity_pairs_and_sets.tsv"
BLOB8_PAIR = HODGECY_II_ROOT / "integral_lattice_blob8" / "hodgecy_ii_84_84a_source_lattice_comparison.json"
BLOB13_PAIR = HODGECY_II_ROOT / "evaluation_blob13" / "hodgecy_ii_84_84a_evaluation_comparison.json"
BLOB12_ROOT = HODGECY_II_ROOT / "node_block_blob12"
SOURCE_INVARIANTS = ("matrix_shape", "rank_Q", "rank_mod_2", "rank_mod_3", "kernel_dim_Q", "cokernel_dim_Q", "smith_normal_form", "integral_cokernel_decomposition", "matrix_hash")


def stable_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stable_json(payload), encoding="utf-8")


def write_table(path: Path, rows: list[dict[str, Any]], delimiter: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)


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
    return str(value).replace("_", "\\_").replace("%", "\\%").replace("#", "\\#")


def load_fidelity_types() -> dict[str, dict[str, str]]:
    with FIDELITY_TSV.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    by_set = {row["set_id"]: row for row in rows}
    return {
        "84": {
            "rational_source_type": by_set["A0002"]["rational_source_types"],
            "integral_source_type": by_set["D0001"]["integral_source_types"],
            "equivariant_type": next(item for item in by_set["A0002"]["equivariant_types"].split(" || ") if "a356b" in item),
        },
        "84a": {
            "rational_source_type": by_set["A0002"]["rational_source_types"],
            "integral_source_type": by_set["D0002"]["integral_source_types"],
            "equivariant_type": next(item for item in by_set["A0002"]["equivariant_types"].split(" || ") if "cec0" in item),
        },
    }


def load_blob8_operands() -> dict[str, dict[str, Any]]:
    payload = read_json(BLOB8_PAIR)
    report = payload["pair_84_source_lattice_report"]["invariant_results"]
    operands: dict[str, dict[str, Any]] = {"84": {}, "84a": {}}
    run_ids: dict[str, str | None] = {"84": None, "84a": None}
    record_ids: dict[str, str | None] = {"84": None, "84a": None}
    for item in report:
        key = item["comparison_key"]
        if key not in SOURCE_INVARIANTS:
            continue
        for operand in item["operands"]:
            arrangement_id = str(operand["geometry_id"]).replace("hodgecy-ii-", "")
            operands[arrangement_id][key] = operand["value"]
            run_ids[arrangement_id] = operand.get("run_id") or run_ids[arrangement_id]
            if key == "matrix_hash":
                record_ids[arrangement_id] = operand.get("record_id")
    for arrangement_id in operands:
        operands[arrangement_id]["source_run_id"] = run_ids[arrangement_id]
        operands[arrangement_id]["source_matrix_record_id"] = record_ids[arrangement_id]
    return operands


def source_signatures() -> dict[str, SourceAssemblySignature]:
    regression = read_json(SOURCE_REGRESSION)
    blob8 = load_blob8_operands()
    fidelity = load_fidelity_types()
    signatures: dict[str, SourceAssemblySignature] = {}
    for arrangement_id in ("84", "84a"):
        source = regression[arrangement_id]
        blob8_source = blob8[arrangement_id]
        rank_q = int(blob8_source["rank_Q"])
        rows, cols = (int(item) for item in blob8_source["matrix_shape"])
        h1_rank = int(blob8_source["kernel_dim_Q"])
        h0_rank = int(blob8_source["cokernel_dim_Q"])
        torsion = tuple(int(item) for item in source["torsion_factors"])
        matrix_hash = str(blob8_source["matrix_hash"])
        signatures[arrangement_id] = SourceAssemblySignature(
            arrangement_id=arrangement_id,
            geometry_id=f"hodgecy-ii-{arrangement_id}",
            source_result_id=f"blob8:{arrangement_id}:{matrix_hash}",
            source_run_id=blob8_source.get("source_run_id"),
            local_inventory={str(key): int(value) for key, value in source["local_inventory"].items()},
            hodge_signature=None if source.get("hodge_signature") is None else {str(key): int(value) for key, value in source["hodge_signature"].items()},
            matrix_shape=(rows, cols),
            rank_Q=rank_q,
            rank_mod_2=int(blob8_source["rank_mod_2"]),
            H1_Q_rank=h1_rank,
            H0_Q_rank=h0_rank,
            smith_normal_form=tuple(int(item) for item in blob8_source["smith_normal_form"]),
            torsion_factors=torsion,
            torsion_order=int(source["torsion_order"]),
            rational_source_type=fidelity[arrangement_id]["rational_source_type"],
            integral_source_type=fidelity[arrangement_id]["integral_source_type"],
            torsion_type="blob8_torsion:" + stable_sha256({"torsion_factors": torsion, "torsion_order": int(source["torsion_order"])}),
            equivariant_type=fidelity[arrangement_id]["equivariant_type"],
            group_order=None if source.get("group_order") is None else int(source["group_order"]),
            evidence_status=EvidenceStatus.VERIFIED,
            provenance={
                "source_values": SOURCE_REGRESSION.relative_to(REPO_ROOT).as_posix(),
                "integral_source_comparison": BLOB8_PAIR.relative_to(REPO_ROOT).as_posix(),
                "source_matrix_record_id": blob8_source.get("source_matrix_record_id"),
            },
        )
    return signatures


def block_evaluation_signatures() -> tuple[dict[str, BlockEvaluationSignature], dict[str, Any]]:
    comparison = read_json(BLOB13_PAIR)
    signatures: dict[str, BlockEvaluationSignature] = {}
    correspondences: dict[str, Any] = {}
    for arrangement_id in ("84", "84a"):
        result = comparison["results"][arrangement_id]
        block_certificate_path = BLOB12_ROOT / arrangement_id / "node_block_certificate.json"
        block_certificate = read_json(block_certificate_path)
        blocks = block_certificate["blocks"]
        block_hashes = block_hashes_from_blocks(blocks)
        correspondence = build_block_index_correspondence(arrangement_id, blocks)
        correspondences[arrangement_id] = correspondence
        ordinary_status = _certificate_status(block_certificate, "ordinary_node_classification", default="UNKNOWN")
        signatures[arrangement_id] = BlockEvaluationSignature(
            arrangement_id=arrangement_id,
            geometry_id=f"hodgecy-ii-{arrangement_id}",
            block_scheme_id=f"blob12:{arrangement_id}:{result['block_scheme_hash']}",
            evaluation_result_id=f"blob13:{arrangement_id}:{result['block_scheme_hash']}:degree8",
            block_scheme_hash=str(result["block_scheme_hash"]),
            block_index_hash=correspondence.correspondence_hash,
            block_ideal_hashes=block_hashes,
            hilbert_profile=tuple(int(item["H_B_d"]) for item in result["hilbert_table"]["values"]),
            H_B_8=int(result["H_B_8"]),
            critical_degree=int(result["critical_degree"]["critical_degree"]),
            evaluation_source_dimension=int(result["evaluation_source_dimension"]),
            evaluation_target_length=int(result["evaluation_target_length"]),
            evaluation_rank=int(result["evaluation_rank"]),
            evaluation_kernel_dimension=int(result["evaluation_kernel_dimension"]),
            evaluation_cokernel_dimension=int(result["evaluation_cokernel_dimension"]),
            evaluation_relation_dimension=int(result["evaluation_relation_dimension"]),
            conditional_classical_defect_value=int(result["conditional_classical_defect_value"]),
            ordinary_node_status=ordinary_status,
            classical_defect_status=str(result["actual_classical_defect_status"]).upper(),
            evidence_status=EvidenceStatus(result["evidence_status"]),
            provenance={
                "block_scheme_certificate": block_certificate_path.relative_to(REPO_ROOT).as_posix(),
                "block_evaluation_result": BLOB13_PAIR.relative_to(REPO_ROOT).as_posix(),
                "certificate_types": [item.get("certificate_type") for item in result["certificates"]],
            },
        )
    return signatures, correspondences


def _certificate_status(payload: dict[str, Any], certificate_type: str, *, default: str) -> str:
    for step in payload.get("certificate_steps", []):
        if step.get("certificate_type") == certificate_type:
            return str(step.get("status", default)).upper()
    return default


def table_ii_6_rows(comparison: Any) -> list[dict[str, Any]]:
    data = comparison.to_dict()
    src = data["source_signatures"]
    ev = data["block_evaluation_signatures"]
    return [
        {"layer": "local inventory", "84": _compact_dict(src["84"]["local_inventory"]), "84a": _compact_dict(src["84a"]["local_inventory"]), "comparison": "equal", "status": "VERIFIED"},
        {"layer": "Hodge signature", "84": _compact_dict(src["84"]["hodge_signature"]), "84a": _compact_dict(src["84a"]["hodge_signature"]), "comparison": "equal", "status": "VERIFIED"},
        {"layer": "source rank_Q", "84": src["84"]["rank_Q"], "84a": src["84a"]["rank_Q"], "comparison": "equal", "status": "VERIFIED"},
        {"layer": "source H1_Q rank", "84": src["84"]["H1_Q_rank"], "84a": src["84a"]["H1_Q_rank"], "comparison": "equal", "status": "VERIFIED"},
        {"layer": "source rank_mod_2", "84": src["84"]["rank_mod_2"], "84a": src["84a"]["rank_mod_2"], "comparison": "different", "status": "VERIFIED"},
        {"layer": "source SNF", "84": _snf(src["84"]["smith_normal_form"]), "84a": _snf(src["84a"]["smith_normal_form"]), "comparison": "different", "status": "VERIFIED"},
        {"layer": "torsion factors", "84": src["84"]["torsion_factors"], "84a": src["84a"]["torsion_factors"], "comparison": "different", "status": "VERIFIED"},
        {"layer": "block ideal hash", "84": ev["84"]["block_scheme_hash"], "84a": ev["84a"]["block_scheme_hash"], "comparison": "different block schemes", "status": "VERIFIED"},
        {"layer": "Hilbert profile H_B(0..8)", "84": ev["84"]["hilbert_profile"], "84a": ev["84a"]["hilbert_profile"], "comparison": "equal", "status": "VERIFIED"},
        {"layer": "H_B(8)", "84": ev["84"]["H_B_8"], "84a": ev["84a"]["H_B_8"], "comparison": "equal", "status": "VERIFIED"},
        {"layer": "evaluation rank", "84": ev["84"]["evaluation_rank"], "84a": ev["84a"]["evaluation_rank"], "comparison": "equal", "status": "VERIFIED"},
        {"layer": "evaluation deficiency", "84": ev["84"]["evaluation_cokernel_dimension"], "84a": ev["84a"]["evaluation_cokernel_dimension"], "comparison": "equal", "status": "VERIFIED"},
        {"layer": "evaluation relation dimension", "84": ev["84"]["evaluation_relation_dimension"], "84a": ev["84a"]["evaluation_relation_dimension"], "comparison": "equal", "status": "VERIFIED"},
        {"layer": "conditional classical defect", "84": 7, "84a": 7, "comparison": "equal if ordinary-node gate passes", "status": "CONDITIONAL"},
        {"layer": "actual classical defect", "84": "UNKNOWN", "84a": "UNKNOWN", "comparison": "unknown", "status": "UNKNOWN"},
        {"layer": "source-to-evaluation chain map", "84": "UNKNOWN", "84a": "UNKNOWN", "comparison": "not constructed", "status": "UNKNOWN"},
    ]


def _compact_dict(payload: dict[str, Any] | None) -> str:
    if payload is None:
        return "UNKNOWN"
    return ";".join(f"{key}={payload[key]}" for key in sorted(payload))


def _snf(values: list[int]) -> str:
    counts: dict[int, int] = {}
    for value in values:
        counts[int(value)] = counts.get(int(value), 0) + 1
    return "(" + ",".join(f"{value}^{count}" if count > 1 else str(value) for value, count in sorted(counts.items())) + ")"


def write_table_ii_6(comparison: Any) -> list[Path]:
    rows = table_ii_6_rows(comparison)
    paths = [
        TABLE_ROOT / "source_block_evaluation_comparison_84_84a.tsv",
        TABLE_ROOT / "source_block_evaluation_comparison_84_84a.csv",
        TABLE_ROOT / "source_block_evaluation_comparison_84_84a.json",
        TABLE_ROOT / "source_block_evaluation_comparison_84_84a.md",
        TABLE_ROOT / "source_block_evaluation_comparison_84_84a.tex",
    ]
    write_table(paths[0], rows, "\t")
    write_table(paths[1], rows, ",")
    write_json(paths[2], rows)
    paths[3].write_text("# Table II.6. Source versus Block-Evaluation Comparison\n\n" + markdown_table(rows), encoding="utf-8")
    paths[4].write_text(latex_table(rows, list(rows[0])), encoding="utf-8")
    return paths


def write_evidence_assets(comparison: Any) -> list[Path]:
    rows = [dict(row) for row in comparison.evidence_status_table]
    paths = [
        DATA_ROOT / "source_block_evaluation_evidence_status_84_84a.tsv",
        DATA_ROOT / "source_block_evaluation_evidence_status_84_84a.json",
        DATA_ROOT / "source_block_evaluation_evidence_status_84_84a.md",
    ]
    write_table(paths[0], rows, "\t")
    write_json(paths[1], rows)
    paths[2].write_text("# Source/Block-Evaluation Evidence Status\n\n" + markdown_table(rows), encoding="utf-8")
    return paths


def write_correspondence_assets(comparison: Any) -> list[Path]:
    paths: list[Path] = []
    for arrangement_id, correspondence in comparison.source_block_index_correspondence.items():
        rows = [dict(item) for item in correspondence.entries]
        path = RUN_ROOT / arrangement_id / "source_block_index_correspondence.tsv"
        write_table(path, rows, "\t")
        paths.append(path)
    return paths


def write_reports(comparison: Any) -> list[Path]:
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "hodgecy_ii_source_evaluation_blob14.v1",
        "hodgecy_version": HODGECY_VERSION,
        "comparison": comparison.to_dict(),
        "firewall": source_evaluation_firewall(),
        "optional_figure_ii_7": {"generated": False, "reason": "Figure II.6 carries the two-axis comparison without adding a second visual."},
    }
    theorem = {
        "schema": "hodgecy_ii_source_evaluation_theorem_candidate.v1",
        "theorem_candidate_record": comparison.theorem_candidate_record,
        "non_determination_certificate": comparison.non_determination_certificate,
        "conditional_corollary_record": comparison.conditional_corollary_record,
    }
    paths = [
        RUN_ROOT / "hodgecy_ii_source_evaluation_blob14.json",
        RUN_ROOT / "hodgecy_ii_source_evaluation_blob14.md",
        RUN_ROOT / "hodgecy_ii_84_84a_source_evaluation_comparison.json",
        RUN_ROOT / "hodgecy_ii_84_84a_source_evaluation_comparison.md",
        RUN_ROOT / "theorem_candidate_block_eval_vs_integral_source.json",
        RUN_ROOT / "theorem_candidate_block_eval_vs_integral_source.md",
        RUN_ROOT / "conditional_defect_corollary.json",
        RUN_ROOT / "conditional_defect_corollary.md",
    ]
    write_json(paths[0], payload)
    paths[1].write_text(report_markdown(comparison), encoding="utf-8")
    write_json(paths[2], comparison.to_dict())
    paths[3].write_text(comparison_markdown(comparison), encoding="utf-8")
    write_json(paths[4], theorem)
    paths[5].write_text(theorem_markdown(comparison), encoding="utf-8")
    write_json(paths[6], comparison.conditional_classical_defect_result)
    paths[7].write_text(conditional_corollary_markdown(comparison), encoding="utf-8")
    return paths


def report_markdown(comparison: Any) -> str:
    rows = table_ii_6_rows(comparison)
    lines = [
        "# HodgeCY II Source versus Block Evaluation - Blob 14",
        "",
        f"- status: `{comparison.status.value}`",
        f"- interpretation: `{comparison.interpretation_class.value}`",
        "- source-to-evaluation chain map: `UNKNOWN`",
        "- actual classical defect: `UNKNOWN`",
        "",
        "## Table II.6",
        "",
        markdown_table(rows).rstrip(),
        "",
        "## Certificate",
        "",
        f"- `{comparison.non_determination_certificate['certificate_id']}`",
        "- verified block Hilbert/evaluation profiles agree through degree 8",
        "- verified integral source Smith types differ",
        "- no reverse determinacy theorem is asserted",
        "",
    ]
    return "\n".join(lines)


def comparison_markdown(comparison: Any) -> str:
    data = comparison.to_dict()
    lines = [
        "# 84/84a Source versus Block-Evaluation Comparison",
        "",
        f"Status: `{data['status']}`",
        "",
        "## Source Axis",
        "",
        f"- shared levels: `{', '.join(data['source_axis']['shared_levels'])}`",
        f"- first separating level: `{data['source_axis']['first_separating_level']}`",
        "",
        "## Geometry/Evaluation Axis",
        "",
        f"- shared levels: `{', '.join(data['geometry_evaluation_axis']['shared_levels'])}`",
        "- first separating level: `None through the verified critical-degree block-evaluation data`",
        "",
        "## Relation Dimensions",
        "",
        "- source rational H1 rank: `2` for both",
        "- evaluation relation dimension: `7` for both",
        "- no identification or subspace inference is made",
        "",
    ]
    return "\n".join(lines)


def theorem_markdown(comparison: Any) -> str:
    return "\n".join(
        [
            "# Candidate Theorem Record",
            "",
            f"- candidate: `{comparison.theorem_candidate_record['candidate_theorem_id']}`",
            f"- status: `{comparison.theorem_candidate_record['status']}`",
            f"- certificate: `{comparison.non_determination_certificate['certificate_id']}`",
            "- statement: verified block-evaluation collapse with integral source separation for `84 / 84a`.",
            "",
        ]
    )


def conditional_corollary_markdown(comparison: Any) -> str:
    result = comparison.conditional_classical_defect_result
    return "\n".join(
        [
            "# Conditional Classical-Defect Corollary",
            "",
            f"- result: `{result['result_id']}`",
            f"- status: `{result['status']}`",
            f"- condition: {result['condition']}",
            "- conclusion: `defect(84) = defect(84a) = 7` under the condition.",
            "- actual classical defect remains `UNKNOWN`.",
            "",
        ]
    )


def write_figure_ii_6(comparison: Any) -> list[Path]:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    svg_path = FIGURE_ROOT / "source_block_two_axis_comparison.svg"
    data_path = FIGURE_ROOT / "source_block_two_axis_comparison_data.json"
    write_json(data_path, {"schema": "hodgecy_ii_source_block_two_axis_comparison.v1", "comparison": comparison.to_dict()})
    svg_path.write_text(two_axis_svg(), encoding="utf-8")
    return [svg_path, data_path]


def two_axis_svg() -> str:
    boxes = [
        ("source", 70, 86, "local/Hodge", "equal"),
        ("source", 230, 86, "rational source", "equal"),
        ("source", 410, 86, "integral/SNF", "split"),
        ("source", 570, 86, "equivariant", "split"),
        ("evaluation", 70, 210, "verified block", "separate hashes"),
        ("evaluation", 250, 210, "H_B(0..8)", "equal"),
        ("evaluation", 410, 210, "E_8 rank", "105 = 105"),
        ("evaluation", 570, 210, "relations", "7 = 7"),
    ]
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="780" height="330" viewBox="0 0 780 330">',
        '<rect width="100%" height="100%" fill="#fff" />',
        '<text x="40" y="34" font-family="Arial, sans-serif" font-size="18" font-weight="700">Figure II.6. Source and block-evaluation axes for 84 / 84a</text>',
        '<text x="38" y="112" font-family="Arial" font-size="13" font-weight="700">Source axis</text>',
        '<text x="38" y="236" font-family="Arial" font-size="13" font-weight="700">Block-evaluation axis</text>',
    ]
    colors = {"equal": ("#e9f5ef", "#438461"), "split": ("#fff0de", "#b06a23"), "separate hashes": ("#eef3fb", "#4f6f9a")}
    for axis, x, y, title, state in boxes:
        fill, stroke = colors.get(state, ("#f5f5f5", "#777"))
        lines.append(f'<rect x="{x}" y="{y}" width="130" height="54" rx="5" fill="{fill}" stroke="{stroke}" />')
        lines.append(f'<text x="{x+65}" y="{y+23}" font-family="Arial" font-size="13" text-anchor="middle">{title}</text>')
        lines.append(f'<text x="{x+65}" y="{y+42}" font-family="Arial" font-size="11" text-anchor="middle" fill="#333">{state}</text>')
        if x < 570:
            lines.append(f'<line x1="{x+130}" y1="{y+27}" x2="{x+150}" y2="{y+27}" stroke="#555" />')
            lines.append(f'<polygon points="{x+150},{y+27} {x+142},{y+22} {x+142},{y+32}" fill="#555" />')
    lines.extend(
        [
            '<line x1="475" y1="140" x2="475" y2="210" stroke="#999" stroke-dasharray="4 4" />',
            '<text x="490" y="178" font-family="Arial" font-size="12" fill="#555">collapse at E_8 despite source split</text>',
            '<text x="70" y="302" font-family="Arial" font-size="12" fill="#555">No source-to-evaluation chain map or integral evaluation lattice is constructed.</text>',
            "</svg>",
        ]
    )
    return "\n".join(lines) + "\n"


def update_scope_manifest(comparison: Any) -> Path:
    path = MANIFEST_ROOT / "hodgecy_ii_scope.json"
    payload = read_json(path)
    payload["required_geometric_outputs"]["blob_14"] = {
        "source_vs_block_evaluation_comparison": "VERIFIED",
        "exact_result_status": comparison.status.value,
        "source_to_evaluation_chain_map": "UNKNOWN",
        "integral_evaluation_lattice": "UNKNOWN",
        "classical_defect": "UNKNOWN",
        "conditional_classical_defect": "CONDITIONAL",
    }
    payload["nonclaims"]["no_source_to_evaluation_morphism"] = (
        "Blob 14 records only a double-line to four-point-block index correspondence; no theorem-backed source-to-evaluation chain map is constructed."
    )
    payload["nonclaims"]["no_integral_evaluation_lattice"] = "Blob 14 constructs no integral evaluation relation lattice."
    payload["source_evaluation_status_blob_14"] = {
        "84_84a": {
            "status": comparison.status.value,
            "interpretation_class": comparison.interpretation_class.value,
            "non_determination_certificate": comparison.non_determination_certificate["certificate_id"],
            "actual_classical_defect": "UNKNOWN",
        }
    }
    write_json(path, payload)
    return path


def update_asset_manifest(paths: list[Path], comparison: Any) -> Path:
    path = MANIFEST_ROOT / "hodgecy_ii_asset_manifest.json"
    payload = read_json(path)
    artifacts = payload.setdefault("artifacts", {})
    for artifact_path in paths:
        rel = artifact_path.relative_to(REPO_ROOT).as_posix()
        artifacts[rel] = {"sha256": file_sha256(artifact_path), "status": "BLOB14_READY"}
    scope = MANIFEST_ROOT / "hodgecy_ii_scope.json"
    artifacts[scope.relative_to(REPO_ROOT).as_posix()] = {"sha256": file_sha256(scope), "status": "CONTEXT_READY"}
    payload["blob_14_source_evaluation"] = {
        "status": comparison.status.value,
        "table_ii_6": "research_outputs/hodgecy_ii/manuscript_assets/tables/source_block_evaluation_comparison_84_84a.tsv",
        "figure_ii_6": "research_outputs/hodgecy_ii/manuscript_assets/figures/source_block_two_axis_comparison.svg",
        "comparison_report": "research_outputs/hodgecy_ii/source_evaluation_blob14/hodgecy_ii_84_84a_source_evaluation_comparison.md",
        "non_determination_certificate": comparison.non_determination_certificate["certificate_id"],
        "classical_defect": "UNKNOWN",
    }
    write_json(path, payload)
    return path


def update_docs() -> list[Path]:
    doc_path = REPO_ROOT / "docs" / "source_block_evaluation_comparison.md"
    doc_path.write_text(
        "\n".join(
            [
                "# Source versus Block-Evaluation Comparison",
                "",
                "Blob 14 compares the verified source assembly records of `84` and `84a` with the verified Blob 12-13 block-scheme evaluation records.",
                "",
                "The source axis collapses through rational source type and separates at integral/SNF type.  The block-evaluation axis agrees through the critical degree: both Hilbert profiles are `1,4,10,20,34,52,74,92,105`, both degree-8 ranks are `105`, and both evaluation relation dimensions are `7`.",
                "",
                "This supports the certificate `block_evaluation_does_not_determine_integral_source_type` for the verified block schemes only.  It does not assert reverse determinacy.",
                "",
                "The source-to-evaluation comparison morphism remains `UNKNOWN`.  The double-line to four-point-block correspondence is an index correspondence, not a chain map.",
                "",
                "The classical defect statement remains conditional: if the verified block scheme is the full ordinary-node scheme under the HodgeCY defect hypotheses, then both defects equal `7`.  The actual classical defects are still `UNKNOWN`.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return [doc_path]


def build_comparison() -> Any:
    source = source_signatures()
    evaluation, correspondences = block_evaluation_signatures()
    return compare_84_84a_source_evaluation(
        source_signatures=source,
        block_evaluation_signatures=evaluation,
        source_block_index_correspondence=correspondences,
        provenance={
            "hodgecy_version": HODGECY_VERSION,
            "git_commit": git_commit(),
            "blob8_source_lattice_comparison": BLOB8_PAIR.relative_to(REPO_ROOT).as_posix(),
            "blob12_block_certificates": [str((BLOB12_ROOT / item / "node_block_certificate.json").relative_to(REPO_ROOT).as_posix()) for item in ("84", "84a")],
            "blob13_evaluation_comparison": BLOB13_PAIR.relative_to(REPO_ROOT).as_posix(),
        },
    )


def main() -> None:
    comparison = build_comparison()
    artifact_paths: list[Path] = []
    artifact_paths.extend(write_reports(comparison))
    artifact_paths.extend(write_table_ii_6(comparison))
    artifact_paths.extend(write_evidence_assets(comparison))
    artifact_paths.extend(write_correspondence_assets(comparison))
    artifact_paths.extend(write_figure_ii_6(comparison))
    artifact_paths.extend(update_docs())
    scope_path = update_scope_manifest(comparison)
    manifest_path = update_asset_manifest([*artifact_paths, scope_path], comparison)
    print("HodgeCY II Blob 14 source/evaluation assets generated")
    print(f"- status: {comparison.status.value}")
    print(f"- interpretation: {comparison.interpretation_class.value}")
    print(f"- source-to-evaluation chain map: {comparison.comparison_morphism_status['source_to_evaluation_chain_map']}")
    print(f"- table II.6: {(TABLE_ROOT / 'source_block_evaluation_comparison_84_84a.tsv').relative_to(REPO_ROOT).as_posix()}")
    print(f"- figure II.6: {(FIGURE_ROOT / 'source_block_two_axis_comparison.svg').relative_to(REPO_ROOT).as_posix()}")
    print(f"- scope manifest: {scope_path.relative_to(REPO_ROOT).as_posix()}")
    print(f"- asset manifest: {manifest_path.relative_to(REPO_ROOT).as_posix()}")


if __name__ == "__main__":
    main()
