import sys, os, json; sys.path.insert(0, '.')
import numpy as np, check
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as P
def draw(rows, fps, outer, fname, xlim, ylim, title=''):
    cu = check.copper(rows, fps)
    fig, axs = plt.subplots(1, 2, figsize=(18, 7), dpi=120)
    for ax, L, col in ((axs[0], 1, 'r'), (axs[1], 2, 'b')):
        ax.plot(*np.asarray(outer.exterior.coords).T, 'k', lw=1)
        for h in check.holes(rows): ax.plot(*np.asarray(h.exterior.coords).T, 'k', lw=.6)
        for lay, net, g, i in cu:
            if lay != L: continue
            for gg in getattr(g, 'geoms', [g]):
                ax.add_patch(P(np.asarray(gg.exterior.coords), fc=col, alpha=.35, ec=col, lw=.3))
            c = g.centroid
            if ':' in str(i) and xlim[0] < c.x < xlim[1] and ylim[0] < c.y < ylim[1]: ax.text(c.x, c.y, net[:9], fontsize=5)
        ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect('equal'); ax.grid(lw=.3); ax.set_title(f'{title} camada {L}')
    fig.tight_layout(); fig.savefig(fname)
