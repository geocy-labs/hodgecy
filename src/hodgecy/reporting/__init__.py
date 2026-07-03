"""Paper-facing reporting utilities for HodgeCY."""

from .paper_figures import (
    plot_concurrency_graphs_84_84a,
    plot_hodge_scatter,
    plot_hodgecy_pipeline,
    plot_same_hodge_cluster_sizes,
    plot_smoothing_bridge_schematic,
)
from .paper_tables import (
    build_concurrency_comparison_table,
    build_defect_queue_table,
    build_same_hodge_cluster_table,
    build_smoothing_bridge_table,
    build_tier_a_control_table,
)

__all__ = [
    "build_concurrency_comparison_table",
    "build_defect_queue_table",
    "build_same_hodge_cluster_table",
    "build_smoothing_bridge_table",
    "build_tier_a_control_table",
    "plot_concurrency_graphs_84_84a",
    "plot_hodge_scatter",
    "plot_hodgecy_pipeline",
    "plot_same_hodge_cluster_sizes",
    "plot_smoothing_bridge_schematic",
]
