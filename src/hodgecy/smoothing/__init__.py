"""Smoothing-bridge scaffolding for double octic arrangements."""

from .bridge import (
    ExpectedNodeStratum,
    QuarticPerturbation,
    SmoothingBridgeProfile,
    double_line_candidates,
    grouped_double_lines,
    line_key_from_pair,
    smoothing_bridge_profile,
)
from .verification import (
    ALLOWED_VERIFICATION_STATUSES,
    LineGenericityCheck,
    MultiplePointCheck,
    FiniteFieldCheck,
    SmoothingVerificationRecord,
    build_smoothing_verification,
    build_summary_frame,
    candidate_quartic,
    candidate_quartic_str,
    record_to_dict,
    run_verification_workflow,
    singular_locus_generators,
    smoothing_polynomial,
    write_default_verification_outputs,
)
from .reviewer_v4_audit import build_reviewer_v4_audit, write_reviewer_v4_audit

__all__ = [
    "ALLOWED_VERIFICATION_STATUSES",
    "ExpectedNodeStratum",
    "FiniteFieldCheck",
    "LineGenericityCheck",
    "MultiplePointCheck",
    "QuarticPerturbation",
    "SmoothingVerificationRecord",
    "build_smoothing_verification",
    "build_summary_frame",
    "candidate_quartic",
    "candidate_quartic_str",
    "SmoothingBridgeProfile",
    "double_line_candidates",
    "grouped_double_lines",
    "line_key_from_pair",
    "record_to_dict",
    "run_verification_workflow",
    "singular_locus_generators",
    "smoothing_bridge_profile",
    "smoothing_polynomial",
    "write_default_verification_outputs",
    "build_reviewer_v4_audit",
    "write_reviewer_v4_audit",
]
