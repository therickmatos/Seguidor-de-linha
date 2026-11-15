"""Gera o projeto EasyEDA Pro "RUSH - Dreamcast" (perseguidor) a partir do
"RUSH - Saturn - Final" (seguidor validado), trazendo do "RUSH perseguidor -
entalhe A" o contorno de 100 x 58,6 mm e o receptor IR J6 (KY-022).

Uso (a partir da raiz do repositório):
    python3 perseguidor/ferramentas/gerar_dreamcast.py

O que muda em relação ao Saturn:
  Esquemático
    - saem os 4 sensores de marca e seus componentes: S1-S4, R4, R5, R7, R8,
      R23-R26, C19, C20 (bloco 3);
    - ficam LED2/R6 (LED A, D2) e LED3/R9 (LED B, D7), agora nas pontas;
    - entra J6 (receptor IR KY-022: 1 = S, 2 = +5V, 3 = GND) em A5 (rede IR_A5);
    - A6 (pino 19), D8 (12) e D9 (13) ficam sem ligação (marca "X").
  PCB
    - contorno trocado pelo do Rush (entalhe A);
    - componentes, redes, trilhas e vias dos sensores de marca removidos;
    - tudo que ficava fora do novo contorno removido; trilhas que ficaram com
      ponta solta são podadas (exceto GND, LEDA_D2 e LEDB_D7);
    - a trilha do A5 (antiga MARK_L_A5) é reaproveitada até a via em
      (-44,76; 5,07) e ligada ao pino 1 do J6; +5V do J6 ligado à trilha de
      +5V em x = -40,51;
    - LED2/LED3 (em cima) e R6/R9 (embaixo) nas pontas da frente,
      x = +-48,3 / +-46,2 mm, y = 11,0 mm. Ficam SEM ROTEAR (ratsnest);
    - preenchimentos de cobre (POURED) apagados: refazer no EasyEDA (Shift+B).

Baseado no RUSH/SATURN, derivado do EVA-RT (EXOTIC TEAM MX), AGPL-3.0.
"""
import glob, copy, json, math, os, re, shutil, sys, tempfile, zipfile
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from epcb import MIL, outline, pathpts  # noqa: E402
from shapely.geometry import LineString, Point  # noqa: E402

RAIZ = os.path.dirname(AQUI)
SATURN = os.path.join(RAIZ, 'origem', 'RUSH - Saturn - Final.epro')
RUSH = os.path.join(RAIZ, 'origem', 'RUSH perseguidor - entalhe A.epro')
SAIDA = os.path.join(RAIZ, 'RUSH - Dreamcast.epro')
NOME = 'RUSH - Dreamcast'
DATA = '2026-11-15'

DEL_DES = {'S1', 'S2', 'S3', 'S4', 'R4', 'R5', 'R7', 'R8',
           'R23', 'R24', 'R25', 'R26', 'C19', 'C20'}
DEL_NETS = {'MARK_R_A6', 'MARK_L2_D8', 'MARK_R2_D9', 'QRE_E1_A', 'QRE_D1_A',
            '$1N2264', '$1N2285'}
RENAME = {'MARK_L_A5': 'IR_A5'}
NO_PRUNE = {'GND', 'LEDA_D2', 'LEDB_D7'}
# novas posições (mm): designador -> (x, y)
MOVE = {'LED2': (-48.3, 11.0), 'R6': (-46.2, 11.0),
        'LED3': (48.3, 11.0), 'R9': (46.2, 11.0)}
ROT = {'R9': 90}   # R9 girado igual ao R6: pino 2 (lado do LED) em cima
# J6 (centro do pino 2), girado como no Rush: pinos 1-2-3 subindo em y
J6_POS = (-40.7, 4.04)


def mm(v):
    return v / MIL


def dumps(r):
    return json.dumps(r, ensure_ascii=False, separators=(',', ':'))


class Ids:
    def __init__(self, start):
        self.n = start

    def __call__(self):
        self.n += 1
        return f'e{self.n}'


def read_rows(path):
    txt = open(path, encoding='utf-8').read()
    return [json.loads(l) if l.strip() else None for l in txt.split('\n')]


def write_rows(path, rows):
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(dumps(r) for r in rows if r is not None))


def max_id(rows):
    return max(int(m) for m in re.findall(r'"e(\d+)"', '\n'.join(dumps(r) for r in rows if r)))


# --------------------------------------------------------------- esquemático
def editar_esquematico(sat, rush):
    rows = read_rows(sat)
    rrows = read_rows(rush)
    new = Ids(max_id(rows) + 1000)

    def geom(r):
        if r[0] == 'COMPONENT':
            return [(r[3], r[4])]
        if r[0] == 'WIRE':
            pts = [p for seg in r[2] for p in seg]
            return list(zip(pts[0::2], pts[1::2]))
        return None

    # bloco 3 (x 20..755, y 200..580): apagar o que não é LED2/R6/LED3/R9
    dele = set()
    for r in rows:
        if r and r[0] in ('COMPONENT', 'WIRE'):
            g = geom(r)
            if all(20 <= x <= 755 and 200 <= y <= 580 for x, y in g) and \
                    (all(x < 300 for x, _ in g) or all(x >= 470 for x, _ in g)):
                dele.add(r[1])
    attrs = defaultdict(dict)
    for r in rows:
        if r and r[0] == 'ATTR':
            attrs[r[2]][r[3]] = r[4]
    apagados = sorted(attrs[i].get('Designator') or attrs[i].get('NET') or i for i in dele)
    des_apag = {attrs[i].get('Designator') for i in dele} & DEL_DES
    assert des_apag == DEL_DES, (des_apag ^ DEL_DES)
    # rótulos das marcas junto do ATmega
    for r in rows:
        if r and r[0] == 'WIRE' and attrs[r[1]].get('NET') in ('MARK_R_A6', 'MARK_L2_D8', 'MARK_R2_D9'):
            dele.add(r[1])
    out = []
    for r in rows:
        if r is None:
            continue
        if r[0] in ('COMPONENT', 'WIRE') and r[1] in dele:
            continue
        if r[0] == 'ATTR' and r[2] in dele:
            continue
        if r[0] == 'ATTR' and r[3] == 'NET' and r[4] in RENAME:
            r[4] = RENAME[r[4]]
        if r[0] == 'ATTR' and r[3] == '@Project Name':
            r[4] = NOME
        if r[0] == 'ATTR' and r[3] == '@Update Date':
            r[4] = DATA
        if r[0] == 'TEXT' and r[5] == '3 - SENSORES DE MARCA':
            r[5] = '3 - LEDS DAS PONTAS E RECEPTOR IR'
        out.append(r)
    # sem ligação: U2 (e6) pinos 12 (e49), 13 (e53), 19 (e77)
    for pin, x, y in (('e49', 810, 915), ('e53', 810, 905), ('e77', 1150, 895)):
        out.append(['ATTR', new(), 'e6' + pin, 'NO_CONNECT', 'yes', 0, 0, x, y, 0, 'st5', 0])
    # J6 do Rush, levado para o bloco 3 (todos os ids renumerados)
    dx, dy = -200, -5
    j6ids = {'e3400', 'e3416', 'e3418', 'e3420'}
    ren = {i: new() for i in sorted(j6ids)}
    for r in rrows:
        if not r:
            continue
        r = copy.deepcopy(r)
        if r[0] == 'COMPONENT' and r[1] in j6ids:
            r[1] = ren[r[1]]; r[3] += dx; r[4] += dy
        elif r[0] == 'WIRE' and r[1] in j6ids:
            r[1] = ren[r[1]]
            r[2] = [[v + (dx if i % 2 == 0 else dy) for i, v in enumerate(seg)] for seg in r[2]]
        elif r[0] == 'ATTR' and r[2] in j6ids:
            r[1] = new(); r[2] = ren[r[2]]
            if r[3] == 'Unique ID':
                r[4] = 'gge78'
            if r[7] is not None:
                r[7] += dx; r[8] += dy
        elif r[0] == 'TEXT' and r[1] == 'e3422':
            r[1] = new(); r[2] = 330; r[3] = 395
        else:
            continue
        out.append(r)
    return out, apagados, ren['e3400']



# ----------------------------------------------------------------------- PCB
def pad_geoms(d, rows):
    """Polígonos (shapely) dos pads, por (comp, numero): lista de (camada, geom, rede)."""
    from shapely.geometry import box
    from shapely import affinity
    comp = {r[1]: r for r in rows if r and r[0] == 'COMPONENT'}
    fp = {r[3]: r[8] for r in rows if r and r[0] == 'ATTR' and r[7] == 'Footprint' and r[8]}
    pn = {(r[1], r[2]): r[3] for r in rows if r and r[0] == 'PAD_NET' and r[2]}
    res = []
    for cid, c in comp.items():
        if cid not in fp:
            continue
        L, cx, cy, rot = c[3], c[4], c[5], c[6]
        for l in open(f'{d}/FOOTPRINT/{fp[cid]}.efoo', encoding='utf-8'):
            p = json.loads(l)
            if p[0] != 'PAD':
                continue
            px, py, prot = p[6], p[7], p[8] or 0
            sh = p[10]
            if sh[0] in ('RECT', 'OVAL'):
                g = box(-sh[1] / 2, -sh[2] / 2, sh[1] / 2, sh[2] / 2)
                if sh[0] == 'OVAL':
                    m = min(sh[1], sh[2]) / 2
                    g = g.buffer(-m).buffer(m) if g.buffer(-m).area > 0 else Point(0, 0).buffer(m)
            elif sh[0] == 'ELLIPSE':
                g = Point(0, 0).buffer(sh[1] / 2)
            elif sh[0] == 'POLY':
                try:
                    from shapely.geometry import Polygon
                    g = Polygon(pathpts(sh[1]))
                except Exception:
                    g = Point(0, 0).buffer(20)
            else:
                g = Point(0, 0).buffer(20)
            g = affinity.rotate(g, prot, origin=(0, 0))
            g = affinity.translate(g, px, py)
            if L == 2:
                g = affinity.scale(g, 1, -1, origin=(0, 0))
            g = affinity.rotate(g, rot, origin=(0, 0))
            g = affinity.translate(g, cx, cy)
            layer = p[4]
            if layer in (1, 2) and L == 2:
                layer = 3 - layer
            layers = (1, 2) if layer == 12 else (layer,)
            res.append((cid, p[5], layers, g, pn.get((cid, p[5]))))
    return res


def copper(rows, pads):
    """lista de (id, camada, geom, rede) de trilhas, vias e pads."""
    items = []
    for r in rows:
        if not r:
            continue
        if r[0] == 'LINE' and r[4] in (1, 2):
            items.append((r[1], r[4], LineString([(r[5], r[6]), (r[7], r[8])]).buffer(r[9] / 2), r[3]))
        elif r[0] == 'VIA':
            g = Point(r[5], r[6]).buffer(r[8] / 2)
            items += [(r[1], 1, g, r[3]), (r[1], 2, g, r[3])]
    for cid, num, layers, g, net in pads:
        for L in layers:
            items.append((f'{cid}.{num}', L, g, net))
    return items


def drc(items, lim_mm=0.15):
    """pares de redes diferentes, mesma camada, com folga < lim."""
    from shapely.strtree import STRtree
    geoms = [it[2] for it in items]
    tree = STRtree(geoms)
    lim = mm(lim_mm)
    bad = set()
    for i, it in enumerate(items):
        for j in tree.query(it[2].buffer(lim)):
            j = int(j)
            if j <= i:
                continue
            jt = items[j]
            if jt[1] != it[1] or (it[3] and it[3] == jt[3]) or it[0] == jt[0]:
                continue
            if not it[3] and not jt[3]:
                continue
            dist = it[2].distance(jt[2])
            if dist < lim:
                bad.add((min(it[0], jt[0]), max(it[0], jt[0]), round(dist * MIL, 3)))
    return bad


def seg_ends(r):
    return (r[5], r[6]), (r[7], r[8])


def near(a, b, tol=1.0):
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


def achar_linha(rows, net, a, b, tol=2.0):
    """trilha da rede `net` com pontas a e b (mm)."""
    a, b = (mm(a[0]), mm(a[1])), (mm(b[0]), mm(b[1]))
    for r in rows:
        if r[0] == 'LINE' and r[3] == net:
            p, q = seg_ends(r)
            if (near(p, a, tol) and near(q, b, tol)) or (near(p, b, tol) and near(q, a, tol)):
                return r
    raise KeyError((net, a, b))


def achar_via(rows, net, a, tol=2.0):
    a = (mm(a[0]), mm(a[1]))
    for r in rows:
        if r[0] == 'VIA' and r[3] == net and near((r[5], r[6]), a, tol):
            return r
    raise KeyError((net, a))


def poda_a_partir_dos_cortes(rows, removidos, pads, pads_apagados=()):
    """Anda a partir de cada ponto de corte (ponta de trilha/via removida) e apaga
    as trilhas e vias que ficaram penduradas, até chegar a um pad, a uma junção
    (duas ou mais trilhas) ou a uma derivação em T. Casamento exato de pontas
    (1 mil), como o EasyEDA grava as trilhas."""
    padby = defaultdict(list)
    for cid, num, layers, g, net in pads:
        if net:
            padby[net].append((layers, g.buffer(1.0)))
    vivos = {id(r): r for r in rows if r[0] in ('LINE', 'VIA')}
    fila = []
    # pontas de trilha que terminavam em pads de componentes apagados
    for net, g in pads_apagados:
        if net in NO_PRUNE - {'GND'} or not net:
            continue
        gb = g.buffer(1.0)
        for r in vivos.values():
            if r[0] == 'LINE' and r[3] == net:
                fila += [(net, p) for p in seg_ends(r) if gb.contains(Point(p))]
    for r in removidos:
        if r[3] in NO_PRUNE - {'GND'} or not r[3]:
            continue
        if r[0] == 'LINE':
            fila += [(r[3], p) for p in seg_ends(r)]
        else:
            fila.append((r[3], (r[5], r[6])))
    podadas = []
    while fila:
        net, pt = fila.pop()
        P = Point(pt)
        if any(g.contains(P) for _, g in padby[net]):
            continue
        ends, vias, tee = [], [], False
        for r in vivos.values():
            if r[3] != net:
                continue
            if r[0] == 'VIA':
                if near((r[5], r[6]), pt):
                    vias.append(r)
                continue
            p, q = seg_ends(r)
            if near(p, pt) or near(q, pt):
                ends.append(r)
            elif LineString([p, q]).distance(P) <= 1.0:
                tee = True
        if tee or len(ends) >= 2:
            continue
        for v in vias:
            del vivos[id(v)]
            podadas.append((v[1], net, 'via', round(v[5] * MIL, 2), round(v[6] * MIL, 2)))
        if len(ends) == 1:
            r = ends[0]
            del vivos[id(r)]
            p, q = seg_ends(r)
            podadas.append((r[1], net, 'trilha', round(p[0] * MIL, 2), round(p[1] * MIL, 2),
                            round(q[0] * MIL, 2), round(q[1] * MIL, 2)))
            fila.append((net, q if near(p, pt) else p))
    return podadas


def ilhas(rows, pads):
    """Conectividade de cobre por rede (trilhas, vias e pads que se tocam)."""
    items = []
    for r in rows:
        if r[0] == 'LINE' and r[4] in (1, 2) and r[3]:
            items.append((r[1], {r[4]}, LineString(seg_ends(r)).buffer(r[9] / 2), r[3], None))
        elif r[0] == 'VIA' and r[3]:
            items.append((r[1], {1, 2}, Point(r[5], r[6]).buffer(r[8] / 2), r[3], None))
    for cid, num, layers, g, net in pads:
        if net:
            items.append((f'{cid}.{num}', set(layers), g, net, (cid, num)))
    pai = list(range(len(items)))

    def raiz(i):
        while pai[i] != i:
            pai[i] = pai[pai[i]]; i = pai[i]
        return i
    byn = defaultdict(list)
    for i, it in enumerate(items):
        byn[it[3]].append(i)
    for net, idx in byn.items():
        for a in range(len(idx)):
            for b in range(a + 1, len(idx)):
                i, j = idx[a], idx[b]
                if items[i][1] & items[j][1] and items[i][2].distance(items[j][2]) <= 0.5:
                    pai[raiz(i)] = raiz(j)
    res = {}
    for net, idx in byn.items():
        grupos = defaultdict(list)
        for i in idx:
            grupos[raiz(i)].append(items[i])
        res[net] = list(grupos.values())
    return res


def editar_pcb(d_sat, d_rush, sat_pcb, rush_pcb, j6_sch, fpdir):
    rows = [r for r in read_rows(sat_pcb) if r is not None]
    rrows = [r for r in read_rows(rush_pcb) if r is not None]
    new = Ids(max(max_id(rows), 9000) + 1000)
    base_pads = pad_geoms(d_sat, rows)
    base_drc = drc(copper(rows, base_pads))

    des = {r[3]: r[8] for r in rows if r[0] == 'ATTR' and r[7] == 'Designator' and r[8]}
    inv = {v: k for k, v in des.items()}
    del_comp = {inv[x] for x in DEL_DES}
    board = outline(rrows)[0]
    inner = board.buffer(-mm(0.3))
    log = defaultdict(list)
    removidos = []
    pads_apagados = [(net, g) for cid, num, ly, g, net in base_pads if cid in del_comp]

    out = []
    pos_contorno = None
    for r in rows:
        t = r[0]
        if t == 'COMPONENT' and r[1] in del_comp:
            log['componentes apagados'].append(des[r[1]]); continue
        if t in ('ATTR', 'PAD_NET') and (r[3] if t == 'ATTR' else r[1]) in del_comp:
            continue
        if t == 'NET' and r[1] in DEL_NETS:
            log['redes apagadas'].append(r[1]); continue
        if t == 'NET' and r[1] in RENAME:
            r[1] = RENAME[r[1]]
        if t == 'PAD_NET' and r[3] in RENAME:
            r[3] = RENAME[r[3]]
        if t in ('LINE', 'VIA'):
            if r[3] in DEL_NETS:
                log['trilhas/vias das redes apagadas'].append(r[1]); continue
            if r[3] in RENAME:
                r[3] = RENAME[r[3]]
            if t == 'LINE':
                g = LineString(seg_ends(r)).buffer(r[9] / 2)
            else:
                g = Point(r[5], r[6]).buffer(r[8] / 2)
            if not inner.contains(g):
                log['trilhas/vias fora do novo contorno'].append((r[1], r[3]))
                removidos.append(r); continue
        if t == 'POLY' and r[4] == 11:
            if pos_contorno is None:
                pos_contorno = len(out)
            continue
        if t == 'POURED':
            continue
        out.append(r)
    # contorno do Rush
    k = pos_contorno
    for r in rrows:
        if r[0] == 'POLY' and r[4] == 11:
            r = copy.deepcopy(r); r[1] = new()
            out.insert(k, r); k += 1

    def mover(cid, x, y):
        c = next(r for r in out if r[0] == 'COMPONENT' and r[1] == cid)
        dx, dy = mm(x) - c[4], mm(y) - c[5]
        c[4], c[5] = round(mm(x), 4), round(mm(y), 4)
        for r in out:
            if r[0] == 'ATTR' and r[3] == cid and r[5] is not None:
                r[5] = round(r[5] + dx, 4); r[6] = round(r[6] + dy, 4)

    # LEDs e resistores para as pontas
    for d, (x, y) in MOVE.items():
        mover(inv[d], x, y)
    for d, a in ROT.items():
        next(r for r in out if r[0] == 'COMPONENT' and r[1] == inv[d])[6] = a
    # J6 do Rush, na ponta esquerda
    jid = next(r[3] for r in rrows if r[0] == 'ATTR' and r[7] == 'Designator' and r[8] == 'J6')
    nj = new()
    k = max(i for i, r in enumerate(out) if r[0] in ('COMPONENT', 'ATTR', 'PAD_NET')) + 1
    add = []
    for r in rrows:
        if r[0] == 'COMPONENT' and r[1] == jid:
            r = copy.deepcopy(r); r[1] = nj; r[8] = 0
            r[7]['Unique ID'] = 'gge78'; r[7]['Channel ID'] = '$1' + j6_sch
        elif r[0] == 'ATTR' and r[3] == jid:
            r = copy.deepcopy(r); r[1] = new(); r[3] = nj
        elif r[0] == 'PAD_NET' and r[1] == jid:
            r = copy.deepcopy(r); r[1] = nj
        else:
            continue
        add.append(r)
    out[k:k] = add
    mover(nj, *J6_POS)
    j6 = {n: g.centroid.coords[0] for cid, n, _, g, _ in pad_geoms(fpdir, out) if cid == nj}
    assert abs(j6['1'][1] * MIL - (J6_POS[1] - 2.54)) < 0.01, j6

    # A5 -> J6.1: a diagonal do A5 termina em (-43,18; 1,5) e segue reta até o pino 1;
    # sai o desvio por baixo (vias em (-44,73; 3,15) e (-44,76; 5,07)) e a subida antiga.
    diag = achar_linha(out, 'IR_A5', (-33.27, -8.41), (-44.83, 3.15))
    xa, ya = mm(-43.18), j6['1'][1]
    p, q = seg_ends(diag)
    if near(p, (mm(-44.83), mm(3.15)), 2):
        diag[5], diag[6] = round(xa, 4), round(ya, 4)
    else:
        diag[7], diag[8] = round(xa, 4), round(ya, 4)
    tirar = [achar_via(out, 'IR_A5', (-44.73, 3.15)), achar_via(out, 'IR_A5', (-44.76, 5.07)),
             achar_linha(out, 'IR_A5', (-44.83, 3.15), (-44.76, 3.22)),
             achar_linha(out, 'IR_A5', (-44.76, 3.22), (-44.76, 5.07)),
             achar_linha(out, 'IR_A5', (-44.76, 5.07), (-44.76, 8.31)),
             # +5V: o trecho vertical em x = -40,51 passaria no pino 3 do J6
             achar_linha(out, '+5V', (-40.51, 6.73), (-40.51, 11.68))]
    for r in tirar:
        out.remove(r)
        log['trilhas/vias substituídas'].append((r[1], r[3]))
    removidos += tirar[-1:]
    # +5V: (-40,51; 11,68) -> x = -39,4 -> desce entre o J6 e a aba do U1 -> J6.2
    x5 = mm(-39.4)
    p2 = j6['2']
    novas = [
        ('IR_A5', 9.8425, [(xa, ya), j6['1']]),
        ('+5V', 19.685, [(mm(-40.51), mm(11.68)), (x5, mm(11.68) - (x5 - mm(-40.51))),
                         (x5, p2[1] + (x5 - p2[0])), p2]),
    ]
    novas = [n + (1,) for n in novas]
    # LEDs das pontas: LED (cima) -> via -> resistor (baixo); D2/D7 descem por baixo
    def pc(d, n):
        return next(g.centroid.coords[0] for cid, num, _, g, _ in pad_geoms(fpdir, out)
                    if cid == inv[d] and num == n)

    def via(net, x, y):
        return ['VIA', new(), 0, net, '', round(x, 4), round(y, 4), 11.811, 23.622, 0, None, None, 0, []]
    leda = achar_linha(out, 'LEDA_D2', (-34.04, -8.78), (-45.74, 2.92))
    pa = next(p for p in seg_ends(leda) if near(p, (mm(-45.74), mm(2.92)), 2))
    ledb = achar_linha(out, 'LEDB_D7', (36.78, -11.81), (49.47, 0.88))
    p0, p1 = seg_ends(ledb)
    fica, corta = (p0, p1) if near(p0, (mm(36.78), mm(-11.81)), 2) else (p1, p0)
    xb = -pa[0]                                   # espelho do lado esquerdo
    t = (xb - fica[0]) / (corta[0] - fica[0])
    pb = (xb, fica[1] + t * (corta[1] - fica[1]))
    if (ledb[5], ledb[6]) == corta:
        ledb[5], ledb[6] = round(pb[0], 4), round(pb[1], 4)
    else:
        ledb[7], ledb[8] = round(pb[0], 4), round(pb[1], 4)
    log['trilhas encurtadas'].append(('LEDB_D7', ledb[1], 'termina em', round(pb[0] * MIL, 2), round(pb[1] * MIL, 2)))
    novas_vias = []
    for led, res, mid, sig, ps in (('LED2', 'R6', '$1N2289', 'LEDA_D2', pa), ('LED3', 'R9', '$1N2298', 'LEDB_D7', pb)):
        l2, r2, r1 = pc(led, '2'), pc(res, '2'), pc(res, '1')
        vx, vy = (l2[0] + r2[0]) / 2, l2[1]
        novas_vias += [via(mid, vx, vy), via(sig, ps[0], ps[1])]
        yk = r1[1] - abs(r1[0] - ps[0])
        novas += [(mid, 9.8425, [l2, (vx, vy)], 1), (mid, 9.8425, [(vx, vy), r2], 2),
                  (sig, 9.8425, [ps, (ps[0], yk), r1], 2)]
    k = next(i for i, r in enumerate(out) if r[0] == 'VIA')
    out[k:k] = novas_vias
    for v in novas_vias:
        log['vias novas'].append((v[3], round(v[5] * MIL, 2), round(v[6] * MIL, 2)))
    k = next(i for i, r in enumerate(out) if r[0] == 'LINE')
    for net, w, pts, cam in novas:
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            r = ['LINE', new(), 0, net, cam, round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4), w, 0]
            out.insert(k, r); k += 1
            log['trilhas novas'].append((net, 'cima' if cam == 1 else 'baixo', round(x0 * MIL, 2), round(y0 * MIL, 2),
                                         round(x1 * MIL, 2), round(y1 * MIL, 2)))
    # poda das trilhas que ficaram penduradas
    pads = pad_geoms(fpdir, out)
    podadas = poda_a_partir_dos_cortes(out, removidos, pads, pads_apagados)
    kill = {p[0] for p in podadas}
    out = [r for r in out if not (r[0] in ('LINE', 'VIA') and r[1] in kill)]
    log['podadas (penduradas depois do corte)'] = podadas
    # ilhas de cobre sem nenhum pad (menos GND, que liga pelos pours)
    pads = pad_geoms(fpdir, out)
    soltas = []
    for net, grupos in ilhas(out, pads).items():
        if net == 'GND':
            continue
        for g in grupos:
            if not any(it[4] for it in g):
                soltas += [(it[0], net) for it in g]
    kill = {x[0] for x in soltas}
    out = [r for r in out if not (r[0] in ('LINE', 'VIA') and r[1] in kill)]
    log['ilhas sem pad apagadas'] = soltas
    # conferências
    pads = pad_geoms(fpdir, out)
    novo_drc = drc(copper(out, pads))
    base_keys = {(a, b) for a, b, _ in base_drc}
    log['folga < 0,15 mm (novos)'] = sorted(x for x in novo_drc if (x[0], x[1]) not in base_keys)
    log['folga < 0,15 mm (já no Saturn)'] = sorted(base_drc)
    return out, log, pads


# ------------------------------------------------------------------ projeto
def main():
    tmp = tempfile.mkdtemp()
    ds, dr = f'{tmp}/sat', f'{tmp}/rush'
    zipfile.ZipFile(SATURN).extractall(ds)
    zipfile.ZipFile(RUSH).extractall(dr)
    pj = json.load(open(f'{ds}/project.json', encoding='utf-8'))
    pr = json.load(open(f'{dr}/project.json', encoding='utf-8'))
    sch = [f'{ds}/SHEET/{s}/{x}' for s in os.listdir(f'{ds}/SHEET') for x in os.listdir(f'{ds}/SHEET/{s}')][0]
    rsch = [f'{dr}/SHEET/{s}/{x}' for s in os.listdir(f'{dr}/SHEET') for x in os.listdir(f'{dr}/SHEET/{s}')][0]
    pcb = f'{ds}/PCB/' + os.listdir(f'{ds}/PCB')[0]
    rpcb = f'{dr}/PCB/' + os.listdir(f'{dr}/PCB')[0]

    # biblioteca: J6 (device, símbolo, footprint) do Rush
    dev = 'c1e5a3b27d4f6e81'
    sym = pr['devices'][dev]['attributes']['Symbol']
    fp = pr['devices'][dev]['attributes']['Footprint']
    pj['devices'][dev] = pr['devices'][dev]
    pj['symbols'][sym] = pr['symbols'][sym]
    pj['footprints'][fp] = pr['footprints'][fp]
    shutil.copy(f'{dr}/SYMBOL/{sym}.esym', f'{ds}/SYMBOL/')
    shutil.copy(f'{dr}/FOOTPRINT/{fp}.efoo', f'{ds}/FOOTPRINT/')
    pj['config']['title'] = NOME
    with open(f'{ds}/project.json', 'w', encoding='utf-8') as f:
        json.dump(pj, f, ensure_ascii=False, separators=(',', ':'))

    rows, apagados, j6_sch = editar_esquematico(sch, rsch)
    write_rows(sch, rows)
    prow, log, pads = editar_pcb(ds, dr, pcb, rpcb, j6_sch, ds)
    write_rows(pcb, prow)

    # conectividade: cada rede deve ser uma ilha só (menos as sem rota de propósito)
    des = {r[3]: r[8] for r in prow if r[0] == 'ATTR' and r[7] == 'Designator' and r[8]}
    conect = []
    for net, grupos in sorted(ilhas(prow, pads).items()):
        com_pad = [g for g in grupos if any(it[4] for it in g)]
        sem_pad = [g for g in grupos if not any(it[4] for it in g)]
        if len(com_pad) > 1 or sem_pad:
            desc = [sorted(f"{des.get(it[4][0], it[4][0])}.{it[4][1]}" for it in g if it[4]) for g in com_pad]
            conect.append((net, len(com_pad), desc, len(sem_pad)))
    log['redes com mais de uma ilha ou cobre solto'] = conect

    # empacotar na mesma estrutura do .epro original
    names = zipfile.ZipFile(SATURN).namelist()
    extra = [f'SYMBOL/{sym}.esym', f'FOOTPRINT/{fp}.efoo']
    with zipfile.ZipFile(SAIDA, 'w', zipfile.ZIP_DEFLATED) as z:
        for n in names + [e for e in extra if e not in names]:
            p = f'{ds}/{n}'
            if n.endswith('/'):
                z.writestr(zipfile.ZipInfo(n), '')
            else:
                z.write(p, n)
    shutil.rmtree(tmp)

    print('Gerado:', os.path.relpath(SAIDA))
    print('Esquemático, apagados:', ', '.join(x for x in apagados if x and not x.startswith('#')))
    for k, v in log.items():
        print(f'PCB, {k}: {len(v)}')
        if k not in ('trilhas/vias das redes apagadas', 'trilhas/vias fora do novo contorno', 'folga < 0,15 mm (já no Saturn)'):
            for x in v:
                print('   ', x)


if __name__ == '__main__':
    main()
