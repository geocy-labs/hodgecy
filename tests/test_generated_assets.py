from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pandas as pd


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_generated_assets_include_partial_verification_and_p4_figures() -> None:
    subprocess.run([sys.executable, "scripts/generate_paper_assets.py"], cwd=repo_root(), check=True)

    smoothing = pd.read_csv(repo_root() / "paper" / "tables" / "table_smoothing_bridge_profiles.csv", dtype={"source_arrangement": str})
    assert set(smoothing["verification_status"]) == {"degree112_certified"}
    assert set(smoothing["expected_node_count_status"]) == {"degree112_certified"}
    assert "Predicted points per line" in smoothing.columns
    assert not any("defect certificate are both repo-backed" in note for note in smoothing["notes"])
    assert not any("Verified: reduced zero-dimensional singular locus" in note for note in smoothing["notes"])
    assert all(
        note == "degree112_certified: (G1), (G2) verified over Q; saturated Jacobian degree 112 certified; reducedness and Hessian-rank checks pending."
        for note in smoothing["notes"]
    )

    smoothing_tex = (repo_root() / "paper" / "tables" / "table_smoothing_bridge_profiles.tex").read_text(encoding="utf-8")
    assert "Predicted points per line" in smoothing_tex
    assert "degree112_certified" in smoothing_tex
    assert "verified 112-node conifold" not in smoothing_tex
    assert "defect = 7" not in smoothing_tex
    assert "Hilbert-function value 105" not in smoothing_tex
    assert "ordinary_node_verified" not in smoothing_tex
    assert "defect_verified" not in smoothing_tex

    for suffix in ("png", "pdf"):
        assert (repo_root() / "paper" / "figures" / f"fig_concurrency_graph_84.{suffix}").exists()
        assert (repo_root() / "paper" / "figures" / f"fig_concurrency_graph_84a.{suffix}").exists()
    assert (repo_root() / "paper" / "tables" / "table_p4_collinearity_certificate.tex").exists()

    schematic_meta = json.loads(
        (repo_root() / "data" / "processed" / "paper_figures" / "fig_smoothing_bridge_schematic_metadata.json").read_text(encoding="utf-8")
    )
    assert schematic_meta["status"] == "degree112_certified"
    assert "predicted singular points" in " ".join(schematic_meta["boxes"]).lower()
    assert schematic_meta["pending_text"] == "Ordinary-node verification pending"
    assert "Ordinary-node verification and defect computation remain queued" == schematic_meta["queue_text"]
    assert "verified 112-node conifold" not in json.dumps(schematic_meta)

    graph84_meta = json.loads(
        (repo_root() / "data" / "processed" / "paper_figures" / "fig_concurrency_graph_84_metadata.json").read_text(encoding="utf-8")
    )
    graph84a_meta = json.loads(
        (repo_root() / "data" / "processed" / "paper_figures" / "fig_concurrency_graph_84a_metadata.json").read_text(encoding="utf-8")
    )
    assert graph84_meta["title"] == "Arrangement 84 p4-collinearity graph"
    assert graph84a_meta["title"] == "Arrangement 84a p4-collinearity graph"
    assert graph84_meta["degree_sequence"] == "[6,8^9]"
    assert graph84a_meta["degree_sequence"] == "[8^6,9^4]"
