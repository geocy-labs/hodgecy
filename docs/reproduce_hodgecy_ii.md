# Reproduce HodgeCY II

HodgeCY II is reproduced from frozen v1.0.0 repository assets.  The workflow
does not rerun the historical 456-record mining pass and does not promote open
ordinary-node, classical-defect, source-to-evaluation, vanishing-cycle, or LMHS
claims.

## Environment

- Python `>=3.10`
- Package dependencies from `pyproject.toml`: `pandas`, `sympy`
- Development test dependency: `pytest`
- Canonical branch after cleanup: `main`
- Package version: `1.0.0`

## Required Inputs

- `research_outputs/hodgecy_ii/complete_fidelity_pairs_and_sets.tsv`
- `research_outputs/hodgecy_ii/final/theorem_evidence/source_lattice/source_lattice_comparison_84_84a.json`
- `research_outputs/hodgecy_ii/final/theorem_evidence/block_geometry/block_geometry_certification_84_84a.json`
- `research_outputs/hodgecy_ii/final/theorem_evidence/block_evaluation/block_evaluation_comparison_84_84a.json`
- `research_outputs/hodgecy_ii/final/theorem_evidence/source_block_comparison/source_block_evaluation_comparison_84_84a.json`

## Command

```bash
python scripts/reproduce_hodgecy_ii.py
```

This validates required inputs, regenerates the final HodgeCY II freeze assets,
runs the fresh-store reproduction check for manuscript census assets, verifies
headline counts, and fails on unsupported promotion.

## Expected Outputs

- processed records: `456`
- nontrivial fidelity sets: `114`
- pairs/triples/larger: `57 / 13 / 44`
- source result: rational equality and integral/SNF separation for `84 / 84a`
- block result: Hilbert/evaluation collapse through degree `8`
- block-evaluation deficiency: `7` for both
- actual classical defect: `UNKNOWN`
- source-to-evaluation morphism: `UNKNOWN`

## Generated Assets

The final synthesis lives under `research_outputs/hodgecy_ii/final/`.
Manuscript-facing tables, figures, and inventories live under
`research_outputs/hodgecy_ii/manuscript_assets/`.

The ignored local SQLite result store is not required.  The fresh-store check
builds the census manuscript assets in a temporary output root and compares the
canonical table content.

## Tests

Run:

```bash
pytest -q tests/test_hodgecy_ii_final_freeze.py
pytest -q
```

Known limitations are recorded as open problems, not test failures.
