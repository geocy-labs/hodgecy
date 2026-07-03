"""Clustering and discriminating-pair helpers for the Cynk--Meyer dataset."""

from __future__ import annotations

from itertools import combinations
from typing import Iterable

import pandas as pd


def singularity_profile_columns() -> list[str]:
    """Return the columns defining the combinatorial singularity profile."""
    return ["p3", "p4_0", "p4_1", "p5_0", "p5_1", "p5_2", "l3"]


def hodge_profile_columns() -> list[str]:
    """Return the columns defining the Hodge-theoretic profile."""
    return ["h12", "h11", "euler"]


def _normalized_frame(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    frame["arrangement"] = frame["arrangement"].astype(str)
    frame["modular_form"] = frame["modular_form"].fillna("").astype(str)
    return frame


def _profile_key(row: pd.Series, columns: Iterable[str]) -> str:
    return "|".join(f"{column}={row[column]}" for column in columns)


def _pair_rows(group: pd.DataFrame, category: str, note: str = "") -> list[dict[str, object]]:
    singularity_cols = singularity_profile_columns()
    hodge_cols = hodge_profile_columns()
    rows: list[dict[str, object]] = []
    for left_index, right_index in combinations(group.index.tolist(), 2):
        left = group.loc[left_index]
        right = group.loc[right_index]
        rows.append(
            {
                "category": category,
                "arrangement_a": left["arrangement"],
                "arrangement_b": right["arrangement"],
                "same_singularity_profile": all(left[col] == right[col] for col in singularity_cols),
                "same_hodge_profile": all(left[col] == right[col] for col in hodge_cols),
                "same_modular_form": left["modular_form"] == right["modular_form"],
                "modular_form_a": left["modular_form"],
                "modular_form_b": right["modular_form"],
                "singularity_profile_a": _profile_key(left, singularity_cols),
                "singularity_profile_b": _profile_key(right, singularity_cols),
                "hodge_profile_a": _profile_key(left, hodge_cols),
                "hodge_profile_b": _profile_key(right, hodge_cols),
                "note": note,
            }
        )
    return rows


def group_by_singularity_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Cluster arrangements by singularity profile."""
    frame = _normalized_frame(df)
    group_cols = singularity_profile_columns()
    summary = (
        frame.groupby(group_cols, dropna=False)
        .agg(
            cluster_size=("arrangement", "size"),
            arrangements=("arrangement", lambda values: ",".join(sorted(values, key=str))),
            hodge_profiles=(
                "arrangement",
                lambda idx: ";".join(
                    sorted(
                        {
                            _profile_key(frame.loc[i], hodge_profile_columns())
                            for i in idx.index
                        }
                    )
                ),
            ),
            modular_forms=(
                "modular_form",
                lambda values: ",".join(sorted({value for value in values if value})),
            ),
        )
        .reset_index()
    )
    return summary.sort_values(["cluster_size", "arrangements"], ascending=[False, True]).reset_index(drop=True)


def group_by_hodge_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Cluster arrangements by Hodge profile."""
    frame = _normalized_frame(df)
    group_cols = hodge_profile_columns()
    summary = (
        frame.groupby(group_cols, dropna=False)
        .agg(
            cluster_size=("arrangement", "size"),
            arrangements=("arrangement", lambda values: ",".join(sorted(values, key=str))),
            singularity_profiles=(
                "arrangement",
                lambda idx: ";".join(
                    sorted(
                        {
                            _profile_key(frame.loc[i], singularity_profile_columns())
                            for i in idx.index
                        }
                    )
                ),
            ),
            modular_forms=(
                "modular_form",
                lambda values: ",".join(sorted({value for value in values if value})),
            ),
        )
        .reset_index()
    )
    return summary.sort_values(["cluster_size", "arrangements"], ascending=[False, True]).reset_index(drop=True)


def find_same_singularity_different_hodge(df: pd.DataFrame) -> pd.DataFrame:
    """Find pairs with the same singularity profile but different Hodge data."""
    frame = _normalized_frame(df)
    rows: list[dict[str, object]] = []
    for _, group in frame.groupby(singularity_profile_columns(), dropna=False):
        if len(group) < 2 or group[hodge_profile_columns()].drop_duplicates().shape[0] < 2:
            continue
        rows.extend(_pair_rows(group, "same_singularity_different_hodge"))
    return pd.DataFrame(rows).sort_values(["arrangement_a", "arrangement_b"]).reset_index(drop=True)


def find_same_singularity_same_hodge_different_modular_form(df: pd.DataFrame) -> pd.DataFrame:
    """Find pairs with identical singularity and Hodge profiles but different modular forms."""
    frame = _normalized_frame(df)
    rows: list[dict[str, object]] = []
    group_cols = singularity_profile_columns() + hodge_profile_columns()
    for _, group in frame.groupby(group_cols, dropna=False):
        distinct_modular_forms = {value for value in group["modular_form"] if value}
        if len(group) < 2 or len(distinct_modular_forms) < 2:
            continue
        rows.extend(_pair_rows(group, "same_singularity_same_hodge_different_modular_form"))
    return pd.DataFrame(rows).sort_values(["arrangement_a", "arrangement_b"]).reset_index(drop=True)


def find_same_hodge_different_singularity(df: pd.DataFrame) -> pd.DataFrame:
    """Find pairs with the same Hodge data but different singularity profiles."""
    frame = _normalized_frame(df)
    rows: list[dict[str, object]] = []
    for _, group in frame.groupby(hodge_profile_columns(), dropna=False):
        if len(group) < 2 or group[singularity_profile_columns()].drop_duplicates().shape[0] < 2:
            continue
        rows.extend(_pair_rows(group, "same_hodge_different_singularity"))
    return pd.DataFrame(rows).sort_values(["arrangement_a", "arrangement_b"]).reset_index(drop=True)


def find_same_modular_form_different_geometry(df: pd.DataFrame) -> pd.DataFrame:
    """Find pairs sharing a modular form label but differing in geometry-sensitive data."""
    frame = _normalized_frame(df)
    frame = frame.loc[frame["modular_form"] != ""].copy()
    rows: list[dict[str, object]] = []
    geometry_cols = singularity_profile_columns() + hodge_profile_columns()
    for modular_form, group in frame.groupby("modular_form", dropna=False):
        if len(group) < 2:
            continue
        for record in _pair_rows(group, "same_modular_form_different_geometry", note=f"modular_form={modular_form}"):
            left = group.loc[group["arrangement"] == record["arrangement_a"]].iloc[0]
            right = group.loc[group["arrangement"] == record["arrangement_b"]].iloc[0]
            if any(left[col] != right[col] for col in geometry_cols):
                rows.append(record)
    return pd.DataFrame(rows).sort_values(["arrangement_a", "arrangement_b"]).reset_index(drop=True)
