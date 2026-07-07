"""
Gate 2 setup: exact verification of genericity conditions (G1)-(G2) for the
smoothing bridge F_eps = P1...P8 + eps*Q^2 on Cynk-Meyer arrangements 84, 84a.

(G1) Q avoids all multiple points of the arrangement.
(G2) Q meets every double line transversely (Q|_L is a binary quartic with
     4 distinct roots, i.e. nonzero discriminant).

All arithmetic exact over Q (sympy Rational / polynomial resultants).
"""
from itertools import combinations
import sympy as sp

x, y, z, t = sp.symbols('x y z t')
s, u_ = sp.symbols('s u_')  # line parameters

# Planes as linear forms
def planes(arr):
    base = [x - t, x + t, y - t, y + t, z - t, z + t]
    if arr == '84':
        return base + [x + y + z + t, x + y + z - 3*t]
    elif arr == '84a':
        return base + [x + y + z - t, x + y + z - 3*t]
    raise ValueError(arr)

# Candidate quartic (from the working session)
Q = x**4 + 2*y**4 + 3*z**4 + 5*t**4 + x*y*z*t

def normal(f):
    return sp.Matrix([f.coeff(v) for v in (x, y, z, t)])

def line_param(f1, f2):
    """Return a rational parametrization p(s,u_) (projective, degree 1) of P_i ∩ P_j."""
    M = sp.Matrix.hstack(normal(f1), normal(f2)).T  # 2x4
    ns = M.nullspace()
    assert len(ns) == 2
    a, b = ns
    return [sp.simplify(a[k]*s + b[k]*u_) for k in range(4)]

def multiple_points(P):
    """All points where >=3 planes meet; return dict point(tuple of Rationals, normalized) -> multiplicity."""
    pts = {}
    for i, j, k in combinations(range(8), 3):
        M = sp.Matrix.vstack(normal(P[i]).T, normal(P[j]).T, normal(P[k]).T)
        if M.rank() == 3:
            ns = M.nullspace()
            v = ns[0]
            # normalize: first nonzero coord = 1
            piv = next(c for c in v if c != 0)
            v = tuple(sp.Rational(c/piv) for c in v)
            if v not in pts:
                mult = sum(1 for f in P if sp.simplify(
                    f.subs({x: v[0], y: v[1], z: v[2], t: v[3]})) == 0)
                pts[v] = mult
    return pts

for arr in ('84', '84a'):
    P = planes(arr)
    mp = multiple_points(P)
    from collections import Counter
    mult_counts = Counter(mp.values())
    print(f"\n=== Arrangement {arr} ===")
    print(f"multiple points: {len(mp)}  by multiplicity: {dict(sorted(mult_counts.items()))}")

    # (G1): Q nonzero at every multiple point
    g1_fail = []
    for v in mp:
        val = Q.subs({x: v[0], y: v[1], z: v[2], t: v[3]})
        if sp.simplify(val) == 0:
            g1_fail.append(v)
    print(f"(G1) Q avoids all multiple points: {'PASS' if not g1_fail else 'FAIL ' + str(g1_fail)}")

    # Double lines: all C(8,2)=28 pairs (l3=0 so none contained in a 3rd plane; verify)
    g2_fail = []
    triple_line = False
    for i, j in combinations(range(8), 2):
        M = sp.Matrix.hstack(normal(P[i]), normal(P[j])).T
        # check no third plane contains the line
        for k in range(8):
            if k in (i, j):
                continue
            if sp.Matrix.vstack(M, normal(P[k]).T).rank() == 2:
                triple_line = True
        param = line_param(P[i], P[j])
        Ql = sp.expand(Q.subs({x: param[0], y: param[1], z: param[2], t: param[3]}))
        # binary quartic in (s,u_); check squarefree: discriminant of dehomogenization nonzero
        # and no common factor issues: check gcd(Ql, dQl/ds, dQl/du_) is constant
        g = sp.gcd(sp.gcd(Ql, sp.diff(Ql, s)), sp.diff(Ql, u_))
        if g.free_symbols:
            g2_fail.append((i, j, sp.factor(Ql)))
        # also check Ql is genuinely degree 4 in the line (not identically lower)
        if sp.total_degree(sp.Poly(Ql, s, u_)) != 4:
            g2_fail.append((i, j, 'degree drop'))
    print(f"l3 = 0 (no triple lines): {'PASS' if not triple_line else 'FAIL'}")
    print(f"(G2) Q|_L squarefree of degree 4 on all 28 double lines: "
          f"{'PASS' if not g2_fail else 'FAIL ' + str(g2_fail[:3])}")
