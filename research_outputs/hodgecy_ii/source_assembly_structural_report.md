# HodgeCY II Source Assembly Structural Report

- Corpus release fingerprint: `8bbf1dff732529afb634f4a24c1d250d3e7ff3a54c79cbfd9c3584e4bca1622b`
- Total double-octic presentations: 456
- Exact computed assemblies: 13
- Blocked/unresolved assemblies: 443
- Repeated-local fibers: 7
- Fixed local+Hodge fibers: 3

## Required Questions

| question | answer |
| --- | --- |
| How many of 456 computed? | 13 exact source assemblies are computed; 443 are enumerated but blocked. |
| All repeated local fibers? | 61/451; 78/79; 80/455; 81/454; 82/245/452/453; 83/84/84a/239/240/241; 85/238 |
| Apart from old 84/84a and 239/240/241? | Six other repeated-local fibers appear: 61/451, 78/79, 80/455, 81/454, 82/245/452/453, and 85/238; 83 also joins the 84/84a/239/240/241 local fiber. |
| Where does 83 land? | 83 lands in the repeated-local fiber 83/84/84a/239/240/241, but it has no promoted exact source assembly. |
| What about 452 and 453? | 452 and 453 share the 82/245 local fiber and the same ordinary Hodge signature with each other, but both are blocked by quadratic-field exact coefficient support. |
| What about 61 and 451? | 61 and 451 share local and ordinary Hodge signatures; 61 is parameterized and 451 is a partial/problematic extraction, so neither has a promoted source assembly. |
| Are 84/240 and 84a/239 equivariantly equivalent? | No under the current full equivariant fingerprint. They are integral-collapse/equivariant-separation pairs. |
| Why did the previous report say 2 cases? | The two cases are exactly 84/240 and 84a/239: same integral type, different equivariant type. |
| Hodge-shift relation? | The 78-85 and 238-245/451-455 rows show repeated local inventories can preserve Euler while shifting h11/h12; the output TSV records exact adjacent deltas. |
| Sequence relationships? | The graph JSON records repeated-local edges among the seven fibers only; it does not assert geometry identity or a proven specialization morphism. |
| Torsion primes? | Computed source assemblies show torsion at primes 2, 3, and 5; 241 is pure 3-primary in the computed subset. |
| Recurrent source types? | 10 recurrent type rows are emitted across local/rational/integral/equivariant levels. |
| Simplest combinatorial predictors? | Local inventory predicts the seven broad repeated fibers; rank, Smith data, and orbit sizes split the computed members further. |
| New structure? | The main new structure is a full 456-row computability frontier plus the explicit reconciliation that the apparent equivariant recurrences are integral recurrences with equivariant separation. |

## Hodge Shift Rows

| sequence_index | arrangement_id | requested_fiber | hodge_signature | delta_h12_from_previous_sequence | delta_h11_from_previous_sequence | delta_euler_from_previous_sequence | assembly_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 78 | 78/79 | h12=3;h11=35;euler=64 |  |  |  | blocked_parameterized_family_requires_specialization |
| 2 | 79 | 78/79 | h12=4;h11=36;euler=64 | 1 | 1 | 0 | blocked_parameterized_family_requires_specialization |
| 3 | 80 | 80/455 | h12=3;h11=37;euler=68 | -1 | 1 | 4 | blocked_parameterized_family_requires_specialization |
| 4 | 81 | 81/454 | h12=2;h11=38;euler=72 | -1 | 1 | 4 | blocked_parameterized_family_requires_specialization |
| 5 | 82 | 82/245/452/453 | h12=1;h11=39;euler=76 | -1 | 1 | 4 | blocked_parameterized_family_requires_specialization |
| 6 | 83 | 83/84/84a/239/240/241 | h12=1;h11=41;euler=80 | 0 | 2 | 4 | blocked_parameterized_family_requires_specialization |
| 7 | 84 | 83/84/84a/239/240/241 | h12=0;h11=40;euler=80 | -1 | -1 | 0 | computed_exact_two_stratum_source_assembly |
| 8 | 84a | 83/84/84a/239/240/241 | h12=0;h11=40;euler=80 | 0 | 0 | 0 | computed_exact_two_stratum_source_assembly |
| 9 | 85 | 85/238 | h12=0;h11=44;euler=88 | 0 | 4 | 8 | blocked_parameterized_family_requires_specialization |
| 10 | 238 | 85/238 |  |  |  |  | computed_exact_two_stratum_source_assembly |
| 11 | 239 | 83/84/84a/239/240/241 |  |  |  |  | computed_exact_two_stratum_source_assembly |
| 12 | 240 | 83/84/84a/239/240/241 |  |  |  |  | computed_exact_two_stratum_source_assembly |
| 13 | 241 | 83/84/84a/239/240/241 |  |  |  |  | computed_exact_two_stratum_source_assembly |
| 14 | 245 | 82/245/452/453 |  |  |  |  | computed_exact_two_stratum_source_assembly |
| 15 | 451 | 61/451 | h12=0;h11=46;euler=92 |  |  |  | blocked_partial_or_problematic_source_extraction |
| 16 | 452 | 82/245/452/453 | h12=0;h11=38;euler=76 | 0 | -8 | -16 | blocked_exact_quadratic_field_coefficients_not_supported |
| 17 | 453 | 82/245/452/453 | h12=0;h11=38;euler=76 | 0 | 0 | 0 | blocked_exact_quadratic_field_coefficients_not_supported |
| 18 | 454 | 81/454 | h12=1;h11=37;euler=72 | 1 | -1 | -4 | blocked_parameterized_family_requires_specialization |
| 19 | 455 | 80/455 | h12=2;h11=36;euler=68 | 1 | -1 | -4 | blocked_parameterized_family_requires_specialization |

## Prime-Sensitive Computed Assemblies

| arrangement_id | torsion_primes | rank_mod_p | smith_normal_form_compact |
| --- | --- | --- | --- |
| 1 | [2,3] | {"11":13,"2":11,"3":12,"5":13,"7":13} | 1^11,2,12 |
| 3 | [2,3] | {"11":16,"2":13,"3":15,"5":16,"7":16} | 1^13,2^2,12 |
| 19 | [2,5] | {"11":18,"2":16,"3":18,"5":17,"7":18} | 1^16,2,20 |
| 32 | [2,3] | {"11":20,"2":18,"3":18,"5":20,"7":20} | 1^18,12^2 |
| 69 | [2,3] | {"11":21,"2":20,"3":20,"5":21,"7":21} | 1^20,6 |
| 84 | [2,3] | {"11":26,"2":23,"3":24,"5":26,"7":26} | 1^23,2,6,12 |
| 84a | [2,3] | {"11":26,"2":21,"3":25,"5":26,"7":26} | 1^21,2,4^3,12 |
| 93 | [2,3] | {"11":23,"2":21,"3":22,"5":23,"7":23} | 1^21,4,72 |
| 238 | [2,3] | {"11":20,"2":16,"3":19,"5":20,"7":20} | 1^16,4^3,12 |
| 239 | [2,3] | {"11":26,"2":21,"3":25,"5":26,"7":26} | 1^21,2,4^3,12 |
| 240 | [2,3] | {"11":26,"2":23,"3":24,"5":26,"7":26} | 1^23,2,6,12 |
| 241 | [3] | {"11":24,"2":24,"3":19,"5":24,"7":24} | 1^19,3^5 |
| 245 | [2,3] | {"11":27,"2":24,"3":26,"5":27,"7":27} | 1^24,2^2,12 |
