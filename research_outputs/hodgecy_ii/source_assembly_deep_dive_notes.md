# HodgeCY II Source Assembly Deep Dive Notes

- Corpus release fingerprint: `8bbf1dff732529afb634f4a24c1d250d3e7ff3a54c79cbfd9c3584e4bca1622b`
- Presentations enumerated with production `FullCorpusContext`: 456
- Exact two-stratum source assemblies reconstructed/stored: 13
- Presentations blocked from exact assembly computation: 443
- Matrix payload directory: `research_outputs/hodgecy_ii/source_assembly_deep_dive/all_456_source_assembly_matrices`

## Computability Status

| status | count |
| --- | --- |
| blocked_exact_quadratic_field_coefficients_not_supported | 2 |
| blocked_parameterized_family_requires_specialization | 440 |
| blocked_partial_or_problematic_source_extraction | 1 |
| computed_exact_two_stratum_source_assembly | 13 |

## Method

The run uses production corpus metadata as the universe boundary, then joins the promoted HodgeCY II source assembly artifacts. Exact matrices are reconstructed only from stored spectra with machine-readable linear forms and incidence tables. Parameterized families, partial extractions, and quadratic-field coefficient records are enumerated but not promoted to exact integral matrices.

## Computed Assemblies

| presentation_id | local_signature | hodge_signature | rank_Q | rank_F2 | kernel_dim_Q | cokernel_dim_Q | smith_normal_form_compact | torsion_primes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | p3=4;p4_0=5;p4_1=0;p5_0=4;p5_1=0;p5_2=0;l3=4 | h12=1;h11=69;euler=136 | 13 | 11 | 3 | 0 | 1^11,2,12 | [2,3] |
| 3 | p3=8;p4_0=6;p4_1=0;p5_0=3;p5_1=0;p5_2=0;l3=3 | h12=3;h11=59;euler=112 | 16 | 13 | 3 | 1 | 1^13,2^2,12 | [2,3] |
| 19 | p3=9;p4_0=8;p4_1=0;p5_0=2;p5_1=0;p5_2=0;l3=2 | h12=4;h11=50;euler=92 | 18 | 16 | 4 | 1 | 1^16,2,20 | [2,5] |
| 32 | p3=8;p4_0=11;p4_1=0;p5_0=1;p5_1=0;p5_2=0;l3=2 | h12=4;h11=46;euler=84 | 20 | 18 | 2 | 0 | 1^18,12^2 | [2,3] |
| 69 | p3=14;p4_0=6;p4_1=0;p5_0=2;p5_1=0;p5_2=0;l3=1 | h12=4;h11=38;euler=68 | 21 | 20 | 4 | 1 | 1^20,6 | [2,3] |
| 84 | p3=16;p4_0=10;p4_1=0;p5_0=0;p5_1=0;p5_2=0;l3=0 | h12=0;h11=40;euler=80 | 26 | 23 | 2 | 0 | 1^23,2,6,12 | [2,3] |
| 84a | p3=16;p4_0=10;p4_1=0;p5_0=0;p5_1=0;p5_2=0;l3=0 | h12=0;h11=40;euler=80 | 26 | 21 | 2 | 0 | 1^21,2,4^3,12 | [2,3] |
| 93 | p3=13;p4_0=9;p4_1=0;p5_0=1;p5_1=0;p5_2=0;l3=1 |  | 23 | 21 | 2 | 0 | 1^21,4,72 | [2,3] |
| 238 | p3=8;p4_0=12;p4_1=0;p5_0=0;p5_1=0;p5_2=0;l3=0 |  | 20 | 16 | 8 | 0 | 1^16,4^3,12 | [2,3] |
| 239 | p3=16;p4_0=10;p4_1=0;p5_0=0;p5_1=0;p5_2=0;l3=0 |  | 26 | 21 | 2 | 0 | 1^21,2,4^3,12 | [2,3] |
| 240 | p3=16;p4_0=10;p4_1=0;p5_0=0;p5_1=0;p5_2=0;l3=0 |  | 26 | 23 | 2 | 0 | 1^23,2,6,12 | [2,3] |
| 241 | p3=16;p4_0=10;p4_1=0;p5_0=0;p5_1=0;p5_2=0;l3=0 |  | 24 | 24 | 4 | 2 | 1^19,3^5 | [3] |
| 245 | p3=20;p4_0=9;p4_1=0;p5_0=0;p5_1=0;p5_2=0;l3=0 |  | 27 | 24 | 1 | 2 | 1^24,2^2,12 | [2,3] |
