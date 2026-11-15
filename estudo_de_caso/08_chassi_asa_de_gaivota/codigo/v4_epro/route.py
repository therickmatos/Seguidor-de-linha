"""Roteador A* em grade (2 faces + vias) para as redes que faltam na v4.

Obstáculos: cobre de outras redes (folga CLR + meia largura), borda (EDGE) e furos
não metalizados. Depois do A*, o caminho é "esticado" (linha de visada) em cada face.
"""
import heapq, math
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Point, LineString
from shapely.ops import unary_union
import check
RES = 0.1
CLR = 0.24          # folga usada na grade (regra da placa: 0,2 mm; sobra para a discretização)
W = 0.2            # largura da trilha (JLC: mín. 0,127)
VIA_D, VIA_HOLE = 0.6, 0.3
EDGE, HOLE = 0.45, 0.35
VIA_COST = 40       # em células (= 4 mm)
X0, Y0, X1, Y1 = -90.0, -36.0, 90.0, 27.0
NX, NY = int((X1 - X0) / RES) + 1, int((Y1 - Y0) / RES) + 1
def to_px(x, y): return ((x - X0) / RES, (y - Y0) / RES)
def raster(geoms):
    im = Image.new('1', (NX, NY), 0); dr = ImageDraw.Draw(im)
    for g in geoms:
        for p in getattr(g, 'geoms', [g]):
            if p.is_empty: continue
            dr.polygon([to_px(x, y) for x, y in p.exterior.coords], fill=1)
    return np.array(im, dtype=bool)
def masks(rows, fps, outer, net, extra=()):
    cu = check.copper(rows, fps) + list(extra)
    hs = check.holes(rows)
    out = {}
    for L in (1, 2):
        others = [g for l, n, g, i in cu if l == L and n != net]
        out[L] = raster([g.buffer(CLR + W / 2, quad_segs=6) for g in others])
    inside = raster([outer.buffer(-(EDGE + W / 2))])
    insv = raster([outer.buffer(-(EDGE + VIA_D / 2))])
    hole_t = raster([h.buffer(HOLE + W / 2) for h in hs])
    hole_v = raster([h.buffer(HOLE + VIA_D / 2) for h in hs])
    for L in (1, 2): out[L] |= ~inside | hole_t
    allv = [g for l, n, g, i in cu if n != net]
    allv += [g for l, n, g, i in cu if n == net and ':' in str(i)]     # sem via dentro de pads (mesmo da rede)
    viablock = raster([g.buffer(CLR + VIA_D / 2, quad_segs=6) for g in allv]) | ~insv | hole_v
    return out, viablock, cu
def cells_of(geoms):
    m = raster(geoms); ys, xs = np.nonzero(m); return set(zip(xs.tolist(), ys.tolist()))
def astar(block, viablock, starts, goals, goal_xy, penalty=None):
    gx, gy = (goal_xy[0] - X0) / RES, (goal_xy[1] - Y0) / RES
    INF = 1e18
    dist = {}
    pq = []
    for L, (x, y) in starts:
        if not block[L][y, x]:
            dist[(L, x, y)] = 0.0; heapq.heappush(pq, (math.hypot(x - gx, y - gy), 0.0, L, x, y))
    prev = {}
    goalset = set(goals)
    steps = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
    n = 0
    while pq:
        f, d, L, x, y = heapq.heappop(pq)
        if d > dist.get((L, x, y), INF): continue
        n += 1
        if (L, (x, y)) in goalset:
            path = [(L, x, y)]
            while path[-1] in prev: path.append(prev[path[-1]])
            return path[::-1], n
        for dx, dy, c in steps:
            nx_, ny_ = x + dx, y + dy
            if not (0 <= nx_ < NX and 0 <= ny_ < NY) or block[L][ny_, nx_]: continue
            # (sem regra de quina: os pinos do ATmega ficam a 45°; a folga é conferida depois, na geometria exata)
            nd = d + c + (penalty[ny_, nx_] if penalty is not None else 0)
            k = (L, nx_, ny_)
            if nd < dist.get(k, INF):
                dist[k] = nd; prev[k] = (L, x, y)
                heapq.heappush(pq, (nd + math.hypot(nx_ - gx, ny_ - gy), nd, L, nx_, ny_))
        if not viablock[y, x]:
            L2 = 3 - L; k = (L2, x, y); nd = d + VIA_COST
            if not block[L2][y, x] and nd < dist.get(k, INF):
                dist[k] = nd; prev[k] = (L, x, y); heapq.heappush(pq, (nd + math.hypot(x - gx, y - gy), nd, L2, x, y))
    return None, n
def clear_line(block, a, b):
    (x0, y0), (x1, y1) = a, b
    n = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 2
    xs = np.rint(np.linspace(x0, x1, n)).astype(int); ys = np.rint(np.linspace(y0, y1, n)).astype(int)
    return not block[ys, xs].any()
def simplify(path, ok):
    """Divide por face e estica cada trecho; ok(L, p, q) testa o segmento na geometria exata."""
    runs = []
    for L, x, y in path:
        P = (X0 + (x + 0.5) * RES, Y0 + (y + 0.5) * RES)
        if runs and runs[-1][0] == L: runs[-1][1].append(P)
        else: runs.append((L, [P]))
    out = []
    for L, pts in runs:
        keep = [pts[0]]; i = 0
        while i < len(pts) - 1:
            lo, hi = i + 1, len(pts) - 1
            j = i + 1
            # maior j com segmento livre (busca de trás para a frente, passo grosso e depois fino)
            for jj in range(hi, i, -max(1, (hi - i) // 40)):
                if ok(L, pts[i], pts[jj]): j = jj; break
            while j + 1 <= hi and ok(L, pts[i], pts[j + 1]): j += 1
            keep.append(pts[j]); i = j
        out.append((L, keep))
    return out
def make_ok(rows, fps, outer, net, extra=(), clr=0.205):
    from shapely.strtree import STRtree
    cu = check.copper(rows, fps) + list(extra)
    hs = check.holes(rows)
    trees = {}
    for L in (1, 2):
        gs = [g for l, n, g, i in cu if l == L and n != net] + [h.buffer(HOLE - clr) for h in hs]
        trees[L] = (STRtree(gs), gs)
    inner = outer.buffer(-(0.3 + W / 2))
    def ok(L, p, q):
        seg = LineString([p, q])
        if not inner.contains(seg): return False
        t, gs = trees[L]
        sb = seg.buffer(W / 2 + clr)
        return not any(gs[k].intersects(sb) for k in t.query(sb))
    return ok
def route(rows, fps, outer, net, src_geoms, dst_geoms, dst_xy, extra=(), avoid=()):
    block, viablock, cu = masks(rows, fps, outer, net, extra)
    penalty = None
    if avoid:     # deixa espaço para a próxima rede: custo extra perto destas geometrias
        penalty = raster([g.buffer(1.4) for g in avoid]).astype(np.float32) * 25
    # mantém distância dos pads de GND para o cobre de GND continuar chegando neles
    gp = [g for l, n, g, i in cu if n == 'GND' and ':' in str(i)]
    pg = raster([g.buffer(1.2) for g in gp]).astype(np.float32) * 8
    penalty = pg if penalty is None else penalty + pg
    starts = [(L, c) for L, g in src_geoms for c in cells_of([g])]
    goals = [(L, c) for L, g in dst_geoms for c in cells_of([g])]
    path, n = astar(block, viablock, starts, goals, dst_xy, penalty)
    if path is None: return None, n
    segs = simplify(path, make_ok(rows, fps, outer, net, extra))
    # pontas: encaixa no centro do pad de destino e no cobre de origem mais próximo
    from shapely.ops import nearest_points
    Ld, gd = next((L, g) for L, g in dst_geoms)
    if segs[-1][0] == Ld: segs[-1][1].append((gd.centroid.x, gd.centroid.y))
    L0 = segs[0][0]; g0 = unary_union([g for L, g in src_geoms if L == L0])
    if not g0.is_empty:
        p = nearest_points(g0, Point(segs[0][1][0]))[0]
        if p.distance(Point(segs[0][1][0])) > 1e-6: segs[0][1].insert(0, (p.x, p.y))
    return segs, n
