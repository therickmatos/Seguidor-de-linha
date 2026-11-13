"""Lê as áreas de cobre já preenchidas (linhas POURED) de um .epcb do EasyEDA Pro."""
import math
from shapely.geometry import Polygon
M = 0.254   # as linhas POURED vêm em unidades de 10 mil
def path_pts(p):
    pts = [(p[0], p[1])]; i = 2; mode = None
    while i < len(p):
        t = p[i]
        if isinstance(t, str):
            mode = t; i += 1
            if mode == 'CIRCLE':
                cx, cy, r = p[i:i + 3]; return [(cx + r * math.cos(a / 24 * 2 * math.pi), cy + r * math.sin(a / 24 * 2 * math.pi)) for a in range(24)]
            continue
        if mode == 'L':
            pts.append((p[i], p[i + 1])); i += 2
        elif mode == 'ARC':
            ang, x, y = p[i], p[i + 1], p[i + 2]; i += 3
            x0, y0 = pts[-1]
            # arco de ângulo 'ang' (graus) de (x0,y0) até (x,y): centro pela corda
            th = math.radians(ang)
            if abs(th) < 1e-6: pts.append((x, y)); continue
            mx, my = (x0 + x) / 2, (y0 + y) / 2; c = math.hypot(x - x0, y - y0)
            if c < 1e-9: continue
            h = c / 2 / math.tan(th / 2)
            nx, ny = -(y - y0) / c, (x - x0) / c
            cx, cy = mx + nx * h, my + ny * h
            a0 = math.atan2(y0 - cy, x0 - cx)
            n = max(2, int(abs(ang) / 10))
            for k in range(1, n + 1):
                a = a0 + th * k / n; R = math.hypot(x0 - cx, y0 - cy)
                pts.append((cx + R * math.cos(a), cy + R * math.sin(a)))
        else:
            i += 1
    return pts
def poured(rows, spoke_w=0.254):
    """[(pour_id, layer, kind, geom mm)]; kind 'fill' (polígono com furos) ou 'spoke' (raio térmico)."""
    from shapely.geometry import LineString
    lay = {r[1]: r[4] for r in rows if r[0] == 'POUR'}
    out = []
    for r in rows:
        if r[0] != 'POURED': continue
        paths = [[(x * M, y * M) for x, y in path_pts(p)] for p in r[5]]
        if r[4]:
            if len(paths[0]) < 3: continue
            g = Polygon(paths[0], [h for h in paths[1:] if len(h) >= 3]).buffer(0)
            out.append((r[2], lay.get(r[2]), 'fill', g))
        else:
            for p in paths:
                if len(p) >= 2: out.append((r[2], lay.get(r[2]), 'spoke', LineString(p).buffer(spoke_w / 2)))
    return out
