import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from epro import *
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP
root, out = sys.argv[1], sys.argv[2]
layers = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else [1, 2]
zoom = [float(v) for v in sys.argv[4].split(',')] if len(sys.argv) > 4 else None
p = Proj(root)
ol, _ = outline_polygon(p)
items = copper(p)
fig, ax = plt.subplots(figsize=(22, 14) if not zoom else (14, 14))
def draw(g, **kw):
    gs = g.geoms if hasattr(g, 'geoms') else [g]
    for x in gs:
        if x.is_empty: continue
        ax.add_patch(MP([(a*MIL, b*MIL) for a, b in x.exterior.coords], closed=True, **kw))
        for h in x.interiors:
            ax.add_patch(MP([(a*MIL, b*MIL) for a, b in h.coords], closed=True, fc='white', ec='none', alpha=1))
draw(ol, fc='#f4f4f4', ec='m', lw=1)
col = {1: '#d62728', 2: '#1f77b4'}
for kind in ('pour', 'track', 'pad', 'via'):
    for L, net, g, k, ref in items:
        if k != kind or L not in layers: continue
        if kind == 'pour': draw(g, fc=col[L], ec='none', alpha=0.12)
        elif kind == 'track': draw(g, fc=col[L], ec='none', alpha=0.6)
        elif kind == 'pad': draw(g, fc='#e0a000' if L == 1 else '#00a0a0', ec='k', lw=0.3, alpha=0.8)
        elif kind == 'via': draw(g, fc='#666', ec='k', lw=0.3, alpha=0.9)
for r in p.pcb:
    if r[0] == 'FILL' and r[4] == 12:
        cx, cy, rr = r[7][0][1:4]; ax.add_patch(plt.Circle((cx*MIL, cy*MIL), rr*MIL, fc='white', ec='k', lw=0.5))
    if r[0] == 'VIA':
        ax.add_patch(plt.Circle((r[5]*MIL, r[6]*MIL), r[7]/2*MIL, fc='white', ec='none'))
    if r[0] == 'PAD':
        g = pad_shape(dict(shape=r[10], x=r[6], y=r[7], rot=r[8])); draw(g, fc='#aaa', ec='k', lw=0.3)
for c in p.comps.values():
    fpid = c['attrs'].get('Footprint')
    if c['attrs'].get('Designator') != 'J6': continue
    th = math.radians(c['rot'])
    for r in p.fps[fpid]:
        if r[0] == 'POLY' and r[4] == 3:
            pts = path_to_coords(r[6])
            xy = [((c['x'] + x*math.cos(th) - y*math.sin(th))*MIL, (c['y'] + x*math.sin(th) + y*math.cos(th))*MIL) for x, y in pts]
            ax.plot([a for a, b in xy], [b for a, b in xy], color='k', lw=1.2)
# pad labels
for q in p.all_pads():
    L = q['layer']
    if L != 12 and L not in layers: continue
    ax.text(q['x']*MIL, q['y']*MIL, f"{q['num']}\n{q['net'][:8]}" if zoom else q['num'], fontsize=4 if not zoom else 6, ha='center', va='center', clip_on=True)
for c in p.comps.values():
    ax.text(c['x']*MIL, c['y']*MIL + 1.2, c['attrs'].get('Designator'), fontsize=6, color='purple', ha='center', weight='bold', clip_on=True)
b = ol.bounds
ax.set_xticks(range(-52, 53, 2)); ax.set_yticks(range(-36, 30, 2)); ax.tick_params(labelsize=6)
if zoom: ax.set_xlim(zoom[0], zoom[1]); ax.set_ylim(zoom[2], zoom[3])
else: ax.set_xlim(b[0]*MIL - 2, b[2]*MIL + 2); ax.set_ylim(b[1]*MIL - 2, b[3]*MIL + 2)
ax.set_aspect('equal'); ax.grid(True, lw=0.2)
plt.savefig(out, dpi=110, bbox_inches='tight')
