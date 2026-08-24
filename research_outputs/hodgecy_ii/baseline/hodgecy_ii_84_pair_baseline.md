# HodgeCY II Baseline - 84 vs 84a

| Invariant | Left | Right | State |
| --- | --- | --- | --- |
| h11 | `40` | `40` | equal |
| h12 | `0` | `0` | equal |
| euler | `80` | `80` | equal |
| local_inventory | `{'l3': 0, 'p3': 16, 'p4_0': 10, 'p4_1': 0, 'p5_0': 0, 'p5_1': 0, 'p5_2': 0}` | `{'l3': 0, 'p3': 16, 'p4_0': 10, 'p4_1': 0, 'p5_0': 0, 'p5_1': 0, 'p5_2': 0}` | equal |
| matrix_shape | `[26, 28]` | `[26, 28]` | equal |
| rank_Q | `26` | `26` | equal |
| rank_mod_2 | `23` | `21` | different |
| rank_mod_3 | `24` | `25` | different |
| kernel_dim_Q | `2` | `2` | equal |
| cokernel_dim_Q | `0` | `0` | equal |
| integral_kernel_rank | `2` | `2` | equal |
| integral_cokernel_decomposition | `{'canonical': 'Z/2Z + Z/6Z + Z/12Z', 'free_rank': 0, 'torsion_factors': [2, 6, 12]}` | `{'canonical': 'Z/2Z + (Z/4Z)^3 + Z/12Z', 'free_rank': 0, 'torsion_factors': [2, 4, 4, 4, 12]}` | different |
| smith_normal_form | `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 6, 12]` | `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 4, 4, 4, 12]` | different |
| automorphism_group_order | `6` | `24` | different |
| plane_orbit_sizes | `[1, 1, 3, 3]` | `[4, 4]` | different |
| double_line_orbit_sizes | `[1, 3, 3, 3, 3, 3, 3, 3, 6]` | `[4, 6, 6, 12]` | different |
| multiple_point_orbit_sizes | `[1, 1, 3, 3, 3, 3, 3, 3, 6]` | `[4, 4, 6, 12]` | different |
| character_C1_distribution | `{'1': 2, '28': 1, '8': 3}` | `{'0': 6, '1': 8, '28': 1, '4': 3, '8': 6}` | different |
| character_C0_distribution | `{'2': 2, '26': 1, '8': 3}` | `{'0': 6, '2': 11, '26': 1, '8': 6}` | different |
| node_relation_rank | `None` | `None` | unknown |
| classical_defect | `None` | `None` | unknown |
| conifold_atom_spectrum | `None` | `None` | unknown |

First current available distinction: rank_mod_2
