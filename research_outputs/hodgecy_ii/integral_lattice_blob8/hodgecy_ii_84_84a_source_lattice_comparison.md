# HodgeCY II Source Lattice Comparison - 84 vs 84a

| Invariant | 84 | 84a | State |
| --- | --- | --- | --- |
| matrix_shape | `[26, 28]` | `[26, 28]` | equal |
| rank_Q | `26` | `26` | equal |
| rank_mod_2 | `23` | `21` | different |
| rank_mod_3 | `24` | `25` | different |
| kernel_dim_Q | `2` | `2` | equal |
| cokernel_dim_Q | `0` | `0` | equal |
| integral_kernel_rank | `2` | `2` | equal |
| smith_normal_form | `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 6, 12]` | `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 4, 4, 4, 12]` | different |
| integral_cokernel_decomposition | `{'cokernel_hash': '588ba80a07284453fbb2f4c794dfd0ff0bc97ca03ace71f7d5939266f6576021', 'free_rank': 0, 'is_torsion_free': False, 'matrix_hash': 'aadb98a0ea808384e93cccf56297067e3c1a275694a2193df3ecb0fbf4d1b97d', 'structure': 'Z/2Z + Z/6Z + Z/12Z', 'torsion_invariant_factors': [2, 6, 12], 'torsion_order': 144, 'torsion_primes': [2, 3]}` | `{'cokernel_hash': '494b2b0cc247a0e646cdc7941ef1092a238243a8ca45bbeb126edd0be52c47cb', 'free_rank': 0, 'is_torsion_free': False, 'matrix_hash': '3955adb4ddcd1305e4bf917959bf281f9beb728db0d3a109af52c5d7caacf862', 'structure': 'Z/2Z + Z/4Z + Z/4Z + Z/4Z + Z/12Z', 'torsion_invariant_factors': [2, 4, 4, 4, 12], 'torsion_order': 1536, 'torsion_primes': [2, 3]}` | different |
| cokernel_structure | `{'cokernel_hash': '588ba80a07284453fbb2f4c794dfd0ff0bc97ca03ace71f7d5939266f6576021', 'free_rank': 0, 'is_torsion_free': False, 'matrix_hash': 'aadb98a0ea808384e93cccf56297067e3c1a275694a2193df3ecb0fbf4d1b97d', 'structure': 'Z/2Z + Z/6Z + Z/12Z', 'torsion_invariant_factors': [2, 6, 12], 'torsion_order': 144, 'torsion_primes': [2, 3]}` | `{'cokernel_hash': '494b2b0cc247a0e646cdc7941ef1092a238243a8ca45bbeb126edd0be52c47cb', 'free_rank': 0, 'is_torsion_free': False, 'matrix_hash': '3955adb4ddcd1305e4bf917959bf281f9beb728db0d3a109af52c5d7caacf862', 'structure': 'Z/2Z + Z/4Z + Z/4Z + Z/4Z + Z/12Z', 'torsion_invariant_factors': [2, 4, 4, 4, 12], 'torsion_order': 1536, 'torsion_primes': [2, 3]}` | different |
| saturation_index | `144` | `1536` | different |
| matrix_hash | `aadb98a0ea808384e93cccf56297067e3c1a275694a2193df3ecb0fbf4d1b97d` | `3955adb4ddcd1305e4bf917959bf281f9beb728db0d3a109af52c5d7caacf862` | different |

First source-lattice distinction: rank_mod_2
