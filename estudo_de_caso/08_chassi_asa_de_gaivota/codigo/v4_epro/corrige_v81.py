"""Ajustes no arquivo v8.1 do Erick (14/11/2026).

- Alinhamentos: C5 com C1 (x), C4/C3 com C5 (y e espaçamento), C2 com C1 (y), R17 com C2 (x);
  LED1 e R1 sobem 0,2 mm junto com C3/C4/C5 (estavam travados e não tinham se movido).
- Trilhas presas aos pads movidos voltam ao centro dos pads, em 0/45/90°.
- C3: trilha de VBAT afastada do pad de GND (folga de 0,05 mm).
- C2: volta a via de VBAT (passagem de face) que tinha sido apagada.
- QRE renomeados: asa esquerda S1 (externo) / S2 (interno); asa direita S3 (interno) / S4 (externo).
- GND: vias de costura onde o cobre ficaria ilhado.

Uso: python3 corrige_v81.py <entrada.epro> <saida.epro>
Baseado no EVA-RT, (c) EXOTIC TEAM MX, AGPL-3.0.
"""
import sys, os, json, math, zipfile, re, collections
from shapely.geometry import Point, LineString
from shapely.ops import unary_union, nearest_points
from shapely.strtree import STRtree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check, verifica_placa as V, plano_gnd as G, angulos
M = 0.0254
mil = lambda v: v / M
SRC, DST = sys.argv[1], sys.argv[2]
z = zipfile.ZipFile(SRC)
PCBN = [n for n in z.namelist() if n.endswith('.epcb')][0]
rows = [json.loads(l) for l in z.read(PCBN).decode('utf-8-sig').splitlines() if l.strip()]
fps = {n.split('/')[1][:-5]: [json.loads(l) for l in z.read(n).decode('utf-8-sig').splitlines() if l.strip()]
       for n in z.namelist() if n.endswith('.efoo')}
outer = V.board(SRC)[2]
inner = outer.buffer(-0.3)
n_id = max(int(r[1][1:]) for r in rows if len(r) > 1 and isinstance(r[1], str) and re.fullmatch(r'e\d+', r[1]))
def nid():
    global n_id
    n_id += 1; return f'e{n_id}'
comp = {r[1]: r for r in rows if r[0] == 'COMPONENT'}
des = {r[3]: r[8] for r in rows if r[0] == 'ATTR' and r[3] in comp and r[7] == 'Designator'}
inv = {v: k for k, v in des.items()}
byid = {r[1]: r for r in rows if len(r) > 1 and isinstance(r[1], str)}
log = []
P = lambda r, e: ((r[5] * M, r[6] * M) if e == 0 else (r[7] * M, r[8] * M))
def setp(r, e, p):
    if e == 0: r[5], r[6] = round(mil(p[0]), 4), round(mil(p[1]), 4)
    else: r[7], r[8] = round(mil(p[0]), 4), round(mil(p[1]), 4)
def line(net, L, pts, w):
    for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):
        if math.hypot(x2 - x1, y2 - y1) < 1e-4: continue
        rows.append(['LINE', nid(), 0, net, L, round(mil(x1), 4), round(mil(y1), 4), round(mil(x2), 4), round(mil(y2), 4), round(mil(w), 4), 0])
def via(net, x, y, d, h):
    rows.append(['VIA', nid(), 0, net, '', round(mil(x), 4), round(mil(y), 4), round(mil(h), 4), round(mil(d), 4), 0, None, None, 0, []])
def drop(*ids):
    rows[:] = [r for r in rows if not (len(r) > 1 and r[1] in ids)]
def pos(d):
    r = comp[inv[d]]; return r[4] * M, r[5] * M
def move(d, x=None, y=None):
    """Move o componente (e seus rótulos). Não arrasta trilhas: elas são refeitas abaixo."""
    r = comp[inv[d]]; x0, y0 = r[4] * M, r[5] * M
    x = x0 if x is None else x; y = y0 if y is None else y
    dx, dy = x - x0, y - y0
    r[4], r[5] = round(mil(x), 4), round(mil(y), 4)
    for a in rows:
        if a[0] == 'ATTR' and a[3] == r[1] and a[5] is not None:
            a[5], a[6] = round(a[5] + mil(dx), 4), round(a[6] + mil(dy), 4)
    log.append(f'{d}: ({x0:.3f}; {y0:.3f}) → ({x:.3f}; {y:.3f})')
    return dx, dy
def padc(d, num):
    g = next(g for l, n, g, i in check.pad_geoms(rows, fps) if i == f'{inv[d]}:{num}')
    return g.centroid.x, g.centroid.y
def mvvia(vid, dx, dy):
    r = byid[vid]; r[5], r[6] = round(r[5] + mil(dx), 4), round(r[6] + mil(dy), 4)
    log.append(f'via {vid} ({r[3]}) deslocada ({dx:+.3f}; {dy:+.3f})')
def mvline(lid, dx, dy):
    r = byid[lid]
    for e in (0, 1): setp(r, e, (P(r, e)[0] + dx, P(r, e)[1] + dy))

# ---------------- 1) alinhamentos ----------------
# C3/C4/C5 voltam ao x original (as trilhas de cima já estão alinhadas a ele), mantendo a subida de 0,2 mm.
Y_ROW = pos('C5')[1]
move('C5', x=-21.718); move('C4', x=-24.895); move('C3', x=-18.542)
# C1 sob o C5 (mesmo x); C2 e C1 na mesma altura (a do C2, que estava bem posicionado)
y_c2 = pos('C2')[1]
dx1, dy1 = move('C1', x=-21.718, y=y_c2)
# via de GND junto ao pad − do C1 fica no lugar; trilha curta até o pad (o C1 andou 0,14 mm)
gv = next(r for r in rows if r[0] == 'VIA' and r[3] == 'GND' and abs(r[5] * M + 22.85) < 0.3 and abs(r[6] * M + 1.06) < 0.3)
line('GND', 1, [(gv[5] * M, gv[6] * M), (padc('C1', 2)[0] - 0.3, gv[6] * M)], 0.5)                                   # via de GND colada ao pad − do C1
# R17 NÃO é centrado com o C2: em x = 19,81 o pad de GND encosta na trilha PWMC_D10 (folga 0) e na via e1240.
# LED1 e R1 sobem junto (estavam travados)
dy_up = Y_ROW - 8.0
move('LED1', y=pos('LED1')[1] + dy_up); move('R1', y=pos('R1')[1] + dy_up)

# ---------------- 2) trilhas presas aos pads movidos ----------------
# C4 +5V: vertical e383 começa no centro do pad
c = padc('C4', 1); setp(byid['e383'], 0, c)
# C5 +5V: vertical e386 começa no centro do pad
c = padc('C5', 2); setp(byid['e386'], 0, c)
# C5 GND → via e1226 (−23,718; 6,325): 45° e horizontal
c = padc('C5', 1); yv = byid['e921'][6] * M
k = (c[0] - (c[1] - yv), yv)
setp(byid['e920'], 0, c); setp(byid['e920'], 1, k); setp(byid['e921'], 0, k)
# C3 VBAT: horizontal no centro do pad e 45° até o topo da vertical e1739, afastada do pad de GND
c = padc('C3', 1); top = P(byid['e1739'], 0)
d = c[1] - top[1]
drop('e653', 'e654')
line('VBAT', 1, [c, (top[0] - d, c[1]), top], 1.5)
log.append('C3: trilha de VBAT refeita a partir do centro do pad (folga ao pad de GND)')
# LED1/R1: rede $1N2302 inteira sobe junto; via de GND do LED1 e suas trilhas também
net_led = byid['e508'][3]
for r in rows:
    if r[0] == 'LINE' and r[3] == net_led: mvline(r[1], 0, dy_up)
for lid in ('e919', 'e918'): mvline(lid, 0, dy_up)
mvvia('e1235', 0, dy_up)
# R1 +5V: o pad continua sobre a vertical e373/e387 (x igual) — junção move junto
for lid, e in (('e373', 0), ('e387', 1)):
    p = P(byid[lid], e); setp(byid[lid], e, (p[0], p[1] + dy_up))
# R17 (posição do Erick): trilhas de GND e do gate saem do centro dos pads, em 45°
cg = padc('R17', 2); vv = byid['e1240']; vx, vy = vv[5] * M, vv[6] * M
dyg = cg[1] - vy
drop('e1744', 'e1745')
line('GND', 1, [cg, (vx + dyg, cg[1]), (vx, vy)], 0.3)
cgt = padc('R17', 1); net_g = byid['e526'][3]
tgt = (21.503, 8.57)
diag = [r[1] for r in rows if r[0] == 'LINE' and r[3] == net_g and
        {(round(P(r, 0)[0], 2), round(P(r, 0)[1], 2)), (round(P(r, 1)[0], 2), round(P(r, 1)[1], 2))} == {(21.33, 8.39), (21.5, 8.57)}]
drop('e526', *diag)
dxg = tgt[0] - cgt[0]
line(net_g, 1, [cgt, (cgt[0], tgt[1] - dxg), tgt], 0.25)
log.append('R17: trilhas de GND e do gate refeitas a partir do centro dos pads')

# ---------------- 3) C2: via de VBAT (passagem de face) ----------------
b0 = P(byid['e1737'], 1)                        # (19,812; 3,937), fim da trilha larga de baixo
VIAC = (21.35, b0[1] - (21.35 - b0[0]))
line('VBAT', 2, [b0, VIAC], 1.5)
via('VBAT', VIAC[0], VIAC[1], 1.6, 1.0)
log.append(f'C2: via VBAT 1,6/1,0 em ({VIAC[0]:.2f}; {VIAC[1]:.2f}) sobre a trilha de cima e1742, com trecho de 1,5 mm na face de baixo')

# ---------------- 4) QRE: nomes e rótulos ----------------
REN = {'S1': 'S1', 'S3': 'S2', 'S4': 'S3', 'S2': 'S4'}       # nome antigo → novo (esq. ext., esq. int., dir. int., dir. ext.)
LBL = {'S1': (-83.0, 13.75), 'S2': (-55.0, 15.6), 'S3': (55.0, 15.6), 'S4': (83.0, 13.75)}
old_ids = {o: inv[o] for o in REN}
for o, nw in REN.items():
    cid = old_ids[o]
    for a in rows:
        if a[0] == 'ATTR' and a[3] == cid and a[7] == 'Designator':
            a[8] = nw; a[5], a[6] = round(mil(LBL[nw][0]), 4), round(mil(LBL[nw][1]), 4)
log.append('QRE renomeados: ' + ', '.join(f'{o}→{n}' for o, n in REN.items()))

# ---------------- 5) GND: costura das ilhas ----------------
def free_pt(p, r, layers=(1, 2), clr=0.2):
    cu = check.copper(rows, fps)
    g = Point(p).buffer(r)
    return all(not any(gg.intersects(g.buffer(clr)) for l, n, gg, i in cu if l == L and n != 'GND') for L in layers)
added = []
for _ in range(40):
    cu, pcs, f, main = G.pieces(rows, fps, outer)
    lost = [(l, i, g) for l, nn, g, i in cu if nn == 'GND' and not any(f(k) == main for k, (L, p) in enumerate(pcs) if L == l and p.intersects(g))]
    isl = sorted([(p.area, L, p) for k, (L, p) in enumerate(pcs) if f(k) != main and p.area >= 2.0], key=lambda t: -t[0])
    if not lost and not isl: break
    pads = unary_union([g for l, n, g, i in check.pad_geoms(rows, fps)])
    hs = unary_union(check.holes(rows))
    vias = unary_union([Point(r[5] * M, r[6] * M).buffer(r[8] * M / 2) for r in rows if r[0] == 'VIA'])
    placed = False
    for a, L, p in isl:
        mainp = unary_union([q for k, (LL, q) in enumerate(pcs) if LL == 3 - L and f(k) == main])
        cand = p.buffer(-0.16).intersection(mainp.buffer(-0.16)).difference(pads.buffer(0.5)).difference(hs.buffer(0.7)) \
                .difference(vias.buffer(0.6)).intersection(outer.buffer(-0.7))
        if cand.is_empty: continue
        q = nearest_points(cand, p.representative_point())[0]
        if not free_pt((q.x, q.y), 0.3): continue
        via('GND', q.x, q.y, 0.6, 0.3); added.append((L, round(a, 1), round(q.x, 2), round(q.y, 2))); placed = True; break
    if not placed: break
log.append(f'vias de costura de GND: {added}')
cu, pcs, f, main = G.pieces(rows, fps, outer)
log.append('GND fora do plano (simulado): ' + str([i for l, nn, g, i in cu if nn == 'GND' and not any(f(k) == main for k, (L, p) in enumerate(pcs) if L == l and p.intersects(g))]))

# nada travado: componentes, trilhas, vias e rótulos
nlock = 0
for r in rows:
    k = {'COMPONENT': 8, 'LINE': 10, 'VIA': 12, 'ATTR': 20}.get(r[0])
    if k is not None and r[k] == 1: r[k] = 0; nlock += 1
log.append(f'objetos destravados: {nlock}')

# cobre antigo: refazer no EasyEDA
rows[:] = [r for r in rows if r[0] != 'POURED']

with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zo:
    for info in z.infolist():
        if info.is_dir(): zo.writestr(info, b''); continue
        data = z.read(info.filename)
        if info.filename == PCBN:
            data = ''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n' for r in rows).encode('utf-8')
        elif info.filename.endswith('.esch'):
            L = [json.loads(l) for l in data.decode('utf-8-sig').splitlines() if l.strip()]
            uid = {}
            for a in L:
                if a[0] == 'ATTR' and a[3] == 'Unique ID': uid[a[2]] = a[4]
            pcb_uid = {o: comp[old_ids[o]][7].get('Unique ID') for o in REN}
            for a in L:
                if a[0] == 'ATTR' and a[3] == 'Designator':
                    for o, nw in REN.items():
                        if uid.get(a[2]) == pcb_uid[o]: a[4] = nw
            data = ''.join(json.dumps(a, ensure_ascii=False, separators=(',', ':')) + '\n' for a in L).encode('utf-8')
        zo.writestr(info, data)
print('\n'.join(log)); print('arquivo:', DST)
