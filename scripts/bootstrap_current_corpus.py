from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from hodgecy.bootstrap import CorpusBootstrapConfig, bootstrap_current_corpus


def _git_head() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap the current acquired HodgeCY corpus into the production catalog.")
    parser.add_argument("--root", required=True, help="HODGECY_DATA_ROOT")
    parser.add_argument("--catalog-name", default="current_corpus")
    parser.add_argument("--batch-size", type=int, default=50000)
    args = parser.parse_args()
    result = bootstrap_current_corpus(CorpusBootstrapConfig(
        data_root=Path(args.root),
        catalog_name=args.catalog_name,
        batch_size=args.batch_size,
        hodgecy_commit=_git_head(),
        hodgecy_version="0.2.0",
    ))
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
