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
    LineGenericityCheck,
    MultiplePointCheck,
    SmoothingVerificationRecord,
    build_smoothing_verification,
    build_summary_frame,
    candidate_quartic,
    record_to_dict,
    singular_locus_generators,
    smoothing_polynomial,
    write_default_verification_outputs,
)

__all__ = [
    "ExpectedNodeStratum",
    "LineGenericityCheck",
    "MultiplePointCheck",
    "QuarticPerturbation",
    "SmoothingVerificationRecord",
    "build_smoothing_verification",
    "build_summary_frame",
    "candidate_quartic",
    "SmoothingBridgeProfile",
    "double_line_candidates",
    "grouped_double_lines",
    "line_key_from_pair",
    "record_to_dict",
    "singular_locus_generators",
    "smoothing_bridge_profile",
    "smoothing_polynomial",
    "write_default_verification_outputs",
]
