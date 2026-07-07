"""Audit helpers for the reviewer V4 verification package."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

import pandas as pd


@dataclass(slots=True)
class ClaimAudit:
    claim_id: str
    arrangement_scope: str
    topic: str
    claimed_value: str
    source_files: list[str]
    support_level: str
    repo_backed: bool
    machine_readable: bool
    promotion_ready: bool
    notes: str


@dataclass(slots=True)
class ReviewerV4Audit:
    package_dirs: list[str]
    files_present: list[str]
    files_missing: list[str]
    claims: list[ClaimAudit]
    promotion_recommendation: str
    notes: str


EXPECTED_SUPPORT_FILES = [
    "nodes_q_84.sing",
    "nodes_q_84a.sing",
    "nodes_p.sing",
    "nodes_p2.sing",
    "defect_p.sing",
    "defect_p2.sing",
    "genericity_check.py",
    "rank60.py",
    "COMPUTATION_LOG.md",
    "hodgecy_v4_inserts.tex",
    "outputs/out84.txt",
    "outputs/out84a.txt",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def reviewer_v4_package_dir(root: Path | None = None) -> Path:
    repo_root = root or _repo_root()
    return repo_root / "data" / "raw" / "updated-files"


def reviewer_v4_full_package_dir(root: Path | None = None) -> Path:
    repo_root = root or _repo_root()
    return repo_root / "data" / "raw" / "hodgecy_v4_full" / "hodgecy_v4"


def _available_support_files(root: Path) -> set[str]:
    paths = [reviewer_v4_package_dir(root), reviewer_v4_full_package_dir(root)]
    found: set[str] = set()
    for package_dir in paths:
        if not package_dir.exists():
            continue
        for file_path in package_dir.rglob("*"):
            if file_path.is_file():
                try:
                    relative = file_path.relative_to(package_dir).as_posix()
                except ValueError:
                    relative = file_path.name
                found.add(relative)
                found.add(file_path.name)
    return found


def _parse_degree_output(path: Path) -> dict[str, int | None]:
    payload = path.read_text(encoding="utf-8")
    degree = None
    dimension = None
    for line in payload.splitlines():
        stripped = line.strip()
        if stripped.isdigit():
            value = int(stripped)
            if dimension is None:
                dimension = value
            else:
                degree = value
                break
    return {"dimension": dimension, "degree": degree}


def build_reviewer_v4_audit(root: Path | None = None) -> ReviewerV4Audit:
    repo_root = root or _repo_root()
    package_dirs = [reviewer_v4_package_dir(repo_root), reviewer_v4_full_package_dir(repo_root)]
    available = _available_support_files(repo_root)
    files_present = sorted(available)
    files_missing = [item for item in EXPECTED_SUPPORT_FILES if item not in available]
    out84 = reviewer_v4_full_package_dir(repo_root) / "outputs" / "out84.txt"
    out84a = reviewer_v4_full_package_dir(repo_root) / "outputs" / "out84a.txt"
    out84_payload = _parse_degree_output(out84) if out84.exists() else {"dimension": None, "degree": None}
    out84a_payload = _parse_degree_output(out84a) if out84a.exists() else {"dimension": None, "degree": None}
    degree_backed = out84_payload["degree"] == 112 and out84a_payload["degree"] == 112
    claims = [
        ClaimAudit(
            claim_id="char0_degree_112",
            arrangement_scope="84,84a",
            topic="char0 singular-locus degree",
            claimed_value="112",
            source_files=["COMPUTATION_LOG.md", "hodgecy_v4_inserts.tex", "scripts/nodes_q_84.sing", "scripts/nodes_q_84a.sing", "outputs/out84.txt", "outputs/out84a.txt"],
            support_level="repo_backed" if degree_backed else "partially_backed",
            repo_backed=degree_backed,
            machine_readable=degree_backed,
            promotion_ready=False,
            notes="The full package includes Singular scripts and output logs showing dim(cone)=1 and deg=112 for 84 and 84a. This backs the degree claim, but not reducedness or Hessian-rank certification.",
        ),
        ClaimAudit(
            claim_id="reduced_true",
            arrangement_scope="84,84a",
            topic="reducedness",
            claimed_value="true",
            source_files=["COMPUTATION_LOG.md", "hodgecy_v4_inserts.tex"],
            support_level="log_only",
            repo_backed=False,
            machine_readable=False,
            promotion_ready=False,
            notes="Reducedness is asserted in prose, but no standalone machine-readable reducedness certificate is present.",
        ),
        ClaimAudit(
            claim_id="hessian_rank_3",
            arrangement_scope="84,84a",
            topic="Hessian rank",
            claimed_value="3 at all singular points",
            source_files=["COMPUTATION_LOG.md", "hodgecy_v4_inserts.tex"],
            support_level="log_only",
            repo_backed=False,
            machine_readable=False,
            promotion_ready=False,
            notes="The package contains the nodality claim in prose, but no Hessian rank distribution certificate or per-point rank export.",
        ),
        ClaimAudit(
            claim_id="defect_equals_7",
            arrangement_scope="84,84a",
            topic="defect",
            claimed_value="7",
            source_files=["COMPUTATION_LOG.md", "hodgecy_v4_inserts.tex", "rank60.py", "scripts/defect_p.sing", "scripts/defect_p2.sing"],
            support_level="partially_backed",
            repo_backed=False,
            machine_readable=False,
            promotion_ready=False,
            notes="The exact rank-60 lower-bound script and the finite-field Singular scripts are present, but no machine-readable finite-field outputs are bundled, so the equality claim defect=7 is not fully repo-backed.",
        ),
        ClaimAudit(
            claim_id="hilbert_degree_8_equals_105",
            arrangement_scope="84,84a",
            topic="Hilbert function degree 8",
            claimed_value="105",
            source_files=["COMPUTATION_LOG.md", "hodgecy_v4_inserts.tex", "scripts/defect_p.sing", "scripts/defect_p2.sing"],
            support_level="partially_backed",
            repo_backed=False,
            machine_readable=False,
            promotion_ready=False,
            notes="The finite-field computation scripts are present, but no raw machine-readable outputs for HF(8)=105 are bundled.",
        ),
        ClaimAudit(
            claim_id="genericity_g1_g2",
            arrangement_scope="84,84a",
            topic="genericity",
            claimed_value="G1 and G2 pass",
            source_files=["genericity_check.py"],
            support_level="repo_backed",
            repo_backed=True,
            machine_readable=False,
            promotion_ready=True,
            notes="The package includes an executable exact-rational genericity script. Equivalent repo-native verification is already integrated and tested.",
        ),
        ClaimAudit(
            claim_id="rank60_lower_bound",
            arrangement_scope="84,84a",
            topic="degree-8 rank lower bound",
            claimed_value="rank 60",
            source_files=["rank60.py"],
            support_level="repo_backed",
            repo_backed=True,
            machine_readable=False,
            promotion_ready=True,
            notes="The package includes the exact rational rank-60 script supporting the lower-bound half of the defect sandwich.",
        ),
    ]
    return ReviewerV4Audit(
        package_dirs=[str(path) for path in package_dirs if path.exists()],
        files_present=files_present,
        files_missing=files_missing,
        claims=claims,
        promotion_recommendation="remain_genericity_verified",
        notes=(
            "Reviewer V4 now includes stronger support than the small updated-files bundle alone: the full package "
            "contains Singular scripts and char-0 degree outputs. However, reducedness, Hessian-rank certification, "
            "and machine-readable finite-field Hilbert/defect outputs are still absent, so promotion beyond "
            "genericity_verified is not warranted."
        ),
    )


def write_reviewer_v4_audit(root: Path | None = None) -> dict[str, Path]:
    repo_root = root or _repo_root()
    audit = build_reviewer_v4_audit(repo_root)
    out_dir = repo_root / "data" / "processed" / "cas_certificates"
    out_dir.mkdir(parents=True, exist_ok=True)
    audit_json = out_dir / "reviewer_v4_audit.json"
    claims_json = out_dir / "reviewer_v4_claims.json"
    claims_csv = out_dir / "reviewer_v4_claims.csv"
    degree_json = out_dir / "reviewer_v4_degree_outputs.json"
    audit_json.write_text(json.dumps(asdict(audit), indent=2), encoding="utf-8")
    claims_json.write_text(json.dumps([asdict(claim) for claim in audit.claims], indent=2), encoding="utf-8")
    pd.DataFrame([asdict(claim) for claim in audit.claims]).to_csv(claims_csv, index=False)
    degree_payload = {}
    full_dir = reviewer_v4_full_package_dir(repo_root)
    for arrangement_id, filename in (("84", "out84.txt"), ("84a", "out84a.txt")):
        output_path = full_dir / "outputs" / filename
        if output_path.exists():
            degree_payload[arrangement_id] = _parse_degree_output(output_path)
    degree_json.write_text(json.dumps(degree_payload, indent=2), encoding="utf-8")
    return {
        "audit_json": audit_json,
        "claims_json": claims_json,
        "claims_csv": claims_csv,
        "degree_json": degree_json,
    }
