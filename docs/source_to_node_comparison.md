# Source-to-Node Comparison Morphisms

the source-to-node comparison layer represents a source-to-node comparison as a certified chain map between
two two-term complexes.  The source complex is

```text
C_src: C1_src --d_src--> C0_src
```

and the node-relation complex is

```text
C_node: C1_node --d_node--> C0_node
```

with a the node-relation layer `RelationRealizationKind`, such as `evaluation_condition`,
`vanishing_cycle`, or `exceptional_curve`.

## The Chain Map

A comparison morphism is the commutative square

```text
C1_src  --d_src-->  C0_src
  | F1                | F0
  v                   v
C1_node --d_node--> C0_node
```

and HodgeCY verifies exactly that

```text
d_node F1 = F0 d_src
```

No approximate residual, matching rank, matching Smith normal form, shared
geometry ID, or shared node count can create this map.

## Induced Homology Maps

The degree-one homology groups are

```text
H1(C_src) = ker(d_src)
H1(C_node) = ker(d_node)
```

Once the square commutes, `F1` sends `ker(d_src)` into `ker(d_node)`, giving

```text
H1(F): H1(C_src) -> H1(C_node)
```

The degree-zero homology groups are cokernels:

```text
H0(C_src) = coker(d_src)
H0(C_node) = coker(d_node)
```

The same square gives a quotient map

```text
H0(F): H0(C_src) -> H0(C_node)
```

Over `QQ`, HodgeCY computes these with exact finite-dimensional linear algebra.
Over `ZZ`, integral quotient behavior is recorded only where an integral source,
target, and comparison map have been supplied; rationalizing an integral-looking
map does not certify a natural integral comparison.

## Dies, Survives, Combines

A source homology class dies precisely when it lies in

```text
ker H1(F)
```

This is a homology-level statement.  It is different from saying a raw source
generator maps to zero at the chain level.

A source class survives when its image in `H1(C_node)` is nonzero.  The
surviving subspace is the image of `H1(F)`.

Source classes combine when distinct source `H1` classes have nonzero images
that become linearly dependent in the target.  HodgeCY records dependency
relations among the mapped source classes as basis-dependent presentations of
an invariant kernel.

## Feasibility Is Not Existence

Rank constraints can rule out properties of a possible comparison.  For
example, over `QQ`, if

```text
dim H1(C_src) > dim H1(C_node)
```

then no injective `H1` comparison can exist.  If

```text
dim H1(C_src) < dim H1(C_node)
```

then no surjective `H1` comparison can exist.

These are necessary constraints only.  They do not assert that a chain map
exists.

## HodgeCY II Status

For HodgeCY II arrangements `84` and `84a`, the source matrices have shape
`26 x 28` and rational rank `26`, so

```text
dim H1(C_src;QQ) = 2
dim H0(C_src;QQ) = 0
```

Their integral source `H0` torsion differs:

```text
84:  2, 6, 12
84a: 2, 4, 4, 4, 12
```

The node/evaluation target still lacks an exact `E_8` matrix and realized
relation complex, so the source-to-evaluation, source-to-vanishing, and
source-to-exceptional comparison morphisms remain `UNKNOWN`.

Conditional rank statements are allowed:

```text
defect = 0  => any induced H1 map is zero
defect = 1  => injective H1 comparison is impossible
defect >= 2 => injectivity is dimensionally possible but not established
```

These statements are not source-to-node maps.
