"""Roteamento de um .epro (EasyEDA Pro) com o FreeRouting 1.9.0 (08/11/2026).

Funcoes para:
  - escrever um DSN (Specctra) a partir do .epro lido por easyeda_cobre.Placa: contorno, furos,
    pads com a forma exata (ja girados/espelhados), redes, cobre fixo (type protect);
  - rodar o FreeRouting;
  - ler o SES e gravar trilhas (LINE) e vias (VIA) de volta no .epcb do .epro.

Unidades em mm; o .epcb guarda mil.

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import collections
import io
import json
import math
import os
import shutil
import subprocess
import zipfile

from shapely.geometry import MultiPolygon, Polygon

import easyeda_cobre as C
from freerouting_io import child, fmt, sexp

JAR = os.environ.get('FREEROUTING_JAR', '/opt/freerouting/freerouting-1.9.0.jar')
VIAS = {'VIA_S': (0.6, 0.3), 'VIA_P': (0.8, 0.4)}
CLEAR = 0.2


def _nome(n):
    return 'N_' + ''.join(ch if ch.isalnum() else '_' for ch in n)


def escrever_dsn(placa, caminho, fixo, rotear, larguras, vias_rede=None, extras_fixos=(), planos=None,
                 autoroute=None, clear=CLEAR, livres=None):
    """fixo(obj) -> bool: trilha/via da placa que entra como cobre protegido.
    rotear: conjunto de redes que o FreeRouting deve ligar (as outras viram pinos isolados).
    larguras: rede -> largura. vias_rede: rede -> 'VIA_S'/'VIA_P'.
    planos: {camada: geometria} de GND (entram como 'plane' da rede GND). Obs.: o FreeRouting 1.9.0
    travou ao abrir planos com furos (janelas); a placa RUSH nao usa esta opcao."""
    vias_rede = vias_rede or {}
    ids = {n: _nome(n) for n in sorted(rotear)}
    pins = collections.defaultdict(list)
    por_ref = collections.defaultdict(list)
    for i, p in enumerate(placa.pads):
        por_ref[p['des']].append(p)
    placements, images, stacks = [], [], []
    pino_de_pad = {}
    for ref, pads in por_ref.items():
        cx = sum(p['centro'][0] for p in pads) / len(pads)
        cy = sum(p['centro'][1] for p in pads) / len(pads)
        nomeref = ''.join(ch if ch.isalnum() else '_' for ch in ref)
        placements.append(f'    (component IMG_{nomeref} (place {nomeref} {fmt(cx)} {fmt(cy)} front 0))')
        ipins, usados = [], collections.Counter()
        for p in pads:
            usados[p['num']] += 1
            pn = p['num'] if usados[p['num']] == 1 else f"{p['num']}_{usados[p['num']]}"
            pn = ''.join(ch if ch.isalnum() or ch == '_' else '_' for ch in pn) or 'X'
            stack = f'PS_{nomeref}_{pn}'
            g = p['geom']
            if isinstance(g, MultiPolygon):
                g = max(g.geoms, key=lambda q: q.area)
            px, py = p['centro']
            coords = list(g.simplify(0.002).exterior.coords)[:-1]
            xy = ' '.join(f'{fmt(x - px)} {fmt(y - py)}' for x, y in coords)
            shapes = ' '.join(f'(shape (polygon {"F" if l == C.TOP else "B"} 0 {xy}))' for l in sorted(p['layers']))
            stacks.append(f'    (padstack {stack} {shapes} (attach off))')
            ipins.append(f'(pin {stack} {pn} {fmt(px - cx)} {fmt(py - cy)})')
            nid = ids[p['net']] if p['net'] in ids else f'NC_{nomeref}_{pn}'
            pins[nid].append(f'{nomeref}-{pn}')
            pino_de_pad[id(p)] = nid
        images.append(f'    (image IMG_{nomeref} {" ".join(ipins)})')
    # contorno recuado 0,1 mm: com a folga de 0,2 do roteador da 0,3 ate a borda
    inner = placa.borda.buffer(-0.1, join_style=2)
    outline = ' '.join(f'{fmt(x)} {fmt(y)}' for x, y in inner.exterior.coords)
    keep = []
    for h in placa.npth:
        hh = h.buffer(0.1)
        xy = ' '.join(f'{fmt(x)} {fmt(y)}' for x, y in list(hh.simplify(0.01).exterior.coords)[:-1])
        for lay in ('F', 'B'):
            keep.append(f'    (keepout (polygon {lay} 0 {xy}))')
    for i in getattr(placa.borda, 'interiors', []):
        hh = Polygon(i).buffer(0.1)
        xy = ' '.join(f'{fmt(x)} {fmt(y)}' for x, y in list(hh.exterior.coords)[:-1])
        for lay in ('F', 'B'):
            keep.append(f'    (keepout (polygon {lay} 0 {xy}))')
    plane_lines = []
    if planos:
        for lay, g in planos.items():
            for part in (g.geoms if isinstance(g, MultiPolygon) else [g]):
                if part.is_empty or part.area < 0.5:
                    continue
                part = part.simplify(0.01)
                xy = ' '.join(f'{fmt(x)} {fmt(y)}' for x, y in list(part.exterior.coords)[:-1])
                win = ''.join(f' (window (polygon {"F" if lay == C.TOP else "B"} 0 ' +
                              ' '.join(f'{fmt(x)} {fmt(y)}' for x, y in list(r.coords)[:-1]) + '))'
                              for r in part.interiors)
                plane_lines.append(f'    (plane {ids["GND"]} (polygon {"F" if lay == C.TOP else "B"} 0 {xy}){win})')
    vias_lib = [f'    (padstack {n} (shape (circle F {fmt(d)})) (shape (circle B {fmt(d)})) (attach off))'
                for n, (d, _) in VIAS.items()]
    auto = autoroute or []
    lines = ['(pcb rush',
             '  (parser (string_quote ") (space_in_quoted_tokens on) (host_cad "easyeda_rotear") (host_version "1"))',
             '  (resolution mm 1000)', '  (unit mm)', '  (structure',
             '    (layer F (type signal))', '    (layer B (type signal))', *auto,
             f'    (boundary (path pcb 0 {outline}))', *keep, *plane_lines,
             '    (via VIA_S VIA_P)',
             '    (control (via_at_smd off))',
             f'    (rule (width 0.25) (clearance {fmt(clear)}))', '  )',
             '  (placement', *placements, '  )',
             '  (library', *images, *stacks, *vias_lib, '  )', '  (network']
    for nid, terms in pins.items():
        lines.append(f'    (net {nid} (pins {" ".join(terms)}))')
    for net, nid in ids.items():
        if nid not in pins:
            continue
        lines.append(f'    (class C_{nid} {nid} (circuit (use_via {vias_rede.get(net, "VIA_S")})) '
                     f'(rule (width {fmt(larguras.get(net, 0.25))}) (clearance {fmt(clear)})))')
    for nid in sorted(x for x in pins if x.startswith('NC_')):
        lines.append(f'    (class C_{nid} {nid} (circuit (use_via VIA_S)) (rule (width 0.25)))')
    lines.append('  )')
    # cobre fixo
    wires = []

    def rede_fixa(net, ponto=None):
        if net in ids:
            return ids[net]
        # cobre de rede que nao e roteada (GND): vira parte do pino isolado do pad que o contem
        from shapely.geometry import Point
        if ponto is not None:
            for p in placa.pads:
                if p['net'] == net and p['geom'].buffer(0.01).contains(Point(ponto)):
                    return pino_de_pad[id(p)]
        raise ValueError(f'cobre fixo da rede {net} fora de pad: {ponto}')
    # cobre fixo de rede nao roteada (fanout de GND): a trilha herda o pino isolado do pad onde
    # comeca; a via, o da trilha que chega nela
    nid_trilha = {}
    for t in placa.tracks:
        if fixo(t) and t['net'] not in ids:
            for ponta in (t['a'], t['b']):
                try:
                    nid_trilha[t['id']] = rede_fixa(t['net'], ponta)
                    break
                except ValueError:
                    pass
    for _ in range(3):      # trilhas encadeadas (pad -> trilha -> trilha)
        for t in placa.tracks:
            if fixo(t) and t['net'] not in ids and t['id'] not in nid_trilha:
                for u in placa.tracks:
                    if u['id'] in nid_trilha and u['layer'] == t['layer'] and \
                            min(math.dist(p, q) for p in (t['a'], t['b']) for q in (u['a'], u['b'])) < 1e-3:
                        nid_trilha[t['id']] = nid_trilha[u['id']]
                        break

    def rede_via(v):
        if v['net'] in ids:
            return ids[v['net']]
        try:
            return rede_fixa(v['net'], (v['x'], v['y']))
        except ValueError:
            for t in placa.tracks:
                if t['id'] in nid_trilha and min(math.dist((v['x'], v['y']), q) for q in (t['a'], t['b'])) < 1e-3:
                    return nid_trilha[t['id']]
            raise
    for t in placa.tracks:
        if not fixo(t):
            continue
        nid = nid_trilha.get(t['id']) or rede_fixa(t['net'], t['a'])
        (x1, y1), (x2, y2) = t['a'], t['b']
        wires.append(f'    (wire (path {"F" if t["layer"] == C.TOP else "B"} {fmt(t["w"])} {fmt(x1)} {fmt(y1)} '
                     f'{fmt(x2)} {fmt(y2)}) (net {nid}) (type protect))')
    for v in placa.vias:
        if not (v['comp'] or fixo(v)):
            continue
        nid = rede_via(v)
        nome = 'VIA_P' if v['d'] > 0.7 else 'VIA_S'
        wires.append(f'    (via {nome} {fmt(v["x"])} {fmt(v["y"])} (net {nid}) (type protect))')
    for e in extras_fixos:
        wires.append(e.format(**ids))
    # cobre inicial nao fixo (continuacao de uma rodada anterior): o FreeRouting pode arrancar
    for t in (livres or {}).get('trilhas', []):
        xy = ' '.join(f'{fmt(x)} {fmt(y)}' for x, y in t['pts'])
        wires.append(f'    (wire (path {"F" if t["layer"] == C.TOP else "B"} {fmt(t["w"])} {xy}) (net {ids[t["net"]]}))')
    for v in (livres or {}).get('vias', []):
        nome = 'VIA_P' if v['d'] > 0.7 else 'VIA_S'
        wires.append(f'    (via {nome} {fmt(v["x"])} {fmt(v["y"])} (net {ids[v["net"]]}))')
    lines += ['  (wiring', *wires, '  )', ')', '']
    with open(caminho, 'w', encoding='utf8') as f:
        f.write('\n'.join(lines))
    return ids


def rodar(dsn, ses, passes=100, extra=(), log=None, timeout=3600):
    if os.path.exists(ses):
        os.remove(ses)
    cmd = ['java', '-jar', JAR, '-de', str(dsn), '-do', str(ses), '-mp', str(passes), '-dct', '0', *extra]
    if shutil.which('xvfb-run') and not os.environ.get('DISPLAY'):
        cmd = ['xvfb-run', '-a'] + cmd
    with open(log or (str(ses) + '.log'), 'w') as fh:
        subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, check=False, timeout=timeout)
    return os.path.exists(ses)


def ler_ses(ses, ids):
    inv = {v: k for k, v in ids.items()}
    s = sexp(open(ses, encoding='utf8').read())
    routes = child(s, 'routes')
    res = child(routes, 'resolution')
    fator = {'mm': 1.0, 'um': .001, 'mil': .0254, 'inch': 25.4}[res[1]] / float(res[2])
    trilhas, vias = [], []
    for net in child(routes, 'network_out')[1:]:
        if not isinstance(net, list) or net[0] != 'net':
            continue
        nome = inv.get(net[1])
        for item in net[2:]:
            if not isinstance(item, list) or not item:
                continue
            fixo = any(isinstance(x, list) and x[:2] == ['type', 'protect'] for x in item)
            if item[0] == 'wire':
                path = child(item, 'path')
                vals = [float(x) * fator for x in path[3:]]
                pts = [(vals[i], vals[i + 1]) for i in range(0, len(vals), 2)]
                trilhas.append({'net': nome, 'nid': net[1], 'layer': {'F': C.TOP, 'B': C.BOT}[path[1]],
                                'w': float(path[2]) * fator, 'pts': pts, 'fixo': fixo})
            elif item[0] == 'via':
                d, furo = VIAS[item[1]]
                vias.append({'net': nome, 'nid': net[1], 'x': float(item[2]) * fator, 'y': float(item[3]) * fator,
                             'd': d, 'furo': furo, 'fixo': fixo})
    return trilhas, vias


def mil(v):
    return round(v / C.MIL, 4)


def gravar_epro(placa, saida, manter, novas_trilhas, novas_vias, pours=None, prefixo='r'):
    """Reescreve o .epro: mantem as LINE/VIA para as quais manter(row) e verdadeiro, acrescenta as novas.
    novas_trilhas: dicts com net, layer, w, pts; novas_vias: net, x, y, d, furo.
    pours: lista de linhas POUR prontas (listas) que substituem as do arquivo; None mantem as do arquivo."""
    usados = {r[1] for r in placa.rows if len(r) > 1 and isinstance(r[1], str)}
    cont = [1]

    def prox():
        while f'{prefixo}{cont[0]}' in usados:
            cont[0] += 1
        usados.add(f'{prefixo}{cont[0]}')
        return f'{prefixo}{cont[0]}'
    out = []
    for r in placa.rows:
        if r[0] in ('LINE', 'VIA') and not manter(r):
            continue
        if r[0] == 'POUR' and pours is not None:
            continue
        out.append(r)
    # novos itens no fim, como as LINE/VIA do arquivo original
    novos = []
    for t in novas_trilhas:
        for (x1, y1), (x2, y2) in zip(t['pts'], t['pts'][1:]):
            if abs(x1 - x2) < 1e-6 and abs(y1 - y2) < 1e-6:
                continue
            novos.append(['LINE', prox(), 0, t['net'], t['layer'], mil(x1), mil(y1), mil(x2), mil(y2), mil(t['w']), 0])
    for v in novas_vias:
        novos.append(['VIA', prox(), 0, v['net'], '', mil(v['x']), mil(v['y']), mil(v['furo']), mil(v['d']), 0,
                      None, None, 0, []])
    for p in pours or []:
        p = list(p)
        p[1] = prox()
        novos.append(p)
    out = out + novos
    # ids no padrao do EasyEDA (e + numero) para os itens novos
    import re
    num = max([int(r[1][1:]) for r in out if len(r) > 1 and isinstance(r[1], str) and re.fullmatch(r'e\d+', r[1])] + [0])
    for r in out:
        if r[0] in ('LINE', 'VIA', 'POUR') and not re.fullmatch(r'e\d+', str(r[1])):
            num += 1
            r[1] = f'e{num}'
    texto = '\n'.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) for r in out) + '\n'
    dados = dict(placa.dados)
    dados[placa.pcb_nome] = texto.encode('utf8')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zo:
        for info in placa.z.infolist():
            zo.writestr(info, dados[info.filename])
    with open(saida, 'wb') as f:
        f.write(buf.getvalue())
