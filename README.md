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

## Gate 2: Smoothing Bridge

The smoothing bridge layer records the expected nodal/conifold construction
\(
F_{\epsilon} = A + \epsilon Q^2,
\)
where \(A\) is the plane-arrangement branch octic and \(Q\) is a generic
quartic. For arrangements with 28 double lines and no triple lines, the naive
expected residual count is 112 nodes under genericity assumptions, with four
expected intersection points on each double line.

At present this is only an expected combinatorial/local-model profile. The
repository records the double-line grouping, expected counts, and genericity
assumptions explicitly, but ordinary-node verification still requires CAS and
local analytic checks.

The repository now also includes exact rational verification scaffolding for
the `84` and `84a` smoothing-bridge candidates. On the Python side, HodgeCY
checks that the chosen quartic \(Q\) avoids every arrangement multiple point
and that the restriction of \(Q\) to each double line is a squarefree quartic,
which is the exact genericity condition behind the expected four nodes per
double line. The heavier projective singular-locus and Hessian-rank checks are
kept conservative: they are never run by default, and they are only promoted
when an explicit optional workflow or external CAS certifies them.

## Gate 3: Defect/Profile Comparison

This layer prepares the comparison between classical defect and HodgeCY atom
block profiles for smoothing-bridge examples. It does not compute classical
defect yet; instead it records candidate smoothing-bridge block profiles,
comparison scaffolds, and a defect-computation queue that makes the missing
steps explicit.

The longer-term test is whether two nodal examples can share the same node
count and classical defect while still exhibiting different atom block
profiles, which would make the block/profile layer a strict refinement of
classical defect. For the current `84/84a` control pair, everything remains
candidate-level until lattice audit, local node verification, and defect
computation are all in place.

## Concurrency-Aware Lattice Profiles

For smoothing-bridge examples built from eight planes, first-order plane-node
incidence is identical at the naive level: each double line contributes four
expected nodes, so the coarsest plane-node counts collapse. If distinguishing
information survives at the arrangement level, it must pass through how double
lines meet at p3, p4, and higher multiple points.

The concurrency-aware profile therefore records line/multiple-point incidence,
multiple-point multiplicity counts, line multiplicity profiles, and p4
collinearity structure. These are arrangement-level inputs to the smoothing
bridge and to any later candidate atom-block interpretation.

For the current paper assets, the repository now emphasizes the p4-collinearity
graphs rather than the full mixed concurrency graph. This keeps the visual
signal focused on the exact place where `84` and `84a` separate:

- `84`: 10 p4 vertices, 39 edges, degree sequence `[6, 8^9]`
- `84a`: 10 p4 vertices, 42 edges, degree sequence `[8^6, 9^4]`

The processed certificate `data/processed/p4_collinearity_certificate.csv`
records the per-vertex degrees and neighbor lists used to generate those
figures.

## Paper Verification Workflow

The paper-strengthening verification workflow is intentionally split into a
fast default path and optional expensive paths.

Default commands:

- `python scripts/generate_paper_assets.py`
- `python scripts/verify_smoothing_bridge_84_84a.py --force`
- `python -m pytest -q`

Optional expensive commands:

- `python scripts/verify_smoothing_bridge_84_84a.py --force --finite-field-checks --max-seconds 600`
- `python scripts/verify_smoothing_bridge_84_84a.py --force --char0-checks --max-seconds 3600`

The default verification driver only does:

- exact rational G1 verification: `Q` avoids all multiple points
- exact rational G2 verification: `Q` is squarefree on every double line
- generation of finite-field / Macaulay2 / Singular handoff artifacts
- writing JSON / CSV outputs
- regeneration of the p4-collinearity figures and certificate

It does not attempt full characteristic-zero Groebner work unless explicitly
asked.

Verification statuses:

- `queued`: no global singular-locus verification has been attempted yet
- `genericity_verified`: exact G1 and G2 succeeded for the explicit `Q`
- `degree112_certified`: exact G1 and G2 succeeded, and a repo-backed
  characteristic-zero degree-112 certificate exists for the singular locus,
  but reducedness, Hessian rank-3, and defect certificates are still missing
- `ordinary_node_verified`: reducedness and Hessian rank-3 certificates exist,
  so the singular locus is certified as 112 ordinary nodes
- `defect_verified`: the ordinary-node certificate is in place and the
  defect/Hilbert-function claims are also repo-backed
- `failed`: the explicit `Q` failed one of the required checks

In the current repository, the paper-facing default is intentionally
conservative: G1 and G2 are verified exactly over `Q` for the explicit quartic,
and the reviewer-V4 package is strong enough to justify `degree112_certified`.
The repository still does not promote to `ordinary_node_verified` or
`defect_verified` unless reducedness, Hessian rank-3, and defect certificates
are actually present in machine-readable form.

For arrangements `84` and `84a`, the current smoothing status is
`degree112_certified`. Exact G1/G2 genericity verification and a
characteristic-zero degree-112 saturated Jacobian certificate are repo-backed.
The repository does not currently promote either arrangement to
`ordinary_node_verified` or `defect_verified`; reducedness, Hessian-rank,
critical-degree, Hilbert-function, and defect certificates remain pending.

## Defect Computation Gate

The next decisive computation for the smoothing-bridge program is the classical
defect of the expected 112-node configurations associated with the `84` and
`84a` smoothing bridges. That computation requires CAS support and depends on
the critical degree in which the node scheme fails to impose independent
conditions.

At present the repository does not fake this degree or the resulting defect.
Instead, it contains raw smoothing-bridge example records, CAS templates, a
high-priority computation queue, and an empty verified-results ingestion file
so that literature verification and subsequent Macaulay2/Singular runs can be
tracked cleanly.

The current queue state for `smoothing_bridge_84` and `smoothing_bridge_84a` is
deliberately conservative: `critical_degree = null`,
`critical_degree_status = needs_literature_verification`, and
`defect_status = not_computed`. This keeps the next mathematical dependency
explicit before any final CAS-backed defect claim is made.

## Paper Tables And Figures

Paper-facing assets are generated by `scripts/generate_paper_assets.py`.
Tables are written under `paper/tables`, figures under `paper/figures`, and
machine-readable companion files under `data/processed/paper_tables` and
`data/processed/paper_figures`.

Some figures depend on optional processed data or optional plotting support,
most notably the p4-collinearity graph figure. When those dependencies are
missing, the asset generator records a clear skip reason rather than failing.
Defect values, singular-locus cardinalities, and operator-route validations are
never fabricated: queued or partial computations remain explicitly marked
`not_computed`, `queued`, or `partial` until verified results are ingested.

## Equivariant HodgeCY Spectra

The equivariant spectrum layer is experimental and additive. It computes
incidence-preserving automorphism groups, stratified gluing complexes, orbit
decompositions, and permutation characters for selected double-octic
arrangements.

This layer is motivated by the Cynk--Kocel--Cynk automorphism classification
for double octic arrangements. It is designed to sit beside the existing
HodgeCY smoothing and atom-profile code rather than replace it.

The current control-triple computation covers arrangements `83`, `84`, and
`84a`. The `84` and `84a` records use the existing HodgeCY representatives.
The `83` record is a rational specialization of a parameterized
Cynk--Kocel--Cynk equation and should be treated as provisional until the
parameter choice is reviewed.

An explicit search helper,
`scripts/search_arrangement_83_representative.py`, searches normalized
integer parameter choices for the arrangement-83 parameterized equation. In the
current run, no valid representative was found for the normalized range
induced by raw tuples `A0,A1,A2,A3 in {-5,...,5} \ {0}`, up to common scaling
with `A0=1`. The current 83 specialization remains `provisional`, with
expected and computed inventories recorded separately in the generated
equivariant-spectrum JSON and a search report written to
`data/processed/equivariant_spectra/arrangement_83_search_report.json`.

This new layer does not change the v0.1.0 smoothing verification claims. It
does not promote `ordinary_node_verified` or `defect_verified`; arrangements
`84` and `84a` remain `degree112_certified`.

Commands:

- `python scripts/search_arrangement_83_representative.py`
- `python scripts/compute_equivariant_spectrum_control_triple.py`
- `python -m pytest -q tests/test_equivariant_incidence.py tests/test_equivariant_gluing_complex.py tests/test_equivariant_spectrum_control_triple.py`

### Fixed-equation equivariant clustering

The fixed-equation clustering pass computes equivariant incidence-gluing
spectra only for currently ingested CKC records that are validated,
non-parameterized, and fixed. In the current repository this includes `84` and
`84a`; the provisional parameterized `83` representative is explicitly skipped
and recorded in the coverage metadata.

The generated cluster tables identify examples with identical local
singularity inventory and Hodge numbers but different equivariant
incidence-gluing data. The first current witness is `84/84a`: they share the
same local inventory and Hodge numbers, but differ in automorphism group order,
rank over `F2`, Smith normal form, orbit decompositions, and permutation
characters.

Machine-readable outputs are written under
`data/processed/equivariant_spectra/`, including
`fixed_equation_equivariant_spectrum_summary.csv`,
`fixed_equation_equivariant_clusters.json`, and
`fixed_equation_equivariant_differentiating_pairs.csv`. Paper-facing tables are
written to `paper/tables/table_fixed_equation_equivariant_clusters.*` and
`paper/tables/table_fixed_equation_equivariant_differentiating_pairs.*`.

Command:

- `python scripts/cluster_equivariant_spectra_fixed_equations.py`
