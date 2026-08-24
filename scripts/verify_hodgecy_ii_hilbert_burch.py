"""Write HodgeCY II Hilbert-Burch block-theorem evidence."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.geometry.hilbert_burch import write_hilbert_burch_evidence  # noqa: E402


def main() -> None:
    json_path, md_path, payload = write_hilbert_burch_evidence(REPO_ROOT)
    print("HodgeCY II Hilbert-Burch evidence generated")
    print(f"- status: {payload['status']}")
    print(f"- json: {json_path.relative_to(REPO_ROOT).as_posix()}")
    print(f"- markdown: {md_path.relative_to(REPO_ROOT).as_posix()}")


if __name__ == "__main__":
    main()
