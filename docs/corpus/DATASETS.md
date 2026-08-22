# HodgeCY Dataset Census

HodgeCY v1.0.0's public Git repository stores code, tests, fixtures, schemas, and this metadata summary. The production corpus lives in an external data root.

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

## Complete Logical Dataset Census

| Dataset ID | Dataset | Family | Completion class | Headline records | Nested/enrichment | Relationships |
| --- | --- | --- | --- | --- | --- | --- |
| aesz_cydb_remote | AESZ/CY differential equation database | picard_fuchs | COMPLETE_REMOTE |  |  |  |
| aps_gcicy_type21_supplements | APS Physical Review D supplemental files g21N5.mx and g21N6.mx | generalized_cicy | COMPLETE_NATIVE_SOURCE |  | 2 native source files |  |
| borcea_voisin_source_registry | Borcea-Voisin systematic source registry | borcea_voisin | SOURCE_REGISTRY_ONLY |  |  |  |
| cicy3_discrete_symmetries_orientifolds | Cicy3 Discrete Symmetries Orientifolds | cicy3 | COMPLETE_NATIVE_LAZY |  |  |  |
| cicy3_divisor_configs_orientifold | Cicy3 Divisor Configs Orientifold | cicy3 | COMPLETE_NORMALIZED | 7,821 |  |  |
| cicy3_divisor_topology_springer | CICY3 divisor topology Springer source | cicy3 | COMPLETE_NORMALIZED | 7,820 |  |  |
| cicy3_divisors_springer | Cicy3 Divisors Springer | cicy3 | MANUAL_SOURCE_REQUIRED |  |  |  |
| cicy3_favorable | Favorable CICY threefold presentations | cicy3 | COMPLETE_NORMALIZED | 7,820 |  |  |
| cicy3_fibrations | Obvious CICY3 fibrations | cicy3 | COMPLETE_NORMALIZED | 139,597 |  |  |
| cicy3_orientifold_discrete_symmetry | Cicy3 Orientifold Discrete Symmetry | cicy3 | COMPLETE_NATIVE_LAZY |  |  |  |
| cicy3_orientifolds_favourable | Cicy3 Orientifolds Favourable | cicy3 | COMPLETE_NORMALIZED | 7,820 |  |  |
| cicy3_quotient_fibrations | Cicy3 Quotient Fibrations | cicy3 | COMPLETE_NORMALIZED | 20,700 |  |  |
| cicy3_quotients | CICY free actions and quotients | cicy3 | COMPLETE_NORMALIZED | 1,695 |  |  |
| cicy3_standard | Complete CICY threefold configurations | cicy3 | COMPLETE_NORMALIZED | 7,890 |  |  |
| cicy3_thraxion_candidates | Cicy3 Thraxion Candidates | cicy3 | COMPLETE_NORMALIZED | 1 |  |  |
| cicy3_thraxion_transitions | Cicy3 Thraxion Transitions | cicy3 | COMPLETE_NORMALIZED | 1 |  |  |
| cicy4_core | Complete CICY fourfold configurations/topology | cicy4 | COMPLETE_NORMALIZED | 921,497 |  |  |
| cicy4_fibrations | CICY4 elliptic fibration archive | cicy4 | COMPLETE_NATIVE_LAZY | 921,497 |  |  |
| cicy_divisor_topologies_cms_2022 | Springer/JHEP CICY divisor topology ESM | cicy3 | COMPLETE_NORMALIZED | 7,820 | 57885 |  |
| cicy_gv_invariants_desy | DESY CICY Gopakumar--Vafa Invariants | cicy3 | COMPLETE_COLUMNAR | 99,515,615 |  |  |
| cicy_gv_invariants_desy_h11_9_repair | DESY CICY GV h11=9 repaired archive | cicy3_enumerative | SOURCE_CORRUPT |  |  |  |
| current_corpus_relationships | Current Corpus Relationships | current_corpus_relationships | COMPLETE_RELATIONSHIP |  |  | 175,928 |
| cytools_source_registry | CYTools software/data interface | toric_hypersurface | SOURCE_REGISTRY_ONLY |  |  |  |
| cytools_toric_computable_capability | CYTools computable toric cone and triangulation workflow | toric_hypersurface | COMPUTABLE_NOT_PREENUMERATED |  |  |  |
| double_octics | Double Octics | double_octics | PARTIAL_PUBLIC_CORPUS |  |  |  |
| double_octics_external | Double Octics External | double_octics_external | PARTIAL_PUBLIC_CORPUS |  |  |  |
| explicit_nodal_conifold_corpus | Explicit Nodal Conifold Corpus | explicit_nodal_conifold_corpus | PARTIAL_PUBLIC_CORPUS |  |  |  |
| gcicy_fake_weighted | Fake weighted projective CYCI records | weighted_p4 | COMPLETE_NORMALIZED | 1,752 |  |  |
| gcicy_ml_cui_gao_wang_2023 | Machine-learned generalized CICY supplemental matrices | cicy3 | MANUAL_SOURCE_REQUIRED |  |  |  |
| genuine_gcicy | Genuine Gcicy | genuine_gcicy | SOURCE_REGISTRY_ONLY |  |  |  |
| grassmannian_homogeneous | Grassmannian Homogeneous | grassmannian_homogeneous | SOURCE_REGISTRY_ONLY |  |  |  |
| grassmannian_homogeneous_source_only | Grassmannian Homogeneous Source Only | grassmannian_homogeneous_source_only | SOURCE_REGISTRY_ONLY |  |  |  |
| integral_topology_torsion_source_registry | Integral topology/torsion source registry | topology | SOURCE_REGISTRY_ONLY |  |  |  |
| ip_weight_systems_4d | 4D IP weight systems with Hodge/K3 data | toric_hypersurface | COMPLETE_NORMALIZED | 184,026 |  |  |
| kreuzer_skarke | Kreuzer-Skarke reflexive 4-polytopes | toric_hypersurface | COMPLETE_NATIVE_LAZY | 473,800,776 |  |  |
| ks_orientifolds_groupofxg_2024 | GroupofXG KS Orientifold Release | toric_hypersurface | COMPLETE_REMOTE | 135 |  |  |
| ml_conifold_pfv_scorer_dataset | ML conifold PFV scorer dataset | source_registry | EXCLUDED_LOW_VALUE |  |  |  |
| partialflagvarieties_grassmannian_cy3_table1 | PartialFlagVarieties Grassmannian CY3 Table 1 | grassmannian_homogeneous | COMPLETE_NORMALIZED | 31 |  |  |
| partialflagvarieties_jl | PartialFlagVarieties.jl | grassmannian_homogeneous | CODE_RESOURCE |  |  |  |
| pfaffian_determinantal_cy_source_registry | Pfaffian/determinantal Calabi-Yau source registry | pfaffian_determinantal | SOURCE_REGISTRY_ONLY |  |  |  |
| picard_fuchs_cyo | Picard Fuchs Cyo | picard_fuchs | COMPLETE_REMOTE | 613 |  |  |
| picard_fuchs_cyo_topological | Calabi-Yau operator topological data | picard_fuchs | COMPLETE_NORMALIZED | 1,197 |  |  |
| thraxion_conifold_transition | Thraxion Conifold Transition | thraxion_conifold_transition | PARTIAL_PUBLIC_CORPUS |  |  |  |
| toric_ci_nef_partitions | Toric Ci Nef Partitions | toric_hypersurface | COMPUTABLE_NOT_PREENUMERATED |  |  |  |
| toric_ks_fibrations_abbasi_nally_taylor_2026 | Toric/KS Fibrations from Zenodo 18500236 | toric_hypersurface | COMPLETE_REMOTE | 5 |  |  |
| toric_orientifold_enrichment | Toric Orientifold Enrichment | toric_hypersurface | COMPLETE_REMOTE |  |  |  |
| toriccy_database | ToricCY database/package/query service | toric_hypersurface | COMPLETE_REMOTE_NATIVE_LAZY |  | 7 |  |
| twoparameterk3_code_resource | TwoParameterK3 Code and Notebook Resource | k3_fibered | CODE_RESOURCE |  |  |  |
| twoparameterk3_models | TwoParameterK3 Model and Operator Source Headers | k3_fibered | COMPLETE_NORMALIZED | 39 |  |  |
| wave2_source_relationships | Wave 2 Source Relationships | source_relationships | COMPLETE_COLUMNAR |  |  |  |
| wave3_source_relationships | Wave 3 Source and Resource Relationships | source_registry | COMPLETE_RELATIONSHIP |  |  |  |
| wave4_source_relationships | Wave 4 source relationships | relationships | COMPLETE_RELATIONSHIP |  |  | 65,714 |
| weighted_p4 | Weighted-P4 CY hypersurfaces | weighted_p4 | COMPLETE_NORMALIZED | 2,781 |  |  |
