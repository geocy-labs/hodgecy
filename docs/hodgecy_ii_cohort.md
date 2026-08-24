# HodgeCY II Cohort Baseline

the source-cohort layer connects the generic result registry and comparison engine to the
current HodgeCY II research cohort. It ingests existing source/coarse data only;
it does not compute new singular schemes, node relations, defects, vanishing
cycles, or Hodge atoms.

## Cohort

The manifest lives at:

```text
data/cohorts/hodgecy_ii.json
```

Current members:

```text
84
84a
239
240
241
```

Arrangement `83` appears in current control-triple data, but the repository
marks that representative as provisional and the fixed-equation batch excludes
it. the source-cohort layer therefore records it as an excluded explicit record, not as a current
cohort member.

## Comparison Sets

The manifest defines three sets:

- `hodgecy-ii-84-pair`: primary `84 / 84a` development pair.
- `hodgecy-ii-239-241`: fixed-local-inventory structural family.
- `hodgecy-ii-source-cohort`: five-member source-level cohort.

The five-member source cohort is a cross-example source-level comparison set.
It does not assert a common conifold realization.

## Source Data Ingested

Ingest reads the release theorem summaries under:

```text
release/hodgecy-v0.2.0/arrangements/<id>/theorem_summary.json
```

The source/local inventory convention is preserved as:

```text
(p3, p4_0, p4_1, p5_0, p5_1, p5_2, l3)
```

the source-cohort layer persists available source-level fields such as:

```text
local_inventory
matrix_shape
rank_Q
rank_mod_2
rank_mod_3
kernel_dim_Q
cokernel_dim_Q
integral_kernel_rank
integral_cokernel_decomposition
smith_normal_form
automorphism_group_order
plane_orbit_sizes
double_line_orbit_sizes
multiple_point_orbit_sizes
character_C1_distribution
character_C0_distribution
```

Known coarse Hodge data are persisted as `ResultKind.HODGE_DATA`; missing Hodge
data remain `EvidenceStatus.UNKNOWN`.

## Provenance

Imported release-summary data use `EvidenceStatus.IMPORTED`, not `VERIFIED`.
The release file path is stored in the invariant provenance. UNKNOWN later-stage
records are explicitly persisted with their own mathematical result kind.

## Mathematical Firewall

Local inventory is source/local-inventory data, not a conifold or smooth
Hodge-atom spectrum.

Source ranks, kernels, Smith normal forms, and cokernel decompositions are
source-level data. They are not node-relation matrices, vanishing-cycle
relations, or geometric defects.

the source-cohort layer records these later-stage quantities as unknown where useful:

```text
node_relation_rank
classical_defect
conifold_atom_spectrum
```

These UNKNOWN records preserve the mathematical level without inventing
calculations.

## Rerun

Library use:

```python
from hodgecy.cohorts import baseline_hodgecy_ii_comparison
from hodgecy.storage import ResultStore

store = ResultStore("results/hodgecy-results.sqlite")
store.initialize()

baseline = baseline_hodgecy_ii_comparison(
    store,
    report_dir="results/reports/hodgecy_ii",
)
```

Ingestion is idempotent for geometry identities and comparison sets. Each
rerun creates a new immutable import run for reproducibility; the comparison
engine's default policy selects the latest completed non-superseded run.

## Reports

When `report_dir` is supplied, the source-cohort layer writes:

```text
hodgecy_ii_84_pair_baseline.json
hodgecy_ii_239_241_baseline.json
hodgecy_ii_source_cohort_baseline.json
hodgecy_ii_84_pair_baseline.md
hodgecy_ii_239_241_baseline.md
hodgecy_ii_source_cohort_baseline.md
```

Machine-readable JSON reports are normalized to remove volatile comparison
timestamps.

## Remaining UNKNOWN

Pending later blobs:

```text
singular schemes
reducedness
pointwise ODP certification
node ideals
critical-degree evaluation
classical defect
node-relation complexes
source-to-node comparison
vanishing-cycle maps
Picard-Lefschetz monodromy
conifold Hodge atoms
smooth Hodge atoms
```

the source-cohort layer is therefore a source/coarse baseline, not a geometry or Hodge-atom
completion pass.
