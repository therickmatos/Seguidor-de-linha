"""Leitura do cobre de um .epro (EasyEDA Pro 2.x) e verificador independente (08/11/2026).

  python easyeda_cobre.py placa.epro [--gnd-planos]

Le direto do .epcb: componentes (footprints do proprio .epro, face de baixo = espelho em y e
depois a rotacao), pads com a rede do PAD_NET, trilhas (LINE), vias (VIA, inclusive as dos
footprints), contorno (POLY na camada 11, ou o laco do Board Outline) e furos (FILL na camada 12).

Confere:
  - ligacoes: ilhas de cobre por rede (com --gnd-planos, o GND e ligado pelos planos simulados
    nas duas faces: placa - (cobre de outras redes + folga) - borda/furos);
  - folga entre cobres de redes diferentes (0,2 mm), cobre-borda e cobre-furo (0,3 mm);
  - larguras por classe de rede, com a excecao do pescoco nos pinos do DRV8874;
  - vias: tamanho por classe e nenhuma via em XTAL1/XTAL2.

Unidades: o .epcb guarda mil; aqui tudo vira mm no referencial do arquivo (origem no centro da
ventoinha, +y para a frente).

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import collections
import io
import json
import math
import sys
import zipfile

from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.ops import polygonize, unary_union
from shapely.strtree import STRtree

MIL = 0.0254
TOP, BOT, MULTI = 1, 2, 12

FOLGA = 0.2          # cobre-cobre
FOLGA_BORDA = 0.3    # cobre-borda e cobre-furo
FOLGA_PLANO = 0.3    # plano de GND simulado ate o cobre de outras redes (o EasyEDA usa <= isso)
TOL = 0.0005

POTENCIA = {'VBAT': 1.5, 'OUT_A1': 1.5, 'OUT_A2': 1.5, 'OUT_B1': 1.5, 'OUT_B2': 1.5, 'OUT_C': 1.0, '+5V': 0.5}
GARGALO = {'VBAT': 1.0, 'OUT_A1': 1.0, 'OUT_A2': 1.0, 'OUT_B1': 1.0, 'OUT_B2': 1.0, 'OUT_C': 1.0, '+5V': 0.5}
GARGALO_MAX_MM = 3.0
PESCOCO_W, PESCOCO_L = 0.4, 1.5      # saida dos pinos do DRV8874
DRV = ('U3', 'U4')
SINAL_MIN = 0.25
CRISTAL = ('XTAL1', 'XTAL2')
VIA_POT = (0.8, 0.4)                 # diametro, furo
REDES_POT_VIA = ('VBAT', 'OUT_A1', 'OUT_A2', 'OUT_B1', 'OUT_B2', 'OUT_C')


def ler_epro(caminho):
    z = zipfile.ZipFile(caminho)
    return z, {i.filename: z.read(i.filename) for i in z.infolist()}


def linhas_json(b):
    return [json.loads(l) for l in b.decode('utf8').split('\n') if l.strip()]


def nome_pcb(dados):
    return next(n for n in dados if n.startswith('PCB/') and n.endswith('.epcb'))


def transformar(px, py, x, y, rot, baixo):
    # face de baixo no EasyEDA Pro: espelho em y do footprint e depois a rotacao (conferido no
    # EVA_RT.eprj: com isso as 79 pontas de trilha nas pecas de baixo caem em pads da mesma rede;
    # com espelho em x, nenhuma)
    if baixo:
        py = -py
    t = math.radians(rot)
    return x + px * math.cos(t) - py * math.sin(t), y + px * math.sin(t) + py * math.cos(t)


def _forma_local(forma):
    tipo = forma[0]
    if tipo in ('RECT',):
        w, h = forma[1] * MIL, forma[2] * MIL
        raio = (forma[3] if len(forma) > 3 and forma[3] else 0) / 100 * min(w, h) / 2
        g = box(-w / 2, -h / 2, w / 2, h / 2)
        if raio > 1e-6:
            g = box(-w / 2 + raio, -h / 2 + raio, w / 2 - raio, h / 2 - raio).buffer(raio, quad_segs=8)
        return g
    if tipo in ('ELLIPSE', 'ROUND', 'CIRCLE'):
        w, h = forma[1] * MIL, forma[2] * MIL
        if abs(w - h) < 1e-6:
            return Point(0, 0).buffer(w / 2, quad_segs=16)
        return affinity.scale(Point(0, 0).buffer(1, quad_segs=16), w / 2, h / 2)
    if tipo == 'OVAL':
        w, h = forma[1] * MIL, forma[2] * MIL
        if w >= h:
            return LineString([(-(w - h) / 2, 0), ((w - h) / 2, 0)]).buffer(h / 2, quad_segs=12)
        return LineString([(0, -(h - w) / 2), (0, (h - w) / 2)]).buffer(w / 2, quad_segs=12)
    if tipo == 'POLY':
        pts = _caminho(forma[1])
        return Polygon(pts).buffer(0)
    raise ValueError(f'forma de pad desconhecida: {forma[:3]}')


def _caminho(lista):
    """Caminho do EasyEDA ([x, y, 'L', x, y, ...]) em mm. Arcos ('ARC') viram retas (so contorno)."""
    pts, i = [], 0
    while i < len(lista):
        v = lista[i]
        if isinstance(v, str):
            i += 1
            if v == 'ARC':
                i += 1      # angulo; o ponto seguinte e o fim
            continue
        pts.append((lista[i] * MIL, lista[i + 1] * MIL))
        i += 2
    return pts


def arco_pontos(p1, p2, angulo, passo_graus=1.0):
    """Pontos de um arco de p1 a p2 que varre `angulo` graus (positivo = anti-horario)."""
    th = math.radians(angulo)
    if abs(th) < 1e-9:
        return [p1, p2]
    (x1, y1), (x2, y2) = p1, p2
    c = math.dist(p1, p2)
    r = c / (2 * math.sin(abs(th) / 2))
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    ux, uy = (x2 - x1) / c, (y2 - y1) / c
    nx, ny = -uy, ux                      # normal a esquerda da corda
    h = r * math.cos(th / 2)
    s = 1 if th > 0 else -1
    cx, cy = mx + s * nx * h, my + s * ny * h
    a1 = math.atan2(y1 - cy, x1 - cx)
    n = max(2, int(abs(angulo) / passo_graus) + 1)
    pts = [(cx + r * math.cos(a1 + th * k / n), cy + r * math.sin(a1 + th * k / n)) for k in range(n + 1)]
    pts[0], pts[-1] = p1, p2
    return pts


def poured(placa):
    """Preenchimento salvo pelo EasyEDA (linhas POURED): {pour_id: [Polygon]} (arcos viram retas)."""
    out = collections.defaultdict(list)

    def anel_pts(anel):
        pts, i = [], 0
        while i < len(anel):
            v = anel[i]
            if v == 'L':
                i += 1
                continue
            if v == 'ARC':
                # arco do ponto anterior ate (x, y), varrendo `angulo` graus (mesma convencao do ARC de trilha)
                ang, x, y = anel[i + 1], anel[i + 2] * MIL * 10, anel[i + 3] * MIL * 10
                if pts and math.dist(pts[-1], (x, y)) > 1e-6:
                    pts += arco_pontos(pts[-1], (x, y), ang, passo_graus=10.0)[1:]
                else:
                    pts.append((x, y))
                i += 4
                continue
            if isinstance(v, str):
                i += 1
                continue
            pts.append((anel[i] * MIL * 10, anel[i + 1] * MIL * 10))   # POURED: unidade de 10 mil
            i += 2
        return pts
    for r in placa.rows:
        if r[0] != 'POURED':
            continue
        # primeiro anel = contorno, os seguintes = furos
        aneis = [anel_pts(a) for a in r[5]]
        aneis = [a for a in aneis if len(a) >= 3]
        if aneis:
            out[r[2]].append(Polygon(aneis[0], aneis[1:]).buffer(0))
    return out


def colocar(g, x, y, rot, baixo):
    if baixo:
        g = affinity.scale(g, 1, -1, origin=(0, 0))
    g = affinity.rotate(g, rot, origin=(0, 0))
    return affinity.translate(g, x, y)


class Placa:
    def __init__(self, caminho):
        self.z, self.dados = ler_epro(caminho)
        self.pcb_nome = nome_pcb(self.dados)
        self.rows = linhas_json(self.dados[self.pcb_nome])
        self._ler()

    # ------------------------------------------------------------------ leitura
    def _ler(self):
        attr = collections.defaultdict(dict)
        for r in self.rows:
            if r[0] == 'ATTR':
                attr[r[3]][r[7]] = r[8]
        padnet = {}
        for r in self.rows:
            if r[0] == 'PAD_NET':
                padnet[(r[1], r[4])] = (str(r[2]), r[3])
        self.comps = {}
        self.pads = []        # dict: des, num, net, layers, geom, centro, comp, furo
        self.vias = []        # dict: id, net, x, y, d, furo, comp
        self.npth = []        # geometrias de furos sem cobre
        for r in self.rows:
            if r[0] != 'COMPONENT':
                continue
            cid, baixo = r[1], r[3] == 2
            x, y, rot = r[4] * MIL, r[5] * MIL, r[6] or 0
            des = attr[cid].get('Designator')
            fpid = attr[cid].get('Footprint')
            self.comps[des] = {'id': cid, 'x': x, 'y': y, 'rot': rot, 'baixo': baixo, 'fp': fpid}
            for f in linhas_json(self.dados[f'FOOTPRINT/{fpid}.efoo']):
                if f[0] == 'PAD':
                    num = str(f[5])
                    net = padnet.get((cid, f[1]), (num, None))[1] or None
                    g = _forma_local(f[10])
                    g = affinity.rotate(g, f[8] or 0, origin=(0, 0))
                    g = affinity.translate(g, f[6] * MIL, f[7] * MIL)
                    g = colocar(g, x, y, rot, baixo)
                    lay = f[4]
                    furo = (f[9][1] * MIL) if f[9] and len(f[9]) > 1 and f[9][1] else 0
                    if lay == MULTI or furo > 0:
                        layers = {TOP, BOT}
                    elif lay == TOP:
                        layers = {BOT} if baixo else {TOP}
                    elif lay == BOT:
                        layers = {TOP} if baixo else {BOT}
                    else:
                        continue
                    cx, cy = transformar(f[6] * MIL, f[7] * MIL, x, y, rot, baixo)
                    self.pads.append({'des': des, 'num': num, 'net': net, 'layers': layers, 'geom': g,
                                      'centro': (cx, cy), 'comp': cid, 'furo': furo, 'id': f[1],
                                      'forma': f[10]})
                elif f[0] == 'VIA':
                    net = padnet.get((cid, f[1]), ('', None))[1] or None
                    cx, cy = transformar(f[5] * MIL, f[6] * MIL, x, y, rot, baixo)
                    self.vias.append({'id': f'{des}:{f[1]}', 'net': net, 'x': cx, 'y': cy, 'furo': f[7] * MIL,
                                      'd': f[8] * MIL, 'comp': des})
                elif f[0] == 'FILL' and f[4] == MULTI:
                    for forma in f[7]:
                        if forma[0] == 'CIRCLE':
                            cx, cy = transformar(forma[1] * MIL, forma[2] * MIL, x, y, rot, baixo)
                            self.npth.append(Point(cx, cy).buffer(forma[3] * MIL, quad_segs=24))
        # nivel da placa
        self.tracks = []
        segs_borda = []
        for r in self.rows:
            if r[0] == 'LINE' and r[4] in (TOP, BOT):
                self.tracks.append({'id': r[1], 'net': r[3] or None, 'layer': r[4],
                                    'a': (r[5] * MIL, r[6] * MIL), 'b': (r[7] * MIL, r[8] * MIL),
                                    'w': r[9] * MIL, 'lock': r[10] if len(r) > 10 else 0})
            elif r[0] == 'ARC' and r[4] in (TOP, BOT):
                # trilha em arco: ["ARC", id, ?, rede, camada, x1, y1, x2, y2, angulo (graus), largura, trava]
                # vira segmentos curtos (id#k); o sentido do angulo so muda o lado do bojo
                pts = arco_pontos((r[5] * MIL, r[6] * MIL), (r[7] * MIL, r[8] * MIL), r[9])
                for k, (a, b) in enumerate(zip(pts, pts[1:])):
                    self.tracks.append({'id': f'{r[1]}#{k}', 'net': r[3] or None, 'layer': r[4], 'a': a, 'b': b,
                                        'w': r[10] * MIL, 'lock': r[11] if len(r) > 11 else 0, 'arco': r[1]})
            elif r[0] == 'VIA':
                self.vias.append({'id': r[1], 'net': r[3] or None, 'x': r[5] * MIL, 'y': r[6] * MIL,
                                  'furo': r[7] * MIL, 'd': r[8] * MIL, 'comp': None})
            elif r[0] == 'POLY' and r[4] == 11:
                pts = _caminho(r[6])
                segs_borda += [LineString([a, b]) for a, b in zip(pts, pts[1:])]
            elif r[0] == 'FILL' and r[4] == MULTI:
                for forma in r[7]:
                    if forma[0] == 'CIRCLE':
                        self.npth.append(Point(forma[1] * MIL, forma[2] * MIL).buffer(forma[3] * MIL, quad_segs=32))
            elif r[0] == 'PAD':      # pads soltos (rasgos do velcro)
                g = _forma_local(r[10])
                g = affinity.rotate(g, r[8] or 0, origin=(0, 0))
                g = affinity.translate(g, r[6] * MIL, r[7] * MIL)
                self.pads.append({'des': f'PAD:{r[1]}', 'num': str(r[5]), 'net': r[3] or None,
                                  'layers': {TOP, BOT}, 'geom': g, 'centro': (r[6] * MIL, r[7] * MIL),
                                  'comp': None, 'furo': 1, 'id': r[1], 'forma': r[10]})
        laços = list(polygonize(unary_union(segs_borda)))
        laços.sort(key=lambda p: -p.area)
        ext = laços[0]
        internos = [p for p in laços[1:] if ext.contains(p.representative_point())]
        self.borda = ext.difference(unary_union(internos)) if internos else ext
        self.placa = self.borda.difference(unary_union(self.npth)) if self.npth else self.borda

    # --------------------------------------------------------------- geometria
    def objetos(self):
        """Lista de objetos de cobre: dict(tipo, net, layers, geom, ref)."""
        objs = []
        for p in self.pads:
            objs.append({'tipo': 'pad', 'net': p['net'], 'layers': p['layers'], 'geom': p['geom'],
                         'ref': f"{p['des']}.{p['num']}", 'obj': p})
        for t in self.tracks:
            g = (LineString([t['a'], t['b']]) if t['a'] != t['b'] else Point(t['a'])).buffer(t['w'] / 2, quad_segs=8)
            objs.append({'tipo': 'trilha', 'net': t['net'], 'layers': {t['layer']}, 'geom': g,
                         'ref': t['id'], 'obj': t})
        for v in self.vias:
            objs.append({'tipo': 'via', 'net': v['net'], 'layers': {TOP, BOT},
                         'geom': Point(v['x'], v['y']).buffer(v['d'] / 2, quad_segs=12), 'ref': v['id'], 'obj': v})
        return objs

    def planos_gnd(self, objs=None, folga=FOLGA_PLANO, largura_min=0.25):
        """Plano de GND simulado em cada face: placa - borda/furos(0,3) - outras redes(folga)."""
        objs = objs or self.objetos()
        area = self.borda.buffer(-FOLGA_BORDA)
        if self.npth:
            area = area.difference(unary_union(self.npth).buffer(FOLGA_BORDA))
        planos = {}
        for lay in (TOP, BOT):
            outros = [o['geom'] for o in objs if lay in o['layers'] and o['net'] != 'GND']
            # furos de pads/vias de GND tambem tiram cobre so no furo (ignorado: o anel e GND)
            g = area.difference(unary_union(outros).buffer(folga, quad_segs=6))
            # sobras muito finas nao sao preenchidas (largura minima do preenchimento 0,25 mm)
            g = g.buffer(-largura_min / 2, quad_segs=4).buffer(largura_min / 2, quad_segs=4)
            planos[lay] = g
        return planos


# ---------------------------------------------------------------------- checagens
def ilhas(objs, net, extra=()):
    itens = [o for o in objs if o['net'] == net] + list(extra)
    pai = list(range(len(itens)))

    def raiz(i):
        while pai[i] != i:
            pai[i] = pai[pai[i]]
            i = pai[i]
        return i
    tree = STRtree([o['geom'] for o in itens])
    for i, o in enumerate(itens):
        for j in tree.query(o['geom'], predicate='intersects'):
            j = int(j)
            if j > i and o['layers'] & itens[j]['layers']:
                pai[raiz(i)] = raiz(j)
    grupos = collections.defaultdict(list)
    for i, o in enumerate(itens):
        grupos[raiz(i)].append(o)
    return list(grupos.values())


def folgas(placa, objs, folga=FOLGA, so_redes=None):
    prob = []
    geoms = [o['geom'] for o in objs]
    tree = STRtree(geoms)
    for i, o in enumerate(objs):
        for j in tree.query(o['geom'].buffer(folga), predicate='intersects'):
            j = int(j)
            if j <= i:
                continue
            q = objs[j]
            if not (o['layers'] & q['layers']):
                continue
            if o['net'] is not None and o['net'] == q['net']:
                continue
            if o['tipo'] == 'pad' and q['tipo'] == 'pad' and o['obj']['comp'] is not None and o['obj']['comp'] == q['obj']['comp'] \
                    and o['net'] is None and q['net'] is None:
                continue
            if so_redes and o['net'] not in so_redes and q['net'] not in so_redes:
                continue
            d = o['geom'].distance(q['geom'])
            if d < folga - TOL:
                prob.append((round(d, 3), o['ref'], o['net'], q['ref'], q['net'], sorted(o['layers'] & q['layers'])))
    return prob


def borda(placa, objs):
    prob = []
    contorno = placa.borda.boundary
    furos = unary_union(placa.npth) if placa.npth else None
    for o in objs:
        if o['tipo'] == 'pad' and o['obj']['comp'] is None:
            continue
        d = o['geom'].distance(contorno)
        if not placa.borda.contains(o['geom']):
            d = -1
        if d < FOLGA_BORDA - TOL:
            prob.append(('borda', round(d, 3), o['ref'], o['net']))
        if furos is not None:
            d2 = o['geom'].distance(furos)
            if d2 < FOLGA_BORDA - TOL:
                prob.append(('furo', round(d2, 3), o['ref'], o['net']))
    return prob


RAMO_VENTOINHA = ('M3.1', 'D1.1', 'C17.1')   # VBAT no ramo da ventoinha: 1,0 mm


def _segs(ts):
    return unary_union([(LineString([t['a'], t['b']]) if t['a'] != t['b'] else Point(t['a'])).buffer(t['w'] / 2, quad_segs=8)
                        for t in ts])


def _eixo(ts):
    """Eixo (linha central) das trilhas: o comprimento de pescoco e gargalo e medido ao longo dele."""
    from shapely.geometry import MultiLineString
    return unary_union([LineString([t['a'], t['b']]) for t in ts if t['a'] != t['b']] or [Point(1e6, 1e6)])


def _clusters(ts):
    """Agrupa trilhas que se tocam (mesma camada)."""
    pai = list(range(len(ts)))

    def raiz(i):
        while pai[i] != i:
            pai[i] = pai[pai[i]]
            i = pai[i]
        return i
    gs = [_segs([t]) for t in ts]
    for i in range(len(ts)):
        for j in range(i + 1, len(ts)):
            if ts[i]['layer'] == ts[j]['layer'] and gs[i].distance(gs[j]) < 1e-4:
                pai[raiz(i)] = raiz(j)
    grupos = collections.defaultdict(list)
    for i, t in enumerate(ts):
        grupos[raiz(i)].append(t)
    return list(grupos.values())


def larguras(placa):
    """Trilhas de potencia abaixo do minimo, medidas como cadeias continuas.

    - pescoco (largura < gargalo): so na saida de pino do DRV8874, >= 0,4 mm e no maximo 1,5 mm
      de comprimento fora do pad (ate encostar em cobre mais largo), medido no eixo da trilha;
    - gargalo (gargalo <= largura < minimo): no maximo 3 mm por cadeia, fora de pads e de cobre largo;
      o VBAT no ramo da ventoinha (M3.1, D1.1, C17.1) e o OUT_C tem minimo de 1,0 mm.
    Devolve lista de (rede, ids, largura minima, comprimento, motivo)."""
    prob = []
    for net, wmin in POTENCIA.items():
        ts = [t for t in placa.tracks if t['net'] == net]
        pads = [p for p in placa.pads if p['net'] == net]
        for camada in (TOP, BOT):
            tc = [t for t in ts if t['layer'] == camada]
            largas = _segs([t for t in tc if t['w'] >= wmin - TOL])
            pads_c = unary_union([p['geom'] for p in pads if camada in p['layers']] or [Point(1e6, 1e6)])
            finas = [t for t in tc if t['w'] < wmin - TOL]
            for cl in _clusters(finas):
                ids = ','.join(t['id'] for t in cl)
                wcl = min(t['w'] for t in cl)
                g = _segs(cl)
                toca = [p for p in pads if camada in p['layers'] and p['geom'].distance(g) < 1e-3]
                nomes = {f"{p['des']}.{p['num']}" for p in toca}
                if net == 'VBAT' and nomes & set(RAMO_VENTOINHA) and wcl >= 1.0 - TOL:
                    continue
                pesc = [t for t in cl if t['w'] < GARGALO[net] - TOL]
                garg = [t for t in cl if t['w'] >= GARGALO[net] - TOL]
                if pesc:
                    wp = min(t['w'] for t in pesc)
                    gp = _segs(pesc)
                    drv = [p for p in toca if p['des'] in DRV and p['geom'].distance(gp) < 1e-3]
                    L = _eixo(pesc).difference(unary_union([pads_c, largas, _segs(garg) if garg else Point(1e6, 1e6)])).length
                    if drv and wp >= PESCOCO_W - TOL and L <= PESCOCO_L + 0.05:
                        prob.append((net, ids, round(wp, 3), round(L, 2), f'pescoco {drv[0]["des"]}.{drv[0]["num"]} (aceito)'))
                    else:
                        prob.append((net, ids, round(wp, 3), round(L, 2), 'PESCOCO FORA DA REGRA'))
                if garg:
                    gg = _segs(garg)
                    L = _eixo(garg).difference(unary_union([pads_c, largas])).length
                    if L <= GARGALO_MAX_MM + 0.05:
                        prob.append((net, ','.join(t['id'] for t in garg), round(min(t['w'] for t in garg), 3), round(L, 2), 'gargalo curto (aceito)'))
                    else:
                        prob.append((net, ','.join(t['id'] for t in garg), round(min(t['w'] for t in garg), 3), round(L, 2), 'GARGALO LONGO'))
    for t in placa.tracks:
        if t['net'] and t['net'] not in POTENCIA and t['net'] != 'GND' and t['w'] < SINAL_MIN - TOL:
            prob.append((t['net'], t['id'], round(t['w'], 3), round(math.dist(t['a'], t['b']), 2), 'SINAL FINO'))
    return prob


VIA_PAD_SMD = 0.2   # borda da via ate pad SMD, mesmo da mesma rede (regra "SMD Pad to Via" do EasyEDA)


def vias(placa):
    prob = []
    smd = [p for p in placa.pads if len(p['layers']) == 1]
    for v in placa.vias:
        if v['comp']:
            continue
        P = Point(v['x'], v['y'])
        for p in smd:
            d = p['geom'].distance(P) - v['d'] / 2
            if d < VIA_PAD_SMD - TOL:
                prob.append(('via perto de pad SMD', v['id'], v['net'], f"{p['des']}.{p['num']}", round(d, 3)))
        if v['net'] in CRISTAL:
            prob.append(('via no cristal', v['id'], v['net']))
        if v['net'] in REDES_POT_VIA and (v['d'] < VIA_POT[0] - TOL or v['furo'] < VIA_POT[1] - TOL):
            prob.append(('via de potencia pequena', v['id'], v['net'], round(v['d'], 3), round(v['furo'], 3)))
        if v['net'] is None:
            prob.append(('via sem rede', v['id']))
    return prob


FURO_FURO = 0.3     # borda a borda entre furos (vias e pads passantes)


def furos(placa):
    """Pares de furos (vias e pads passantes) a menos de FURO_FURO mm borda a borda."""
    hs = [((v['x'], v['y']), v['furo'], v['id']) for v in placa.vias]
    hs += [(p['centro'], p['furo'], f"{p['des']}.{p['num']}") for p in placa.pads
           if p['furo'] and not p['des'].startswith('PAD:')]
    prob = []
    for i in range(len(hs)):
        for j in range(i + 1, len(hs)):
            d = math.dist(hs[i][0], hs[j][0]) - hs[i][1] / 2 - hs[j][1] / 2
            if d < FURO_FURO - TOL:
                prob.append((round(d, 3), hs[i][2], hs[j][2]))
    return prob


def pontas_soltas(placa, objs):
    """Extremidades de trilha que nao tocam nada da mesma rede (trilha morta)."""
    prob = []
    por_rede = collections.defaultdict(list)
    for o in objs:
        por_rede[o['net']].append(o)
    for t in placa.tracks:
        for pt in (t['a'], t['b']):
            P = Point(pt)
            ok = False
            for o in por_rede[t['net']]:
                if o['obj'] is t or t['layer'] not in o['layers']:
                    continue
                if o['geom'].distance(P) < 0.01:
                    ok = True
                    break
            if not ok:
                prob.append((t['net'], t['id'], tuple(round(v, 3) for v in pt)))
    return prob


def relatorio(caminho, gnd_planos=True, saida=print):
    placa = Placa(caminho)
    objs = placa.objetos()
    redes = sorted({p['net'] for p in placa.pads if p['net']})
    saida(f'componentes {len(placa.comps)}, pads {len(placa.pads)}, trilhas {len(placa.tracks)}, '
          f'vias {len(placa.vias)} ({sum(1 for v in placa.vias if not v["comp"])} da placa), redes {len(redes)}')
    abertas = {}
    extra = []
    if gnd_planos:
        planos = placa.planos_gnd(objs)
        for lay, g in planos.items():
            geoms = list(g.geoms) if isinstance(g, MultiPolygon) else [g]
            extra += [{'tipo': 'plano', 'net': 'GND', 'layers': {lay}, 'geom': gg, 'ref': f'plano{lay}', 'obj': None}
                      for gg in geoms if not gg.is_empty]
    for net in redes:
        gr = ilhas(objs, net, extra if net == 'GND' else ())
        grp = [g for g in gr if any(o['tipo'] == 'pad' for o in g)]
        if len(grp) > 1:
            abertas[net] = [sorted(o['ref'] for o in g if o['tipo'] == 'pad') for g in grp]
    saida(f'\n== ligacoes abertas ({len(abertas)} redes) ==')
    for net, gs in abertas.items():
        saida(f'  {net}: {len(gs)} ilhas -> ' + ' | '.join(','.join(g) for g in gs))
    f = folgas(placa, objs)
    saida(f'\n== folga < {FOLGA} mm entre redes diferentes: {len(f)} ==')
    for p in sorted(f):
        saida('  ' + str(p))
    b = borda(placa, objs)
    saida(f'\n== cobre a menos de {FOLGA_BORDA} mm da borda/furo: {len(b)} ==')
    for p in b:
        saida('  ' + str(p))
    w = larguras(placa)
    ruins = [x for x in w if 'aceito' not in x[4]]
    saida(f'\n== larguras: {len(ruins)} abaixo do minimo, {len(w) - len(ruins)} gargalos/pescocos aceitos ==')
    for p in sorted(w):
        saida('  ' + str(p))
    v = vias(placa) + [('furo-furo',) + x for x in furos(placa)]
    saida(f'\n== vias: {len(v)} problemas ==')
    for p in v:
        saida('  ' + str(p))
    s = pontas_soltas(placa, objs)
    saida(f'\n== pontas de trilha soltas: {len(s)} ==')
    for p in s[:60]:
        saida('  ' + str(p))
    return placa, abertas, f, b, ruins, v, s


if __name__ == '__main__':
    relatorio(sys.argv[1], gnd_planos='--gnd-planos' in sys.argv)
