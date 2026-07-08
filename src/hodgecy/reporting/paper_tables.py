"""Paper-ready tables for the HodgeCY Paper 1 draft."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from hodgecy.arrangements import arrangement_84, arrangement_84a, build_concurrency_profile, p4_collinearity_certificate_rows
from hodgecy.datasets.cynk_meyer import load_table1
from hodgecy.defects import build_smoothing_bridge_defect_queue
from hodgecy.smoothing.bridge import QuarticPerturbation, profile_to_dict, smoothing_bridge_profile


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def ensure_output_dirs() -> dict[str, Path]:
    root = _repo_root()
    paths = {
        "paper_tables": root / "paper" / "tables",
        "paper_figures": root / "paper" / "figures",
        "processed_tables": root / "data" / "processed" / "paper_tables",
        "processed_figures": root / "data" / "processed" / "paper_figures",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _write_table_bundle(df: pd.DataFrame, csv_path: Path, tex_path: Path, json_path: Path) -> pd.DataFrame:
    df.to_csv(csv_path, index=False)
    json_path.write_text(df.to_json(orient="records", indent=2), encoding="utf-8")
    tex_path.write_text(df.to_latex(index=False, escape=False), encoding="utf-8")
    return df


def build_tier_a_control_table() -> pd.DataFrame:
    paths = ensure_output_dirs()
    df = load_table1()
    rows = df.loc[df["arrangement"].astype(str).isin(["83", "84", "84a"])].copy()
    interpretations = {
        "83": "Same singularity profile as 84 but different Hodge numbers; baseline that counts do not determine Hodge data.",
        "84": "Rigid control arrangement; same numerical profile as 84a but different modular form.",
        "84a": "Rigid arithmetic-control arrangement; same numerical and Hodge profile as 84 but modular form differs.",
    }
    rows["interpretation"] = rows["arrangement"].astype(str).map(interpretations)
    columns = [
        "arrangement",
        "p3",
        "p4_0",
        "p4_1",
        "p5_0",
        "p5_1",
        "p5_2",
        "l3",
        "h12",
        "h11",
        "euler",
        "rigid",
        "modular_form",
        "hodgecy_role",
        "interpretation",
    ]
    rows = rows[columns].sort_values("arrangement", key=lambda series: series.astype(str).map({"83": 0, "84": 1, "84a": 2}))
    return _write_table_bundle(
        rows,
        paths["paper_tables"] / "table_tier_a_controls.csv",
        paths["paper_tables"] / "table_tier_a_controls.tex",
        paths["processed_tables"] / "table_tier_a_controls.json",
    )


def build_same_hodge_cluster_table(min_cluster_size=2) -> pd.DataFrame:
    paths = ensure_output_dirs()
    df = load_table1()
    grouped_rows = []
    range_columns = ["p3", "l3", "p4_0", "p4_1", "p5_0", "p5_1", "p5_2"]
    for (h12, h11), group in df.groupby(["h12", "h11"], dropna=False):
        if len(group) < min_cluster_size:
            continue
        row = {
            "h12": h12,
            "h11": h11,
            "arrangements": ", ".join(group["arrangement"].astype(str).tolist()),
            "cluster_size": len(group),
            "note": "Repeated Hodge pair across distinct arrangements.",
        }
        for column in range_columns:
            values = sorted(group[column].tolist())
            row[f"{column}_range"] = f"{values[0]}-{values[-1]}"
        grouped_rows.append(row)
    result = pd.DataFrame(grouped_rows).sort_values(["cluster_size", "h12", "h11"], ascending=[False, True, True]).reset_index(drop=True)
    return _write_table_bundle(
        result,
        paths["paper_tables"] / "table_same_hodge_clusters.csv",
        paths["paper_tables"] / "table_same_hodge_clusters.tex",
        paths["processed_tables"] / "table_same_hodge_clusters.json",
    )


def _load_smoothing_profiles() -> list[dict]:
    path = _repo_root() / "data" / "processed" / "smoothing_bridge_84_84a_profiles.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    perturbation = QuarticPerturbation(label="generic_quartic_Q", polynomial=None)
    return [
        profile_to_dict(smoothing_bridge_profile(arrangement_84(), perturbation=perturbation)),
        profile_to_dict(smoothing_bridge_profile(arrangement_84a(), perturbation=perturbation)),
    ]


def _load_smoothing_verification_records() -> dict[str, dict]:
    root = _repo_root()
    records: dict[str, dict] = {}
    for arrangement_id in ("84", "84a"):
        path = root / "data" / "processed" / f"smoothing_verification_{arrangement_id}.json"
        if path.exists():
            records[arrangement_id] = json.loads(path.read_text(encoding="utf-8"))
    return records


def _verification_status_note(record: dict) -> str:
    status = record.get("verification_status", "queued")
    if status == "defect_verified":
        return (
            "Ordinary-node certification and the defect certificate are both repo-backed: "
            "degree 112, reducedness, Hessian rank 3, and the defect/Hilbert-function claims are all certified."
        )
    if status == "ordinary_node_verified":
        return "Verified: reduced zero-dimensional singular locus of length 112; Hessian rank 3 at all singular points."
    if status == "degree112_certified":
        return (
            "degree112_certified: (G1), (G2) verified over Q; saturated Jacobian degree 112 certified; "
            "reducedness and Hessian-rank checks pending."
        )
    if status == "genericity_verified":
        return (
            "Genericity verified: explicit Q avoids all multiple points and is squarefree on all 28 double lines; "
            "global singular-locus length/reducedness/Hessian checks remain queued."
        )
    if status == "failed":
        return record.get("notes", "Verification failed for the explicit Q.")
    return "Verification queued."


def build_smoothing_bridge_table() -> pd.DataFrame:
    paths = ensure_output_dirs()
    profiles = _load_smoothing_profiles()
    verification_records = _load_smoothing_verification_records()
    queue_path = _repo_root() / "data" / "processed" / "defect_computation_queue.csv"
    if queue_path.exists():
        queue = pd.read_csv(queue_path, dtype={"example_id": str, "source_arrangement": str})
    else:
        queue = build_smoothing_bridge_defect_queue()
    queue_by_arrangement = {str(row["source_arrangement"]): row for _, row in queue.iterrows()}

    rows = []
    for profile in profiles:
        source_arrangement = str(profile["arrangement_id"])
        queue_row = queue_by_arrangement.get(source_arrangement)
        verification = verification_records.get(source_arrangement, {})
        verification_status = verification.get("verification_status", "queued")
        expected_status = verification_status
        rows.append(
            {
                "example_id": f"smoothing_bridge_{source_arrangement}",
                "source_arrangement": source_arrangement,
                "double_line_count": profile.get("number_of_double_lines"),
                "triple_line_count": profile.get("triple_line_count"),
                "expected_nodes_per_double_line": profile.get("expected_nodes_per_double_line"),
                "expected_node_count": profile.get("expected_nodes_total"),
                "expected_node_count_status": expected_status,
                "verification_status": verification_status,
                "q_avoids_all_multiple_points": verification.get("G1_avoids_multiple_points"),
                "all_double_lines_have_four_simple_zeros": verification.get("G2_squarefree_on_double_lines"),
                "block_count": profile.get("number_of_double_lines"),
                "candidate_block_profile_summary": (
                    f"{profile.get('number_of_double_lines')} blocks of size {profile.get('expected_nodes_per_double_line')}"
                    if profile.get("number_of_double_lines") is not None and profile.get("expected_nodes_per_double_line") is not None
                    else "missing"
                ),
                "gluing_deficit": (
                    profile.get("expected_nodes_total") - profile.get("number_of_double_lines")
                    if profile.get("expected_nodes_total") is not None and profile.get("number_of_double_lines") is not None
                    else None
                ),
                "defect_status": queue_row["defect_status"] if queue_row is not None else "not_computed",
                "critical_degree_status": queue_row["critical_degree_status"] if queue_row is not None else "needs_literature_verification",
                "notes": _verification_status_note(verification) if verification else profile.get("notes"),
            }
        )
    result = pd.DataFrame(rows)
    result = result.rename(
        columns={
            "expected_nodes_per_double_line": "Predicted points per line",
            "expected_node_count": "Predicted singular points",
        }
    )
    return _write_table_bundle(
        result,
        paths["paper_tables"] / "table_smoothing_bridge_profiles.csv",
        paths["paper_tables"] / "table_smoothing_bridge_profiles.tex",
        paths["processed_tables"] / "table_smoothing_bridge_profiles.json",
    )


def build_p4_collinearity_certificate_table() -> pd.DataFrame:
    paths = ensure_output_dirs()
    rows = []
    for arrangement in (arrangement_84(), arrangement_84a()):
        rows.extend(p4_collinearity_certificate_rows(build_concurrency_profile(arrangement)))
    frame = pd.DataFrame(rows)
    processed_csv = _repo_root() / "data" / "processed" / "p4_collinearity_certificate.csv"
    frame.to_csv(processed_csv, index=False)
    frame.to_csv(paths["paper_tables"] / "table_p4_collinearity_certificate.csv", index=False)

    lines = [
        r"\begin{tabularx}{\textwidth}{@{}llcX@{}}",
        r"\toprule",
        r"Arrangement & Vertex & Degree & Neighbors \\",
        r"\midrule",
    ]
    for row in frame.itertuples(index=False):
        lines.append(
            f"{row.arrangement} & {row.vertex_label} & {row.degree} & {row.neighbor_labels} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}", ""])
    (paths["paper_tables"] / "table_p4_collinearity_certificate.tex").write_text("\n".join(lines), encoding="utf-8")
    return frame


def build_concurrency_comparison_table() -> pd.DataFrame:
    paths = ensure_output_dirs()
    root = _repo_root()
    profile_paths = {
        "84": root / "data" / "processed" / "concurrency_profile_84.json",
        "84a": root / "data" / "processed" / "concurrency_profile_84a.json",
    }
    comparison_path = root / "data" / "processed" / "concurrency_comparison_84_84a.json"

    if not all(path.exists() for path in profile_paths.values()):
        result = pd.DataFrame(
            [
                {
                    "arrangement_id": "84",
                    "double_line_count": None,
                    "p3_count": None,
                    "p4_count": None,
                    "p5_count": None,
                    "p4_collinearity_edge_count": None,
                    "p3_p4_collinear_pair_count": None,
                    "line_profile_summary": "missing",
                    "colored_graph_isomorphism_status": "missing",
                    "conclusion": "Run scripts/build_concurrency_profiles_84_84a.py to generate the required profiles.",
                },
                {
                    "arrangement_id": "84a",
                    "double_line_count": None,
                    "p3_count": None,
                    "p4_count": None,
                    "p5_count": None,
                    "p4_collinearity_edge_count": None,
                    "p3_p4_collinear_pair_count": None,
                    "line_profile_summary": "missing",
                    "colored_graph_isomorphism_status": "missing",
                    "conclusion": "Run scripts/build_concurrency_profiles_84_84a.py to generate the required profiles.",
                },
            ]
        )
    else:
        comparison_payload = json.loads(comparison_path.read_text(encoding="utf-8")) if comparison_path.exists() else {}
        rows = []
        for arrangement_id, path in profile_paths.items():
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows.append(
                {
                    "arrangement_id": arrangement_id,
                    "double_line_count": payload.get("double_line_count"),
                    "p3_count": payload.get("p3_count"),
                    "p4_count": payload.get("p4_count"),
                    "p5_count": payload.get("p5_count"),
                    "p4_collinearity_edge_count": payload.get("p4_collinearity_edge_count"),
                    "p3_p4_collinear_pair_count": payload.get("p3_p4_collinear_pair_count"),
                    "line_profile_summary": "; ".join(
                        f"{entry['count']}x{entry['profile']}" for entry in payload.get("line_profile_counts", [])
                    ),
                    "colored_graph_isomorphism_status": comparison_payload.get("colored_graph_isomorphic"),
                    "conclusion": comparison_payload.get("conclusion"),
                }
            )
        result = pd.DataFrame(rows)
    return _write_table_bundle(
        result,
        paths["paper_tables"] / "table_concurrency_comparison_84_84a.csv",
        paths["paper_tables"] / "table_concurrency_comparison_84_84a.tex",
        paths["processed_tables"] / "table_concurrency_comparison_84_84a.json",
    )


def build_defect_queue_table() -> pd.DataFrame:
    paths = ensure_output_dirs()
    queue_path = _repo_root() / "data" / "processed" / "defect_computation_queue.csv"
    if queue_path.exists():
        queue = pd.read_csv(queue_path, dtype={"example_id": str, "source_arrangement": str})
    else:
        queue = build_smoothing_bridge_defect_queue()
        queue.to_csv(queue_path, index=False)
    columns = [
        "example_id",
        "source_arrangement",
        "expected_node_count",
        "critical_degree",
        "critical_degree_status",
        "defect_status",
        "required_tool",
        "priority",
        "notes",
    ]
    queue = queue[columns]
    return _write_table_bundle(
        queue,
        paths["paper_tables"] / "table_defect_queue.csv",
        paths["paper_tables"] / "table_defect_queue.tex",
        paths["processed_tables"] / "table_defect_queue.json",
    )
