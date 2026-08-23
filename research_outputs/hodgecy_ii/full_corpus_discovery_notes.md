# HodgeCY II Full-Corpus Discovery Notes

- Corpus release fingerprint: `8bbf1dff732529afb634f4a24c1d250d3e7ff3a54c79cbfd9c3584e4bca1622b`
- Catalog counts: {"instance_count": 80, "logical_dataset_count": 53, "physical_source_count": 187, "query_table_count": 32, "relationship_edge_count": 247243, "source_data_record_count": 574616978}
- Method: production catalog and production Parquet tables are the primary source. CKC/Cynk-Meyer source-assembly artifacts are used only as historical source artifacts for registered production double-octic PDFs that have no production normalized table.

## Relationship Graph Pass

- Traversed 247243 production relationship edges.
- Nontrivial connected components: 14016; largest component has 6384 nodes.
- `explicit_nodal_conifold_corpus` has 0 production relationship edges and status `descriptor_only_no_production_record_table`.
- Interpretation: the production graph is real and queryable, but the explicit nodal/conifold corpus is still a descriptor-level route in v1.0.0, so no row-level node records can be promoted from it in this pass.

## CY3 Projection

- Built a row-level CY3/source/presentation projection with 217558 rows from normalized production tables plus registered double-octic source artifacts.
- Families represented at row level: cicy3, cicy3_quotient, cicy3_topology, double_octic, grassmannian, ip_weight_system, weighted_hypersurface.
- The projection deliberately preserves entity level and presentation type; it does not collapse source presentations to geometry identities.

## Hodge Collision Pass

- Distinct Hodge tuples: 30319.
- Hodge group inventory rows by dataset/family: 44161.
- Repeated-Hodge inventory rows: 39293.
- Cross-family Hodge collisions: 10478.
- Early reading: ordinary Hodge data collapse heavily both within families and across construction families; the useful signal lives in the attached structural columns and relationship neighborhoods.

## Large Dataset Scans

- Kreuzer-Skarke rows scanned: 473800776; Hodge groups: 30108; repeated groups: 28796; largest fiber: 910113.
- DESY GV invariant rows scanned: 99515615; parent/type summary rows: 5521.
- CICY4 rows scanned for global analogy: 921497; coarse groups: 4419.
- Large-table result: the coarse invariants are extremely non-injective; repeated Hodge fibers are the norm, not an exception.

## Double-Octic Fidelity

- Double-octic source/presentation records: 456.
- Computed source complexes available: 13.
- Fixed-local/fixed-Hodge fibers: 3.
- Repeated local-inventory fibers: 7.
- Requested repeated-inventory members unresolved for source assembly: 13.
- Rational-collapse/integral-separation sets: 1.
- Integral-collapse/equivariant-separation sets: 2.
- Torsion-sensitive Hodge collisions in source assemblies: 1.
- The 84/84a pattern is not isolated: repeated local inventory can split under rational, integral, and equivariant source-complex data.

## Other Fidelity Channels

- Fibration-sensitive Hodge collisions: 203.
- Symmetry/quotient-sensitive Hodge collisions: 22.
- Operator-linked relationship rows: 624.
- Nodal/conifold/transition relationship rows: 0.
- Anomalies/unresolved objects: 2.
- These channels are fidelity phenomena, not Hodge-atom claims. They identify where coarse invariants forget structure.
