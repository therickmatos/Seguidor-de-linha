"""Figura de conferencia do XT30 (J1) no canto traseiro esquerdo: vista de cima e corte.

Compara a posicao atual (A, na ampliacao do contorno) com o XT30 encostado no suporte
do motor esquerdo, na vertical (B) e deitado (C). Motor e bateria ficam por cima da placa.
Saida: hardware/preview/xt30_alternativas.jpg

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import math

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as effects
from matplotlib.patches import Circle, Rectangle, Polygon as PPoly

import layout_placa as M
import placa_v2 as V

BG = '#0f1317'; BOARD = '#173026'; WHITE = '#f3f5ee'; GRID = '#3c514a'
OK = '#7ed6a0'; BAD = '#ff6b6b'; CUR = '#f0c987'; MOTOR = '#c79bff'; BAT = '#6fb6ff'; GB = '#9aa7a0'

# medidas (mm)
XT_L, XT_W, XT_H = 10.214, 5.2, 10.2        # corpo do XT30 (comprimento, largura, altura estimada)
PAD_D, PAD_P = 3.9, 5.0                      # pads estimados e passo
SUP_IN, SUP_OUT = -30.5, -40.0               # suporte do motor esquerdo (faces interna/externa)
SUP_Y0, SUP_Y1 = -28.5, -1.8
MOT_Y, MOT_Z, MOT_R = -19.03, 7.64, 5.1      # eixo do motor (y, altura) e raio do furo do suporte
MOT_X0, MOT_X1 = -38.5, -18.5                # corpo 1020 (20 mm) saindo para dentro (estimado)
BATT = (-22.5, -42.6, 22.5, -22.1, 3.0, 15.0)  # x0, y0, x1, y1, z0, z1
EDGE_Y = -28.5                               # borda traseira entre x -28,9 e -22,25
CLR = 0.3                                    # cobre-borda


def n(v):
    return f'{v:.1f}'.replace('.', ',')


def stroke(t, w=2.0):
    t.set_path_effects([effects.withStroke(linewidth=w, foreground=BG)])
    return t


def dim(ax, p0, p1, text, color=WHITE, off=(0, 0), fs=8, ha='center'):
    ax.annotate('', xy=p1, xytext=p0, arrowprops=dict(arrowstyle='<->', color=color, lw=0.9,
                                                      shrinkA=0, shrinkB=0), zorder=30)
    mx, my = (p0[0] + p1[0]) / 2 + off[0], (p0[1] + p1[1]) / 2 + off[1]
    stroke(ax.text(mx, my, text, color=color, fontsize=fs, ha=ha, va='center', zorder=31))


def xt30_top(ax, cx, cy, rot, color, label, ls='-'):
    w, h = (XT_L, XT_W) if rot == 0 else (XT_W, XT_L)
    ax.add_patch(Rectangle((cx - w / 2, cy - h / 2), w, h, fill=True, fc=color, alpha=.18,
                           ec=color, lw=1.6, ls=ls, zorder=20))
    for s in (-1, 1):
        px, py = (cx + s * PAD_P / 2, cy) if rot == 0 else (cx, cy + s * PAD_P / 2)
        ax.add_patch(Circle((px, py), PAD_D / 2, fc='none', ec=color, lw=1.0, zorder=21))
        ax.add_patch(Circle((px, py), 1.25, fc=color, alpha=.5, ec='none', zorder=21))
    stroke(ax.text(cx, cy, label, color=color, fontsize=13, fontweight='bold', ha='center',
                   va='center', zorder=25), 3)
    return cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2


def main():
    fig = plt.figure(figsize=(16, 15.5), dpi=170, facecolor=BG)
    ax = fig.add_axes([0.06, 0.40, 0.90, 0.50])
    ax2 = fig.add_axes([0.06, 0.07, 0.90, 0.27])
    for a in (ax, ax2):
        a.set_facecolor(BG)
        a.tick_params(colors='#9fb0a8', labelsize=8)
        for s in a.spines.values():
            s.set_color('#4a5a54')
        a.grid(color=GRID, alpha=.35, lw=.4)

    # ---------------------------------------------------------------- vista de cima
    x0, x1, y0, y1 = -46, 34, -44, -6
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal')
    ax.set_xticks(range(-45, 35, 5)); ax.set_yticks(range(-40, -5, 5))
    orig = PPoly(M.BOARD_DATA['contorno'], closed=True, fc='none', ec='#e1e7db', lw=.8, ls=(0, (4, 3)), zorder=3)
    from figura_v2 import poly
    poly(ax, M.BOARD, facecolor=BOARD, edgecolor='#dfe6da', lw=1.0, zorder=1)
    ax.add_patch(orig)
    # componentes reais (baixos) para referencia
    pos = V.load()
    for c in pos:
        if c['face'] != 'TOP' or not (x0 < c['x'] < x1 and y0 < c['y'] < y1):
            continue
        for p in M.get_pads(c):
            poly(ax, p['shape'], facecolor='#5e5440', edgecolor='none', zorder=4)
    for name in ('suporte_motor_E_tras', 'suporte_motor_E_frente', 'suporte_motor_D_tras', 'carcaca_SO', 'carcaca_SE'):
        h = next(h for h in M.BOARD_DATA['furos'] if h['nome'] == name)
        ax.add_patch(Circle((h['x'], h['y']), h['d'] / 2, fc=BG, ec='#dfe6da', lw=.8, zorder=5))
    # suportes dos motores (em cima, apoiados na placa)
    for xa, xb in ((SUP_OUT, SUP_IN), (-SUP_IN, -SUP_OUT)):
        ax.add_patch(Rectangle((xa, SUP_Y0), xb - xa, SUP_Y1 - SUP_Y0, fc=GB, alpha=.22, ec=GB, lw=1.2, zorder=6))
    stroke(ax.text(-35.25, -14.0, 'suporte do\nmotor esq.\n(apoiado na placa)', color=GB, fontsize=8,
                   ha='center', va='center', zorder=8))
    stroke(ax.text(32.6, -14.0, 'suporte\ndir.', color=GB, fontsize=8, ha='center', zorder=8))
    # motor esquerdo (por cima, 2,6..12,7 mm)
    ax.add_patch(Rectangle((MOT_X0, MOT_Y - MOT_R), MOT_X1 - MOT_X0, 2 * MOT_R, fc=MOTOR, alpha=.18,
                           ec=MOTOR, lw=1.4, ls=(0, (5, 3)), zorder=10))
    stroke(ax.text(-24.0, MOT_Y + 2.2, 'motor esq. 1020 (por cima: 2,5 a 12,7 mm de altura)', color=MOTOR,
                   fontsize=8.5, ha='center', zorder=12))
    ax.plot([MOT_X0, MOT_X1], [MOT_Y, MOT_Y], color=MOTOR, lw=.6, ls='-.', zorder=11)
    # bateria (por cima, 3..15 mm)
    bx0, by0, bx1, by1, bz0, bz1 = BATT
    ax.add_patch(Rectangle((bx0, by0), bx1 - bx0, by1 - by0, fc=BAT, alpha=.13, ec=BAT, lw=1.4,
                           ls=(0, (5, 3)), zorder=9))
    stroke(ax.text(0, -38.5, 'bateria 45 × 20,5 mm (por cima: 3 a 15 mm de altura)', color=BAT, fontsize=8.5,
                   ha='center', zorder=12))

    # A: posicao atual (na ampliacao do contorno)
    a = xt30_top(ax, -35.5, -31.7, 0, CUR, 'A')
    # B: vertical, encostado no suporte, pads a 0,3 mm da borda
    cyB = EDGE_Y + CLR + PAD_D / 2 + PAD_P / 2
    b = xt30_top(ax, SUP_IN + XT_W / 2, cyB, 90, BAD, 'B')
    # C: deitado, encostado no suporte, pads a 0,3 mm da borda
    cyC = EDGE_Y + CLR + PAD_D / 2
    c = xt30_top(ax, SUP_IN + XT_L / 2, cyC, 0, BAD, 'C', ls=(0, (2, 2)))

    # cotas
    dim(ax, (b[2], -9.0), (-SUP_IN, -9.0), f'{n(-SUP_IN - b[2])} mm (fim do XT30 em B → suporte dir.)', off=(0, 0.8))
    ax.plot([b[2], b[2]], [b[3], -8.0], color=WHITE, lw=.5, ls=':', zorder=29)
    ax.plot([-SUP_IN, -SUP_IN], [SUP_Y1, -8.0], color=WHITE, lw=.5, ls=':', zorder=29)
    dim(ax, (SUP_IN, -7.2), (-SUP_IN, -7.2), f'{n(2 * -SUP_IN)} mm entre os suportes', off=(0, 0.75), color='#c7d2cc')
    dim(ax, (b[2], -23.2), (bx0, -23.2), f'{n(bx0 - b[2])}', off=(1.3, 0.0), color=BAT, ha='left')
    dim(ax, (-21.0, MOT_Y - MOT_R), (-21.0, EDGE_Y), f'{n(MOT_Y - MOT_R - EDGE_Y)} mm livres\natrás do motor',
        off=(3.2, 0), color=OK, ha='left')
    dim(ax, (-45.0, a[3]), (-45.0, SUP_Y0), f'{n(SUP_Y0 - a[3])}', off=(0.9, 0), color=CUR, fs=7.5, ha='left')
    stroke(ax.text(b[0] - 0.3, b[3] + 0.4, f'B invade o motor\nem {n(b[3] - (MOT_Y - MOT_R))} mm (y)',
                   color=BAD, fontsize=8, ha='right', va='bottom', zorder=32))
    stroke(ax.text(c[2] + 0.4, c[1] - 0.2, f'C invade a bateria em {n(c[2] - bx0)} mm (x)\n'
                   f'e o motor em {n(c[3] - (MOT_Y - MOT_R))} mm (y)', color=BAD, fontsize=8,
                   ha='left', va='top', zorder=32))
    stroke(ax.text(a[0], a[1] - 0.6, 'A: atual, livre de motor e bateria (corpo sai 0,6 mm além do suporte em x)',
                   color=CUR, fontsize=8, ha='left', va='top', zorder=32))
    ax.text(x0 + 0.5, y1 - 0.8, 'VISTA DE CIMA', color=WHITE, fontsize=11, fontweight='bold', va='top')

    # ---------------------------------------------------------------- corte x = centro de B
    xc = SUP_IN + XT_W / 2
    ax2.set_xlim(-44, -6); ax2.set_ylim(-3, 17); ax2.set_aspect('equal')
    ax2.set_xlabel('y (mm) — frente para a direita', color='#9fb0a8', fontsize=8)
    ax2.set_ylabel('altura sobre a placa (mm)', color='#9fb0a8', fontsize=8)
    ax2.add_patch(Rectangle((EDGE_Y, -1.6), 40, 1.6, fc=BOARD, ec='#dfe6da', lw=.8, zorder=2))
    ax2.add_patch(Rectangle((EDGE_Y - 40, -1.6), 40, 1.6, fc='none', ec='#dfe6da', lw=.6, ls=':', zorder=2))
    stroke(ax2.text(EDGE_Y + 0.2, -2.6, 'borda da placa (y = −28,5) · placa à direita', color='#dfe6da', fontsize=8))
    ax2.add_patch(Circle((MOT_Y, MOT_Z), MOT_R, fc=MOTOR, alpha=.2, ec=MOTOR, lw=1.4, zorder=5))
    stroke(ax2.text(MOT_Y, MOT_Z, 'motor\nØ10', color=MOTOR, fontsize=9, ha='center', va='center', zorder=6))
    ax2.add_patch(Rectangle((by0, bz0), by1 - by0, bz1 - bz0, fc='none', ec=BAT, lw=1.0, ls=(0, (5, 3)), zorder=4))
    stroke(ax2.text((by0 + by1) / 2, 9, 'bateria\n(só para x > −22,5;\nnão está neste corte)', color=BAT,
                    fontsize=8, ha='center', va='center', zorder=6))
    ax2.add_patch(Rectangle((b[1], 0), b[3] - b[1], XT_H, fc=BAD, alpha=.18, ec=BAD, lw=1.6, zorder=7))
    stroke(ax2.text((b[1] + b[3]) / 2, XT_H + 0.6, 'B (vertical, ~10 mm de altura)', color=BAD, fontsize=9, ha='center', zorder=8))
    ax2.add_patch(Rectangle((c[1], 0), c[3] - c[1], XT_H, fc='none', ec=BAD, lw=1.2, ls=(0, (2, 2)), zorder=7))
    stroke(ax2.text((c[1] + c[3]) / 2, -2.6 + 0.0, '', color=BAD))
    dim(ax2, (-12.0, 0), (-12.0, MOT_Z - MOT_R + 0.06), f'{n(MOT_Z - MOT_R)} mm livres sob o motor', off=(0.5, 0),
        color=MOTOR, ha='left')
    ax2.plot([-12.6, MOT_Y], [MOT_Z - MOT_R, MOT_Z - MOT_R], color=MOTOR, lw=.5, ls=':')
    dim(ax2, (EDGE_Y, 13.6), (MOT_Y - MOT_R, 13.6), n(MOT_Y - MOT_R - EDGE_Y), off=(0, 0.7), color=OK)
    dim(ax2, (b[1], 11.6), (b[3], 11.6), n(XT_L), off=(0, 0.7), color=BAD)
    ax2.set_title(f'CORTE EM x = {n(xc)} (centro de B), visto da esquerda', color=WHITE, fontsize=11,
                  fontweight='bold', loc='left')

    fig.text(0.06, 0.965, 'XT30 (J1) NO CANTO TRASEIRO ESQUERDO — ALTERNATIVAS', color=WHITE, fontsize=17,
             fontweight='bold')
    fig.text(0.06, 0.945, 'A = posição atual (na ampliação do contorno) · B = vertical encostado no suporte · '
             'C = deitado encostado no suporte. B e C com os pads a 0,3 mm da borda (y = −28,5).',
             color='#c7d2cc', fontsize=10)
    fig.text(0.06, 0.928, 'Contorno tracejado = original; preenchido = atual (com a ampliação até y = −35). '
             'mm, origem no centro da ventoinha, +y = frente.', color='#c7d2cc', fontsize=10)
    fig.text(0.06, 0.035, 'Fontes: furo do motor Ø10,2 com eixo em y −19,03 e 7,6 mm de altura (gearbox.stl); corpo do 1020 '
             'saindo 20 mm para dentro (decisão de 05/11: motores sobre os drivers) — extensão em x estimada. '
             'XT30: corpo 10,2 × 5,2 da foto, altura ~10 e pads Ø3,9 estimados.', color='#9fb0a8', fontsize=8.5,
             wrap=True)
    fig.text(0.06, 0.018, 'Baseado no EVA-RT © EXOTIC TEAM MX — AGPL-3.0.', color='#9fb0a8', fontsize=8.5)
    out = M.OUTPUT / 'xt30_alternativas.jpg'
    fig.savefig(out, dpi=170, facecolor=BG)
    print(out)


if __name__ == '__main__':
    main()
