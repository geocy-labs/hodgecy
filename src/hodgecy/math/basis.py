from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence
from hodgecy.core.errors import ValidationError
from hodgecy.core.ids import HodgeCYID, IdentityKind
from .domains import CoefficientDomain

Coefficient = int | str | Fraction

@dataclass(frozen=True, slots=True)
class Basis:
    basis_id: HodgeCYID
    module: str
    coefficient_domain: CoefficientDomain
    labels: tuple[str, ...]
    convention: str | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        if self.basis_id.kind not in {IdentityKind.PRESENTATION, IdentityKind.DERIVED_OBJECT}:
            raise ValidationError("basis_id must be a presentation or derived-object identity")
        if len(set(self.labels)) != len(self.labels):
            raise ValidationError("basis labels must be unique")

    @property
    def dimension(self) -> int:
        return len(self.labels)

    def require_compatible(self, other: "Basis") -> None:
        if self.basis_id != other.basis_id or self.coefficient_domain != other.coefficient_domain:
            raise ValidationError("Basis-sensitive objects use incompatible bases")

    def to_dict(self) -> dict[str, object]:
        return {"basis_id": self.basis_id.to_dict(), "module": self.module, "coefficient_domain": self.coefficient_domain.to_dict(), "labels": list(self.labels), "convention": self.convention, "source": self.source}

@dataclass(frozen=True, slots=True)
class BasisVector:
    basis: Basis
    entries: tuple[Coefficient, ...]
    variance: str = "contravariant"

    def __post_init__(self) -> None:
        if len(self.entries) != self.basis.dimension:
            raise ValidationError("Vector length does not match basis dimension")
        normalized = tuple(self.basis.coefficient_domain.normalize(entry) for entry in self.entries)
        object.__setattr__(self, "entries", normalized)

    def equal_in_same_basis(self, other: "BasisVector") -> bool:
        self.basis.require_compatible(other.basis)
        return self.entries == other.entries

    def to_dict(self) -> dict[str, object]:
        return {"basis": self.basis.to_dict(), "entries": list(self.entries), "variance": self.variance}

@dataclass(frozen=True, slots=True)
class BasisMatrix:
    row_basis: Basis
    column_basis: Basis
    rows: tuple[tuple[Coefficient, ...], ...]
    representation: str = "dense"

    def __post_init__(self) -> None:
        if len(self.rows) != self.row_basis.dimension:
            raise ValidationError("Matrix row count does not match row basis dimension")
        normalized_rows = []
        for row in self.rows:
            if len(row) != self.column_basis.dimension:
                raise ValidationError("Matrix column count does not match column basis dimension")
            normalized_rows.append(tuple(self.row_basis.coefficient_domain.normalize(entry) for entry in row))
        if self.row_basis.coefficient_domain != self.column_basis.coefficient_domain:
            raise ValidationError("Row and column coefficient domains must match")
        object.__setattr__(self, "rows", tuple(normalized_rows))

    @property
    def shape(self) -> tuple[int, int]:
        return (self.row_basis.dimension, self.column_basis.dimension)

    def to_dict(self) -> dict[str, object]:
        return {"row_basis": self.row_basis.to_dict(), "column_basis": self.column_basis.to_dict(), "rows": [list(row) for row in self.rows], "representation": self.representation, "shape": list(self.shape)}
