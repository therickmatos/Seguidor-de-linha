"""Gargalo de largura (caminho mais largo) nas redes de potência e capacidade por IPC-2221 (cobre 1 oz, externo)."""
import sys, os, math, heapq, collections
from shapely.strtree import STRtree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verifica_placa as V, check
M = 0.0254
PLAT = 0.7          # parede do furo (~25 µm) / cobre externo (35 µm)
def ipc_amp(w_mm, dT=20, oz=1.0):
    A = w_mm / 0.0254 * 1.378 * oz            # mil²
    return 0.048 * dT ** 0.44 * A ** 0.725
def items(rows, fps, net):
    out = []   # (layers, geom, cap_mm, desc)
    for l, n, g, i in check.pad_geoms(rows, fps):
        if n == net: out.append(({l}, g, 99.0, str(i)))
    # passagem de face pelos pads PTH: limitada pela parede do furo
    holes = {}
    comp = {r[1]: r for r in rows if r[0] == 'COMPONENT'}
    for r in rows:
        if r[0] == 'LINE' and r[3] == net and r[4] in (1, 2):
            from shapely.geometry import LineString
            out.append(({r[4]}, LineString([(r[5] * M, r[6] * M), (r[7] * M, r[8] * M)]).buffer(r[9] * M / 2), r[9] * M,
                        f"trilha {r[1]} face {r[4]} {r[9]*M:.2f} mm ({r[5]*M:.1f};{r[6]*M:.1f})→({r[7]*M:.1f};{r[8]*M:.1f})"))
        if r[0] == 'VIA' and r[3] == net:
            from shapely.geometry import Point
            out.append(({1, 2}, Point(r[5] * M, r[6] * M).buffer(r[8] * M / 2), math.pi * r[7] * M * PLAT,
                        f"via {r[1]} {r[8]*M:.1f}/{r[7]*M:.1f} em ({r[5]*M:.1f};{r[6]*M:.1f})"))
    return out
def merge_pth(its, rows, fps):
    # pads PTH aparecem uma vez por face com o mesmo id: liga as duas faces pela parede do furo
    byid = collections.defaultdict(list)
    for k, (ls, g, c, d) in enumerate(its): byid[d].append(k)
    extra = []
    for d, ks in byid.items():
        if len(ks) == 2 and ':' in d: extra.append((ks[0], ks[1]))
    return extra
def widest(its, extra, src, dst):
    n = len(its)
    tree = STRtree([g for ls, g, c, d in its])
    adj = collections.defaultdict(list)
    for a in range(n):
        for b in tree.query(its[a][1]):
            if b != a and (its[a][0] & its[b][0]) and its[a][1].intersects(its[b][1]): adj[a].append(b)
    for a, b in extra:
        adj[a].append(b); adj[b].append(a)
    best = {s: its[s][2] for s in src}; prev = {}
    pq = [(-best[s], s) for s in src]; heapq.heapify(pq)
    while pq:
        c, a = heapq.heappop(pq); c = -c
        if c < best.get(a, -1): continue
        for b in adj[a]:
            cb = min(c, its[b][2])
            if cb > best.get(b, -1): best[b] = cb; prev[b] = a; heapq.heappush(pq, (-cb, b))
    t = max(dst, key=lambda k: best.get(k, -1))
    path = [t]
    while path[-1] in prev: path.append(prev[path[-1]])
    return best.get(t, 0), [its[k][3] for k in path[::-1]], sorted(set((round(its[k][2], 2), its[k][3]) for k in path))[:3]
if __name__ == '__main__':
    P = sys.argv[1]
    rows, fps, outer = V.board(P)
    comp = {r[1]: r for r in rows if r[0] == 'COMPONENT'}
    des = {r[3]: r[8] for r in rows if r[0] == 'ATTR' and r[3] in comp and r[7] == 'Designator'}
    inv = {v: k for k, v in des.items()}
    def ids(its, d, pin): return [k for k, (ls, g, c, dd) in enumerate(its) if dd == f'{inv[d]}:{pin}']
    casos = [('VBAT', ('J1', '1'), [('U3', '11')], 'bateria → driver esquerdo (U3 VM)'),
             ('VBAT', ('J1', '1'), [('U4', '11')], 'bateria → driver direito (U4 VM)'),
             ('VBAT', ('J1', '1'), [('M3', '1')], 'bateria → ventoinha (M3 +)'),
             ('OUT_A1', ('U3', '8'), [('M1', '2')], 'U3 → motor esquerdo (OUT_A1)'),
             ('OUT_A2', ('U3', '10'), [('M1', '1')], 'U3 → motor esquerdo (OUT_A2)'),
             ('OUT_B1', ('U4', '8'), [('M2', '2')], 'U4 → motor direito (OUT_B1)'),
             ('OUT_B2', ('U4', '10'), [('M2', '1')], 'U4 → motor direito (OUT_B2)'),
             ('OUT_C', ('M3', '2'), [('Q1', '3')], 'ventoinha − → AO3400 dreno (OUT_C)')]
    for net, (sd, sp), dsts, txt in casos:
        its = items(rows, fps, net); extra = merge_pth(its, rows, fps)
        src = ids(its, sd, sp); dst = [k for d, p in dsts for k in ids(its, d, p)]
        w, path, worst = widest(its, extra, src, dst)
        print(f"{txt}: gargalo {w:.2f} mm → {ipc_amp(w, 10):.1f} A (ΔT 10 °C) / {ipc_amp(w, 20):.1f} A (ΔT 20 °C)")
        for c, d in worst: print(f"     {c:.2f} mm  {d}")
