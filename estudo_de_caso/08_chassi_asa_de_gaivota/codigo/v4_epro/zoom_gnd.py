"""Ilhas de GND simuladas num recorte: python3 zoom_gnd.py arq.epro x0 x1 y0 y1 saida.png"""
import sys; sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import verifica_placa as V, plano_gnd as G
from shapely.geometry import box
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
P, x0, x1, y0, y1, out = sys.argv[1], *map(float, sys.argv[2:6]), sys.argv[6]
rows, fps, outer = V.board(P)
cu, pcs, f, main = G.pieces(rows, fps, outer)
Wb = box(x0, y0, x1, y1)
fig, axs = plt.subplots(1, 2, figsize=(22, 22 * (y1 - y0) / (x1 - x0) / 2 + 1.5))
for ax, L in zip(axs, (1, 2)):
    x, y = outer.exterior.xy; ax.plot(x, y, 'k', lw=1)
    for k, (LL, p) in enumerate(pcs):
        if LL != L or not p.intersects(Wb): continue
        xx, yy = p.exterior.xy; ax.fill(xx, yy, color='#7c7' if f(k) == main else '#f90', alpha=0.6, lw=0)
    for l, n, g, i in cu:
        if l != L or not g.intersects(Wb): continue
        for gg in getattr(g, 'geoms', [g]):
            xx, yy = gg.exterior.xy; ax.plot(xx, yy, color='r' if n == 'GND' else 'b', lw=0.7)
        c = g.representative_point(); ax.text(c.x, c.y, f'{i}\n{n}', fontsize=5)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.grid(alpha=.3); ax.set_title(f'face {L}')
plt.tight_layout(); plt.savefig(out, dpi=80)
