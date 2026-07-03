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

## Nodal Defect And Operator-Route Layer

The repository now includes schema-level support for classical node-scheme
defect computations. Actual Hilbert-function calculations still require
external CAS tools such as Macaulay2 or Singular, and the bundled templates are
deliberately scaffolds rather than claimed computations.

Within the current atom-profile layer, classical defect is treated as a coarse
numerical shadow of flexible-sector compression. This is only a first schema:
relation/block refinements and operator-side comparison data are left as
explicit placeholders until geometric computations are supplied.

The operator-route schemas are also now present for later storage of
Picard--Fuchs, conifold-point, and monodromy/nilpotent-profile data. No
mathematical results are faked by these placeholder modules; unsupported values
remain marked as `not_computed`, `not_loaded`, or `unknown`.

## Gate 1: Lattice Audit For 84 And 84a

The pair `84/84a` is currently treated as a motivational/control pair in the
double octic program. They share Cynk--Meyer Table 1 counts and Hodge numbers,
but differ at the equation and modular-form level, so they are a natural first
test for whether arrangement-incidence structure already separates examples that
coarse numerical data collapse.

This Gate 1 layer computes arrangement-level incidence information from the
explicit eight-plane data and checks whether the incidence lattices of `84` and
`84a` are isomorphic. It is not yet a conifold Hodge atom computation, because
these arrangements are not being modeled here as finite-node conifold
degenerations. The outcome instead tells us whether `84/84a` can function as a
relation-layer witness or only as an arithmetic/Hodge-control pair.

The current Gate 1 audit result is already nontrivial: `84` and `84a` have the
same coarse subset-rank fingerprint, but the brute-force incidence-isomorphism
search over all `8!` plane permutations finds no subset-rank-preserving
isomorphism. In the present repository, that means the pair is not separated by
the coarsest fingerprint summary, yet it is separated by the full
arrangement-incidence test currently implemented.
