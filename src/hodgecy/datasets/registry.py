from __future__ import annotations

from dataclasses import dataclass, field

from hodgecy.core.ids import HodgeCYID

from .base import DatasetAdapter


@dataclass(slots=True)
class AdapterRegistry:
    _adapters: dict[str, DatasetAdapter] = field(default_factory=dict)

    def register(self, adapter: DatasetAdapter, *, replace: bool = False) -> None:
        key = adapter.descriptor.dataset_id.serialize()
        if key in self._adapters and not replace:
            raise ValueError(f"Adapter already registered for {key}.")
        self._adapters[key] = adapter

    def get(self, dataset_id: HodgeCYID | str) -> DatasetAdapter:
        key = dataset_id if isinstance(dataset_id, str) else dataset_id.serialize()
        if not key.startswith("hcy:"):
            key = HodgeCYID.dataset(key).serialize()
        return self._adapters[key]

    def list_dataset_ids(self) -> tuple[HodgeCYID, ...]:
        return tuple(adapter.descriptor.dataset_id for adapter in self._adapters.values())

    def list_adapters(self) -> tuple[DatasetAdapter, ...]:
        return tuple(self._adapters.values())
