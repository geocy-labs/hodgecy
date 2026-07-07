"""
Exact verification over Q: for each arrangement, the subspace of degree-8 forms
  S = Q*H^0(O(4)) + sum_i (A/P_i)*H^0(O(1))   (35 + 32 = 67 spanning forms)
inside H^0(O(8)) (dim 165) has rank exactly 60.

Combined with:
  (a) every element of S vanishes on the node set Sigma (structural lemma), so
      h^0(I_Sigma(8)) >= 60 over Q, i.e. defect >= 7;
  (b) HF(R/I,8) = 105 at p = 32003 and p = 1000003, so by semicontinuity
      h^0_Q(I_Sigma(8)) <= 60, i.e. defect <= 7;
this proves delta(84) = delta(84a) = 7 over Q.
"""
import sympy as sp
from itertools import combinations_with_replacement
from sympy import Rational

x, y, z, t = sp.symbols('x y z t')
V = (x, y, z, t)

def monomials(deg):
    out = []
    for c in combinations_with_replacement(range(4), deg):
        m = sp.Integer(1)
        for i in c:
            m *= V[i]
        out.append(m)
    return out

MON8 = monomials(8)
IDX8 = {m: k for k, m in enumerate(MON8)}
MON4 = monomials(4)

def coeff_vec(poly):
    p = sp.Poly(sp.expand(poly), *V)
    vec = [Rational(0)] * len(MON8)
    for mono, c in zip(p.monoms(), p.coeffs()):
        m = sp.prod([V[i]**e for i, e in enumerate(mono)])
        vec[IDX8[m]] = Rational(c)
    return vec

Q = x**4 + 2*y**4 + 3*z**4 + 5*t**4 + x*y*z*t

for arr, seventh in (('84', x + y + z + t), ('84a', x + y + z - t)):
    P = [x - t, x + t, y - t, y + t, z - t, z + t, seventh, x + y + z - 3*t]
    A = sp.prod(P)
    rows = []
    for m in MON4:
        rows.append(coeff_vec(Q * m))
    for i in range(8):
        Ai = sp.cancel(A / P[i])
        for l in V:
            rows.append(coeff_vec(Ai * l))
    M = sp.Matrix(rows)
    r = M.rank()
    print(f"arrangement {arr}: spanning forms = {M.rows}, ambient dim = {len(MON8)}, rank = {r}")
    print(f"  => h^0(I_Sigma(8)) >= {r}  => defect >= {r - (165 - 112)}")
