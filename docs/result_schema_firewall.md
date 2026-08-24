# Result Schema and Mathematical Firewall

HodgeCY result objects carry an explicit mathematical level. The schema layer
is intentionally conservative: data computed at one level remains at that level
unless later code supplies a verified comparison or construction.

```text
source / arrangement
        |
actual node geometry
        |
node relations
        |
degeneration / conifold atom information

smooth atom information follows a separate
quantum-product / Euler-spectral construction.
```

The core result kinds are:

- `source_assembly`: combinatorial, incidence, arrangement, assembly, source
  matrix, rank, Smith form, kernel, cokernel, automorphism, or source-profile
  data.
- `node_geometry`: data about an actual singular fiber and its singular scheme.
- `node_relation`: relations attached to a verified geometric node
  configuration.
- `conifold_atom`: degeneration-theoretic Hodge-atom information, including
  future local atoms, vanishing contributions, monodromy, Picard-Lefschetz
  operators, LMHS decorations, and extension data.
- `smooth_hodge_atom`: the future smooth Hodge-atom construction coming from
  quantum product, Euler operators, spectral decomposition, and
  Hodge-compatible generalized eigenspaces.

Numerical agreement between invariants at two levels is not itself a certified
comparison morphism between those levels.

Existing source assembly matrices remain source-level computational objects
unless and until a theorem-backed or independently verified map to geometric
node/vanishing-cycle data is supplied.

## Evidence Status

Every reusable result value carries an `EvidenceStatus`:

- `computed`: produced by a defined computational procedure.
- `verified`: accompanied by an implemented or externally certified
  mathematical verification.
- `imported`: taken from a trusted external dataset/reference.
- `assumed`: used as an input assumption.
- `conjectural`: proposed but not established.
- `unknown`: not presently known or not calculated.
- `not_applicable`: the invariant does not apply.

Unknown mathematical information should be represented as a `ResultValue` with
status and explanatory metadata, not as a bare `None` whose meaning is lost.

## Promotion Safety

The schema exposes explicit promotion functions for future certified
constructions, but they raise `MathematicalPromotionError` unless supplied with
a `ResultValue` whose status is `verified`.

This prevents accidental relabeling such as:

```text
source assembly matrix -> node relation matrix
source rank            -> vanishing-cycle relation rank
source spectrum        -> conifold atom spectrum
source spectrum        -> smooth Hodge-atom spectrum
```

Blob 1 does not implement persistence, singularity finding, node ideals,
Smith-normal-form algorithms, vanishing-cycle calculations, Picard-Lefschetz
monodromy, quantum products, Euler operators, or actual smooth Hodge atoms.
Those later calculations should attach their own result kind and evidence
metadata rather than strengthening source-level results in place.
