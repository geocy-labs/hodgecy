"""Picard--Fuchs operator schemas for HodgeCY."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PicardFuchsOperator:
    example_id: str
    operator_label: str | None
    order: int | None
    coefficients: list[str] | None
    source: str | None
    status: str = "not_loaded"
    notes: str | None = None


@dataclass(slots=True)
class ConifoldPoint:
    example_id: str
    parameter_value: str | None
    local_coordinate: str | None
    multiplicity: int | None
    source: str | None
    status: str = "candidate"
    notes: str | None = None
