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
from shapely.ops import unary_union

import footprints as F
import geo

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUTPUT = ROOT / 'hardware' / 'preview'
BOARD_DATA = json.loads((HERE / 'geometria.json').read_text(encoding='utf8'))
OUTLINE = Polygon(BOARD_DATA['contorno'])

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
    'C8': (26.67, 2.79, -90, 'TOP', 'posicao original EVA-RT'),
    'C10': (5.71, -18.29, 135, 'TOP', 'posicao original EVA-RT'),
    'D1': (26.5, 3.05, -90, 'BOTTOM', 'diodo junto aos pads da ventoinha'),
    'Q1': (26.92, 9.14, 180, 'TOP', 'no lugar e orientacao originais'),
    'SW0': (36.35, -30.25, 180, 'TOP', 'B3U na posicao original'),
    'SW1': (37.34, 5.84, 0, 'TOP', 'B3U na posicao original'),
    'SW2': (37.34, 11.30, 0, 'TOP', 'B3U na posicao original'),
    'J1': (-54.0, 4.5, 0, 'TOP', 'PROPOSTA: XT30 vertical no braco; confirmar modelo e encaixe'),
    'J3': (9.0, -28.75, 0, 'TOP', 'PROPOSTA: deslocado; colide com rasgo original do velcro'),
    'J4': (32.5, 7.05, 0, 'TOP', 'Bluetooth obrigatorio, entre ventoinha e botoes'),
    'R16': (29.2, 8.2, 0, 'BOTTOM', 'Bluetooth: perto de J4, liberando SW1'),
    'R17': (29.2, 10.2, 0, 'BOTTOM', 'Bluetooth: perto de J4, liberando SW1'),
    'R18': (29.2, 12.2, 0, 'BOTTOM', 'Bluetooth: perto de J4, liberando SW2'),
    'R15': (10.5, -20.0, 90, 'TOP', 'novo pull-up nSLEEP, preserva C10'),
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
    for c in positions:
        c['motivo'] = previous.get(c['ref'], '')
        if c['ref'] in OVERRIDES:
            c['x'], c['y'], c['rot'], c['face'], c['motivo'] = OVERRIDES[c['ref']]
        c['footprint'] = F.REF_FOOTPRINT[c['ref']]
        c['tht'] = F.FOOTPRINTS[c['footprint']]['tht']
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
        result.append({'ref': ref, 'pin': pin, 'symbol_pin': symbol_pin,
                       'net': PIN_NET.get((ref, symbol_pin)), 'shape': shape,
                       'x': float(px), 'y': float(py), 'furo': raw['furo'],
                       'layers': (1, 2) if fp['tht'] or raw['furo'] else ((1,) if face == 'TOP' else (2,))})
    return result

def body(c):
    if c['ref'] in ('M1', 'M2', 'M3'):
        return None
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
