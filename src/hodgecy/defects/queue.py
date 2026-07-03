"""Queue utilities for smoothing-bridge defect computations."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_defect_queue(path="data/processed/defect_computation_queue.csv") -> pd.DataFrame:
    """Load the defect-computation queue from disk."""
    queue_path = Path(path)
    if not queue_path.is_absolute():
        queue_path = _repo_root() / queue_path
    return pd.read_csv(queue_path, dtype={"example_id": str, "source_arrangement": str})


def build_smoothing_bridge_defect_queue() -> pd.DataFrame:
    """Build the high-priority defect queue for smoothing-bridge 84 and 84a."""
    examples_path = _repo_root() / "data" / "raw" / "smoothing_bridge_examples.json"
    payload = json.loads(examples_path.read_text(encoding="utf-8"))

    rows = []
    for record in payload:
        rows.append(
            {
                "example_id": record["example_id"],
                "source_arrangement": record["source_arrangement"],
                "expected_node_count": record["expected_node_count"],
                "critical_degree": record["critical_degree"],
                "critical_degree_status": record["critical_degree_status"],
                "defect_status": record["defect_status"],
                "required_tool": "Macaulay2_or_Singular",
                "priority": "high",
                "notes": (
                    "Compute classical nodal defect for the smoothing bridge example "
                    "F_epsilon=A+epsilon Q^2 after choosing explicit generic Q and verifying nodes."
                ),
            }
        )
    return pd.DataFrame(rows)
