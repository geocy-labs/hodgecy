# Smoothing Bridge Local Model

This note records the current Gate 2 local-model scaffolding for the double
octic smoothing bridge
\[
F_{\epsilon} = A + \epsilon Q^2,
\]
where \(A=P_1\cdots P_8\) is the arrangement branch octic and \(Q\) is a
generic quartic.

## Local picture along a double line

Along a double line cut out by two planes, the motivating local model is
\[
xy + \epsilon Q^2.
\]
If the restriction of \(Q\) to the double line is a degree-4 polynomial with
four simple zeros, then the residual singular points are expected at the
intersection of that line with \(\{Q=0\}\).

## What still needs verification

- Each residual singular point should still be checked locally for ordinary
  node type.
- Triple and higher strata require separate analysis and may invalidate the
  naive count.
- The current repository records expected combinatorial counts and genericity
  assumptions, not a completed local analytic proof.

## Current 84 / 84a reading

For arrangements `84` and `84a`, Table 1 records `l3 = 0`, which supports the
expectation of 28 double lines and therefore an expected residual count of 112
nodes under genericity assumptions. CAS computation and local analytic
verification are still required before interpreting these as verified ODPs of
the double cover.
