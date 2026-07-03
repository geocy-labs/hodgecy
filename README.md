# HodgeCY

HodgeCY is the computational research repository for Hodge-theoretic and
related arithmetic experiments under the GeoCY organization.

The first target in this repository is the Cynk--Meyer double octic dataset
from arXiv:`math/0304121`.

## Repository Layout

- `src/hodgecy/`: Python package source
- `data/raw/`: raw source data files and hand-entered transcription stubs
- `data/processed/`: processed research-ready tables
- `notebooks/`: exploratory notebooks
- `scripts/`: utility scripts for dataset preparation and checks
- `m2/`: Macaulay2 experiments
- `tests/`: package and data integrity tests
- `paper/tables/`: paper-facing table outputs
- `paper/figures/`: paper-facing figure outputs

## Current Status

This first scaffold provides:

- a `src`-layout Python package named `hodgecy`
- loader stubs for the Cynk--Meyer dataset
- placeholder raw CSV/JSON source files
- basic tests for imports, file existence, and loader return types

No heavy algebraic geometry functionality is included yet.
