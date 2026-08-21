# Blob 10 Certificate, Reporting, And Release Compatibility

Blob 10 adds generic certificate and reporting infrastructure for HodgeCY build/data artifacts. It does not run Blob 9, execute research experiments, or modify the historical v0.2.0 release artifacts.

## Certificate Classes

`hodgecy.certificates` distinguishes artifact classes and certificate purposes:

- cache: disposable performance material, not provenance
- derived: reproducible HodgeCY-generated material, not automatically certified
- certified: frozen, checksum-backed, provenance-rich artifacts

Certificate purposes include source ingest, normalization, relationship import, data snapshot, report artifact, and legacy theorem result compatibility. A certificate purpose does not promote mathematical claim level by name.

## Manifest Schema

Generic certificates use schema `hodgecy.certificate` / `certificate.v1`. A manifest records subjects, payload checksums, source instances/revisions/checksums, basis labels, relationship evidence, validation events, algorithm provenance, environment metadata, generated summaries, and a deterministic certificate identity.

Certificate identity excludes timestamps and environment capture but includes scientific payload references, subjects, validation, algorithms, checksums, purpose, and schema.

## Build And Verification

`build_certificate` writes payloads and `certificate.json` in a temporary directory, verifies the result, and then atomically promotes it to the final certificate directory. Rebuilding the same certificate is idempotent; conflicting content at the same certificate identity is rejected.

`verify_certificate` checks schema compatibility, manifest identity, duplicate/unsafe paths, missing payloads, payload sizes, and SHA-256 checksums. It returns typed verification issues and does not repair malformed certificates.

## Registry And Reporting

`CertificateRegistryRecord` exposes scalar summary metadata for queryable certificate registries. `register_certificate_summary_parquet_source` registers a certificate registry Parquet table through the existing catalog as a derived artifact. `hodgecy.reporting.certificates` provides compact status rows and reports from registry records.

## Historical Release Compatibility

`legacy_release_summary` and `verify_legacy_release_checksums` read the historical `release/hodgecy-v0.2.0` manifest and verify checksums without rewriting or migrating those files. Existing theorem-bearing examples remain covered by the historical release verifier.
