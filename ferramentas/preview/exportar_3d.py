"""Exporta a placa v2 + mecanica do EVA-RT para a previa 3D (hardware/preview/placa_3d.html).

Placa: z de 0 (face de baixo) a 1,6 (face de cima); x, y no referencial do seguidor.
Mecanica (STL do EVA-RT), ja transformada para o referencial da placa:
- suportes dos motores (gearbox.stl) girados 180 graus em relacao a geometria.py, conforme
  a camada Document do EVA_RT.eprj (motor com eixo em y -11,26) e o furo do eixo da roda
  medido no STL (y -22,59, 7,0 mm acima da placa);
- carcaca da ventoinha (impeller_base_1, giro 45 graus) e rotor (altura estimada);
- placa de succao (suction_base) embaixo; aros das rodas (wheel_rim) a partir de |x| = 42.
Itens estimados: motores 1020 (cilindro 10 x 20), engrenagem 64T M0,3 (19,8 x 2), pinhao,
pneus, bateria GNB 45 x 20,5 x 12 (frente em y -22,1, 3 mm acima da placa).

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import base64
import json
import math
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import unary_union

import footprints as F
import layout_placa as M
import placa_v2 as V
import rotear_v2 as R

STL = M.ROOT / 'referencias' / 'eva-rt' / '3d_models'
T = 1.6                       # espessura da placa
MOT_Y, MOT_H = -11.256, 7.64  # eixo do motor (y) e altura sobre a face de cima
AXLE_Y, AXLE_H = -22.59, 7.0  # eixo da roda


def rnd(v):
    return round(float(v), 3)


def rings(g, tol=0.01):
    """MultiPolygon -> [[exterior, [furos...]], ...] com coordenadas arredondadas."""
    out = []
    g = g.simplify(tol, preserve_topology=True)
    for p in getattr(g, 'geoms', [g]):
        if p.is_empty or p.geom_type != 'Polygon':
            continue
        ext = [[rnd(x), rnd(y)] for x, y in list(p.exterior.coords)[:-1]]
        holes = [[[rnd(x), rnd(y)] for x, y in list(i.coords)[:-1]] for i in p.interiors]
        out.append([ext, holes])
    return out


def b64(arr):
    return base64.b64encode(np.asarray(arr, dtype='<f4').tobytes()).decode('ascii')


def stl_part(name, fn):
    """Triangulos do STL transformados por fn(xyz)->xyz (array Nx3); corrige o sentido se espelhado."""
    m = trimesh.load(STL / f'{name}.stl')
    v = m.vertices[m.faces].reshape(-1, 3)
    w, flip = fn(v)
    w = w.reshape(-1, 3, 3)
    if flip:
        w = w[:, [0, 2, 1], :]
    return b64(w.reshape(-1))


def main(cobre=True):
    pos = V.load()
    cu = json.loads(R.COBRE.read_text(encoding='utf8'))
    tracks, vias = cu['tracks'], cu['vias']
    pours = {}
    for k, rs in cu['planos'].items():
        pours[int(k)] = unary_union([Polygon(r, h) for r, h in zip(rs, cu['planos_furos'][k])])

    # ---------------------------------------------------------------- placa e cobre
    board = M.BOARD
    pads = M.all_pads(pos)
    layers = {}
    for L in (1, 2):
        cop = [LineString(t['xy']).buffer(t['width'] / 2, quad_segs=6) for t in tracks if t['layer'] == L]
        cop += [Point(v['xy']).buffer(v['diameter'] / 2, quad_segs=10) for v in vias]
        cop.append(pours[L])
        exposed = [p['shape'] for p in pads if L in p['layers']]
        layers[L] = {'cobre': rings(unary_union(cop)) if cobre else [],
                     'pads': rings(unary_union(exposed), 0.005)}
    drills = [[rnd(v['xy'][0]), rnd(v['xy'][1]), rnd(v['drill'] / 2)] for v in vias] if cobre else []
    drills += [[rnd(p['x']), rnd(p['y']), rnd(p['furo'] / 2)] for p in pads if p['furo']]

    # ---------------------------------------------------------------- componentes
    def color(c):
        ref, val = c['ref'], str(c.get('valor', ''))
        if ref.startswith('R'):
            return '#202024'
        if ref in ('C1', 'C2'):
            return '#27406b'
        if ref == 'C5':
            return '#d9a93a'
        if ref.startswith('C'):
            return '#b89468'
        if ref.startswith('LED'):
            return {'LED5': '#4fd17a', 'LED4': '#ff5a4a'}.get(ref, '#f2efe4')
        if ref == 'X1':
            return '#b9bec6'
        if ref == 'J1':
            return '#e9b51c'
        if ref.startswith('SW'):
            return '#b9bec6'          # capa metalica da chave 3 x 6
        return '#17171a'

    comps = []
    for c in pos:
        ref = c['ref']
        fp = F.FOOTPRINTS[c['footprint']]
        bottom = c['face'] == 'BOTTOM'
        if ref in ('M1', 'M2', 'M3', 'J5'):
            continue
        h = fp['altura_mm']
        if ref in ('C1', 'C2'):
            shape = Point(c['x'], c['y']).buffer(3.15, quad_segs=10)
        elif ref == 'J3':
            continue                          # desenhado a parte (barra deitada)
        else:
            shape = M.body(c)
            if shape is None:
                continue
        if ref == 'J2':
            h = 2.5
        item = {'ref': ref, 'poly': rings(shape, 0.005)[0][0], 'h': rnd(h),
                'z0': rnd(0.0 if bottom else T), 'down': bottom, 'cor': color(c),
                'valor': str(c.get('valor', ''))}
        comps.append(item)
    # pinos da J2 (barra reta) e barra deitada J3 embaixo
    pins = []
    for p in M.get_pads(next(c for c in pos if c['ref'] == 'J2')):
        pins.append({'box': [rnd(p['x']), rnd(p['y']), rnd(T + 2.5 + 3.0), 0.64, 0.64, 6.0]})
        pins.append({'box': [rnd(p['x']), rnd(p['y']), rnd(-1.5), 0.64, 0.64, 3.0]})
    j3 = next(c for c in pos if c['ref'] == 'J3')
    extra = []
    for p in M.get_pads(j3):
        # pino deitado sobre o pad (z -0,32), do fim do pad ate 6 mm alem do plastico
        y0, y1 = -27.6, -38.9
        pins.append({'box': [rnd(p['x']), rnd((y0 + y1) / 2), -0.32, 0.64, rnd(y0 - y1), 0.64]})
    extra.append({'ref': 'J3', 'box': [0.0, -31.45, -0.32, 12.7, 2.5, 2.5], 'cor': '#17171a'})

    # ---------------------------------------------------------------- mecanica
    def gearbox(side):
        def fn(v):
            x, y, z = v[:, 0], v[:, 1], v[:, 2]
            X = (40.0 - x) * side          # giro de 180 graus (dir.) e espelho (esq.)
            Y = -y + MOT_Y
            Z = z + 2.5 + T
            return np.stack([X, Y, Z], 1), side < 0
        return fn

    def carcass(v):
        a = math.radians(45)
        x, y, z = v[:, 0], v[:, 1], v[:, 2]
        return np.stack([x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a), z + T], 1), False

    def rotor(v):
        return np.stack([v[:, 0], v[:, 1], v[:, 2] + T + 0.5], 1), False

    def suction(v):
        return np.stack([v[:, 0], v[:, 1] - 27.5, v[:, 2] - 0.6], 1), False

    def wheel(side):
        def fn(v):
            x, y, z = v[:, 0], v[:, 1], v[:, 2]
            X = side * (40.0 + z)            # eixo do aro (z do STL) ao longo de x, a partir de |x| = 40
            Y = AXLE_Y + y
            Z = T + AXLE_H + x
            return np.stack([X, Y, Z], 1), side > 0   # troca de eixos inverte o sentido
        return fn

    mech = [
        {'nome': 'Suporte do motor dir. (gearbox.stl)', 'cor': '#8d939c', 'tri': stl_part('gearbox', gearbox(1))},
        {'nome': 'Suporte do motor esq. (gearbox.stl, espelhado)', 'cor': '#8d939c', 'tri': stl_part('gearbox', gearbox(-1))},
        {'nome': 'Carcaça da ventoinha (impeller_base_1.stl)', 'cor': '#c9cdd3', 'tri': stl_part('impeller_base_1', carcass)},
        {'nome': 'Rotor (impeller_fan.stl, altura estimada)', 'cor': '#e0a33a', 'tri': stl_part('impeller_fan', rotor)},
        {'nome': 'Placa de sucção (suction_base.stl)', 'cor': '#6f7680', 'tri': stl_part('suction_base', suction)},
        {'nome': 'Aro da roda dir. (wheel_rim.stl)', 'cor': '#d3d6db', 'tri': stl_part('wheel_rim', wheel(1))},
        {'nome': 'Aro da roda esq. (wheel_rim.stl)', 'cor': '#d3d6db', 'tri': stl_part('wheel_rim', wheel(-1))},
    ]
    # cilindros: [x, y, z(centro), raio, comprimento, eixo]
    cyl = []
    for s in (1, -1):
        cyl.append({'nome': 'Motor 1020', 'c': [s * 28.0, MOT_Y, T + MOT_H], 'r': 5.0, 'L': 20.0, 'eixo': 'x', 'cor': '#b7bcc4'})
        cyl.append({'nome': 'Engrenagem 64T M0,3 (estimada)', 'c': [s * 41.0, AXLE_Y, T + AXLE_H], 'r': 9.9, 'L': 2.0,
                    'eixo': 'x', 'cor': '#e8e2d0'})
        cyl.append({'nome': 'Pinhão 11T', 'c': [s * 41.0, MOT_Y, T + MOT_H], 'r': 1.95, 'L': 2.0, 'eixo': 'x',
                    'cor': '#c8a33a'})
        cyl.append({'nome': 'Pneu (estimado)', 'c': [s * 51.25, AXLE_Y, T + AXLE_H], 'r': 10.75, 'L': 18.0,
                    'eixo': 'x', 'cor': '#232427', 'tubo': 8.25})
        cyl.append({'nome': 'Eixo da roda Ø2', 'c': [s * 45.5, AXLE_Y, T + AXLE_H], 'r': 1.0, 'L': 30.0,
                    'eixo': 'x', 'cor': '#9aa0a8'})
    boxes = [{'nome': 'Bateria GNB 350 2S (45 × 20,5 × 12)', 'box': [0.0, -32.35, T + 3.0 + 6.0, 45.0, 20.5, 12.0],
              'cor': '#2f6bd8'}]

    ox0, oy0, ox1, oy1 = board.bounds
    j1 = next(c for c in pos if c['ref'] == 'J1')
    corpo = M.body(j1).bounds
    fj = V.folgas_j1(pos)
    jx, jy = j1['x'], j1['y']
    # plugue femea encaixado (par encaixado ~20,1 mm, manual do XT30U) e os dois fios saindo por cima
    topo = T + 10.2
    p1 = next(p for p in M.get_pads(j1) if p['pin'] == '1'); p2 = next(p for p in M.get_pads(j1) if p['pin'] == '2')
    extra += [
        {'nome': 'Plugue XT30 fêmea encaixado (estimado, par com ~20 mm)', 'cor': '#c99512',
         'box': [rnd(jx), rnd(jy), rnd(topo + 4.95), 5.4, 10.4, 9.9]},
        {'nome': 'Fio + (vermelho)', 'cor': '#c8322b', 'box': [rnd(p1['x']), rnd(p1['y']), rnd(topo + 12.9), 1.9, 1.9, 6.0]},
        {'nome': 'Fio − (preto)', 'cor': '#202022', 'box': [rnd(p2['x']), rnd(p2['y']), rnd(topo + 12.9), 1.9, 1.9, 6.0]}]
    n = lambda v: f'{v:.1f}'.replace('.', ',').replace('-', '−')
    notas = {
        'engrenagem': ('<strong>XT30 em pé por dentro do suporte esquerdo.</strong> J1 em '
                       f'({n(j1["x"])}; {n(j1["y"])}), eixo longo em y, pino 1 (+) para a frente: corpo a '
                       f'{n(fj["corpo_suporte"])} mm do suporte, {n(fj["corpo_motor"])} mm do motor, '
                       f'{n(fj["corpo_bateria"])} mm da bateria e {n(fj["corpo_engrenagem"])} mm do plano da engrenagem '
                       '64T (|x| 40…42, estimada). Traseira com os pés do EVA-RT estendidos em linha reta até y −33; chaves 3 × 6 '
                       '(TC-3610) em SW0–SW2. O plugue fêmea encaixado e os fios são '
                       'estimados (par com ~20 mm). Use a vista “XT30 (J1)”.'),
        'placa': ('Só posições: o roteamento ainda vai ser refeito para o novo J1 e o novo contorno, então a máscara '
                  'aparece sem trilhas; pads, furos e referências nas duas faces. A face de baixo é vista como está na '
                  'placa (texto espelhado de propósito para ler por baixo).') if not cobre else
                 ('Cobre e planos de GND sob a máscara aparecem em verde mais claro, pads expostos em prata. A face de '
                  'baixo é vista como está na placa (texto espelhado de propósito para ler por baixo).'),
    }
    data = {
        'notas': notas,
        'espessura': T,
        'limites': [rnd(ox0), rnd(oy0), rnd(ox1), rnd(oy1)],
        'placa': rings(board, 0.005),
        'camadas': {str(k): v for k, v in layers.items()},
        'furos': drills,
        'componentes': comps,
        'pinos': pins,
        'extras': extra,
        'mecanica': mech,
        'cilindros': cyl,
        'caixas': boxes,
        'refs': [{'ref': c['ref'], 'x': rnd(c['x']), 'y': rnd(c['y']), 'face': c['face']} for c in pos
                 if c['ref'] not in ('J8', 'J9')],
    }
    data['vista_xt30'] = {'p': [-82, -78, 58], 't': [rnd(jx), rnd(jy), 6]}
    out = M.OUTPUT / 'placa_3d.html'
    js = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    tpl = (M.HERE / 'placa_3d_modelo.html').read_text(encoding='utf8')
    out.write_text(tpl.replace('/*__DADOS__*/null', js), encoding='utf8')
    print(out, f'{len(js) / 1e6:.2f} MB de dados')


if __name__ == '__main__':
    import sys
    main(cobre='--sem-cobre' not in sys.argv)
