# HodgeCY II Node Relation Model

Status: unresolved model note.

This file prevents the project from treating every node-related matrix as the
same object.

## Objects currently distinguished

1. `Z<L(A)>`

   The source double-line lattice, rank 28 for 84 and 84a.

2. `Z<P(A)>`

   The source multiple-point lattice, rank 26 for 84 and 84a.

3. `d_A: Z<L(A)> -> Z<P(A)>`

   The source assembly boundary. This is the 26 x 28 source matrix whose ranks
   and Smith forms separate 84 and 84a integrally.

4. `Z<Sigma_A>`

   The formal node lattice for the smoothing bridge. It has rank 112 once the
   28 double-line blocks are expanded into four formal nodes each.

5. `beta_A: Z<L(A)> -> Z<Sigma_A>`

   The formal block expansion. The current implementation gives a 112 x 28
   exact 0/1 matrix with one column per source double line and four rows per
   block. It does not encode vanishing-cycle relations, exceptional-curve
   relations, defect, or Hodge atom extension data.

6. `R_A`

   Placeholder for the actual geometrically justified node relation object.
   It is not yet implemented.

## Candidate exact sequences to audit

- Free node lattice to vanishing-cycle relation lattice.
- Exceptional-curve relation lattice on a small resolution.
- Evaluation map controlling classical defect in the critical degree.
- Mixed-Hodge/perverse extension relation law from the conifold literature.

These may be related, but HodgeCY II must not silently identify them.

## Current computational stance

The only implemented node-side map is the formal beta_A block expansion. It is
safe for block accounting and for testing that every formal node belongs to one
block. It is not sufficient for Hodge realization.

## Next exact tasks

- Ingest or regenerate exact Gate A node certificates.
- Define `R_A` from the conifold relation literature with coefficient ring,
  signs, and exact sequence.
- Only after that, test whether a commutative diagram involving `d_A`,
  `beta_A`, and a geometrically defined `r_A` exists.
