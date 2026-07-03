"""Concurrency-aware profiles for plane arrangements."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
from itertools import combinations
import math

import sympy as sp

from .planes import PlaneArrangement


@dataclass(slots=True)
class MultiplePoint:
    point_id: str
    coordinates: tuple[int, int, int, int]
    multiplicity: int
    planes: list[str]
    incident_double_lines: list[str]


@dataclass(slots=True)
class DoubleLine:
    line_id: str
    planes: tuple[str, str]
    canonical_key: str
    incident_multiple_points: list[str]
    multiple_point_multiplicity_profile: list[int]
    expected_smoothed_nodes: int = 4


@dataclass(slots=True)
class ArrangementConcurrencyProfile:
    arrangement_id: str
    plane_count: int
    double_line_count: int
    multiple_point_count_by_multiplicity: dict[int, int]
    line_profile_counts: list[dict]
    p3_count: int
    p4_count: int
    p5_count: int
    p4_collinearity_degree_sequence: list[int]
    p4_collinearity_edge_count: int
    p3_p4_collinear_pair_count: int
    status: str
    multiple_points: list[MultiplePoint]
    double_lines: list[DoubleLine]
    notes: str | None = None


def fraction_to_str(x) -> str:
    """Convert a rational-like value to a JSON-safe string."""
    value = Fraction(x)
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _normalize_integer_tuple(values: list[Fraction]) -> tuple[int, int, int, int]:
    denominators = [value.denominator for value in values if value != 0]
    scale = 1
    for denominator in denominators:
        scale = math.lcm(scale, denominator)
    scaled = [int(value * scale) for value in values]
    gcd = 0
    for value in scaled:
        gcd = math.gcd(gcd, abs(value))
    gcd = gcd or 1
    normalized = [value // gcd for value in scaled]
    for value in normalized:
        if value != 0:
            if value < 0:
                normalized = [-entry for entry in normalized]
            break
    return tuple(normalized)  # type: ignore[return-value]


def vector_to_projective_str(pt) -> str:
    """Convert a homogeneous projective point into a canonical string."""
    normalized = _normalize_integer_tuple([Fraction(value) for value in pt])
    return "(" + ":".join(str(value) for value in normalized) + ")"


def rref_key_to_str(key) -> str:
    """Convert an RREF-like key to a canonical JSON-safe string."""
    return "|".join(",".join(fraction_to_str(value) for value in row) for row in key)


def _line_key_from_pair(arrangement: PlaneArrangement, i: int, j: int) -> str:
    matrix = sp.Matrix([arrangement.planes[i].coefficients, arrangement.planes[j].coefficients])
    reduced, _ = matrix.rref()
    rows = []
    for row_index in range(reduced.rows):
        row = tuple(Fraction(reduced[row_index, col_index]) for col_index in range(reduced.cols))
        if any(value != 0 for value in row):
            rows.append(row)
    return rref_key_to_str(rows)


def _point_key_from_planes(arrangement: PlaneArrangement, indices: tuple[int, ...]) -> tuple[int, int, int, int] | None:
    matrix = sp.Matrix([arrangement.planes[index].coefficients for index in indices])
    if matrix.rank() != 3:
        return None
    nullspace = matrix.nullspace()
    if len(nullspace) != 1:
        return None
    vector = [Fraction(entry) for entry in nullspace[0]]
    if all(value == 0 for value in vector):
        return None
    return _normalize_integer_tuple(vector)


def build_concurrency_profile(arrangement: PlaneArrangement) -> ArrangementConcurrencyProfile:
    """Build the exact concurrency profile for a plane arrangement."""
    line_records = []
    for line_number, (i, j) in enumerate(combinations(range(len(arrangement.planes)), 2), start=1):
        line_records.append(
            {
                "line_id": f"L{line_number:02d}",
                "indices": (i, j),
                "planes": (arrangement.planes[i].label, arrangement.planes[j].label),
                "canonical_key": _line_key_from_pair(arrangement, i, j),
            }
        )

    point_to_planes: dict[tuple[int, int, int, int], set[int]] = {}
    for subset_size in range(3, len(arrangement.planes) + 1):
        for subset in combinations(range(len(arrangement.planes)), subset_size):
            point_key = _point_key_from_planes(arrangement, subset)
            if point_key is not None:
                point_to_planes.setdefault(point_key, set()).update(subset)

    multiple_points = []
    point_lookup: dict[tuple[int, int, int, int], MultiplePoint] = {}
    for point_number, (coordinates, plane_indices) in enumerate(sorted(point_to_planes.items()), start=1):
        point_id = f"pt{point_number:02d}"
        plane_labels = sorted(arrangement.planes[index].label for index in plane_indices)
        point = MultiplePoint(
            point_id=point_id,
            coordinates=coordinates,
            multiplicity=len(plane_indices),
            planes=plane_labels,
            incident_double_lines=[],
        )
        multiple_points.append(point)
        point_lookup[coordinates] = point

    double_lines = []
    point_by_id = {point.point_id: point for point in multiple_points}
    for record in line_records:
        incident_points = []
        for point in multiple_points:
            plane_set = set(point.planes)
            if set(record["planes"]).issubset(plane_set):
                incident_points.append(point.point_id)
                point.incident_double_lines.append(record["line_id"])
        multiplicity_profile = sorted(point_by_id[point_id].multiplicity for point_id in incident_points)
        double_lines.append(
            DoubleLine(
                line_id=record["line_id"],
                planes=record["planes"],
                canonical_key=record["canonical_key"],
                incident_multiple_points=sorted(incident_points),
                multiple_point_multiplicity_profile=multiplicity_profile,
            )
        )

    multiple_point_count_by_multiplicity: dict[int, int] = {}
    for point in multiple_points:
        point.incident_double_lines.sort()
        multiple_point_count_by_multiplicity[point.multiplicity] = multiple_point_count_by_multiplicity.get(point.multiplicity, 0) + 1

    line_profile_counter: dict[tuple[int, ...], int] = {}
    for line in double_lines:
        profile = tuple(line.multiple_point_multiplicity_profile)
        line_profile_counter[profile] = line_profile_counter.get(profile, 0) + 1
    line_profile_counts = [
        {"profile": list(profile), "count": count}
        for profile, count in sorted(line_profile_counter.items(), key=lambda item: (item[0], item[1]))
    ]

    p4_points = [point for point in multiple_points if point.multiplicity == 4]
    p4_degree = {point.point_id: 0 for point in p4_points}
    p4_edge_count = 0
    p3_p4_collinear_pair_count = 0
    for line in double_lines:
        p4_ids = [point_id for point_id in line.incident_multiple_points if point_by_id[point_id].multiplicity == 4]
        p3_ids = [point_id for point_id in line.incident_multiple_points if point_by_id[point_id].multiplicity == 3]
        if len(p4_ids) >= 2:
            for left, right in combinations(sorted(p4_ids), 2):
                p4_degree[left] += 1
                p4_degree[right] += 1
                p4_edge_count += 1
        p3_p4_collinear_pair_count += len(p3_ids) * len(p4_ids)

    return ArrangementConcurrencyProfile(
        arrangement_id=arrangement.arrangement_id,
        plane_count=len(arrangement.planes),
        double_line_count=len(double_lines),
        multiple_point_count_by_multiplicity=dict(sorted(multiple_point_count_by_multiplicity.items())),
        line_profile_counts=line_profile_counts,
        p3_count=multiple_point_count_by_multiplicity.get(3, 0),
        p4_count=multiple_point_count_by_multiplicity.get(4, 0),
        p5_count=multiple_point_count_by_multiplicity.get(5, 0),
        p4_collinearity_degree_sequence=sorted(p4_degree.values(), reverse=True),
        p4_collinearity_edge_count=p4_edge_count,
        p3_p4_collinear_pair_count=p3_p4_collinear_pair_count,
        status="computed",
        multiple_points=multiple_points,
        double_lines=double_lines,
        notes="Concurrency-aware arrangement profile built from exact rational incidence data.",
    )


def concurrency_profile_to_dict(profile: ArrangementConcurrencyProfile) -> dict:
    """Serialize a concurrency profile to a JSON-safe dictionary."""
    return asdict(profile)
