# HodgeCY

HodgeCY is a source-aware computational Hodge and Calabi--Yau data system. It
keeps source presentations, normalized records, derived invariants,
relationships, and theorem-grade certificates distinct so that a calculation
can be reused without silently becoming a geometric claim.

Current release: **HodgeCY v1.0.0 - First Comprehensive Corpus Release**.

DOI: https://doi.org/10.5281/zenodo.22062175

The historical HodgeCY I / v0.2.0 DOI remains separate:
https://doi.org/10.5281/zenodo.21429481

## Current Mathematical Layers

HodgeCY separates the following layers.

- Source / arrangement layer: source records, plane arrangements, incidence
  profiles, Hodge table links, rational/modular/integral source assembly, Smith
  normal forms, torsion, and symmetry signatures.
- Node geometry layer: singular-scheme infrastructure, Hilbert functions,
  ordinary-double-point checks, node-block certificates where explicit
  geometric input is available, and verified block-scheme Hilbert/evaluation
  theorems where the required hypotheses have been certified.
- Relation layer: abstract node-relation complexes and source-to-node
  comparison framework, with feasibility states separated from theorem claims.
  Block-evaluation relations are not identified with node, vanishing-cycle,
  LMHS, or Hodge-atom relations.
- Future Hodge-atom layers: vanishing-cycle, LMHS, extension, and atom-level
  structures. These are not inferred merely from source-fidelity census
  membership.

The firewall is intentional: same local inventory, same Hodge data, same
rational source type, same integral source type, and same equivariant source
type are different statements.

## What HodgeCY Can Currently Compute

Implemented generic infrastructure includes:

- arrangement/source profiles and incidence inventories;
- rational, modular, and integral source assembly;
- exact integer-lattice and Smith-normal-form calculations;
- source symmetry and equivariant signature comparisons;
- persistent result records, artifacts, certificates, and comparison sets;
- cross-dataset catalog/query infrastructure with lazy large-table access;
- singular-scheme and Hilbert-function certification scaffolding;
- classical-defect infrastructure;
- node-relation complexes;
- source-to-node comparison morphisms and feasibility records.

Completed theorem-bearing calculations are narrower. HodgeCY I provides the
tracked double-octic source and smoothing assets for the principal `84 / 84a`
pair, including the original source-fidelity witness. HodgeCY II extends that
witness into exact block geometry and proves a structural Hilbert--Burch
explanation for the common block Hilbert/evaluation profile. Broader
population-level source-fidelity census rows are context unless a separate
validation status says otherwise.

## Quick Start

Install for local development:

```bash
python -m pip install -e ".[dev,storage]"
python -m pytest -q
```

Generate the HodgeCY II manuscript-facing census assets:

```bash
python scripts/generate_hodgecy_ii_manuscript_assets.py
```

Verify the structural HodgeCY II Hilbert--Burch/block theorem:

```bash
python scripts/verify_hodgecy_ii_hilbert_burch.py
```

Reproduce the final HodgeCY II synthesis package:

```bash
python scripts/reproduce_hodgecy_ii.py
```

The generated scope and asset manifests are:

- [HodgeCY II scope](research_outputs/hodgecy_ii/manuscript_assets/manifest/hodgecy_ii_scope.json)
- [HodgeCY II asset manifest](research_outputs/hodgecy_ii/manuscript_assets/manifest/hodgecy_ii_asset_manifest.json)
- [HodgeCY II final results](research_outputs/hodgecy_ii/final/hodgecy_ii_final_results.json)
- [HodgeCY II Hilbert--Burch theorem](research_outputs/hodgecy_ii/final/hodgecy_ii_hilbert_burch_theorem.tex)
- [HodgeCY II related-work review](research_outputs/hodgecy_ii/final/hodgecy_ii_literature_review.md)
- [HodgeCY II related-work BibTeX](research_outputs/hodgecy_ii/final/hodgecy_ii_related_work.bib)
- [Hilbert--Burch theorem evidence](research_outputs/hodgecy_ii/final/theorem_evidence/hilbert_burch_block_theorem.json)

For external production data, configure a data root:

```bash
export HODGECY_DATA_ROOT=/path/to/hodgecy-data
```

PowerShell:

```powershell
$env:HODGECY_DATA_ROOT="<path-to-hodgecy-data>"
```

## HodgeCY II

HodgeCY II uses the complete source-level fidelity census as population
context:

- total double-octic presentations processed: `456`;
- historical nontrivial fidelity pairs/sets: `114`;
- pairs/triples/larger sets: `57 / 13 / 44`;
- primary deep geometric laboratory: `84 / 84a`.

The census shows that source-fidelity collapse and separation recur beyond the
principal pair. HodgeCY II does not geometrically analyze all 114 sets; that
full population classification is deferred to HodgeCY III.

For `84` and `84a`, the primary witness has the same local inventory, the same
Hodge signature, and the same rational source type, but different verified
integral source Smith types:

- `84`: `(1^23,2,6,12)`;
- `84a`: `(1^21,2,4,4,4,12)`.

HodgeCY II then follows this witness into exact block geometry. For the
verified eight-plane block construction, the line skeleton has resolution

```text
0 -> S(-8)^7 -> S(-7)^8 -> I_C -> 0
```

and the frozen quartic is regular on the verified line skeleton. The resulting
block scheme has Hilbert series

```text
Hilb_{S/I_B}(t) = (1-t^4)(1-8t^7+7t^8)/(1-t)^4
```

and Hilbert function

```text
1,4,10,20,34,52,74,92,105,112,112,...
```

stabilizing at degree `9`. In particular, `H_B(8)=105`,
`h^1(P^3,I_B(8))=7`, and the degree-8 block-evaluation deficiency is `7` for
the verified block scheme.

The central HodgeCY II phenomenon is therefore non-monotone across fidelity
layers: integral source separation, followed by structurally forced
block-evaluation collapse. The verified degree-8 block-evaluation data do not
determine the integral source-assembly type on the witness pair `84 / 84a`.
The reverse implication is not claimed.

This remains a theorem about the verified block scheme. It is not an
unconditional classical defect calculation. Ordinary-node promotion, equality
with the full saturated Jacobian/full singular scheme, the actual classical
nodal defect, a source-to-evaluation morphism, an integral evaluation lattice,
and LMHS/MHM/Hodge-atom interpretations remain open or not claimed as
appropriate.

The final HodgeCY II synthesis freezes question statuses, theorem/evidence
records, conditional results, open problems, manuscript table/figure
inventories, and a HodgeCY III handoff under
[research_outputs/hodgecy_ii/final](research_outputs/hodgecy_ii/final).

The source-checked HodgeCY II related-work review is available at
[research_outputs/hodgecy_ii/final/hodgecy_ii_literature_review.md](research_outputs/hodgecy_ii/final/hodgecy_ii_literature_review.md).

Representative controls include `61 / 451`, `84 / 84a`, `452 / 453`,
`84 / 240`, `84a / 239`, and `239 / 240 / 241`. The generated tables preserve
the factor-normalization warning for `451` and the deferred exact
quadratic-field status for `452 / 453`.

## Reproducibility

Persistent outputs record HodgeCY version, git commit, input hashes, source
record IDs, generator version, and validation/provenance status. Generated
manuscript assets are rebuilt from the historical census TSV and current v1.0
structured source records. The structural Hilbert--Burch theorem has a
dedicated verifier and theorem-evidence bundle, and the final reproduction
workflow checks deterministic manuscript assets and unsupported-promotion
status.

Local SQLite result stores, caches, and transient CAS artifacts are not
committed. Versioned artifacts are JSON/TSV/CSV/Markdown/LaTeX/SVG files with
hashes in the asset manifest.

## Documentation

Start with the documentation index:

- [Documentation index](docs/README.md)
- [Current public corpus summary](docs/corpus/README.md)
- [Result schema firewall](docs/result_schema_firewall.md)
- [ResultStore registry](docs/result_store_registry.md)
- [Comparison engine](docs/comparison_engine.md)
- [HodgeCY II cohort](docs/hodgecy_ii_cohort.md)
- [Integral lattice engine](docs/integral_lattice_engine.md)
- [Node relation complexes](docs/node_relation_complexes.md)
- [Source-to-node comparison](docs/source_to_node_comparison.md)
- [Source versus block evaluation](docs/source_block_evaluation_comparison.md)
- [Reproduce HodgeCY II](docs/reproduce_hodgecy_ii.md)

## Repository Layout

- `src/hodgecy/`: package code, adapters, exact algebra, storage, comparison,
  relations, certificates, and research helpers.
- `scripts/`: reproducibility, corpus, and manuscript-asset generators.
- `tests/`: package, data, storage, comparison, and HodgeCY regression tests.
- `docs/`: architecture and workflow documentation.
- `docs/corpus/`: sanitized public corpus metadata.
- `data/`: small fixtures and HodgeCY I/HodgeCY II reproducibility inputs.
- `research_outputs/`: versioned research reports and generated manuscript
  assets; local databases and caches stay ignored.
- `paper/`: manuscript-facing tables and figures for the earlier paper asset
  pipeline.
- `release/`: historical v0.2.0 release/reproducibility bundle.

## Roadmap

- Preserve and publish the completed HodgeCY II source-vs-block theorem.
- Promote ordinary-node, full singular-scheme, and classical-defect layers only
  when independently certified.
- Keep source-to-evaluation morphisms and integral evaluation-lattice
  comparisons open until constructed.
- Reserve full theorem-level population stratification and broader new mining
  for HodgeCY III.
- Treat future LMHS/MHM/Hodge-atom comparison as a separate theoretical bridge,
  not an inferred result.

## Licensing And Citation

The HodgeCY software is MIT licensed; see [LICENSE](LICENSE). External datasets
retain their own licenses and terms.

For the current comprehensive HodgeCY release, cite:

```text
Rahman, A. (2026). HodgeCY v1.0.0 - First Comprehensive Corpus Release
(Version 1.0.0) [Computer software]. Zenodo.
https://doi.org/10.5281/zenodo.22062175
```

For HodgeCY I / v0.2.0:

```text
Rahman, Abdul. HodgeCY: Computational Hodge Atom Profiles and Source Assembly
Spectra for Double-Octic Calabi--Yau Threefolds. Version 0.2.0. Zenodo.
https://doi.org/10.5281/zenodo.21429481
```
