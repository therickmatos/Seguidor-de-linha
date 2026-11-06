"""Figura da placa base v2: face de cima e face de baixo (vista atraves da placa).

Uso: python figura_v2.py [saida.jpg] [x0 x1 y0 y1]   (recorte opcional, so face de cima)
Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import json
import math
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as effects
from matplotlib.patches import Polygon as PatchPolygon, PathPatch
from matplotlib.path import Path as MPath
from shapely.geometry import LineString, Point, box

import footprints as F
import layout_placa as M
import placa_v2 as V
import rotear_v2 as R

BG = '#0f1317'; BOARD = '#173026'; WHITE = '#f3f5ee'; GRID = '#3c514a'
TOPC = '#e8604f'; BOTC = '#4f9be8'; PAD = '#f0c987'; AIR = '#ffe36f'
POUR = {1: '#5a2b27', 2: '#22385a'}


def poly(ax, g, **kw):
    if g.is_empty:
        return
    if g.geom_type == 'Polygon':
        verts, codes = [], []
        for ring in [g.exterior, *g.interiors]:
            c = list(ring.coords)
            verts += c
            codes += [MPath.MOVETO] + [MPath.LINETO] * (len(c) - 2) + [MPath.CLOSEPOLY]
        ax.add_patch(PathPatch(MPath(verts, codes), **kw))
    else:
        for p in g.geoms:
            poly(ax, p, **kw)


def load_copper():
    data = json.loads(R.COBRE.read_text(encoding='utf8'))
    from shapely.geometry import Polygon
    pours = {}
    for k, rings in data['planos'].items():
        holes = data['planos_furos'][k]
        pours[int(k)] = [Polygon(r, h) for r, h in zip(rings, holes)]
    return data, pours


def draw(ax, pos, data, pours, layer, view, open_edges, labels=True):
    x0, x1, y0, y1 = view
    ax.set_facecolor(BG)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal')
    step = 5 if x1 - x0 > 60 else 1
    ax.set_xticks(range(math.ceil(x0 / step) * step, int(x1) + 1, step))
    ax.set_yticks(range(math.ceil(y0 / step) * step, int(y1) + 1, step))
    ax.grid(color=GRID, alpha=.3, lw=.3, zorder=0)
    ax.tick_params(colors='#9fb0a8', labelsize=5.5, length=2, pad=1)
    for s in ax.spines.values():
        s.set_color('#4a5a54')
    poly(ax, M.BOARD, facecolor=BOARD, edgecolor='#dfe6da', lw=.9, zorder=1)
    other = 2 if layer == 1 else 1
    col = {1: TOPC, 2: BOTC}
    # outra face, apagada
    for t in data['tracks']:
        if t['layer'] == other:
            xs, ys = zip(*t['xy'])
            ax.plot(xs, ys, color=col[other], alpha=.18, lw=R_lw(ax, t['width']),
                    solid_capstyle='round', zorder=2)
    for p in pours[layer]:
        poly(ax, p, facecolor=POUR[layer], edgecolor='none', alpha=.85, zorder=3)
    for t in data['tracks']:
        if t['layer'] == layer:
            xs, ys = zip(*t['xy'])
            ax.plot(xs, ys, color=col[layer], lw=R_lw(ax, t['width']),
                    solid_capstyle='round', solid_joinstyle='round', zorder=5)
    for v in data['vias']:
        ax.add_patch(plt.Circle(v['xy'], v['diameter'] / 2, color='#c9b27a', zorder=13, lw=0))
        ax.add_patch(plt.Circle(v['xy'], v['drill'] / 2, color=BG, zorder=14, lw=0))
    # componentes e pads
    for c in pos:
        on = c['face'] == ('TOP' if layer == 1 else 'BOTTOM')
        for p in M.get_pads(c):
            if layer in p['layers']:
                fc = PAD if on or c['tht'] else PAD
                poly(ax, p['shape'], facecolor=fc, edgecolor='#00000055', lw=.2, zorder=9)
                if p['furo']:
                    ax.add_patch(plt.Circle((p['x'], p['y']), p['furo'] / 2, color=BG, zorder=10))
                if p['pin'] == '1' and c['ref'] not in ('M1', 'M2', 'M3'):
                    ax.add_patch(plt.Circle((p['x'], p['y']), .17, color='white', zorder=11))
        b = M.body(c)
        if on and b is not None and c['ref'] not in ('M1', 'M2', 'M3'):
            poly(ax, b, facecolor='none', edgecolor='#e9eee6', lw=.45, alpha=.55, zorder=12)
        if on and labels and x0 < c['x'] < x1 and y0 < c['y'] < y1:
            bb = b.bounds if b is not None else (c['x'] - 1, c['y'] - 1, c['x'] + 1, c['y'] + 1)
            ty = bb[3] + .55
            t = ax.text(c['x'], ty, c['ref'], fontsize=4.6 if x1 - x0 > 60 else 7, color=WHITE,
                        ha='center', va='bottom', fontweight='bold', zorder=20)
            t.set_path_effects([effects.withStroke(linewidth=1.4, foreground=BG)])
    for e in open_edges:
        (ax_, ay), (bx, by) = e
        ax.plot([ax_, bx], [ay, by], color=AIR, lw=1.0, zorder=21)
        ax.add_patch(plt.Circle((ax_, ay), .6, fill=False, color=AIR, lw=.8, zorder=21))


def R_lw(ax, w):
    fig = ax.figure
    x0, x1 = ax.get_xlim()
    return w * fig.get_figwidth() * 72 * ax.get_position().width / (x1 - x0)


def open_edges_from(ver, pos):
    pads = {f"{p['ref']}.{p['pin']}": (p['x'], p['y']) for p in M.all_pads(pos)}
    edges = []
    for net, groups in ver['abertas_final'].items():
        for g in groups[1:]:
            a = pads[groups[0][0]]
            b = min((pads[q] for q in g), key=lambda q: math.dist(q, a))
            edges.append((a, b))
    return edges


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else str(M.OUTPUT / 'placa_v2.jpg')
    pos = V.load()
    data, pours = load_copper()
    ver = json.loads(R.VERIF.read_text(encoding='utf8'))
    edges = open_edges_from(ver, pos)
    if len(sys.argv) > 5:
        view = tuple(float(v) for v in sys.argv[2:6])
        layer = int(sys.argv[6]) if len(sys.argv) > 6 else 1
        w = 14
        fig, ax = plt.subplots(figsize=(w, w * (view[3] - view[2]) / (view[1] - view[0])), dpi=150)
        draw(ax, pos, data, pours, layer, view, edges)
        fig.savefig(out, dpi=150, facecolor=BG, bbox_inches='tight')
        print(out)
        return
    view = (-76, 76, -36.5, 27)
    fig = plt.figure(figsize=(20, 18.2), dpi=210, facecolor=BG)
    ax1 = fig.add_axes([0.04, 0.515, 0.92, 0.40])
    ax2 = fig.add_axes([0.04, 0.075, 0.92, 0.40])
    draw(ax1, pos, data, pours, 1, view, edges)
    draw(ax2, pos, data, pours, 2, view, edges)
    nopen = sum(len(g) - 1 for g in ver['abertas_final'].values())
    fig.text(0.04, 0.965, 'PLACA BASE v2 — J3 embaixo, ATmega na posição do EVA-RT, plano de GND',
             color=WHITE, fontsize=17, fontweight='bold')
    fig.text(0.04, 0.945, f"{ver['trilhas']} trilhas · {ver['vias']} vias · ligações abertas: {nopen} · "
             f"folga mínima entre redes {ver['folga_mm']} mm, cobre–borda {ver['borda_mm']} mm · "
             'grade 5 mm, +y = frente, origem no centro da ventoinha', color='#c7d2cc', fontsize=10)
    fig.text(0.04, 0.922, 'FACE DE CIMA (cobre vermelho, plano GND marrom)', color=WHITE, fontsize=11,
             fontweight='bold')
    fig.text(0.04, 0.482, 'FACE DE BAIXO — vista através da placa, sem espelhar (cobre azul, plano GND azul-escuro)',
             color=WHITE, fontsize=11, fontweight='bold')
    fig.text(0.04, 0.045, 'Pads em bege; ponto branco = pino 1; cobre da outra face apagado ao fundo; '
             'vias em dourado; amarelo = ligação aberta.', color='#c7d2cc', fontsize=9)
    fig.text(0.04, 0.028, 'Prévia para guiar o layout no EasyEDA Pro (não é arquivo de fabricação; '
             'fazer o DRC lá). Baseado no EVA-RT © EXOTIC TEAM MX — AGPL-3.0.', color='#9fb0a8', fontsize=9)
    fig.savefig(out, dpi=210, facecolor=BG)
    print(out)


if __name__ == '__main__':
    main()
