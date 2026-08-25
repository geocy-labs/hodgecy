# Figure and Table Map

## Main Figures

| label | asset | section/subsection | status | purpose | caption |
| --- | --- | --- | --- | --- | --- |
| II.1 | `research_outputs/hodgecy_ii/manuscript_assets/figures/fidelity_hierarchy.svg` | Section 2.7 | Main, essential | Introduces the local-to-source-to-geometry fidelity ladder. | The HodgeCY II fidelity hierarchy, separating local inventory, Hodge data, rational source assembly, integral Smith type, torsion/equivariant source layers, and later geometric block/evaluation layers. |
| II.2 | `research_outputs/hodgecy_ii/manuscript_assets/figures/neighborhood_84_refinement_tree.svg` | Section 4.5 | Main, essential | Shows why \(84/84a\) is the deep witness inside the nearby recurrent fiber. | Refinement tree around the \(84/84a\) witness, with repeated-local and rational-collapse neighbors displayed before finer source-level separation. |
| II.3 | `research_outputs/hodgecy_ii/manuscript_assets/figures/node_certification_bridge.svg` | Section 6.4 | Main, essential | Keeps verified degree-112 block schemes separate from ordinary-node promotion. | Certification bridge from the frozen eight-plane/quartic data to verified block schemes; ordinary-node promotion and full singular-scheme equality remain open. |
| II.4 | `research_outputs/hodgecy_ii/manuscript_assets/figures/hilbert_profile_comparison.svg` | Section 7.2 | Main, essential | Visualizes equality of the \(84\) and \(84a\) Hilbert profiles. | Identical verified block Hilbert profiles for \(84\) and \(84a\), including \(H_B(8)=105\) and stabilization at degree \(9\). |
| II.6 | `research_outputs/hodgecy_ii/manuscript_assets/figures/source_block_two_axis_comparison.svg` | Section 8.1 | Main, essential | Central visual for non-monotone fidelity: source split, block-evaluation collapse. | Source-level integral separation versus structurally explained block-evaluation collapse for the \(84/84a\) witness pair. |

## Supplementary Figures

| label | asset | section/subsection | status | purpose | caption |
| --- | --- | --- | --- | --- | --- |
| II.5 | `research_outputs/hodgecy_ii/manuscript_assets/figures/evaluation_relation_diagram.svg` | Appendix or supplement after Section 7 | Supplementary, optional/redundant | Gives relation-level detail for readers who want the degree-eight evaluation diagram. | Degree-eight verified block-evaluation relation diagram for the \(84/84a\) block schemes. This figure supplements the Hilbert-profile and two-axis comparison figures. |
| S.1 | `research_outputs/hodgecy_ii/manuscript_assets/figures/final_result_hierarchy.svg` | Supplement | Supplementary, optional | Records the final result hierarchy and future-work handoff. | Final HodgeCY II result hierarchy, with theorem-level, certified, conditional, and open layers separated. |

## Main Tables

| label | asset stem | section/subsection | status | purpose | columns to retain/remove | caption |
| --- | --- | --- | --- | --- | --- | --- |
| II.1 | `fidelity_census_summary` | Section 3.2 | Main, essential | Records 456 processed presentations, 114 nontrivial sets, and 57/13/44. | Retain totals, pairs, triples, larger sets, status. Remove generator-only metadata if space is tight. | Frozen HodgeCY II source-fidelity census summary for the 456-presentation double-octic cohort. |
| II.2 | `representative_fidelity_controls` | Section 3.4 | Main, essential | Shows representative controls beyond the principal witness. | Retain members, shared invariant, first separating invariant, warning/status. Remove raw file paths. | Representative fidelity-control sets illustrating recurring collapse and separation patterns. |
| II.3 | `neighborhood_84_refinement` | Section 4.5 | Main, essential | Places \(84/84a\) beside \(239/240/241\) and adjacent controls. | Retain members, shared local/Hodge/rational layers, integral/equivariant separation, caveats. Remove verbose provenance hashes. | The \(84\)-neighborhood refinement table, showing the witness pair and nearby repeated-local fibers. |
| II.4 | `node_certification_84_84a` | Section 6.4 | Main, essential | Distinguishes verified block scheme status from open node promotion. | Retain degree, reducedness, line restrictions, block status, ordinary-node status. Remove duplicate script metadata. | Certification status for the \(84/84a\) verified degree-112 block schemes and open ordinary-node promotion. |
| II.5 | `block_evaluation_comparison_84_84a` | Section 7.3 | Main, essential | Gives \(H_B(8)=105\), evaluation rank, and deficiency \(7\). | Retain degree, \(H_B(8)\), rank, cokernel/deficiency, theorem status. Remove redundant Hilbert coefficients if Figure II.4 is adjacent. | Critical-degree verified block-evaluation comparison for \(84\) and \(84a\). |
| II.6 | `source_block_evaluation_comparison_84_84a` | Section 8.2 | Main, centerpiece | Shows integral source separation and block-evaluation equality in one table. | Retain local/Hodge/rational/integral source fields and block-evaluation fields. Remove internal evidence paths. | Source separation versus block-evaluation collapse on the \(84/84a\) witness pair. |
| II.7 | `final_evidence_status_matrix` | Section 9.5 | Main if space allows; appendix if page pressure | Enforces the paper's proved/certified/conditional/open status firewall. | Retain claim, status, evidence, nonclaim note. Remove long machine identifiers. | Final HodgeCY II evidence and claim-status matrix. |

## Redundancy Assessment

Figure II.5 is the only figure that should normally move to the supplement:
Figure II.4 already shows the shared Hilbert profile, and Figure II.6 gives the
main source-versus-block comparison.  Table II.7 should remain in the main text
unless the page limit is strict, because the claims firewall is central to the
paper's correctness.

## Caption Rules

- Captions must say "verified block scheme" when referring to the degree-112
  finite schemes.
- Captions must not identify block-evaluation deficiency with classical nodal
  defect.
- Captions must not imply ordinary-node promotion.
- Captions must not imply that the 114 source-level sets have all been
  geometrically analyzed.
