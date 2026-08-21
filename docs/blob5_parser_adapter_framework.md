# Blob 5 Parser and Adapter Framework

Blob 5 implements the accepted parser/adapter framework scope from `implementation_blobs.tsv`:
parser protocols, rejected-record handling, adapter descriptors, and a fixture harness. It does not perform a full permanent corpus migration; corpus-specific adapters are intended to build on this layer.

## Parser Layer

The `hodgecy.parsers` package provides small, deterministic parsers for fixture-scale source formats:

- `JsonlParser` parses line-delimited JSON objects and rejects malformed lines or non-object records.
- `BlockTextParser` parses blank-line or `---` separated `key: value` blocks.
- `MathematicaRuleParser` parses a safe subset of Mathematica rule/list syntax without evaluation.
- `ZipArchiveParser` delegates safe archive members by extension and rejects unsafe paths.
- `ParquetRowParser` reads Parquet rows through PyArrow with optional row and column limits.

All parsers return `ParseResult` objects containing `ParsedRecord`, `RejectedRecord`, and `ValidationEvent` data. Rejections can be serialized deterministically with `write_rejected_jsonl`.

## Adapter Layer

The `hodgecy.datasets.base` module provides:

- `DatasetAdapter` protocol for future corpus-specific adapters.
- `FixtureDatasetAdapter` for parser fixture runs.
- `AdapterRun` and `AdapterRunSummary` for execution summaries.
- `NormalizationManifest` for deterministic normalization metadata.

`FixtureDatasetAdapter` converts parsed records into core `SourceRecordEnvelope` objects using Blob 3 provenance and identity types. It preserves parser validation events and adds a source-envelope validation event for downstream validation gates.

## Registry

`AdapterRegistry` stores one adapter per dataset identity and rejects duplicate registration unless `replace=True` is explicit.

## Scope Boundary

The larger permanent-corpus ingest described in the prompt is intentionally deferred. The authoritative Blob 5 row in `implementation_blobs.tsv` specifies no data migration and fixture coverage for block text, Mathematica rules/list, JSONL, ZIP, and Parquet. This framework is the base that later dataset-specific adapters can use for CICY, Kreuzer-Skarke, CYO, DESY archive payloads, and other corpora.
