# Node Relation Complexes

HodgeCY records node relations as an explicit two-term complex

```text
[ C_node -> T ]
```

with `C_node` in homological degree `1`, `T` in degree `0`, and relation
module `ker(rho)`.  The realization map `rho: C_node -> T` must be supplied
with a declared `RelationRealizationKind`; the kind is part of the complex
hash.

## Verified Node Generators

`NodeGeneratorModule` requires an ordered, verified finite node support.  A
scheme degree, an imported expected node count, or a source-assembly generator
set is not enough to certify `C_node`.

Degree-only data are recorded as expected metadata, not as a node generator
module.

## Evaluation-Condition Relations

For an exact critical-degree evaluation matrix

```text
E: QQ^N -> QQ^r
```

represented by an `r x N` matrix with rows indexed by nodes and columns by the
monomial basis, HodgeCY constructs the evaluation-condition relation map as

```text
rho = E^T: QQ^r -> QQ^N
```

Then

```text
dim ker(E^T) = r - rank(E) = dim coker(E)
```

at the critical degree.  If a classical defect value is supplied, it is only a
cross-check for this evaluation construction; it is not promoted to a
vanishing-cycle or exceptional-curve relation.

Point-evaluation construction records the projective point order, normalized
coordinate representatives, variables, and monomial basis.  A quotient-ring or
Hilbert route may certify the rank and relation dimension, but it does not
claim a realized relation matrix unless a supported basis map is available.

## Integral Models

Integral node-relation complexes are constructed only from a verified supplied
integral model.  When such a model is present, HodgeCY uses the Blob 8 integer
lattice engine to record rational rank, Smith normal form, torsion, saturation
index, and the integer kernel.  Without that certificate, integral relation
SNF and torsion remain `UNKNOWN`.

## Firewall

- An evaluation-condition relation is not a vanishing-cycle relation.
- An evaluation-condition relation is not an exceptional-curve relation.
- A source-assembly kernel is not a node-relation lattice.
- Defect rank does not imply a vanishing-cycle relation rank.
- Same rank does not imply same complex.
- Blob 9 does not construct a source-to-node map.
- Blob 9 does not construct conifold or smooth Hodge atoms.

## HodgeCY II 84 / 84a Status

For the current v1.0.0 HodgeCY II corpus, arrangements `84` and `84a` have
imported fixed-parameter singular-scheme degree `112`.  The double-octic
critical-degree rule gives `kcrit = 8` and `N_k = 165`, so the expected shapes
are:

```text
E_8: QQ^165 -> QQ^112
rho = E_8^T: QQ^112 -> QQ^165
```

The actual node generator module, rational evaluation relation complex,
integral evaluation relation complex, vanishing-cycle relation, and
exceptional-curve relation remain `UNKNOWN` because the release does not yet
provide verified complete support, reduced ODP certificates, or an explicit
realization map.
