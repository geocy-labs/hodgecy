"""Generate paper-facing HodgeCY tables and figures."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.reporting import (  # noqa: E402
    build_concurrency_comparison_table,
    build_defect_queue_table,
    build_same_hodge_cluster_table,
    build_smoothing_bridge_table,
    build_tier_a_control_table,
    plot_concurrency_graphs_84_84a,
    plot_hodge_scatter,
    plot_hodgecy_pipeline,
    plot_same_hodge_cluster_sizes,
    plot_smoothing_bridge_schematic,
)
from hodgecy.reporting.paper_tables import ensure_output_dirs  # noqa: E402
from hodgecy.smoothing import write_default_verification_outputs  # noqa: E402


def main() -> None:
    ensure_output_dirs()
    generated = []

    write_default_verification_outputs(REPO_ROOT)
    generated.append("smoothing_verification_outputs")

    build_tier_a_control_table()
    generated.append("table_tier_a_controls")
    build_same_hodge_cluster_table()
    generated.append("table_same_hodge_clusters")
    build_smoothing_bridge_table()
    generated.append("table_smoothing_bridge_profiles")
    build_concurrency_comparison_table()
    generated.append("table_concurrency_comparison_84_84a")
    build_defect_queue_table()
    generated.append("table_defect_queue")

    plot_hodge_scatter()
    generated.append("fig_hodge_scatter")
    plot_same_hodge_cluster_sizes()
    generated.append("fig_same_hodge_cluster_sizes")
    plot_smoothing_bridge_schematic()
    generated.append("fig_smoothing_bridge_schematic")
    plot_concurrency_graphs_84_84a()
    generated.append("fig_concurrency_graphs_84_84a")
    plot_hodgecy_pipeline()
    generated.append("fig_hodgecy_pipeline")

    print("Generated paper assets:")
    for item in generated:
        print(f"- {item}")
    skipped_path = REPO_ROOT / "data" / "processed" / "paper_figures" / "concurrency_graphs_skipped.json"
    if skipped_path.exists():
        print(f"- concurrency graph plot skipped: {json.loads(skipped_path.read_text(encoding='utf-8'))['reason']}")


if __name__ == "__main__":
    main()
