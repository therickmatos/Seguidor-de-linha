import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import epro
from epro import *
CLR = 10.0; EDGE = 20.0
_orig = epro.copper
def copper_sim(proj):
    items = [it for it in _orig(proj) if it[3] != 'pour']
    ol, _ = outline_polygon(proj)
    holes = []
    for r in proj.pcb:
        if r[0] == 'FILL' and r[4] == 12:
            cx, cy, rr = r[7][0][1:4]; holes.append(Point(cx, cy).buffer(rr + CLR, 32))
        if r[0] == 'PAD':
            g = pad_shape(dict(shape=r[10], x=r[6], y=r[7], rot=r[8])); holes.append(g.buffer(CLR))
    for r in proj.pcb:
        if r[0] != 'POUR': continue
        L, net = r[4], r[3]
        x, y, w, h = r[8][0][1:5]
        reg = box(x, y - h, x + w, y).intersection(ol.buffer(-EDGE))
        obst = unary_union([g.buffer(CLR, 8) for (LL, n, g, k, ref) in items if LL == L and n != net] + holes)
        fill = reg.difference(obst)
        for k, poly in enumerate(fill.geoms if hasattr(fill, 'geoms') else [fill]):
            if poly.area > 100: items.append((L, net, poly, 'pour', f'sim{L}_{k}'))
    return items
epro.copper = copper_sim
if __name__ == '__main__':
  exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'drc.py')).read().replace('from epro import *', 'from epro import *\ncopper = copper_sim'))
