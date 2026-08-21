# HodgeCY Blob 11 Large-Data Lazy Access

Blob 11 keeps query rows separate from materialized domain payloads. Normal catalog queries return lightweight Arrow-backed result sets; nested or heavy payloads are loaded only when the query explicitly opts in.

## Kreuzer-Skarke Parquet

Use `register_kreuzer_skarke_parquet_source()` with data-root-relative Parquet paths. The registration records physical files, row-group metadata, source revision, schema, heavy column metadata, and safe default projections. Durable catalog records keep relative paths; local absolute paths are used only to open files under the active data root.

The default KS projection excludes `vertices`. The `vertices` field is marked nested, heavy, non-indexable, projection-unsafe, and materialization-only. Scalar filters such as `h11 == 1`, `h12 == 101`, `vertex_count >= n`, and point-count ranges compile to Arrow dataset predicates.

```python
from hodgecy.query import Q, QuerySpec

result = catalog.query(
    QuerySpec(datasets=("kreuzer_skarke",), fields=("h11", "h12", "euler_characteristic"))
    .where(Q.col("h11") == 1)
)

plan = result.explain()
for batch in result.iter_batches(batch_size=100_000):
    ...
```

## Explicit Collection And Heavy Columns

`LazyResultSet` does not support direct iteration. Use `head(n)`, `take(n)`, `iter_batches()`, `to_arrow()`, `to_pandas()`, or `materialize()`. `MaterializationPolicy` has separate limits for total rows, estimated bytes, and heavy-column rows.

```python
from hodgecy.query import MaterializationPolicy, QuerySpec

heavy = catalog.query(QuerySpec(
    datasets=("kreuzer_skarke",),
    fields=("vertices",),
    include_heavy=True,
    materialization_policy=MaterializationPolicy(row_limit=100, heavy_row_limit=1),
))
selected = heavy.head(1)
```

## Query Explain

`result.explain()` reports backend, projected columns, heavy columns, predicate pushdown presence, partition/file count, row-group count, relative source paths, and known/estimated/unknown row and byte estimates. Estimates are operational planning aids, not scientific data.

## Parquet Metadata Cache

`build_parquet_metadata_cache()` writes a disposable JSON cache for Parquet file and row-group metadata. It is rebuildable, versioned, and invalidated by source revision/checksum or file stat fingerprint changes. It never stores heavy payload values such as KS vertices.

## CICY4 Native Fibration Archive

`build_cicy4_fibration_archive_index()` creates a lightweight ZIP member index for native CICY4 fibration archives. It records member names, compressed/expanded sizes, CRC values, and parent ID ranges when supplied by hints, member names, or an explicit streaming pass. Lookup returns member locators; `iter_member_lines()` streams a selected member without extracting the archive.

## Relationship Tables

Relationship queries continue to use catalog-backed `QuerySpec` filters. `RelationshipQueryService` adds backend-filtered counts, type filters, and bounded one-step frontier access. Multi-depth traversal requires explicit batching and row limits.
