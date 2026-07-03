"""Generate clustering summaries and discriminating pairs for the Cynk--Meyer dataset."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.datasets.cynk_meyer import load_table1, validate_table1
from hodgecy.experiments.clustering import (
    find_same_hodge_different_singularity,
    find_same_modular_form_different_geometry,
    find_same_singularity_different_hodge,
    find_same_singularity_same_hodge_different_modular_form,
    group_by_hodge_profile,
    group_by_singularity_profile,
)


def _flag_examples(pairs: pd.DataFrame) -> pd.DataFrame:
    frame = pairs.copy()
    frame["flag_83_vs_84"] = (
        (frame["category"] == "same_singularity_different_hodge")
        & (
            ((frame["arrangement_a"] == "83") & (frame["arrangement_b"] == "84"))
            | ((frame["arrangement_a"] == "84") & (frame["arrangement_b"] == "83"))
        )
    )
    frame["flag_84_vs_84a"] = (
        (frame["category"] == "same_singularity_same_hodge_different_modular_form")
        & (
            ((frame["arrangement_a"] == "84") & (frame["arrangement_b"] == "84a"))
            | ((frame["arrangement_a"] == "84a") & (frame["arrangement_b"] == "84"))
        )
    )
    frame["flag_2_vs_85"] = (
        (frame["category"] == "same_modular_form_different_geometry")
        & (
            ((frame["arrangement_a"] == "2") & (frame["arrangement_b"] == "85"))
            | ((frame["arrangement_a"] == "85") & (frame["arrangement_b"] == "2"))
        )
    )
    cluster_members = {"12", "15", "20", "29", "44"}
    frame["flag_hodge_cluster_3_51"] = (
        (frame["category"] == "same_hodge_different_singularity")
        & frame["arrangement_a"].isin(cluster_members)
        & frame["arrangement_b"].isin(cluster_members)
    )
    return frame


def main() -> None:
    df = load_table1()
    validate_table1(df)

    processed_dir = REPO_ROOT / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    hodge_clusters = group_by_hodge_profile(df)
    singularity_clusters = group_by_singularity_profile(df)
    pairs = pd.concat(
        [
            find_same_singularity_different_hodge(df),
            find_same_singularity_same_hodge_different_modular_form(df),
            find_same_hodge_different_singularity(df),
            find_same_modular_form_different_geometry(df),
        ],
        ignore_index=True,
    ).drop_duplicates(subset=["category", "arrangement_a", "arrangement_b"])

    pairs = _flag_examples(pairs).sort_values(["category", "arrangement_a", "arrangement_b"]).reset_index(drop=True)

    hodge_clusters.to_csv(processed_dir / "clusters_by_hodge.csv", index=False)
    singularity_clusters.to_csv(processed_dir / "clusters_by_singularity.csv", index=False)
    pairs.to_csv(processed_dir / "discriminating_pairs.csv", index=False)


if __name__ == "__main__":
    main()
