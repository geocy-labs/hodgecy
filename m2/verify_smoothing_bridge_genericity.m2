-- Exact-rational smoothing verification template for arrangements 84 and 84a.
-- This script is intentionally conservative: it is a CAS follow-up template for
-- projective singular-locus length/reducedness and Hessian-rank checks.
-- Machine-readable output is expected to be written by a local runner once the
-- heavy computation is executed in a verified Macaulay2 environment.

R = QQ[x,y,z,t];

A84 = (x-t)*(x+t)*(y-t)*(y+t)*(z-t)*(z+t)*(x+y+z+t)*(x+y+z-3*t);
A84a = (x-t)*(x+t)*(y-t)*(y+t)*(z-t)*(z+t)*(x+y+z-t)*(x+y+z-3*t);
Q = x^4 + 2*y^4 + 3*z^4 + 5*t^4 + x*y*z*t;

verifyExample = method();
verifyExample String := id -> (
    A := if id == "84" then A84 else A84a;
    F := A + Q^2;
    I := ideal(F, diff(x,F), diff(y,F), diff(z,F), diff(t,F));
    hess = matrix {
        {diff(x,diff(x,F)), diff(x,diff(y,F)), diff(x,diff(z,F)), diff(x,diff(t,F))},
        {diff(y,diff(x,F)), diff(y,diff(y,F)), diff(y,diff(z,F)), diff(y,diff(t,F))},
        {diff(z,diff(x,F)), diff(z,diff(y,F)), diff(z,diff(z,F)), diff(z,diff(t,F))},
        {diff(t,diff(x,F)), diff(t,diff(y,F)), diff(t,diff(z,F)), diff(t,diff(t,F))}
    };
    << "Example " << id << " prepared. Singular ideal and Hessian matrix available.\n";
    << "Projective zero-dimensionality / reducedness / length checks should be run locally and recorded externally.\n";
);

verifyExample "84";
verifyExample "84a";
