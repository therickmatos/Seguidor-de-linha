"""Vista de cima da placa v2 so com posicoes (sem trilhas) + mecanica do EVA-RT e detalhe do XT30.

Saida: hardware/preview/posicao_v2.jpg. Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as effects
from matplotlib.patches import Circle, Polygon as PPoly

import layout_placa as M
import placa_v2 as V
from figura_v2 import poly
from figura_xt30 import (BG, BOARD, WHITE, GRID, OK, MOTOR, BAT, GB, CUR, SUP_IN, SUP_OUT, SUP_Y0, SUP_Y1,
                         MOT_X0, MOT_X1, MOT_Y0, MOT_Y1, BATT, dim, rect, n, stroke)

GEAR = '#ff8a3d'; TIRE = '#8b8f96'; BOT = '#6fb6ff'; PADC = '#f0c987'
AXLE_Y = -22.59


def mecanica(ax):
    for s in (1, -1):
        xa, xb = sorted((s * SUP_OUT, s * SUP_IN))
        rect(ax, xa, SUP_Y0, xb, SUP_Y1, fc=GB, alpha=.16, ec=GB, lw=1.0, zorder=3)
        xa, xb = sorted((s * MOT_X0, s * MOT_X1))
        rect(ax, xa, MOT_Y0, xb, MOT_Y1, fc=MOTOR, alpha=.10, ec=MOTOR, lw=1.0, ls=(0, (5, 3)), zorder=3)
        xa, xb = sorted((s * 40.0, s * 42.0))
        rect(ax, xa, AXLE_Y - 9.9, xb, AXLE_Y + 9.9, fc=GEAR, alpha=.25, ec=GEAR, lw=1.2, zorder=3)
        xa, xb = sorted((s * 42.0, s * 60.5))
        rect(ax, xa, AXLE_Y - 10.75, xb, AXLE_Y + 10.75, fc='none', ec=TIRE, lw=1.0, ls=(0, (4, 3)), zorder=3)
    bx0, by0, bx1, by1, _, _ = BATT
    rect(ax, bx0, by0, bx1, by1, fc=BAT, alpha=.08, ec=BAT, lw=1.0, ls=(0, (5, 3)), zorder=3)
    ax.add_patch(Circle((0, 0), 17.0, fc='none', ec='#c9cdd3', lw=.8, ls=(0, (2, 3)), zorder=3))
    ax.plot([-45, 45], [AXLE_Y, AXLE_Y], color='#dfe6da', lw=.5, ls='-.', alpha=.5, zorder=3)


def placa(ax, pos, labels=True, fs=4.6):
    poly(ax, M.BOARD, facecolor=BOARD, edgecolor='#dfe6da', lw=1.0, zorder=1)
    ax.add_patch(PPoly(M.BOARD_DATA['contorno'], closed=True, fc='none', ec='#e1e7db', lw=.6,
                       ls=(0, (4, 3)), alpha=.7, zorder=2))
    for c in pos:
        top = c['face'] == 'TOP'
        col = PADC if top else BOT
        for p in M.get_pads(c):
            poly(ax, p['shape'], facecolor=col, edgecolor='none', alpha=1 if top else .55, zorder=5 if top else 4)
            if p['furo']:
                ax.add_patch(Circle((p['x'], p['y']), p['furo'] / 2, color=BG, zorder=6))
            if p['pin'] == '1' and c['ref'] not in ('M1', 'M2', 'M3'):
                ax.add_patch(Circle((p['x'], p['y']), .16, color='white', zorder=7))
        b = M.body(c)
        if b is not None and c['ref'] not in ('M1', 'M2', 'M3'):
            poly(ax, b, facecolor='none', edgecolor=WHITE if top else BOT, lw=.45,
                 ls='-' if top else (0, (2, 2)), alpha=.7, zorder=6)
        (vx0, vx1), (vy0, vy1) = ax.get_xlim(), ax.get_ylim()
        if labels and vx0 < c['x'] < vx1 and vy0 < c['y'] < vy1:
            bb = b.bounds if b is not None else (c['x'] - 1, c['y'] - 1, c['x'] + 1, c['y'] + 1)
            stroke(ax.text(c['x'], bb[3] + .45, c['ref'], fontsize=fs, color=WHITE if top else BOT,
                           ha='center', va='bottom', fontweight='bold', zorder=20, clip_on=True), 1.4)


def main():
    pos = V.load()
    fig = plt.figure(figsize=(20, 14.6), dpi=200, facecolor=BG)
    ax = fig.add_axes([0.04, 0.32, 0.92, 0.58])
    ax2 = fig.add_axes([0.04, 0.05, 0.50, 0.24])
    for a in (ax, ax2):
        a.set_facecolor(BG); a.set_aspect('equal')
        a.tick_params(colors='#9fb0a8', labelsize=7)
        for s in a.spines.values():
            s.set_color('#4a5a54')
        a.grid(color=GRID, alpha=.3, lw=.35)
    ax.set_xlim(-76, 76); ax.set_ylim(-37, 27)
    ax.set_xticks(range(-75, 76, 5)); ax.set_yticks(range(-35, 26, 5))
    ax2.set_xlim(-44, -14); ax2.set_ylim(-37, -14)
    mecanica(ax); placa(ax, pos)
    for (x, y, t, c) in [(-51.0, -24.0, 'roda/pneu\n(estimado)', TIRE), (-41.0, -9.5, 'engrenagem\n64T', GEAR),
                         (-28.0, -5.2, 'motor', MOTOR), (0, -40.0 + 4.6, 'bateria', BAT), (12.5, 13.2, 'rotor Ø34', '#c9cdd3')]:
        stroke(ax.text(x, y, t, color=c, fontsize=8, ha='center', va='center', zorder=21), 2)

    # detalhe do XT30 em pe no degrau esquerdo
    mecanica(ax2); placa(ax2, pos, fs=7)
    f = V.folgas_j1(pos)
    j1 = next(c for c in pos if c['ref'] == 'J1')
    x0, y0, x1, y1 = f['corpo']
    dim(ax2, (SUP_IN, -20.5), (x0, -20.5), n(f['corpo_suporte']), off=(0, 0.55), color=GB, fs=7.5)
    dim(ax2, (x0 + 0.5, y1), (x0 + 0.5, MOT_Y0), f"{n(f['corpo_motor'])} até o motor", off=(-0.3, 0), color=MOTOR,
        fs=7.5, ha='right')
    dim(ax2, (x1, -24.0), (-22.5, -24.0), n(f['corpo_bateria']), off=(0, 0.55), color=BAT, fs=7.5)
    stroke(ax2.text(-22.3, -25.4, 'bateria', color=BAT, fontsize=7.5, va='top'), 2)
    ax2.set_title('DETALHE: J1 (XT30) EM PÉ NO DEGRAU ESQUERDO', color=WHITE, fontsize=10, fontweight='bold', loc='left')
    stroke(ax2.text(-43.6, -36.4, f"pads Ø3,9 a {n(f['cobre_borda'])} mm da borda (y = −28,5); pino 1 (+) para a "
                    "frente; tracejado = contorno B original (degrau em −28,5)", color=CUR, fontsize=7.5), 2)

    fig.text(0.04, 0.955, 'PLACA BASE — VERSÃO ALPHA · POSIÇÕES', color=WHITE, fontsize=18, fontweight='bold')
    fig.text(0.04, 0.935, f'J1 (XT30) em pé em ({n(j1["x"])}; {n(j1["y"])}), eixo longo em y, por dentro do suporte '
             f'esquerdo: {n(f["corpo_suporte"])} mm do suporte, {n(f["corpo_motor"])} mm do motor, '
             f'{n(f["corpo_bateria"])} mm da bateria e {n(f["corpo_engrenagem"])} mm do plano da engrenagem. '
             'Traseira reta em y = −33 (pés do EVA-RT estendidos); chaves 3 × 6 (TC-3610).', color='#c7d2cc', fontsize=10.5)
    fig.text(0.04, 0.918, 'Bege = pads da face de cima, contorno branco = corpo; azul tracejado = face de baixo '
             '(vista através da placa); ponto branco = pino 1. Contorno tracejado = original do contorno B. '
             'Grade de 5 mm, +y = frente.', color='#c7d2cc', fontsize=10.5)
    lx = 0.58
    for i, (t, c) in enumerate([
            ('Suportes dos motores, motores (Ø10 × 20, eixo em y −11,26) e eixo das rodas (y −22,59): '
             'EVA_RT.eprj (camada Document) + gearbox.stl', GB),
            ('Engrenagem 64T M0,3 (Ø19,8 × 2) em |x| 40…42: estimada pelo README do EVA-RT', GEAR),
            ('Pneus (rolos de impressora) e posição das rodas em x: estimados', TIRE),
            ('Bateria GNB 350 2S 45 × 20,5: frente em y −22,1 (anel da carcaça), 3 mm acima da placa', BAT),
            ('XT30U-M (C99101, de cabo): corpo 10,2 × 5,2 da foto; pads Ø3,9 e furos Ø2,5 estimados — medir os '
             'copos e cortar rente embaixo', CUR),
            ('Conferir no conjunto real a folga do XT30 até a face interna do suporte e até o motor', WHITE)]):
        fig.text(lx, 0.265 - i * 0.032, '■ ' + t, color=c, fontsize=9.5, wrap=True)
    fig.text(0.04, 0.018, 'Baseado no EVA-RT © EXOTIC TEAM MX — AGPL-3.0.', color='#9fb0a8', fontsize=9)
    out = M.OUTPUT / 'posicao_v2.jpg'
    fig.savefig(out, dpi=200, facecolor=BG)
    print(out)


if __name__ == '__main__':
    main()
