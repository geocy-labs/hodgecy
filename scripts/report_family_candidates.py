"""Generate candidate-report rows for selected Cynk--Meyer one-parameter families."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.datasets.cynk_meyer import load_family_equations, load_table1, validate_table1


TARGET_FAMILIES = ["1", "5", "14"]


def main() -> None:
    table = load_table1()
    validate_table1(table)
    families = pd.DataFrame(load_family_equations())
    families["family_id"] = families["family_id"].astype(str)

    rows: list[dict[str, object]] = []
    for arrangement in TARGET_FAMILIES:
        table_row = table.loc[table["arrangement"].astype(str) == arrangement]
        family_row = families.loc[families["family_id"] == arrangement]
        if table_row.empty or family_row.empty:
            raise ValueError(f"Missing Table 1 or family-equation entry for arrangement {arrangement}")

        source_row = table_row.iloc[0]
        equation_row = family_row.iloc[0]
        rows.append(
            {
                "arrangement": arrangement,
                "equation": equation_row["equation"],
                "h12": source_row["h12"],
                "h11": source_row["h11"],
                "euler": source_row["euler"],
                "hodgecy_role": "family_operator_candidate",
                "nodal_special_fibers_known": "unknown",
                "operator_data_needed": "yes",
                "notes": (
                    "These are h12=1 Cynk--Meyer one-parameter families; conifold special fibers "
                    "and operator-route data must be supplied or verified before atom-level comparison."
                ),
            }
        )

    out_dir = REPO_ROOT / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out_dir / "family_candidates.csv", index=False)


if __name__ == "__main__":
    main()
