# Classical Nodal Defect

Blob 7 introduces the evaluation-map layer used for classical nodal defect
computations.  It deliberately separates three things:

1. a theorem-derived critical degree,
2. an exact evaluation cokernel in that degree, and
3. promotion of that cokernel to a verified classical nodal defect.

## Node Ideal to Evaluation Rank

Let

```text
Sigma in P^3
```

be a finite projective scheme with homogeneous ideal

```text
I_Sigma in S = k[x0,x1,x2,x3].
```

The degree `k` evaluation map is

```text
ev_{Sigma,k}: H^0(P^3,O(k)) -> H^0(Sigma,O_Sigma(k)).
```

The source dimension is

```text
N_k = h^0(P^3,O(k)) = binomial(k+3,3).
```

Blob 6 computes the Hilbert function

```text
H_Sigma(k) = dim_k (S/I_Sigma)_k.
```

For an exact homogeneous finite-scheme ideal, Blob 7 uses

```text
rank(ev_{Sigma,k}) = H_Sigma(k).
```

If the scheme length is `r`, then

```text
dim coker(ev_{Sigma,k}) = r - rank(ev_{Sigma,k}).
```

This cokernel is an evaluation cokernel.  It is not a node-relation lattice, a
source-assembly cokernel, a vanishing-cycle space, or a Hodge atom.

## Explicit Point Matrix

When a complete exact reduced rational point set is available, HodgeCY can also
build the evaluation matrix directly.  Rows are normalized projective points and
columns are a canonical ordered monomial basis of `S_k`.  The matrix rank over
`QQ` cross-checks the Hilbert-function rank.

The generic engine does not require point coordinates when an exact homogeneous
ideal is already available.

## Double-Solid Critical Degree

For the nodal double-solid convention used by Clemens/Cynk, a double cover of
`P^3` branched over a surface of degree `2d` has critical degree

```text
k_crit = 3d - 4.
```

For a double octic,

```text
branch degree = 8
d = 4
k_crit = 8
N_8 = binomial(11,3) = 165.
```

This rule is model-specific.  Blob 7 applies it only to the recorded nodal
double-solid setting: characteristic zero, base `P^3`, cover degree `2`, and an
even positive branch degree.  It is not automatically applied to arbitrary
hypersurfaces, cyclic covers, weighted models, or higher-dimensional varieties.

## Defect Promotion Firewall

For a verified classical nodal defect in the double-solid setting, HodgeCY
requires at least:

- a finite singular scheme,
- complete support,
- reducedness,
- ordinary-node classification,
- an exact node ideal,
- an applicable double-solid model,
- a certified critical-degree rule,
- and an exact evaluation/Hilbert computation.

Without those prerequisites, HodgeCY may record a critical degree or an
evaluation cokernel, but it does not promote the value to verified classical
nodal defect.

## Current 84 / 84a State

The HodgeCY II 84 and 84a records support the double-octic critical-degree
convention:

```text
k_crit = 8
N_8 = 165.
```

Their imported fixed-parameter singular-scheme degree is `112`, but the exact
homogeneous node ideal is still absent from the canonical tracked data.  Thus
the numerical calculation remains pending:

```text
delta = 112 - H_Sigma(8)
      = 112 - rank(ev_{Sigma,8})
```

once a verified reduced 112-node ideal or equivalent certified computation is
available.

Degree `112` alone does not determine `I_Sigma`, `H_Sigma(8)`, or the
evaluation rank.
