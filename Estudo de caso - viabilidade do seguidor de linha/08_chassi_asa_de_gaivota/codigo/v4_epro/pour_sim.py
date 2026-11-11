"""Simula o preenchimento de GND (as duas faces) e confere se todo o GND fica numa peça só."""
import sys, collections
from shapely.ops import unary_union
import verifica_placa as V, check
def sim(path, clr=0.254, edge=0.3):
    rows, fps, outer = V.board(path)
    cu = check.copper(rows, fps); hs = check.holes(rows)
    area = outer.buffer(-edge).difference(unary_union([h.buffer(0.3) for h in hs]))
    comps = []   # (layer, geom)
    for L in (1, 2):
        other = unary_union([g.buffer(clr) for l, n, g, i in cu if l == L and n != 'GND'])
        pour = area.difference(other)
        gnd = unary_union([g for l, n, g, i in cu if l == L and n == 'GND'])
        full = unary_union([pour, gnd])
        for p in getattr(full, 'geoms', [full]):
            if p.area > 0.5: comps.append((L, p))
    # liga peças das duas faces por vias/pads PTH de GND
    n = len(comps); parent = list(range(n))
    def f(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    links = [g for l, nn, g, i in cu if nn == 'GND' and (str(i).startswith('e') and ':' not in str(i) or l == 12)]
    vias = [g for l, nn, g, i in cu if nn == 'GND' and l == 1 and any(g.equals(h) for ll, n2, h, j in cu if ll == 2 and j == i)]
    for v in vias:
        hit = [k for k, (L, p) in enumerate(comps) if p.intersects(v)]
        for a, b in zip(hit, hit[1:]): parent[f(a)] = f(b)
    groups = collections.defaultdict(float)
    for k, (L, p) in enumerate(comps): groups[f(k)] += p.area
    main = max(groups, key=groups.get)
    # pads/vias de GND fora do grupo principal
    lost = []
    for l, nn, g, i in cu:
        if nn != 'GND': continue
        inside = [k for k, (L, p) in enumerate(comps) if L == l and p.intersects(g)]
        if not any(f(k) == main for k in inside): lost.append((l, i, round(g.centroid.x, 2), round(g.centroid.y, 2)))
    return len(groups), lost
for p in ('/home/user/Seguidor-de-linha/ProPrj_RUSH - SATURN - v3_2026-11-09.epro', '/home/user/Seguidor-de-linha/ProPrj_RUSH - SATURN - v4_asa_gaivota_2026-11-11.epro'):
    g, lost = sim(p); print(p.split('/')[-1], 'grupos de cobre GND:', g, '· itens de GND fora do grupo principal:', lost)
