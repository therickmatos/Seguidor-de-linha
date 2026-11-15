"""Figura de conferência do PCB de um .epro (trilhas, vias, pads, furos, contorno).
Uso: python3 figura_pcb.py arquivo.epro saida.png [xmin xmax ymin ymax]   (mm)"""
import glob, os, sys, tempfile, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gerar_dreamcast import read_rows, pad_geoms, outline, MIL, LineString, Point  # noqa: E402
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

epro, png = sys.argv[1], sys.argv[2]
x0, x1, y0, y1 = map(float, sys.argv[3:7]) if len(sys.argv) > 6 else (-52, 52, -35, 27)
d = tempfile.mkdtemp()
zipfile.ZipFile(epro).extractall(d)
rows = [r for r in read_rows(glob.glob(d + '/PCB/*.epcb')[0]) if r]
des = {r[3]: r[8] for r in rows if r[0] == 'ATTR' and r[7] == 'Designator' and r[8]}
fig, ax = plt.subplots(figsize=(16, 16 * (y1 - y0) / (x1 - x0)))


def fill(g, **kw):
    for gg in getattr(g, 'geoms', [g]):
        x, y = gg.exterior.xy
        ax.fill([v * MIL for v in x], [v * MIL for v in y], **kw)


for p in outline(rows):
    x, y = p.exterior.xy
    ax.plot([v * MIL for v in x], [v * MIL for v in y], 'k-', lw=1.5)
for r in rows:
    if r[0] == 'LINE' and r[4] in (1, 2):
        fill(LineString([(r[5], r[6]), (r[7], r[8])]).buffer(r[9] / 2),
             color='tab:red' if r[4] == 1 else 'tab:blue', alpha=.45, lw=0)
    elif r[0] == 'VIA':
        fill(Point(r[5], r[6]).buffer(r[8] / 2), color='tab:green')
    elif r[0] == 'FILL' and r[4] == 12:
        for s in r[7]:
            if s[0] == 'CIRCLE':
                ax.add_patch(plt.Circle((s[1] * MIL, s[2] * MIL), s[3] * MIL, fill=False, color='k'))
cent = {}
for c, n, ly, g, net in pad_geoms(d, rows):
    fill(g, color='orange' if ly == (1, 2) else ('darkred' if ly == (1,) else 'navy'), alpha=.85)
    cent.setdefault(c, []).append(g.centroid.coords[0])
for c, pts in cent.items():
    x = sum(p[0] for p in pts) / len(pts) * MIL
    y = max(p[1] for p in pts) * MIL + 0.8
    if x0 < x < x1 and y0 < y < y1:
        ax.text(x, y, des.get(c, ''), fontsize=7, ha='center', weight='bold')
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.grid(True, lw=.3)
ax.set_title(os.path.basename(epro) + '  (vermelho = cima, azul = baixo, laranja = PTH; mm, origem no centro da ventoinha)', fontsize=9)
plt.savefig(png, dpi=110, bbox_inches='tight')
