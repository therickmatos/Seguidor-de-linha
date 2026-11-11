import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from epro import *
import epro
from poursim import copper_sim
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP
p = Proj(sys.argv[1]); out = sys.argv[2]
ol, _ = outline_polygon(p)
items = copper_sim(p)
fig, axs = plt.subplots(1, 2, figsize=(20, 7.2), facecolor='white')
def draw(ax, g, **kw):
    for x in (g.geoms if hasattr(g, 'geoms') else [g]):
        if x.is_empty: continue
        ax.add_patch(MP([(a*MIL, b*MIL) for a, b in x.exterior.coords], closed=True, **kw))
        for h in x.interiors:
            ax.add_patch(MP([(a*MIL, b*MIL) for a, b in h.coords], closed=True, fc='#1f5f3a', ec='none'))
for ax, L, title in ((axs[0], 1, 'Face de cima (top)'), (axs[1], 2, 'Face de baixo (vista por cima, transparente)')):
    draw(ax, ol, fc='#1f5f3a', ec='#d0d0d0', lw=1.5)
    for kind in ('pour', 'track'):
        for LL, net, g, k, ref in items:
            if LL == L and k == kind:
                draw(ax, g, fc='#2f8a55' if kind == 'pour' else '#3fa66a', ec='none')
    for LL, net, g, k, ref in items:
        if LL == L and k in ('pad', 'via'):
            draw(ax, g, fc='#d9b24a' if k == 'pad' else '#c9a440', ec='none')
    for r in p.pcb:
        if r[0] == 'FILL' and r[4] == 12:
            cx, cy, rr = r[7][0][1:4]; ax.add_patch(plt.Circle((cx*MIL, cy*MIL), rr*MIL, fc='white', ec='#d0d0d0'))
        if r[0] == 'VIA':
            ax.add_patch(plt.Circle((r[5]*MIL, r[6]*MIL), r[7]/2*MIL, fc='white', ec='none'))
        if r[0] == 'PAD':
            draw(ax, pad_shape(dict(shape=r[10], x=r[6], y=r[7], rot=r[8])), fc='#d9b24a', ec='none')
    for q in p.all_pads():
        if q['hole'] and q['hole'][1] > 0:
            ax.add_patch(plt.Circle((q['x']*MIL, q['y']*MIL), q['hole'][1]/2*MIL, fc='white', ec='none'))
    for c in p.comps.values():
        if (c['layer'] == L):
            ref = c['attrs'].get('Designator')
            col = '#ff5050' if ref == 'J6' else 'white'
            ax.text(c['x']*MIL - (4.5 if ref == 'J6' else 0), c['y']*MIL, ref, color=col, fontsize=7 if ref != 'J6' else 10, ha='center', va='center', weight='bold',
                    bbox=dict(fc='#00000055', ec='none', pad=0.5))
    b = ol.bounds
    ax.set_xlim(b[0]*MIL - 2, b[2]*MIL + 2); ax.set_ylim(b[1]*MIL - 2, b[3]*MIL + 2)
    ax.set_aspect('equal'); ax.set_title(title, fontsize=13); ax.tick_params(labelsize=7)
    ax.set_xlabel('x (mm)'); ax.set_ylabel('y (mm, + = frente)')
fig.suptitle('Perseguidor (RUSH – SATURN, entalhe A) com o J6 / KY-022  ·  100 × 58,6 mm  ·  polígonos de GND simulados', fontsize=12)
plt.tight_layout(); plt.savefig(out, dpi=150, facecolor='white')
