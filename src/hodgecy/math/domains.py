from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

class DomainKind(str, Enum):
    INTEGER = "Z"
    RATIONAL = "Q"
    FINITE_FIELD = "F_p"

@dataclass(frozen=True, slots=True)
class CoefficientDomain:
    kind: DomainKind
    prime: int | None = None

    def __post_init__(self) -> None:
        if self.kind is DomainKind.FINITE_FIELD:
            if self.prime is None or self.prime < 2 or not _is_prime(self.prime):
                raise ValueError("F_p requires a prime p")
        elif self.prime is not None:
            raise ValueError("Only finite fields may carry a prime")

    @classmethod
    def integers(cls) -> "CoefficientDomain":
        return cls(DomainKind.INTEGER)

    @classmethod
    def rationals(cls) -> "CoefficientDomain":
        return cls(DomainKind.RATIONAL)

    @classmethod
    def finite_field(cls, prime: int) -> "CoefficientDomain":
        return cls(DomainKind.FINITE_FIELD, prime)

    def normalize(self, value: int | str | Fraction) -> int | str:
        if self.kind is DomainKind.INTEGER:
            if isinstance(value, Fraction) and value.denominator != 1:
                raise ValueError("Non-integral rational in integer domain")
            return int(value)
        if self.kind is DomainKind.RATIONAL:
            frac = value if isinstance(value, Fraction) else Fraction(value)
            return f"{frac.numerator}/{frac.denominator}"
        assert self.prime is not None
        return int(value) % self.prime

    def to_dict(self) -> dict[str, int | str | None]:
        return {"kind": self.kind.value, "prime": self.prime}

def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value == 2:
        return True
    if value % 2 == 0:
        return False
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True
