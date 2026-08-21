# HodgeCY Blob 4 Storage and Query Foundation

Blob 4 adds the first permanent storage/catalog/query layer without ingesting the full external corpus.

## Data Root

Use an explicit root or `HODGECY_DATA_ROOT`:

```python
from hodgecy import open_data_root
root = open_data_root("/path/to/hodgecy-data")
```

Importing `hodgecy` does not open a catalog, scan data, create directories, or require the external corpus.

## Catalog

Create or open a local catalog under the external data root:

```python
from hodgecy.storage import open_catalog
catalog = open_catalog(root, create=True)
```

The catalog stores logical dataset descriptors separately from installed dataset instances and physical sources. Paths are stored relative to the data root when local.

## Parquet Sources

Small fixture or real read-only Parquet sources can be registered without copying contents. Heavy columns, such as KS `vertices`, can be marked as heavy so scalar projections do not load them by default.

## Query

```python
from hodgecy.query import Q

spec = Q.dataset("ks_fixture").where(Q.hodge(1, 1) == 2).select("h11", "h12", "euler")
result = catalog.query(spec)
rows = result.head(5)
```

Results are lazy. Use `count()`, `iter_batches()`, `head()`, or `take(n)` for bounded access. Full materialization through `to_arrow()` or `to_pandas()` enforces the query materialization limit unless an explicit override is supplied.

## Backends

PyArrow powers Blob 4 fixture Parquet scans. DuckDB is part of the accepted permanent architecture and is exposed as an optional backend dependency; requesting it without installing `hodgecy[storage]` raises a typed missing-capability error.
