# HodgeCY

HodgeCY is a computational Hodge/Calabi--Yau data system and reproducibility framework for assembling, querying, relating, and validating large heterogeneous Calabi--Yau and Hodge-theoretic datasets.

Current release: **HodgeCY v1.0.0 - First Comprehensive Corpus Release**.

DOI: https://doi.org/10.5281/zenodo.22062175

The historical HodgeCY I / v0.2.0 DOI remains separate.

The repository contains the HodgeCY Python package, data adapters, query/catalog infrastructure, tests, small fixtures, documentation, and HodgeCY I reproducibility assets. The production research corpus is intentionally kept outside Git and is addressed through a local data root.

HodgeCY does **not** claim to be a complete database of all Calabi--Yau manifolds. It is a source-aware corpus and infrastructure layer: source records, presentations, abstract geometry claims, derived relationships, and theorem certificates are kept distinct.

## Current Corpus At A Glance

| Measure | Audited value |
| --- | --- |
| Headline source/data records | 574,616,978 |
| Logical datasets | 53 |
| Dataset/source instances | 80 |
| Physical sources | 187 |
| Query tables | 32 |
| Relationship edges | 241,798 |
| CICY divisor enrichment rows | 57,885 |
| ToricCY top-level assets | 7 |
| Acquisition waves complete | 4 |
| Comprehensive initial corpus | Yes |
| Wave 5 required | No |

**Counting convention.** The headline source/data record count counts one primary source, normalized, or native record according to the final corpus census. Relationship edges, nested divisor rows, archive member counts, remote asset counts, and source-registry entries are reported separately because they are different kinds of objects.

The small public metadata summary is in [`docs/corpus`](docs/corpus/README.md). It contains no production data rows.

## Major Datasets

| Data family | Dataset/source | Record count | Representation | Notes |
| --- | --- | --- | --- | --- |
| Toric/KS | Kreuzer--Skarke 4D reflexive polytopes | 473,800,776 | COMPLETE_COLUMNAR / native-lazy query table | Large Parquet-backed corpus; heavy columns stay lazy. |
| Enumerative | DESY CICY GV invariants | 99,515,615 | COMPLETE_COLUMNAR | h11=1..8 represented; h11=9 source-corrupt exception tracked. |
| CICY4 | Complete CICY fourfold configurations/topology | 921,497 | COMPLETE_LOCAL / normalized | CICY4 fibration archive remains native-lazy where appropriate. |
| Toric weights | 4D IP weight systems | 184,026 | COMPLETE_LOCAL / normalized | Weight-system and Hodge/K3 metadata. |
| CICY fibrations | Obvious CICY3 fibrations | 139,597 | COMPLETE_LOCAL / normalized | Exact source-backed fibration edges. |
| CICY quotients | CICY3 quotient fibrations | 20,700 | COMPLETE_LOCAL / normalized | Quotient fibration records. |
| CICY3 | Complete CICY threefold configurations | 7,890 | COMPLETE_LOCAL / normalized | Standard CICY3 presentations. |
| CICY3 | Favorable CICY data | 7,890 | COMPLETE_LOCAL / normalized | Favorable presentations and topology fields. |
| Weighted hypersurfaces | Weighted-P4 CY hypersurfaces | 7,555 | COMPLETE_LOCAL / normalized | Weighted P4 source rows. |
| CICY quotient/free action | CICY free actions and quotients | 1,695 | COMPLETE_LOCAL / normalized | Free-action source records. |
| Divisors | Springer/JHEP CICY divisor topology | 7,820 parent records; 57,885 divisor rows | COMPLETE_NORMALIZED | Nested divisor Hodge tuples are enrichment rows, not headline records. |
| gCICY | APS g21N5.mx / g21N6.mx genuine gCICY source | 2 native source files | COMPLETE_NATIVE_SOURCE | Wolfram export needed before normalized row count is claimed. |
| ToricCY | ToricCY POLY/GEOM/TRIANG/INVOL assets | 7 top-level assets; 4,434,624,498 advertised bytes | COMPLETE_REMOTE_NATIVE_LAZY | Remote/native-lazy registry, not an eager mirror. |
| Operators | Picard--Fuchs/operator records | 613 operators; 584 topological rows | COMPLETE_LOCAL / normalized | Operator and topological enrichment layers. |
| Double octics | HodgeCY I double-octic sources and certificates | partial public corpus | PARTIAL_PUBLIC_CORPUS | Theorem-bearing examples remain explicitly scoped. |
| Grassmannian | PartialFlagVarieties / Grassmannian CY3 records | 31 | COMPLETE_COLUMNAR | Source-derived records plus code resource. |
| K3-fibered | TwoParameterK3 source models | 39 | COMPLETE_COLUMNAR | Source model/operator headers. |

See [`docs/corpus/DATASETS.md`](docs/corpus/DATASETS.md) for the complete logical dataset census.

## What HodgeCY Represents

HodgeCY represents multiple orthogonal layers:

- construction and presentation records;
- source-reported Hodge and topological invariants;
- weight systems and toric data;
- CICY and CICY4 configuration data;
- fibrations and quotient/fibration relationships;
- group actions, quotients, involutions, and orientifold-related source data;
- divisors, intersection-ring expressions, and divisor topology;
- basis-aware vectors, matrices, tensors, and exact algebra infrastructure;
- Picard--Fuchs operators, periods, and topological operator enrichments;
- enumerative invariant sources;
- source-backed relationships and crosswalks;
- provenance, validation, and source-integrity states;
- native-lazy and remote/native-lazy large-data representations.

Depth is not uniform across all categories. [`docs/corpus/COVERAGE.md`](docs/corpus/COVERAGE.md) gives the conservative final coverage matrix.

## Data Architecture

HodgeCY uses a source-preserving architecture:

```text
raw/native source
  -> source instance + provenance
  -> normalized typed records OR native/lazy representation
  -> relationship/enrichment layer
  -> query interface
  -> certificates/reproducibility where applicable
```

A source record is not the same thing as a presentation; a presentation is not automatically an abstract geometry; a derived relationship is not a theorem unless it has the required validation or certificate. This distinction is central to HodgeCY.

## External Data Model

The hundreds of millions of records are not committed to Git. The Git repository contains code, adapters, schemas, tests, small fixtures, documentation, and reproducibility logic. The large research corpus lives in an external data root with raw, staged, normalized, catalog, manifest, checksum, report, cache, rejected, and log areas.

Configure a corpus root with `HODGECY_DATA_ROOT` or pass a root explicitly:

```bash
export HODGECY_DATA_ROOT=/path/to/hodgecy-data
```

```powershell
$env:HODGECY_DATA_ROOT="<path-to-hodgecy-data>"
```

The package reads this environment variable through `hodgecy.config.HodgeCYConfig`.

## Installation

HodgeCY requires Python 3.10 or newer.

```bash
git clone https://github.com/geocy-labs/hodgecy.git
cd hodgecy
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev,storage]"
```

On PowerShell:

```powershell
git clone https://github.com/geocy-labs/hodgecy.git
cd hodgecy
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[dev,storage]"
```

Core dependencies are `pandas` and `sympy`. The `dev` extra installs `pytest`; the `storage` extra installs `duckdb` and `pyarrow` for catalog/query work.

## Quick Start

Open the current external corpus catalog:

```python
from hodgecy.config import open_data_root
from hodgecy.storage import open_catalog

root = open_data_root(require_exists=True)
catalog = open_catalog(root, name="current_corpus", read_only=True)

print(len(catalog.payload["datasets"]))
print(len(catalog.payload["tables"]))
```

Query a bounded projection from a registered table:

```python
from hodgecy.query import QuerySpec

spec = QuerySpec(
    table="current_cicy3_standard",
    fields=("source_record_id", "h11", "h21"),
).limit(5)

rows = catalog.query(spec).to_arrow()
print(rows)
```

Inspect large-data planning before materialization:

```python
from hodgecy.query import QuerySpec

spec = QuerySpec(
    table="kreuzer_skarke",
    fields=("h11", "h12", "euler_characteristic"),
).limit(10)

result = catalog.query(spec)
print(result.plan)
```

Large tables are lazy by default; use explicit projections and limits.

## HodgeCY I

HodgeCY I is the theorem-bearing double-octic/reproducibility layer in this repository. It is narrower than the full corpus: it concerns computational Hodge atom profiles, source assembly spectra, and selected double-octic Calabi--Yau threefold arrangements.

Public references:

- HodgeCY I manuscript/preprint: https://www.preprints.org/manuscript/202607.0967
- HodgeCY I / v0.2.0 archived software DOI: https://doi.org/10.5281/zenodo.21429481

The broader corpus documentation does not upgrade source-reported fields into HodgeCY I theorem claims. Theorem-bearing outputs remain limited to the certified/reproducibility assets tracked for HodgeCY I.

## Known Limitations

HodgeCY documents limitations explicitly:

- DESY CICY GV `h11=9` is represented as `SOURCE_CORRUPT`.
- APS genuine gCICY files `g21N5.mx` and `g21N6.mx` are verified native Wolfram sources, but normalized row export requires a Wolfram-compatible runtime.
- ToricCY is represented as remote/native-lazy metadata and asset indexing, not as a fully normalized local mirror.
- Pfaffian/determinantal Calabi--Yau coverage is source-registry-only.
- Integral topology/torsion coverage is source-registry-only.

See [`docs/corpus/KNOWN_LIMITATIONS.md`](docs/corpus/KNOWN_LIMITATIONS.md).

## Provenance And Validation

Every permanent corpus disposition records source identity, source instance, source revision, physical source or locator, checksum/integrity state where applicable, adapter/schema, validation state, and citation or URL. Data licenses remain attached to their original sources.

See [`docs/corpus/PROVENANCE.md`](docs/corpus/PROVENANCE.md).

## Repository Layout

- `src/hodgecy/`: Python package, catalog/query/storage infrastructure, adapters, exact algebra, relationships, certificates, and HodgeCY I modules.
- `scripts/`: reproducibility and corpus/bootstrap utilities.
- `tests/`: package, data, corpus, query, and HodgeCY I regression tests.
- `docs/`: architecture and public corpus documentation.
- `docs/corpus/`: sanitized current corpus metadata and audit-facing public docs.
- `data/`: small repository fixtures and HodgeCY I reproducibility sources; not the production corpus.
- `paper/`: manuscript-facing tables and figures.
- `release/`: v0.2.0 release/reproducibility bundle.
- `m2/` and `singular/`: CAS scripts/templates for optional verification workflows.

## Development And Testing

Run the full test suite:

```bash
python -m pytest -q
```

Useful focused checks:

```bash
python -m pytest tests/test_wave2_permanent_ingest.py -q
python -m pytest tests/test_current_corpus_closure.py -q
python -m pytest tests/test_ckc_239_240_241_theorem_values.py -q
```

The final public-documentation promotion gate reruns the full suite and the HodgeCY I theorem-bearing regression slice.

## Licensing

The HodgeCY software is MIT licensed; see [`LICENSE`](LICENSE). External datasets retain their own source licenses and terms. The HodgeCY software license does not relicense third-party source corpora.

## Citation

For the current comprehensive HodgeCY release, cite:

```text
Rahman, A. (2026). HodgeCY v1.0.0 - First Comprehensive Corpus Release
(Version 1.0.0) [Computer software]. Zenodo.
https://doi.org/10.5281/zenodo.22062175
```

For the narrower historical HodgeCY I / v0.2.0 double-octic computational release, cite:

```text
Rahman, Abdul. HodgeCY: Computational Hodge Atom Profiles and Source Assembly Spectra
for Double-Octic Calabi--Yau Threefolds. Version 0.2.0. Zenodo.
https://doi.org/10.5281/zenodo.21429481
```

Do not cite the v0.2.0 DOI as the v1.0.0 DOI.

## Future Data Updates

The initial corpus acquisition program is complete: four acquisition waves were reconciled, Wave 5 is not required, and the comprehensive initial corpus is released as HodgeCY v1.0.0. Future public datasets should be treated as versioned HodgeCY corpus updates rather than reopening the initial acquisition program.
