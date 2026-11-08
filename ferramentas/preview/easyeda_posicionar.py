"""Posiciona as pecas de um projeto EasyEDA Pro (.epro) pela placa de referencia (KiCad / previa v2)
e coloca o contorno, os furos e os rasgos. Feito para o projeto RUSH do Erick (07/11/2026).

  python easyeda_posicionar.py entrada.epro saida.epro

- Cada peca do .epcb (achada pelo designador) recebe posicao, rotacao e face calculadas para o
  footprint DELA (o do EasyEDA): os pads com o mesmo numero do esquematico sao ajustados, por minimos
  quadrados, aos pads da referencia (placa_v2 + footprints da previa). Face de baixo = espelho em y do
  footprint e depois a rotacao (convencao do EasyEDA; ate 08/11/2026 este script usava espelho em x,
  o que esta errado: as pecas de baixo do projeto RUSH ficaram giradas 180 graus em relacao ao calculado).
- Origem = centro do furo da ventoinha, +y = frente (o EasyEDA Pro guarda a placa em mil, y para cima).
- Contorno (POLY na camada 11, em segmentos, como no EVA-RT), furos (FILL circular na camada 12, como os
  furos do EVA-RT) e rasgos do velcro (laco fechado na camada 11, recorte interno).
- O designador vai para o centro da peca (camada de serigrafia da face dela).
- Confere depois: distancia de cada pad ao pad de referencia, folga entre pads de redes diferentes,
  pad-borda/furo, e a rede de cada pad (PAD_NET do EasyEDA) contra a rede da referencia.

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import collections
import io
import json
import math
import sys
import zipfile

from shapely.geometry import LineString, Point, Polygon, box
from shapely import affinity

import layout_placa as M
import placa_v2 as V

MIL = 0.0254
# pecas em que so os pads pequenos entram no ajuste (a aba/pad termico do footprint da LCSC tem outro centro)
SO_PINOS = {'U1': ['1', '3']}
# deslocamentos (mm) depois do ajuste, por causa de footprints da LCSC maiores que os da referencia:
# o cristal 5032 da LCSC (pads 1,9 x 2,4 em +-2,05) encostava nos pinos do TQFP da LCSC (mais longos) e
# ficava a 0,13 mm da borda; o C10 ficava a 0,199 mm do pino 8 do ATmega
AJUSTES = {'X1': (-0.6, 0.2), 'C10': (0.0, -0.05)}


def mil(v):
    return round(v / MIL, 4)


def ler_epro(caminho):
    z = zipfile.ZipFile(caminho)
    return z, {i.filename: z.read(i.filename) for i in z.infolist()}


def linhas_json(b):
    return [json.loads(l) for l in b.decode('utf8').split('\n') if l.strip()]


def pads_footprint(dados, uuid):
    """{numero: {'x','y' (mm), 'w','h' (mm, ja girados pela rotacao do pad), 'forma', 'furo'}}"""
    out = {}
    for r in linhas_json(dados[f'FOOTPRINT/{uuid}.efoo']):
        if r[0] != 'PAD':
            continue
        num, x, y, prot = str(r[5]), r[6] * MIL, r[7] * MIL, r[8] or 0
        forma = r[10][0]
        w, h = r[10][1] * MIL, r[10][2] * MIL
        furo = r[9][1] * MIL if r[9] and r[9][1] else 0
        out.setdefault(num, []).append({'x': x, 'y': y, 'w': w, 'h': h, 'rot': prot, 'forma': forma,
                                        'furo': furo, 'camada': r[4]})
    return out


def transformar(px, py, x, y, rot, baixo):
    # face de baixo no EasyEDA Pro: espelho em y do footprint e depois a rotacao. Corrigido em 08/11/2026
    # (antes era espelho em x, o que deixava as pecas de baixo giradas 180 graus em relacao ao calculado);
    # conferido no EVA_RT.eprj: com espelho em y as 79 pontas de trilha das pecas de baixo caem em pads
    # da mesma rede. Ver easyeda_cobre.py.
    if baixo:
        py = -py
    t = math.radians(rot)
    return x + px * math.cos(t) - py * math.sin(t), y + px * math.sin(t) + py * math.cos(t)


def forma_pad(p, x, y, rot, baixo):
    cx, cy = transformar(p['x'], p['y'], x, y, rot, baixo)
    w, h = p['w'], p['h']
    if p['forma'] in ('ELLIPSE', 'ROUND') and abs(w - h) < 1e-6:
        return Point(cx, cy).buffer(w / 2, quad_segs=12)
    if p['forma'] in ('OVAL', 'ELLIPSE'):
        g = (LineString([(-(w - h) / 2, 0), ((w - h) / 2, 0)]).buffer(h / 2, quad_segs=12) if w >= h else
             LineString([(0, -(h - w) / 2), (0, (h - w) / 2)]).buffer(w / 2, quad_segs=12))
    else:
        g = box(-w / 2, -h / 2, w / 2, h / 2)
    g = affinity.rotate(g, p['rot'] or 0, origin=(0, 0))
    if baixo:
        g = affinity.scale(g, 1, -1, origin=(0, 0))
    g = affinity.rotate(g, rot, origin=(0, 0))
    return affinity.translate(g, cx, cy)


def ajustar(locais, alvos, baixo):
    """Rotacao + translacao (com espelho em y se baixo) que leva os pads locais aos alvos."""
    a = [(x, -y if baixo else y) for x, y in locais]
    ax, ay = sum(p[0] for p in a) / len(a), sum(p[1] for p in a) / len(a)
    qx, qy = sum(p[0] for p in alvos) / len(alvos), sum(p[1] for p in alvos) / len(alvos)
    s_cross = sum((p[0] - ax) * (q[1] - qy) - (p[1] - ay) * (q[0] - qx) for p, q in zip(a, alvos))
    s_dot = sum((p[0] - ax) * (q[0] - qx) + (p[1] - ay) * (q[1] - qy) for p, q in zip(a, alvos))
    rot = math.degrees(math.atan2(s_cross, s_dot))
    # arredonda para 0,01 grau (as rotacoes da referencia sao multiplos de 45)
    for passo in (45.0, 0.01):
        r = round(rot / passo) * passo
        if abs(r - rot) < 0.5:
            rot = r
            break
    t = math.radians(rot)
    x = qx - (ax * math.cos(t) - ay * math.sin(t))
    y = qy - (ax * math.sin(t) + ay * math.cos(t))
    return x, y, rot % 360


def referencia():
    """ref -> {'face', 'pinos': {pino_esquematico: (x, y)}} da placa de referencia."""
    import footprints as F
    out = {}
    for c in V.load():
        fp = F.FOOTPRINTS[c['footprint']]
        mapa = {p['pino']: str(p['rede_pino']) for p in fp['pads']}
        pinos = {}
        for p in M.get_pads(c):
            sp = mapa.get(p['pin'])
            if sp and sp not in pinos:
                pinos[sp] = (p['x'], p['y'], p['net'])
        out[c['ref']] = {'face': c['face'], 'pinos': pinos}
    return out


def contorno_e_furos(prox_id):
    rows = []
    pts = list(M.OUTLINE.exterior.coords)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        rows.append(['POLY', prox_id(), 0, '', 11, 10, [mil(x0), mil(y0), 'L', mil(x1), mil(y1)], 0])
    for h in M.BOARD_DATA['furos']:
        if h['tipo'] == 'furo':
            rows.append(['FILL', prox_id(), 0, '', 12, 1, 0, [['CIRCLE', mil(h['x']), mil(h['y']), mil(h['d'] / 2)]], 0])
        else:   # rasgo com pontas redondas: laco fechado no contorno (recorte interno)
            r = h['h'] / 2
            g = LineString([(h['x'] - h['w'] / 2 + r, h['y']), (h['x'] + h['w'] / 2 - r, h['y'])]).buffer(r, quad_segs=8)
            p = list(g.exterior.coords)
            for (x0, y0), (x1, y1) in zip(p, p[1:]):
                rows.append(['POLY', prox_id(), 0, '', 11, 10, [mil(x0), mil(y0), 'L', mil(x1), mil(y1)], 0])
    return rows


def main(entrada, saida):
    z, dados = ler_epro(entrada)
    pcb_nome = next(n for n in dados if n.startswith('PCB/') and n.endswith('.epcb'))
    pcb = linhas_json(dados[pcb_nome])
    attr = collections.defaultdict(dict)
    attr_row = {}
    for r in pcb:
        if r[0] == 'ATTR':
            attr[r[3]][r[7]] = r[8]
            if r[7] == 'Designator':
                attr_row[r[3]] = r
    padnet = {(r[1], str(r[2])): r[3] for r in pcb if r[0] == 'PAD_NET' and r[2] != ''}
    ref = referencia()
    rel, novo = [], {}
    for r in pcb:
        if r[0] != 'COMPONENT':
            continue
        des = attr[r[1]].get('Designator')
        if des not in ref:
            rel.append((des, 'SEM REFERENCIA'))
            continue
        fp = pads_footprint(dados, attr[r[1]]['Footprint'])
        baixo = ref[des]['face'] == 'BOTTOM'
        pinos = SO_PINOS.get(des, sorted(ref[des]['pinos']))
        comuns = [p for p in pinos if p in fp]
        loc = [(fp[p][0]['x'], fp[p][0]['y']) for p in comuns]
        alv = [ref[des]['pinos'][p][:2] for p in comuns]
        x, y, rot = ajustar(loc, alv, baixo)
        dx, dy = AJUSTES.get(des, (0.0, 0.0))
        x, y = x + dx, y + dy
        erro = max(math.dist(transformar(*l, x, y, rot, baixo), q) for l, q in zip(loc, alv))
        erro_todos = max(math.dist(transformar(fp[p][0]['x'], fp[p][0]['y'], x, y, rot, baixo), ref[des]['pinos'][p][:2])
                         for p in ref[des]['pinos'] if p in fp)
        rede_errada = [p for p in ref[des]['pinos'] if padnet.get((r[1], p)) not in (ref[des]['pinos'][p][2], None)]
        novo[r[1]] = (x, y, rot, baixo, des, fp)
        rel.append((des, round(x, 3), round(y, 3), rot, 'baixo' if baixo else 'cima', round(erro, 3),
                    round(erro_todos, 3), rede_errada))
    # escreve
    usados = {r[1] for r in pcb if len(r) > 1 and isinstance(r[1], str)}
    cont = [90000]

    def prox_id():
        while f'e{cont[0]}' in usados:
            cont[0] += 1
        usados.add(f'e{cont[0]}')
        return f'e{cont[0]}'
    out = []
    for r in pcb:
        if r[0] == 'COMPONENT' and r[1] in novo:
            x, y, rot, baixo, _, _ = novo[r[1]]
            r = list(r)
            r[3], r[4], r[5], r[6] = (2 if baixo else 1), mil(x), mil(y), rot
        elif r[0] == 'ATTR' and r[7] == 'Designator' and r[3] in novo:
            x, y, rot, baixo, _, _ = novo[r[3]]
            r = list(r)
            r[4], r[5], r[6] = (4 if baixo else 3), mil(x), mil(y)
        out.append(r)
    out += contorno_e_furos(prox_id)
    texto = '\n'.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) for r in out)
    dados[pcb_nome] = texto.encode('utf8')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zo:
        for info in z.infolist():
            zo.writestr(info, dados[info.filename])
    open(saida, 'wb').write(buf.getvalue())
    return rel, novo


def conferir(novo, padnet_por_comp=None):
    """Folgas entre pads de redes diferentes e pad-borda/furo, com os footprints do EasyEDA."""
    ref = referencia()
    pads = []
    for cid, (x, y, rot, baixo, des, fp) in novo.items():
        for num, lst in fp.items():
            for p in lst:
                g = forma_pad(p, x, y, rot, baixo)
                tht = p['camada'] == 12 or p['furo'] > 0
                faces = {1, 2} if tht else ({2} if baixo else {1})
                rede = ref[des]['pinos'].get(num, (0, 0, None))[2]
                pads.append((des, num, rede, faces, g))
    prob = []
    borda = M.BOARD.boundary
    for d, n, rede, f, g in pads:
        dist = g.distance(borda) if M.BOARD.contains(g.centroid) else -1
        if dist < 0.299:
            prob.append(('borda/furo', f'{d}.{n}', round(dist, 3)))
    for i, a in enumerate(pads):
        for b in pads[i + 1:]:
            if a[0] == b[0] and a[1] == b[1]:
                continue
            if not (a[3] & b[3]):
                continue
            if a[2] is not None and a[2] == b[2]:
                continue
            dd = a[4].distance(b[4])
            if dd < 0.2:
                prob.append(('folga', f'{a[0]}.{a[1]}', f'{b[0]}.{b[1]}', round(dd, 3)))
    return prob


if __name__ == '__main__':
    rel, novo = main(sys.argv[1], sys.argv[2])
    for linha in rel:
        print(*linha)
    for p in conferir(novo):
        print('PROBLEMA', *p)
