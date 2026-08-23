from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.research.ckc_authoritative_raw_ingest import run_authoritative_ingest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Acquire and ingest authoritative raw CKC arXiv source material.")
    parser.add_argument("--root", required=True, help="Production HODGECY_DATA_ROOT.")
    parser.add_argument("--output-root", default=str(REPO_ROOT / "research_outputs" / "hodgecy_ii" / "ckc_authoritative_raw_ingest"))
    parser.add_argument("--force-download", action="store_true", help="Re-download arXiv PDF/source even if local copies exist.")
    args = parser.parse_args(argv)

    result = run_authoritative_ingest(args.root, output_root=args.output_root, force_download=args.force_download)
    summary = result["summary"]
    manifest = result["manifest"]
    flags = manifest["completeness_flags"]
    print("CKC authoritative raw ingest complete")
    print(f"- arXiv: {summary['arxiv_id']}{summary['arxiv_version']}")
    print(f"- PDF pages ingested: {summary['pdf_pages_ingested']} / {summary['pdf_page_count']}")
    print(f"- source files ingested: {summary['source_files_ingested']}")
    print(f"- arrangement equations found: {summary['arrangement_equations_found']} / 455")
    print(f"- CKC dossiers built: {summary['ckc_dossiers_built']} / 455")
    print(f"- missing CKC IDs: {summary['missing_ckc_ids']}")
    print(f"- completeness flags: {flags}")
    print(f"- report: {Path(args.output_root) / 'ckc_authoritative_raw_ingest_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
