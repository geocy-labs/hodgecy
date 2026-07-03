"""Plane-arrangement data for selected Cynk--Meyer examples."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Plane:
    label: str
    coefficients: tuple[int | str, int | str, int | str, int | str]
    equation: str | None = None


@dataclass(slots=True)
class PlaneArrangement:
    arrangement_id: str
    planes: list[Plane]
    variables: tuple[str, str, str, str] = ("x", "y", "z", "t")
    source: str | None = None
    notes: str | None = None


def arrangement_84() -> PlaneArrangement:
    """Return the explicit eight-plane arrangement used for Cynk--Meyer 84."""
    return PlaneArrangement(
        arrangement_id="84",
        source="Cynk--Meyer arrangement 84 control audit",
        notes="Motivational/control arrangement for incidence-lattice comparison.",
        planes=[
            Plane("p1", (1, 0, 0, -1), "x - t"),
            Plane("p2", (1, 0, 0, 1), "x + t"),
            Plane("p3", (0, 1, 0, -1), "y - t"),
            Plane("p4", (0, 1, 0, 1), "y + t"),
            Plane("p5", (0, 0, 1, -1), "z - t"),
            Plane("p6", (0, 0, 1, 1), "z + t"),
            Plane("p7", (1, 1, 1, 1), "x + y + z + t"),
            Plane("p8", (1, 1, 1, -3), "x + y + z - 3t"),
        ],
    )


def arrangement_84a() -> PlaneArrangement:
    """Return the explicit eight-plane arrangement used for Cynk--Meyer 84a."""
    return PlaneArrangement(
        arrangement_id="84a",
        source="Cynk--Meyer arrangement 84a control audit",
        notes="Motivational/control arrangement for incidence-lattice comparison.",
        planes=[
            Plane("p1", (1, 0, 0, -1), "x - t"),
            Plane("p2", (1, 0, 0, 1), "x + t"),
            Plane("p3", (0, 1, 0, -1), "y - t"),
            Plane("p4", (0, 1, 0, 1), "y + t"),
            Plane("p5", (0, 0, 1, -1), "z - t"),
            Plane("p6", (0, 0, 1, 1), "z + t"),
            Plane("p7", (1, 1, 1, -1), "x + y + z - t"),
            Plane("p8", (1, 1, 1, -3), "x + y + z - 3t"),
        ],
    )


def arrangement_83_family_symbolic() -> PlaneArrangement | None:
    """Return None until a concrete parameter specialization for arrangement 83 is encoded."""
    return None
