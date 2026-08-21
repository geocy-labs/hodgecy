from __future__ import annotations

from io import BytesIO
from pathlib import PurePosixPath
from zipfile import ZipFile

from .base import ParseResult, ParsedRecord, RejectedRecord, SourceChunk, parser_provenance, reject
from .block_text import BlockTextParser
from .jsonl import JsonlParser
from .mathematica import MathematicaRuleParser


class ZipArchiveParser:
    parser_name = "zip_archive"
    parser_version = "1.0.0"
    payload_type = "archive_member_record"

    def parse(self, source: SourceChunk) -> ParseResult:
        provenance = parser_provenance(self.parser_name, self.parser_version)
        records: list[ParsedRecord] = []
        rejected: list[RejectedRecord] = []
        with ZipFile(BytesIO(source.bytes())) as archive:
            for member in archive.namelist():
                if member.endswith("/"):
                    continue
                if _unsafe_member(member):
                    rejected.append(reject(
                        source,
                        parser_name=self.parser_name,
                        parser_version=self.parser_version,
                        error_code="unsafe_zip_member_path",
                        error_message="Archive member path is absolute, contains '..', or uses backslashes.",
                        payload_excerpt=member,
                        archive_member=member,
                    ))
                    continue
                member_bytes = archive.read(member)
                parser = _parser_for_member(member)
                if parser is None:
                    rejected.append(reject(
                        source,
                        parser_name=self.parser_name,
                        parser_version=self.parser_version,
                        error_code="unsupported_zip_member_type",
                        error_message="No fixture parser is registered for this archive member extension.",
                        payload_excerpt=member,
                        archive_member=member,
                    ))
                    continue
                member_source = SourceChunk(
                    dataset_id=source.dataset_id,
                    distribution_id=source.distribution_id,
                    payload=member_bytes,
                    relative_path=source.relative_path,
                    archive_member=member,
                    source_version=source.source_version,
                    source_url=source.source_url,
                    citation=source.citation,
                    doi=source.doi,
                    file_sha256=source.file_sha256,
                    metadata={**source.metadata, "zip_member": member},
                )
                result = parser.parse(member_source)
                records.extend(result.records)
                rejected.extend(result.rejected)
        return ParseResult(provenance, tuple(records), tuple(rejected))


def _unsafe_member(member: str) -> bool:
    path = PurePosixPath(member)
    return member.startswith("/") or "\\" in member or ".." in path.parts


def _parser_for_member(member: str):
    lowered = member.lower()
    if lowered.endswith(".jsonl"):
        return JsonlParser()
    if lowered.endswith(".txt") or lowered.endswith(".blocks"):
        return BlockTextParser()
    if lowered.endswith(".m") or lowered.endswith(".wl"):
        return MathematicaRuleParser()
    return None
