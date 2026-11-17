"""Recorte ampliado das duas faces com ids dos itens: python3 zoom.py arq.epro x0 x1 y0 y1 saida.png [redes destacadas]"""
import sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import verifica_placa as V, check
from shapely.geometry import box, Point
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
P, x0, x1, y0, y1, out = sys.argv[1], *map(float, sys.argv[2:6]), sys.argv[6]
hl = sys.argv[7].split(',') if len(sys.argv) > 7 else []
rows, fps, outer = V.board(P)
cu = check.copper(rows, fps)
hs = check.holes(rows)
# pads soltos (PAD fora de componente)
from shapely import affinity
from shapely.geometry import LineString
M = 0.0254
for r in rows:
    if r[0] == 'PAD':
        s = r[10]; w, h = s[1] * M, s[2] * M
        g = LineString([(-(w - h) / 2, 0), ((w - h) / 2, 0)]).buffer(h / 2) if w >= h else LineString([(0, -(h - w) / 2), (0, (h - w) / 2)]).buffer(w / 2)
        g = affinity.translate(affinity.rotate(g, r[8], origin=(0, 0)), r[6] * M, r[7] * M)
        for L in (1, 2): cu.append((L, r[3], g, r[1]))
W = box(x0, y0, x1, y1)
fig, axs = plt.subplots(1, 2, figsize=(22, 22 * (y1 - y0) / (x1 - x0) / 2 + 1))
for ax, L in zip(axs, (1, 2)):
    xx, yy = outer.exterior.xy; ax.plot(xx, yy, 'k', lw=1)
    for h in hs:
        if h.intersects(W): xx, yy = h.exterior.xy; ax.plot(xx, yy, 'k--', lw=0.8)
    for l, n, g, i in cu:
        if l != L or not g.intersects(W): continue
        c = '#c33' if n == 'GND' else ('#e0a' if n in hl else ('#36c' if L == 1 else '#c80'))
        for gg in getattr(g, 'geoms', [g]):
            xx, yy = gg.exterior.xy; ax.fill(xx, yy, color=c, alpha=0.6, lw=0)
        p = g.representative_point()
        ax.text(p.x, p.y, f'{i}\n{n}', fontsize=5)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.grid(alpha=0.3); ax.set_title(f'face {L}')
plt.tight_layout(); plt.savefig(out, dpi=90)
