# HodgeCY Corpus Documentation

This directory contains the small, public metadata view of the initial comprehensive HodgeCY corpus. It is intentionally not the corpus itself.

## Current Audited State

| Measure | Value |
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
| Wave 5 required | No |

## Counting Convention

The headline source/data record count counts primary source, normalized, or native records according to the final record census. Relationship edges, nested divisor rows, archive members, remote asset counts, and source-registry entries are reported separately because adding unlike objects would obscure what is actually queryable or represented.

## Files

- `current_corpus_summary.json`: compact public machine-readable corpus metadata.
- `current_dataset_census.tsv`: one row per logical dataset, with high-level counts and statuses only.
- `DATASETS.md`: readable dataset census and major source summary.
- `COVERAGE.md`: coverage state by construction family and mathematical data layer.
- `PROVENANCE.md`: source/provenance and integrity model.
- `KNOWN_LIMITATIONS.md`: final known exceptions and future update triggers.

No file in this directory contains local machine paths or production data rows.
