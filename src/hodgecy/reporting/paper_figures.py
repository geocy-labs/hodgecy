"""Paper-ready figures for the HodgeCY Paper 1 draft."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import pandas as pd

from hodgecy.arrangements import (
    arrangement_84,
    arrangement_84a,
    build_concurrency_profile,
    build_p4_collinearity_graph,
    p4_collinearity_certificate_rows,
)
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
    paths = ensure_output_dirs()
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.axis("off")
    boxes = [
        (0.08, 0.5, "Eight-plane\narrangement source"),
        (0.42, 0.5, "28 double lines"),
        (0.76, 0.5, "4 predicted points per line\n= 112 predicted singular points"),
    ]
    for x, y, text in boxes:
        ax.text(x, y, text, ha="center", va="center", fontsize=11, bbox=dict(boxstyle="round,pad=0.5", fc="#f4f1ea", ec="#444"))
    ax.annotate("", xy=(0.32, 0.5), xytext=(0.18, 0.5), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.annotate("", xy=(0.66, 0.5), xytext=(0.52, 0.5), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.text(0.5, 0.9, r"$F_{\epsilon} = \prod(P_i) + \epsilon Q^2$", ha="center", fontsize=13)
    ax.text(0.5, 0.82, "degree112_certified for arrangements 84 and 84a", ha="center", fontsize=10)
    ax.text(0.5, 0.18, "Generic Q avoids multiple points and meets double lines transversely", ha="center", fontsize=9)
    ax.text(0.5, 0.11, "Ordinary-node verification pending", ha="center", fontsize=9)
    ax.text(0.5, 0.05, "Ordinary-node verification and defect computation remain queued", ha="center", fontsize=9)
    _save_figure(fig, "fig_smoothing_bridge_schematic")
    metadata = {
        "status": "degree112_certified",
        "boxes": [text for _, _, text in boxes],
        "top_text": r"$F_{\epsilon} = \prod(P_i) + \epsilon Q^2$",
        "status_text": "degree112_certified for arrangements 84 and 84a",
        "pending_text": "Ordinary-node verification pending",
        "queue_text": "Ordinary-node verification and defect computation remain queued",
    }
    (paths["processed_figures"] / "fig_smoothing_bridge_schematic_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )


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

    certificate_rows = []
    for arrangement in (arrangement_84(), arrangement_84a()):
        arrangement_id = arrangement.arrangement_id
        profile = build_concurrency_profile(arrangement)
        graph = build_p4_collinearity_graph(profile)
        certificate_rows.extend(p4_collinearity_certificate_rows(profile))
        fig, ax = plt.subplots(figsize=(8.0, 7.2))
        pos = nx.kamada_kawai_layout(graph)
        degrees = dict(graph.degree())
        if arrangement_id == "84":
            highlight_nodes = {node for node, degree in degrees.items() if degree == 6}
            highlight_color = "#d94841"
            subtitle = "10 vertices, 39 edges; unique degree-6 vertex highlighted"
            degree_sequence = "[6,8^9]"
        else:
            highlight_nodes = {node for node, degree in degrees.items() if degree == 9}
            highlight_color = "#7f3c8d"
            subtitle = "10 vertices, 42 edges; degree-9 vertices highlighted"
            degree_sequence = "[8^6,9^4]"
        node_colors = [highlight_color if node in highlight_nodes else "#3b6ba5" for node in graph.nodes]
        node_sizes = [520 if node in highlight_nodes else 340 for node in graph.nodes]
        nx.draw_networkx_edges(graph, pos=pos, ax=ax, edge_color="#b8b8b8", width=1.4)
        nx.draw_networkx_nodes(graph, pos=pos, ax=ax, node_size=node_sizes, node_color=node_colors, edgecolors="#222222", linewidths=0.8)
        nx.draw_networkx_labels(graph, pos=pos, ax=ax, font_size=8, font_color="white")
        legend_items = [
            Line2D([0], [0], marker="o", color="w", markerfacecolor="#3b6ba5", markeredgecolor="#222222", markersize=8, label="degree-8 p4 vertex"),
            Line2D([0], [0], marker="o", color="w", markerfacecolor=highlight_color, markeredgecolor="#222222", markersize=8, label="highlighted vertex class"),
        ]
        ax.legend(handles=legend_items, loc="upper center", bbox_to_anchor=(0.5, -0.03), ncol=2, frameon=False, fontsize=8)
        ax.set_title(f"Arrangement {arrangement_id} p4-collinearity graph\n{subtitle}; degree sequence {degree_sequence}", fontsize=11)
        ax.axis("off")
        _save_figure(fig, f"fig_concurrency_graph_{arrangement_id}")
        metadata = {
            "title": f"Arrangement {arrangement_id} p4-collinearity graph",
            "subtitle": subtitle,
            "degree_sequence": degree_sequence,
            "highlighted_nodes": sorted(highlight_nodes),
            "vertex_count": graph.number_of_nodes(),
            "edge_count": graph.number_of_edges(),
        }
        (paths["processed_figures"] / f"fig_concurrency_graph_{arrangement_id}_metadata.json").write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )

    pd.DataFrame(certificate_rows).to_csv(root / "data" / "processed" / "p4_collinearity_certificate.csv", index=False)


def plot_hodgecy_pipeline() -> None:
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.axis("off")
    steps = [
        "Cynk--Meyer dataset",
        "Arrangement / Hodge / arithmetic controls",
        r"Smoothing bridge $F_{\epsilon} = A + \epsilon Q^2$",
        "degree112_certified predicted singular points",
        "Ordinary-node verification pending",
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
