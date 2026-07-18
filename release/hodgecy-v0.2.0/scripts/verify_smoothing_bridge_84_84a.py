"""Generate smoothing verification outputs for selected arrangements."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy.reporting import build_p4_collinearity_certificate_table, plot_concurrency_graphs_84_84a  # noqa: E402
from hodgecy.smoothing.verification import run_verification_workflow  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Replace the primary output files when possible.")
    parser.add_argument(
        "--out-dir",
        default="data/processed",
        help="Output directory for JSON/CSV verification artifacts, relative to the repo root by default.",
    )
    parser.add_argument(
        "--arrangements",
        default="84,84a",
        help="Comma-separated arrangement ids to verify.",
    )
    parser.add_argument("--finite-field-checks", action="store_true", help="Run optional finite-field sanity checks.")
    parser.add_argument("--char0-checks", action="store_true", help="Run optional characteristic-zero checks if available.")
    parser.add_argument("--max-seconds", type=int, default=None, help="Time budget for optional expensive checks.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    arrangement_ids = [item.strip() for item in args.arrangements.split(",") if item.strip()]
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir

    result = run_verification_workflow(
        REPO_ROOT,
        out_dir=out_dir,
        arrangements=arrangement_ids,
        force=args.force,
        finite_field_checks=args.finite_field_checks,
        char0_checks=args.char0_checks,
        max_seconds=args.max_seconds,
    )
    figure_note = None
    certificate_note = None
    try:
        plot_concurrency_graphs_84_84a()
    except OSError as exc:
        figure_note = f"Figure regeneration was skipped because the target files were locked: {exc}"
    try:
        build_p4_collinearity_certificate_table()
    except OSError as exc:
        certificate_note = f"Certificate table regeneration was skipped because the target files were locked: {exc}"

    print("Verification workflow summary:")
    print(f"- output directory: {out_dir}")
    print(f"- arrangements: {', '.join(arrangement_ids)}")
    print(f"- finite-field checks: {'enabled' if args.finite_field_checks else 'disabled'}")
    print(f"- char0 checks: {'enabled' if args.char0_checks else 'disabled'}")
    if args.max_seconds is not None:
        print(f"- max seconds: {args.max_seconds}")
    for record in result.records:
        print(f"- {record.source_arrangement}: {record.verification_status}")
    print("- write results:")
    for write_result in result.write_results:
        suffix = f" [{write_result.status}]"
        if write_result.actual_path != write_result.logical_path:
            print(f"  - {write_result.logical_path} -> {write_result.actual_path}{suffix}")
        else:
            print(f"  - {write_result.actual_path}{suffix}")
        if write_result.notes:
            print(f"    note: {write_result.notes}")
    print(f"- summary csv: {result.summary_path}")
    print("- p4 figures: paper/figures/fig_concurrency_graph_84.[png|pdf], paper/figures/fig_concurrency_graph_84a.[png|pdf]")
    print("- p4 certificate: data/processed/p4_collinearity_certificate.csv, paper/tables/table_p4_collinearity_certificate.tex")
    if figure_note:
        print(f"- note: {figure_note}")
    if certificate_note:
        print(f"- note: {certificate_note}")


if __name__ == "__main__":
    main()
