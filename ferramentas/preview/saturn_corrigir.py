"""Correcoes no ProPrj_RUSH_-_SATURN (versao editada pelo Erick no EasyEDA, 08/11/2026).

  python saturn_corrigir.py entrada.epro saida.epro

O DRC do EasyEDA deu 9 erros: 1 de netlist, 2 de via desconectada e 6 de folga do preenchimento do plano.
- netlist: a via termica e62 do U3 estava na rede "gnd" (minuscula) -> volta para GND;
- folga do preenchimento e vias desconectadas: o preenchimento salvo (linhas POURED) e anterior as
  ultimas edicoes de trilhas/vias (o plano encosta em trilhas que mudaram de lugar). As linhas POURED
  saem; o EasyEDA refaz o preenchimento ao reconstruir os planos (Shift+B);
- larguras (regra do Erick: pescoco de 0,4 mm por no maximo 1,5 mm na saida do DRV8874): o VBAT do U3.11
  e do U4.11 ficava com ~1,9 e ~1,65 mm de 0,4 mm -> trecho de 1,0 mm logo depois do pescoco;
- OUT_B2: dois pedacinhos de 0,25 mm (0,01 e 0,07 mm) que so se sobrepunham ao resto saem.
Nada mais muda (pecas, demais trilhas, vias e planos).

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import sys

import numpy as np
from shapely.geometry import LineString
from shapely.ops import unary_union

import easyeda_cobre as C
import easyeda_rotear as R


def alargar(placa, objs, pino, x0, borda_pad, y_fim, sentido, largura=1.0, pescoco_max=1.4):
    """Trecho vertical de `largura` mm que comeca logo depois do pescoco do `pino` (borda do pad em y =
    borda_pad, sentido +1 = para cima) e vai ate y_fim (cobre largo da mesma rede). Procura o x (perto de
    x0) com folga >= 0,2 do cobre de outras redes na face de cima."""
    net = 'VBAT'
    outros = unary_union([o['geom'] for o in objs if C.TOP in o['layers'] and o['net'] != net])
    melhor = None
    for dx in np.arange(-0.6, 0.61, 0.02):
        x = x0 + dx
        for dy in np.arange(0.3, pescoco_max + 0.01, 0.05):
            y_ini = borda_pad + sentido * (dy + largura / 2)   # centro da ponta do trecho largo
            g = LineString([(x, y_ini), (x, y_fim)]).buffer(largura / 2, quad_segs=12)
            if outros.distance(g) < 0.2 + 0.01:
                continue
            # tem de encostar no pescoco (x0) para ficar ligado
            if abs(x - x0) > largura / 2 - 0.1:
                continue
            nota = (round(dy, 2), abs(dx))
            if melhor is None or nota < melhor[0]:
                melhor = (nota, x, y_ini)
            break
    if melhor is None:
        raise SystemExit(f'sem lugar para alargar o VBAT do {pino}')
    (dy, _), x, y_ini = melhor
    print(f'{pino}: trecho de {largura} mm em x = {x:.2f}, de y = {y_ini:.2f} a {y_fim:.2f}; pescoco exposto ~{dy:.2f} mm')
    # trecho largo + conector de 0,4 mm do eixo do pescoco ate a ponta dele (ligacao ponta a ponta; o
    # conector fica dentro do cobre que ja existe)
    return [{'net': net, 'layer': C.TOP, 'w': largura, 'pts': [(x, y_ini), (x, y_fim)]},
            {'net': net, 'layer': C.TOP, 'w': 0.4, 'pts': [(x0, y_ini), (x, y_ini)]}]


def main(entrada, saida):
    placa = C.Placa(entrada)
    objs = placa.objetos()
    pads = {f"{p['des']}.{p['num']}": p for p in placa.pads}
    novas = []
    # U3.11: pad de y -16,197 a -14,45 (fileira de baixo); a barra do C11/C13 fica em y -18,75
    p = pads['U3.11']
    novas += alargar(placa, objs, 'U3.11', p['centro'][0], p['geom'].bounds[1], -18.75, -1)
    # U4.11: pad de y -10,45 a -8,70 (fileira de cima); a barra do C14/C16 fica em y -6,25
    p = pads['U4.11']
    novas += alargar(placa, objs, 'U4.11', p['centro'][0], p['geom'].bounds[3], -6.25, +1)
    # pedacinhos de 0,25 mm no OUT_B2 que so se sobrepoem ao resto
    tirar = {t['id'] for t in placa.tracks if t['net'] == 'OUT_B2' and t['w'] < 0.3 and
             LineString([t['a'], t['b']]).length < 0.1}
    print('OUT_B2: trechos de 0,25 mm retirados:', sorted(tirar))
    rows = []
    for r in placa.rows:
        if r[0] == 'PAD_NET' and r[3] == 'gnd':
            r = list(r)
            r[3] = 'GND'
            print('rede "gnd" -> GND em', r[1], r[4])
        if r[0] == 'POURED':
            continue
        rows.append(r)
    placa.rows = rows
    R.gravar_epro(placa, saida, lambda r: not (r[0] == 'LINE' and r[1] in tirar), novas, [])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
