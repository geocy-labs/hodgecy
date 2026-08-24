# HodgeCY II Star-Configuration / Hilbert-Burch Audit

Status: `AUDITED`  
Audit date: `2026-08-24`

## Verified HodgeCY Hypotheses

For both `84` and `84a`, the verifier records:

| condition | value |
| --- | --- |
| pair count | `28` |
| pairwise rank | `2` |
| triple count | `56` |
| triple-rank distribution | `{"3": 56}` |
| no three planes contain a line | `true` |
| higher-order point concurrences | allowed |

## Literature Basis

Geramita, Harbourne, and Migliore, *Star configurations in P^n*, Journal of Algebra 376 (2013), 279-299, DOI `10.1016/j.jalgebra.2012.11.034`, arXiv `1203.5685`.

Relevant audited pieces:

| item | use |
| --- | --- |
| Definition 2.1 | defines star configurations under the properly-meeting hyperplane hypothesis |
| Proposition 2.6 | supplies the basic-double-link construction used in the direct proof |
| Proposition 2.9 | gives ACM/Hilbert/generator data under the proper-meeting hypothesis |

## Hypothesis Mismatch

The full proper-meeting hypothesis is stronger than the verified HodgeCY II hypotheses. In particular, proper meeting rules out higher-order point concurrences that the `84` and `84a` arrangements allow. This mismatch is not hidden and Proposition 2.9 is not used as a black-box theorem for the witness pair.

## Applied Proof Route

The manuscript theorem uses a direct codimension-two proof:

\[
  J_s=\bigcap_{i<j\le s}(L_i,L_j),
  \qquad
  P_s=\prod_{i=1}^sL_i.
\]

The induction step is the basic-double-link identity

\[
  J_s=L_sJ_{s-1}+(P_{s-1}).
\]

Because no three planes contain a line, \(L_s=0\) contains no old line component. This proves

\[
  (F/L_1,\ldots,F/L_8)=\bigcap_{i<j}(L_i,L_j)
\]

under precisely the hypotheses verified for `84` and `84a`. Saturation and reducedness follow from the intersection of distinct line primes. The displayed Hilbert-Burch matrix then gives

\[
  0\to S(-8)^7\to S(-7)^8\to I_C\to0.
\]

Conclusion: `84` and `84a` satisfy every hypothesis used in the manuscript theorem; they do not satisfy the stronger full proper-meeting hypothesis.

