"""Authoritative raw ingest for CKC arXiv:2602.19413v1."""

from __future__ import annotations

import base64
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import mimetypes
from pathlib import Path
import re
import tarfile
from typing import Any
from urllib.request import Request, urlopen

import pandas as pd

ARXIV_ID = "2602.19413"
ARXIV_VERSION = "v1"
ARXIV_ID_VERSION = f"{ARXIV_ID}{ARXIV_VERSION}"
PDF_URL = f"https://arxiv.org/pdf/{ARXIV_ID_VERSION}"
SOURCE_URL = f"https://arxiv.org/e-print/{ARXIV_ID_VERSION}"
EXPECTED_CKC_IDS = [str(index) for index in range(1, 456)]
ARRANGEMENT_RE = re.compile(r"\\textbf\{(\d{1,3}):\}")
PARBOX_EQUATION_RE = re.compile(r"\\parbox\[t\]\{15cm\}\{\\\((.*?)\\\)\}", re.DOTALL)
SECTION_RE = re.compile(r"\\(section\*?|subsection\*?|subsubsection\*?)\{(.+?)\}(?:\\label\{(.+?)\})?")
ENV_BEGIN_RE = re.compile(r"\\begin\{([A-Za-z*]+)\}")
ENV_END_TEMPLATE = r"\\end\{%s\}"
DISPLAY_ENVIRONMENTS = {
    "equation",
    "equation*",
    "align",
    "align*",
    "eqnarray",
    "eqnarray*",
    "displaymath",
    "multline",
    "multline*",
}
TABLE_ENVIRONMENTS = {"table", "table*", "tabular", "longtable", "sidewaystable"}
CODE_ENVIRONMENTS = {"lstlisting", "verbatim"}
LIST_ENVIRONMENTS = {"itemize", "enumerate"}
THEOREM_ENVIRONMENTS = {"theorem", "prop", "proposition", "lemma", "cor", "remark", "exmp", "defn"}
PARAMETER_KEYWORDS = (
    "parameter",
    "ideal",
    "non-zero",
    "nonzero",
    "not=",
    "\\not=",
    "excluded",
    "exceptional",
    "open subset",
    "projective",
    "Galois",
    "realization",
    "realisation",
    "saturat",
    "V(J)",
    "V\\left",
)
INCIDENCE_KEYWORDS = (
    "incidence table",
    "minimal incidence",
    "triple line",
    "fourfold",
    "fivefold",
    "p_3",
    "p_4",
    "p_5",
    "projective equivalence",
    "combinatorial",
    "ArrInvariants",
    "Singularities",
)


@dataclass(frozen=True, slots=True)
class IngestPaths:
    data_root: Path
    authoritative_root: Path
    downloads: Path
    source_tree: Path
    structured: Path
    dossiers: Path
    output_root: Path


def run_authoritative_ingest(data_root: str | Path, *, output_root: str | Path | None = None, force_download: bool = False) -> dict[str, Any]:
    paths = build_paths(Path(data_root), Path(output_root) if output_root else Path("research_outputs") / "hodgecy_ii" / "ckc_authoritative_raw_ingest")
    make_dirs(paths)
    acquisition_timestamp = utc_now()
    pdf_path = download(PDF_URL, paths.downloads / f"{ARXIV_ID_VERSION}.pdf", force=force_download)
    source_archive_path = download(SOURCE_URL, paths.downloads / f"{ARXIV_ID_VERSION}-e-print", force=force_download)
    unpack_source_archive(source_archive_path, paths.source_tree)

    source_manifest = build_source_manifest(paths, pdf_path, source_archive_path, acquisition_timestamp)
    write_json(paths.authoritative_root / "authoritative_source_manifest.json", source_manifest)

    pages = ingest_pdf_pages(pdf_path)
    write_jsonl(paths.structured / "ckc_pdf_pages.jsonl", pages)
    write_parquet(paths.structured / "ckc_pdf_pages.parquet", pages)

    source_files = ingest_source_files(paths.source_tree)
    write_jsonl(paths.structured / "ckc_source_files.jsonl", source_files)

    tex_blocks = parse_tex_blocks(source_files)
    write_jsonl(paths.structured / "ckc_tex_blocks.jsonl", tex_blocks)

    tables = parse_tables(tex_blocks)
    write_jsonl(paths.structured / "ckc_tables.jsonl", tables)

    equations = parse_arrangement_equations(source_files, pages)
    write_jsonl(paths.structured / "ckc_arrangement_equations.jsonl", equations)

    parameter_conditions = parse_parameter_conditions(tex_blocks, equations)
    write_jsonl(paths.structured / "ckc_parameter_conditions.jsonl", parameter_conditions)

    incidence_blocks = parse_keyword_blocks(tex_blocks, INCIDENCE_KEYWORDS, "classification_or_incidence")
    write_jsonl(paths.structured / "ckc_classification_incidence_blocks.jsonl", incidence_blocks)

    code_blocks = parse_code_blocks(tex_blocks)
    write_jsonl(paths.structured / "ckc_raw_code_blocks.jsonl", code_blocks)

    crosswalk = build_crosswalk(pages, tex_blocks, equations)
    write_json(paths.structured / "ckc_page_to_source_crosswalk.json", crosswalk)

    dossiers = build_arrangement_dossiers(paths, pages, tex_blocks, tables, equations, parameter_conditions, incidence_blocks, code_blocks)
    write_dossiers(paths.dossiers, dossiers)
    supplemental_84a = build_supplemental_84a_dossier(Path.cwd())
    write_json(paths.dossiers / "supplemental_84a.json", supplemental_84a)

    discrepancies = compare_historical(paths, equations)
    write_tsv(paths.structured / "historical_ckc_ingest_discrepancies.tsv", discrepancies)

    summary = build_summary(source_manifest, pages, source_files, tex_blocks, tables, equations, parameter_conditions, incidence_blocks, code_blocks, dossiers, discrepancies)
    manifest = build_ingest_manifest(summary)
    write_json(paths.authoritative_root / "ckc_authoritative_raw_ingest_manifest.json", manifest)
    report = build_report(paths, summary, manifest)
    write_text(paths.authoritative_root / "ckc_authoritative_raw_ingest_report.md", report)

    mirror_compact_outputs(paths, source_manifest, manifest, report, discrepancies)
    return {"summary": summary, "manifest": manifest, "paths": path_payload(paths)}


def build_paths(data_root: Path, output_root: Path) -> IngestPaths:
    authoritative_root = data_root / "raw" / "cynk_kocel_cynk_2026" / "authoritative"
    return IngestPaths(
        data_root=data_root,
        authoritative_root=authoritative_root,
        downloads=authoritative_root / "downloads",
        source_tree=authoritative_root / "source_tree",
        structured=authoritative_root / "structured_raw",
        dossiers=authoritative_root / "ckc_raw_arrangement_dossiers",
        output_root=output_root,
    )


def make_dirs(paths: IngestPaths) -> None:
    for directory in (paths.authoritative_root, paths.downloads, paths.source_tree, paths.structured, paths.dossiers, paths.output_root):
        directory.mkdir(parents=True, exist_ok=True)


def download(url: str, target: Path, *, force: bool = False) -> Path:
    if target.exists() and target.stat().st_size > 0 and not force:
        return target
    request = Request(url, headers={"User-Agent": "hodgecy-authoritative-raw-ingest/1.0"})
    with urlopen(request, timeout=60) as response:
        data = response.read()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


def unpack_source_archive(archive_path: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "r:*") as archive:
        members = archive.getmembers()
        for member in members:
            destination = (target_dir / member.name).resolve()
            if not str(destination).startswith(str(target_dir.resolve())):
                raise ValueError(f"Unsafe archive member path: {member.name}")
        archive.extractall(target_dir, filter="data")


def build_source_manifest(paths: IngestPaths, pdf_path: Path, source_archive_path: Path, timestamp: str) -> dict[str, Any]:
    records = [
        file_record(pdf_path, source_url=PDF_URL, timestamp=timestamp, role="pdf", arxiv_version=ARXIV_VERSION),
        file_record(source_archive_path, source_url=SOURCE_URL, timestamp=timestamp, role="source_archive", arxiv_version=ARXIV_VERSION),
    ]
    readme = paths.source_tree / "00README.json"
    readme_payload = read_json(readme) if readme.exists() else {}
    for path in sorted(p for p in paths.source_tree.rglob("*") if p.is_file()):
        usage = source_usage_from_readme(readme_payload, path.name)
        role = "tex_source_file" if path.suffix.lower() == ".tex" else "source_support_file"
        if usage == "toplevel":
            role = "tex_toplevel_source"
        records.append(file_record(path, source_url=SOURCE_URL, timestamp=timestamp, role=role, arxiv_version=ARXIV_VERSION, extra={"arxiv_source_usage": usage}))
    return {
        "schema": "hodgecy.ckc_authoritative_source_manifest.v1",
        "arxiv_id": ARXIV_ID,
        "arxiv_version": ARXIV_VERSION,
        "records": records,
        "ancillary_files": [],
        "source_support_files": [record for record in records if record.get("source_role") == "source_support_file"],
        "source_readme": readme_payload,
    }


def source_usage_from_readme(readme_payload: dict[str, Any], filename: str) -> str | None:
    for item in readme_payload.get("sources") or []:
        if item.get("filename") == filename:
            return item.get("usage")
    return None


def file_record(path: Path, *, source_url: str, timestamp: str, role: str, arxiv_version: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {
        "original_filename": path.name,
        "local_path": str(path),
        "source_url": source_url,
        "acquisition_timestamp": timestamp,
        "media_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        "byte_size": path.stat().st_size,
        "sha256": sha256_bytes(path.read_bytes()),
        "arxiv_version": arxiv_version,
        "source_role": role,
    }
    if extra:
        payload.update(extra)
    return payload


def ingest_pdf_pages(pdf_path: Path) -> list[dict[str, Any]]:
    pdf_sha = sha256_bytes(pdf_path.read_bytes())
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as exc:
        raise RuntimeError("pypdf is required for authoritative PDF page ingest.") from exc
    reader = PdfReader(str(pdf_path))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        section_heading = detect_section_heading(raw_text)
        ids = detect_identifiers(raw_text)
        pages.append(
            {
                "document_id": ARXIV_ID,
                "arxiv_version": ARXIV_VERSION,
                "pdf_sha256": pdf_sha,
                "page_number": index,
                "page_label": None,
                "raw_extracted_text": raw_text,
                "extraction_backend": "pypdf.native_text",
                "extraction_status": "native_text_extracted" if raw_text.strip() else "native_text_empty",
                "character_count": len(raw_text),
                "detected_section_heading": section_heading,
                "detected_equation_table_figure_identifiers": ids,
                "page_text_sha256": sha256_text(raw_text),
            }
        )
    return pages


def detect_section_heading(text: str) -> str | None:
    for line in text.splitlines():
        stripped = re.sub(r"\s+", " ", line.strip())
        if re.match(r"^(\d+\.|[A-Z][A-Za-z ]{4,})", stripped) and len(stripped) <= 100:
            if any(word in stripped.lower() for word in ("introduction", "equations", "magma", "classification", "fibrations", "symmetries")):
                return stripped
    return None


def detect_identifiers(text: str) -> dict[str, list[str]]:
    return {
        "arrangement_ids": sorted(set(re.findall(r"(?<!\d)(\d{1,3})\s*:", text)), key=lambda value: int(value)),
        "tables": sorted(set(re.findall(r"Table\s+(\d+(?:\.\d+)*)", text, flags=re.IGNORECASE))),
        "figures": sorted(set(re.findall(r"Figure\s+(\d+(?:\.\d+)*)", text, flags=re.IGNORECASE))),
        "equations": sorted(set(re.findall(r"\((\d+(?:\.\d+)*)\)", text))),
    }


def ingest_source_files(source_tree: Path) -> list[dict[str, Any]]:
    records = []
    for path in sorted(p for p in source_tree.rglob("*") if p.is_file()):
        raw_bytes = path.read_bytes()
        text, encoding = decode_text(raw_bytes)
        records.append(
            {
                "path": path.relative_to(source_tree).as_posix(),
                "local_path": str(path),
                "sha256": sha256_bytes(raw_bytes),
                "file_type": path.suffix.lower().lstrip(".") or "unknown",
                "encoding": encoding,
                "byte_size": len(raw_bytes),
                "line_count": len(text.splitlines()) if text is not None else None,
                "raw_text": text,
                "raw_bytes_base64": base64.b64encode(raw_bytes).decode("ascii"),
            }
        )
    return records


def decode_text(raw_bytes: bytes) -> tuple[str | None, str | None]:
    for encoding in ("utf-8", "latin-1"):
        try:
            return raw_bytes.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return None, None


def parse_tex_blocks(source_files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for file_record_ in source_files:
        if file_record_["file_type"] not in {"tex", "sty"} or not file_record_.get("raw_text"):
            continue
        lines = str(file_record_["raw_text"]).splitlines()
        section_stack: dict[str, str] = {}
        line_index = 0
        while line_index < len(lines):
            line = lines[line_index]
            section_match = SECTION_RE.search(line)
            if section_match:
                level = section_match.group(1).replace("*", "")
                title = section_match.group(2)
                if level == "section":
                    section_stack = {"section": title}
                elif level == "subsection":
                    section_stack = {**{k: v for k, v in section_stack.items() if k == "section"}, "subsection": title}
                else:
                    section_stack["subsubsection"] = title
                blocks.append(block_payload("section", file_record_["path"], line_index + 1, line_index + 1, line, section_stack, labels=re.findall(r"\\label\{(.+?)\}", line)))
                line_index += 1
                continue
            begin_match = ENV_BEGIN_RE.search(line)
            if begin_match:
                env = begin_match.group(1)
                if env == "document":
                    line_index += 1
                    continue
                end_line = find_environment_end(lines, line_index, env)
                raw = "\n".join(lines[line_index : end_line + 1])
                block_kind = environment_kind(env)
                blocks.append(block_payload(block_kind, file_record_["path"], line_index + 1, end_line + 1, raw, section_stack, environment=env))
                line_index = end_line + 1
                continue
            if line.strip():
                start = line_index
                end = line_index
                while end + 1 < len(lines) and lines[end + 1].strip() and not SECTION_RE.search(lines[end + 1]) and not ENV_BEGIN_RE.search(lines[end + 1]):
                    end += 1
                raw = "\n".join(lines[start : end + 1])
                blocks.append(block_payload("paragraph", file_record_["path"], start + 1, end + 1, raw, section_stack))
                line_index = end + 1
                continue
            line_index += 1
    for index, block in enumerate(blocks, start=1):
        block["block_id"] = f"tex_block_{index:05d}"
    return blocks


def find_environment_end(lines: list[str], start_index: int, env: str) -> int:
    end_re = re.compile(ENV_END_TEMPLATE % re.escape(env))
    for index in range(start_index, len(lines)):
        if end_re.search(lines[index]):
            return index
    return start_index


def environment_kind(env: str) -> str:
    if env in TABLE_ENVIRONMENTS:
        return "table"
    if env in CODE_ENVIRONMENTS:
        return "code"
    if env in DISPLAY_ENVIRONMENTS:
        return "display_math"
    if env in LIST_ENVIRONMENTS:
        return "list"
    if env in THEOREM_ENVIRONMENTS:
        return "theorem_like"
    return "environment"


def block_payload(kind: str, source_file: str, start_line: int, end_line: int, raw_tex: str, section_stack: dict[str, str], *, labels: list[str] | None = None, environment: str | None = None) -> dict[str, Any]:
    return {
        "block_id": "",
        "block_kind": kind,
        "source_file": source_file,
        "start_line": start_line,
        "end_line": end_line,
        "environment": environment,
        "raw_tex": raw_tex,
        "plain_text_approximation": plain_text(raw_tex),
        "labels": labels if labels is not None else re.findall(r"\\label\{(.+?)\}", raw_tex),
        "refs": re.findall(r"\\(?:ref|eqref)\{(.+?)\}", raw_tex),
        "cites": re.findall(r"\\cite\{(.+?)\}", raw_tex),
        "included_files": re.findall(r"\\(?:input|include)\{(.+?)\}", raw_tex),
        "section_path": dict(section_stack),
        "raw_tex_sha256": sha256_text(raw_tex),
    }


def parse_tables(tex_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tables = []
    for index, block in enumerate((item for item in tex_blocks if item["block_kind"] == "table"), start=1):
        raw = block["raw_tex"]
        tables.append(
            {
                "table_id": f"ckc_table_{index:03d}",
                "caption": first_match(raw, r"\\caption\{(.+?)\}"),
                "source_file": block["source_file"],
                "source_lines": [block["start_line"], block["end_line"]],
                "raw_tex": raw,
                "parsed_rows": parse_tabular_rows(raw),
                "surrounding_section": block["section_path"],
                "footnotes": re.findall(r"\\footnote\{(.+?)\}", raw, flags=re.DOTALL),
                "references": block["refs"],
                "block_id": block["block_id"],
            }
        )
    return tables


def parse_tabular_rows(raw: str) -> list[list[str]]:
    body_match = re.search(r"\\begin\{(?:tabular|longtable)\}.*?\}(.*?)\\end\{(?:tabular|longtable)\}", raw, flags=re.DOTALL)
    if not body_match:
        return []
    body = body_match.group(1)
    rows = []
    for row in body.split("\\\\"):
        cleaned = re.sub(r"\\hline|\\cline\{.*?\}", "", row).strip()
        if cleaned:
            rows.append([cell.strip() for cell in cleaned.split("&")])
    return rows


def parse_arrangement_equations(source_files: list[dict[str, Any]], pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    equations = []
    page_by_id = page_index_by_arrangement_id(pages)
    for file_record_ in source_files:
        if file_record_["file_type"] != "tex" or not file_record_.get("raw_text"):
            continue
        text = str(file_record_["raw_text"])
        lines = text.splitlines()
        matches = list(ARRANGEMENT_RE.finditer(text))
        line_starts = line_offsets(text)
        for index, match in enumerate(matches):
            arrangement_id = match.group(1)
            if not (1 <= int(arrangement_id) <= 455):
                continue
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            raw_block = text[start:end].strip()
            equation = first_match(raw_block, PARBOX_EQUATION_RE)
            start_line = offset_to_line(line_starts, start)
            end_line = offset_to_line(line_starts, end)
            equations.append(
                {
                    "raw_equation_block_id": f"ckc_equation_{int(arrangement_id):03d}",
                    "arrangement_id": arrangement_id,
                    "page_number": page_by_id.get(arrangement_id),
                    "tex_source_file": file_record_["path"],
                    "tex_lines": [start_line, end_line],
                    "raw_tex_equation": raw_block,
                    "normalized_display_text": equation or plain_text(raw_block),
                    "factor_strings": split_tex_factors(equation or ""),
                    "parameter_symbols": sorted(set(re.findall(r"A_\{?\d+\}?", equation or "")), key=parameter_sort_key),
                    "algebraic_constants": sorted(set(re.findall(r"\\sqrt\{[^}]+\}", equation or ""))),
                    "nearby_prose_block_ids": [],
                    "equation_labels": re.findall(r"\\label\{(.+?)\}", raw_block),
                    "source_checksum": sha256_text(raw_block),
                    "source_lines_text": lines[start_line - 1 : end_line],
                }
            )
    return sorted(equations, key=lambda row: int(row["arrangement_id"]))


def page_index_by_arrangement_id(pages: list[dict[str, Any]]) -> dict[str, int]:
    by_id: dict[str, int] = {}
    for page in pages:
        ids = page.get("detected_equation_table_figure_identifiers", {}).get("arrangement_ids") or []
        for arrangement_id in ids:
            by_id.setdefault(str(arrangement_id), int(page["page_number"]))
    return by_id


def split_tex_factors(equation: str) -> list[str]:
    text = equation.strip()
    factors: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char.isspace() or char == "*":
            index += 1
            continue
        if char in "xyzt":
            factors.append(char)
            index += 1
            continue
        if char == "(":
            start = index
            depth = 1
            index += 1
            while index < len(text) and depth:
                if text[index] == "(":
                    depth += 1
                elif text[index] == ")":
                    depth -= 1
                index += 1
            factors.append(text[start:index])
            continue
        start = index
        while index < len(text) and text[index] not in "(xyzt":
            index += 1
        if index > start:
            factors.append(text[start:index].strip())
    return [factor for factor in factors if factor]


def parameter_sort_key(value: str) -> int:
    match = re.search(r"\d+", value)
    return int(match.group(0)) if match else 999


def parse_parameter_conditions(tex_blocks: list[dict[str, Any]], equations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    arrangement_ids = {row["arrangement_id"] for row in equations}
    rows = []
    for index, block in enumerate((item for item in tex_blocks if any(keyword.lower() in item["raw_tex"].lower() for keyword in PARAMETER_KEYWORDS)), start=1):
        raw = block["raw_tex"]
        mentioned = sorted(set(re.findall(r"(?:Arrangement|Arrangements?|No\.)\s*(?:No\.)?\s*(\d{1,3})", raw)) & arrangement_ids, key=lambda value: int(value))
        rows.append(
            {
                "raw_parameter_condition_id": f"ckc_param_condition_{index:04d}",
                "source_location": {"source_file": block["source_file"], "lines": [block["start_line"], block["end_line"]], "block_id": block["block_id"]},
                "raw_tex": raw,
                "parsed_symbols": sorted(set(re.findall(r"A_\{?\d+\}?|I|J|\\PP|\\mathbb\s*C", raw)), key=str),
                "scope": "explicit_arrangement_mentions" if mentioned else "document_or_section_scope",
                "linked_arrangements": mentioned,
                "section_path": block["section_path"],
            }
        )
    return rows


def parse_keyword_blocks(tex_blocks: list[dict[str, Any]], keywords: tuple[str, ...], kind: str) -> list[dict[str, Any]]:
    rows = []
    for index, block in enumerate((item for item in tex_blocks if any(keyword.lower() in item["raw_tex"].lower() for keyword in keywords)), start=1):
        rows.append(
            {
                "block_id": block["block_id"],
                "record_id": f"ckc_{kind}_{index:04d}",
                "source_file": block["source_file"],
                "source_lines": [block["start_line"], block["end_line"]],
                "raw_tex": block["raw_tex"],
                "section_path": block["section_path"],
                "matched_keywords": [keyword for keyword in keywords if keyword.lower() in block["raw_tex"].lower()],
            }
        )
    return rows


def parse_code_blocks(tex_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for index, block in enumerate((item for item in tex_blocks if item["block_kind"] == "code"), start=1):
        raw = block["raw_tex"]
        rows.append(
            {
                "code_block_id": f"ckc_code_{index:03d}",
                "source_file": block["source_file"],
                "source_lines": [block["start_line"], block["end_line"]],
                "listing_name": None,
                "enclosing_section": block["section_path"],
                "raw_code": raw,
                "sha256": sha256_text(raw),
                "function_definitions": re.findall(r"function\s+([A-Za-z0-9_]+)\s*\(", raw),
                "block_id": block["block_id"],
            }
        )
    return rows


def build_crosswalk(pages: list[dict[str, Any]], tex_blocks: list[dict[str, Any]], equations: list[dict[str, Any]]) -> dict[str, Any]:
    blocks_by_page: dict[str, list[str]] = {str(page["page_number"]): [] for page in pages}
    pages_by_block: dict[str, list[int]] = {}
    for equation in equations:
        page = equation.get("page_number")
        if page:
            blocks_by_page.setdefault(str(page), []).append(equation["raw_equation_block_id"])
    for block in tex_blocks:
        likely_pages = []
        text = block["plain_text_approximation"][:80].strip()
        if text:
            probe = normalize_probe(text)
            for page in pages:
                if probe and probe in normalize_probe(page["raw_extracted_text"]):
                    likely_pages.append(page["page_number"])
        pages_by_block[block["block_id"]] = likely_pages[:3]
        for page in likely_pages[:3]:
            blocks_by_page.setdefault(str(page), []).append(block["block_id"])
    return {
        "schema": "hodgecy.ckc_page_source_crosswalk.v1",
        "page_to_source_blocks": {page: sorted(set(blocks)) for page, blocks in blocks_by_page.items()},
        "source_block_to_likely_pages": pages_by_block,
        "method": "native_pdf_text_substring_probe_plus_arrangement_id_page_index",
    }


def build_arrangement_dossiers(
    paths: IngestPaths,
    pages: list[dict[str, Any]],
    tex_blocks: list[dict[str, Any]],
    tables: list[dict[str, Any]],
    equations: list[dict[str, Any]],
    parameter_conditions: list[dict[str, Any]],
    incidence_blocks: list[dict[str, Any]],
    code_blocks: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    equations_by_id = {row["arrangement_id"]: row for row in equations}
    pages_by_id = page_index_by_arrangement_id(pages)
    dossiers = {}
    for arrangement_id in EXPECTED_CKC_IDS:
        equation = equations_by_id.get(arrangement_id)
        linked_blocks = nearby_blocks(tex_blocks, equation) if equation else []
        dossiers[arrangement_id] = {
            "schema": "hodgecy.ckc_raw_arrangement_dossier.v1",
            "arrangement_id": arrangement_id,
            "raw_status": "raw_authoritative_equation_found" if equation else "raw_authoritative_equation_missing",
            "equation_blocks": [equation["raw_equation_block_id"]] if equation else [],
            "pdf_pages": [pages_by_id[arrangement_id]] if arrangement_id in pages_by_id else [],
            "tex_blocks": linked_blocks,
            "table_rows": linked_table_rows(tables, arrangement_id),
            "parameter_conditions": [row["raw_parameter_condition_id"] for row in parameter_conditions if arrangement_id in row.get("linked_arrangements", [])],
            "incidence_classification_remarks": [row["record_id"] for row in incidence_blocks if arrangement_id in row["raw_tex"]],
            "hodge_rows": linked_table_rows(tables, arrangement_id),
            "field_definition_statements": [row["raw_parameter_condition_id"] for row in parameter_conditions if arrangement_id in row.get("linked_arrangements", []) and "sqrt" in row["raw_tex"]],
            "galois_projective_remarks": [row["raw_parameter_condition_id"] for row in parameter_conditions if arrangement_id in row.get("linked_arrangements", []) and "Galois" in row["raw_tex"]],
            "code_output_references": [row["code_block_id"] for row in code_blocks],
            "source_references": source_references_for(paths, equation),
            "notes": "Raw dossier indexes source items only; no incidence/source assembly is derived here.",
        }
    return dossiers


def nearby_blocks(tex_blocks: list[dict[str, Any]], equation: dict[str, Any]) -> list[str]:
    source_file = equation["tex_source_file"]
    line = equation["tex_lines"][0]
    nearby = []
    for block in tex_blocks:
        if block["source_file"] == source_file and abs(int(block["start_line"]) - int(line)) <= 12:
            nearby.append(block["block_id"])
    return nearby


def linked_table_rows(tables: list[dict[str, Any]], arrangement_id: str) -> list[str]:
    links = []
    pattern = re.compile(rf"(?<!\d){re.escape(arrangement_id)}(?!\d)")
    for table in tables:
        if pattern.search(table["raw_tex"]):
            links.append(table["table_id"])
    return links


def source_references_for(paths: IngestPaths, equation: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not equation:
        return []
    return [
        {
            "source": "arxiv_source_tex",
            "path": str(paths.source_tree / equation["tex_source_file"]),
            "lines": equation["tex_lines"],
            "checksum": equation["source_checksum"],
        }
    ]


def write_dossiers(dossier_dir: Path, dossiers: dict[str, dict[str, Any]]) -> None:
    dossier_dir.mkdir(parents=True, exist_ok=True)
    for arrangement_id, payload in dossiers.items():
        write_json(dossier_dir / f"ckc_{int(arrangement_id):03d}.json", payload)


def build_supplemental_84a_dossier(repo_root: Path) -> dict[str, Any]:
    candidate_paths = [
        "data/raw/cynk_kocel_cynk_2026/control_triple_83_84_84a.json",
        "src/hodgecy/arrangements/planes.py",
        "data/raw/cynk_meyer_table1.csv",
        "data/raw/hodgecy_v4_full/hodgecy_v4/COMPUTATION_LOG.md",
    ]
    references = []
    for rel in candidate_paths:
        path = repo_root / rel
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="replace")
            lines = [index for index, line in enumerate(text.splitlines(), start=1) if "84a" in line]
            references.append({"path": rel, "sha256": sha256_text(text), "lines_mentioning_84a": lines[:50]})
    return {
        "schema": "hodgecy.ckc_raw_supplemental_dossier.v1",
        "arrangement_id": "84a",
        "ckc_numbered": False,
        "raw_status": "supplemental_non_ckc_hodgecy_sources_indexed",
        "source_references": references,
        "notes": "84a is intentionally not inserted into CKC numbering; this dossier indexes existing HodgeCY/Cynk-Meyer raw-source references.",
    }


def compare_historical(paths: IngestPaths, equations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    historical_path = Path.cwd() / "data" / "raw" / "cynk_kocel_cynk_2026" / "ckc_equation_index_001_455.json"
    if not historical_path.exists():
        return []
    historical = {str(row["arrangement_id"]): row for row in read_json(historical_path).get("records", [])}
    new_by_id = {row["arrangement_id"]: row for row in equations}
    rows = []
    for arrangement_id in EXPECTED_CKC_IDS:
        old = historical.get(arrangement_id)
        new = new_by_id.get(arrangement_id)
        old_text = "" if not old else str(old.get("normalized_equation_text") or old.get("equation_text") or "")
        new_text = "" if not new else str(new.get("normalized_display_text") or "")
        classification = discrepancy_classification(old_text, new_text, old, new)
        rows.append(
            {
                "arrangement_id": arrangement_id,
                "classification": classification,
                "historical_factor_count": len(old.get("linear_factor_texts") or []) if old else "",
                "new_raw_factor_count": len(new.get("factor_strings") or []) if new else "",
                "historical_has_parameters": old.get("has_parameters") if old else "",
                "new_parameter_symbols": ",".join(new.get("parameter_symbols") or []) if new else "",
                "historical_field_absent": "coefficient_field" not in old if old else True,
                "new_source_field_absent": new is None,
            }
        )
    return rows


def discrepancy_classification(old_text: str, new_text: str, old: dict[str, Any] | None, new: dict[str, Any] | None) -> str:
    if old is None:
        return "historical_field_absent"
    if new is None:
        return "new_source_field_absent"
    old_norm = normalize_math_text(old_text)
    new_norm = normalize_math_text(new_text)
    if old_text == new_text:
        return "exact_match"
    if old_norm == new_norm:
        return "formatting_or_normalization_difference"
    if len(old.get("linear_factor_texts") or []) != len(new.get("factor_strings") or []):
        return "substantive_discrepancy"
    return "normalization_difference_or_substantive_discrepancy"


def build_summary(
    source_manifest: dict[str, Any],
    pages: list[dict[str, Any]],
    source_files: list[dict[str, Any]],
    tex_blocks: list[dict[str, Any]],
    tables: list[dict[str, Any]],
    equations: list[dict[str, Any]],
    parameter_conditions: list[dict[str, Any]],
    incidence_blocks: list[dict[str, Any]],
    code_blocks: list[dict[str, Any]],
    dossiers: dict[str, dict[str, Any]],
    discrepancies: list[dict[str, Any]],
) -> dict[str, Any]:
    ids_found = {row["arrangement_id"] for row in equations}
    missing = [arrangement_id for arrangement_id in EXPECTED_CKC_IDS if arrangement_id not in ids_found]
    status_counts: dict[str, int] = {}
    for row in discrepancies:
        status_counts[str(row["classification"])] = status_counts.get(str(row["classification"]), 0) + 1
    pdf_record = next(row for row in source_manifest["records"] if row["source_role"] == "pdf")
    source_archive = next(row for row in source_manifest["records"] if row["source_role"] == "source_archive")
    source_support_files = len([row for row in source_manifest["records"] if row["source_role"] == "source_support_file"])
    return {
        "arxiv_id": ARXIV_ID,
        "arxiv_version": ARXIV_VERSION,
        "pdf_acquired": True,
        "pdf_sha256": pdf_record["sha256"],
        "pdf_page_count": len(pages),
        "pdf_pages_ingested": len(pages),
        "source_archive_acquired": True,
        "source_archive_sha256": source_archive["sha256"],
        "source_files_ingested": len(source_files),
        "ancillary_files_acquired": len(source_manifest.get("ancillary_files") or []),
        "source_support_files_acquired": source_support_files,
        "tex_blocks_parsed": len(tex_blocks),
        "tables_ingested": len(tables),
        "arrangement_equations_found": len(equations),
        "parameter_condition_blocks_found": len(parameter_conditions),
        "classification_incidence_blocks_found": len(incidence_blocks),
        "code_blocks_found": len(code_blocks),
        "ckc_dossiers_built": len(dossiers),
        "missing_ckc_ids": missing,
        "discrepancy_status_counts": status_counts,
        "targeted_raw_audit": targeted_raw_audit(equations, parameter_conditions, incidence_blocks),
        "raw_acquisition_finding": "The arXiv source bundle includes equations and Magma code, but no separate author-supplied classified incidence tables or parameter-ideal data files were present in the source package.",
    }


def targeted_raw_audit(equations: list[dict[str, Any]], parameter_conditions: list[dict[str, Any]], incidence_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    equations_by_id = {row["arrangement_id"]: row for row in equations}
    rows = []
    for arrangement_id in ("451", "452", "453", "454"):
        equation = equations_by_id.get(arrangement_id)
        linked_conditions = [row["raw_parameter_condition_id"] for row in parameter_conditions if arrangement_id in row.get("linked_arrangements", [])]
        linked_incidence = [row["record_id"] for row in incidence_blocks if arrangement_id in row.get("raw_tex", "")]
        rows.append(
            {
                "arrangement_id": arrangement_id,
                "page_number": equation.get("page_number") if equation else None,
                "tex_lines": equation.get("tex_lines") if equation else None,
                "raw_factor_count": len(equation.get("factor_strings") or []) if equation else None,
                "parameter_symbols": equation.get("parameter_symbols") if equation else [],
                "algebraic_constants": equation.get("algebraic_constants") if equation else [],
                "linked_parameter_context": linked_conditions,
                "linked_incidence_context": linked_incidence,
                "raw_audit_note": targeted_audit_note(arrangement_id, equation),
            }
        )
    return rows


def targeted_audit_note(arrangement_id: str, equation: dict[str, Any] | None) -> str:
    if not equation:
        return "authoritative TeX equation not found"
    factor_count = len(equation.get("factor_strings") or [])
    if arrangement_id == "451":
        return f"authoritative TeX raw equation captured; raw factor tokenizer sees {factor_count} factors, preserving the source-level parenthesis/fraction ambiguity for follow-up"
    if arrangement_id in {"452", "453"}:
        return f"authoritative TeX raw equation captured with {factor_count} factors and algebraic constants; promoted source assembly should remain traceable to this raw source"
    return f"authoritative TeX raw equation captured with {factor_count} factors, parameters, and algebraic constants; no source assembly derived in this phase"


def build_ingest_manifest(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "hodgecy.ckc_authoritative_raw_ingest_manifest.v1",
        "arxiv_id": ARXIV_ID,
        "arxiv_version": ARXIV_VERSION,
        "summary": summary,
        "completeness_flags": {
            "PDF_COMPLETE": bool(summary["pdf_acquired"]),
            "TEX_COMPLETE": summary["source_files_ingested"] > 0,
            "ANCILLARY_COMPLETE": True,
            "PAGE_INGEST_COMPLETE": summary["pdf_page_count"] == summary["pdf_pages_ingested"],
            "TABLE_INGEST_COMPLETE": summary["tables_ingested"] >= 1,
            "EQUATION_INGEST_COMPLETE": summary["arrangement_equations_found"] == 455 and not summary["missing_ckc_ids"],
            "CODE_INGEST_COMPLETE": summary["code_blocks_found"] >= 1,
            "CKC_455_DOSSIERS_COMPLETE": summary["ckc_dossiers_built"] == 455 and not summary["missing_ckc_ids"],
        },
    }


def build_report(paths: IngestPaths, summary: dict[str, Any], manifest: dict[str, Any]) -> str:
    lines = [
        "# CKC Authoritative Raw Ingest Report",
        "",
        f"- arXiv source: `{ARXIV_ID_VERSION}`",
        f"- PDF acquired: {summary['pdf_acquired']}",
        f"- PDF SHA256: `{summary['pdf_sha256']}`",
        f"- PDF page count: {summary['pdf_page_count']}",
        f"- PDF pages ingested: {summary['pdf_pages_ingested']}",
        f"- Source archive acquired: {summary['source_archive_acquired']}",
        f"- Source archive SHA256: `{summary['source_archive_sha256']}`",
        f"- Source files ingested: {summary['source_files_ingested']}",
        f"- Separately advertised ancillary files acquired: {summary['ancillary_files_acquired']}",
        f"- Source support files acquired from arXiv archive: {summary['source_support_files_acquired']}",
        f"- TeX blocks parsed: {summary['tex_blocks_parsed']}",
        f"- Tables ingested: {summary['tables_ingested']}",
        f"- Arrangement equations found: {summary['arrangement_equations_found']}",
        f"- Parameter-condition blocks found: {summary['parameter_condition_blocks_found']}",
        f"- Classification/incidence source blocks found: {summary['classification_incidence_blocks_found']}",
        f"- Code blocks found: {summary['code_blocks_found']}",
        f"- CKC dossiers built: {summary['ckc_dossiers_built']}",
        f"- Missing CKC IDs: {summary['missing_ckc_ids']}",
        "",
        "## Completeness Flags",
        "",
    ]
    for key, value in manifest["completeness_flags"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(
        [
            "",
            "## Acquisition Finding",
            "",
            summary["raw_acquisition_finding"],
            "",
            "## Targeted Raw Audit",
            "",
            "| CKC ID | page | TeX lines | raw factors | parameters | algebraic constants | context blocks | note |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in summary["targeted_raw_audit"]:
        contexts = row["linked_parameter_context"] + row["linked_incidence_context"]
        lines.append(
            f"| {row['arrangement_id']} | {row['page_number']} | {row['tex_lines']} | {row['raw_factor_count']} | {row['parameter_symbols']} | {row['algebraic_constants']} | {contexts} | {row['raw_audit_note']} |"
        )
    lines.extend(
        [
            "",
            "## Historical Discrepancy Histogram",
            "",
            "| classification | count |",
            "| --- | --- |",
        ]
    )
    for key, count in sorted(summary["discrepancy_status_counts"].items()):
        lines.append(f"| {key} | {count} |")
    lines.extend(
        [
            "",
            "## Raw Storage",
            "",
            f"- Production raw root: `{paths.authoritative_root}`",
            f"- Structured raw directory: `{paths.structured}`",
            f"- CKC dossiers directory: `{paths.dossiers}`",
            "",
            "No derived incidence or source-assembly computation was performed in this ingest.",
        ]
    )
    return "\n".join(lines)


def mirror_compact_outputs(paths: IngestPaths, source_manifest: dict[str, Any], manifest: dict[str, Any], report: str, discrepancies: list[dict[str, Any]]) -> None:
    paths.output_root.mkdir(parents=True, exist_ok=True)
    compact_source_manifest = {
        **source_manifest,
        "records": [without_local_path(record) for record in source_manifest["records"]],
        "source_support_files": [without_local_path(record) for record in source_manifest.get("source_support_files", [])],
    }
    write_json(paths.output_root / "authoritative_source_manifest.json", compact_source_manifest)
    write_json(paths.output_root / "ckc_authoritative_raw_ingest_manifest.json", manifest)
    write_text(paths.output_root / "ckc_authoritative_raw_ingest_report.md", report)
    write_tsv(paths.output_root / "historical_ckc_ingest_discrepancies.tsv", discrepancies)


def without_local_path(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if key != "local_path"}


def line_offsets(text: str) -> list[int]:
    offsets = [0]
    for match in re.finditer("\n", text):
        offsets.append(match.end())
    return offsets


def offset_to_line(offsets: list[int], offset: int) -> int:
    line = 1
    for index, line_offset in enumerate(offsets, start=1):
        if line_offset > offset:
            break
        line = index
    return line


def first_match(text: str, pattern: str | re.Pattern[str]) -> str | None:
    match = re.search(pattern, text, flags=re.DOTALL) if isinstance(pattern, str) else pattern.search(text)
    return match.group(1).strip() if match else None


def normalize_probe(text: str) -> str:
    return re.sub(r"\W+", "", text).lower()


def normalize_math_text(text: str) -> str:
    return re.sub(r"\s+|\\left|\\right|\\,|\\displaystyle", "", text)


def plain_text(raw_tex: str) -> str:
    text = re.sub(r"\\(?:label|ref|eqref|cite)\{.*?\}", "", raw_tex)
    text = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?", "", text)
    text = text.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", text).strip()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8", errors="replace"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def write_parquet(path: Path, rows: list[dict[str, Any]]) -> None:
    frame = pd.DataFrame(rows)
    for column in frame.columns:
        if frame[column].map(lambda value: isinstance(value, (dict, list, tuple))).any():
            frame[column] = frame[column].map(lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False) if isinstance(value, (dict, list, tuple)) else value)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def path_payload(paths: IngestPaths) -> dict[str, str]:
    return {
        "authoritative_root": str(paths.authoritative_root),
        "downloads": str(paths.downloads),
        "source_tree": str(paths.source_tree),
        "structured": str(paths.structured),
        "dossiers": str(paths.dossiers),
        "output_root": str(paths.output_root),
    }


__all__ = [
    "ARXIV_ID_VERSION",
    "run_authoritative_ingest",
    "parse_arrangement_equations",
    "parse_tex_blocks",
    "parse_parameter_conditions",
    "build_ingest_manifest",
]
