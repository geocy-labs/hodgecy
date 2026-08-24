# Verified Node-Block Geometry

Blob 12 adds a repo-native certificate layer for the predicted node blocks of
the HodgeCY II arrangements `84` and `84a`.

For each arrangement the frozen perturbation is

```text
Q0 = x^4 + 2*y^4 + 3*z^4 + 5*t^4 + x*y*z*t
F_A = A + Q0^2
epsilon = 1
```

The exact block attached to a double line `L_ij = V(l_i,l_j)` is
`B_ij = V(l_i,l_j,Q0)`.  The verifier checks, over `QQ`, that all 28 double
lines have squarefree degree-4 restrictions of `Q0`, so the predicted block
scheme is a reduced disjoint union of degree `28 * 4 = 112`.

The verifier also reduces `F_A` and all four first partial derivatives modulo
each block ideal `(l_i,l_j,Q0)`.  Zero remainder proves the predicted block
scheme is contained in the Jacobian singular scheme.

## Current Promotion Status

The strongest repo-native Blob 12 status is:

```text
exact reduced disjoint degree-112 predicted block scheme with Jacobian containment
```

The ordinary-node promotion remains `UNKNOWN`.  The missing prerequisite is a
reproducible exact certificate for the saturated Jacobian ideal: zero
dimensionality, degree `112`, reducedness, and a frozen final ideal identified
with the predicted block scheme.  Historical Singular output backs the
degree-112 claim, but no exact CAS executable is available in the current
environment to reconstruct and freeze the saturated ideal.

Blob 12 does not compute defect, vanishing cycles, or source-to-node morphisms.
