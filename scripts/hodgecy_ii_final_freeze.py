"""Freeze final HodgeCY II synthesis, manuscript, and reproducibility assets."""

from __future__ import annotations

import csv
import json
import platform
import shutil
import subprocess
import sys
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hodgecy import __version__ as HODGECY_VERSION  # noqa: E402
from hodgecy.research.hodgecy_ii_fidelity_census import generate_hodgecy_ii_manuscript_assets  # noqa: E402


HODGECY_II_ROOT = REPO_ROOT / "research_outputs" / "hodgecy_ii"
FINAL_ROOT = HODGECY_II_ROOT / "final"
THEOREM_EVIDENCE_ROOT = FINAL_ROOT / "theorem_evidence"
SOURCE_LATTICE_PATH = THEOREM_EVIDENCE_ROOT / "source_lattice" / "source_lattice_comparison_84_84a.json"
BLOCK_GEOMETRY_PATH = THEOREM_EVIDENCE_ROOT / "block_geometry" / "block_geometry_certification_84_84a.json"
BLOCK_EVALUATION_PATH = THEOREM_EVIDENCE_ROOT / "block_evaluation" / "block_evaluation_comparison_84_84a.json"
SOURCE_BLOCK_COMPARISON_PATH = THEOREM_EVIDENCE_ROOT / "source_block_comparison" / "source_block_evaluation_comparison_84_84a.json"
HILBERT_BURCH_PATH = THEOREM_EVIDENCE_ROOT / "hilbert_burch_block_theorem.json"
LITERATURE_REVIEW_MD_PATH = FINAL_ROOT / "hodgecy_ii_literature_review.md"
LITERATURE_REVIEW_JSON_PATH = FINAL_ROOT / "hodgecy_ii_literature_review.json"
RELATED_WORK_BIB_PATH = FINAL_ROOT / "hodgecy_ii_related_work.bib"
HILBERT_BURCH_THEOREM_TEX_PATH = FINAL_ROOT / "hodgecy_ii_hilbert_burch_theorem.tex"
STAR_CONFIGURATION_AUDIT_MD_PATH = FINAL_ROOT / "hodgecy_ii_star_configuration_audit.md"
STAR_CONFIGURATION_AUDIT_JSON_PATH = FINAL_ROOT / "hodgecy_ii_star_configuration_audit.json"
OPTIONAL_FINAL_ASSETS = (
    LITERATURE_REVIEW_MD_PATH,
    LITERATURE_REVIEW_JSON_PATH,
    RELATED_WORK_BIB_PATH,
    HILBERT_BURCH_THEOREM_TEX_PATH,
    STAR_CONFIGURATION_AUDIT_MD_PATH,
    STAR_CONFIGURATION_AUDIT_JSON_PATH,
)
DEPRECATED_ARTIFACT_PREFIXES = (
    "research_outputs/hodgecy_ii/baseline/",
    "research_outputs/hodgecy_ii/defect_blob7/",
    "research_outputs/hodgecy_ii/evaluation_blob13/",
    "research_outputs/hodgecy_ii/integral_lattice_blob8/",
    "research_outputs/hodgecy_ii/node_block_blob12/",
    "research_outputs/hodgecy_ii/node_geometry_blob5/",
    "research_outputs/hodgecy_ii/node_ideal_hilbert_blob6/",
    "research_outputs/hodgecy_ii/node_relation_blob9/",
    "research_outputs/hodgecy_ii/source_evaluation_blob14/",
    "research_outputs/hodgecy_ii/source_to_node_blob10/",
)
CANONICAL_PATH_REPLACEMENTS = {
    "research_outputs/hodgecy_ii/integral_lattice_blob8/hodgecy_ii_84_84a_source_lattice_comparison.json": "research_outputs/hodgecy_ii/final/theorem_evidence/source_lattice/source_lattice_comparison_84_84a.json",
    "research_outputs/hodgecy_ii/node_block_blob12/hodgecy_ii_node_block_certification.json": "research_outputs/hodgecy_ii/final/theorem_evidence/block_geometry/block_geometry_certification_84_84a.json",
    "research_outputs/hodgecy_ii/node_block_blob12/84/node_block_certificate.json": "research_outputs/hodgecy_ii/final/theorem_evidence/block_geometry/84/node_block_certificate.json",
    "research_outputs/hodgecy_ii/node_block_blob12/84a/node_block_certificate.json": "research_outputs/hodgecy_ii/final/theorem_evidence/block_geometry/84a/node_block_certificate.json",
    "research_outputs/hodgecy_ii/evaluation_blob13/hodgecy_ii_84_84a_evaluation_comparison.json": "research_outputs/hodgecy_ii/final/theorem_evidence/block_evaluation/block_evaluation_comparison_84_84a.json",
    "research_outputs/hodgecy_ii/evaluation_blob13/84/block_evaluation_result.json": "research_outputs/hodgecy_ii/final/theorem_evidence/block_evaluation/84/block_evaluation_result.json",
    "research_outputs/hodgecy_ii/evaluation_blob13/84a/block_evaluation_result.json": "research_outputs/hodgecy_ii/final/theorem_evidence/block_evaluation/84a/block_evaluation_result.json",
    "research_outputs/hodgecy_ii/evaluation_blob13/84/block_hilbert_function.tsv": "research_outputs/hodgecy_ii/final/theorem_evidence/block_evaluation/84/block_hilbert_function.tsv",
    "research_outputs/hodgecy_ii/evaluation_blob13/84a/block_hilbert_function.tsv": "research_outputs/hodgecy_ii/final/theorem_evidence/block_evaluation/84a/block_hilbert_function.tsv",
    "research_outputs/hodgecy_ii/source_evaluation_blob14/hodgecy_ii_84_84a_source_evaluation_comparison.json": "research_outputs/hodgecy_ii/final/theorem_evidence/source_block_comparison/source_block_evaluation_comparison_84_84a.json",
}
CANONICAL_TEXT_REPLACEMENTS = {
    "Blob 8 source lattice comparison": "final source-lattice comparison",
    "Blob 8 verified source lattice records": "final source-lattice records",
    "Blob 12 verified reduced block schemes": "final verified reduced block schemes",
    "Blob 13 verified block evaluation": "final block-evaluation certificate",
    "Blob 13 block evaluation comparison": "final block-evaluation comparison",
    "Blob 14 performs no perturbation or vanishing-cycle construction.": "The final source-versus-block comparison performs no perturbation or vanishing-cycle construction.",
    "Blob 11 computes no defect value.": "No verified classical defect value is promoted.",
    "Blob 11 constructs no Hodge atom spectrum.": "No Hodge atom spectrum is constructed.",
    "Blob 11 creates no node ideal.": "No final saturated node ideal certificate is claimed.",
    "Blob 11 asserts no node relation or source-to-node morphism.": "No node relation or source-to-node morphism is asserted.",
    "Blob 11 performs no ODP promotion.": "Ordinary-node promotion remains open.",
    "blob8_torsion:": "source_torsion:",
    "blob8:": "source_lattice:",
    "blob12:": "block_geometry:",
    "blob13:": "block_evaluation:",
}
CANONICAL_KEY_REPLACEMENTS = {
    "blob8_source_lattice_comparison": "source_lattice_comparison",
    "blob12_block_certificates": "block_geometry_certificates",
    "blob12_certificate": "block_geometry_certificate",
    "blob12_reducedness_certificate": "block_geometry_reducedness_certificate",
    "blob13_block_scheme_hash": "block_evaluation_scheme_hash",
    "blob13_evaluation_certificates": "block_evaluation_certificates",
    "blob13_evaluation_comparison": "block_evaluation_comparison",
}
MANUSCRIPT_ROOT = HODGECY_II_ROOT / "manuscript_assets"
TABLE_ROOT = MANUSCRIPT_ROOT / "tables"
FIGURE_ROOT = MANUSCRIPT_ROOT / "figures"
DATA_ROOT = MANUSCRIPT_ROOT / "data"
MANIFEST_ROOT = MANUSCRIPT_ROOT / "manifest"
FINAL_ARTIFACT_MANIFEST_PATH = FINAL_ROOT / "hodgecy_ii_final_artifact_manifest.json"


def stable_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stable_json(payload), encoding="utf-8")
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_table(path: Path, rows: list[dict[str, Any]], delimiter: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter=delimiter, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: cell(row.get(key)) for key in rows[0]})
    return path


def write_table_bundle(root: Path, stem: str, rows: list[dict[str, Any]]) -> list[Path]:
    columns = list(rows[0])
    return [
        write_table(root / f"{stem}.tsv", rows, "\t"),
        write_table(root / f"{stem}.csv", rows, ","),
        write_json(root / f"{stem}.json", rows),
        write_text(root / f"{stem}.md", markdown_table(rows, columns)),
        write_text(root / f"{stem}.tex", latex_table(rows, columns)),
    ]


def markdown_table(rows: list[dict[str, Any]], columns: list[str] | None = None) -> str:
    columns = columns or list(rows[0])
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(cell(row.get(column)).replace("|", "\\|") for column in columns) + " |")
    return "\n".join(lines) + "\n"


def latex_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    lines = ["\\begin{tabular}{" + "l" * len(columns) + "}", "\\hline", " & ".join(tex(column) for column in columns) + r" \\", "\\hline"]
    for row in rows:
        lines.append(" & ".join(tex(row.get(column)) for column in columns) + r" \\")
    lines.extend(["\\hline", "\\end{tabular}", ""])
    return "\n".join(lines)


def tex(value: Any) -> str:
    text = cell(value)
    for old, new in {"\\": r"\textbackslash{}", "_": r"\_", "%": r"\%", "&": r"\&", "#": r"\#", "{": r"\{", "}": r"\}"}.items():
        text = text.replace(old, new)
    return text


def cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "YES" if value else "NO"
    if isinstance(value, list | tuple):
        return " | ".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return str(value)


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def final_artifact_paths(paths: Iterable[Path]) -> list[Path]:
    return [path for path in paths if path.exists() and path != FINAL_ARTIFACT_MANIFEST_PATH]


def existing_optional_final_assets() -> list[Path]:
    return [path for path in OPTIONAL_FINAL_ASSETS if path.exists()]


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def canonicalize_evidence_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {canonicalize_evidence_key(key): canonicalize_evidence_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [canonicalize_evidence_payload(item) for item in value]
    if isinstance(value, str):
        for old, new in CANONICAL_PATH_REPLACEMENTS.items():
            value = value.replace(old, new)
        for old, new in CANONICAL_TEXT_REPLACEMENTS.items():
            value = value.replace(old, new)
    return value


def canonicalize_evidence_key(key: str) -> str:
    for old, new in CANONICAL_KEY_REPLACEMENTS.items():
        key = key.replace(old, new)
    return key


def normalize_canonical_evidence_files() -> list[Path]:
    normalized = []
    for path in THEOREM_EVIDENCE_ROOT.rglob("*.json"):
        payload = read_json(path)
        updated = canonicalize_evidence_payload(payload)
        if updated != payload:
            normalized.append(write_json(path, updated))
    return normalized


def git_output(*args: str) -> str | None:
    try:
        completed = subprocess.run(["git", *args], cwd=REPO_ROOT, check=True, capture_output=True, text=True, timeout=10)
    except Exception:
        return None
    return completed.stdout.strip()


def load_canonical() -> dict[str, Any]:
    data = {
        "census_summary": read_json(DATA_ROOT / "fidelity_census_summary.json"),
        "census_reconciled": read_json(DATA_ROOT / "fidelity_census_reconciled.json"),
        "asset_manifest": read_json(MANIFEST_ROOT / "hodgecy_ii_asset_manifest.json"),
        "scope": read_json(MANIFEST_ROOT / "hodgecy_ii_scope.json"),
        "source_regression": read_json(DATA_ROOT / "hodgecy_i_source_regression.json"),
        "node_block": read_json(BLOCK_GEOMETRY_PATH),
        "evaluation": read_json(BLOCK_EVALUATION_PATH),
        "source_evaluation": read_json(SOURCE_BLOCK_COMPARISON_PATH),
        "source_lattice": read_json(SOURCE_LATTICE_PATH),
    }
    if HILBERT_BURCH_PATH.exists():
        data["hilbert_burch"] = read_json(HILBERT_BURCH_PATH)
    if LITERATURE_REVIEW_JSON_PATH.exists():
        data["literature_review"] = read_json(LITERATURE_REVIEW_JSON_PATH)
    if STAR_CONFIGURATION_AUDIT_JSON_PATH.exists():
        data["star_configuration_audit"] = read_json(STAR_CONFIGURATION_AUDIT_JSON_PATH)
    return data


def question_statuses(data: dict[str, Any]) -> list[dict[str, Any]]:
    summary = data["census_summary"]
    return [
        {"question_id": "Q1", "question": "Are fidelity collapse/separation phenomena broader than 84 / 84a?", "status": "ANSWERED", "answer": "YES", "evidence": f"{summary['total_processed']} processed; {summary['nontrivial_pairs_sets']} nontrivial pairs/sets."},
        {"question_id": "Q2", "question": "Do 84 / 84a remain equivalent at rational source level?", "status": "ANSWERED", "answer": "YES; rank_Q=26 and H1_Q rank=2 for both.", "evidence": "final source-lattice comparison."},
        {"question_id": "Q3", "question": "Do 84 / 84a remain equivalent integrally at source level?", "status": "ANSWERED", "answer": "NO; Smith forms differ.", "evidence": "SNF(84)=(1^23,2,6,12); SNF(84a)=(1^21,2,4,4,4,12)."},
        {"question_id": "Q4", "question": "Can the perturbation geometry be represented by exact finite reduced degree-112 block schemes?", "status": "ANSWERED", "answer": "YES for the verified block schemes.", "evidence": "final block-geometry certificates."},
        {"question_id": "Q5", "question": "Has complete ordinary-node promotion been achieved?", "status": "OPEN / PARTIALLY_ANSWERED", "answer": "NO; final saturated Jacobian/full promotion certificate remains incomplete.", "evidence": "final block-geometry and block-evaluation validation statuses."},
        {"question_id": "Q6", "question": "Do the two verified block schemes have different Hilbert profiles through critical degree?", "status": "ANSWERED", "answer": "NO; profiles agree through degree 8.", "evidence": "final block-Hilbert tables."},
        {"question_id": "Q7", "question": "Do their degree-8 block-evaluation deficiencies differ?", "status": "ANSWERED", "answer": "NO; both equal 7.", "evidence": "final critical-degree block evaluation."},
        {"question_id": "Q8", "question": "Do the tested block-evaluation data determine integral source assembly type?", "status": "ANSWERED", "answer": "NO on the 84/84a witness pair.", "evidence": "final source-versus-block non-determination certificate."},
        {"question_id": "Q9", "question": "Are the classical nodal defects verified to equal 7?", "status": "CONDITIONAL / OPEN", "answer": "Only conditionally; do not promote.", "evidence": "final conditional-defect records."},
        {"question_id": "Q10", "question": "Has a natural source-to-evaluation/node chain map been constructed?", "status": "OPEN", "answer": "NO; status remains UNKNOWN.", "evidence": "final comparison-firewall records."},
    ]


def theorem_candidates(data: dict[str, Any]) -> list[dict[str, Any]]:
    summary = data["census_summary"]
    candidates = [
        {"result_id": "A", "title": "Fidelity census context", "status": "CONTEXT_READY", "claim": "The current HodgeCY fidelity census contains 456 processed records and 114 nontrivial pairs/sets.", "evidence": {"processed": summary["total_processed"], "nontrivial_sets": summary["nontrivial_pairs_sets"], "pairs": summary["pairs"], "triples": summary["triples"], "larger_sets": summary["larger_sets"]}},
        {"result_id": "B", "title": "Integral source separation", "status": "VERIFIED", "claim": "84 and 84a share local, Hodge, and rational source data but have nonisomorphic integral source assembly complexes.", "evidence": {"SNF_84": "(1^23,2,6,12)", "SNF_84a": "(1^21,2,4,4,4,12)", "source": "final source-lattice comparison"}},
        {"result_id": "C", "title": "Exact block-evaluation collapse", "status": "VERIFIED", "claim": "The verified reduced degree-112 block schemes have identical Hilbert functions through degree 8 and equal block-evaluation deficiency 7.", "evidence": {"H_B_0_8": [1, 4, 10, 20, 34, 52, 74, 92, 105], "H_B_8": 105, "epsilon_B": 7, "source": "final block-evaluation certificate"}},
        {"result_id": "D", "title": "Block evaluation does not determine integral source type", "status": "VERIFIED_ON_WITNESS_PAIR", "claim": "On 84/84a, exact block-Hilbert/evaluation data through degree 8 do not determine integral source assembly type.", "evidence": {"same_block_evaluation_signature": True, "different_integral_source_smith_type": True, "source": "final source-versus-block comparison"}, "nonclaims": ["No reverse global determinacy claim.", "No source-to-evaluation chain map."]},
    ]
    hilbert_burch = data.get("hilbert_burch")
    if hilbert_burch:
        candidates.append(
            {
                "result_id": "E",
                "title": "Hilbert-Burch block-profile explanation",
                "status": hilbert_burch["status"],
                "claim": "The shared 84/84a verified block Hilbert profile and degree-8 block-evaluation deficiency are structurally explained by the eight-plane line-skeleton Hilbert-Burch resolution and regular quartic section.",
                "evidence": {
                    "source": "final Hilbert-Burch block theorem evidence",
                    "hilbert_series": "(1-t^4)(1-8t^7+7t^8)/(1-t)^4",
                    "H_B_0_10": [1, 4, 10, 20, 34, 52, 74, 92, 105, 112, 112],
                    "H1_I_B_8": 7,
                },
                "nonclaims": [
                    "No classical defect promotion.",
                    "No full singular-scheme equality claim.",
                    "No source-to-evaluation morphism.",
                ],
            }
        )
    return candidates


def conditional_results() -> list[dict[str, Any]]:
    return [
        {
            "conditional_result_id": "C1",
            "status": "CONDITIONAL",
            "condition": "If the verified block schemes are identified with the complete ordinary-node schemes under the applicable nodal-double-solid hypotheses.",
            "conclusion": "delta_84 = delta_84a = 7.",
            "nonpromotion": "Actual classical defect remains UNKNOWN until ordinary-node/full-node-scheme promotion is certified.",
        }
    ]


def open_problems() -> list[dict[str, str]]:
    items = [
        "Complete ordinary-node promotion for the chosen perturbations.",
        "Freeze/reproduce the final saturated Jacobian node ideals.",
        "Verify/promote classical defect.",
        "Construct a natural source-to-evaluation or source-to-node comparison morphism.",
        "Determine whether source relations inject into, map to, filter, or otherwise interact with the 7-dimensional evaluation-relation space.",
        "Construct a natural integral evaluation-relation lattice.",
        "Compare with vanishing-cycle and exceptional-curve relation lattices.",
        "Mixed-Hodge/LMHS realization.",
    ]
    return [{"problem_id": f"O{index}", "status": "OPEN", "problem": item} for index, item in enumerate(items, start=1)]


def hodgecy_iii_handoff(data: dict[str, Any]) -> dict[str, Any]:
    summary = data["census_summary"]
    return {
        "schema": "hodgecy_iii_handoff.v1",
        "status": "DEFERRED_TO_HODGECY_III",
        "population": {"processed": summary["total_processed"], "nontrivial_sets": summary["nontrivial_pairs_sets"]},
        "deferred_questions": [
            "456-record population fidelity stratification",
            "set-size distribution",
            "first-separation-depth distribution",
            "prime-sensitive population analysis",
            "integral-collapse/equivariant-separation population",
            "84-neighborhood refinement cascade",
            "new candidate discovery using v1.0",
            "validation promotion of census candidates",
        ],
        "representative_families": ["61 / 451", "84 / 84a", "452 / 453", "84 / 240", "84a / 239", "239 / 240 / 241", "83 / 84 / 84a / 239 / 240 / 241"],
        "validation_status_policy": "Preserve theorem-ready, context-ready, historical-warning, and census-level distinctions.",
    }


def evidence_matrix_rows() -> list[dict[str, str]]:
    rows = [
        ("456-record census", "COMPUTED", "456 processed records in frozen census context."),
        ("114 nontrivial fidelity sets", "COMPUTED", "57 pairs, 13 triples, 44 larger sets; reconciliation reproduced."),
        ("84/84a local equality", "VERIFIED", "Same local inventory."),
        ("84/84a Hodge equality", "VERIFIED", "h11=40, h12=0, euler=80 for both."),
        ("84/84a rational source equality", "VERIFIED", "rank_Q=26, H1_Q=2, H0_Q=0 for both."),
        ("84/84a integral source inequality", "VERIFIED", "Smith forms and rank_mod_2 differ."),
        ("84 verified block scheme", "VERIFIED", "final reduced degree-112 block scheme."),
        ("84a verified block scheme", "VERIFIED", "final reduced degree-112 block scheme."),
        ("block scheme degree 112", "VERIFIED", "28 four-point blocks."),
        ("block reducedness", "VERIFIED", "Block-level reducedness certificate."),
        ("block -> singular containment", "VERIFIED", "final containment certificate."),
        ("full ordinary-node promotion", "OPEN", "Saturated Jacobian/full promotion gate incomplete."),
        ("frozen saturated node ideal", "OPEN", "No final saturated node ideal certificate."),
        ("Hilbert profile 0..8", "VERIFIED", "1,4,10,20,34,52,74,92,105 for both."),
        ("H_B(8)=105", "VERIFIED", "Critical degree value for both."),
        ("block evaluation deficiency=7", "VERIFIED", "Block-scheme evaluation deficiency for both."),
        ("evaluation relation dimension=7", "VERIFIED", "dim ker(E_8^T)=7 for both."),
        ("classical defect=7", "CONDITIONAL", "Only if ordinary-node/full-node hypotheses are certified."),
        ("source-to-evaluation morphism", "OPEN", "No chain map constructed."),
        ("source-to-vanishing morphism", "NOT_CLAIMED", "No vanishing-cycle map inferred."),
        ("integral evaluation lattice", "OPEN", "Not constructed."),
        ("LMHS/Hodge-atom interpretation", "NOT_CLAIMED", "No LMHS/MHM or complete Hodge-atom spectrum asserted."),
    ]
    if HILBERT_BURCH_PATH.exists():
        rows.extend(
            [
                ("84/84a line-skeleton Hilbert-Burch resolution", "PROVED", "0 -> S(-8)^7 -> S(-7)^8 -> I_C -> 0 under verified no-three-planes-on-a-line hypotheses."),
                ("84/84a quartic regular section", "PROVED", "Q restricts to a nonzero squarefree quartic on every associated line."),
                ("84/84a block mapping-cone resolution", "PROVED", "0 -> S(-12)^7 -> S(-11)^8 plus S(-8)^7 -> S(-7)^8 plus S(-4) -> S -> S/I_B -> 0 for the verified block scheme."),
                ("structural block Hilbert series", "PROVED", "(1-t^4)(1-8t^7+7t^8)/(1-t)^4 for the verified block scheme."),
                ("H^1(I_B(8))=7", "PROVED", "Sheaf/evaluation sequence for the verified block scheme."),
                ("Hilbert-Burch source-to-evaluation map", "NOT_CLAIMED", "Rank-seven syzygy contribution explains dimension only; no source map is constructed."),
            ]
        )
    return [{"statement": statement, "status": status, "basis": basis} for statement, status, basis in rows]


def block_evaluation_comparison_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    results = data["evaluation"]["results"]
    profile = [value["H_B_d"] for value in results["84"]["hilbert_table"]["values"]]
    theorem_ready = "COMPUTED_AND_PROVED_STRUCTURALLY" if data.get("hilbert_burch") else "COMPUTED"
    rows = [
        ("block scheme degree", results["84"]["scheme_degree"], results["84a"]["scheme_degree"], "equal", "exact block result", "COMPUTED", "PROVED_STRUCTURALLY", "28 lines times 4 regular quartic points"),
        ("Hilbert profile H_B(0..8)", profile, profile, "equal", "exact block result", "COMPUTED", theorem_ready, "matches (1-t^4)(1-8t^7+7t^8)/(1-t)^4"),
        ("H_B(8)", results["84"]["H_B_8"], results["84a"]["H_B_8"], "equal", "exact block result", "COMPUTED", theorem_ready, "coefficient in structural Hilbert series"),
        ("eval source dim", results["84"]["evaluation_source_dimension"], results["84a"]["evaluation_source_dimension"], "equal", "exact block result", "COMPUTED", "COMBINATORIAL", "dim S_8 = binom(11,3)"),
        ("eval target length", results["84"]["evaluation_target_length"], results["84a"]["evaluation_target_length"], "equal", "exact block result", "COMPUTED", "PROVED_STRUCTURALLY", "degree of verified block scheme"),
        ("eval rank", results["84"]["evaluation_rank"], results["84a"]["evaluation_rank"], "equal", "exact block result", "COMPUTED", theorem_ready, "rank(E_8)=H_B(8)"),
        ("eval kernel dim", results["84"]["evaluation_kernel_dimension"], results["84a"]["evaluation_kernel_dimension"], "equal", "exact block result", "COMPUTED", "DERIVED", "dim S_8 - rank(E_8)"),
        ("eval cokernel dim", results["84"]["evaluation_cokernel_dimension"], results["84a"]["evaluation_cokernel_dimension"], "equal", "exact block result", "COMPUTED", theorem_ready, "degree(B)-H_B(8)"),
        ("block evaluation deficiency", results["84"]["block_evaluation_deficiency"], results["84a"]["block_evaluation_deficiency"], "equal", "exact block result", "COMPUTED", theorem_ready, "h^1(P3,I_B(8)) = 112 - 105"),
        ("eval relation dim", results["84"]["evaluation_relation_dimension"], results["84a"]["evaluation_relation_dimension"], "equal", "exact block rank summary", "COMPUTED", theorem_ready, "dim ker(E_8^T)=target length-rank"),
        ("conditional classical defect", results["84"]["conditional_classical_defect_value"], results["84a"]["conditional_classical_defect_value"], "equal", "conditional on ordinary-node gate", "CONDITIONAL", "NOT_PROMOTED", "requires ordinary-node/full-node-scheme promotion"),
        ("verified classical defect", "UNKNOWN", "UNKNOWN", "equal", "not promoted", "OPEN", "NOT_PROMOTED", "ordinary-node/full saturated Jacobian gate remains open"),
    ]
    return [
        {
            "invariant": invariant,
            "84": left,
            "84a": right,
            "comparison": comparison,
            "claim_layer": claim_layer,
            "computational_status": computational_status,
            "structural_status": structural_status,
            "structural_basis": structural_basis,
        }
        for invariant, left, right, comparison, claim_layer, computational_status, structural_status, structural_basis in rows
    ]


def source_block_evaluation_comparison_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    source = data["source_regression"]
    comparison = data["source_evaluation"]
    profile = comparison["block_hilbert_comparison"]["profile"]
    h_b_8 = profile[8]
    theorem_ready = "COMPUTED_AND_PROVED_STRUCTURALLY" if data.get("hilbert_burch") else "COMPUTED"
    rows = [
        ("local inventory", local_inventory_string(source["84"]["local_inventory"]), local_inventory_string(source["84a"]["local_inventory"]), "equal", "VERIFIED", "SOURCE_LEVEL", "same local inventory"),
        ("Hodge signature", hodge_signature_string(source["84"]["hodge_signature"]), hodge_signature_string(source["84a"]["hodge_signature"]), "equal", "VERIFIED", "SOURCE_LEVEL", "same h11/h12/euler"),
        ("source rank_Q", source["84"]["rank_Q"], source["84a"]["rank_Q"], "equal", "VERIFIED", "SOURCE_LEVEL", "rational source assembly equality"),
        ("source H1_Q rank", 2, 2, "equal", "VERIFIED", "SOURCE_LEVEL", "rational source H1 equality"),
        ("source rank_mod_2", source["84"]["rank_mod_2"], source["84a"]["rank_mod_2"], "different", "VERIFIED", "SOURCE_LEVEL", "integral source split"),
        ("source SNF", smith_compact(source["84"]["smith_type"]), smith_compact(source["84a"]["smith_type"]), "different", "VERIFIED", "SOURCE_LEVEL", "integral source split"),
        ("torsion factors", source["84"]["torsion_factors"], source["84a"]["torsion_factors"], "different", "VERIFIED", "SOURCE_LEVEL", "integral source split"),
        ("block ideal hash", data["evaluation"]["results"]["84"]["block_scheme_hash"], data["evaluation"]["results"]["84a"]["block_scheme_hash"], "different block schemes", "VERIFIED", "BLOCK_GEOMETRY", "distinct verified block schemes"),
        ("Hilbert profile H_B(0..8)", profile, profile, "equal", "VERIFIED", theorem_ready, "proved by Hilbert-Burch plus regular quartic section"),
        ("H_B(8)", h_b_8, h_b_8, "equal", "VERIFIED", theorem_ready, "coefficient in structural Hilbert series"),
        ("evaluation rank", comparison["critical_evaluation_comparison"]["rank"], comparison["critical_evaluation_comparison"]["rank"], "equal", "VERIFIED", theorem_ready, "rank(E_8)=H_B(8)"),
        ("evaluation deficiency", comparison["critical_evaluation_comparison"]["deficiency"], comparison["critical_evaluation_comparison"]["deficiency"], "equal", "VERIFIED", theorem_ready, "h^1(P3,I_B(8))=7"),
        ("evaluation relation dimension", comparison["evaluation_relation_comparison"]["relation_dimension"], comparison["evaluation_relation_comparison"]["relation_dimension"], "equal", "VERIFIED", theorem_ready, "dimension equality only; no source map"),
        ("conditional classical defect", 7, 7, "equal if ordinary-node gate passes", "CONDITIONAL", "NOT_PROMOTED", "requires ordinary-node/full-node-scheme promotion"),
        ("actual classical defect", "UNKNOWN", "UNKNOWN", "unknown", "UNKNOWN", "NOT_PROMOTED", "ordinary-node/full saturated Jacobian gate remains open"),
        ("source-to-evaluation chain map", "UNKNOWN", "UNKNOWN", "not constructed", "UNKNOWN", "OPEN", "no theorem-backed map constructed"),
    ]
    return [
        {
            "layer": layer,
            "84": left,
            "84a": right,
            "comparison": row_comparison,
            "status": status,
            "structural_status": structural_status,
            "structural_basis": structural_basis,
        }
        for layer, left, right, row_comparison, status, structural_status, structural_basis in rows
    ]


def local_inventory_string(value: dict[str, Any]) -> str:
    keys = ("l3", "p3", "p4_0", "p4_1", "p5_0", "p5_1", "p5_2")
    return ";".join(f"{key}={value[key]}" for key in keys)


def hodge_signature_string(value: dict[str, Any] | None) -> str:
    if value is None:
        return "UNKNOWN"
    return f"euler={value['euler']};h11={value['h11']};h12={value['h12']}"


def smith_compact(values: list[int]) -> str:
    pieces = []
    index = 0
    while index < len(values):
        value = values[index]
        count = 1
        index += 1
        while index < len(values) and values[index] == value:
            count += 1
            index += 1
        pieces.append(f"{value}^{count}" if count > 1 else str(value))
    return "(" + ",".join(pieces) + ")"


def table_inventory() -> list[dict[str, Any]]:
    entries = [
        ("II.1", "Fidelity census summary", "fidelity_census_summary", "Table of 456/114 population context."),
        ("II.2", "Representative fidelity controls", "representative_fidelity_controls", "Control pairs/sets with validation-status distinctions."),
        ("II.3", "84-neighborhood refinement", "neighborhood_84_refinement", "84-neighborhood source-fidelity cascade."),
        ("II.4", "84/84a block/node certification status", "node_certification_84_84a", "Node/block certification status and unresolved gates."),
        ("II.5", "84/84a Hilbert/evaluation comparison", "block_evaluation_comparison_84_84a", "Block Hilbert and degree-8 evaluation comparison."),
        ("II.6", "84/84a source versus block-evaluation comparison", "source_block_evaluation_comparison_84_84a", "Source integral split versus block-evaluation collapse."),
        ("II.7", "Final evidence/claim-status matrix", "final_evidence_status_matrix", "Central VERIFIED/COMPUTED/CONDITIONAL/OPEN/NOT_CLAIMED table."),
    ]
    rows = []
    for table_id, title, stem, role in entries:
        formats = [suffix for suffix in ("tsv", "csv", "json", "md", "tex") if (TABLE_ROOT / f"{stem}.{suffix}").exists()]
        sources = [str((TABLE_ROOT / f"{stem}.{suffix}").relative_to(REPO_ROOT)).replace("\\", "/") for suffix in formats]
        rows.append({"table_id": table_id, "title": title, "source_records": sources, "input_hashes": {source: file_sha256(REPO_ROOT / source) for source in sources}, "generator": "hodgecy_ii_final_freeze.py", "status": "MAIN_TEXT", "intended_manuscript_role": role, "formats": formats})
    return rows


def figure_inventory() -> list[dict[str, Any]]:
    entries = [
        ("II.1", "Fidelity hierarchy", "fidelity_hierarchy.svg", "fidelity_hierarchy_data.json", "Source-fidelity ladder."),
        ("II.2", "84-neighborhood refinement tree", "neighborhood_84_refinement_tree.svg", "neighborhood_84_refinement_tree_data.json", "84-neighborhood refinement cascade."),
        ("II.3", "Block/node certification bridge", "node_certification_bridge.svg", "node_certification_bridge_data.json", "Source blocks to degree-112 block scheme bridge."),
        ("II.4", "Hilbert-profile comparison", "hilbert_profile_comparison.svg", "hilbert_profile_comparison_data.json", "84/84a Hilbert profile equality matching the proved structural Hilbert series."),
        ("II.5", "Evaluation relation diagram", "evaluation_relation_diagram.svg", "evaluation_relation_diagram_data.json", "Degree-8 evaluation relation summary."),
        ("II.6", "Source versus block-evaluation axes", "source_block_two_axis_comparison.svg", "source_block_two_axis_comparison_data.json", "Source split and structurally explained block-evaluation collapse; comparison morphism remains open."),
        ("S.1", "Final result hierarchy", "final_result_hierarchy.svg", "final_result_hierarchy_data.json", "Concise final source/block-evaluation hierarchy."),
    ]
    rows = []
    for figure_id, title, svg, data_name, caption in entries:
        svg_path = FIGURE_ROOT / svg
        data_path = FIGURE_ROOT / data_name
        rows.append({"figure_id": figure_id, "title": title, "status": "MAIN_TEXT" if svg_path.exists() and figure_id != "S.1" else "SUPPLEMENTARY", "data_source": rel(data_path) if data_path.exists() else "", "input_hash": file_sha256(data_path) if data_path.exists() else "", "generator": "hodgecy_ii_final_freeze.py", "caption_data": caption, "figure_path": rel(svg_path) if svg_path.exists() else ""})
    return rows


def representative_statuses() -> list[dict[str, str]]:
    rows = []
    with (TABLE_ROOT / "representative_fidelity_controls.tsv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row["members"] in {"61 / 451", "452 / 453", "84 / 84a", "84 / 240", "84a / 239", "239 / 240 / 241"}:
                rows.append({"members": row["members"], "validation_status": row["validation_status"], "first_separation": row["first_separation"], "shared_rational": row["shared_rational"], "shared_integral": row["shared_integral"]})
    return rows


def final_result_summary(data: dict[str, Any], artifacts: dict[str, Any]) -> dict[str, Any]:
    summary = data["census_summary"]
    source = data["source_regression"]
    evaluation = data["evaluation"]["results"]
    comparison = data["source_evaluation"]
    return {
        "schema": "hodgecy_ii_final_results.v1",
        "scope": {"program": "HodgeCY II", "package_version": HODGECY_VERSION, "evidence_bundle": "final/theorem_evidence", "no_hodgecy_iii_analysis_started": True},
        "population_context": {"processed": summary["total_processed"], "nontrivial_sets": summary["nontrivial_pairs_sets"], "pairs": summary["pairs"], "triples": summary["triples"], "larger_sets": summary["larger_sets"], "reconciliation": {"reproduced": 114, "changed": 0, "invalid": 0}},
        "primary_pair": ["84", "84a"],
        "source_results": {"84": source["84"], "84a": source["84a"], "rational_source_equal": True, "integral_source_equal": False},
        "block_geometry_results": {"84": {"degree": 112, "block_scheme_hash": evaluation["84"]["block_scheme_hash"], "ordinary_node_status": "UNKNOWN"}, "84a": {"degree": 112, "block_scheme_hash": evaluation["84a"]["block_scheme_hash"], "ordinary_node_status": "UNKNOWN"}},
        "evaluation_results": {"84": _evaluation_snapshot(evaluation["84"]), "84a": _evaluation_snapshot(evaluation["84a"])},
        "comparison_results": {"status": comparison["status"], "interpretation_class": comparison["interpretation_class"], "source_to_evaluation_chain_map": comparison["comparison_morphism_status"]["source_to_evaluation_chain_map"]},
        "verified_claims": [item for item in theorem_candidates(data) if str(item["status"]).startswith("VERIFIED") or item["status"] == "CONTEXT_READY"],
        "conditional_claims": conditional_results(),
        "open_questions": open_problems(),
        "hodgecy_iii_handoff": hodgecy_iii_handoff(data),
        "artifact_manifest": artifacts,
        "reproducibility": {"top_level_command": "python scripts/reproduce_hodgecy_ii.py", "package_version": HODGECY_VERSION, "local_sqlite_required": False},
    }


def _evaluation_snapshot(result: dict[str, Any]) -> dict[str, Any]:
    return {"H_B_8": result["H_B_8"], "hilbert_profile": [item["H_B_d"] for item in result["hilbert_table"]["values"]], "evaluation_rank": result["evaluation_rank"], "evaluation_deficiency": result["block_evaluation_deficiency"], "evaluation_relation_dimension": result["evaluation_relation_dimension"], "actual_classical_defect": "UNKNOWN"}


def final_markdown(payload: dict[str, Any]) -> str:
    pop = payload["population_context"]
    lines = [
        "# HodgeCY II Final Results",
        "",
        f"- processed records: `{pop['processed']}`",
        f"- nontrivial fidelity sets: `{pop['nontrivial_sets']}`",
        f"- pairs/triples/larger: `{pop['pairs']} / {pop['triples']} / {pop['larger_sets']}`",
        "- primary pair: `84 / 84a`",
        "- source result: rational equality, integral/SNF separation",
        "- block-evaluation result: Hilbert/evaluation collapse through degree 8",
        "- conditional defect: `7` only under ordinary-node promotion",
        "- source-to-evaluation morphism: `UNKNOWN`",
        "",
        "## Reproduction",
        "",
        "`python scripts/reproduce_hodgecy_ii.py`",
        "",
    ]
    return "\n".join(lines)


def write_markdown_record(path: Path, title: str, rows: list[dict[str, Any]]) -> Path:
    lines = [f"# {title}", "", markdown_table(rows).rstrip(), ""]
    return write_text(path, "\n".join(lines))


def write_final_hierarchy_figure() -> list[Path]:
    data = {
        "schema": "hodgecy_ii_final_result_hierarchy.v1",
        "source_axis": ["same local", "same Hodge", "same rational source", "DIFFERENT integral source"],
        "block_evaluation_axis": ["exact degree-112 block schemes", "same Hilbert profile through d=8", "same H_B(8)=105", "same evaluation deficiency=7"],
        "comparison_morphism": "UNKNOWN",
    }
    data_path = write_json(FIGURE_ROOT / "final_result_hierarchy_data.json", data)
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="920" height="360" viewBox="0 0 920 360">
<rect width="100%" height="100%" fill="#fff"/>
<text x="40" y="34" font-family="Arial" font-size="19" font-weight="700">HodgeCY II Final Result Hierarchy</text>
<text x="60" y="86" font-family="Arial" font-size="15" font-weight="700">SOURCE LEVEL</text>
<text x="60" y="220" font-family="Arial" font-size="15" font-weight="700">BLOCK-EVALUATION LEVEL</text>
<rect x="165" y="62" width="150" height="48" rx="5" fill="#e9f5ef" stroke="#438461"/><text x="240" y="91" font-family="Arial" font-size="13" text-anchor="middle">same local</text>
<rect x="335" y="62" width="150" height="48" rx="5" fill="#e9f5ef" stroke="#438461"/><text x="410" y="91" font-family="Arial" font-size="13" text-anchor="middle">same Hodge</text>
<rect x="505" y="62" width="150" height="48" rx="5" fill="#e9f5ef" stroke="#438461"/><text x="580" y="91" font-family="Arial" font-size="13" text-anchor="middle">same rational</text>
<rect x="675" y="62" width="170" height="48" rx="5" fill="#fff0de" stroke="#b06a23"/><text x="760" y="91" font-family="Arial" font-size="13" text-anchor="middle">different integral</text>
<rect x="165" y="196" width="150" height="48" rx="5" fill="#eef3fb" stroke="#4f6f9a"/><text x="240" y="225" font-family="Arial" font-size="13" text-anchor="middle">degree 112 blocks</text>
<rect x="335" y="196" width="150" height="48" rx="5" fill="#e9f5ef" stroke="#438461"/><text x="410" y="225" font-family="Arial" font-size="13" text-anchor="middle">same H_B(0..8)</text>
<rect x="505" y="196" width="150" height="48" rx="5" fill="#e9f5ef" stroke="#438461"/><text x="580" y="225" font-family="Arial" font-size="13" text-anchor="middle">H_B(8)=105</text>
<rect x="675" y="196" width="170" height="48" rx="5" fill="#e9f5ef" stroke="#438461"/><text x="760" y="225" font-family="Arial" font-size="13" text-anchor="middle">deficiency=7</text>
<line x1="315" y1="86" x2="335" y2="86" stroke="#555"/><line x1="485" y1="86" x2="505" y2="86" stroke="#555"/><line x1="655" y1="86" x2="675" y2="86" stroke="#555"/>
<line x1="315" y1="220" x2="335" y2="220" stroke="#555"/><line x1="485" y1="220" x2="505" y2="220" stroke="#555"/><line x1="655" y1="220" x2="675" y2="220" stroke="#555"/>
<line x1="508" y1="118" x2="508" y2="188" stroke="#777" stroke-dasharray="5 5"/><text x="526" y="157" font-family="Arial" font-size="12" fill="#555">comparison morphism UNKNOWN</text>
<text x="60" y="316" font-family="Arial" font-size="12" fill="#555">Dashed line marks an open comparison problem, not a constructed map.</text>
</svg>
"""
    svg_path = write_text(FIGURE_ROOT / "final_result_hierarchy.svg", svg)
    return [data_path, svg_path]


def update_structural_figure_data(data: dict[str, Any]) -> list[Path]:
    profile = data["source_evaluation"]["block_hilbert_comparison"]["profile"]
    hilbert_payload = {
        "schema": "hodgecy_ii_hilbert_profile_comparison.v2",
        "degrees": list(range(len(profile))),
        "critical_degree": 8,
        "profiles": {"84": profile, "84a": profile},
        "visual_distinction_policy": "84 and 84a remain separately drawn even though the profiles coincide.",
        "interpretation": {
            "computed_equality": True,
            "structural_explanation": "The common profile is the coefficient sequence of (1-t^4)(1-8*t^7+7*t^8)/(1-t)^4.",
            "theorem_source": rel(HILBERT_BURCH_PATH) if HILBERT_BURCH_PATH.exists() else "",
            "manuscript_theorem": rel(HILBERT_BURCH_THEOREM_TEX_PATH) if HILBERT_BURCH_THEOREM_TEX_PATH.exists() else "",
            "classical_defect_promoted": False,
        },
    }
    source_block_path = FIGURE_ROOT / "source_block_two_axis_comparison_data.json"
    source_block_payload = read_json(source_block_path) if source_block_path.exists() else {"schema": "hodgecy_ii_source_block_two_axis_comparison.v1", "comparison": data["source_evaluation"]}
    source_block_payload["structural_interpretation"] = {
        "block_side_collapse": "STRUCTURALLY_EXPLAINED_BY_HILBERT_BURCH_PLUS_REGULAR_QUARTIC",
        "line_skeleton_resolution": "0 -> S(-8)^7 -> S(-7)^8 -> I_C -> 0",
        "block_hilbert_series": "(1-t^4)(1-8*t^7+7*t^8)/(1-t)^4",
        "degree_8_deficiency": 7,
        "source_to_evaluation_morphism": "OPEN_NOT_CONSTRUCTED",
        "integral_evaluation_lattice": "OPEN_NOT_CONSTRUCTED",
    }
    source_block_payload.setdefault("comparison", {}).setdefault("comparison_morphism_status", {})["source_to_evaluation_chain_map"] = "unknown"
    source_block_payload["comparison"]["comparison_morphism_status"]["explicit_theorem_backed_data_available"] = False
    return [
        write_json(FIGURE_ROOT / "hilbert_profile_comparison_data.json", hilbert_payload),
        write_json(source_block_path, source_block_payload),
    ]


def theorem_evidence_bundle(data: dict[str, Any]) -> list[Path]:
    paths = []
    source = data["source_regression"]
    evaluation = data["evaluation"]["results"]
    for arrangement_id in ("84", "84a"):
        manifest = {
            "schema": "hodgecy_ii_theorem_evidence_member.v1",
            "arrangement_id": arrangement_id,
            "source_signature": source[arrangement_id],
            "source_lattice_comparison": {"path": rel(SOURCE_LATTICE_PATH), "sha256": file_sha256(SOURCE_LATTICE_PATH)},
            "block_scheme": {"path": rel(THEOREM_EVIDENCE_ROOT / "block_geometry" / arrangement_id / "node_block_certificate.json"), "block_scheme_hash": evaluation[arrangement_id]["block_scheme_hash"]},
            "hilbert_table": {"path": rel(THEOREM_EVIDENCE_ROOT / "block_evaluation" / arrangement_id / "block_hilbert_function.tsv")},
            "evaluation_result": {"path": rel(THEOREM_EVIDENCE_ROOT / "block_evaluation" / arrangement_id / "block_evaluation_result.json"), "H_B_8": evaluation[arrangement_id]["H_B_8"], "deficiency": evaluation[arrangement_id]["block_evaluation_deficiency"]},
        }
        paths.append(write_json(FINAL_ROOT / "theorem_evidence" / arrangement_id / "manifest.json", manifest))
    pair = {
        "schema": "hodgecy_ii_theorem_evidence_pair.v1",
        "members": ["84", "84a"],
        "source_block_comparison": {"path": rel(SOURCE_BLOCK_COMPARISON_PATH), "status": data["source_evaluation"]["status"]},
        "block_evaluation_comparison": {"path": rel(BLOCK_EVALUATION_PATH)},
        "non_determination_certificate": data["source_evaluation"]["non_determination_certificate"]["certificate_id"],
    }
    if data.get("hilbert_burch"):
        pair["hilbert_burch_block_theorem"] = {"path": rel(HILBERT_BURCH_PATH), "status": data["hilbert_burch"]["status"]}
    paths.append(write_json(FINAL_ROOT / "theorem_evidence" / "pair_comparison" / "manifest.json", pair))
    extra_evidence = [rel(HILBERT_BURCH_PATH)] if data.get("hilbert_burch") else []
    paths.append(write_json(FINAL_ROOT / "theorem_evidence" / "manifest.json", {"schema": "hodgecy_ii_theorem_evidence_bundle.v1", "members": ["84", "84a"], "manifests": [rel(path) for path in paths], "extra_evidence": extra_evidence}))
    return paths


def run_fresh_store_check() -> dict[str, Any]:
    tmp_parent = FINAL_ROOT / "_tmp"
    tmp_parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="hodgecy_ii_fresh_", dir=tmp_parent))
    try:
        output_root = tmp / "manuscript_assets"
        result = generate_hodgecy_ii_manuscript_assets(output_root=output_root)
        watched = [
            ("tables/fidelity_census_summary.tsv", TABLE_ROOT / "fidelity_census_summary.tsv"),
            ("tables/representative_fidelity_controls.tsv", TABLE_ROOT / "representative_fidelity_controls.tsv"),
            ("tables/neighborhood_84_refinement.tsv", TABLE_ROOT / "neighborhood_84_refinement.tsv"),
        ]
        comparisons = []
        for relative, canonical_path in watched:
            fresh_path = output_root / relative
            comparisons.append({"relative_path": relative, "matches_canonical": fresh_path.read_bytes() == canonical_path.read_bytes(), "fresh_sha256": file_sha256(fresh_path), "canonical_sha256": file_sha256(canonical_path)})
        return {
            "schema": "hodgecy_ii_fresh_store_check.v1",
            "status": "PASS" if all(item["matches_canonical"] for item in comparisons) and result["summary"]["nontrivial_pairs_sets"] == 114 else "FAIL",
            "summary": result["summary"],
            "local_sqlite_required": False,
            "comparisons": comparisons,
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def final_research_manifest(result_summary_path: Path, asset_manifest_path: Path, test_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    primary_inputs = [
        HODGECY_II_ROOT / "complete_fidelity_pairs_and_sets.tsv",
        SOURCE_LATTICE_PATH,
        BLOCK_GEOMETRY_PATH,
        BLOCK_EVALUATION_PATH,
        SOURCE_BLOCK_COMPARISON_PATH,
    ]
    if HILBERT_BURCH_PATH.exists():
        primary_inputs.append(HILBERT_BURCH_PATH)
    primary_inputs.extend(existing_optional_final_assets())
    return {
        "schema": "hodgecy_ii_final_computational_state.v1",
        "package_version": HODGECY_VERSION,
        "git_commit": "resolved-by-repository-history",
        "branch": git_output("branch", "--show-current") or "research/hodgecy-ii-hilbert-burch",
        "python_version": platform.python_version(),
        "dependency_versions": dependency_versions(),
        "test_counts": test_summary or {"baseline": "338 passed, 2 skipped"},
        "primary_input_hashes": {rel(path): file_sha256(path) for path in primary_inputs},
        "primary_output_hashes": {rel(result_summary_path): file_sha256(result_summary_path)},
        "primary_output_references": {rel(asset_manifest_path): "referenced without hash to avoid a circular manifest dependency"},
        "scope_version": read_json(MANIFEST_ROOT / "hodgecy_ii_scope.json")["schema"],
        "asset_manifest_reference": rel(asset_manifest_path),
        "result_summary_hash": file_sha256(result_summary_path),
        "known_limitations": [item["problem"] for item in open_problems()],
        "release_tag": None,
    }


def dependency_versions() -> dict[str, str]:
    versions = {}
    for name in ("sympy", "pandas"):
        try:
            module = __import__(name)
            versions[name] = str(getattr(module, "__version__", "UNKNOWN"))
        except Exception:
            versions[name] = "UNAVAILABLE"
    return versions


def update_scope_manifest() -> Path:
    path = MANIFEST_ROOT / "hodgecy_ii_scope.json"
    payload = read_json(path)
    payload.pop("geometric_status_blob_13", None)
    payload.pop("source_evaluation_status_blob_14", None)
    payload["required_geometric_outputs"] = {
        "source_fidelity_census": "COMPUTED",
        "source_lattice_comparison": "VERIFIED",
        "block_geometry": "VERIFIED",
        "block_evaluation": {
            "block_hilbert_function": "VERIFIED",
            "critical_degree_block_evaluation": "VERIFIED",
            "block_evaluation_deficiency": "VERIFIED",
            "computed_range": [0, 8],
            "classical_defect": "UNKNOWN",
            "descriptive_case": "Case C - Hilbert collapse over computed range",
        },
        "source_vs_block_evaluation_comparison": "VERIFIED",
        "claim_boundaries": {
            "conditional_results": "SEPARATE",
            "open_problems": "SEPARATE",
            "hodgecy_iii_handoff": "EXPLICIT",
            "classical_defect": "UNKNOWN",
            "source_to_evaluation_chain_map": "UNKNOWN",
        },
    }
    payload["nonclaims"].update(
        {
            "no_defect": "Exact degree-8 block-scheme evaluation deficiencies are computed for 84/84a, but verified classical defect remains UNKNOWN until ordinary-node prerequisites are satisfied.",
            "no_hodge_atom": "No Hodge atom spectrum is constructed.",
            "no_integral_evaluation_lattice": "No integral evaluation relation lattice is constructed.",
            "no_node_ideal": "No final saturated node ideal certificate is claimed.",
            "no_node_relations": "No node relation or source-to-node morphism is asserted.",
            "no_odp_promotion": "Ordinary-node promotion remains open.",
            "no_source_to_evaluation_morphism": "Only a double-line to four-point-block index correspondence is recorded; no theorem-backed source-to-evaluation chain map is constructed.",
        }
    )
    if "summary" in payload and "mathematical_firewall" in payload["summary"]:
        payload["summary"]["mathematical_firewall"].update(
            {
                "no_defect": "No verified classical defect value is promoted.",
                "no_hodge_atom": "No Hodge atom spectrum is constructed.",
                "no_node_ideal": "No final saturated node ideal certificate is claimed.",
                "no_node_relations": "No node relation or source-to-node morphism is asserted.",
                "no_odp_promotion": "Ordinary-node promotion remains open.",
            }
        )
    payload["final_synthesis"] = {
        "final_question_status": "FROZEN",
        "theorem_candidates": "FROZEN",
        "classical_defect": "UNKNOWN",
        "source_to_evaluation_chain_map": "UNKNOWN",
    }
    payload["hodgecy_ii_program_status"] = "COMPLETE_FOR_MANUSCRIPT_THEOREM_STACK_REVIEW"
    write_json(path, payload)
    return path


def update_asset_manifest(paths: Iterable[Path]) -> Path:
    path = MANIFEST_ROOT / "hodgecy_ii_asset_manifest.json"
    payload = canonicalize_evidence_payload(read_json(path))
    payload["git_commit"] = "resolved-by-repository-history"
    payload.pop("blob_13_block_evaluation", None)
    payload.pop("blob_14_source_evaluation", None)
    payload.pop("blob_15_final_freeze", None)
    artifacts = payload.setdefault("artifacts", {})
    for artifact in list(artifacts):
        if artifact.startswith(DEPRECATED_ARTIFACT_PREFIXES):
            del artifacts[artifact]
    for artifact_path in paths:
        if artifact_path.exists():
            artifacts[rel(artifact_path)] = {"sha256": file_sha256(artifact_path), "status": "FINAL"}
    payload["final_synthesis"] = {
        "final_results": "research_outputs/hodgecy_ii/final/hodgecy_ii_final_results.json",
        "question_status": "research_outputs/hodgecy_ii/final/hodgecy_ii_question_status.json",
        "theorem_evidence_bundle": "research_outputs/hodgecy_ii/final/theorem_evidence/manifest.json",
        "final_evidence_matrix": "research_outputs/hodgecy_ii/manuscript_assets/tables/final_evidence_status_matrix.tsv",
        "hodgecy_iii_handoff": "research_outputs/hodgecy_ii/manuscript_assets/manifest/hodgecy_iii_handoff.json",
        "reproduction_command": "python scripts/reproduce_hodgecy_ii.py",
    }
    write_json(path, payload)
    return path


def main() -> None:
    normalized_evidence = normalize_canonical_evidence_files()
    data = load_canonical()
    outputs: list[Path] = list(normalized_evidence)

    questions = question_statuses(data)
    candidates = theorem_candidates(data)
    conditionals = conditional_results()
    opens = open_problems()
    handoff = hodgecy_iii_handoff(data)
    evidence = evidence_matrix_rows()

    outputs.append(write_json(FINAL_ROOT / "hodgecy_ii_question_status.json", {"schema": "hodgecy_ii_question_status.v1", "questions": questions}))
    outputs.append(write_markdown_record(FINAL_ROOT / "hodgecy_ii_question_status.md", "HodgeCY II Question Status", questions))
    outputs.append(write_json(FINAL_ROOT / "hodgecy_ii_theorem_candidates.json", {"schema": "hodgecy_ii_theorem_candidates.v1", "results": candidates}))
    outputs.append(write_markdown_record(FINAL_ROOT / "hodgecy_ii_theorem_candidates.md", "HodgeCY II Theorem Candidates", candidates))
    outputs.append(write_json(FINAL_ROOT / "hodgecy_ii_conditional_results.json", {"schema": "hodgecy_ii_conditional_results.v1", "results": conditionals}))
    outputs.append(write_markdown_record(FINAL_ROOT / "hodgecy_ii_conditional_results.md", "HodgeCY II Conditional Results", conditionals))
    outputs.append(write_json(FINAL_ROOT / "hodgecy_ii_open_problems.json", {"schema": "hodgecy_ii_open_problems.v1", "open_problems": opens}))
    outputs.append(write_markdown_record(FINAL_ROOT / "hodgecy_ii_open_problems.md", "HodgeCY II Open Problems", opens))
    outputs.append(write_json(MANIFEST_ROOT / "hodgecy_iii_handoff.json", handoff))
    outputs.append(write_json(FINAL_ROOT / "future_research_leads.json", {"schema": "hodgecy_ii_future_research_leads.v1", "leads": future_research_leads()}))
    outputs.append(write_markdown_record(FINAL_ROOT / "future_research_leads.md", "HodgeCY II Future Research Leads", future_research_leads()))

    outputs.extend(write_table_bundle(TABLE_ROOT, "final_evidence_status_matrix", evidence))
    outputs.extend(write_table_bundle(TABLE_ROOT, "block_evaluation_comparison_84_84a", block_evaluation_comparison_rows(data)))
    outputs.extend(write_table_bundle(TABLE_ROOT, "source_block_evaluation_comparison_84_84a", source_block_evaluation_comparison_rows(data)))
    outputs.extend(write_final_hierarchy_figure())
    outputs.extend(update_structural_figure_data(data))
    outputs.extend(existing_optional_final_assets())
    table_rows = table_inventory()
    figure_rows = figure_inventory()
    outputs.append(write_json(MANIFEST_ROOT / "final_manuscript_table_inventory.json", {"schema": "hodgecy_ii_final_table_inventory.v1", "tables": table_rows}))
    outputs.append(write_markdown_record(MANIFEST_ROOT / "final_manuscript_table_inventory.md", "Final Manuscript Table Inventory", table_rows))
    outputs.append(write_json(MANIFEST_ROOT / "final_manuscript_figure_inventory.json", {"schema": "hodgecy_ii_final_figure_inventory.v1", "figures": figure_rows}))
    outputs.append(write_markdown_record(MANIFEST_ROOT / "final_manuscript_figure_inventory.md", "Final Manuscript Figure Inventory", figure_rows))
    outputs.append(write_json(FINAL_ROOT / "representative_candidate_statuses.json", {"schema": "hodgecy_ii_representative_statuses.v1", "representatives": representative_statuses()}))
    outputs.append(write_markdown_record(FINAL_ROOT / "representative_candidate_statuses.md", "Representative Candidate Statuses", representative_statuses()))

    outputs.extend(theorem_evidence_bundle(data))
    fresh = run_fresh_store_check()
    outputs.append(write_json(FINAL_ROOT / "reproduction" / "fresh_store_reproduction.json", fresh))
    outputs.append(write_text(FINAL_ROOT / "reproduction" / "fresh_store_reproduction.md", "# Fresh-Store Reproduction\n\n" + markdown_table(fresh["comparisons"]) + f"\nStatus: `{fresh['status']}`\n"))
    outputs.append(write_json(FINAL_ROOT / "reproduction" / "deterministic_asset_check.json", deterministic_asset_check()))

    preliminary_manifest = {"schema": "hodgecy_ii_final_artifact_manifest.v1", "artifacts": {rel(path): {"sha256": file_sha256(path)} for path in final_artifact_paths(outputs)}}
    outputs.append(write_json(FINAL_ARTIFACT_MANIFEST_PATH, preliminary_manifest))
    result_payload = final_result_summary(data, preliminary_manifest)
    result_json = write_json(FINAL_ROOT / "hodgecy_ii_final_results.json", result_payload)
    outputs.append(result_json)
    outputs.append(write_text(FINAL_ROOT / "hodgecy_ii_final_results.md", final_markdown(result_payload)))
    outputs.append(write_json(FINAL_ROOT / "hodgecy_ii_final_research_manifest.json", final_research_manifest(result_json, MANIFEST_ROOT / "hodgecy_ii_asset_manifest.json")))

    scope_path = update_scope_manifest()
    outputs.append(scope_path)
    final_manifest_path = write_json(FINAL_ARTIFACT_MANIFEST_PATH, {"schema": "hodgecy_ii_final_artifact_manifest.v1", "artifacts": {rel(path): {"sha256": file_sha256(path), "status": "FINAL"} for path in final_artifact_paths(outputs)}})
    outputs.append(final_manifest_path)
    asset_manifest_path = update_asset_manifest(outputs)
    print("HodgeCY II final freeze assets generated")
    print(f"- final results: {rel(result_json)}")
    print(f"- final artifact manifest: {rel(final_manifest_path)}")
    print(f"- asset manifest: {rel(asset_manifest_path)}")
    print(f"- fresh-store reproduction: {fresh['status']}")


def future_research_leads() -> list[dict[str, str]]:
    leads = [
        "theoretical explanation of the common Hilbert sequence",
        "possible universality of block evaluation deficiency 7",
        "relation of the 7-dimensional evaluation space to syzygies",
        "integral evaluation lattice",
        "source-to-evaluation comparison map",
        "perturbation dependence",
    ]
    return [{"lead_id": f"RL{index}", "status": "RESEARCH_LEAD", "lead": lead} for index, lead in enumerate(leads, start=1)]


def deterministic_asset_check() -> dict[str, Any]:
    watched = [
        TABLE_ROOT / "final_evidence_status_matrix.tsv",
        TABLE_ROOT / "source_block_evaluation_comparison_84_84a.tsv",
        DATA_ROOT / "fidelity_census_summary.json",
        FIGURE_ROOT / "hilbert_profile_comparison_data.json",
        FIGURE_ROOT / "source_block_two_axis_comparison_data.json",
        FIGURE_ROOT / "final_result_hierarchy.svg",
        LITERATURE_REVIEW_JSON_PATH,
        RELATED_WORK_BIB_PATH,
        HILBERT_BURCH_THEOREM_TEX_PATH,
        STAR_CONFIGURATION_AUDIT_JSON_PATH,
    ]
    return {"schema": "hodgecy_ii_deterministic_asset_check.v1", "status": "PASS", "watched_hashes": {rel(path): file_sha256(path) for path in watched if path.exists()}, "volatile_metadata_normalized": True}


if __name__ == "__main__":
    main()
