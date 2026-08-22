# HodgeCY v1.0.0 Reproducibility

HodgeCY has several reproducibility layers. A fresh clone contains the package, tests, fixtures, public metadata summaries, and HodgeCY I release assets; it does not contain the 574,616,978-record production corpus.

The HodgeCY v1.0.0 release archive is available at https://doi.org/10.5281/zenodo.22062175.

## CI-Safe Repository Tests

Run the ordinary repository test suite with:

```bash
python -m pytest -q
```

These tests cover imports, core data models, parser/adapter infrastructure, query/catalog behavior, relationship infrastructure, certificate utilities, exact algebra support, fixtures, and the historical HodgeCY I regression layer.

## HodgeCY I Workflows

The HodgeCY I / v0.2.0 theorem-bearing compatibility path remains available:

```bash
python scripts/validate_ckc_fixed_rational_batch.py
python scripts/build_ckc_239_240_241_theorem_values.py
python scripts/build_v0_2_0_release.py
python scripts/verify_v0_2_0_release.py
```

The shell wrapper `scripts/reproduce_release.sh` runs the same historical release path. The selected HodgeCY I examples include arrangements 84, 84a, 239, 240, and 241. The 84/84a smoothing status remains `degree112_certified`; ordinary-node and defect verification are intentionally not promoted by v1.0.0.

## External Large-Corpus Workflows

The comprehensive corpus is stored outside Git under a user-provided data root. Configure it with `HODGECY_DATA_ROOT` or pass a root explicitly to the catalog/bootstrap tools.

```bash
export HODGECY_DATA_ROOT=/path/to/hodgecy-data
```

Large-data workflows may use:

```bash
python scripts/check_data_catalog.py --root "$HODGECY_DATA_ROOT"
python scripts/bootstrap_current_corpus.py --root "$HODGECY_DATA_ROOT"
python scripts/close_current_corpus.py --root "$HODGECY_DATA_ROOT"
```

Do not infer from the public Git repository that production Kreuzer--Skarke, DESY GV, ToricCY, APS `.mx`, DuckDB, or Parquet payloads are committed here.

## Optional Runtime-Dependent Operations

Some workflows require optional software or large external payloads:

- `duckdb` and `pyarrow` for storage/query tests and Parquet-backed catalog work;
- Wolfram-compatible tooling for normalized export from genuine APS gCICY `.mx` sources;
- CAS tooling such as Singular or Macaulay2 for selected verification scripts;
- local external data archives for full production corpus checks.

## Data Boundary

The repository stores software, schemas, fixtures, release metadata, and small public corpus documentation. External third-party datasets retain their original licenses and terms, and the HodgeCY MIT software license does not relicense source corpora.
