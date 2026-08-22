# HodgeCY II Source-Fidelity Census

This is a source-level census of committed double-octic assembly data. It does not claim node, defect, LMHS, or genuine Hodge-atom realization.

## Denominators

- CKC source types audited: 455
- Raw CKC source records loaded: 455
- Source-computable census-eligible assemblies: 13
- Census-eligible assemblies inside the numbered CKC index: 12
- Supplemental validated control assemblies: 1 (84a)
- Ineligible raw source records: 443
- Raw extraction parser coverage complete: True
- Full validated CKC dataset loaded: False

## Fidelity Counts

- Clean two-stratum eligible assemblies: 7
- Truncated two-stratum eligible assemblies: 6
- Local inventory fibers: 9
- Rational signatures: 10
- Integral signatures: 11
- Equivariant signatures: 13

## Recovery Witnesses

- Local-to-rational recovery fibers: 1
- Rational-to-integral recovery fibers: 1
- Integral-to-equivariant recovery fibers: 2
- Hodge-refined source assembly recovery fibers: 1

The central local fiber is `84,84a,239,240,241`: arrangement 241 is separated at rational rank, while 84/84a/239/240 require integral refinement. The hodge-linked pair `84,84a` remains the committed witness that identical Hodge and local data can separate at source-level integral assembly.

## Source Tables

- `census/ckc_coverage_audit.tsv` audits all 455 raw CKC source records.
- `census/source_assembly_records.tsv` lists the 13 eligible normalized source assemblies.
- `census/table_local_collapse_rational_recovery.tsv` and `census/table_rational_collapse_integral_recovery.tsv` give the main refinement witnesses.

## Local-to-Rational Witness

- Members: `84,84a,239,240,241`
- Target classes: `2`

## Rational-to-Integral Witness

- Members: `84,84a,239,240`
- Target classes: `2`
