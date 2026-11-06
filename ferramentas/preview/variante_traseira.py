"""Variante da traseira (06/11): contorno traseiro do EVA-RT (degraus) e XT30 em pe com o eixo longo em y.

A versao alpha alongou os dois cantos traseiros ate y = -35 para caber o XT30 (J1) deitado no canto
esquerdo. Aqui a traseira volta a ser a do contorno B original, que e a do EVA-RT: pes em y = -32 para
|x| 33..40, chanfro ate o degrau em y = -28,5 (|x| 22,3..28,9) e o centro em y = -30. O J1 vai para o
degrau esquerdo, encostado por dentro do suporte do motor (opcao "B" de DECISOES_2026-11-05), com o
chanfro do EVA-RT de cada lado. O SW0 continua no pe direito, na posicao do EVA-RT.

Nao altera a alpha: aplica a variante sobre os modulos em memoria e gera
  hardware/preview/traseira_eva_xt30.jpg   (posicoes, comparacao com a alpha e folgas do J1)
  hardware/preview/traseira_3d.html        (previa 3D so com posicoes)
Uso: python variante_traseira.py [--3d]

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import sys

from shapely.geometry import box
from shapely.ops import unary_union

import layout_placa as M
import placa_v2 as V

# (guardado no layout_placa: o exportar_3d importa este modulo de novo depois da variante aplicada)
OUTLINE_ALPHA = getattr(M, 'OUTLINE_ALPHA', M.OUTLINE)
# J1: corpo x -30,1..-24,9 (0,4 mm do suporte em x = -30,5), pad de tras a 0,3 mm da borda (y = -28,5)
J1_VAR = (-27.5, -23.7, 270, V.T, 'XT30 em pe, eixo longo em y, por dentro do suporte esq.; pino 1 (+, lado reto) '
          'para a frente, junto dos capacitores de VM do U2')
SUPORTE_E = box(-40, -28.5, -30.5, -1.78)
MOTOR_E = box(-38, -16.26, -18, -6.26)
BATERIA = box(-22.5, -42.6, 22.5, -22.1)
BORDA_DEGRAU = -28.5


def aplicar():
    M.OUTLINE_ALPHA = OUTLINE_ALPHA
    M.OUTLINE = M.OUTLINE_ORIGINAL
    M.BOARD = M.OUTLINE.difference(unary_union([g for _, g in M.HOLES]))
    V.POS['J1'] = J1_VAR


def folgas(pos):
    j1 = next(c for c in pos if c['ref'] == 'J1')
    corpo = M.body(j1)
    pads = M.get_pads(j1)
    cobre = unary_union([p['shape'] for p in pads])
    borda = M.OUTLINE.exterior
    vizinhos = []
    for c in pos:
        if c['ref'] in ('J1', 'M1', 'M2', 'M3') or c['face'] != 'TOP':
            continue
        b = M.body(c)
        g = unary_union([p['shape'] for p in M.get_pads(c)] + ([b] if b is not None else []))
        vizinhos.append((round(corpo.distance(g), 2), c['ref']))
    return {
        'corpo': [round(v, 2) for v in corpo.bounds],
        'pads': {p['pin']: [round(p['x'], 2), round(p['y'], 2), p['net']] for p in pads},
        'corpo_suporte': round(corpo.distance(SUPORTE_E), 2),
        'corpo_motor': round(corpo.distance(MOTOR_E), 2),
        'corpo_bateria': round(corpo.distance(BATERIA), 2),
        'cobre_borda': round(cobre.distance(borda), 2),
        'corpo_alem_da_borda': round(BORDA_DEGRAU - corpo.bounds[1], 2),
        'corpo_engrenagem': round(corpo.bounds[0] + 40, 2),
        'vizinho_mais_perto': sorted(vizinhos)[:3],
    }


def areas():
    a_alpha = OUTLINE_ALPHA.area
    a_var = M.OUTLINE_ORIGINAL.area
    tras = box(-80, -40, 80, -28)
    return {'placa_alpha_mm2': round(a_alpha), 'placa_variante_mm2': round(a_var),
            'retirado_mm2': round(a_alpha - a_var),
            'atras_de_y-28_alpha': round(OUTLINE_ALPHA.intersection(tras).area),
            'atras_de_y-28_variante': round(M.OUTLINE_ORIGINAL.intersection(tras).area)}


def figura(pos, f):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as PPoly
    import figura_posicao as FP
    from figura_xt30 import BG, GRID, WHITE, GB, MOTOR, BAT, CUR, dim, n, stroke

    ALPHA = '#ff8a8a'
    fig = plt.figure(figsize=(20, 14.0), dpi=200, facecolor=BG)
    ax = fig.add_axes([0.04, 0.36, 0.92, 0.53])
    ax2 = fig.add_axes([0.04, 0.05, 0.44, 0.27], anchor='E')
    ax3 = fig.add_axes([0.52, 0.05, 0.44, 0.27], anchor='W')
    for a in (ax, ax2, ax3):
        a.set_facecolor(BG); a.set_aspect('equal')
        a.tick_params(colors='#9fb0a8', labelsize=7)
        for s in a.spines.values():
            s.set_color('#4a5a54')
        a.grid(color=GRID, alpha=.3, lw=.35)
    ax.set_xlim(-76, 76); ax.set_ylim(-44, 27)
    ax.set_xticks(range(-75, 76, 5)); ax.set_yticks(range(-40, 26, 5))
    ax2.set_xlim(-44, -14); ax2.set_ylim(-37, -14)
    ax3.set_xlim(14, 44); ax3.set_ylim(-37, -14)
    for a, lab, fs in ((ax, True, 4.6), (ax2, True, 7), (ax3, True, 7)):
        FP.mecanica(a)
        FP.placa(a, pos, labels=lab, fs=fs)
        a.add_patch(PPoly(list(OUTLINE_ALPHA.exterior.coords), closed=True, fc='none', ec=ALPHA, lw=1.1,
                          ls=(0, (4, 2.5)), zorder=9))

    # cotas do J1 no detalhe
    x0, y0, x1, y1 = f['corpo']
    dim(ax2, (-30.5, -20.5), (x0, -20.5), n(f['corpo_suporte']), off=(0, 0.55), color=GB, fs=7.5)
    dim(ax2, (-29.4, y1), (-29.4, -16.26), f"{n(f['corpo_motor'])} até o motor", off=(-0.3, 0), color=MOTOR, fs=7.5,
        ha='right')
    dim(ax2, (x1, -24.0), (-22.5, -24.0), n(f['corpo_bateria']), off=(0, 0.55), color=BAT, fs=7.5)
    stroke(ax2.text(-22.3, -25.4, 'bateria', color=BAT, fontsize=7.5, va='top'), 2)
    ax2.set_title('DETALHE: J1 (XT30) EM PÉ NO DEGRAU ESQUERDO', color=WHITE, fontsize=10, fontweight='bold',
                  loc='left')
    stroke(ax2.text(-43.6, -36.4, f"pads Ø3,9 a {n(f['cobre_borda'])} mm da borda; corpo passa "
                    f"{n(f['corpo_alem_da_borda'])} mm do degrau (y = −28,5); pino 1 (+) para a frente",
                    color=CUR, fontsize=7.5), 2)
    ax3.set_title('PÉ DIREITO: SW0 NA POSIÇÃO DO EVA-RT', color=WHITE, fontsize=10, fontweight='bold', loc='left')
    stroke(ax3.text(15.4, -36.4, 'tracejado vermelho = contorno da alpha (lóbulo até y = −35)', color=ALPHA,
                    fontsize=7.5), 2)

    ar = areas()
    fig.text(0.04, 0.955, 'TRASEIRA DO EVA-RT + XT30 EM PÉ (eixo longo em y) — PROPOSTA, SÓ POSIÇÕES', color=WHITE,
             fontsize=18, fontweight='bold')
    fig.text(0.04, 0.935, 'Contorno = contorno B original, que tem a traseira do EVA-RT: pés em y = −32 (|x| 33…40), '
             'chanfro até o degrau em y = −28,5 (|x| 22,3…28,9) e centro em y = −30. '
             f'Tracejado vermelho = alpha (lóbulos até y = −35): saem {ar["retirado_mm2"]} mm² de placa.',
             color='#c7d2cc', fontsize=10.5)
    fig.text(0.04, 0.917, f'J1 em ({n(J1_VAR[0])}; {n(J1_VAR[1])}), girado 270°: corpo x {n(x0)}…{n(x1)}, '
             f'y {n(y0)}…{n(y1)}; {n(f["corpo_suporte"])} mm do suporte, {n(f["corpo_motor"])} mm do motor, '
             f'{n(f["corpo_bateria"])} mm da bateria e {n(f["corpo_engrenagem"])} mm do plano da engrenagem. '
             'Roteamento ainda não refeito.', color='#c7d2cc', fontsize=10.5)
    fig.text(0.04, 0.899, 'Bege = pads da face de cima, contorno branco = corpo; azul tracejado = face de baixo; '
             'ponto branco = pino 1. Cinza = suportes dos motores, roxo = motores, azul = bateria, laranja = '
             'engrenagens. Grade de 5 mm, +y = frente.', color='#c7d2cc', fontsize=10.5)
    fig.text(0.04, 0.018, 'Gerado por ferramentas/preview/variante_traseira.py. Baseado no EVA-RT © EXOTIC TEAM MX — '
             'AGPL-3.0.', color='#9fb0a8', fontsize=9)
    out = M.OUTPUT / 'traseira_eva_xt30.jpg'
    fig.savefig(out, dpi=200, facecolor=BG)
    print(out)


def main():
    aplicar()
    pos = V.load()
    prob = V.check(pos) + V.check_board()
    f = folgas(pos)
    j1 = next(c for c in pos if c['ref'] == 'J1')
    g = V.footprint_shape(j1)
    if g.intersects(SUPORTE_E):
        prob.append(('suporte do motor', 'J1'))
    print('problemas:', prob)
    print('J1:', f)
    print('areas:', areas())
    figura(pos, f)
    if '--3d' in sys.argv:
        import exportar_3d as E
        E.main(cobre=False, variante=True)
    return prob


if __name__ == '__main__':
    main()
