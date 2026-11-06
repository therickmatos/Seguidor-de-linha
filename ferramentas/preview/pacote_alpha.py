"""Monta hardware/placa_alpha/ (versao alpha da placa base) para o layout no EasyEDA Pro.

Gera: placa_alpha.jpg (trilhas), posicao_alpha.jpg (posicoes), posicoes_alpha.csv,
contorno_alpha.dxf (contorno + todos os furos e rasgos), guia_alpha.dxf (cobre, pads,
vias, corpos e referencias por camada, para importar como guia), trilhas_fixas_alpha.csv
(cobre desenhado a mao) e copia o RELATORIO. Rodar depois de rotear_v2.py importar.

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import csv
import json
import shutil
import sys

import ezdxf
from shapely.geometry import Polygon

import layout_placa as M
import placa_v2 as V
import rotear_v2 as R

OUT = M.ROOT / 'hardware' / 'placa_alpha'


def contorno_dxf(path):
    d = ezdxf.new('R2010'); d.units = 4
    for name in ('CONTORNO', 'FUROS'):
        d.layers.new(name)
    msp = d.modelspace()
    msp.add_lwpolyline(list(M.OUTLINE.exterior.coords)[:-1], close=True, dxfattribs={'layer': 'CONTORNO'})
    for h in M.BOARD_DATA['furos']:
        if h['tipo'] == 'furo':
            msp.add_circle((h['x'], h['y']), h['d'] / 2, dxfattribs={'layer': 'FUROS'})
        else:
            msp.add_lwpolyline(list(M.hole_shape(h).exterior.coords)[:-1], close=True,
                               dxfattribs={'layer': 'FUROS'})
    d.saveas(path)


def guia_dxf(path, pos, data):
    d = ezdxf.new('R2010'); d.units = 4
    names = ['CONTORNO', 'FUROS', 'COBRE_CIMA', 'COBRE_BAIXO', 'PLANO_GND_CIMA', 'PLANO_GND_BAIXO',
             'PADS_CIMA', 'PADS_BAIXO', 'VIAS', 'CORPOS_CIMA', 'CORPOS_BAIXO', 'REFS_CIMA', 'REFS_BAIXO']
    for nme in names:
        d.layers.new(nme)
    msp = d.modelspace()
    msp.add_lwpolyline(list(M.OUTLINE.exterior.coords)[:-1], close=True, dxfattribs={'layer': 'CONTORNO'})
    for _, g in M.HOLES:
        msp.add_lwpolyline(list(g.exterior.coords)[:-1], close=True, dxfattribs={'layer': 'FUROS'})
    for t in data['tracks']:
        lay = 'COBRE_CIMA' if t['layer'] == 1 else 'COBRE_BAIXO'
        msp.add_lwpolyline(t['xy'], dxfattribs={'layer': lay, 'const_width': t['width']})
    for k, rings in data['planos'].items():
        lay = 'PLANO_GND_CIMA' if k == '1' else 'PLANO_GND_BAIXO'
        for r, holes in zip(rings, data['planos_furos'][k]):
            msp.add_lwpolyline(r, close=True, dxfattribs={'layer': lay})
            for h in holes:
                msp.add_lwpolyline(h, close=True, dxfattribs={'layer': lay})
    for v in data['vias']:
        msp.add_circle(v['xy'], v['diameter'] / 2, dxfattribs={'layer': 'VIAS'})
        msp.add_circle(v['xy'], v['drill'] / 2, dxfattribs={'layer': 'VIAS'})
    for c in pos:
        top = c['face'] == 'TOP'
        for p in M.get_pads(c):
            for L in p['layers']:
                msp.add_lwpolyline(list(p['shape'].exterior.coords)[:-1], close=True,
                                   dxfattribs={'layer': 'PADS_CIMA' if L == 1 else 'PADS_BAIXO'})
        b = M.body(c)
        if b is not None and c['ref'] not in ('M1', 'M2', 'M3'):
            msp.add_lwpolyline(list(b.exterior.coords)[:-1], close=True,
                               dxfattribs={'layer': 'CORPOS_CIMA' if top else 'CORPOS_BAIXO'})
        t = msp.add_text(c['ref'], height=0.8, dxfattribs={'layer': 'REFS_CIMA' if top else 'REFS_BAIXO'})
        t.set_placement((c['x'], c['y']), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    d.saveas(path)


def trilhas_fixas(path):
    tr, vs = R.fixed_copper()
    with open(path, 'w', encoding='utf8', newline='') as fh:
        w = csv.writer(fh, delimiter=';', lineterminator='\n')
        w.writerow(['rede', 'camada', 'largura_mm', 'pontos (x y em mm, na ordem)'])
        for t in tr:
            w.writerow([t['net'], 'cima' if t['layer'] == 1 else 'baixo', f"{t['width']:.2f}".replace('.', ','),
                        ' | '.join(f'{x:.3f} {y:.3f}'.replace('.', ',') for x, y in t['xy'])])
        for v in vs:
            w.writerow([v['net'], 'via', f"{v['diameter']:.1f}/{v['drill']:.1f}".replace('.', ','),
                        f"{v['xy'][0]:.3f} {v['xy'][1]:.3f}".replace('.', ',')])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pos = V.load()
    probs = V.check(pos) + V.check_board()
    if probs:
        raise SystemExit(f'posicionamento com problemas: {probs}')
    ver = json.loads(R.VERIF.read_text(encoding='utf8'))
    if ver['abertas_final'] or ver['violacoes']:
        print('ATENCAO: roteamento com pendencias:', ver['abertas_final'], len(ver['violacoes']), 'violacoes')
    data = json.loads(R.COBRE.read_text(encoding='utf8'))
    import figura_v2, figura_posicao, relatorio_v2
    sys.argv = ['figura_v2', str(OUT / 'placa_alpha.jpg')]
    figura_v2.main()
    figura_posicao.main()
    shutil.copy(M.OUTPUT / 'posicao_v2.jpg', OUT / 'posicao_alpha.jpg')
    V.export_csv(pos, OUT / 'posicoes_alpha.csv')
    contorno_dxf(OUT / 'contorno_alpha.dxf')
    guia_dxf(OUT / 'guia_alpha.dxf', pos, data)
    trilhas_fixas(OUT / 'trilhas_fixas_alpha.csv')
    relatorio_v2.main()
    shutil.copy(M.OUTPUT / 'RELATORIO_v2.md', OUT / 'RELATORIO_alpha.md')
    print('pacote em', OUT)


if __name__ == '__main__':
    main()
