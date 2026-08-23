from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.research.ckc_authoritative_staging import run_authoritative_staging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stage authoritative CKC records and reconstruct generic incidence.")
    parser.add_argument("--root", required=True, help="Production HODGECY_DATA_ROOT containing authoritative CKC raw ingest.")
    parser.add_argument("--output-root", default=str(REPO_ROOT / "research_outputs" / "hodgecy_ii" / "ckc_authoritative_staging"))
    args = parser.parse_args(argv)

    summary = run_authoritative_staging(args.root, output_root=args.output_root)
    print("CKC authoritative staging and incidence reconstruction complete")
    for key in (
        "CKC_STAGED_RECORDS",
        "EXACT_8_FACTOR_PARSES",
        "HISTORICAL_CANONICAL_MATCHES",
        "HISTORICAL_TRUE_SUBSTANTIVE_DISCREPANCIES",
        "INCIDENCE_MATCH_WITHOUT_EXTRA_CONSTRAINTS",
        "INCIDENCE_MATCH_AFTER_SCOPED_CONSTRAINTS",
        "INCIDENCE_STILL_MISMATCHED",
        "EXACT_CKC_SOURCE_ASSEMBLIES",
        "TOTAL_WITH_84A",
        "451_STATUS",
        "454_STATUS",
        "83_STATUS",
    ):
        print(f"- {key} = {summary[key]}")
    print(f"- output directory: {args.output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
