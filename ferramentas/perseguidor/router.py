import sys, os, math, heapq; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from epro import *
import numpy as np
from PIL import Image, ImageDraw

RES = 0.1 / MIL   # grid step in mil (0.1 mm)

class Grid:
    def __init__(self, proj, extra_items=(), net=None, width_mil=9.84, clr_mil=8.5, via_d=23.622, edge_clr_mil=15.75, hole_clr_mil=15.75, keepouts=()):
        self.p = proj
        ol, _ = outline_polygon(proj)
        self.ol = ol
        b = ol.bounds
        self.x0, self.y0 = b[0] - 40, b[1] - 40
        self.nx = int((b[2] - b[0] + 80) / RES) + 1
        self.ny = int((b[3] - b[1] + 80) / RES) + 1
        items = [it for it in copper(proj) if it[3] != 'pour'] + list(extra_items)
        holes = []
        for r in proj.pcb:
            if r[0] == 'FILL' and r[4] == 12:
                cx, cy, rr = r[7][0][1:4]; holes.append(Point(cx, cy).buffer(rr, 32))
            if r[0] == 'PAD':   # board-level slots (plated) -> copper both layers
                g = pad_shape(dict(shape=r[10], x=r[6], y=r[7], rot=r[8]))
                items.append((1, '__slot', g, 'pad', r[1])); items.append((2, '__slot', g, 'pad', r[1]))
        self.items = items
        def rast(geoms, buf):
            im = Image.new('1', (self.nx, self.ny), 0); dr = ImageDraw.Draw(im)
            for g in geoms:
                gg = g.buffer(buf, 8)
                for poly in (gg.geoms if hasattr(gg, 'geoms') else [gg]):
                    if poly.is_empty: continue
                    pts = [((x - self.x0) / RES, (y - self.y0) / RES) for x, y in poly.exterior.coords]
                    dr.polygon(pts, fill=1)
            return np.array(im, dtype=bool)
        def outside(buf):
            im = Image.new('1', (self.nx, self.ny), 1); dr = ImageDraw.Draw(im)
            inner = ol.buffer(-buf)
            for poly in (inner.geoms if hasattr(inner, 'geoms') else [inner]):
                dr.polygon([((x - self.x0) / RES, (y - self.y0) / RES) for x, y in poly.exterior.coords], fill=0)
                for h in poly.interiors:
                    dr.polygon([((x - self.x0) / RES, (y - self.y0) / RES) for x, y in h.coords], fill=1)
            return np.array(im, dtype=bool)
        hw = width_mil / 2
        self.block = {}
        self.vblock = None
        out_t = outside(edge_clr_mil + hw)
        out_v = outside(edge_clr_mil + via_d / 2)
        hole_t = rast(holes, hole_clr_mil + hw)
        hole_v = rast(holes, hole_clr_mil + via_d / 2)
        ko = rast(list(keepouts), hw) if keepouts else np.zeros_like(out_t)
        for L in (1, 2):
            others = [g for (LL, n, g, k, ref) in items if LL == L and n != net]
            self.block[L] = rast(others, clr_mil + hw) | out_t | hole_t | ko
        vb = None
        for L in (1, 2):
            others = [g for (LL, n, g, k, ref) in items if LL == L and n != net]
            b2 = rast(others, clr_mil + via_d / 2)
            vb = b2 if vb is None else (vb | b2)
        self.vblock = vb | out_v | hole_v | ko
    def ij(self, x, y): return int(round((x - self.x0) / RES)), int(round((y - self.y0) / RES))
    def xy(self, i, j): return self.x0 + i * RES, self.y0 + j * RES
    def route(self, starts, goals, via_cost=25, layer_pen=None, max_iter=5_000_000):
        """starts/goals: list of (x_mil, y_mil, layer) ; layer 12 = both"""
        def expand(lst):
            out = []
            for x, y, L in lst:
                i, j = self.ij(x, y)
                for LL in ((1, 2) if L == 12 else (L,)): out.append((i, j, LL))
            return out
        S = expand(starts); G = set(expand(goals))
        gx = np.mean([g[0] for g in G]); gy = np.mean([g[1] for g in G])
        h = lambda i, j: math.hypot(i - gx, j - gy) * 0.95
        openq = []; came = {}; cost = {}
        for s in S:
            cost[s] = 0; heapq.heappush(openq, (h(s[0], s[1]), 0, s)); came[s] = None
        moves = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
        it = 0
        while openq:
            f, c, n = heapq.heappop(openq); it += 1
            if it > max_iter: break
            if n in G:
                path = []
                while n is not None: path.append(n); n = came[n]
                return path[::-1]
            if c > cost.get(n, 1e18): continue
            i, j, L = n
            pen = (layer_pen or {}).get(L, 1.0)
            for di, dj, mc in moves:
                ni, nj = i + di, j + dj
                if not (0 <= ni < self.nx and 0 <= nj < self.ny): continue
                nn = (ni, nj, L)
                if self.block[L][nj, ni] and nn not in G: continue
                # direction change penalty
                pr = came.get(n)
                turn = 0
                if pr is not None and pr[2] == L and (i - pr[0], j - pr[1]) != (di, dj): turn = 0.6
                nc = c + mc * pen + turn
                if nc < cost.get(nn, 1e18):
                    cost[nn] = nc; came[nn] = n; heapq.heappush(openq, (nc + h(ni, nj), nc, nn))
            if not self.vblock[j, i]:
                nn = (i, j, 3 - L); nc = c + via_cost
                if not self.block[3 - L][j, i] and nc < cost.get(nn, 1e18):
                    cost[nn] = nc; came[nn] = n; heapq.heappush(openq, (nc + h(i, j), nc, nn))
        return None
    def to_segments(self, path):
        """-> list of ('L', layer, x1,y1,x2,y2) and ('V', x,y) in mil"""
        segs = []
        k = 0
        while k < len(path) - 1:
            a = path[k]; b = path[k + 1]
            if a[2] != b[2]:
                segs.append(('V',) + self.xy(a[0], a[1])); k += 1; continue
            d = (b[0] - a[0], b[1] - a[1]); m = k + 1
            while m < len(path) - 1 and path[m + 1][2] == a[2] and (path[m + 1][0] - path[m][0], path[m + 1][1] - path[m][1]) == d:
                m += 1
            segs.append(('L', a[2]) + self.xy(a[0], a[1]) + self.xy(path[m][0], path[m][1]))
            k = m
        return segs
