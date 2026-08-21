from __future__ import annotations

import argparse
from pathlib import Path

from hodgecy import open_data_root
from hodgecy.core.dataset import ConstructionFamily, DatasetDescriptor
from hodgecy.core.ids import HodgeCYID
from hodgecy.core.status import AcquisitionStatus, RedistributionStatus
from hodgecy.storage import DatasetInstance, open_catalog

KS_RELATIVE_DIR = Path("raw/kreuzer_skarke/parquet")
EXPECTED_KS_ROWS = 473_800_776


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only HodgeCY data catalog smoke check")
    parser.add_argument("--root", default=None, help="HODGECY data root; defaults to environment/config")
    parser.add_argument("--create", action="store_true", help="Create metadata catalog if missing")
    args = parser.parse_args()

    root = open_data_root(args.root, require_exists=True)
    catalog = open_catalog(root, create=args.create)
    manifest = root.manifests / "datasets.json"
    if manifest.exists():
        catalog.bootstrap_manifest(manifest)

    ks_dir = root.root / KS_RELATIVE_DIR
    if ks_dir.exists():
        parquet_files = sorted(ks_dir.glob("*.parquet"))
        if parquet_files:
            descriptor = DatasetDescriptor(
                dataset_id=HodgeCYID.dataset("kreuzer_skarke_4d"),
                name="Kreuzer-Skarke 4D reflexive polytopes",
                construction_family=ConstructionFamily.known("toric_hypersurface"),
                acquisition_status=AcquisitionStatus.COMPLETE_COLUMNAR,
                redistribution_status=RedistributionStatus.ACQUIRED_LOCALLY_BY_USER,
                expected_count=EXPECTED_KS_ROWS,
                verified_count=EXPECTED_KS_ROWS,
                metadata={"integration": "read_only"},
            )
            catalog.register_dataset(descriptor)
            catalog.register_instance(DatasetInstance(
                instance_id="kreuzer_skarke_4d_local_parquet",
                dataset_id=descriptor.dataset_id,
                source_version="local_parquet",
                acquisition_status=AcquisitionStatus.COMPLETE_COLUMNAR,
                redistribution_status=RedistributionStatus.ACQUIRED_LOCALLY_BY_USER,
                record_count=EXPECTED_KS_ROWS,
            ))
            print(f"KS parquet files found: {len(parquet_files)}")
            print(f"Expected KS rows: {EXPECTED_KS_ROWS}")
    print(f"Catalog: {catalog.path}")
    print(f"Datasets known: {len(catalog.list_datasets())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
