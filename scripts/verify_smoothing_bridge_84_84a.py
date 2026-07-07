"""Generate exact-rational smoothing verification outputs for 84 and 84a."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.smoothing import write_default_verification_outputs  # noqa: E402


def main() -> None:
    records = write_default_verification_outputs(REPO_ROOT)
    print("Generated smoothing verification outputs:")
    for record in records:
        print(f"- smoothing_verification_{record.source_arrangement}.json ({record.overall_status})")
    print("- smoothing_verification_summary.csv")


if __name__ == "__main__":
    main()
