# Node-Scheme Defect Critical Degree

The decisive next computation for the smoothing-bridge examples is the
classical defect of the node scheme in the critical degree where the nodes fail
to impose independent conditions.

At present, HodgeCY does **not** hardcode that degree. It must be verified from
the relevant Clemens, Werner, van Straten, and Cynk literature before the final
CAS computation is treated as authoritative.

This matters conceptually because HodgeCY interprets the classical defect as
the coarse numerical shadow of flexible Hodge atom compression. If the degree is
misidentified, then the numerical defect comparison is compromised at the first
step.

Once the critical degree is verified from the literature, the Macaulay2 and
Singular templates for the smoothing-bridge node scheme should be updated so
that the queue can move from `not_computed` to a real CAS-backed computation
path.
