# Blob 8 Basis-Aware Exact Algebra Infrastructure

Blob 8 adds generic exact-algebra infrastructure used by existing HodgeCY computations. It does not run new corpus scans, discovery jobs, theorem searches, or mathematical candidate ranking.

## Basis-Aware Arrays

`hodgecy.math.arrays.BasisArray` records array identity together with every basis axis. It supports dense payloads or metadata-only arrays, stores an entry hash, and refuses equality checks across incompatible basis IDs or coefficient domains.

Use it for source or derived arrays whose entries only make sense in a named basis, such as C2 vectors, intersection matrices/tensors, divisor coordinates, and boundary maps.

## Exact Algebra Results

`hodgecy.algebra.results` introduces stable result records for:

- rational rank
- finite-field rank over prime fields
- Smith normal form invariants over `Z`
- rational kernel/cokernel dimensions

Each result points at an `ExactMatrixRef`, records the exact operation, schema version `exact_algebra_result.v1`, exactness status, and deterministic identity. The helpers are small wrappers around existing SymPy-backed behavior.

## Assembly Wrappers

`hodgecy.assemblies` provides neutral assembly summaries for chain complexes and gluing complexes. A summary records chain modules, boundary maps, matrix references, and exact result payloads. These wrappers are meant for provenance and registry integration, not for discovery execution.

## HodgeCY I Compatibility

The existing public functions in `hodgecy.equivariant.gluing_complex` now delegate through the Blob 8 result wrappers while keeping their legacy return types:

- `rank_over_Q(...) -> int`
- `rank_mod_p(...) -> int`
- `kernel_dimension_Q(...) -> int`
- `cokernel_dimension_Q(...) -> int`
- `smith_normal_form_invariants(...) -> list[int] | None`

Existing theorem-bearing fixtures therefore continue to see the same outputs.
