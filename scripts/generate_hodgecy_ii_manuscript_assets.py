"""Generate HodgeCY II fidelity-census manuscript assets."""

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.research.hodgecy_ii_fidelity_census import generate_hodgecy_ii_manuscript_assets  # noqa: E402


def main() -> None:
    result = generate_hodgecy_ii_manuscript_assets()
    summary = result["summary"]
    print("HodgeCY II manuscript assets generated")
    print(f"- total processed: {summary['total_processed']}")
    print(f"- nontrivial pairs/sets: {summary['nontrivial_pairs_sets']}")
    print(f"- scope manifest: {result['scope_manifest']}")
    print(f"- asset manifest: {result['asset_manifest']}")


if __name__ == "__main__":
    main()
