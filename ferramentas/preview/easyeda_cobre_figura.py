"""Figura das duas faces de um .epro (cobre, pads, vias, planos de GND simulados e ligacoes abertas).

  python easyeda_cobre_figura.py placa.epro saida.png [--zoom x0 y0 x1 y1] [--sem-planos]

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import nearest_points

import easyeda_cobre as C


def _patches(ax, g, **kw):
    geoms = list(g.geoms) if hasattr(g, 'geoms') else [g]
    for p in geoms:
        if p.is_empty or not isinstance(p, Polygon):
            continue
        xs, ys = p.exterior.xy
        ax.fill(xs, ys, **kw)
        for i in p.interiors:
            xs, ys = i.xy
            ax.fill(xs, ys, color='white', lw=0)


def figura(caminho, saida, zoom=None, planos=True, rotulos=True):
    placa = C.Placa(caminho)
    objs = placa.objetos()
    pl = placa.planos_gnd(objs) if planos else {}
    extra = []
    for lay, g in pl.items():
        geoms = list(g.geoms) if isinstance(g, MultiPolygon) else [g]
        extra += [{'tipo': 'plano', 'net': 'GND', 'layers': {lay}, 'geom': gg, 'ref': 'plano', 'obj': None} for gg in geoms]
    redes = sorted({p['net'] for p in placa.pads if p['net']})
    abertas = []
    for net in redes:
        gr = C.ilhas(objs, net, extra if net == 'GND' else ())
        gr = [g for g in gr if any(o['tipo'] == 'pad' for o in g)]
        if len(gr) > 1:
            base = gr[0]
            for g in gr[1:]:
                ga = min(((o, q) for o in base for q in g if o['tipo'] != 'plano' and q['tipo'] != 'plano'),
                         key=lambda t: t[0]['geom'].distance(t[1]['geom']), default=None)
                if ga:
                    a, b = nearest_points(ga[0]['geom'], ga[1]['geom'])
                    abertas.append((net, a, b))
    fig, axs = plt.subplots(1, 2, figsize=(26, 11) if not zoom else (22, 11))
    cores = {C.TOP: '#d62728', C.BOT: '#1f77b4'}
    for ax, lay, nome in ((axs[0], C.TOP, 'face de cima (vista de cima)'), (axs[1], C.BOT, 'face de baixo (vista de cima, atraves da placa)')):
        _patches(ax, placa.borda, color='#f4f1e8', lw=0)
        xs, ys = placa.borda.exterior.xy
        ax.plot(xs, ys, color='k', lw=0.8)
        for h in placa.npth:
            xs, ys = h.exterior.xy
            ax.plot(xs, ys, color='k', lw=0.6)
        if lay in pl:
            _patches(ax, pl[lay], color='#9edc9e', alpha=0.45, lw=0)
        for o in objs:
            if lay not in o['layers']:
                continue
            if o['tipo'] == 'trilha':
                cor = cores[lay]
                if o['net'] in C.POTENCIA:
                    cor = {'VBAT': '#ff7f0e', '+5V': '#9467bd'}.get(o['net'], '#8c564b')
                if o['net'] == 'GND':
                    cor = '#2ca02c'
                _patches(ax, o['geom'], color=cor, alpha=0.75, lw=0)
            elif o['tipo'] == 'pad':
                cor = '#555555' if o['net'] != 'GND' else '#2ca02c'
                _patches(ax, o['geom'], color=cor, alpha=0.9, lw=0)
            elif o['tipo'] == 'via':
                _patches(ax, o['geom'], color='#e5a50a' if o['net'] != 'GND' else '#006400', lw=0)
        if rotulos:
            for des, c in placa.comps.items():
                if (lay == C.BOT) == c['baixo']:
                    ax.text(c['x'], c['y'], des, fontsize=6 if not zoom else 9, ha='center', va='center',
                            color='black', alpha=0.8, zorder=10)
        for net, a, b in abertas:
            ax.plot([a.x, b.x], [a.y, b.y], color='magenta', lw=1.2, zorder=11)
            ax.text((a.x + b.x) / 2, (a.y + b.y) / 2, net, color='magenta', fontsize=7, zorder=12)
        ax.set_aspect('equal')
        ax.set_title(nome)
        if zoom:
            ax.set_xlim(zoom[0], zoom[2])
            ax.set_ylim(zoom[1], zoom[3])
        ax.grid(True, lw=0.2)
    fig.tight_layout()
    fig.savefig(saida, dpi=110 if not zoom else 130)
    return abertas


if __name__ == '__main__':
    z = None
    if '--zoom' in sys.argv:
        i = sys.argv.index('--zoom')
        z = [float(v) for v in sys.argv[i + 1:i + 5]]
    ab = figura(sys.argv[1], sys.argv[2], z, planos='--sem-planos' not in sys.argv)
    for net, a, b in ab:
        print(net, (round(a.x, 2), round(a.y, 2)), '->', (round(b.x, 2), round(b.y, 2)))
