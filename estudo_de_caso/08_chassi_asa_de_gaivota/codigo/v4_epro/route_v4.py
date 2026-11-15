"""Roteia MARK_L2_D8 e MARK_R2_D9 na v4 (chamado por build.py antes de gravar)."""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check, route as R
from shapely.geometry import LineString, Point
def route_all(Bd, fps, order=(('MARK_L2_D8', '12'), ('MARK_R2_D9', '13')), via_cost=150, verbose=True, reserve=True):
    R.VIA_COST = via_cost
    extra, report = [], {}
    for net, pin in order:
        cu = check.copper(Bd.pcb, fps) + extra
        dst = [(L, g) for L, n, g, i in cu if i == f'e238:{pin}']
        src = [(L, g) for L, n, g, i in cu if n == net and i != f'e238:{pin}']
        c = dst[0][1].centroid
        later = [p for nn, p in order[order.index((net, pin)) + 1:]]
        avoid = [g for L, n, g, i in cu if reserve and i in [f'e238:{p}' for p in later]]
        segs, n = R.route(Bd.pcb, fps, Bd.outer, net, src, dst, (c.x, c.y), extra, avoid)
        if not segs:
            report[net] = None; continue
        for L, p in segs:   # a próxima rede desvia desta
            if len(p) > 1: extra.append((L, net, LineString(p).buffer(R.W / 2), f'nova-{net}'))
        for p in [p[0] for L, p in segs[1:]]:
            for LL in (1, 2): extra.append((LL, net, Point(p).buffer(R.VIA_D / 2), f'via-{net}'))
        prevL = None
        for k, (L, pts) in enumerate(segs):
            if prevL is not None:
                Bd.via(net, *pts[0], d=R.VIA_D, hole=R.VIA_HOLE)
            if len(pts) > 1:
                Bd.line(net, L, pts, R.W)
            prevL = L
        report[net] = dict(vias=len(segs) - 1, comprimento=round(sum(LineString(p).length for L, p in segs if len(p) > 1), 1),
                           trechos=[(L, [(round(x, 2), round(y, 2)) for x, y in p]) for L, p in segs])
        if verbose: print(net, report[net]['vias'], 'vias,', report[net]['comprimento'], 'mm')
    return report
