"""Figura de conferencia do XT30 (J1) no canto traseiro esquerdo: vista de cima e corte.

Compara a posicao atual (A, na ampliacao do contorno) com o XT30 encostado no suporte
do motor esquerdo, na vertical (B) e deitado (C). Saida: hardware/preview/xt30_alternativas.jpg

Fonte da posicao dos suportes e motores: camada Document do EVA_RT.eprj, grupos GBX_A
(esquerdo) e GBX_B (direito): suporte x 30,5..40 / y -28,5..-1,78; abraçadeira do motor
y -17,83..-4,68; mancal do eixo y -25,57..-19,62; corpo do motor 20 x 10 em x 18..38,
y -16,26..-6,26 (eixo em y -11,26); linha do eixo das rodas em y -22,6. A altura do motor
(furo de 10,2 mm com fundo a 2,55 mm da placa) vem do gearbox.stl.

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as effects
from matplotlib.patches import Circle, Rectangle, Polygon as PPoly

import layout_placa as M
import placa_v2 as V
from figura_v2 import poly

BG = '#0f1317'; BOARD = '#173026'; WHITE = '#f3f5ee'; GRID = '#3c514a'
OK = '#7ed6a0'; BAD = '#ff6b6b'; CUR = '#f0c987'; MOTOR = '#c79bff'; BAT = '#6fb6ff'; GB = '#9aa7a0'

MIL = 0.0254
XT_L, XT_W, XT_H = 10.214, 5.2, 10.2         # corpo do XT30 (comprimento, largura, altura estimada)
PAD_D, PAD_P = 3.9, 5.0                       # pads estimados e passo
SUP_IN, SUP_OUT, SUP_Y0, SUP_Y1 = -30.5, -40.0, -28.5, -1.78   # e15 (GBX_A)
CLAMP_Y = (-17.83, -4.68)                     # e17: abraçadeira do motor
BEAR_Y = (-25.57, -19.62)                     # e20: mancal do eixo
MOT_X0, MOT_X1, MOT_Y0, MOT_Y1 = -38.0, -18.0, -16.26, -6.26   # e18: corpo do motor
MOT_Y = (MOT_Y0 + MOT_Y1) / 2
MOT_Z, MOT_R = 7.64, 5.1                      # altura do eixo e raio (gearbox.stl)
AXLE_Y = -22.6                                # e1358: eixo das rodas
BATT = (-22.5, -42.6, 22.5, -22.1, 3.0, 15.0)  # GNB 350 2S deitada (hipotese do preview)
EVA_BATT = (-29.0, -33.83, 29.0, -20.83)      # e182: bateria do EVA-RT (58 x 13)
EDGE_Y = -28.5
CLR = 0.3


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


def rect(ax, x0, y0, x1, y1, **kw):
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, **kw))


def xt30_top(ax, cx, cy, rot, color, label, ls='-'):
    w, h = (XT_L, XT_W) if rot == 0 else (XT_W, XT_L)
    rect(ax, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, fc=color, alpha=.18, ec=color, lw=1.6,
         ls=ls, zorder=20)
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
    ax2 = fig.add_axes([0.06, 0.075, 0.90, 0.26])
    for a in (ax, ax2):
        a.set_facecolor(BG)
        a.tick_params(colors='#9fb0a8', labelsize=8)
        for s in a.spines.values():
            s.set_color('#4a5a54')
        a.grid(color=GRID, alpha=.35, lw=.4)

    # ---------------------------------------------------------------- vista de cima
    x0, x1, y0, y1 = -46, 34, -44, -2
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal')
    ax.set_xticks(range(-45, 35, 5)); ax.set_yticks(range(-40, 0, 5))
    poly(ax, M.BOARD, facecolor=BOARD, edgecolor='#dfe6da', lw=1.0, zorder=1)
    ax.add_patch(PPoly(M.BOARD_DATA['contorno'], closed=True, fc='none', ec='#e1e7db', lw=.8,
                       ls=(0, (4, 3)), zorder=3))
    for c in V.load():
        if c['face'] == 'TOP' and x0 < c['x'] < x1 and y0 < c['y'] < y1:
            for p in M.get_pads(c):
                poly(ax, p['shape'], facecolor='#5e5440', edgecolor='none', zorder=4)
    for h in M.BOARD_DATA['furos']:
        if h['tipo'] == 'furo' and x0 < h['x'] < x1 and y0 < h['y'] < y1:
            ax.add_patch(Circle((h['x'], h['y']), h['d'] / 2, fc=BG, ec='#dfe6da', lw=.8, zorder=5))
    for sx in (1, -1):        # suportes (e15/e24), abraçadeira e mancal
        xa, xb = sorted((sx * SUP_OUT, sx * SUP_IN))
        rect(ax, xa, SUP_Y0, xb, SUP_Y1, fc=GB, alpha=.20, ec=GB, lw=1.2, zorder=6)
        for ya, yb in (CLAMP_Y, BEAR_Y):
            rect(ax, xa, ya, xb, yb, fc='none', ec=GB, lw=.7, ls=':', zorder=7)
    stroke(ax.text(-35.25, -8.5, 'suporte do\nmotor esq.', color=GB, fontsize=8, ha='center', zorder=8))
    stroke(ax.text(-35.25, -22.6, 'mancal', color=GB, fontsize=7, ha='center', va='center', zorder=8))
    stroke(ax.text(32.5, -8.5, 'suporte\ndir.', color=GB, fontsize=8, ha='center', zorder=8))
    ax.plot([-40, 40], [AXLE_Y, AXLE_Y], color='#dfe6da', lw=.6, ls='-.', alpha=.6, zorder=8)
    stroke(ax.text(2.0, AXLE_Y + 0.4, 'eixo das rodas (y −22,6)', color='#c7d2cc', fontsize=7, zorder=9))
    for sx in (1, -1):        # motores (e18/e22)
        xa, xb = sorted((sx * MOT_X0, sx * MOT_X1))
        rect(ax, xa, MOT_Y0, xb, MOT_Y1, fc=MOTOR, alpha=.18, ec=MOTOR, lw=1.4, ls=(0, (5, 3)), zorder=10)
    stroke(ax.text(-28.0, MOT_Y1 + 0.6, 'motor esq. 1020 (por cima: 2,5 a 12,7 mm)', color=MOTOR,
                   fontsize=8.5, ha='center', zorder=12))
    bx0, by0, bx1, by1, bz0, bz1 = BATT
    rect(ax, bx0, by0, bx1, by1, fc=BAT, alpha=.13, ec=BAT, lw=1.4, ls=(0, (5, 3)), zorder=9)
    stroke(ax.text(0, -40.5, 'bateria GNB 350 2S 45 × 20,5 (por cima: 3 a 15 mm)', color=BAT, fontsize=8.5,
                   ha='center', zorder=12))
    ex0, ey0, ex1, ey1 = EVA_BATT
    rect(ax, ex0, ey0, ex1, ey1, fc='none', ec='#8fa0b8', lw=.8, ls=(0, (1, 2)), zorder=9)
    stroke(ax.text(ex1 - 0.5, ey0 + 0.5, 'bateria do EVA-RT (58 × 13)', color='#8fa0b8', fontsize=7,
                   ha='right', zorder=12))

    a = xt30_top(ax, -35.5, -31.7, 0, CUR, 'A')
    cyB = EDGE_Y + CLR + PAD_D / 2 + PAD_P / 2
    b = xt30_top(ax, SUP_IN + XT_W / 2, cyB, 90, OK, 'B')
    cyC = EDGE_Y + CLR + PAD_D / 2
    c = xt30_top(ax, SUP_IN + XT_L / 2, cyC, 0, BAD, 'C', ls=(0, (2, 2)))

    # cotas
    dim(ax, (b[2], -3.6), (-SUP_IN, -3.6), f'{n(-SUP_IN - b[2])} mm (fim do XT30 em B → suporte dir.)', off=(0, 0.8))
    ax.plot([b[2], b[2]], [b[3], -2.8], color=WHITE, lw=.5, ls=':', zorder=29)
    ax.plot([-SUP_IN, -SUP_IN], [SUP_Y1, -2.8], color=WHITE, lw=.5, ls=':', zorder=29)
    dim(ax, (b[2], -20.0), (bx0, -20.0), n(bx0 - b[2]), off=(1.0, 0.0), color=BAT, ha='left')
    dim(ax, (-27.9, b[3]), (-27.9, MOT_Y0), f'{n(MOT_Y0 - b[3])} mm até o motor', off=(0.4, 0),
        color=OK, ha='left')
    dim(ax, (-21.0, MOT_Y0), (-21.0, EDGE_Y), f'{n(MOT_Y0 - EDGE_Y)} mm livres\natrás do motor',
        off=(0.4, -3.0), color='#c7d2cc', ha='left')
    stroke(ax.text(c[2] + 0.4, c[1] - 0.3, f'C invade a bateria em {n(c[2] - bx0)} mm (x)', color=BAD,
                   fontsize=8, ha='left', va='top', zorder=32))
    stroke(ax.text(a[0], a[1] - 0.6, 'A: atual (na ampliação do contorno; o VIN do EVA-RT fica neste mesmo canto)',
                   color=CUR, fontsize=8, ha='left', va='top', zorder=32))
    ax.text(x0 + 0.5, y1 - 0.6, 'VISTA DE CIMA', color=WHITE, fontsize=11, fontweight='bold', va='top')

    # ---------------------------------------------------------------- corte x = centro de B
    xc = SUP_IN + XT_W / 2
    ax2.set_xlim(-44, -2); ax2.set_ylim(-3, 17); ax2.set_aspect('equal')
    ax2.set_xlabel('y (mm) — frente para a direita', color='#9fb0a8', fontsize=8)
    ax2.set_ylabel('altura sobre a placa (mm)', color='#9fb0a8', fontsize=8)
    rect(ax2, EDGE_Y, -1.6, 40, 0, fc=BOARD, ec='#dfe6da', lw=.8, zorder=2)
    stroke(ax2.text(EDGE_Y + 0.2, -2.6, 'borda da placa (y = −28,5) · placa à direita', color='#dfe6da',
                    fontsize=8))
    ax2.add_patch(Circle((MOT_Y, MOT_Z), MOT_R, fc=MOTOR, alpha=.2, ec=MOTOR, lw=1.4, zorder=5))
    stroke(ax2.text(MOT_Y, MOT_Z, 'motor\nØ10', color=MOTOR, fontsize=9, ha='center', va='center', zorder=6))
    rect(ax2, by0, bz0, by1, bz1, fc='none', ec=BAT, lw=1.0, ls=(0, (5, 3)), zorder=4)
    stroke(ax2.text((by0 + by1) / 2, 9, 'bateria\n(só para x > −22,5;\nnão está neste corte)', color=BAT,
                    fontsize=8, ha='center', va='center', zorder=6))
    rect(ax2, b[1], 0, b[3], XT_H, fc=OK, alpha=.18, ec=OK, lw=1.6, zorder=7)
    stroke(ax2.text((b[1] + b[3]) / 2, XT_H + 0.6, 'B (vertical, ~10 mm de altura)', color=OK, fontsize=9,
                    ha='center', zorder=8))
    dim(ax2, (b[3], 4.0), (MOT_Y - MOT_R, 4.0), n(MOT_Y - MOT_R - b[3]), off=(0, 0.7), color=OK)
    dim(ax2, (-4.0, 0), (-4.0, MOT_Z - MOT_R + 0.06), f'{n(MOT_Z - MOT_R)}', off=(0.4, 0), color=MOTOR, ha='left')
    ax2.plot([-4.6, MOT_Y], [MOT_Z - MOT_R, MOT_Z - MOT_R], color=MOTOR, lw=.5, ls=':')
    dim(ax2, (b[1], 12.2), (b[3], 12.2), n(XT_L), off=(0, 0.7), color=OK)
    ax2.set_title(f'CORTE EM x = {n(xc)} (centro de B), visto da esquerda', color=WHITE, fontsize=11,
                  fontweight='bold', loc='left')

    fig.text(0.06, 0.965, 'XT30 (J1) NO CANTO TRASEIRO ESQUERDO — com os motores na posição do EVA-RT',
             color=WHITE, fontsize=17, fontweight='bold')
    fig.text(0.06, 0.945, 'A = posição atual (na ampliação do contorno) · B = vertical encostado no suporte · '
             'C = deitado encostado no suporte. B e C com os pads a 0,3 mm da borda (y = −28,5).',
             color='#c7d2cc', fontsize=10)
    fig.text(0.06, 0.928, 'Contorno tracejado = original; preenchido = atual (com a ampliação até y = −35). '
             'mm, origem no centro da ventoinha, +y = frente.', color='#c7d2cc', fontsize=10)
    fig.text(0.06, 0.043, 'Fontes: suportes, abraçadeiras, mancais, motores (20 × 10, eixo em y −11,26) e eixo das '
             'rodas (y −22,6) desenhados na camada Document do EVA_RT.eprj (grupos GBX_A/GBX_B);',
             color='#9fb0a8', fontsize=8.5)
    fig.text(0.06, 0.030, 'altura do motor pelo gearbox.stl. XT30: corpo 10,2 × 5,2 da foto, altura ~10 e pads Ø3,9 '
             'estimados. Em B, deixar 0,3–0,5 mm de folga para a face do suporte.', color='#9fb0a8', fontsize=8.5)
    fig.text(0.06, 0.014, 'Baseado no EVA-RT © EXOTIC TEAM MX — AGPL-3.0.', color='#9fb0a8', fontsize=8.5)
    out = M.OUTPUT / 'xt30_alternativas.jpg'
    fig.savefig(out, dpi=170, facecolor=BG)
    print(out)
    print('B:', [round(v, 2) for v in b], 'motor y0', MOT_Y0, 'folga', round(MOT_Y0 - b[3], 2))


if __name__ == '__main__':
    main()
