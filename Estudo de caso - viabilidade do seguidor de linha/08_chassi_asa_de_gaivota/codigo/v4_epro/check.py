"""Checagem de folgas (aproximação do DRC) das trilhas/vias/pads novos ou movidos."""
import math, sys
from shapely.geometry import LineString, Point, Polygon, box
from shapely import affinity
from shapely.ops import unary_union
M = 0.0254
def pad_geoms(rows, fps):
    comps = {}
    for r in rows:
        if r[0] == 'COMPONENT': comps[r[1]] = dict(row=r, fp=None, nets={})
    for r in rows:
        if r[0] == 'ATTR' and r[3] in comps and r[7] == 'Footprint': comps[r[3]]['fp'] = r[8]
        if r[0] == 'PAD_NET' and r[1] in comps and r[2]: comps[r[1]]['nets'][r[2]] = r[3]
    out = []
    for cid, c in comps.items():
        r = c['row']
        if not c['fp']: continue
        for p in fps[c['fp']]:
            if p[0] != 'PAD': continue
            x, y = p[6], p[7]; s = p[10]
            w, h = s[1] * M, s[2] * M
            if s[0] == 'RECT':
                g = box(-w / 2, -h / 2, w / 2, h / 2)
            elif s[0] == 'OVAL':          # oblongo (pontas semicirculares), como no EasyEDA
                g = (LineString([(-(w - h) / 2, 0), ((w - h) / 2, 0)]).buffer(h / 2, quad_segs=12) if w >= h
                     else LineString([(0, -(h - w) / 2), (0, (h - w) / 2)]).buffer(w / 2, quad_segs=12))
                if abs(w - h) < 1e-9: g = Point(0, 0).buffer(w / 2, quad_segs=12)
            else:                         # ELLIPSE
                g = affinity.scale(Point(0, 0).buffer(1, quad_segs=12), w / 2, h / 2)
            g = affinity.rotate(g, p[8], origin=(0, 0)); g = affinity.translate(g, x * M, y * M)
            if r[3] == 2: g = affinity.scale(g, 1, -1, origin=(0, 0))
            g = affinity.rotate(g, r[6], origin=(0, 0)); g = affinity.translate(g, r[4] * M, r[5] * M)
            lay = p[4]
            layers = [1, 2] if lay == 12 else [r[3] if lay == 1 else 3 - r[3]]
            for L in layers: out.append((L, c['nets'].get(p[5], ''), g, f'{cid}:{p[5]}'))
    return out
def copper(rows, fps):
    out = pad_geoms(rows, fps)
    for r in rows:
        if r[0] == 'LINE' and r[4] in (1, 2):
            out.append((r[4], r[3], LineString([(r[5] * M, r[6] * M), (r[7] * M, r[8] * M)]).buffer(r[9] * M / 2, quad_segs=8), r[1]))
        elif r[0] == 'VIA':
            for L in (1, 2): out.append((L, r[3], Point(r[5] * M, r[6] * M).buffer(r[8] * M / 2, quad_segs=12), r[1]))
        elif r[0] == 'ARC' and r[4] in (1, 2):
            out.append((r[4], r[3], LineString([(r[5] * M, r[6] * M), (r[7] * M, r[8] * M)]).buffer(r[10] * M / 2 + 0.25), r[1]))
    return out
def holes(rows):
    hs = []
    for r in rows:
        if r[0] == 'FILL' and r[4] == 12:
            for sh in r[7]:
                if sh[0] == 'CIRCLE': hs.append(Point(sh[1] * M, sh[2] * M).buffer(sh[3] * M, quad_segs=16))
        if r[0] == 'PAD' and r[9] and r[9][0] == 'SLOT':
            x, y = r[6] * M, r[7] * M; L, W = r[9][1] * M, r[9][2] * M
            g = LineString([(0, -(L - W) / 2), (0, (L - W) / 2)]).buffer(W / 2)
            hs.append(affinity.translate(affinity.rotate(g, r[8], origin=(0, 0)), x, y))
    return hs
def check(rows, fps, outer, ids, clr=0.2, edge=0.3, hole=0.3, verbose=True):
    cu = copper(rows, fps)
    hs = holes(rows)
    probs = []
    ring = outer.exterior
    mine = [c for c in cu if c[3] in ids or any(c[3].startswith(i + ':') for i in ids)]
    for L, net, g, i in mine:
        de = g.distance(ring) if outer.contains(g) else -g.difference(outer).area
        if de < edge: probs.append(('borda', i, net, round(de, 3)))
        for L2, net2, g2, i2 in cu:
            if L2 != L or net2 == net and net: continue
            if i2 == i: continue
            d = g.distance(g2)
            if d < clr: probs.append(('folga', i, net, i2, net2, L, round(d, 3)))
        for h in hs:
            d = g.distance(h)
            if 0 < d < hole and not (net and False): probs.append(('furo', i, net, round(d, 3)))
    if verbose:
        seen = set()
        for p in probs:
            k = tuple(sorted([str(p[1]), str(p[3])])) if p[0] == 'folga' else p
            if k in seen: continue
            seen.add(k); print(p)
    return probs
