import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from epro import *
from shapely.strtree import STRtree
from collections import defaultdict
root = sys.argv[1]
CLR = float(sys.argv[2]) if len(sys.argv) > 2 else 7.8   # mil
p = Proj(root)
ol, _ = outline_polygon(p)
items = copper(p)
# union-find
par = list(range(len(items)))
def f(i):
    while par[i] != i:
        par[i] = par[par[i]]; i = par[i]
    return i
def u(a, b): par[f(a)] = f(b)
geoms = [it[2] for it in items]
tree = STRtree(geoms)
shorts = []; clr = []
for i, (L, net, g, k, ref) in enumerate(items):
    for j in tree.query(g.buffer(CLR)):
        if j <= i: continue
        L2, net2, g2, k2, ref2 = items[j]
        if L2 != L: continue
        d = g.distance(g2)
        if net == net2 and net and d < 1e-3:
            u(i, j)
        elif net != net2:
            if k == 'pour' and k2 == 'pour': continue
            if d < 1e-3: shorts.append((ref, net, ref2, net2, L))
            elif d < CLR - 0.05: clr.append((round(d*MIL, 3), ref, net, ref2, net2, L))
        elif net == net2 and not net and d < 1e-3:
            pass
# same net same object across layers (TH pads, vias): link by ref
byref = defaultdict(list)
for i, it in enumerate(items):
    if it[3] in ('via',) or (it[3] == 'pad'): byref[it[4]].append(i)
for ref, ii in byref.items():
    for a in ii[1:]:
        if items[a][3] == 'via' or True:
            # TH pad appears on both layers with same ref; SMD only once
            u(ii[0], a)
# pads with same ref/num (e.g. thermal pad 17 multiple) connect electrically via component? no - keep separate
nets = defaultdict(list)
for i, it in enumerate(items):
    if it[3] == 'pad' and it[1]: nets[it[1]].append(i)
print('== Redes não conectadas (ilhas de pads):')
bad = 0
for net, ii in sorted(nets.items()):
    groups = defaultdict(set)
    for i in ii: groups[f(i)].add(items[i][4])
    if len(groups) > 1:
        bad += 1
        print(' ', net, ' | '.join(','.join(sorted(s)) for s in groups.values()))
print('  total', bad)
print('== Curtos (cobre de redes diferentes se tocando):')
for s in sorted(set(shorts)): print(' ', s)
print('== Folga < %.3f mm:' % (CLR*MIL))
for s in sorted(set(clr)): print(' ', s)
# outline clearance
print('== Cobre a < 0.3 mm da borda / fora da placa:')
edge = ol.exterior
holes = []
for r in p.pcb:
    if r[0] == 'FILL' and r[4] == 12:
        cx, cy, rr = r[7][0][1:4]; holes.append(Point(cx, cy).buffer(rr, 32))
for L, net, g, k, ref in items:
    if k == 'pour': continue
    d = g.distance(edge)
    if d < 0.3/MIL or not ol.contains(g):
        if k == 'pad' and ref.split('.')[0] in ('J1',): pass
        print('  borda', ref, net, k, L, round(d*MIL, 3))
    for h in holes:
        dh = g.distance(h)
        if dh < 0.3/MIL: print('  furo', ref, net, k, L, round(dh*MIL, 3))
