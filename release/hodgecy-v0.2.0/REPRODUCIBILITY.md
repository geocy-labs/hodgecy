# HodgeCY v0.2.0 Reproducibility

## Commands

```bash
python scripts/validate_ckc_fixed_rational_batch.py
python scripts/build_ckc_239_240_241_theorem_values.py
python scripts/build_v0_2_0_release.py
python scripts/verify_v0_2_0_release.py
python -m pytest -q
```

The shell wrapper `scripts/reproduce_release.sh` runs the same release path.

## Matrix support format

Each `column_supports.json` lists the row indices and point labels where a given double-line column has entry 1. The verifier reconstructs the full 26 x 28 integral matrix from these supports and compares it entrywise with `matrix.json` and `matrix.csv`.

## Validation statuses

The 84/84a smoothing status is `degree112_certified`; ordinary-node and defect verification are intentionally not promoted in this release.
