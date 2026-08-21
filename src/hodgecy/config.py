from __future__ import annotations

import json
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any
from .core.errors import ConfigurationError

_ENV_DATA_ROOT = "HODGECY_DATA_ROOT"

@dataclass(frozen=True, slots=True)
class HodgeCYDataRoot:
    root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", self.root.expanduser().resolve())

    @property
    def raw(self) -> Path:
        return self.root / "raw"
    @property
    def native(self) -> Path:
        return self.root / "raw"
    @property
    def staged(self) -> Path:
        return self.root / "staged"
    @property
    def normalized(self) -> Path:
        return self.root / "normalized"
    @property
    def derived(self) -> Path:
        return self.root / "derived"
    @property
    def indexes(self) -> Path:
        return self.root / "indexes"
    @property
    def catalogs(self) -> Path:
        return self.root / "catalogs"
    @property
    def manifests(self) -> Path:
        return self.root / "manifests"
    @property
    def certificates(self) -> Path:
        return self.root / "certificates"
    @property
    def cache(self) -> Path:
        return self.root / "cache"
    @property
    def logs(self) -> Path:
        return self.root / "logs"
    @property
    def rejected(self) -> Path:
        return self.root / "rejected"
    @property
    def reports(self) -> Path:
        return self.root / "reports"

    def require_exists(self) -> "HodgeCYDataRoot":
        if not self.root.exists():
            raise ConfigurationError(f"HodgeCY data root does not exist: {self.root}")
        if not self.root.is_dir():
            raise ConfigurationError(f"HodgeCY data root is not a directory: {self.root}")
        return self

    def catalog(self, *, name: str = "hodgecy_catalog", create: bool = False, read_only: bool = False):
        from .storage import open_catalog

        return open_catalog(self, name=name, create=create, read_only=read_only)

@dataclass(frozen=True, slots=True)
class HodgeCYConfig:
    data_root: HodgeCYDataRoot | None = None
    cache_root: Path | None = None
    certificate_root: Path | None = None
    materialization_row_limit: int = 100_000
    optional_backends: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if self.materialization_row_limit <= 0:
            raise ConfigurationError("materialization_row_limit must be positive")
        if self.cache_root is not None:
            object.__setattr__(self, "cache_root", self.cache_root.expanduser().resolve())
        if self.certificate_root is not None:
            object.__setattr__(self, "certificate_root", self.certificate_root.expanduser().resolve())

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "HodgeCYConfig":
        env = environ or os.environ
        root = env.get(_ENV_DATA_ROOT)
        return cls(data_root=HodgeCYDataRoot(Path(root)) if root else None)

    @classmethod
    def from_file(cls, path: Path) -> "HodgeCYConfig":
        payload = json.loads(path.read_text(encoding="utf-8"))
        data_root = payload.get("data_root")
        return cls(
            data_root=HodgeCYDataRoot(Path(data_root)) if data_root else None,
            cache_root=Path(payload["cache_root"]) if payload.get("cache_root") else None,
            certificate_root=Path(payload["certificate_root"]) if payload.get("certificate_root") else None,
            materialization_row_limit=int(payload.get("materialization_row_limit", 100_000)),
            optional_backends=dict(payload.get("optional_backends") or {}),
        )

    @classmethod
    def load(cls, *, data_root: str | Path | None = None, config_file: Path | None = None, environ: dict[str, str] | None = None) -> "HodgeCYConfig":
        config = cls.from_file(config_file) if config_file else cls()
        env_config = cls.from_env(environ)
        if env_config.data_root is not None:
            config = replace(config, data_root=env_config.data_root)
        if data_root is not None:
            config = replace(config, data_root=HodgeCYDataRoot(Path(data_root)))
        return config

    def to_dict(self) -> dict[str, Any]:
        return {
            "data_root": None if self.data_root is None else self.data_root.root.as_posix(),
            "cache_root": None if self.cache_root is None else self.cache_root.as_posix(),
            "certificate_root": None if self.certificate_root is None else self.certificate_root.as_posix(),
            "materialization_row_limit": self.materialization_row_limit,
            "optional_backends": self.optional_backends or {},
        }

def open_data_root(root: str | Path | None = None, *, require_exists: bool = False) -> HodgeCYDataRoot:
    config = HodgeCYConfig.load(data_root=root)
    if config.data_root is None:
        raise ConfigurationError("No HodgeCY data root configured; pass a root or set HODGECY_DATA_ROOT")
    return config.data_root.require_exists() if require_exists else config.data_root
