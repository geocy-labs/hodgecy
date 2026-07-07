from itertools import combinations
import sympy as sp
from collections import Counter

x, y, z, t = sp.symbols('x y z t')

def normal(f): return sp.Matrix([f.coeff(v) for v in (x,y,z,t)])

def build(arr):
    base = [x-t, x+t, y-t, y+t, z-t, z+t]
    P = base + ([x+y+z+t, x+y+z-3*t] if arr=='84' else [x+y+z-t, x+y+z-3*t])
    pts = {}
    for i,j,k in combinations(range(8),3):
        M = sp.Matrix.vstack(normal(P[i]).T, normal(P[j]).T, normal(P[k]).T)
        if M.rank()==3:
            v = M.nullspace()[0]
            piv = next(c for c in v if c!=0); v = tuple(sp.Rational(c/piv) for c in v)
            if v not in pts:
                pts[v] = frozenset(l for l,f in enumerate(P) if sp.simplify(f.subs(dict(zip((x,y,z,t),v))))==0)
    p4 = [v for v,s in pts.items() if len(s)==4]
    # edge iff two p4 points lie on a common double line = share >=2 planes
    E = []
    for a,b in combinations(range(len(p4)),2):
        if len(pts[p4[a]] & pts[p4[b]]) >= 2: E.append((a,b))
    deg = Counter()
    for a,b in E: deg[a]+=1; deg[b]+=1
    return p4, E, sorted(deg.values())

for arr in ('84','84a'):
    p4, E, degs = build(arr)
    print(arr, "p4 points:", len(p4), "edges:", len(E), "degree seq:", degs)
