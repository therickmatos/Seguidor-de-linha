"""Dados compartilhados do preview da base. Coordenadas em mm, +y para a frente.

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path

import numpy as np
from shapely.geometry import Point, Polygon, LineString, box
from shapely import affinity
from shapely.ops import unary_union

import footprints as F
import geo

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUTPUT = ROOT / 'hardware' / 'preview'
BOARD_DATA = json.loads((HERE / 'geometria.json').read_text(encoding='utf8'))
OUTLINE_ORIGINAL = Polygon(BOARD_DATA['contorno'])
# Traseira (07/11): pes do EVA-RT estendidos em linha reta ate y = -33, dos dois lados, de |x| = 40 a
# |x| = 24, com chanfro de 45 graus ate o centro em y = -30 (|x| = 21). Assim o XT30 em pe recua para
# longe do motor e a chave de reset 3 x 6 (SW0) cabe no pe direito. A alpha de 06/11 tinha alongado os
# cantos ate y = -35 (XT30 deitado) e depois voltado ao contorno B original (degrau em y = -28,5).
# O contorno nao passa de |x| = 40 (engrenagem da roda em |x| 40..42).
def _pe_traseiro(lado):
    import math
    r, cx, cy = 1.0, 40.0 - 1.0, -33.0 + 1.0
    arco = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in range(0, -91, -10)]
    pts = [(40.0, -28.4)] + arco + [(24.0, -33.0), (21.0, -30.0), (20.25, -30.0), (20.25, -28.4)]
    return Polygon([(lado * x, y) for x, y in pts]).buffer(0)

# Bracos (07/11): altura de 5,0 mm (y 2,0..7,0), como as asas de 14 x 5 mm do EVA-RT, no lugar dos 7,4 mm
# do contorno B (y 0,8..8,2). Mesma ponta em |x| = 74,1 com cantos de R1,5, QRE de marca em (+-69,5; 4,5)
# e raiz arredondada (R1) na juncao com o ombro em |x| = 50.
BRACO_Y0, BRACO_Y1, BRACO_PONTA, BRACO_R = 2.0, 7.0, 74.1, 1.5


def _braco(lado):
    x1 = BRACO_PONTA - BRACO_R
    g = unary_union([box(49.9, BRACO_Y0, x1, BRACO_Y1),
                     box(x1, BRACO_Y0 + BRACO_R, BRACO_PONTA, BRACO_Y1 - BRACO_R),
                     Point(x1, BRACO_Y0 + BRACO_R).buffer(BRACO_R, quad_segs=16),
                     Point(x1, BRACO_Y1 - BRACO_R).buffer(BRACO_R, quad_segs=16)])
    for yc, ys in ((BRACO_Y0 - 1.0, BRACO_Y0 - 1.0), (BRACO_Y1 + 1.0, BRACO_Y1)):
        canto = box(50.0, min(ys, ys + 1.0), 51.0, max(ys, ys + 1.0))
        g = g.union(canto.difference(Point(51.0, yc).buffer(1.0, quad_segs=16)))
    return affinity.scale(g, xfact=lado, origin=(0, 0)) if lado < 0 else g


OUTLINE = unary_union([OUTLINE_ORIGINAL, _pe_traseiro(1), _pe_traseiro(-1)])
OUTLINE = OUTLINE.difference(unary_union([box(50.0, -1.0, 80.0, 12.0), box(-80.0, -1.0, -50.0, 12.0)]))
OUTLINE = unary_union([OUTLINE, _braco(1), _braco(-1)]).buffer(0)
# grade de 0,1 um: evita vertices quase coincidentes (espelhamento) que quebram o GEOS nos planos de GND
import shapely as _shapely
OUTLINE = _shapely.set_precision(OUTLINE, 1e-4)

def hole_shape(h):
    if h['tipo'] == 'furo':
        return Point(h['x'], h['y']).buffer(h['d'] / 2, quad_segs=20)
    return box(h['x']-h['w']/2, h['y']-h['h']/2,
               h['x']+h['w']/2, h['y']+h['h']/2)

HOLES = [(h['nome'], hole_shape(h)) for h in BOARD_DATA['furos']]
BOARD = OUTLINE.difference(unary_union([g for _, g in HOLES]))

def netlist():
    text = (ROOT / 'hardware/seguidor_base/REDES.md').read_text(encoding='utf8')
    out = {}
    for line in text.splitlines():
        match = re.match(r'\|\s*`([^`]+)`\s*\|\s*([^|]+)\|', line)
        if match:
            for ref, pin in re.findall(r'\b([A-Z][A-Z0-9]*)\.(\d+)\b', match.group(2)):
                out[(ref, pin)] = match.group(1)
    return out

PIN_NET = netlist()

# Partimos do arquivo ja criado pelo agente anterior e substituimos somente
# posicoes que o pedido novo ou a verificacao de encaixe alteraram.
OVERRIDES = {
    'C2': (22.0, 2.06, 90, 'TOP', 'posicao original EVA-RT'),
    'C6': (-25.30, -15.20, 90, 'TOP', 'VM U2; ajustado para liberar os pinos adjacentes'),
    'C7': (25.20, -9.25, 270, 'TOP', 'VM U3; ajustado para liberar os pinos adjacentes'),
    'C8': (26.67, 2.79, -90, 'TOP', 'posicao original EVA-RT'),
    'C9': (-4.75, -26.45, 225, 'TOP', 'deslocado para liberar J3 central, proximo ao U1'),
    'C10': (5.71, -18.29, 135, 'TOP', 'posicao original EVA-RT'),
    'C13': (-24.25, -17.65, 0, 'TOP', 'VCP/VM U2; proximo sem obstruir pinos'),
    'C14': (-21.45, -17.65, 0, 'TOP', 'CPH/CPL U2; proximo sem obstruir pinos'),
    'C15': (24.15, -7.15, 180, 'TOP', 'VCP/VM U3; proximo sem obstruir pinos'),
    'C16': (21.35, -7.15, 180, 'TOP', 'CPH/CPL U3; proximo sem obstruir pinos'),
    'D1': (26.5, 3.05, -90, 'BOTTOM', 'diodo junto aos pads da ventoinha'),
    'Q1': (26.92, 9.14, 180, 'TOP', 'no lugar e orientacao originais'),
    'SW0': (36.35, -30.25, 180, 'TOP', 'B3U na posicao original'),
    'SW1': (37.34, 5.84, 0, 'TOP', 'B3U na posicao original'),
    'SW2': (37.34, 11.30, 0, 'TOP', 'B3U na posicao original'),
    'J1': (-35.5, -31.7, 0, 'TOP', 'XT30 no canto inferior esquerdo; pad 1 e lado reto = positivo'),
    'J3': (0.0, -28.8, 0, 'TOP', 'barra inferior centralizada; corpo 90 graus para tras'),
    'J4': (32.5, 7.05, 0, 'TOP', 'Bluetooth obrigatorio, entre ventoinha e botoes'),
    'R16': (29.2, 8.2, 0, 'BOTTOM', 'Bluetooth: perto de J4, liberando SW1'),
    'R17': (29.2, 10.2, 0, 'BOTTOM', 'Bluetooth: perto de J4, liberando SW1'),
    'R18': (29.2, 12.2, 0, 'BOTTOM', 'Bluetooth: perto de J4, liberando SW2'),
    'R15': (10.5, -20.0, 90, 'TOP', 'novo pull-up nSLEEP, preserva C10'),
    'U1': (0.0, -22.25, -45, 'TOP', 'avancado 0,75 mm para centralizar J3'),
    'X1': (-7.9, -25.3, 180, 'TOP', 'PROPOSTA: 3225 baixo sob bateria; modelo a confirmar'),
    # O conjunto foi transladado sem trocar a face ou a rotacao do EVA-RT.
    'R6': (-61.73, 4.43, 90, 'BOTTOM', 'asa esquerda transladada ao braco'),
    'R20': (-64.67, 3.61, 180, 'BOTTOM', 'asa esquerda transladada ao braco'),
    'R30': (-64.67, 5.39, 180, 'BOTTOM', 'asa esquerda transladada ao braco'),
    'R7': (61.73, 4.57, 270, 'BOTTOM', 'asa direita transladada ao braco'),
    'R21': (64.67, 5.39, 0, 'BOTTOM', 'asa direita transladada ao braco'),
    'R31': (64.67, 3.61, 0, 'BOTTOM', 'asa direita transladada ao braco'),
}

def load_positions():
    positions = json.loads((HERE / 'posicoes.json').read_text(encoding='utf8'))
    with (HERE / 'posicoes.csv').open(encoding='utf8', newline='') as fh:
        previous = {r['ref']: r.get('motivo','') for r in csv.DictReader(fh,delimiter=';')}
    # Referencias dos itens substituidos no EVA-RT, para marcar seus centros
    # anteriores na figura de mudancas. CONV1..5 eram pads, nao um componente.
    replaced = {'J1': ('TOP',-36.35,-30.25,0), 'J2': ('TOP',0,25.74,180),
                'J3': ('TOP',0,-28.57,0), 'U2': ('TOP',-22.10,-12.45,-90),
                'U3': ('TOP',22.10,-12.45,-90)}
    for c in positions:
        c['motivo'] = previous.get(c['ref'], '')
        if c['ref'] in OVERRIDES:
            c['x'], c['y'], c['rot'], c['face'], c['motivo'] = OVERRIDES[c['ref']]
        c['footprint'] = F.REF_FOOTPRINT[c['ref']]
        c['tht'] = F.FOOTPRINTS[c['footprint']]['tht']
        if c['ref'] in replaced:
            lado,x,y,rot = replaced[c['ref']]
            c['eva'] = {'lado':lado,'x':x,'y':y,'rot':rot}
    return positions

def export_positions(positions):
    eva = {}
    with (HERE / 'eva_rt_componentes.csv').open(encoding='utf8',newline='') as fh:
        for r in csv.DictReader(fh,delimiter=';'):
            eva[r['ref']] = r
    with (HERE/'posicoes.csv').open('w',encoding='utf8',newline='') as fh:
        wr=csv.writer(fh,delimiter=';',lineterminator='\n')
        wr.writerow(['ref','valor','footprint','face','x_mm','y_mm','rot_graus','mudou_do_EVA-RT','motivo'])
        for c in positions:
            old=eva.get(c['ref'])
            same=bool(old and abs(c['x']-float(old['x_mm']))<.05 and
                      abs(c['y']-float(old['y_mm']))<.05 and
                      (float(c['rot'])-float(old['rot']))%360==0 and
                      c['face']==('BOTTOM' if old['lado']=='BOT' else 'TOP'))
            c['mudou']='nao' if same else 'sim'
            wr.writerow([c['ref'],c.get('valor',''),c['footprint'],c['face'],
                         f"{c['x']:.3f}".replace('.',','),f"{c['y']:.3f}".replace('.',','),
                         c['rot'],c['mudou'],c['motivo']])
    (HERE/'posicoes.json').write_text(json.dumps(positions,indent=1,ensure_ascii=False),encoding='utf8')

def get_pads(c):
    ref, x, y, rot, face = c['ref'], c['x'], c['y'], c['rot'], c['face']
    fp = F.FOOTPRINTS[c['footprint']]
    result = []
    for pin, symbol_pin, q, raw in geo.pad_quads(ref, x, y, rot, face):
        if isinstance(q, tuple):
            _, px, py, radius = q
            shape = Point(px, py).buffer(radius, quad_segs=12)
        else:
            shape = Polygon(q)
            px, py = shape.centroid.x, shape.centroid.y
            if raw['forma']=='oval':
                w,h=raw['w'],raw['h']
                if w>=h:
                    oval=LineString([(-(w-h)/2,0),((w-h)/2,0)]).buffer(h/2,quad_segs=12)
                else:
                    oval=LineString([(0,-(h-w)/2),(0,(h-w)/2)]).buffer(w/2,quad_segs=12)
                shape=affinity.translate(affinity.rotate(oval,rot,origin=(0,0)),px,py)
        result.append({'ref': ref, 'pin': pin, 'symbol_pin': symbol_pin,
                       'net': PIN_NET.get((ref, symbol_pin)), 'shape': shape,
                       'x': float(px), 'y': float(py), 'furo': raw['furo'],
                       'layers': (1, 2) if fp['tht'] or raw['furo'] else ((1,) if face == 'TOP' else (2,))})
    return result

def body(c):
    if c['ref'] in ('M1', 'M2', 'M3'):
        return None
    if c['ref']=='J1':
        # Lado positivo reto e lado negativo semicircular conforme desenho do usuario.
        w,h=F.FOOTPRINTS[c['footprint']]['corpo']; r=h/2; center=w/2-r
        points=[[-w/2,-h/2], [center,-h/2]]
        points += [[center+r*math.cos(math.radians(a)), r*math.sin(math.radians(a))]
                   for a in range(-85,91,5)]
        points += [[-w/2,h/2]]
        return Polygon(geo._to_board(points,None,c['x'],c['y'],c['rot'],c['face']))
    pts = geo.corpo_quad(c['ref'], c['x'], c['y'], c['rot'], c['face'])
    return Polygon(pts) if pts is not None else None

def all_pads(positions):
    return [p for c in positions if not c['dnp'] for p in get_pads(c)]

def check_positions(positions):
    pads = all_pads(positions)
    problems = []
    for p in pads:
        if not BOARD.buffer(-0.19).covers(p['shape']):
            problems.append(('cobre fora/recortado', p['ref'], p['pin']))
    for i, a in enumerate(pads):
        for b in pads[i+1:]:
            if a['ref'] == b['ref'] or not set(a['layers']).intersection(b['layers']):
                continue
            gap = a['shape'].distance(b['shape'])
            if gap < 0.19 and (a['net'] != b['net'] or a['net'] is None):
                problems.append(('folga entre pads', f"{a['ref']}.{a['pin']}", f"{b['ref']}.{b['pin']}", round(gap, 3)))
    for i, a in enumerate(positions):
        if a['dnp'] or body(a) is None: continue
        for b in positions[i+1:]:
            if b['dnp'] or body(b) is None: continue
            if a['face'] != b['face'] and not (a['tht'] or b['tht']): continue
            if body(a).intersection(body(b)).area > 0.01:
                problems.append(('corpos sobrepostos', a['ref'], b['ref']))
    return problems

if __name__ == '__main__':
    pp = load_positions()
    print(len(pp), 'componentes')
    for problem in check_positions(pp):
        print(problem)
