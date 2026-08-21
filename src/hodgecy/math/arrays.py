from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from hodgecy.core.errors import ValidationError
from hodgecy.core.ids import DistributionLocator, HodgeCYID, IdentityKind
from hodgecy.core.provenance import ComputationProvenance, SourceProvenance
from hodgecy.core.serialization import stable_sha256
from hodgecy.core.status import ValidationEvent
from hodgecy.core.versions import SchemaVersion

from .basis import Basis, BasisMatrix, Coefficient

ARRAY_SCHEMA_VERSION = "basis_array.v1"


@dataclass(frozen=True, slots=True)
class BasisArray:
    name: str
    axes: tuple[Basis, ...]
    shape: tuple[int, ...]
    entries: tuple[Any, ...] | None = None
    array_id: HodgeCYID | None = None
    representation: str = "dense"
    variance: tuple[str, ...] = ()
    source_locator: DistributionLocator | None = None
    source_provenance: SourceProvenance | None = None
    computation_provenance: ComputationProvenance | None = None
    validation_events: tuple[ValidationEvent, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: SchemaVersion = SchemaVersion(ARRAY_SCHEMA_VERSION)

    def __post_init__(self) -> None:
        if not self.axes:
            raise ValidationError("BasisArray requires at least one basis axis")
        if len(self.axes) != len(self.shape):
            raise ValidationError("BasisArray shape must have one entry per basis axis")
        for axis, extent in zip(self.axes, self.shape):
            if extent != axis.dimension:
                raise ValidationError("BasisArray shape is incompatible with its basis axes")
        if self.variance and len(self.variance) != len(self.axes):
            raise ValidationError("BasisArray variance must have one entry per basis axis")
        if self.entries is not None:
            expected = 1
            for extent in self.shape:
                expected *= extent
            if len(self.entries) != expected:
                raise ValidationError("BasisArray entry count does not match shape")
        if self.array_id is None:
            object.__setattr__(self, "array_id", self._derived_id())
        assert self.array_id is not None
        self.array_id.require_kind(IdentityKind.DERIVED_OBJECT)

    def _derived_id(self) -> HodgeCYID:
        return HodgeCYID.derived_from_components(
            IdentityKind.DERIVED_OBJECT,
            "basis_array",
            {
                "name": self.name,
                "axes": [axis.to_dict() for axis in self.axes],
                "shape": self.shape,
                "entries_hash": None if self.entries is None else stable_sha256(self.entries),
                "representation": self.representation,
                "variance": self.variance,
                "schema_version": self.schema_version.to_dict(),
            },
        )

    @property
    def entry_count(self) -> int | None:
        return None if self.entries is None else len(self.entries)

    @classmethod
    def from_matrix(cls, name: str, matrix: BasisMatrix, *, metadata: dict[str, Any] | None = None) -> "BasisArray":
        entries: list[Coefficient] = []
        for row in matrix.rows:
            entries.extend(row)
        return cls(
            name=name,
            axes=(matrix.row_basis, matrix.column_basis),
            shape=matrix.shape,
            entries=tuple(entries),
            representation=matrix.representation,
            variance=("row", "column"),
            metadata=metadata or {},
        )

    def require_same_axes(self, other: "BasisArray") -> None:
        if self.shape != other.shape or len(self.axes) != len(other.axes):
            raise ValidationError("BasisArray objects have incompatible shapes or axes")
        for left, right in zip(self.axes, other.axes):
            left.require_compatible(right)

    def equal_entries_in_same_axes(self, other: "BasisArray") -> bool:
        self.require_same_axes(other)
        return self.entries == other.entries

    def to_dict(self, *, include_entries: bool = True) -> dict[str, Any]:
        assert self.array_id is not None
        return {
            "array_id": self.array_id.to_dict(),
            "name": self.name,
            "axes": [axis.to_dict() for axis in self.axes],
            "shape": list(self.shape),
            "entry_count": self.entry_count,
            "entries": list(self.entries) if include_entries and self.entries is not None else None,
            "entries_hash": None if self.entries is None else stable_sha256(self.entries),
            "representation": self.representation,
            "variance": list(self.variance),
            "source_locator": None if self.source_locator is None else self.source_locator.to_dict(),
            "source_provenance": None if self.source_provenance is None else self.source_provenance.to_dict(),
            "computation_provenance": None if self.computation_provenance is None else self.computation_provenance.to_dict(),
            "validation_events": [event.to_dict() for event in self.validation_events],
            "metadata": self.metadata,
            "schema_version": self.schema_version.to_dict(),
        }


def flatten_dense_rows(rows: Sequence[Sequence[Any]]) -> tuple[Any, ...]:
    return tuple(value for row in rows for value in row)
