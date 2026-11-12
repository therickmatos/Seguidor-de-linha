import sys, json, os, importlib, math
sys.path.insert(0, '.')
import build as Bd, check, route as R
fps = {f[:-5]: [json.loads(l) for l in open(os.path.join(Bd.ORIG, 'FOOTPRINT', f), encoding='utf-8-sig') if l.strip()] for f in os.listdir(os.path.join(Bd.ORIG, 'FOOTPRINT'))}
from shapely.geometry import LineString, Point
base = [r for r in Bd.pcb]
def attempt(order, vcost):
    R.VIA_COST = vcost
    rows = list(base); extra = []; res = {}
    for net, pin in order:
        cu = check.copper(rows, fps) + extra
        dst = [(L, g) for L, n, g, i in cu if i == f'e238:{pin}']
        src = [(L, g) for L, n, g, i in cu if n == net and i != f'e238:{pin}']
        c = dst[0][1].centroid
        segs, n = R.route(rows, fps, Bd.outer, net, src, dst, (c.x, c.y), extra)
        if not segs: return None
        vias = len(segs) - 1; length = sum(LineString(p).length for L, p in segs if len(p) > 1)
        res[net] = (vias, round(length, 1), segs)
        for i, (L, p) in enumerate(segs):
            if len(p) > 1: extra.append((L, net, LineString(p).buffer(R.W / 2), f'novo-{net}-{i}'))
            if i: 
                for LL in (1, 2): extra.append((LL, net, Point(p[0]).buffer(R.VIA_D / 2), f'via-{net}-{i}'))
    return res
for order in ([('MARK_L2_D8', '12'), ('MARK_R2_D9', '13')], [('MARK_R2_D9', '13'), ('MARK_L2_D8', '12')]):
    for vc in (40, 120, 300):
        r = attempt(order, vc)
        print([o[0] for o in order], 'custo via', vc, '->', None if r is None else {k: v[:2] for k, v in r.items()}, flush=True)
