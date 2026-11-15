"""Acrescenta vias de GND para religar ao plano principal os pads de GND que ficariam isolados no cobre."""
import collections
from shapely.geometry import Point
from shapely.ops import unary_union
import check
def pour_groups(rows, fps, outer, clr=0.254, edge=0.3):
    cu = check.copper(rows, fps); hs = check.holes(rows)
    area = outer.buffer(-edge).difference(unary_union([h.buffer(0.3) for h in hs]))
    comps = []
    for L in (1, 2):
        other = unary_union([g.buffer(clr) for l, n, g, i in cu if l == L and n != 'GND'])
        full = unary_union([area.difference(other), unary_union([g for l, n, g, i in cu if l == L and n == 'GND'])])
        comps += [(L, p) for p in getattr(full, 'geoms', [full]) if p.area > 0.5]
    n = len(comps); par = list(range(n))
    def f(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    for l, nn, g, i in cu:
        if nn == 'GND' and l == 1 and any(j == i for ll, n2, h, j in cu if ll == 2):
            hit = [k for k, (L, p) in enumerate(comps) if p.intersects(g)]
            for a, b in zip(hit, hit[1:]): par[f(a)] = f(b)
    area_of = collections.defaultdict(float)
    for k, (L, p) in enumerate(comps): area_of[f(k)] += p.area
    main = max(area_of, key=area_of.get)
    lost = [(l, i, g) for l, nn, g, i in cu if nn == 'GND' and not any(f(k) == main for k, (L, p) in enumerate(comps) if L == l and p.intersects(g))]
    return comps, f, main, lost
def stitch(Bd, fps, via_d=0.6, via_h=0.3, max_iter=6):
    added = []
    for _ in range(max_iter):
        comps, f, main, lost = pour_groups(Bd.pcb, fps, Bd.outer)
        if not lost: break
        l, i, g = lost[0]
        isl = next(p for k, (L, p) in enumerate(comps) if L == l and p.intersects(g))
        mainp = unary_union([p for k, (L, p) in enumerate(comps) if L == 3 - l and f(k) == main])
        cand = isl.buffer(-via_d / 2 - 0.05).intersection(mainp.buffer(-via_d / 2 - 0.05))
        pads = unary_union([pg for L2, n2, pg, i2 in check.pad_geoms(Bd.pcb, fps)])
        cand = cand.difference(pads.buffer(via_d / 2 + 0.15))      # nada de via dentro de pad
        if cand.is_empty:
            print('sem lugar para via de GND perto de', i); break
        from shapely.ops import nearest_points
        p = nearest_points(cand, g.centroid)[0]
        Bd.via('GND', p.x, p.y, d=via_d, hole=via_h); added.append((i, round(p.x, 2), round(p.y, 2)))
    return added
