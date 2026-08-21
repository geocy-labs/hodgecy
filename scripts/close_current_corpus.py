from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from hodgecy.bootstrap import CorpusBootstrapConfig, CorpusClosureConfig, bootstrap_current_corpus, close_current_corpus


def _git_head() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Close the current HodgeCY corpus integration state.")
    parser.add_argument("--root", type=Path, required=True, help="External HodgeCY data root")
    parser.add_argument("--catalog-name", default="current_corpus")
    parser.add_argument("--batch-size", type=int, default=50_000)
    parser.add_argument("--skip-bootstrap", action="store_true")
    parser.add_argument("--remote-verified", action="store_true")
    args = parser.parse_args()
    commit = _git_head()
    if not args.skip_bootstrap:
        bootstrap_current_corpus(CorpusBootstrapConfig(args.root, catalog_name=args.catalog_name, batch_size=args.batch_size, hodgecy_commit=commit))
    result = close_current_corpus(CorpusClosureConfig(args.root, catalog_name=args.catalog_name, hodgecy_commit=commit, remote_verified=args.remote_verified, pushed_commit=commit if args.remote_verified else None))
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
