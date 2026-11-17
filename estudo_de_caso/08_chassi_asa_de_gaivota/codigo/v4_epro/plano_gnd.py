"""Simula o 'reconstruir cobre' do GND (duas faces) e agrupa as peças ligadas por vias/pads PTH de GND."""
import collections
from shapely.ops import unary_union
import check
POUR_CLR, POUR_EDGE = 0.35, 0.35   # medido no cobre gravado pelo EasyEDA no v7
def pieces(rows, fps, outer):
    cu = check.copper(rows, fps); hs = check.holes(rows)
    area = outer.buffer(-POUR_EDGE).difference(unary_union([h.buffer(POUR_CLR) for h in hs]))
    pcs = []
    for L in (1, 2):
        other = unary_union([g.buffer(POUR_CLR) for l, n, g, i in cu if l == L and n != 'GND'])
        full = unary_union([area.difference(other).buffer(-0.1).buffer(0.1),
                            unary_union([g for l, n, g, i in cu if l == L and n == 'GND'])])
        pcs += [(L, p) for p in getattr(full, 'geoms', [full]) if p.area > 0.05]
    n = len(pcs); par = list(range(n))
    def f(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    ids = collections.defaultdict(set)
    for l, nn, g, i in cu:
        if nn == 'GND': ids[i].add(l)
    for i, ls in ids.items():
        if ls != {1, 2}: continue
        g = next(g for l, nn, g, j in cu if j == i)
        hit = [k for k, (L, p) in enumerate(pcs) if p.intersects(g)]
        for a, b in zip(hit, hit[1:]): par[f(a)] = f(b)
    tot = collections.defaultdict(float)
    for k, (L, p) in enumerate(pcs): tot[f(k)] += p.area
    main = max(tot, key=tot.get)
    return cu, pcs, f, main
def plot(rows, fps, outer, out, xlim=(-88, 88), ylim=(-35, 27)):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    cu, pcs, f, main = pieces(rows, fps, outer)
    fig, axs = plt.subplots(2, 1, figsize=(20, 14))
    for ax, L in zip(axs, (1, 2)):
        x, y = outer.exterior.xy; ax.plot(x, y, 'k', lw=1)
        for k, (LL, p) in enumerate(pcs):
            if LL != L: continue
            col = '#7c7' if f(k) == main else '#f90'
            xx, yy = p.exterior.xy; ax.fill(xx, yy, color=col, lw=0)
            for h in p.interiors: xx, yy = h.xy; ax.fill(xx, yy, color='w', lw=0)
        for l, n, g, i in cu:
            if l != L or n == 'GND': continue
            for gg in getattr(g, 'geoms', [g]):
                xx, yy = gg.exterior.xy; ax.fill(xx, yy, color='#36c' if L == 1 else '#c80', alpha=0.6, lw=0)
        ax.set_aspect('equal'); ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_title(f'face {L} (verde = GND ligado; laranja = ilha)')
    plt.tight_layout(); plt.savefig(out, dpi=70); plt.close()
