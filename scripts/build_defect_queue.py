"""Build the defect-computation queue for smoothing-bridge examples."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.defects import build_smoothing_bridge_defect_queue  # noqa: E402


def main() -> None:
    queue = build_smoothing_bridge_defect_queue()
    queue_path = REPO_ROOT / "data" / "processed" / "defect_computation_queue.csv"
    queue.to_csv(queue_path, index=False)

    lines = [
        r"\begin{tabular}{@{}p{2.6cm}p{1.6cm}p{1.5cm}p{1.9cm}p{1.6cm}p{2.4cm}p{1.2cm}p{5.6cm}@{}}",
        r"\toprule",
        r"Example & Source & Nodes & Critical degree & Degree status & Defect status & Priority & Notes \\",
        r"\midrule",
    ]
    for _, row in queue.iterrows():
        lines.append(
            f"{row['example_id']} & {row['source_arrangement']} & {row['expected_node_count']} & "
            f"{row['critical_degree']} & {row['critical_degree_status']} & {row['defect_status']} & "
            f"{row['priority']} & {row['notes']} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", ""])
    (REPO_ROOT / "paper" / "tables" / "defect_computation_queue.tex").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
