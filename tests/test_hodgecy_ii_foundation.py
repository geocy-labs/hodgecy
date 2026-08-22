from __future__ import annotations

import sympy as sp

from hodgecy.research import (
    EvidenceStatus,
    FidelityDepth,
    FidelityLayer,
    FidelityLevel,
    RealizationStatus,
    beta_block_expansion_matrix,
    first_separating_level,
    source_survival_profile,
)


def test_beta_block_expansion_matrix_has_28_by_4_partition() -> None:
    matrix = beta_block_expansion_matrix(28, nodes_per_block=4)

    assert matrix.shape == (112, 28)
    assert matrix.rank() == 28
    assert [sum(matrix[row, col] for row in range(matrix.rows)) for col in range(matrix.cols)] == [4] * 28
    assert all(sum(matrix[row, col] for col in range(matrix.cols)) == 1 for row in range(matrix.rows))


def test_first_separating_level_for_source_84_84a_seed_is_integral() -> None:
    layers = [
        FidelityLayer(
            FidelityLevel.F0_HODGE_NUMBERS,
            (0, 40, 80),
            (0, 40, 80),
            EvidenceStatus.COMPUTATIONALLY_VERIFIED,
            RealizationStatus.SOURCE_ONLY,
        ),
        FidelityLayer(
            FidelityLevel.F1_LOCAL_ATOMS,
            (16, 10, 0, 0, 0, 0, 0),
            (16, 10, 0, 0, 0, 0, 0),
            EvidenceStatus.COMPUTATIONALLY_VERIFIED,
            RealizationStatus.SOURCE_ONLY,
        ),
        FidelityLayer(
            FidelityLevel.F2_RATIONAL_RELATIONS,
            26,
            26,
            EvidenceStatus.COMPUTATIONALLY_VERIFIED,
            RealizationStatus.SOURCE_ONLY,
        ),
        FidelityLayer(
            FidelityLevel.F3_INTEGRAL_RELATIONS,
            (1,) * 23 + (2, 6, 12),
            (1,) * 21 + (2, 4, 4, 4, 12),
            EvidenceStatus.COMPUTATIONALLY_VERIFIED,
            RealizationStatus.SOURCE_ONLY,
        ),
    ]

    assert first_separating_level(layers) is FidelityDepth.F3_INTEGRAL_RELATIONS


def test_source_survival_profile_without_comparison_stays_source_only() -> None:
    profile = source_survival_profile(
        "84",
        source_relation_rank=26,
        source_smith_normal_form=(1,) * 23 + (2, 6, 12),
    )

    assert profile.evidence_status is EvidenceStatus.UNRESOLVED
    assert profile.realization_status is RealizationStatus.SOURCE_ONLY
    assert profile.comparison_rank is None
    assert profile.terminology_guard == "source_survival_profile_is_not_hodge_atom_spectrum"


def test_source_survival_profile_with_matrix_is_only_candidate_node_realized() -> None:
    profile = source_survival_profile(
        "formal",
        source_relation_rank=2,
        source_smith_normal_form=(1, 2),
        comparison_matrix=sp.eye(2),
    )

    assert profile.evidence_status is EvidenceStatus.CANDIDATE
    assert profile.realization_status is RealizationStatus.NODE_REALIZED
    assert profile.comparison_rank == 2
