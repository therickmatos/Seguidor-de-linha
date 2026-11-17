"""Encontra cantos de trilha (dois segmentos da mesma rede e face se encontrando) com ângulo interno <= 90°."""
import math, collections
from shapely.geometry import Point
import check
M = 0.0254
def corners(rows, fps, tol=1.0):
    ends = collections.defaultdict(list)          # (net, layer, x, y) -> [(row index, 'a'|'b')]
    for k, r in enumerate(rows):
        if r[0] == 'LINE' and r[4] in (1, 2):
            for side, (x, y) in (('a', (r[5], r[6])), ('b', (r[7], r[8]))):
                ends[(r[3], r[4], round(x * M, 3), round(y * M, 3))].append((k, side))
    pads = check.pad_geoms(rows, fps)
    vias = [(r[3], Point(r[5] * M, r[6] * M).buffer(r[8] * M / 2)) for r in rows if r[0] == 'VIA']
    out = []
    for (net, L, x, y), lst in ends.items():
        if len(lst) != 2: continue
        P = Point(x, y)
        if any(n == net and (l == L or l == 12) and g.buffer(1e-3).contains(P) for l, n, g, i in pads): continue
        if any(n == net and g.buffer(1e-3).contains(P) for n, g in vias): continue
        vs = []
        for k, side in lst:
            r = rows[k]
            ox, oy = (r[7], r[8]) if side == 'a' else (r[5], r[6])
            vs.append((ox * M - x, oy * M - y))
        (ax, ay), (bx, by) = vs
        la, lb = math.hypot(ax, ay), math.hypot(bx, by)
        if la < 1e-6 or lb < 1e-6: continue
        ang = math.degrees(math.acos(max(-1, min(1, (ax * bx + ay * by) / (la * lb)))))
        if ang <= 90 + tol:
            out.append(dict(net=net, layer=L, x=x, y=y, ang=round(ang, 1), segs=lst, la=la, lb=lb))
    return out
