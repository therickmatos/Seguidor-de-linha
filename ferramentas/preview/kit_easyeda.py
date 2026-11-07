"""Kit para fazer a placa no EasyEDA Pro a partir do esquematico do Erick (projeto RUSH, 07/11/2026).

Gera em hardware/placa_alpha/:
  contorno_furos_easyeda.dxf  contorno + furos + rasgos numa camada so (BOARD_OUTLINE): importar na camada
                              Board Outline; formas fechadas internas viram recorte (furo/rasgo fresado)
  furos.csv                   os furos e rasgos com coordenadas, para quem preferir coloca-los como furo NPTH
  posicoes_easyeda.csv        cada componente com face, centro e DOIS pinos (numeracao do esquematico) em
                              coordenadas da placa vistas de cima: posiciona-se pelo pino A e gira-se ate o
                              pino B cair no lugar (vale para qualquer footprint, LCSC ou nosso)
Origem no centro do furo da ventoinha, +y = frente, mm.

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import csv
import math

import ezdxf

import footprints as F
import layout_placa as M
import placa_v2 as V

OUT = M.ROOT / 'hardware' / 'placa_alpha'


def n(v, casas=3):
    return f'{v:.{casas}f}'.replace('.', ',')


def dxf_contorno():
    d = ezdxf.new('R2010')
    d.units = ezdxf.units.MM
    d.layers.new('BOARD_OUTLINE')
    msp = d.modelspace()
    at = {'layer': 'BOARD_OUTLINE'}
    msp.add_lwpolyline(list(M.OUTLINE.exterior.coords)[:-1], close=True, dxfattribs=at)
    for h in M.BOARD_DATA['furos']:
        if h['tipo'] == 'furo':
            msp.add_circle((h['x'], h['y']), h['d'] / 2, dxfattribs=at)
        else:   # rasgo com pontas arredondadas (como a fresa corta): retangulo w x h com raio h/2
            x, y, w, hh = h['x'], h['y'], h['w'], h['h']
            r = hh / 2
            x0, x1 = x - w / 2 + r, x + w / 2 - r
            # (x, y, bulge): bulge 1 = meia volta
            msp.add_lwpolyline([(x0, y - r, 0), (x1, y - r, 1), (x1, y + r, 0), (x0, y + r, 1)],
                               format='xyb', close=True, dxfattribs=at)
    d.saveas(OUT / 'contorno_furos_easyeda.dxf')


def csv_furos():
    with open(OUT / 'furos.csv', 'w', encoding='utf8', newline='') as fh:
        w = csv.writer(fh, delimiter=';', lineterminator='\n')
        w.writerow(['nome', 'tipo', 'x_mm', 'y_mm', 'diametro_mm', 'largura_mm', 'altura_mm', 'obs'])
        for h in M.BOARD_DATA['furos']:
            if h['tipo'] == 'furo':
                w.writerow([h['nome'], 'furo NPTH', n(h['x']), n(h['y']), n(h['d'], 2), '', '',
                            'sem cobre; furo da ventoinha = recorte' if h['d'] > 5 else 'sem cobre'])
            else:
                w.writerow([h['nome'], 'rasgo NPTH (pontas R0,5)', n(h['x']), n(h['y']), '', n(h['w'], 2),
                            n(h['h'], 2), '1,0 mm = largura minima de fresa da JLC'])


def pinos_esquematico(c):
    """[(pino do esquematico, x, y)] para os pads que tem pino no esquematico."""
    fp = F.FOOTPRINTS[c['footprint']]
    mapa = {p['pino']: p['rede_pino'] for p in fp['pads']}
    out = []
    for p in M.get_pads(c):
        sp = mapa.get(p['pin'])
        if sp:
            out.append((str(sp), p['x'], p['y']))
    # tira repetidos (pad termico etc.): fica o primeiro de cada pino
    vistos, unicos = set(), []
    for t in out:
        if t[0] not in vistos:
            vistos.add(t[0])
            unicos.append(t)
    return unicos


def csv_posicoes(pos):
    with open(OUT / 'posicoes_easyeda.csv', 'w', encoding='utf8', newline='') as fh:
        w = csv.writer(fh, delimiter=';', lineterminator='\n')
        w.writerow(['ref', 'valor', 'face', 'centro_x', 'centro_y', 'rot_previa', 'pino_A', 'A_x', 'A_y',
                    'pino_B', 'B_x', 'B_y', 'obs'])
        def chave(c):
            r = c['ref']
            return (r.rstrip('0123456789'), int(''.join(ch for ch in r if ch.isdigit()) or 0))
        for c in sorted(pos, key=chave):
            pads = M.get_pads(c)
            xs = [p['shape'].bounds[0] for p in pads] + [p['shape'].bounds[2] for p in pads]
            ys = [p['shape'].bounds[1] for p in pads] + [p['shape'].bounds[3] for p in pads]
            cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
            pins = pinos_esquematico(c)
            a = next((t for t in pins if t[0] == '1'), pins[0])
            b = max((t for t in pins if t[0] != a[0]), key=lambda t: math.hypot(t[1] - a[1], t[2] - a[2]))
            face = 'baixo' if c['face'] == 'BOTTOM' else 'cima'
            w.writerow([c['ref'], c.get('valor', ''), face, n(cx), n(cy), c['rot'], a[0], n(a[1]), n(a[2]),
                        b[0], n(b[1]), n(b[2]), c.get('motivo', '')])


def main():
    pos = V.load()
    dxf_contorno()
    csv_furos()
    csv_posicoes(pos)
    print('kit EasyEDA em', OUT)


if __name__ == '__main__':
    main()
