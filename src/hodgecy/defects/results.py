"""Verified-result ingestion for defect computations."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_verified_defect_results(path) -> pd.DataFrame:
    """Load verified defect results from disk."""
    results_path = Path(path)
    if not results_path.is_absolute():
        results_path = _repo_root() / results_path
    return pd.read_csv(results_path, dtype={"example_id": str})


def merge_defect_results_with_profiles(profiles_df: pd.DataFrame, results_df: pd.DataFrame) -> pd.DataFrame:
    """Merge candidate profiles with verified defect results when available."""
    return profiles_df.merge(results_df, on="example_id", how="left")
