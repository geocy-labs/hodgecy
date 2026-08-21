from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from .ids import HodgeCYID, IdentityKind

class AdapterCapability(str, Enum):
    STREAMING = "streaming"
    ARCHIVE = "archive"
    COLUMNAR = "columnar"
    REMOTE = "remote"
    RELATION = "relation"
    NATIVE_PAYLOAD = "native_payload"
    MANUAL_SOURCE = "manual_source"
    COMPUTABLE_SOURCE = "computable_source"

@dataclass(frozen=True, slots=True)
class DatasetAdapterDescriptor:
    dataset_id: HodgeCYID
    adapter_name: str
    adapter_version: str
    capabilities: tuple[AdapterCapability, ...]

    def __post_init__(self) -> None:
        self.dataset_id.require_kind(IdentityKind.DATASET)

    def supports(self, capability: AdapterCapability) -> bool:
        return capability in self.capabilities
