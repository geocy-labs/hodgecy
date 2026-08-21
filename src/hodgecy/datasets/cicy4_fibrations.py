from __future__ import annotations

import json
import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator
from zipfile import ZipFile

from hodgecy.core.serialization import canonical_json, stable_sha256
from hodgecy.storage.errors import StorageError

CICY4_FIBRATION_INDEX_SCHEMA = "cicy4_fibration_archive_index.v1"
CICY4_FIBRATION_SOURCE_REVISION = "cicy4-fibration-native-local"
_PARENT_KEYS = ("parent_id", "parent", "matrix_number", "cicy4_id")
_RANGE_RE = re.compile(r"(?P<start>\d{1,7})\D+(?P<end>\d{1,7})")


@dataclass(frozen=True, slots=True)
class ArchiveMemberLocator:
    archive_relative_path: str | None
    member_name: str

    def to_dict(self) -> dict[str, Any]:
        return {"archive_relative_path": self.archive_relative_path, "member_name": self.member_name}


@dataclass(frozen=True, slots=True)
class CICY4FibrationMemberIndex:
    member_name: str
    compressed_size: int
    file_size: int
    parent_min: int | None = None
    parent_max: int | None = None
    record_count: int | None = None
    checksum_crc32: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def contains_parent(self, parent_id: int) -> bool:
        if self.parent_min is None or self.parent_max is None:
            return False
        return self.parent_min <= parent_id <= self.parent_max

    def to_dict(self) -> dict[str, Any]:
        return {
            "member_name": self.member_name,
            "compressed_size": self.compressed_size,
            "file_size": self.file_size,
            "parent_min": self.parent_min,
            "parent_max": self.parent_max,
            "record_count": self.record_count,
            "checksum_crc32": self.checksum_crc32,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CICY4FibrationMemberIndex":
        return cls(
            member_name=str(payload["member_name"]),
            compressed_size=int(payload["compressed_size"]),
            file_size=int(payload["file_size"]),
            parent_min=payload.get("parent_min"),
            parent_max=payload.get("parent_max"),
            record_count=payload.get("record_count"),
            checksum_crc32=payload.get("checksum_crc32"),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class CICY4FibrationArchiveIndex:
    archive_path: Path
    archive_relative_path: str | None
    source_revision: str | None
    source_checksum: str | None
    members: tuple[CICY4FibrationMemberIndex, ...]
    schema_version: str = CICY4_FIBRATION_INDEX_SCHEMA

    def locate_parent(self, parent_id: int) -> tuple[CICY4FibrationMemberIndex, ...]:
        return tuple(member for member in self.members if member.contains_parent(parent_id))

    def locator_for_parent(self, parent_id: int) -> tuple[ArchiveMemberLocator, ...]:
        return tuple(ArchiveMemberLocator(self.archive_relative_path, member.member_name) for member in self.locate_parent(parent_id))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "builder_version": "blob11",
            "archive_path": self.archive_path.as_posix(),
            "archive_relative_path": self.archive_relative_path,
            "source_revision": self.source_revision,
            "source_checksum": self.source_checksum,
            "archive_fingerprint": _archive_fingerprint(self.archive_path, self.source_revision, self.source_checksum),
            "members": [member.to_dict() for member in self.members],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any], *, archive_path: str | Path | None = None) -> "CICY4FibrationArchiveIndex":
        if payload.get("schema_version") != CICY4_FIBRATION_INDEX_SCHEMA:
            raise StorageError("Unsupported CICY4 fibration archive index schema")
        path = Path(archive_path or payload["archive_path"])
        return cls(
            archive_path=path,
            archive_relative_path=payload.get("archive_relative_path"),
            source_revision=payload.get("source_revision"),
            source_checksum=payload.get("source_checksum"),
            members=tuple(CICY4FibrationMemberIndex.from_dict(row) for row in payload.get("members") or ()),
        )

    def write(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".tmp")
        temporary.write_text(canonical_json(self.to_dict()) + "\n", encoding="utf-8")
        temporary.replace(target)
        return target


@contextmanager
def open_archive_member(archive_path: str | Path, member_name: str) -> Iterator[Any]:
    with ZipFile(Path(archive_path)) as archive:
        with archive.open(member_name) as handle:
            yield handle


def iter_member_lines(archive_path: str | Path, member_name: str, *, encoding: str = "utf-8") -> Iterator[str]:
    with open_archive_member(archive_path, member_name) as handle:
        for line in handle:
            yield line.decode(encoding).rstrip("\n")


def build_cicy4_fibration_archive_index(
    archive_path: str | Path,
    *,
    archive_relative_path: str | None = None,
    source_revision: str | None = CICY4_FIBRATION_SOURCE_REVISION,
    source_checksum: str | None = None,
    parent_range_hints: dict[str, tuple[int, int]] | None = None,
    scan_text_members: bool = False,
) -> CICY4FibrationArchiveIndex:
    path = Path(archive_path).expanduser().resolve()
    hints = parent_range_hints or {}
    members: list[CICY4FibrationMemberIndex] = []
    with ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            if _unsafe_member(info.filename):
                raise StorageError(f"Unsafe archive member path: {info.filename}")
            parent_min: int | None
            parent_max: int | None
            record_count: int | None = None
            if info.filename in hints:
                parent_min, parent_max = hints[info.filename]
            else:
                parent_min, parent_max = _range_from_member_name(info.filename)
            if scan_text_members and (parent_min is None or parent_max is None or record_count is None):
                scanned_min, scanned_max, scanned_count = _scan_parent_range(archive, info.filename)
                parent_min = scanned_min if scanned_min is not None else parent_min
                parent_max = scanned_max if scanned_max is not None else parent_max
                record_count = scanned_count
            members.append(CICY4FibrationMemberIndex(
                member_name=info.filename,
                compressed_size=int(info.compress_size),
                file_size=int(info.file_size),
                parent_min=parent_min,
                parent_max=parent_max,
                record_count=record_count,
                checksum_crc32=int(info.CRC),
                metadata={"range_source": "hint_or_member_name" if not scan_text_members else "hint_member_name_or_streamed_member"},
            ))
    return CICY4FibrationArchiveIndex(
        archive_path=path,
        archive_relative_path=archive_relative_path,
        source_revision=source_revision,
        source_checksum=source_checksum,
        members=tuple(members),
    )


def read_cicy4_fibration_archive_index(path: str | Path, *, archive_path: str | Path | None = None, source_revision: str | None = None, source_checksum: str | None = None) -> CICY4FibrationArchiveIndex:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    index = CICY4FibrationArchiveIndex.from_dict(payload, archive_path=archive_path)
    expected_path = index.archive_path
    expected_fingerprint = _archive_fingerprint(expected_path, source_revision if source_revision is not None else index.source_revision, source_checksum if source_checksum is not None else index.source_checksum)
    if payload.get("archive_fingerprint") != expected_fingerprint:
        raise StorageError("CICY4 fibration archive index is stale for this source archive")
    return index


def _range_from_member_name(member_name: str) -> tuple[int | None, int | None]:
    groups = re.findall(r"\d+", PurePosixPath(member_name).stem)
    if len(groups) < 2:
        return None, None
    start = int(groups[-2])
    end = int(groups[-1])
    return (min(start, end), max(start, end))


def _scan_parent_range(archive: ZipFile, member_name: str) -> tuple[int | None, int | None, int]:
    parent_ids: list[int] = []
    with archive.open(member_name) as handle:
        for raw_line in handle:
            line = raw_line.decode("utf-8").strip()
            if not line:
                continue
            parent = _parent_from_line(line)
            if parent is not None:
                parent_ids.append(parent)
    if not parent_ids:
        return None, None, 0
    return min(parent_ids), max(parent_ids), len(parent_ids)


def _parent_from_line(line: str) -> int | None:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        match = re.search(r"\b(?:parent|parent_id|matrix_number|cicy4_id)\D+(\d+)\b", line)
        return int(match.group(1)) if match else None
    for key in _PARENT_KEYS:
        if key in payload:
            try:
                return int(payload[key])
            except (TypeError, ValueError):
                return None
    return None


def _unsafe_member(member: str) -> bool:
    path = PurePosixPath(member)
    return member.startswith("/") or "\\" in member or ".." in path.parts


def _archive_fingerprint(path: Path, source_revision: str | None, source_checksum: str | None) -> str:
    stat = path.stat()
    return stable_sha256({
        "archive_name": path.name,
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "source_revision": source_revision,
        "source_checksum": source_checksum,
    })
