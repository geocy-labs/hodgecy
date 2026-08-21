from __future__ import annotations

from hodgecy.core.errors import ValidationError
from hodgecy.core.relationships import EvidenceType


def forbid_geometry_identity_from_hodge_numbers() -> None:
    raise ValidationError("Matching Hodge numbers are not evidence of same abstract geometry.")


def forbid_mirror_from_hodge_swap() -> None:
    raise ValidationError("Exchanged Hodge numbers are not evidence of a mirror relationship.")


def forbid_free_action_certification_from_source(evidence_type: EvidenceType) -> None:
    if evidence_type is EvidenceType.SOURCE_EXPLICIT:
        raise ValidationError("A source-reported free action is not computationally certified freeness.")


def forbid_geometry_identity_from_weight_crosswalk() -> None:
    raise ValidationError("An exact weight-vector crosswalk is a source/presentation relation, not certified same geometry.")
