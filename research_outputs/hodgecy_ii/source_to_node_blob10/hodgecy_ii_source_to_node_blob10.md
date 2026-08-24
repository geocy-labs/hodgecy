# HodgeCY II Source-to-Node Comparison - Blob 10

## Source Complex

| Geometry | d_src Shape | rank_Q | H1_Q | H0_Q | H0_Z torsion |
| --- | --- | --- | --- | --- | --- |
| 239 | `[26, 28]` | `26` | `2` | `0` | `2,4,4,4,12` |
| 240 | `[26, 28]` | `26` | `2` | `0` | `2,6,12` |
| 241 | `[26, 28]` | `24` | `4` | `2` | `3,3,3,3,3` |
| 84 | `[26, 28]` | `26` | `2` | `0` | `2,6,12` |
| 84a | `[26, 28]` | `26` | `2` | `0` | `2,4,4,4,12` |

## Node Complex

| Geometry | Expected Nodes | kcrit | E_k Shape | rho Shape | H1(C_eval) |
| --- | --- | --- | --- | --- | --- |
| 239 | `None` | `None` | `None` | `None` | `UNKNOWN` |
| 240 | `None` | `None` | `None` | `None` | `UNKNOWN` |
| 241 | `None` | `None` | `None` | `None` | `UNKNOWN` |
| 84 | `112` | `8` | `[112, 165]` | `[165, 112]` | `UNKNOWN` |
| 84a | `112` | `8` | `[112, 165]` | `[165, 112]` | `UNKNOWN` |

## Comparison Morphism

| Geometry | Source -> Eval | Source -> Vanishing | Source -> Exceptional |
| --- | --- | --- | --- |
| 239 | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |
| 240 | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |
| 241 | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |
| 84 | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |
| 84a | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |

## 84 / 84a Conditional Rank Constraints
- source H1_Q rank is `2` for both 84 and 84a.
- if defect = 0, any induced H1 map to the evaluation relation is zero.
- if defect = 1, injective H1 comparison is impossible.
- if defect >= 2, injectivity is dimensionally possible but not established.

## Firewall
- Matching dimensions, ranks, SNF, geometry IDs, or node counts do not create a chain map.
- A source-to-evaluation map is not a source-to-vanishing map.
- Rational comparison does not imply integral comparison.
- Feasibility is not existence.
- No Hodge atom is constructed.
