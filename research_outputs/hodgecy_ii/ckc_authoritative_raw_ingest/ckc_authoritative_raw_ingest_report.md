# CKC Authoritative Raw Ingest Report

- arXiv source: `2602.19413v1`
- PDF acquired: True
- PDF SHA256: `b356c1e6972424eb69c7d10383511cfe62c71daf00afe8bca5572e9c2eac2955`
- PDF page count: 50
- PDF pages ingested: 50
- Source archive acquired: True
- Source archive SHA256: `a177799a9b70b4b12476f747a02291b6316a5237d8ab92c15eb3b63e31890a52`
- Source files ingested: 3
- Separately advertised ancillary files acquired: 0
- Source support files acquired from arXiv archive: 2
- TeX blocks parsed: 687
- Tables ingested: 5
- Arrangement equations found: 455
- Parameter-condition blocks found: 47
- Classification/incidence source blocks found: 60
- Code blocks found: 1
- CKC dossiers built: 455
- Missing CKC IDs: []

## Completeness Flags

- `PDF_COMPLETE`: True
- `TEX_COMPLETE`: True
- `ANCILLARY_COMPLETE`: True
- `PAGE_INGEST_COMPLETE`: True
- `TABLE_INGEST_COMPLETE`: True
- `EQUATION_INGEST_COMPLETE`: True
- `CODE_INGEST_COMPLETE`: True
- `CKC_455_DOSSIERS_COMPLETE`: True

## Acquisition Finding

The arXiv source bundle includes equations and Magma code, but no separate author-supplied classified incidence tables or parameter-ideal data files were present in the source package.

## Targeted Raw Audit

| CKC ID | page | TeX lines | raw factors | parameters | algebraic constants | context blocks | note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 451 | 45 | [2985, 2988] | 13 | [] | ['\\sqrt{-3}'] | ['ckc_param_condition_0016', 'ckc_classification_or_incidence_0024'] | authoritative TeX raw equation captured; raw factor tokenizer sees 13 factors, preserving the source-level parenthesis/fraction ambiguity for follow-up |
| 452 | 45 | [2988, 2991] | 8 | [] | ['\\sqrt{-3}'] | ['ckc_param_condition_0016', 'ckc_classification_or_incidence_0024'] | authoritative TeX raw equation captured with 8 factors and algebraic constants; promoted source assembly should remain traceable to this raw source |
| 453 | 45 | [2991, 2994] | 8 | [] | ['\\sqrt{5}'] | ['ckc_param_condition_0016', 'ckc_classification_or_incidence_0004', 'ckc_classification_or_incidence_0024'] | authoritative TeX raw equation captured with 8 factors and algebraic constants; promoted source assembly should remain traceable to this raw source |
| 454 | 45 | [2994, 2997] | 8 | ['A_{0}', 'A_{1}'] | ['\\sqrt{-3}'] | ['ckc_param_condition_0016', 'ckc_classification_or_incidence_0004', 'ckc_classification_or_incidence_0024'] | authoritative TeX raw equation captured with 8 factors, parameters, and algebraic constants; no source assembly derived in this phase |

## Historical Discrepancy Histogram

| classification | count |
| --- | --- |
| formatting_or_normalization_difference | 11 |
| normalization_difference_or_substantive_discrepancy | 444 |

## Raw Storage

- Production raw root: `C:\geocy-labs\hodgecy-data\raw\cynk_kocel_cynk_2026\authoritative`
- Structured raw directory: `C:\geocy-labs\hodgecy-data\raw\cynk_kocel_cynk_2026\authoritative\structured_raw`
- CKC dossiers directory: `C:\geocy-labs\hodgecy-data\raw\cynk_kocel_cynk_2026\authoritative\ckc_raw_arrangement_dossiers`

No derived incidence or source-assembly computation was performed in this ingest.
