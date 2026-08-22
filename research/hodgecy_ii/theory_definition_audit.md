# HodgeCY II Theory Definition Audit

Status: initial research audit.

This file records the definitions that must be respected before any HodgeCY II
object is called a genuine Hodge atom spectrum. Source assembly records are not
identified with Hodge atom data.

## Sources read

- HodgeCY: Computational Hodge Atom Profiles and Source Assembly Spectra for Double-Octic Calabi-Yau Threefolds, Preprints.org manuscript 202607.0967, especially the open comparison problems named in the HodgeCY II brief: <https://www.preprints.org/manuscript/202607.0967>.
- Hodge Atoms at Conifold Degenerations: F-Bundles, Limiting Mixed Hodge Modules, and the Rigid-Flexible Decomposition, arXiv:2604.17754: <https://arxiv.org/abs/2604.17754>.
- Cycle Relations and Global Gluing in Multi-Node Conifold Degenerations, arXiv:2604.16055: <https://arxiv.org/abs/2604.16055>.

## Definition ledger

| Theoretical object | Source citation | Coefficients | Shifts / twists | Monodromy / signs | Integral status | Required computational representation |
|---|---|---:|---|---|---|---|
| Source assembly complex | HodgeCY I, Sections 5, 7, 10 | Z and Q for matrix/SNF/rank data | None currently encoded | Incidence signs must not be adjusted silently | Integral source lattice is implemented | Exact incidence matrix, rank_Q, rank_Fp, SNF, automorphism action |
| Formal 28 x 4 node block expansion beta_A | HodgeCY II Gate B specification | Z | None | Blocks inherit source double-line labels only | Integral formal map | 112 x 28 exact 0/1 matrix; not a Hodge map |
| Free node lattice Z<Sigma_A> | HodgeCY II Gates B-C; conifold-node literature | Z, Q after tensoring | Depends on vanishing-cycle convention | Orientation/sign data unresolved | Integral lattice exists formally; Hodge meaning unresolved | Node basis, block labels, comparison target once node scheme is verified |
| Vanishing-cycle relation lattice | Cycle Relations and Global Gluing, arXiv:2604.16055 | Q in published perverse/MHM framework; integral refinements require separate justification | Picard-Lefschetz and MHM conventions | Relation signs depend on oriented vanishing-cycle basis | Not automatically integral | Exact relation matrix with cited construction from geometry |
| Classical defect | Double-octic nodal defect theory; local repo docs and computation logs | Usually over base field for Hilbert function | Critical degree must be cited; for octic double solids the existing log records k_crit = 8 | No monodromy sign issue | Scalar invariant, not a Hodge atom | Node ideal, Hilbert function at k_crit, rank/cokernel certificate |
| Corrected mixed Hodge module P^H | Hodge Atoms at Conifold Degenerations, arXiv:2604.17754 | Q-Hodge modules | Flexible node term uses Tate twist (-1) in the source paper summary | var/can and Stokes-extension conventions must be fixed from paper | Integral structure requires Iritani/integral-structure choices | Nearby/vanishing cycles, var/can maps, extension class |
| Rigid atom A(IC^H_X0) | arXiv:2604.17754 | Hodge/MHM side, rational by default | IC convention and shifts must be audited in detail | Monodromy action inherited from degeneration | Integral refinement unresolved | Rigid sector record with exact citation and conventions |
| Flexible node atom A(i_{k*} Q^H_{p_k}(-1)) | arXiv:2604.17754 | Q by default | Tate twist (-1) explicitly appears in source summary | One local sector per verified ordinary node | Integral refinement unresolved | One node-supported rank-one record per verified node |
| Total degeneration atom A(P^H) | arXiv:2604.17754 | Q by default | Exact sequence of atoms; extension may be non-split | Non-split mixing controlled by intersection data | Integral refinement unresolved | Rigid-flexible exact sequence plus extension/mixing matrix |
| Equivariant Hodge atom action | Equivariant extension theory remains to be audited; Preprints 202608.1433 is a candidate source, not yet absorbed here | TBD | TBD | Need G_A^proj and G_A^geom, not just incidence group G_A | TBD | Geometrically realized group action on node/Hodge objects |

## Convention uncertainties

- The exact sign convention for can/var and the relation between Picard-Lefschetz
  orientations and source incidence signs is unresolved.
- The coefficient ring for any integral Hodge-atom refinement is unresolved.
  Source SNF is integral, but this does not by itself create integral Hodge
  atom data.
- The Tate twist and shift conventions for the flexible node sector must be
  checked directly against the full arXiv:2604.17754 text before implementation.
- The current repository can build formal beta_A block matrices, but the actual
  node relation object is not yet identified.
- The older raw computation log claims ordinary-node and defect completion.
  The released theorem summaries and processed verification manifests still
  mark ordinary-node and defect verification as false/pending, so HodgeCY II
  starts from the conservative released state until exact certificates are
  ingested.

## Terminology rule

The following labels are reserved for distinct records:

- `source assembly spectrum`
- `formal node block expansion`
- `verified node relation spectrum`
- `classical defect`
- `Hodge atom spectrum`
- `LMHS / extension data`

No source-level or formal-node record may be promoted to `Hodge atom spectrum`
without a cited MHM/F-bundle realization and exact comparison data.
