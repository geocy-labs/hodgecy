from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from hodgecy.bootstrap import Wave2IngestConfig, ingest_wave2_sources


def _git_head() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Permanently ingest Wave 2 acquired sources into the current HodgeCY corpus.")
    parser.add_argument("--root", required=True, help="HODGECY_DATA_ROOT")
    parser.add_argument("--catalog-name", default="current_corpus")
    parser.add_argument("--batch-size", type=int, default=100_000)
    parser.add_argument("--pushed-commit")
    parser.add_argument("--remote-verified", action="store_true")
    parser.add_argument("--tests-run", action="append", default=[])
    parser.add_argument("--tests-passed", action="store_true")
    parser.add_argument("--hodgecy-i-regressions", default="pending_final_run")
    args = parser.parse_args()
    result = ingest_wave2_sources(Wave2IngestConfig(
        data_root=Path(args.root),
        catalog_name=args.catalog_name,
        batch_size=args.batch_size,
        hodgecy_commit=_git_head(),
        pushed_commit=args.pushed_commit,
        remote_verified=args.remote_verified,
        tests_run=tuple(args.tests_run),
        tests_passed=args.tests_passed,
        hodgecy_i_regressions=args.hodgecy_i_regressions,
    ))
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
