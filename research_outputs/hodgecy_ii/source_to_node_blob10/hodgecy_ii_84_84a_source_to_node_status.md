# HodgeCY II Source-to-Node Status - 84 vs 84a

| Invariant | 84 | 84a | State |
| --- | --- | --- | --- |
| source_d_shape | `[26, 28]` | `[26, 28]` | equal |
| source_rank_Q | `26` | `26` | equal |
| source_H1_rank_Q | `2` | `2` | equal |
| source_H0_rank_Q | `0` | `0` | equal |
| source_H0_Z_torsion | `[2, 6, 12]` | `[2, 4, 4, 4, 12]` | different |
| expected_node_count | `112` | `112` | equal |
| critical_degree | `8` | `8` | equal |
| expected_evaluation_matrix_shape | `[112, 165]` | `[112, 165]` | equal |
| expected_relation_map_shape | `[165, 112]` | `[165, 112]` | equal |
| node_evaluation_H1_rank | `None` | `None` | unknown |
| source_to_evaluation_chain_map | `None` | `None` | unknown |
| source_to_vanishing_chain_map | `None` | `None` | unknown |
| source_to_exceptional_chain_map | `None` | `None` | unknown |
| conditional_defect_feasibility | `[{'condition': 'defect = 0', 'existence_statement': False, 'implication': 'any induced H1 map is zero', 'injective': False, 'target_h1_rank': 0}, {'condition': 'defect = 1', 'existence_statement': False, 'implication': 'injective H1 comparison is impossible', 'injective': False, 'target_h1_rank': 1}, {'condition': 'defect >= 2', 'existence_statement': False, 'implication': 'injectivity is dimensionally possible but not established', 'injective': 'possible', 'target_h1_rank': '>=2'}]` | `[{'condition': 'defect = 0', 'existence_statement': False, 'implication': 'any induced H1 map is zero', 'injective': False, 'target_h1_rank': 0}, {'condition': 'defect = 1', 'existence_statement': False, 'implication': 'injective H1 comparison is impossible', 'injective': False, 'target_h1_rank': 1}, {'condition': 'defect >= 2', 'existence_statement': False, 'implication': 'injectivity is dimensionally possible but not established', 'injective': 'possible', 'target_h1_rank': '>=2'}]` | equal |

First source-to-node status distinction: source_H0_Z_torsion
