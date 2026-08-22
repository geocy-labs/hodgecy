# HodgeCY II Theorem Candidates

## THEOREM-READY

None in this branch checkpoint.

## COMPUTATIONAL OBSERVATION

- The frozen source data for 84 and 84a agree at F0, F1, and F2, and separate
  at source-level F3 by Smith normal form.
- The formal beta_A block expansion has shape 112 x 28, rank 28 over Q, four
  formal nodes per source double-line block, and each formal node lies in one
  block.

## CANDIDATE

- Gate A ordinary-node verification for 84 and 84a. Existing raw computation
  logs claim completion, but committed release/processed manifests still require
  exact certificate ingestion before promotion.
- Defect equality delta(84) = delta(84a) = 7. Existing raw logs claim this, but
  the processed verified-defect table is empty in this checkpoint.

## NEGATIVE RESULT

None yet.

## UNRESOLVED

- Correct node relation object for the 112-node degeneration.
- Source-to-node chain/comparison map.
- Genuine rational/integral/equivariant Hodge atom comparison.
- LMHS / extension fidelity.

## SOURCE-FIDELITY CENSUS CHECKPOINT

- Source-level CKC audit complete for 455 raw source records, with 13 committed source-recomputed assemblies classified.
- The census is a computational observation only: it is not a node, defect, LMHS, or Hodge-atom realization result.
- Current source-level recovery witnesses include the local fiber `84,84a,239,240,241` and the Hodge-refined integral split `84,84a`.
