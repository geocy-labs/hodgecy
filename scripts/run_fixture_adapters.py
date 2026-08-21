from __future__ import annotations

import json
from pathlib import Path

from hodgecy.datasets import FixtureDatasetAdapter
from hodgecy.parsers import JsonlParser, SourceChunk, write_rejected_jsonl
from hodgecy.core.ids import HodgeCYID


def run_fixture(output_dir: Path) -> dict[str, object]:
    dataset_id = HodgeCYID.dataset("fixture_dataset")
    source = SourceChunk(
        dataset_id=dataset_id,
        distribution_id="fixture_jsonl",
        payload='{"id":"demo","h11":1}\nnot-json\n',
        relative_path="fixtures/demo.jsonl",
        source_version="fixture-v1",
    )
    adapter = FixtureDatasetAdapter.build(dataset_id="fixture_dataset", parser=JsonlParser(), sources=[source])
    run = adapter.run()
    manifest = adapter.normalization_manifest(run, output_refs=("memory://fixture_dataset",))
    output_dir.mkdir(parents=True, exist_ok=True)
    rejected_path = output_dir / "fixture_rejected.jsonl"
    write_rejected_jsonl(rejected_path, run.rejected)
    manifest_path = output_dir / "fixture_manifest.json"
    manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return {
        "summary": run.summary.to_dict(),
        "manifest_path": str(manifest_path),
        "rejected_path": str(rejected_path),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the Blob 5 fixture adapter harness.")
    parser.add_argument("--output-dir", type=Path, default=Path(".hodgecy-fixtures"))
    args = parser.parse_args()
    print(json.dumps(run_fixture(args.output_dir), indent=2, sort_keys=True))
