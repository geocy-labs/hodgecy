# HodgeCY II Capability Audit

Status: initial branch audit on `research/hodgecy-ii-fidelity`.

## Capability classification

| Need | Current repo support | Classification | Notes |
|---|---|---|---|
| 84 / 84a arrangement representatives | `src/hodgecy/arrangements`, release `source.json` files | ALREADY_IMPLEMENTED | Ordered plane factors are frozen in v0.2 release artifacts. |
| Exact incidence and singular strata | `src/hodgecy/equivariant/incidence_tables.py`, release `matrix.json` | ALREADY_IMPLEMENTED | Matrix row/column generators provide 26 x 28 source complex. |
| Source assembly ranks | `src/hodgecy/assemblies`, `src/hodgecy/equivariant/gluing_complex.py` | ALREADY_IMPLEMENTED | Exact rank_Q/rank_Fp and kernel/cokernel records exist. |
| Smith normal form | `src/hodgecy/algebra/results.py`, source summaries | ALREADY_IMPLEMENTED | Values match expected 84 and 84a SNFs. |
| Automorphism group and orbit data | `src/hodgecy/equivariant/automorphisms.py`, release `orbit_data.json` | ALREADY_IMPLEMENTED | This is the incidence-preserving source group, not necessarily geometric/Hodge action. |
| Equivariant source signatures | `src/hodgecy/equivariant/spectrum.py`, fixed batch outputs | ALREADY_IMPLEMENTED | Source-level only. |
| Quartic Q0 and epsilon | `src/hodgecy/smoothing/verification.py`, processed verification JSON | ALREADY_IMPLEMENTED | Q0 and epsilon are exact and frozen. |
| Genericity G1/G2 | `src/hodgecy/smoothing/verification.py` | ALREADY_IMPLEMENTED | Q avoids multiple points and restricts squarefree on double lines. |
| Degree-112 singular scheme evidence | processed `smoothing_verification_*.json`, Singular/M2 scripts, raw computation log | IMPLEMENTATION_INCOMPLETE | Processed manifests record `degree112_certified` but leave length/reducedness/Hessian fields null. |
| Ordinary-node promotion | raw log claims complete; release summaries say false | CAS_REQUIRED | Exact certificate ingestion needed before promotion. |
| Frozen radical node ideal | not present as a small stable artifact | CAS_REQUIRED | Gate A needs ideal files/checksums. |
| 28 x 4 block expansion beta_A | added in `hodgecy.research.hodgecy_ii` | ALREADY_IMPLEMENTED | Formal exact 112 x 28 block matrix only. |
| Actual node relation object | no implementation | THEORY_REQUIRED | Must distinguish free node lattice, vanishing-cycle relations, exceptional-curve relations, evaluation data, and defect. |
| Defect critical degree | local raw log says degree 8; docs queue exists | IMPLEMENTATION_INCOMPLETE | Need cite-backed source and exact certificate ingestion. |
| Defect computation | raw log claims delta = 7 for both; processed CSV empty | CAS_REQUIRED | Must freeze Hilbert/evaluation certificate before marking verified. |
| Source-to-node comparison chain map | no implementation | THEORY_REQUIRED | beta_A alone is not the comparison map demanded by Problem 7.10. |
| Genuine Hodge atom spectrum | no implementation | THEORY_REQUIRED | Requires MHM/F-bundle definitions and exact geometric data. |
| LMHS/extension data | no implementation | THEORY_REQUIRED | Needs can/var, N, weight filtration, extension classes. |
| Systematic source assembly scan | partial fixed-equation batch outputs exist | NEW_CODE_REQUIRED | Need complete safe corpus scan with clean/truncated two-stratum policy. |
| Theorem-candidate reporting | not present before this branch | NEW_CODE_REQUIRED | Initial manifest/table scaffold generated under `research_outputs/hodgecy_ii`. |

## Existing scripts inspected

- `scripts/audit_lattices_84_84a.py`
- `scripts/smoothing_bridge_84_84a.py`
- `scripts/verify_smoothing_bridge_84_84a.py`
- `scripts/compare_smoothing_bridge_84_84a.py`
- `scripts/build_smoothing_bridge_atom_profiles.py`
- `scripts/build_defect_queue.py`
- `scripts/compute_equivariant_spectrum_control_triple.py`
- `scripts/compute_fixed_equation_batch_001.py`
- `scripts/build_ckc_239_240_241_theorem_values.py`

## Immediate blockers

- Gate A certificate ingestion is the first mathematical blocker: the repository
  has scripts/log evidence, but the current committed verification records still
  do not expose the radical support, Hessian rank, node ideal, or per-node block
  decomposition as exact small certificates.
- Gate C is conceptual: the correct node relation object must be defined before
  any source-to-node commutativity test is meaningful.
- Gate F cannot start until the theory definition audit is refined into exact
  computational conventions.
