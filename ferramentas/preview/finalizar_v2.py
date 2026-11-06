"""Finalizador: liga ligacoes que o FreeRouting deixou abertas (A* em grade, duas faces).

Grade de 0,1 mm; cada celula livre fica a pelo menos folga + meia largura (+ margem de
discretizacao) de todo cobre de outras redes, furos e borda. Troca de face por via.
O resultado passa depois pelo mesmo verificador de folgas e conectividade do rotear_v2.

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import heapq
import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

import layout_placa as M

STEP = 0.1
X0, X1, Y0, Y1 = -75.0, 75.0, -36.0, 26.5
NX = int(round((X1 - X0) / STEP)) + 1
NY = int(round((Y1 - Y0) / STEP)) + 1
MARGIN = 0.08


def _cells(geom):
    """Indices (iy, ix) das celulas cujo centro esta dentro de geom."""
    x0, y0, x1, y1 = geom.bounds
    ix0 = max(0, int(math.floor((x0 - X0) / STEP)))
    ix1 = min(NX - 1, int(math.ceil((x1 - X0) / STEP)))
    iy0 = max(0, int(math.floor((y0 - Y0) / STEP)))
    iy1 = min(NY - 1, int(math.ceil((y1 - Y0) / STEP)))
    if ix1 < ix0 or iy1 < iy0:
        return None
    xs = X0 + STEP * np.arange(ix0, ix1 + 1)
    ys = Y0 + STEP * np.arange(iy0, iy1 + 1)
    gx, gy = np.meshgrid(xs, ys)
    inside = shapely.contains_xy(geom, gx, gy)
    return iy0, ix0, inside


def _mark(grid, geom):
    r = _cells(geom)
    if r is None:
        return
    iy0, ix0, inside = r
    h, w = inside.shape
    grid[iy0:iy0 + h, ix0:ix0 + w] |= inside


def route(objs, net, group_a, group_b, width=0.25, clear=0.2, edge=0.3, via_d=0.6, via_cost=25.0):
    """objs: copper_objects (sem planos). group_a/b: nomes de pads (REF.pino) de dois grupos da rede.

    Devolve (trilhas, vias) ou None.
    """
    hw = width / 2
    blocked = {1: np.zeros((NY, NX), bool), 2: np.zeros((NY, NX), bool)}
    via_block = np.zeros((NY, NX), bool)
    # fora da placa / furos
    outside = shapely.geometry.box(X0 - 1, Y0 - 1, X1 + 1, Y1 + 1).difference(M.BOARD)
    for layer in (1, 2):
        _mark(blocked[layer], outside.buffer(edge + hw + MARGIN))
    _mark(via_block, outside.buffer(edge + via_d / 2 + MARGIN))
    own = {1: [], 2: []}
    for o in objs:
        if o['net'] == net:
            for l in o['layers']:
                own[l].append(o)
            continue
        g_tr = o['geom'].buffer(clear + hw + MARGIN, quad_segs=6)
        g_via = o['geom'].buffer(clear + via_d / 2 + MARGIN, quad_segs=6)
        for l in o['layers']:
            _mark(blocked[l], g_tr)
        _mark(via_block, g_via)
    # pads da propria rede tambem nao recebem via (via em pad SMD)
    for l in (1, 2):
        for o in own[l]:
            if o['pad']:
                _mark(via_block, o['geom'].buffer(via_d / 2 + 0.05))
    # grupos de cobre da rede: celulas de origem e destino
    def group_geom(names):
        geoms = {1: [], 2: []}
        names = set(names)
        # cobre da rede que encosta nos pads do grupo (componente conexa)
        seeds = [o for l in (1, 2) for o in own[l] if o['pad'] in names]
        comp = {id(o): o for o in seeds}
        changed = True
        allown = [o for l in (1, 2) for o in own[l]]
        while changed:
            changed = False
            for o in allown:
                if id(o) in comp:
                    continue
                for c in list(comp.values()):
                    if o['layers'] & c['layers'] and o['geom'].distance(c['geom']) < 0.001:
                        comp[id(o)] = o
                        changed = True
                        break
        for o in comp.values():
            for l in o['layers']:
                geoms[l].append(o['geom'])
        return {l: unary_union(g) if g else None for l, g in geoms.items()}
    ga, gb = group_geom(group_a), group_geom(group_b)
    src = {l: np.zeros((NY, NX), bool) for l in (1, 2)}
    dst = {l: np.zeros((NY, NX), bool) for l in (1, 2)}
    for l in (1, 2):
        if ga[l] is not None:
            _mark(src[l], ga[l].buffer(-0.05) if ga[l].buffer(-0.05).area > 0 else ga[l])
        if gb[l] is not None:
            _mark(dst[l], gb[l].buffer(-0.05) if gb[l].buffer(-0.05).area > 0 else gb[l])
        src[l] &= ~blocked[l] | src[l]
    # A* (Dijkstra com heuristica octil ate o centro do destino)
    tgt = [np.argwhere(dst[l]) for l in (1, 2)]
    tcells = np.vstack([t for t in tgt if len(t)]) if any(len(t) for t in tgt) else None
    if tcells is None:
        return None
    ty, tx = tcells.mean(axis=0)
    INF = np.float32(1e18)
    g = np.full((2, NY, NX), INF, np.float32)
    parent = np.full((2, NY, NX), -1, np.int64)
    heap = []
    for li, l in enumerate((1, 2)):
        for iy, ix in np.argwhere(src[l]):
            g[li, iy, ix] = 0
            heapq.heappush(heap, (0.0, li, int(iy), int(ix)))
    free = [~blocked[1] | src[1] | dst[1], ~blocked[2] | src[2] | dst[2]]
    vok = ~via_block
    moves = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
             (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
    found = None
    while heap:
        f, li, iy, ix = heapq.heappop(heap)
        gc = g[li, iy, ix]
        if dst[(1, 2)[li]][iy, ix]:
            found = (li, iy, ix)
            break
        h0 = f - gc
        for dy, dx, c in moves:
            ny, nx = iy + dy, ix + dx
            if 0 <= ny < NY and 0 <= nx < NX and free[li][ny, nx]:
                ng = gc + c * (1.0 if li == 0 else 1.15)
                if ng < g[li, ny, nx]:
                    g[li, ny, nx] = ng
                    parent[li, ny, nx] = (li * NY + iy) * NX + ix
                    dd = abs(ny - ty), abs(nx - tx)
                    hh = max(dd) + 0.4142 * min(dd)
                    heapq.heappush(heap, (ng + hh, li, ny, nx))
        if vok[iy, ix]:
            lj = 1 - li
            if free[lj][iy, ix]:
                ng = gc + via_cost
                if ng < g[lj, iy, ix]:
                    g[lj, iy, ix] = ng
                    parent[lj, iy, ix] = (li * NY + iy) * NX + ix
                    heapq.heappush(heap, (ng + (f - gc), lj, iy, ix))
    if found is None:
        return None
    # reconstroi
    path = []
    li, iy, ix = found
    while True:
        path.append((li, iy, ix))
        p = parent[li, iy, ix]
        if p < 0:
            break
        li, rem = divmod(int(p), NY * NX)
        iy, ix = divmod(rem, NX)
    path.reverse()
    tracks, vias = [], []
    cur = [path[0]]
    for a, b in zip(path, path[1:]):
        if a[0] != b[0]:
            vias.append([X0 + STEP * a[2], Y0 + STEP * a[1]])
            tracks.append(cur)
            cur = [b]
        else:
            cur.append(b)
    tracks.append(cur)
    out = []
    for seg in tracks:
        if len(seg) < 2:
            continue
        pts = [(X0 + STEP * c[2], Y0 + STEP * c[1]) for c in seg]
        # simplifica pontos colineares
        simp = [pts[0]]
        for i in range(1, len(pts) - 1):
            d1 = (round((pts[i][0] - simp[-1][0]) / STEP), round((pts[i][1] - simp[-1][1]) / STEP))
            d2 = (round((pts[i + 1][0] - pts[i][0]) / STEP), round((pts[i + 1][1] - pts[i][1]) / STEP))
            n1 = math.gcd(abs(d1[0]), abs(d1[1])) or 1
            n2 = math.gcd(abs(d2[0]), abs(d2[1])) or 1
            if (d1[0] // n1, d1[1] // n1) != (d2[0] // n2, d2[1] // n2):
                simp.append(pts[i])
        simp.append(pts[-1])
        out.append({'layer': (1, 2)[seg[0][0]], 'xy': [list(p) for p in simp]})
    return out, vias
