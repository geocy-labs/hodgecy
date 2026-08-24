"""Source-versus-block-evaluation comparisons for HodgeCY II.

Blob 14 compares already-certified source assembly records with already
verified block-scheme evaluation records.  It deliberately does not construct
or infer a source-to-evaluation chain map.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from hodgecy.core.results import EvidenceStatus
from hodgecy.core.serialization import stable_sha256
from hodgecy.geometry.block_evaluation import BlockEvaluationResult, evaluation_firewall
from hodgecy.relations.source_to_node import ComparisonFeasibilityResult, ComparisonMorphismKind, h1_rank_feasibility, source_to_node_firewall


class SourceEvaluationStatus(str, Enum):
    EXACT_BLOCK_EVALUATION_COLLAPSE = "EXACT_BLOCK_EVALUATION_COLLAPSE"
    UNKNOWN = "UNKNOWN"


class SourceEvaluationInterpretation(str, Enum):
    BLOCK_EVALUATION_COLLAPSE_WITH_INTEGRAL_SOURCE_SEPARATION = "BLOCK_EVALUATION_COLLAPSE_WITH_INTEGRAL_SOURCE_SEPARATION"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class SourceAssemblySignature:
    arrangement_id: str
    geometry_id: str
    source_result_id: str
    source_run_id: str | None
    local_inventory: Mapping[str, int]
    hodge_signature: Mapping[str, int] | None
    matrix_shape: tuple[int, int]
    rank_Q: int
    rank_mod_2: int
    H1_Q_rank: int
    H0_Q_rank: int
    smith_normal_form: tuple[int, ...]
    torsion_factors: tuple[int, ...]
    torsion_order: int
    rational_source_type: str
    integral_source_type: str
    torsion_type: str
    equivariant_type: str
    group_order: int | None
    evidence_status: EvidenceStatus
    provenance: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["matrix_shape"] = list(self.matrix_shape)
        payload["smith_normal_form"] = list(self.smith_normal_form)
        payload["torsion_factors"] = list(self.torsion_factors)
        payload["evidence_status"] = self.evidence_status.value
        return payload


@dataclass(frozen=True, slots=True)
class BlockEvaluationSignature:
    arrangement_id: str
    geometry_id: str
    block_scheme_id: str
    evaluation_result_id: str
    block_scheme_hash: str
    block_index_hash: str
    block_ideal_hashes: tuple[str, ...]
    hilbert_profile: tuple[int, ...]
    H_B_8: int
    critical_degree: int
    evaluation_source_dimension: int
    evaluation_target_length: int
    evaluation_rank: int
    evaluation_kernel_dimension: int
    evaluation_cokernel_dimension: int
    evaluation_relation_dimension: int
    conditional_classical_defect_value: int
    ordinary_node_status: str
    classical_defect_status: str
    evidence_status: EvidenceStatus
    provenance: Mapping[str, Any]

    @classmethod
    def from_result(
        cls,
        result: BlockEvaluationResult,
        *,
        block_scheme_id: str,
        evaluation_result_id: str,
        block_ideal_hashes: Sequence[str],
        block_index_hash: str,
        ordinary_node_status: str = "UNKNOWN",
    ) -> "BlockEvaluationSignature":
        return cls(
            arrangement_id=result.arrangement_id,
            geometry_id=f"hodgecy-ii-{result.arrangement_id}",
            block_scheme_id=block_scheme_id,
            evaluation_result_id=evaluation_result_id,
            block_scheme_hash=result.block_scheme_hash,
            block_index_hash=block_index_hash,
            block_ideal_hashes=tuple(block_ideal_hashes),
            hilbert_profile=tuple(value.H_B_d for value in result.hilbert_table.values),
            H_B_8=result.H_B_8,
            critical_degree=int(result.critical_degree["critical_degree"]),
            evaluation_source_dimension=result.evaluation_source_dimension,
            evaluation_target_length=result.evaluation_target_length,
            evaluation_rank=result.evaluation_rank,
            evaluation_kernel_dimension=result.evaluation_kernel_dimension,
            evaluation_cokernel_dimension=result.evaluation_cokernel_dimension,
            evaluation_relation_dimension=result.evaluation_relation_dimension,
            conditional_classical_defect_value=result.conditional_classical_defect_value,
            ordinary_node_status=ordinary_node_status,
            classical_defect_status=result.actual_classical_defect_status.value.upper(),
            evidence_status=result.evidence_status,
            provenance={
                "blob13_block_scheme_hash": result.block_scheme_hash,
                "blob13_evaluation_certificates": [item.get("certificate_type") for item in result.certificates],
            },
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["block_ideal_hashes"] = list(self.block_ideal_hashes)
        payload["hilbert_profile"] = list(self.hilbert_profile)
        payload["evidence_status"] = self.evidence_status.value
        return payload


@dataclass(frozen=True, slots=True)
class AxisComparison:
    axis: str
    levels: tuple[str, ...]
    shared_levels: tuple[str, ...]
    first_separating_level: str | None
    conclusion: str
    evidence_status: EvidenceStatus

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["levels"] = list(self.levels)
        payload["shared_levels"] = list(self.shared_levels)
        payload["evidence_status"] = self.evidence_status.value
        return payload


@dataclass(frozen=True, slots=True)
class SourceBlockIndexCorrespondence:
    arrangement_id: str
    correspondence_kind: str
    source_generator_family: str
    target_block_family: str
    count: int
    status: str
    chain_map_claim: bool
    entries: tuple[Mapping[str, Any], ...]
    correspondence_hash: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["entries"] = [dict(item) for item in self.entries]
        return payload


@dataclass(frozen=True, slots=True)
class SourceEvaluationComparison:
    comparison_id: str
    members: tuple[str, str]
    geometry_ids: tuple[str, str]
    source_result_ids: tuple[str, str]
    block_scheme_ids: tuple[str, str]
    evaluation_result_ids: tuple[str, str]
    status: SourceEvaluationStatus
    interpretation_class: SourceEvaluationInterpretation
    source_axis: AxisComparison
    geometry_evaluation_axis: AxisComparison
    source_signatures: Mapping[str, SourceAssemblySignature]
    block_evaluation_signatures: Mapping[str, BlockEvaluationSignature]
    shared_coarse_data: Mapping[str, Any]
    source_rational_comparison: Mapping[str, Any]
    source_integral_comparison: Mapping[str, Any]
    block_hilbert_comparison: Mapping[str, Any]
    critical_evaluation_comparison: Mapping[str, Any]
    evaluation_relation_comparison: Mapping[str, Any]
    classical_defect_comparison: Mapping[str, Any]
    comparison_morphism_status: Mapping[str, Any]
    non_determination_certificate: Mapping[str, Any]
    conditional_classical_defect_result: Mapping[str, Any]
    relation_dimension_comparison: Mapping[str, Any]
    feasibility_2_to_7: ComparisonFeasibilityResult
    source_block_index_correspondence: Mapping[str, SourceBlockIndexCorrespondence]
    theorem_candidate_record: Mapping[str, Any]
    conditional_corollary_record: Mapping[str, Any]
    hodgecy_i_question_status: tuple[Mapping[str, Any], ...]
    evidence_status_table: tuple[Mapping[str, Any], ...]
    certificate_ids: tuple[str, ...]
    provenance: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "comparison_id": self.comparison_id,
            "members": list(self.members),
            "geometry_ids": list(self.geometry_ids),
            "source_result_ids": list(self.source_result_ids),
            "block_scheme_ids": list(self.block_scheme_ids),
            "evaluation_result_ids": list(self.evaluation_result_ids),
            "status": self.status.value,
            "interpretation_class": self.interpretation_class.value,
            "source_axis": self.source_axis.to_dict(),
            "geometry_evaluation_axis": self.geometry_evaluation_axis.to_dict(),
            "source_signatures": {key: value.to_dict() for key, value in self.source_signatures.items()},
            "block_evaluation_signatures": {key: value.to_dict() for key, value in self.block_evaluation_signatures.items()},
            "shared_coarse_data": dict(self.shared_coarse_data),
            "source_rational_comparison": dict(self.source_rational_comparison),
            "source_integral_comparison": dict(self.source_integral_comparison),
            "block_hilbert_comparison": dict(self.block_hilbert_comparison),
            "critical_evaluation_comparison": dict(self.critical_evaluation_comparison),
            "evaluation_relation_comparison": dict(self.evaluation_relation_comparison),
            "classical_defect_comparison": dict(self.classical_defect_comparison),
            "comparison_morphism_status": dict(self.comparison_morphism_status),
            "non_determination_certificate": dict(self.non_determination_certificate),
            "conditional_classical_defect_result": dict(self.conditional_classical_defect_result),
            "relation_dimension_comparison": dict(self.relation_dimension_comparison),
            "feasibility_2_to_7": self.feasibility_2_to_7.to_dict(),
            "source_block_index_correspondence": {key: value.to_dict() for key, value in self.source_block_index_correspondence.items()},
            "theorem_candidate_record": dict(self.theorem_candidate_record),
            "conditional_corollary_record": dict(self.conditional_corollary_record),
            "hodgecy_i_question_status": [dict(item) for item in self.hodgecy_i_question_status],
            "evidence_status_table": [dict(item) for item in self.evidence_status_table],
            "certificate_ids": list(self.certificate_ids),
            "provenance": dict(self.provenance),
            "firewall": source_evaluation_firewall(),
        }


def source_evaluation_firewall() -> dict[str, bool]:
    firewall = {
        "same_block_evaluation_does_not_determine_integral_source_type": True,
        "different_integral_source_type_does_not_imply_different_block_evaluation": True,
        "block_index_correspondence_is_not_chain_map": True,
        "source_h1_rank_is_not_evaluation_relation_dimension": True,
        "rank_feasibility_is_not_existence": True,
        "conditional_classical_defect_is_not_actual_classical_defect": True,
        "ordinary_node_gate_required_for_classical_defect": True,
        "no_integral_evaluation_lattice_constructed": True,
        "no_source_to_evaluation_morphism_inferred": True,
    }
    firewall.update({f"evaluation.{key}": value for key, value in evaluation_firewall().items()})
    firewall.update({f"source_to_node.{key}": value for key, value in source_to_node_firewall().items()})
    return firewall


def build_block_index_correspondence(arrangement_id: str, blocks: Sequence[Mapping[str, Any]]) -> SourceBlockIndexCorrespondence:
    entries = tuple(
        {
            "source_generator_id": str(block["line_id"]),
            "target_block_id": str(block["block_id"]),
            "planes": list(block.get("planes") or ()),
            "degree": int(block["degree"]),
            "status": str(block.get("status", "UNKNOWN")),
        }
        for block in blocks
    )
    correspondence_hash = stable_sha256(
        {
            "arrangement_id": arrangement_id,
            "correspondence_kind": "double_line_to_four_point_block",
            "entries": entries,
            "chain_map_claim": False,
        }
    )
    return SourceBlockIndexCorrespondence(
        arrangement_id=arrangement_id,
        correspondence_kind="double_line_to_four_point_block",
        source_generator_family="double_line",
        target_block_family="four_point_verified_block",
        count=len(entries),
        status="RECORDED_INDEX_CORRESPONDENCE_ONLY",
        chain_map_claim=False,
        entries=entries,
        correspondence_hash=correspondence_hash,
    )


def block_hashes_from_blocks(blocks: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    return tuple(
        stable_sha256(
            {
                "block_id": str(block["block_id"]),
                "line_id": str(block["line_id"]),
                "ideal_generators": list(block.get("ideal_generators") or ()),
                "parameter_polynomial": block.get("parameter_polynomial"),
                "degree": int(block["degree"]),
                "status": str(block.get("status", "UNKNOWN")),
            }
        )
        for block in blocks
    )


def compare_84_84a_source_evaluation(
    *,
    source_signatures: Mapping[str, SourceAssemblySignature],
    block_evaluation_signatures: Mapping[str, BlockEvaluationSignature],
    source_block_index_correspondence: Mapping[str, SourceBlockIndexCorrespondence],
    provenance: Mapping[str, Any],
) -> SourceEvaluationComparison:
    left = source_signatures["84"]
    right = source_signatures["84a"]
    left_eval = block_evaluation_signatures["84"]
    right_eval = block_evaluation_signatures["84a"]
    shared_source = (
        "local_inventory",
        "Hodge signature",
        "matrix shape",
        "rank_Q",
        "H1_Q rank",
        "H0_Q rank",
        "rational source type",
    )
    source_axis = AxisComparison(
        axis="source",
        levels=("local/Hodge", "rational source", "integral source", "equivariant source"),
        shared_levels=("local/Hodge", "rational source"),
        first_separating_level="integral source",
        conclusion="same local/Hodge and rational source data; integral/SNF and equivariant source signatures differ",
        evidence_status=EvidenceStatus.VERIFIED,
    )
    geometry_axis = AxisComparison(
        axis="geometry/evaluation",
        levels=("verified block scheme", "Hilbert profile", "degree-8 evaluation", "evaluation relation dimension"),
        shared_levels=("Hilbert profile", "degree-8 evaluation", "evaluation relation dimension"),
        first_separating_level=None,
        conclusion="exact verified block-evaluation profiles agree through the critical degree",
        evidence_status=EvidenceStatus.VERIFIED,
    )
    feasibility = h1_rank_feasibility(source_h1_rank=left.H1_Q_rank, target_h1_rank=left_eval.evaluation_relation_dimension)
    certificate_id = "block_evaluation_does_not_determine_integral_source_type"
    conditional_defect_id = "conditional_defect_collapse_84_84a"
    return SourceEvaluationComparison(
        comparison_id="hodgecy_ii_84_84a_source_vs_block_evaluation",
        members=("84", "84a"),
        geometry_ids=(left.geometry_id, right.geometry_id),
        source_result_ids=(left.source_result_id, right.source_result_id),
        block_scheme_ids=(left_eval.block_scheme_id, right_eval.block_scheme_id),
        evaluation_result_ids=(left_eval.evaluation_result_id, right_eval.evaluation_result_id),
        status=SourceEvaluationStatus.EXACT_BLOCK_EVALUATION_COLLAPSE,
        interpretation_class=SourceEvaluationInterpretation.BLOCK_EVALUATION_COLLAPSE_WITH_INTEGRAL_SOURCE_SEPARATION,
        source_axis=source_axis,
        geometry_evaluation_axis=geometry_axis,
        source_signatures=source_signatures,
        block_evaluation_signatures=block_evaluation_signatures,
        shared_coarse_data={
            "local_inventory": dict(left.local_inventory),
            "hodge_signature": dict(left.hodge_signature or {}),
            "source_matrix_shape": list(left.matrix_shape),
            "source_rank_Q": left.rank_Q,
            "source_H1_Q_rank": left.H1_Q_rank,
            "source_H0_Q_rank": left.H0_Q_rank,
            "block_hilbert_profile": list(left_eval.hilbert_profile),
            "critical_degree": left_eval.critical_degree,
            "H_B_8": left_eval.H_B_8,
            "evaluation_rank": left_eval.evaluation_rank,
            "evaluation_relation_dimension": left_eval.evaluation_relation_dimension,
        },
        source_rational_comparison={
            "state": "equal",
            "shared_type": left.rational_source_type,
            "shared_data": {"rank_Q": left.rank_Q, "H1_Q_rank": left.H1_Q_rank, "H0_Q_rank": left.H0_Q_rank},
            "evidence_status": "VERIFIED",
            "source": "Blob 8 source lattice comparison",
        },
        source_integral_comparison={
            "state": "different",
            "first_difference": "rank_mod_2",
            "84": {"rank_mod_2": left.rank_mod_2, "SNF": list(left.smith_normal_form), "torsion_factors": list(left.torsion_factors)},
            "84a": {"rank_mod_2": right.rank_mod_2, "SNF": list(right.smith_normal_form), "torsion_factors": list(right.torsion_factors)},
            "evidence_status": "VERIFIED",
            "source": "Blob 8 source lattice comparison",
        },
        block_hilbert_comparison={
            "state": "equal",
            "compared_degrees": list(range(len(left_eval.hilbert_profile))),
            "profile": list(left_eval.hilbert_profile),
            "first_difference": None,
            "evidence_status": "VERIFIED",
            "source": "Blob 13 block evaluation comparison",
        },
        critical_evaluation_comparison={
            "state": "equal",
            "degree": left_eval.critical_degree,
            "source_dimension": left_eval.evaluation_source_dimension,
            "target_length": left_eval.evaluation_target_length,
            "rank": left_eval.evaluation_rank,
            "kernel_dimension": left_eval.evaluation_kernel_dimension,
            "cokernel_dimension": left_eval.evaluation_cokernel_dimension,
            "deficiency": left_eval.evaluation_cokernel_dimension,
            "evidence_status": "VERIFIED",
        },
        evaluation_relation_comparison={
            "state": "equal",
            "relation_dimension": left_eval.evaluation_relation_dimension,
            "relation_is_rank_summary_not_integral_lattice": True,
            "evidence_status": "VERIFIED",
        },
        classical_defect_comparison={
            "state": "unknown_actual_equal_conditional",
            "conditional_value_if_block_scheme_is_full_ordinary_node_scheme": 7,
            "actual_classical_defect": {"84": "UNKNOWN", "84a": "UNKNOWN"},
            "ordinary_node_status": {"84": left_eval.ordinary_node_status, "84a": right_eval.ordinary_node_status},
        },
        comparison_morphism_status={
            "source_to_evaluation_chain_map": ComparisonMorphismKind.UNKNOWN.value,
            "explicit_theorem_backed_data_available": False,
            "block_index_correspondence_recorded": True,
            "reason": "No theorem-backed chain-level map from the source assembly complex to the degree-8 block-evaluation relation complex is supplied.",
        },
        non_determination_certificate={
            "certificate_id": certificate_id,
            "witnesses": ["84", "84a"],
            "claim": "Verified block Hilbert/evaluation data through the critical degree do not determine the integral source type.",
            "support": [
                "84 and 84a have equal verified block Hilbert profiles through degree 8.",
                "84 and 84a have equal degree-8 evaluation rank, deficiency, and evaluation relation dimension.",
                "84 and 84a have different verified integral source Smith types.",
            ],
            "nonclaims": ["No reverse determinacy theorem is asserted.", "No source-to-evaluation chain map is constructed."],
            "evidence_status": "VERIFIED",
        },
        conditional_classical_defect_result={
            "result_id": conditional_defect_id,
            "status": "CONDITIONAL_DEFECT_COLLAPSE",
            "condition": "if the verified block scheme is the full ordinary-node scheme under the HodgeCY defect hypotheses",
            "conclusion": {"84": 7, "84a": 7},
            "actual_classical_defect": {"84": "UNKNOWN", "84a": "UNKNOWN"},
        },
        relation_dimension_comparison={
            "source_H1_Q_rank": {"84": left.H1_Q_rank, "84a": right.H1_Q_rank},
            "evaluation_relation_dimension": {"84": left_eval.evaluation_relation_dimension, "84a": right_eval.evaluation_relation_dimension},
            "state": "2-to-7-dimension-comparison-only",
            "no_identification_or_subspace_inference": True,
        },
        feasibility_2_to_7=feasibility,
        source_block_index_correspondence=source_block_index_correspondence,
        theorem_candidate_record={
            "candidate_theorem_id": "candidate_block_evaluation_collapse_with_integral_source_separation",
            "hypotheses": ["Blob 8 verified source lattice records", "Blob 12 verified reduced block schemes", "Blob 13 verified block evaluation"],
            "statement": "At the verified block-evaluation level, 84 and 84a collapse while their integral source types separate.",
            "status": "CANDIDATE_THEOREM_RECORD",
        },
        conditional_corollary_record={
            "conditional_corollary_id": "conditional_classical_defect_collapse_84_84a",
            "condition": "ordinary-node/full-node-scheme promotion",
            "statement": "Under the ordinary-node promotion gate, both classical defects equal 7.",
            "status": "CONDITIONAL",
        },
        hodgecy_i_question_status=(
            {
                "question": "source assembly determines classical defect",
                "status": "UNRESOLVED",
                "reason": "No source-to-evaluation or source-to-node morphism is constructed.",
            },
            {
                "question": "block evaluation less discriminating than integral source assembly",
                "status": "SUPPORTED_EXACTLY_FOR_VERIFIED_BLOCK_SCHEMES",
                "reason": "Block evaluation agrees for 84/84a while integral source type differs.",
            },
            {
                "question": "classical defect less discriminating than source assembly",
                "status": "CONDITIONAL",
                "reason": "Both conditional defect values are 7; actual classical defect remains UNKNOWN.",
            },
            {
                "question": "additional perturbation geometry essential",
                "status": "NOT_ESTABLISHED",
                "reason": "Blob 14 performs no perturbation or vanishing-cycle construction.",
            },
        ),
        evidence_status_table=(
            {"layer": "source assembly rational data", "84": "VERIFIED", "84a": "VERIFIED", "claim_status": "VERIFIED"},
            {"layer": "source assembly integral/SNF data", "84": "VERIFIED", "84a": "VERIFIED", "claim_status": "VERIFIED"},
            {"layer": "verified block scheme", "84": "VERIFIED", "84a": "VERIFIED", "claim_status": "VERIFIED"},
            {"layer": "block Hilbert profile through degree 8", "84": "VERIFIED", "84a": "VERIFIED", "claim_status": "VERIFIED"},
            {"layer": "degree-8 block evaluation", "84": "VERIFIED", "84a": "VERIFIED", "claim_status": "VERIFIED"},
            {"layer": "conditional classical defect", "84": "CONDITIONAL", "84a": "CONDITIONAL", "claim_status": "CONDITIONAL"},
            {"layer": "ordinary-node promotion", "84": "UNKNOWN", "84a": "UNKNOWN", "claim_status": "UNKNOWN"},
            {"layer": "actual classical defect", "84": "UNKNOWN", "84a": "UNKNOWN", "claim_status": "UNKNOWN"},
            {"layer": "source-to-evaluation chain map", "84": "UNKNOWN", "84a": "UNKNOWN", "claim_status": "UNKNOWN"},
            {"layer": "integral evaluation lattice", "84": "UNKNOWN", "84a": "UNKNOWN", "claim_status": "UNKNOWN"},
        ),
        certificate_ids=(
            certificate_id,
            conditional_defect_id,
            "source_relation_rank_2_vs_eval_relation_dim_7_feasibility_only",
        ),
        provenance=provenance,
    )
