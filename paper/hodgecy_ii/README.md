# HodgeCY II Manuscript Package

This directory contains the manuscript architecture for the HodgeCY II paper.
It is planning and assembly material only: it does not introduce new
mathematics, alter theorem status, tag a release, or change package metadata.

## Frozen Inputs

The package is based on the verified HodgeCY II repository state with:

- `456` processed double-octic presentations.
- `114` nontrivial source-level pairs/sets.
- `57 / 13 / 44` pairs/triples/larger sets.
- theorem status `PROVED_WITH_STATED_HYPOTHESES` for the Hilbert--Burch block
  theorem.
- unsupported promotions: none.

Primary evidence and manuscript assets live under
`research_outputs/hodgecy_ii/final/` and
`research_outputs/hodgecy_ii/manuscript_assets/`.

## Files

- `hodgecy_ii.tex`: compilable manuscript skeleton.
- `abstract_draft.tex`: 200-word abstract draft.
- `section_outline.tex`: detailed 30--40 page section architecture.
- `theorem_stack.tex`: theorem/proposition stack stated at manuscript level.
- `scope_nonclaims.tex`: precise claims firewall and nonclaims.
- `manuscript_plan.md`: high-level writing plan and page budget.
- `title_candidates.md`: ranked title options and recommendation.
- `figure_table_map.md`: main/supplementary figure and table placement.
- `related_work_notes.md`: conservative literature-positioning notes.
- `references.bib`: manuscript bibliography copied from the verified related-work
  bundle, with HodgeCY release references added.

## Compilation

From this directory:

```bash
pdflatex -interaction=nonstopmode -halt-on-error hodgecy_ii.tex
bibtex hodgecy_ii
pdflatex -interaction=nonstopmode -halt-on-error hodgecy_ii.tex
pdflatex -interaction=nonstopmode -halt-on-error hodgecy_ii.tex
```

If a local TeX installation is unavailable, the files are still plain LaTeX
source and can be compiled in any standard LaTeX environment with `amsmath`,
`amssymb`, `amsthm`, `geometry`, and `hyperref`.
