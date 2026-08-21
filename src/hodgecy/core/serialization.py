from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from typing import Any


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Fraction):
        return f"{value.numerator}/{value.denominator}"
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def canonical_json(value: Any) -> str:
    return json.dumps(value, default=_json_default, sort_keys=True, separators=(",", ":"))


def stable_sha256(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()
