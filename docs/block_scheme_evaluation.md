# Block-Scheme Evaluation

Blob 13 computes exact degree-8 evaluation invariants for the verified
HodgeCY II block schemes of arrangements `84` and `84a`.

The calculation chain is:

```text
I_B
  -> S/I_B
  -> H_B(d)
  -> E_8
  -> epsilon_B
  -> dim ker(E_8^T)
```

Here `B` is the reduced degree-112 block scheme certified in Blob 12.  The
global saturated node ideal is still not frozen, so the block scheme is used as
an exact finite scheme in its own right.

## Exact Evaluation Route

For each block `B_i = V(l_i,l_j,Q0)` on a double line, Blob 13 uses the exact
line quotient:

```text
QQ[u] / (Q0|_{L_i})
```

and computes the rank of

```text
S_d -> direct_sum_i (S/I_{B_i})_d
```

over `QQ`.  Because Blob 12 certifies the blocks are reduced and pairwise
disjoint, this rank is the Hilbert value `H_B(d)` of the verified block scheme.

At the critical degree from the Clemens/Cynk nodal double-solid rule:

```text
branch degree = 8
d = 4
k_crit = 3d - 4 = 8
N_8 = h^0(P^3, O(8)) = 165
```

the rank identity used is:

```text
rank(E_8) = H_B(8)
```

and the block-scheme evaluation deficiency is:

```text
epsilon_B = 112 - H_B(8).
```

For `84` and `84a`, Blob 13 obtains:

```text
H_B(8) = 105
epsilon_B = 7
dim ker(E_8^T) = 7
```

## Firewall

`epsilon_B` is a verified block-scheme evaluation deficiency.  It is not a
verified classical nodal defect unless the ordinary-node and final node-ideal
prerequisites are also certified.

Blob 13 therefore records:

```text
conditional_classical_defect_value = 7
actual classical_defect = UNKNOWN
```

No integral evaluation relation lattice is manufactured, no source-to-evaluation
morphism is inferred, and no vanishing-cycle, exceptional-curve,
Picard-Lefschetz, or Hodge-atom calculation is performed.
