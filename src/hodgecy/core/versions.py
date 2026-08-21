from __future__ import annotations

import re
from dataclasses import dataclass
from .errors import ValidationError

_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")

@dataclass(frozen=True, slots=True)
class SchemaVersion:
    value: str = "v1"

    def __post_init__(self) -> None:
        if not _VERSION_RE.fullmatch(self.value):
            raise ValidationError(f"Invalid schema version: {self.value!r}")

    def to_dict(self) -> dict[str, str]:
        return {"value": self.value}

    @classmethod
    def from_dict(cls, payload: dict[str, str]) -> "SchemaVersion":
        return cls(str(payload["value"]))

    def __str__(self) -> str:
        return self.value
