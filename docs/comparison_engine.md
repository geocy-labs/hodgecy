# Generic Comparison Engine

Blob 3 adds a geometry-agnostic comparison layer for persisted HodgeCY results.
It compares records that already exist in a `ResultStore`; it does not compute
new invariants.

The motivation is research reproducibility. HodgeCY frequently has geometries
that agree under coarse invariants and separate only after progressively finer
records are introduced. The comparison engine makes that hierarchy explicit.

## States

The engine uses Blob 1 `ComparisonState`:

- `equal`: operands are comparable and equal under the declared comparison
  rule.
- `different`: operands are comparable and differ.
- `unknown`: the comparison cannot be decided because required values are
  missing, unknown, conjectural, or insufficient under the active policy.
- `incomparable`: operands belong to incompatible mathematical kinds.

Evidence status is preserved. For example, `8 VERIFIED` compared with
`8 COMPUTED` can be value-equal while still reporting distinct operand
statuses.

## Run Selection

Historical runs are never overwritten. The default run policy is:

```text
latest completed non-superseded run
```

for the requested geometry, calculation type, result kind, and invariant name.

Explicit historical comparison is available by supplying `run_ids`. Strict
current-run auditing is available through:

```python
ComparisonPolicy(run_selection=RunSelectionPolicy.ALL_CURRENT_STRICT)
```

If multiple current completed runs provide conflicting values under the strict
policy, the engine raises `AmbiguousResultError` rather than choosing an
arbitrary record.

## Pair Comparison

```python
from hodgecy.comparison import ComparisonEngine

engine = ComparisonEngine(store)
report = engine.compare_pair(
    "synthetic-A",
    "synthetic-B",
    invariants=["h11", "h21", "source_rank"],
)
```

The report contains one `ComparisonResult` per invariant and a deterministic
machine-readable `to_dict()` representation. `to_markdown()` provides a compact
human-readable table.

## Set Comparison

Comparison sets are loaded from Blob 2 `ComparisonSetRecord` objects:

```python
results = engine.compare_set(
    comparison_set_id,
    invariants=["source_rank"],
)
```

For a value pattern such as:

```text
X1 = 8
X2 = 8
X3 = 9
X4 = UNKNOWN
```

the set result preserves:

```text
equivalence_groups:
    8 -> X1, X2
    9 -> X3
unknown_members:
    X4
```

Unknown members are not treated as an ordinary equality class unless a future
caller explicitly changes policy.

## Equivalence Classes and Refinement

`group_by_invariants()` partitions geometries by canonical invariant tuples.
Unknown values are placed in an unresolved bucket.

```python
classes = engine.group_by_invariants(
    ["A", "B", "C", "D"],
    ["h11", "h21"],
)
```

`classify()` progressively refines classes by ordered levels:

```python
classification = engine.classify(
    ["A", "B", "C", "D"],
    levels=[
        ["h11", "h21"],
        ["source_rank"],
        ["source_snf"],
    ],
)
```

This records how coarse classes split as finer persisted invariants are added.

## First Distinguishing Invariant

```python
first = engine.first_difference(
    ["A", "B"],
    ["h11", "h21", "source_rank", "source_snf"],
)
```

The first `different` level is returned. Unknown levels are not skipped
silently; they produce an `unknown` result unless policy changes in a later
extension.

## Spectrum Comparison

Same-kind spectra can be compared directly:

```text
SourceAssemblySpectrum  vs SourceAssemblySpectrum
ConifoldAtomSpectrum    vs ConifoldAtomSpectrum
SmoothHodgeAtomSpectrum vs SmoothHodgeAtomSpectrum
```

Cross-kind spectra return `incomparable`:

```text
SourceAssemblySpectrum vs ConifoldAtomSpectrum
SourceAssemblySpectrum vs SmoothHodgeAtomSpectrum
```

Spectrum comparison first checks content hashes. If hashes differ, it compares
the canonical mathematical payload and reports field differences where
practical. Geometry-specific record metadata is not treated as a mathematical
spectrum difference.

## Canonical Values

Values are normalized through the same deterministic canonical JSON convention
used by the result store. Dictionary key order does not affect equality, and
tuples/lists are compared through their JSON-compatible representation.

## Mathematical Firewall

Numerical coincidence is not a certified comparison morphism.

For example:

```text
source_rank = 8
node_relation_rank = 8
```

does not imply that source assembly data and node-relation data agree as
mathematical objects. They remain different result kinds. Persistence and
comparison both preserve that boundary.

Blob 3 does not ingest cohorts, compute singularities, certify ODPs, compute
node ideals, perform Smith normal form, build source-to-node maps, compute
monodromy, or construct Hodge atoms. It compares existing persisted records.
