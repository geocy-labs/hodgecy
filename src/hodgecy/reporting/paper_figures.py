"""Paper-ready figures for the HodgeCY Paper 1 draft."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch
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
    fig, ax = plt.subplots(figsize=(10.8, 2.7))
    ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    boxes = [
        (0.12, "Eight-plane\narrangement"),
        (0.37, "28 double lines"),
        (0.62, "28 four-point blocks"),
        (0.87, r"$\deg \Sigma = 112$"),
    ]
    box_width = 0.18
    box_height = 0.25
    box_y = 0.57
    for center_x, text in boxes:
        left = center_x - box_width / 2
        bottom = box_y - box_height / 2
        patch = FancyBboxPatch(
            (left, bottom),
            box_width,
            box_height,
            boxstyle="round,pad=0.02,rounding_size=0.025",
            linewidth=1.0,
            edgecolor="#333333",
            facecolor="white",
        )
        ax.add_patch(patch)
        ax.text(center_x, box_y, text, ha="center", va="center", fontsize=10.5, color="#111111")

    for (left_x, _), (right_x, _) in zip(boxes, boxes[1:]):
        ax.annotate(
            "",
            xy=(right_x - box_width / 2 - 0.006, box_y),
            xytext=(left_x + box_width / 2 + 0.006, box_y),
            arrowprops=dict(arrowstyle="->", lw=1.2, color="#333333"),
        )

    status = "Degree 112 certified; global support, reducedness, and pointwise node\ncertificates pending."
    ax.text(0.5, 0.22, status, ha="center", va="center", fontsize=9.5, color="#222222", linespacing=1.3)
    _save_figure(fig, "fig_smoothing_bridge_schematic")
    metadata = {
        "status": "degree112_certified",
        "boxes": [text for _, text in boxes],
        "status_text": "Degree 112 certified; global support, reducedness, and pointwise node certificates pending.",
        "style": "four-stage left-to-right chain",
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
