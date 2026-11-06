"""Roteamento da placa base v2 com FreeRouting + pos-processamento verificado.

Etapas (python rotear_v2.py tudo):
  dsn       gera v2/seguidor_v2.dsn (componentes agrupados, pads reais, cobre fixo)
  rotear    roda o FreeRouting 1.9.0 (java -jar $FREEROUTING_JAR) -> v2/seguidor_v2.ses
  continuar usa o SES atual como cobre inicial e roda mais uma vez (rip-up do que sobrou)
  importar  le o SES, liga o que sobrou com o finalizador A* (finalizar_v2.py), alarga a
            potencia, faz o plano de GND nas duas faces, remove trilhas de GND redundantes
            e verifica folgas e conectividade -> v2/cobre_v2.json e v2/verificacao_v2.json

O SES publicado (v2/seguidor_v2.ses) veio de: dsn -> rotear 100 -> continuar 100. O
FreeRouting nao e deterministico entre versoes; rodar de novo pode dar outro resultado.

Modelo de previa (nao e projeto EasyEDA). Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import collections
import json
import math
import os
import shutil
import subprocess
import sys

from shapely.geometry import LineString, Point, MultiPolygon, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

import layout_placa as M
import placa_v2 as V
from freerouting_io import fmt, sexp, child

DSN = V.SAIDA / 'seguidor_v2.dsn'
SES = V.SAIDA / 'seguidor_v2.ses'
MAPA = V.SAIDA / 'mapa_v2.json'
COBRE = V.SAIDA / 'cobre_v2.json'
VERIF = V.SAIDA / 'verificacao_v2.json'
JAR = os.environ.get('FREEROUTING_JAR', '/tmp/claude-0/fr/fr19.jar')

CLEAR = 0.20                    # folga entre cobres de redes diferentes
EDGE = 0.30                     # folga cobre-borda/furo
POWER = {'VBAT', 'OUT_A1', 'OUT_A2', 'OUT_B1', 'OUT_B2', 'OUT_C'}
VIAS = {'VIA_S': (0.6, 0.3), 'VIA_P': (0.8, 0.4)}   # diametro, furo


def width_for(net):
    if net in POWER:
        return 0.40             # cabe no pino 0,45 do DRV8874; alargado depois
    if net in ('+5V', 'GND'):
        return 0.40
    return 0.25


def via_for(net):
    return 'VIA_P' if net in POWER or net in ('+5V', 'GND') else 'VIA_S'


# ---------------------------------------------------------------- cobre fixo (pre-roteado)
# Troncos de VBAT como no EVA-RT: face de baixo, do J1 subindo pela esquerda ate C1 e
# contornando a frente da ventoinha ate C2; na direita, C2 desce pela face de cima ate
# C15/C7 (VM do U3). Assim o VBAT nao passa entre o ATmega e a ventoinha, por onde saem
# os sinais para a barra de sensores. Com o XT30 em pe em x = -27, o pino + (J1.1, furo
# passante) fica sobre o tronco de baixo e liga direto o VM do U2 por cima (C6/C13).
PRE_TRACKS = [
    ('VBAT', 2, 1.2, [(-27.0, -21.2), (-27.0, 3.31), (-22.0, 3.31)]),
    ('VBAT', 2, 1.2, [(-22.0, 3.31), (-14.31, 11.0), (9.0, 11.0), (17.0, 3.0), (17.0, 0.81), (22.0, 0.81)]),
    ('VBAT', 1, 1.0, [(-27.0, -21.2), (-24.5, -18.7), (-24.5, -17.9)]),
    ('VBAT', 1, 1.0, [(22.0, 0.81), (24.49, -1.68), (24.49, -7.3)]),
    # U3 (rot 90): potencia na fileira de cima; OUT2 sai pelo corredor entre os pinos e
    # C15/C7, VM sobe ate C15.1, OUT1 sai pela direita e contorna o furo do suporte do motor
    ('OUT_B2', 1, 0.4, [(23.725, -9.675), (23.725, -8.5), (27.6, -8.5)]),
    ('OUT_B2', 1, 1.0, [(27.6, -8.5), (36.08, -0.02), (36.58, 0.0)]),
    ('VBAT', 1, 0.4, [(23.075, -9.675), (23.075, -7.3), (23.9, -7.3)]),
    ('OUT_B1', 1, 0.4, [(24.375, -15.225), (25.3, -15.225)]),
    # bomba de carga do U3 (pinos 12-14 -> C15.2 e C16), sem cruzar o VM
    ('VCP_B', 1, 0.25, [(22.425, -9.675), (22.425, -7.3)]),
    ('CPH_B', 1, 0.25, [(21.775, -9.675), (21.775, -8.2), (21.25, -7.675), (21.25, -7.3)]),
    ('CPL_B', 1, 0.25, [(21.125, -9.675), (21.125, -8.6), (19.6, -8.6), (19.6, -7.3)]),
    ('OUT_B1', 1, 1.0, [(25.3, -15.225), (27.0, -15.225), (39.2, -3.025), (39.2, 2.54), (36.58, 2.54)]),
    # Bluetooth: TXD do HC-05 (J4.3) ao R18.2 pela face de baixo, no corredor entre a coluna
    # do J4 e os resistores R16-R18, contornando o R18 por cima (o autorroteador dava 6 vias)
    ('BT_TXD', 2, 0.25, [(32.5, 5.78), (31.05, 7.23), (31.05, 12.95), (30.8, 13.2), (28.625, 13.2),
                         (28.375, 12.95), (28.375, 12.2)]),
    # cristal: trilhas curtas desenhadas a mao (pino 7 -> X1.1 -> C11; pino 8 -> X1.3 -> C12)
    ('XTAL1', 1, 0.25, [(-1.604, -27.433), (-2.046, -27.875), (-5.6, -27.875), (-5.6, -26.55),
                        (-6.7, -26.55), (-6.7, -25.125)]),
    ('XTAL2', 1, 0.25, [(-1.039, -27.999), (-1.481, -28.441), (-2.29, -29.25), (-8.9, -29.25),
                        (-8.9, -28.25), (-10.475, -28.25)]),
    # feixe dos sensores (como o octogono do EVA-RT): S0/S1 pela direita do furo da
    # ventoinha, S2/S3/C0 pela esquerda, cruzando a frente ate a barra J2
    ('S1_A1', 1, 0.25, [(1.039, -18.001), (1.481, -17.559), (9.6, -9.44), (9.6, 13.0),
                        (6.35, 16.25), (6.35, 22.74)]),
    ('S0_A0', 1, 0.25, [(1.604, -18.567), (2.046, -18.125), (10.2, -9.971), (10.2, 13.249),
                        (8.89, 14.559), (8.89, 22.74)]),
    ('S2_A2', 1, 0.25, [(-1.047, -17.993), (-1.489, -17.551), (-9.6, -9.44), (-9.6, 13.0),
                        (-4.2, 18.4), (3.81, 18.4), (3.81, 22.74)]),
    ('S3_A3', 1, 0.25, [(-1.613, -18.559), (-2.055, -18.117), (-10.2, -9.972), (-10.2, 13.249),
                        (-4.449, 19.0), (1.27, 19.0), (1.27, 22.74)]),
    ('C0_A4', 1, 0.25, [(-2.179, -19.124), (-2.621, -18.682), (-10.8, -10.503), (-10.8, 13.498),
                        (-4.698, 19.6), (-1.27, 19.6), (-1.27, 22.74)]),
]
PRE_VIAS = []   # o J1 (furo passante) faz a passagem de face do VBAT


def fixed_copper():
    tracks = [{'id': f'F{i + 1}', 'net': n, 'layer': l, 'width': w, 'xy': [list(p) for p in pts],
               'status': 'nova', 'fixa': True} for i, (n, l, w, pts) in enumerate(PRE_TRACKS)]
    vias = [{'id': f'FV{i + 1}', 'net': n, 'xy': list(xy), 'diameter': VIAS[t][0], 'drill': VIAS[t][1],
             'status': 'nova', 'fixa': True} for i, (n, t, xy) in enumerate(PRE_VIAS)]
    return tracks, vias


# ---------------------------------------------------------------- vias fixas
def thermal_vias(positions):
    """Vias de GND no pad termico de cada DRV8874 (calor e retorno para a face de baixo)."""
    out = []
    for c in positions:
        if c['ref'] not in ('U2', 'U3'):
            continue
        # pad termico 5,0 (x) x 3,4 (y) com rot +-90; 3 x 2 vias de 0,6/0,3
        for dx in (-1.5, 0.0, 1.5):
            for dy in (-0.75, 0.75):
                out.append({'id': f"TV-{c['ref']}-{len(out)}", 'net': 'GND',
                            'xy': [c['x'] + dx, c['y'] + dy], 'diameter': 0.6,
                            'drill': 0.3, 'status': 'nova', 'fixa': True})
    return out


# ---------------------------------------------------------------- DSN
def make_dsn():
    pos = V.load()
    problems = V.check(pos) + V.check_board()
    if problems:
        raise SystemExit(f'posicionamento com problemas: {problems}')
    pads = M.all_pads(pos)
    nets = sorted({p['net'] for p in pads if p['net']})
    ids = {n: f'N{i:03d}' for i, n in enumerate(nets, 1)}
    by_ref = collections.defaultdict(list)
    pins = collections.defaultdict(list)
    for p in pads:
        by_ref[p['ref']].append(p)
        nid = ids[p['net']] if p['net'] else f'NC_{p["ref"]}_{p["pin"]}'
        pins[nid].append(f'{p["ref"]}-{p["pin"]}')
    placements, images, stacks = [], [], []
    for c in pos:
        ref = c['ref']
        if ref not in by_ref:
            continue
        placements.append(f'    (component IMG_{ref} (place {ref} {fmt(c["x"])} {fmt(c["y"])} front 0))')
        ipins = []
        for p in by_ref[ref]:
            stack = f'PAD_{ref}_{p["pin"]}'
            coords = list(p['shape'].exterior.coords)[:-1]
            xy = ' '.join(f'{fmt(x - p["x"])} {fmt(y - p["y"])}' for x, y in coords)
            shapes = ' '.join(f'(shape (polygon {"F" if l == 1 else "B"} 0 {xy}))' for l in p['layers'])
            stacks.append(f'    (padstack {stack} {shapes} (attach off))')
            ipins.append(f'(pin {stack} {p["pin"]} {fmt(p["x"] - c["x"])} {fmt(p["y"] - c["y"])})')
        images.append(f'    (image IMG_{ref} {" ".join(ipins)})')
    # contorno recuado 0,1 mm: com a folga de 0,2 do roteador da 0,3 ate a borda
    inner = M.OUTLINE.buffer(-0.1, join_style=2)
    outline = ' '.join(f'{fmt(x)} {fmt(y)}' for x, y in inner.exterior.coords)
    keep = []
    for h in M.BOARD_DATA['furos']:
        for layer in ('F', 'B'):
            if h['tipo'] == 'furo':
                keep.append(f'    (keepout (circle {layer} {fmt(h["d"] + 0.2)} {fmt(h["x"])} {fmt(h["y"])}))')
            else:
                x0, y0, x1, y1 = M.hole_shape(h).buffer(0.1, join_style=2).bounds
                keep.append(f'    (keepout (rect {layer} {fmt(x0)} {fmt(y0)} {fmt(x1)} {fmt(y1)}))')
    vias_lib = [f'    (padstack {n} (shape (circle F {fmt(d)})) (shape (circle B {fmt(d)})) (attach off))'
                for n, (d, _) in VIAS.items()]
    lines = ['(pcb seguidor_v2',
             '  (parser (string_quote ") (space_in_quoted_tokens on) (host_cad "preview") (host_version "v2"))',
             '  (resolution mm 1000)', '  (unit mm)', '  (structure',
             '    (layer F (type signal))', '    (layer B (type signal))',
             f'    (boundary (path pcb 0 {outline}))', *keep,
             '    (via VIA_S VIA_P)',
             '    (control (via_at_smd off))',
             f'    (rule (width 0.25) (clearance {fmt(CLEAR)}))', '  )',
             '  (placement', *placements, '  )',
             '  (library', *images, *stacks, *vias_lib, '  )', '  (network']
    for nid, terms in pins.items():
        lines.append(f'    (net {nid} (pins {" ".join(terms)}))')
    for net in nets:
        nid = ids[net]
        lines.append(f'    (class C_{nid} {nid} (circuit (use_via {via_for(net)})) '
                     f'(rule (width {fmt(width_for(net))}) (clearance {fmt(CLEAR)})))')
    for nid in sorted(x for x in pins if x.startswith('NC_')):
        lines.append(f'    (class C_{nid} {nid} (circuit (use_via VIA_S)) (rule (width 0.25)))')
    lines.append('  )')
    wires = [f'    (via VIA_S {fmt(v["xy"][0])} {fmt(v["xy"][1])} (net {ids["GND"]}) (type protect))'
             for v in thermal_vias(pos)]
    ft, fv = fixed_copper()
    for t in ft:
        xy = ' '.join(f'{fmt(x)} {fmt(y)}' for x, y in t['xy'])
        wires.append(f'    (wire (path {"F" if t["layer"] == 1 else "B"} {fmt(t["width"])} {xy}) '
                     f'(net {ids[t["net"]]}) (type protect))')
    for v in fv:
        name = 'VIA_P' if v['diameter'] > 0.7 else 'VIA_S'
        wires.append(f'    (via {name} {fmt(v["xy"][0])} {fmt(v["xy"][1])} (net {ids[v["net"]]}) (type protect))')
    # pre-checagem do cobre fixo contra pads de outras redes
    objs = copper_objects(pos, ft, fv + thermal_vias(pos))
    bad = clearance_issues(objs, M.BOARD)
    if bad:
        raise SystemExit(f'cobre fixo com folga insuficiente: {bad}')
    lines += ['  (wiring', *wires, '  )', ')', '']
    DSN.write_text('\n'.join(lines), encoding='utf8')
    MAPA.write_text(json.dumps({'net_ids': {v: k for k, v in ids.items()}}, indent=1), encoding='utf8')
    print('DSN:', len(by_ref), 'componentes,', len(pads), 'pads,', len(nets), 'redes', flush=True)


def continue_dsn():
    """DSN com o resultado do SES atual como cobre inicial (nao fixo), para mais uma rodada."""
    mapping = json.loads(MAPA.read_text(encoding='utf8'))['net_ids']
    ids = {name: nid for nid, name in mapping.items()}
    tracks, vias = read_ses()
    ft, fv = fixed_copper()
    fixed_xy = [tuple(v['xy']) for v in fv + thermal_vias(V.load())]
    fixed_keys = {(t['layer'], tuple((round(p[0], 3), round(p[1], 3)) for p in t['xy'])) for t in ft}
    wires = []
    for t in tracks:
        if (t['layer'], tuple((round(p[0], 3), round(p[1], 3)) for p in t['xy'])) in fixed_keys:
            continue
        xy = ' '.join(f'{fmt(x)} {fmt(y)}' for x, y in t['xy'])
        wires.append(f'    (wire (path {"F" if t["layer"] == 1 else "B"} {fmt(t["width"])} {xy}) (net {ids[t["net"]]}))')
    for v in vias:
        if any(abs(v['xy'][0] - x) < 1e-3 and abs(v['xy'][1] - y) < 1e-3 for x, y in fixed_xy):
            continue
        name = 'VIA_P' if v['diameter'] > 0.7 else 'VIA_S'
        wires.append(f'    (via {name} {fmt(v["xy"][0])} {fmt(v["xy"][1])} (net {ids[v["net"]]}))')
    src = DSN.read_text(encoding='utf8')
    marker = '  (wiring\n'
    if src.count(marker) != 1:
        raise ValueError('secao wiring inesperada')
    DSN.write_text(src.replace(marker, marker + '\n'.join(wires) + '\n'), encoding='utf8')
    print('continuacao:', len(wires), 'elementos iniciais', flush=True)


def run_freerouting(passes=100):
    # FreeRouting 1.9.0 (algoritmo classico; o 2.x oscila e restaura tabuleiros piores)
    # baixar: github.com/freerouting/freerouting/releases (v1.9.0); no Linux sem tela usa xvfb-run
    cmd = ['java', '-jar', JAR, '-de', str(DSN), '-do', str(SES), '-mp', str(passes), '-dct', '0']
    # FR_EXTRA, ex. "-mt 0": sem a otimizacao final (ela travou numa das rodadas da versao alpha)
    cmd += os.environ.get('FR_EXTRA', '').split()
    if shutil.which('xvfb-run') and not os.environ.get('DISPLAY'):
        cmd = ['xvfb-run', '-a'] + cmd
    print(' '.join(cmd), flush=True)
    log = V.SAIDA / 'freerouting.log'
    with open(log, 'w') as fh:
        subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, check=False, timeout=3600)
    if not SES.exists():
        raise SystemExit('FreeRouting nao gerou o SES; ver ' + str(log))


# ---------------------------------------------------------------- leitura do SES
def read_ses():
    mapping = json.loads(MAPA.read_text(encoding='utf8'))['net_ids']
    ses = sexp(SES.read_text(encoding='utf8'))
    routes = child(ses, 'routes')
    res = child(routes, 'resolution')
    factor = {'mm': 1.0, 'um': .001, 'mil': .0254, 'inch': 25.4}[res[1]] / float(res[2])
    tracks, vias = [], []
    for net in child(routes, 'network_out')[1:]:
        if not isinstance(net, list) or net[0] != 'net':
            continue
        name = mapping.get(net[1])
        if name is None:
            continue
        for item in net[2:]:
            if not isinstance(item, list) or not item:
                continue
            if item[0] == 'wire':
                path = child(item, 'path')
                vals = [float(x) * factor for x in path[3:]]
                tracks.append({'id': f'T{len(tracks) + 1}', 'net': name,
                               'layer': {'F': 1, 'B': 2}[path[1]], 'width': float(path[2]) * factor,
                               'xy': [[vals[i], vals[i + 1]] for i in range(0, len(vals), 2)],
                               'status': 'nova'})
            elif item[0] == 'via':
                d, drill = VIAS[item[1]]
                vias.append({'id': f'V{len(vias) + 1}', 'net': name,
                             'xy': [float(item[2]) * factor, float(item[3]) * factor],
                             'diameter': d, 'drill': drill, 'status': 'nova'})
    return tracks, vias


# ---------------------------------------------------------------- geometria de cobre
def seg_shapes(t):
    pts = t['xy']
    return [LineString([pts[i], pts[i + 1]]).buffer(t['width'] / 2, quad_segs=8)
            for i in range(len(pts) - 1)] or [Point(pts[0]).buffer(t['width'] / 2)]


def copper_objects(positions, tracks, vias, pours=None):
    objs = []
    for p in M.all_pads(positions):
        objs.append({'name': f"{p['ref']}.{p['pin']}", 'net': p['net'], 'layers': set(p['layers']),
                     'geom': p['shape'], 'pad': f"{p['ref']}.{p['pin']}" if p['net'] else None})
    for t in tracks:
        objs.append({'name': t['id'], 'net': t['net'], 'layers': {t['layer']},
                     'geom': unary_union(seg_shapes(t)), 'pad': None})
    for v in vias:
        objs.append({'name': v['id'], 'net': v['net'], 'layers': {1, 2},
                     'geom': Point(v['xy']).buffer(v['diameter'] / 2, quad_segs=12), 'pad': None})
    for layer, g in (pours or {}).items():
        for i, part in enumerate(getattr(g, 'geoms', [g])):
            if not part.is_empty:
                objs.append({'name': f'GND-plano-{layer}-{i}', 'net': 'GND', 'layers': {layer},
                             'geom': part, 'pad': None})
    return objs


def connectivity(objs):
    """Ligacoes abertas por rede (grupos de cobre que contem pads e nao se tocam)."""
    nets = collections.defaultdict(list)
    for o in objs:
        if o['net']:
            nets[o['net']].append(o)
    open_ = {}
    for net, items in nets.items():
        parent = list(range(len(items)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        tree = STRtree([o['geom'] for o in items])
        for i, o in enumerate(items):
            for j in tree.query(o['geom'].buffer(0.001)):
                j = int(j)
                if j > i and o['layers'] & items[j]['layers'] and o['geom'].distance(items[j]['geom']) < 0.001:
                    parent[find(j)] = find(i)
        groups = collections.defaultdict(list)
        for i, o in enumerate(items):
            groups[find(i)].append(o)
        with_pads = [[o['pad'] for o in g if o['pad']] for g in groups.values()]
        with_pads = [g for g in with_pads if g]
        if len(with_pads) > 1:
            open_[net] = with_pads
    return open_


def clearance_issues(objs, board):
    issues = []
    inner = board.buffer(-(EDGE - 0.01))
    for o in objs:
        if not o['name'].startswith('GND-plano') and o['pad'] is None and not inner.covers(o['geom']):
            issues.append({'tipo': 'borda/furo', 'obj': o['name'], 'rede': o['net']})
    for layer in (1, 2):
        sub = [o for o in objs if layer in o['layers']]
        tree = STRtree([o['geom'] for o in sub])
        for i, a in enumerate(sub):
            for j in tree.query(a['geom'].buffer(CLEAR)):
                j = int(j)
                if j <= i:
                    continue
                b = sub[j]
                if a['net'] is not None and a['net'] == b['net']:
                    continue
                if a['name'].split('.')[0] == b['name'].split('.')[0] and a['pad'] is None and b['pad'] is None:
                    continue
                gap = a['geom'].distance(b['geom'])
                if gap < CLEAR - 0.01:
                    issues.append({'tipo': 'folga', 'camada': layer, 'a': a['name'], 'b': b['name'],
                                   'rede_a': a['net'], 'rede_b': b['net'], 'folga_mm': round(gap, 3)})
    return issues


# ---------------------------------------------------------------- alargar potencia
def widen(positions, tracks, vias, nets_widths):
    """Alarga cada segmento das redes indicadas ate a maior largura que mantem as folgas."""
    board_in = M.BOARD.buffer(-EDGE)
    out = []
    for t in tracks:
        if t['net'] not in nets_widths:
            out.append(t)
            continue
        pts = t['xy']
        k = 0
        for i in range(len(pts) - 1):
            (xa, ya), (xb, yb) = pts[i], pts[i + 1]
            n = max(1, int(math.ceil(math.hypot(xb - xa, yb - ya) / 2.0)))   # pedacos de ate 2 mm
            for j in range(n):
                p0 = [xa + (xb - xa) * j / n, ya + (yb - ya) * j / n]
                p1 = [xa + (xb - xa) * (j + 1) / n, ya + (yb - ya) * (j + 1) / n]
                out.append({**t, 'id': f"{t['id']}.{k}", 'xy': [p0, p1]})
                k += 1
    tracks = out
    # rodadas por largura crescente: todas as trilhas sobem juntas, sem uma tomar o espaco das outras
    steps = sorted({w for ws in nets_widths.values() for w in ws})
    for w in steps:
        for t in sorted(tracks, key=lambda t: -LineString(t['xy']).length):
            if t['net'] not in nets_widths or w not in nets_widths[t['net']] or w <= t['width']:
                continue
            others = [o for o in copper_objects(positions, [x for x in tracks if x is not t], vias)
                      if t['layer'] in o['layers'] and o['net'] != t['net']]
            g = LineString(t['xy']).buffer(w / 2, quad_segs=8)
            if not board_in.covers(g):
                continue
            tree = STRtree([o['geom'] for o in others])
            near = [others[int(j)] for j in tree.query(g.buffer(CLEAR))]
            if all(o['geom'].distance(g) >= CLEAR for o in near):
                t['width'] = w
    # junta pedacos consecutivos de mesma largura (mesma trilha de origem)
    merged = []
    for t in tracks:
        prev = merged[-1] if merged else None
        if (prev is not None and t['net'] in nets_widths and prev['net'] == t['net'] and
                prev['layer'] == t['layer'] and abs(prev['width'] - t['width']) < 1e-9 and
                prev['id'].rsplit('.', 1)[0] == t['id'].rsplit('.', 1)[0] and
                math.dist(prev['xy'][-1], t['xy'][0]) < 1e-6):
            a, b, c = prev['xy'][-2], prev['xy'][-1], t['xy'][1]
            if abs((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])) < 1e-9:
                prev['xy'][-1] = c
            else:
                prev['xy'].append(c)
            continue
        merged.append({**t, 'xy': [list(p) for p in t['xy']]})
    return merged


# ---------------------------------------------------------------- plano de GND
def ground_pours(positions, tracks, vias):
    objs = copper_objects(positions, tracks, vias)
    pours = {}
    for layer in (1, 2):
        area = M.BOARD.buffer(-EDGE)
        foreign = [o['geom'].buffer(0.25, quad_segs=6) for o in objs
                   if layer in o['layers'] and o['net'] != 'GND']
        allowed = area.difference(unary_union(foreign))
        # sem filetes < 0,3 mm; a interseccao garante que a abertura nao invade a folga
        g = allowed.buffer(-0.15, join_style=2).buffer(0.15, join_style=2).intersection(allowed)
        parts = [p for p in getattr(g, 'geoms', [g]) if p.area > 2.0]     # ilhas pequenas fora
        pours[layer] = MultiPolygon(parts) if parts else Polygon()
    return pours


def stitching_vias(positions, tracks, vias, pours, step=5.0):
    """Vias de costura GND onde os dois planos tem espaco, numa grade de passo `step`."""
    d = VIAS['VIA_S'][0]
    ok = pours[1].buffer(-(d / 2 + 0.05)).intersection(pours[2].buffer(-(d / 2 + 0.05)))
    objs = copper_objects(positions, tracks, vias)
    foreign = unary_union([o['geom'] for o in objs if o['net'] != 'GND']).buffer(CLEAR + d / 2)
    holes = unary_union([g for _, g in M.HOLES]).buffer(EDGE + d / 2 + 0.2)
    # nenhuma via de costura encostada em pad (nem de GND): solda e distancia entre furos
    pads = unary_union([p['shape'] for p in M.all_pads(positions)]).buffer(d / 2 + 0.25)
    ok = ok.difference(foreign).difference(holes).difference(pads)
    new = []
    xs = [x * step for x in range(int(-76 / step), int(76 / step) + 1)]
    ys = [y * step for y in range(int(-36 / step), int(27 / step) + 1)]
    existing = [Point(v['xy']) for v in vias]
    for x in xs:
        for y in ys:
            p = Point(x, y)
            if ok.contains(p) and all(p.distance(e) > 1.5 for e in existing):
                v = {'id': f'GV{len(new) + 1}', 'net': 'GND', 'xy': [x, y], 'diameter': d,
                     'drill': VIAS['VIA_S'][1], 'status': 'nova', 'costura': True}
                new.append(v)
                existing.append(p)
    return new


def stitch_islands(positions, tracks, vias, pours):
    """Uma via de costura em cada ilha de plano sem ligacao, onde a outra face tem plano."""
    d, drill = VIAS['VIA_S']
    objs = copper_objects(positions, tracks, vias)
    foreign = unary_union([o['geom'] for o in objs if o['net'] != 'GND']).buffer(CLEAR + d / 2)
    holes = unary_union([g for _, g in M.HOLES]).buffer(EDGE + d / 2 + 0.05)
    holes = holes.union(unary_union([p['shape'] for p in M.all_pads(positions)]).buffer(d / 2 + 0.25))
    live = drop_floating(positions, tracks, vias, pours)
    n0 = sum(1 for v in vias if v['id'].startswith('GI'))
    new = []
    for layer in (1, 2):
        other = 2 if layer == 1 else 1
        live_parts = list(getattr(live[layer], 'geoms', [live[layer]]))
        for isl in getattr(pours[layer], 'geoms', [pours[layer]]):
            if isl.is_empty or any(isl.intersects(lp) and isl.intersection(lp).area > 0.01 for lp in live_parts):
                continue
            # so vale costurar onde a outra face tem plano LIGADO; ilha com ilha nao resolve nada
            # (antes repetia a mesma via a cada rodada e deixava vias soltas, que o DRC do KiCad acusa)
            ok = (isl.buffer(-(d / 2 + 0.05)).intersection(live[other].buffer(-(d / 2 + 0.05)))
                  .difference(foreign).difference(holes))
            if ok.is_empty:
                continue
            p = ok.representative_point()
            if any(math.hypot(p.x - v['xy'][0], p.y - v['xy'][1]) < d + CLEAR for v in vias + new):
                continue
            new.append({'id': f'GI{n0 + len(new) + 1}', 'net': 'GND', 'xy': [p.x, p.y], 'diameter': d,
                        'drill': drill, 'status': 'nova', 'costura': True})
    return new


def drop_floating(positions, tracks, vias, pours):
    """Descarta ilhas do plano que nao encostam em nenhum cobre de GND ligado a um pad."""
    objs = [o for o in copper_objects(positions, tracks, vias, pours) if o['net'] == 'GND']
    parent = list(range(len(objs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    tree = STRtree([o['geom'] for o in objs])
    for i, o in enumerate(objs):
        for j in tree.query(o['geom'].buffer(0.001)):
            j = int(j)
            if j > i and o['layers'] & objs[j]['layers'] and o['geom'].distance(objs[j]['geom']) < 0.001:
                parent[find(j)] = find(i)
    alive = {find(i) for i, o in enumerate(objs) if o['pad']}
    keep = {1: [], 2: []}
    for i, o in enumerate(objs):
        if o['name'].startswith('GND-plano') and find(i) in alive:
            keep[next(iter(o['layers']))].append(o['geom'])
    return {k: (MultiPolygon(v) if v else Polygon()) for k, v in keep.items()}


def prune_ground(positions, tracks, vias, pours):
    """Remove trilhas de GND que o plano ja substitui, sem abrir nenhuma ligacao."""
    removed = 0
    gnd = sorted([t for t in tracks if t['net'] == 'GND'], key=lambda t: -LineString(t['xy']).length)
    base = connectivity(copper_objects(positions, tracks, vias, pours)).get('GND')
    if base:
        return tracks, 0
    current = list(tracks)
    for t in gnd:
        trial = [x for x in current if x is not t]
        if 'GND' not in connectivity([o for o in copper_objects(positions, trial, vias, pours)
                                       if o['net'] == 'GND']):
            current = trial
            removed += 1
    return current, removed


def importar():
    pos = V.load()
    tracks, vias = read_ses()
    ft, fv = fixed_copper()
    fixed = thermal_vias(pos) + fv
    # o SES devolve o cobre fixo tambem; manter so uma copia de cada
    vias = [v for v in vias if not any(abs(v['xy'][0] - f['xy'][0]) < 1e-3 and
                                       abs(v['xy'][1] - f['xy'][1]) < 1e-3 for f in fixed)] + fixed
    fixed_keys = {(t['layer'], tuple(map(tuple, (map(lambda p: (round(p[0], 3), round(p[1], 3)), t['xy']))))) for t in ft}
    tracks = [t for t in tracks if (t['layer'], tuple((round(p[0], 3), round(p[1], 3)) for p in t['xy'])) not in fixed_keys] + ft
    raw_open = connectivity(copper_objects(pos, tracks, vias))
    print('FreeRouting:', len(tracks), 'trilhas,', len(vias), 'vias; abertas:',
          {k: len(v) - 1 for k, v in raw_open.items()}, flush=True)
    # finalizador A* para o que sobrou (GND fica para o plano)
    import finalizar_v2 as FZ
    finished = []
    for net, groups in raw_open.items():
        if net == 'GND':
            continue
        for g in groups[1:]:
            objs = copper_objects(pos, tracks, vias)
            cur = connectivity([o for o in objs if o['net'] == net]).get(net)
            if not cur:
                break
            a = next(x for x in cur if groups[0][0] in x)
            b = next((x for x in cur if g[0] in x), None)
            if b is None or b is a:
                continue
            res = FZ.route(objs, net, a, b, width=width_for(net))
            if res is None:
                print('finalizador: sem caminho para', net, g, flush=True)
                continue
            segs, vs = res
            for sgm in segs:
                tracks.append({'id': f'A{len(tracks) + 1}', 'net': net, 'layer': sgm['layer'],
                               'width': width_for(net), 'xy': sgm['xy'], 'status': 'nova', 'finalizador': True})
            for xy in vs:
                d, drill = VIAS['VIA_S']
                vias.append({'id': f'AV{len(vias) + 1}', 'net': net, 'xy': xy, 'diameter': d, 'drill': drill,
                             'status': 'nova', 'finalizador': True})
            finished.append(net)
            print('finalizador: ligado', net, len(segs), 'trechos,', len(vs), 'vias', flush=True)
    widths = {n: [0.5, 0.6, 0.8, 1.0, 1.2] for n in POWER}
    widths['+5V'] = [0.6, 0.5]
    tracks = widen(pos, tracks, vias, widths)
    pours = ground_pours(pos, tracks, vias)
    vias += stitching_vias(pos, tracks, vias, pours)
    pours = ground_pours(pos, tracks, vias)
    for _ in range(3):              # ilhas soltas: costura (cada via pode ligar outra ilha)
        extra = stitch_islands(pos, tracks, vias, pours)
        if not extra:
            break
        vias += extra
        pours = ground_pours(pos, tracks, vias)
    pours = drop_floating(pos, tracks, vias, pours)
    tracks, removed = prune_ground(pos, tracks, vias, pours)
    # descarta ilhas do plano que nao tocam nenhum cobre de GND ligado a pads
    objs = copper_objects(pos, tracks, vias, pours)
    open_ = connectivity(objs)
    issues = clearance_issues(objs, M.BOARD)
    data = {'tracks': tracks, 'vias': vias,
            'planos': {str(k): [list(map(list, p.exterior.coords)) for p in getattr(g, 'geoms', [g]) if not p.is_empty]
                       for k, g in pours.items()},
            'planos_furos': {str(k): [[list(map(list, i.coords)) for i in p.interiors]
                                      for p in getattr(g, 'geoms', [g]) if not p.is_empty]
                             for k, g in pours.items()}}
    COBRE.write_text(json.dumps(data, ensure_ascii=False), encoding='utf8')
    ver = {'folga_mm': CLEAR, 'borda_mm': EDGE, 'trilhas': len(tracks), 'vias': len(vias),
           'trilhas_gnd_removidas_pelo_plano': removed,
           'abertas_do_freerouting': {k: len(v) - 1 for k, v in raw_open.items()},
           'ligadas_pelo_finalizador': finished,
           'abertas_final': {k: v for k, v in open_.items()},
           'violacoes': issues}
    VERIF.write_text(json.dumps(ver, ensure_ascii=False, indent=1), encoding='utf8')
    print('final:', len(tracks), 'trilhas,', len(vias), 'vias,', removed, 'trilhas GND removidas;',
          'abertas', {k: len(v) - 1 for k, v in open_.items()}, '; violacoes', len(issues), flush=True)
    for i in issues[:15]:
        print(i)


if __name__ == '__main__':
    step = sys.argv[1] if len(sys.argv) > 1 else 'tudo'
    if step in ('dsn', 'tudo'):
        make_dsn()
    if step == 'continuar':
        continue_dsn()
        run_freerouting(int(sys.argv[2]) if len(sys.argv) > 2 else 100)
        importar()
    if step in ('rotear', 'tudo'):
        run_freerouting(int(sys.argv[2]) if len(sys.argv) > 2 else 100)
    if step in ('importar', 'tudo'):
        importar()
