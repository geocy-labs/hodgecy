from itertools import combinations
import sympy as sp
from collections import Counter
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

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
    E = [(a,b) for a,b in combinations(range(len(p4)),2) if len(pts[p4[a]] & pts[p4[b]])>=2]
    deg = Counter()
    for a,b in E: deg[a]+=1; deg[b]+=1
    return p4, E, deg

fig, axes = plt.subplots(1, 2, figsize=(11, 5.2))
for ax, arr, hi_deg, title in ((axes[0],'84',6,'Arrangement 84: 39 edges, degree sequence $[6,8^9]$'),
                               (axes[1],'84a',9,'Arrangement 84$^a$: 42 edges, degree sequence $[8^6,9^4]$')):
    p4, E, deg = build(arr)
    n = len(p4)
    # place highlighted vertices for clarity: sort so highlighted are spread
    order = sorted(range(n), key=lambda v: (deg[v]!=hi_deg, v))
    pos = {}
    for r,v in enumerate(order):
        ang = 2*math.pi*r/n + math.pi/2
        pos[v] = (math.cos(ang), math.sin(ang))
    for a,b in E:
        ax.plot([pos[a][0],pos[b][0]],[pos[a][1],pos[b][1]], color='#9aa5b1', lw=0.9, zorder=1)
    for v in range(n):
        hot = (deg[v]==hi_deg)
        ax.scatter(*pos[v], s=340 if hot else 240,
                   color='#c0392b' if hot else '#2c6e91',
                   edgecolor='black', linewidth=0.8, zorder=2)
        ax.annotate(str(deg[v]), pos[v], color='white', ha='center', va='center',
                    fontsize=9, fontweight='bold', zorder=3)
    ax.set_title(title, fontsize=10.5)
    ax.set_xlim(-1.28,1.28); ax.set_ylim(-1.28,1.28); ax.set_aspect('equal'); ax.axis('off')
fig.suptitle('$p_4$-collinearity graphs: the non-isomorphism witnesses of Theorem 5.4 (vertex labels = degrees)', fontsize=11)
fig.tight_layout(rect=[0,0,1,0.94])
fig.savefig('p4_collinearity_graphs.pdf', bbox_inches='tight')
fig.savefig('p4_collinearity_graphs.png', dpi=180, bbox_inches='tight')
print('written')
