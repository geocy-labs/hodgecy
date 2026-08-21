from __future__ import annotations

import json

import pytest

pytest.importorskip("pyarrow")

from hodgecy.bootstrap import Wave2IngestConfig, ingest_wave2_sources
from hodgecy.core.dataset import ConstructionFamily, DatasetDescriptor
from hodgecy.core.ids import HodgeCYID
from hodgecy.core.status import AcquisitionStatus, RedistributionStatus, SourceIntegrityStatus
from hodgecy.query import QuerySpec
from hodgecy.storage import open_catalog


def _write(path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fixture_root(tmp_path):
    root = tmp_path
    catalog = open_catalog(root, name="current_corpus", create=True)
    catalog.register_dataset(DatasetDescriptor(
        dataset_id=HodgeCYID.dataset("cicy3_standard"),
        name="CICY3 fixture",
        construction_family=ConstructionFamily.known("cicy3"),
        acquisition_status=AcquisitionStatus.COMPLETE_COLUMNAR,
        redistribution_status=RedistributionStatus.REDISTRIBUTABLE,
    ))
    catalog.register_dataset(DatasetDescriptor(
        dataset_id=HodgeCYID.dataset("kreuzer_skarke"),
        name="KS fixture",
        construction_family=ConstructionFamily.known("toric_hypersurface"),
        acquisition_status=AcquisitionStatus.COMPLETE_COLUMNAR,
        redistribution_status=RedistributionStatus.REDISTRIBUTABLE,
    ))

    candidates = [
        ("wave2_001", "ACQUIRE_FULL", "DESY CICY GV", "enumerative", "cicy3", "https://desy.example/gv", "Num", "GV rows", "CMRW", "", "OPEN", "5522"),
        ("wave2_002", "MANUAL_ACQUISITION_REQUIRED", "Springer divisor topology", "divisor", "cicy3", "https://doi.org/10.1007/s00220-022-04410-9", "doi", "divisor data", "CMS", "10.1007/s00220-022-04410-9", "MANUAL", ""),
        ("wave2_003", "MANUAL_ACQUISITION_REQUIRED", "APS gCICY", "gCICY", "generalized_cicy", "https://doi.org/10.1103/PhysRevD.106.046016", "doi", "gCICY data", "Cui Gao Wang", "10.1103/PhysRevD.106.046016", "MANUAL", ""),
        ("wave2_004", "ACQUIRE_METADATA_AND_INDEX", "Zenodo toric KS fibrations", "fibration", "toric_hypersurface", "https://zenodo.org/records/18500236", "zenodo_file", "remote files", "Abbasi Nally Taylor", "10.5281/zenodo.18500236", "REMOTE", "2"),
        ("wave2_005", "ACQUIRE_METADATA_AND_INDEX", "GroupofXG orientifolds", "orientifold", "toric_hypersurface", "https://github.com/GroupofXG/anewcydatabase/releases/tag/data-v1", "release_asset", "remote assets", "Cao Gao Gao", "", "REMOTE", "1"),
        ("wave2_006", "REGISTER_SOURCE_ONLY", "CYTools", "software", "toric_hypersurface", "https://cy.tools", "repository", "software source", "CYTools", "", "SOURCE", ""),
        ("wave2_007", "REGISTER_REMOTE", "AESZ/CYDB", "picard", "picard_fuchs", "https://cydb.mathematik.uni-mainz.de", "remote", "remote source", "AESZ", "", "REMOTE", ""),
        ("wave2_008", "DUPLICATE_EXISTING", "KS duplicate", "toric", "toric_hypersurface", "https://ks.example", "polytope", "duplicate", "KS", "", "DUPLICATE", ""),
        ("wave2_009", "DUPLICATE_EXISTING", "CICY duplicate", "cicy", "cicy3", "https://cicy.example", "Num", "duplicate", "CICY", "", "DUPLICATE", ""),
        ("wave2_010", "REGISTER_SOURCE_ONLY", "Borcea Voisin", "source", "borcea_voisin", "https://example.org/borcea", "source", "source registry", "BV", "", "SOURCE", ""),
        ("wave2_011", "REGISTER_SOURCE_ONLY", "Pfaffian determinantal", "source", "pfaffian_determinantal", "https://example.org/pfaffian", "source", "source registry", "Pfaffian", "", "SOURCE", ""),
        ("wave2_012", "REGISTER_SOURCE_ONLY", "Grassmannian homogeneous", "source", "grassmannian_homogeneous", "https://example.org/grassmannian", "source", "source registry", "Grassmannian", "", "SOURCE", ""),
    ]
    header = "candidate_id\tacquisition_decision\tname\tcategory\tconstruction_family\tsource_URL\tidentifier_scheme\tnew_information\tcitation\tDOI\tlicense_status\tadvertised_record_count\toverlap_with_existing_HodgeCY\tnotes\n"
    _write(root / "reports" / "acquisition_wave2" / "candidates.tsv", header + "".join("\t".join(row + ("", "")) + "\n" for row in candidates))
    _write(root / "reports" / "acquisition_wave2" / "source_inventory.tsv",
           "dataset_id\tlocal_path\tsource_url\tSHA256\tbyte_size\tarchive_format\tparse_status\n"
           "cicy_gv_invariants_desy\traw/cicy_gv_invariants_desy/CICY-H11=1.zip\thttps://desy.example/h1\t\t4\tzip\tZIP_VALID\n"
           "cicy_gv_invariants_desy\traw/cicy_gv_invariants_desy/CICY-H11=9.zip\thttps://desy.example/h9\t\t7\tzip\tZIP_VALIDATION_FAILED\n")
    _write(root / "reports" / "acquisition_wave2" / "identifier_inventory.tsv", "dataset_id\tstable_source_id\tjoin_to_existing_HodgeCY\n")
    _write(root / "reports" / "acquisition_wave2" / "hodgecy_fit.tsv", "dataset_id\tnew_adapter_required\n")
    _write(root / "reports" / "acquisition_wave2" / "record_counts.tsv",
           "dataset_id\th11_bucket\tmember_count\tvalidation_issue\n"
           "cicy_gv_invariants_desy\t1\t1\t\n"
           "cicy_gv_invariants_desy\t9\t1\tzlib invalid block type\n")
    _write(root / "reports" / "acquisition_wave2" / "coverage_after.tsv", "coverage_axis\tdatasets_added\nenumerative\tcicy_gv_invariants_desy\ntoric\ttoric_ks_fibrations_abbasi_nally_taylor_2026\n")
    _write(root / "reports" / "implementation" / "acquisition_wave2_manifest.json", json.dumps({"WAVE2_ACQUISITION_COMPLETE": "YES"}))
    _write(root / "manifests" / "acquisition_wave2_datasets.json", json.dumps([{"candidate_id": row[0], "intended_permanent_completion_state": row[1]} for row in candidates]))

    _write(root / "raw" / "cicy_gv_invariants_desy" / "CICY-H11=1.zip", "good")
    _write(root / "raw" / "cicy_gv_invariants_desy" / "CICY-H11=9.zip", "corrupt")
    _write(root / "extracted" / "cicy_gv_invariants_desy" / "CICY-H11=1" / "1.dat", "n[ 1 ] = 512\nn[ 0 , 1 ] = 144\n")
    _write(root / "raw" / "toric_ks_fibrations_abbasi_nally_taylor_2026" / "zenodo_record_18500236.json", "{}")
    _write(root / "raw" / "toric_ks_fibrations_abbasi_nally_taylor_2026" / "fibers-public-main.zip", "remote-index")
    _write(root / "raw" / "ks_orientifolds_groupofxg_2024" / "github_release_data-v1.json", "{}")
    _write(root / "raw" / "ks_orientifolds_groupofxg_2024" / "README.md", "release")
    _write(root / "staged" / "acquisition_wave2" / "toric_ks_fibrations_zenodo_files.tsv", "file\tlocal_state\turl\nfiber-a.csv\tREMOTE_INDEXED\thttps://zenodo.example/a\nfiber-b.csv\tLOCAL_METADATA\thttps://zenodo.example/b\n")
    _write(root / "staged" / "acquisition_wave2" / "ks_orientifolds_groupofxg_release_assets.tsv", "asset\tlocal_state\turl\norientifold-a.zip\tREMOTE_INDEXED\thttps://github.example/a\n")
    return root


def test_wave2_permanent_ingest_fixture_reconciles_candidates_and_queries(tmp_path) -> None:
    root = _fixture_root(tmp_path)
    result = ingest_wave2_sources(Wave2IngestConfig(root, batch_size=1, hodgecy_commit="fixture-sha"))

    assert len(result.queue) == 12
    assert result.wave2_fully_integrated is True
    assert result.wave3_ready is True
    assert result.enumerative_record_count == 2
    assert result.rejected_counts["cicy_gv_h11_9_corrupt_members"] == 1

    catalog = open_catalog(root, name="current_corpus", read_only=True)
    gv = catalog.query(QuerySpec(table="wave2_cicy_gv_invariants", fields=("parent_cicy_id", "degree_coordinates_json", "invariant_value_raw"))).to_arrow()
    assert gv.num_rows == 2
    integrity = catalog.query(QuerySpec(table="wave2_cicy_gv_source_integrity", fields=("integrity_status", "validation_issue"))).to_arrow()
    assert integrity.num_rows == 1
    assert integrity.column("integrity_status")[0].as_py() == SourceIntegrityStatus.SOURCE_CORRUPT.value
    assert "zlib" in integrity.column("validation_issue")[0].as_py()
    assert catalog.query(QuerySpec(table="wave2_toric_ks_fibration_remote_files")).to_arrow().num_rows == 2
    assert catalog.query(QuerySpec(table="wave2_ks_orientifold_release_assets")).to_arrow().num_rows == 1
    assert catalog.query(QuerySpec(table="wave2_source_relationships")).to_arrow().num_rows == 3
    assert (root / "reports" / "implementation" / "wave2_permanent_ingest_report.md").exists()
