# Persistent Result Registry

the ResultStore layer adds a SQLite-backed registry for immutable HodgeCY research results.
The registry stores provenance and retrieval metadata; it does not perform new
mathematical calculations.

## Layout

A typical project layout is:

```text
results/
    hodgecy-results.sqlite
    artifacts/
        <sha256-addressed files>
    exports/
        <optional JSON envelopes>
```

The package does not hard-code this path. `ResultStore(path)` receives the
SQLite path and uses a configurable artifact directory.

## Records

The registry stores:

- `GeometryRecord`: a stable geometry/dataset entry. Equality is not inferred
  from display names; callers must supply a stable `geometry_id` or use the
  documented deterministic helper based on source metadata.
- `CalculationRun`: one immutable execution context with HodgeCY version, git
  commit when available, input/parameter hashes, backend, coefficient ring, and
  status.
- `InvariantRecord`: scalar or small JSON-compatible mathematical values with
  the result-schema layer `ResultKind` and `EvidenceStatus`.
- `CertificateRecord`: persistent evidence supporting a subject such as a
  future matrix rank, node verification, or source-to-node comparison.
- `ArtifactRecord`: metadata for external files such as matrices, lattices, or
  forms. Large payloads are kept out of SQLite rows.
- `SpectrumRecord`: persistence envelope for the result-schema layer spectrum objects.
- `ComparisonSetRecord`: named sets of two or more geometries for future the comparison-engine layer
  comparison logic.

## Immutability

Research records are historical. Completed runs are not overwritten when a
calculation is repeated. Instead a later run can supersede an earlier one by
recording:

```text
superseded_by_run_id
supersession_reason
```

The old run and its outputs remain inspectable.

## Evidence and Certificates

`EvidenceStatus.UNKNOWN` is persisted as real data; it is not dropped because a
value is null.

`EvidenceStatus.VERIFIED` can reference a concrete `CertificateRecord` through
`certificate_id`. the ResultStore layer does not require certificates for every legacy
verified object, because older in-memory objects may not have persistent
certificates yet. New persisted verified research results should carry a
certificate whenever possible.

## Content Hashes

Hashes use deterministic SHA-256 over normalized JSON-compatible content or file
bytes. JSON normalization is the same as `canonical_json`: sorted keys and
compact separators. Python's process-randomized `hash()` is never used.

Artifacts are stored as content-addressed files. Integrity validation recomputes
the file hash and raises `ArtifactIntegrityError` if the bytes differ from the
stored hash.

## SQLite and JSON

SQLite is the canonical searchable registry. JSON envelopes are portable
interchange/export records:

```json
{
  "schema_version": "result_store.v1",
  "record_type": "geometry",
  "payload": {}
}
```

JSON export is deterministic where practical, but importing/exporting JSON does
not replace the SQLite registry.

## Schema Versioning

The SQLite schema uses `PRAGMA user_version`. the ResultStore layer creates schema version `1`.
Opening a database with a future unsupported version fails with
`ResultStoreSchemaVersionError`.

This is intentionally lightweight. Future migrations should add explicit
version steps without making existing research records unreadable.

## Spectrum Type Preservation

The persistence layer stores both:

```text
result_kind
concrete_type
```

for spectra. These must agree. A stored `SourceAssemblySpectrum` is restored as
`SourceAssemblySpectrum`, not as a `ConifoldAtomSpectrum` or
`SmoothHodgeAtomSpectrum`. Invalid discriminator/type pairs fail loudly.

Persistence is not a back door around the the result-schema layer mathematical firewall.

## Synthetic Example

```python
from hodgecy.core import EvidenceStatus, ResultKind
from hodgecy.storage import ResultStore

store = ResultStore("results/hodgecy-results.sqlite")
store.initialize()

geom = store.add_geometry(
    geometry_id="synthetic-A",
    display_name="Synthetic geometry A",
    geometry_type="test",
)

run = store.begin_run(
    geometry_id=geom.geometry_id,
    calculation_type="source_assembly",
)

store.record_invariant(
    run_id=run.run_id,
    name="source_rank",
    value=8,
    result_kind=ResultKind.SOURCE_ASSEMBLY,
    evidence_status=EvidenceStatus.COMPUTED,
)

store.complete_run(run.run_id)

rows = store.get_invariants(geometry_id="synthetic-A")
```

the ResultStore layer does not implement comparison algorithms, singularity finding, node
relations, vanishing cycles, monodromy, Hodge atoms, or quantum products. It
stores their future results without silently strengthening their meaning.
