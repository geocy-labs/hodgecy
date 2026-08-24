# Singular-Scheme and ODP Certification

Blob 5 introduces the first reusable HodgeCY layer for actual node geometry.
It separates four claims that are often conflated in informal double-octic
workflows.

## Singular Scheme

For a homogeneous hypersurface

```text
X = V(F) in P^n
```

HodgeCY forms the projective singular scheme from

```text
F, dF/dx0, ..., dF/dxn
```

The implementation keeps `F` in the generator list. In characteristic zero,
Euler's relation makes `F` redundant under the usual homogeneous hypotheses,
but retaining it makes the convention explicit and avoids depending on an
unstated omission.

Projective computations are handled by affine-chart decomposition. In chart
`x_j != 0`, HodgeCY sets `x_j = 1`, computes the affine singular equations for
the dehomogenized polynomial, and then canonicalizes projective points when
assembling support across charts. The affine origin of the homogeneous cone is
therefore not counted as a projective singular point.

## Four Claim Levels

Candidate points are only a proposed list. They do not prove that the list is
the full singular support.

Pointwise singular verification checks, exactly, that each candidate satisfies
`F = 0` and all first partials vanish. This proves singularity of the listed
points, but not completeness.

A complete finite singular scheme requires a separate support certificate. The
preferred exact pattern is:

```text
zero-dimensional singular scheme
known scheme degree
verified distinct support points
reducedness
```

Only then can degree, support cardinality, and completeness be safely aligned.

Ordinary-double-point certification is a further local claim at each support
point. It is not implied by degree or by candidate verification.

## Affine-Chart Hessian

For a point on a projective hypersurface, HodgeCY does not classify the
homogeneous Hessian directly. The radial projective direction can create the
wrong rank test.

Instead, it chooses a chart containing the point, dehomogenizes `F`, and
computes the Hessian of the local affine equation. For a local equation

```text
f(u1, ..., un) = 0
```

an ordinary double point is certified when:

```text
f(0) = 0
df(0) = 0
rank Hess(f)(0) = n
```

Equivalently, the Hessian determinant is nonzero.

## Double Covers

For a local double-cover model

```text
w^2 = F(u1, u2, u3)
```

HodgeCY records the total-space equation

```text
G(w, u) = w^2 - F(u)
```

and tests the Hessian including the `w` direction. Branch-surface ODP data are
not silently promoted to total-space ODP data; the certificate stores both the
branch classification and the total-space classification.

## Exact Arithmetic

Verified certificates in Blob 5 use exact SymPy arithmetic over `QQ` for the
supported in-repository backend. Approximate numerical roots are not promoted
to `VERIFIED`.

The backend is intentionally small. It supports exact synthetic fixtures,
projective point normalization, chartwise zero-dimensional solving where SymPy
can solve the system, and explicit UNKNOWN states where completeness or
reducedness cannot be certified.

## Fixed vs Generic Parameters

If a model is represented by a family such as

```text
P1 ... P8 + epsilon Q^2
```

Blob 5 records the exact specialization used, such as `epsilon = 1`.
Verification at one fixed nonzero value is not promoted to a generic-parameter
theorem.

## HodgeCY II Status

For arrangements 84 and 84a, the repository contains fixed epsilon smoothing
metadata and imported release facts that the saturated projective Jacobian
scheme has dimension `0` and degree `112`.

The current Blob 5 registry does not contain canonical exact support,
reducedness, affine-chart Hessian, or double-cover total-space ODP certificates
for all 112 points. Consequently, HodgeCY leaves support cardinality,
reducedness, ODP count, double-cover ODP status, and global finite-reduced-ODP
status as `UNKNOWN`.

Arrangements 239, 240, and 241 remain source-level cohort members until exact
supported singular-fiber models are supplied.

## Firewall

Blob 5 does not compute:

```text
node-relation ranks
classical defect
vanishing-cycle relations
source-to-node maps
Picard-Lefschetz data
conifold Hodge atoms
smooth Hodge atoms
```

A verified node count does not imply a node-relation rank. An ODP certificate
does not imply vanishing-cycle independence. A singular-scheme degree does not
become a support cardinality without completeness and reducedness.
