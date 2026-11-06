"""Onde cabem botoes 6x6x4,5 THT de 2 pinos na placa alpha (sem mexer nos outros componentes).

Saida: hardware/preview/botoes_6x6.jpg. Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

import layout_placa as M
import placa_v2 as V
from figura_posicao import mecanica, placa
from figura_xt30 import BG, WHITE, GRID, stroke

OK, MEH, CUR = '#7ed6a0', '#f0c35a', '#ff6b6b'
# (rotulo, x, y, rot, cor, texto)
CAND = [('SW0', 34.0, -32.0, 0, OK, 'A: reset no lóbulo traseiro direito\n(só se os pinos ficarem no meio dos lados)'),
        ('SW1?', 54.0, 4.5, 0, MEH, 'B: braço direito\n(o braço flexiona ao apertar)'),
        ('SW2?', -54.0, 4.5, 0, MEH, 'C: braço esquerdo'),
        ('SW?', -37.0, 9.0, 90, MEH, 'D: frente esquerda,\nao lado do U5'),
        ('SW?', -27.0, -23.25, 90, MEH, 'E: vão entre o suporte\ne a bateria (acesso ruim)')]


def main():
    pos = V.load()
    fig = plt.figure(figsize=(20, 11.5), dpi=180, facecolor=BG)
    ax = fig.add_axes([0.04, 0.12, 0.92, 0.74])
    ax.set_facecolor(BG); ax.set_aspect('equal')
    ax.tick_params(colors='#9fb0a8', labelsize=7)
    for s in ax.spines.values():
        s.set_color('#4a5a54')
    ax.grid(color=GRID, alpha=.3, lw=.35)
    ax.set_xlim(-76, 76); ax.set_ylim(-37, 27)
    ax.set_xticks(range(-75, 76, 5)); ax.set_yticks(range(-35, 26, 5))
    mecanica(ax); placa(ax, pos)
    for ref, x, y, rot, cor, txt in CAND:
        ax.add_patch(Rectangle((x - 3, y - 3), 6, 6, fc=cor, alpha=.25, ec=cor, lw=1.6, zorder=30))
        for s in (-1, 1):
            px, py = (x + s * 3.25, y) if rot == 0 else (x, y + s * 3.25)
            ax.add_patch(Circle((px, py), 1.0, fc='none', ec=cor, lw=1.2, zorder=31))
        dy = -5.0 if y > -10 else 4.2
        stroke(ax.text(x, y + dy, txt, color=cor, fontsize=8.5, ha='center', va='center', zorder=32), 2)
    for c in pos:
        if c['ref'] in ('SW0', 'SW1', 'SW2'):
            ax.add_patch(Circle((c['x'], c['y']), 2.6, fc='none', ec=CUR, lw=1.2, ls=(0, (2, 2)), zorder=29))
    fig.text(0.04, 0.95, 'BOTÕES 6×6×4,5 THT (2 PINOS) — ONDE CABEM SEM MEXER NO RESTO', color=WHITE,
             fontsize=17, fontweight='bold')
    fig.text(0.04, 0.925, 'Busca automática numa grade de 0,5 mm: corpo 6 × 6 sem tocar componentes, rotor, carcaça, bateria, '
             'motores, suportes, engrenagens e presilhas; pinos fora da placa de sucção e dos componentes da face de baixo.',
             color='#c7d2cc', fontsize=10)
    fig.text(0.04, 0.905, 'Círculo vermelho tracejado = B3U atuais (SW0 reset, SW1, SW2). Verde = cabe bem; amarelo = cabe, '
             'mas com ressalva. Na frente direita (lugar do SW1/SW2) não cabe: J4, Q1, LED4, C2 e o motor M2 ocupam a área.',
             color='#c7d2cc', fontsize=10)
    fig.text(0.04, 0.06, 'Pinos supostos a 6,5 mm, no meio de dois lados opostos; com pinos em diagonal, a posição A não '
             'cabe. Medir o botão real.', color='#9fb0a8', fontsize=9.5)
    fig.text(0.04, 0.04, 'Baseado no EVA-RT © EXOTIC TEAM MX — AGPL-3.0.', color='#9fb0a8', fontsize=9)
    out = M.OUTPUT / 'botoes_6x6.jpg'
    fig.savefig(out, dpi=180, facecolor=BG)
    print(out)


if __name__ == '__main__':
    main()
