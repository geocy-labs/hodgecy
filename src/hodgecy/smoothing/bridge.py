"""Combinatorial scaffolding for smoothing bridges F_epsilon = A + epsilon Q^2."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations

import pandas as pd

from hodgecy.arrangements.incidence import intersection_rank
from hodgecy.arrangements.planes import PlaneArrangement


@dataclass(slots=True)
class QuarticPerturbation:
    label: str
    polynomial: str | None
    genericity: str = "generic"
    source: str | None = None
    notes: str | None = None


@dataclass(slots=True)
class ExpectedNodeStratum:
    arrangement_id: str
    stratum_label: str
    plane_pair: tuple[str, str]
    expected_nodes: int
    reason: str
    status: str = "expected_not_verified"


@dataclass(slots=True)
class SmoothingBridgeProfile:
    arrangement_id: str
    perturbation_label: str
    number_of_planes: int
    number_of_double_lines: int | None
    triple_line_count: int | None
    expected_nodes_total: int | None
    assumptions: list[str]
    warnings: list[str]
    expected_nodes_per_double_line: int | None = 4
    status: str = "expected_not_verified"
    notes: str | None = None


def double_line_candidates(arrangement: PlaneArrangement) -> pd.DataFrame:
    """Return all rank-2 plane-pair intersections as double-line candidates."""
    rows: list[dict[str, object]] = []
    for i, j in combinations(range(len(arrangement.planes)), 2):
        rank = intersection_rank(arrangement, (i, j))
        if rank == 2:
            rows.append(
                {
                    "arrangement_id": arrangement.arrangement_id,
                    "plane_i": arrangement.planes[i].label,
                    "plane_j": arrangement.planes[j].label,
                    "rank": rank,
                    "stratum_label": f"{arrangement.planes[i].label}_{arrangement.planes[j].label}",
                }
            )
    return pd.DataFrame(rows)


def line_key_from_pair(arrangement: PlaneArrangement, i: int, j: int) -> str:
    """Return a canonical row-space key for the line cut out by a plane pair."""
    matrix = arrangement.planes[i].coefficients, arrangement.planes[j].coefficients
    import sympy as sp

    reduced, _ = sp.Matrix(matrix).rref()
    rows = []
    for row_index in range(reduced.rows):
        row = tuple(str(reduced[row_index, col_index]) for col_index in range(reduced.cols))
        if any(value != "0" for value in row):
            rows.append(row)
    return "|".join(",".join(row) for row in rows)


def grouped_double_lines(arrangement: PlaneArrangement) -> pd.DataFrame:
    """Group plane-pair intersections by canonical line key."""
    candidates = double_line_candidates(arrangement)
    if candidates.empty:
        return pd.DataFrame(
            columns=[
                "arrangement_id",
                "line_key",
                "plane_pairs",
                "pair_count",
                "distinct_plane_labels",
                "is_triple_or_higher_line_candidate",
                "expected_nodes_if_generic_Q",
            ]
        )

    key_rows: list[dict[str, object]] = []
    label_to_index = {plane.label: index for index, plane in enumerate(arrangement.planes)}
    for _, row in candidates.iterrows():
        i = label_to_index[row["plane_i"]]
        j = label_to_index[row["plane_j"]]
        key_rows.append(
            {
                "arrangement_id": arrangement.arrangement_id,
                "line_key": line_key_from_pair(arrangement, i, j),
                "plane_pair": (row["plane_i"], row["plane_j"]),
            }
        )

    grouped_records = []
    frame = pd.DataFrame(key_rows)
    for line_key, group in frame.groupby("line_key", dropna=False):
        plane_pairs = [f"{left}:{right}" for left, right in group["plane_pair"]]
        distinct_labels = sorted({label for pair in group["plane_pair"] for label in pair})
        grouped_records.append(
            {
                "arrangement_id": arrangement.arrangement_id,
                "line_key": line_key,
                "plane_pairs": ";".join(plane_pairs),
                "pair_count": len(group),
                "distinct_plane_labels": ",".join(distinct_labels),
                "is_triple_or_higher_line_candidate": len(group) > 1,
                "expected_nodes_if_generic_Q": 4,
            }
        )
    return pd.DataFrame(grouped_records).sort_values(
        ["pair_count", "plane_pairs"], ascending=[False, True]
    ).reset_index(drop=True)


def smoothing_bridge_profile(
    arrangement: PlaneArrangement,
    perturbation: QuarticPerturbation | None = None,
    table1_row: dict | None = None,
) -> SmoothingBridgeProfile:
    """Build the Gate 2 smoothing-bridge expectation profile for an arrangement."""
    perturbation = perturbation or QuarticPerturbation(label="generic_quartic_Q", polynomial=None)
    grouped = grouped_double_lines(arrangement)
    warnings: list[str] = []
    assumptions = [
        "Q is a generic quartic",
        "Q avoids higher singular strata of the arrangement",
        "Q intersects each double line transversely in four points",
        "local analytic node verification remains to be checked",
    ]

    grouped_triple_candidates = int(grouped["is_triple_or_higher_line_candidate"].sum()) if not grouped.empty else 0

    if table1_row is not None and "l3" in table1_row:
        triple_line_count = int(table1_row["l3"])
    else:
        triple_line_count = grouped_triple_candidates
        warnings.append("Triple-line count inferred from grouped pair multiplicities; no Table 1 row supplied.")

    if grouped_triple_candidates > 0:
        warnings.append("Repeated line keys detected; triple or higher line candidates require separate analysis.")

    if table1_row is None:
        warnings.append("No Table 1 row supplied; smoothing counts are recorded under genericity assumptions only.")

    number_of_double_lines = int((grouped["pair_count"] == 1).sum()) if not grouped.empty else 0
    expected_nodes_total = None
    if triple_line_count == 0 and grouped_triple_candidates == 0:
        expected_nodes_total = 4 * number_of_double_lines
    else:
        warnings.append("Naive 4-per-line node count suppressed because triple/higher line structure may interfere.")

    notes = (
        "Combinatorial/local-model smoothing bridge only: residual node counts remain expected values "
        "until CAS and local analytic verification are completed."
    )

    return SmoothingBridgeProfile(
        arrangement_id=arrangement.arrangement_id,
        perturbation_label=perturbation.label,
        number_of_planes=len(arrangement.planes),
        number_of_double_lines=number_of_double_lines,
        triple_line_count=triple_line_count,
        expected_nodes_total=expected_nodes_total,
        assumptions=assumptions,
        warnings=warnings,
        notes=notes,
    )


def profile_to_dict(profile: SmoothingBridgeProfile) -> dict:
    """Serialize a smoothing-bridge profile to a plain dictionary."""
    return asdict(profile)
