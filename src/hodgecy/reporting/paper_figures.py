"""Paper-ready figures for the HodgeCY Paper 1 draft."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from hodgecy.arrangements import build_concurrency_graph
from hodgecy.datasets.cynk_meyer import load_table1
from hodgecy.reporting.paper_tables import ensure_output_dirs


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _save_figure(fig, stem: str) -> None:
    paths = ensure_output_dirs()
    png_path = paths["paper_figures"] / f"{stem}.png"
    pdf_path = paths["paper_figures"] / f"{stem}.pdf"
    fig.savefig(png_path, dpi=200, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)


def plot_hodge_scatter() -> None:
    paths = ensure_output_dirs()
    df = load_table1()
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(df["h12"], df["h11"], color="#2f6b8a", alpha=0.85)
    highlights = {"83", "84", "84a", "2", "43", "61", "85"}
    for _, row in df.iterrows():
        label = str(row["arrangement"])
        if label in highlights:
            ax.annotate(label, (row["h12"], row["h11"]), textcoords="offset points", xytext=(4, 4), fontsize=8)
    ax.set_xlabel("h12")
    ax.set_ylabel("h11")
    ax.set_title("Cynk--Meyer double octics by Hodge numbers")
    ax.grid(alpha=0.2)
    _save_figure(fig, "fig_hodge_scatter")
    metadata = {
        "title": "Cynk--Meyer double octics by Hodge numbers",
        "point_count": int(len(df)),
        "highlighted_arrangements": sorted(highlights & set(df["arrangement"].astype(str))),
    }
    (paths["processed_figures"] / "fig_hodge_scatter_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def plot_same_hodge_cluster_sizes() -> None:
    paths = ensure_output_dirs()
    df = load_table1()
    cluster_sizes = (
        df.groupby(["h12", "h11"], dropna=False)
        .size()
        .reset_index(name="cluster_size")
        .loc[lambda frame: frame["cluster_size"] >= 2]
        .sort_values(["cluster_size", "h12", "h11"], ascending=[False, True, True])
    )
    labels = [f"({row.h12},{row.h11})" for row in cluster_sizes.itertuples()]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(labels, cluster_sizes["cluster_size"], color="#b85c38")
    if {"3", "51"}:
        for index, row in cluster_sizes.reset_index(drop=True).iterrows():
            if row["h12"] == 3 and row["h11"] == 51:
                ax.annotate("12,15,20,29,44", (index, row["cluster_size"]), textcoords="offset points", xytext=(0, 6), ha="center", fontsize=8)
    ax.set_xlabel("Hodge pair")
    ax.set_ylabel("Cluster size")
    ax.set_title("Repeated Hodge-number profiles in the Cynk--Meyer dataset")
    ax.tick_params(axis="x", rotation=45)
    _save_figure(fig, "fig_same_hodge_cluster_sizes")


def plot_smoothing_bridge_schematic() -> None:
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.axis("off")
    boxes = [
        (0.08, 0.5, "Eight-plane\narrangement source"),
        (0.42, 0.5, "28 double lines"),
        (0.76, 0.5, "4 nodes per line\n= 112 expected nodes"),
    ]
    for x, y, text in boxes:
        ax.text(x, y, text, ha="center", va="center", fontsize=11, bbox=dict(boxstyle="round,pad=0.5", fc="#f4f1ea", ec="#444"))
    ax.annotate("", xy=(0.32, 0.5), xytext=(0.18, 0.5), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.annotate("", xy=(0.66, 0.5), xytext=(0.52, 0.5), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.text(0.5, 0.86, r"$F_{\epsilon} = \prod(P_i) + \epsilon Q^2$", ha="center", fontsize=13)
    ax.text(0.5, 0.18, "Generic Q avoids multiple points and meets double lines transversely", ha="center", fontsize=9)
    ax.text(0.5, 0.09, "Node verification and defect computation remain queued", ha="center", fontsize=9)
    _save_figure(fig, "fig_smoothing_bridge_schematic")


def plot_concurrency_graphs_84_84a() -> None:
    paths = ensure_output_dirs()
    root = _repo_root()
    try:
        import networkx as nx
    except ImportError:
        (paths["processed_figures"] / "concurrency_graphs_skipped.json").write_text(
            json.dumps({"reason": "networkx unavailable"}, indent=2),
            encoding="utf-8",
        )
        return

    profile_paths = {
        "84": root / "data" / "processed" / "concurrency_profile_84.json",
        "84a": root / "data" / "processed" / "concurrency_profile_84a.json",
    }
    if not all(path.exists() for path in profile_paths.values()):
        (paths["processed_figures"] / "concurrency_graphs_skipped.json").write_text(
            json.dumps({"reason": "concurrency profiles missing"}, indent=2),
            encoding="utf-8",
        )
        return

    from hodgecy.arrangements.concurrency import ArrangementConcurrencyProfile, DoubleLine, MultiplePoint

    colors = {"plane": "#3b6ba5", "double_line": "#d17c28", "p3": "#4c9a5f", "p4": "#a73d5c", "p5": "#6a4c93"}
    for arrangement_id, path in profile_paths.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        profile = ArrangementConcurrencyProfile(
            arrangement_id=payload["arrangement_id"],
            plane_count=payload["plane_count"],
            double_line_count=payload["double_line_count"],
            multiple_point_count_by_multiplicity={int(key): value for key, value in payload["multiple_point_count_by_multiplicity"].items()},
            line_profile_counts=payload["line_profile_counts"],
            p3_count=payload["p3_count"],
            p4_count=payload["p4_count"],
            p5_count=payload["p5_count"],
            p4_collinearity_degree_sequence=payload["p4_collinearity_degree_sequence"],
            p4_collinearity_edge_count=payload["p4_collinearity_edge_count"],
            p3_p4_collinear_pair_count=payload["p3_p4_collinear_pair_count"],
            status=payload["status"],
            multiple_points=[MultiplePoint(**point) for point in payload["multiple_points"]],
            double_lines=[DoubleLine(**line) for line in payload["double_lines"]],
            notes=payload.get("notes"),
        )
        graph = build_concurrency_graph(profile)
        fig, ax = plt.subplots(figsize=(10, 8))
        pos = nx.spring_layout(graph, seed=42)
        node_colors = [colors.get(graph.nodes[node]["type"], "#999999") for node in graph.nodes]
        nx.draw_networkx(graph, pos=pos, ax=ax, node_size=120, font_size=6, with_labels=False, node_color=node_colors, edge_color="#bbbbbb")
        ax.set_title(f"Concurrency graph for arrangement {arrangement_id}")
        ax.axis("off")
        _save_figure(fig, f"fig_concurrency_graph_{arrangement_id}")


def plot_hodgecy_pipeline() -> None:
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.axis("off")
    steps = [
        "Cynk--Meyer dataset",
        "Arrangement / Hodge / arithmetic controls",
        r"Smoothing bridge $F_{\epsilon} = A + \epsilon Q^2$",
        "Expected nodal double octic conifold",
        "Node scheme defect computation",
        "HodgeCY atom profile",
        "Operator / Picard--Fuchs route comparison",
    ]
    ys = list(reversed([0.1 + index * 0.12 for index in range(len(steps))]))
    for y, label in zip(ys, steps):
        ax.text(0.5, y, label, ha="center", va="center", fontsize=11, bbox=dict(boxstyle="round,pad=0.4", fc="#f7f5ef", ec="#555"))
    for top, bottom in zip(ys, ys[1:]):
        ax.annotate("", xy=(0.5, bottom + 0.05), xytext=(0.5, top - 0.05), arrowprops=dict(arrowstyle="->", lw=1.5))
    _save_figure(fig, "fig_hodgecy_pipeline")
