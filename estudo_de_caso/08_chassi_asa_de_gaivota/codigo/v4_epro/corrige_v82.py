"""Ajustes finais no arquivo v8.2 do Erick (14/11/2026).

- J3 (gravação): a via de +5V em (2,93; −24,14) fechava o GND do pad e77:2; volta para (3,31; −24,06).
- R3: pad de GND ilhado na face de cima → via de GND ao lado, com trilha curta.
- Rótulos dos QRE de novo dentro da placa.
Uso: python3 corrige_v82.py <entrada.epro> <saida.epro>
Baseado no EVA-RT, (c) EXOTIC TEAM MX, AGPL-3.0.
"""
import sys, os, json, math, zipfile, re
import numpy as np
from shapely.geometry import Point, LineString
from shapely.ops import unary_union
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check, verifica_placa as V, plano_gnd as G
M = 0.0254
mil = lambda v: v / M
SRC, DST = sys.argv[1], sys.argv[2]
z = zipfile.ZipFile(SRC)
PCBN = [n for n in z.namelist() if n.endswith('.epcb')][0]
rows = [json.loads(l) for l in z.read(PCBN).decode('utf-8-sig').splitlines() if l.strip()]
fps = {n.split('/')[1][:-5]: [json.loads(l) for l in z.read(n).decode('utf-8-sig').splitlines() if l.strip()]
       for n in z.namelist() if n.endswith('.efoo')}
outer = V.board(SRC)[2]
n_id = max(int(r[1][1:]) for r in rows if len(r) > 1 and isinstance(r[1], str) and re.fullmatch(r'e\d+', r[1]))
def nid():
    global n_id
    n_id += 1; return f'e{n_id}'
def line(net, L, pts, w):
    for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):
        if math.hypot(x2 - x1, y2 - y1) < 1e-4: continue
        rows.append(['LINE', nid(), 0, net, L, round(mil(x1), 4), round(mil(y1), 4), round(mil(x2), 4), round(mil(y2), 4), round(mil(w), 4), 0])
def via(net, x, y, d, h):
    rows.append(['VIA', nid(), 0, net, '', round(mil(x), 4), round(mil(y), 4), round(mil(h), 4), round(mil(d), 4), 0, None, None, 0, []])
def ends(r): return ((round(r[5] * M, 2), round(r[6] * M, 2)), (round(r[7] * M, 2), round(r[8] * M, 2)))
def find_line(net, L, a, b):
    for r in rows:
        if r[0] == 'LINE' and r[3] == net and r[4] == L and set(ends(r)) == {a, b}: return r
    raise KeyError((net, L, a, b))
def free(g, net, layers=(1, 2), clr=0.2):
    cu = check.copper(rows, fps)
    return all(not any(gg.intersects(g.buffer(clr)) for l, n, gg, i in cu if l == L and n != net) for L in layers)
log = []

# 1) +5V perto do pino do ATmega: via de (2,93; −24,14) para (3,31; −24,06), como no v8.1
vr = next(r for r in rows if r[0] == 'VIA' and r[3] == '+5V' and abs(r[5] * M - 2.93) < 0.02 and abs(r[6] * M + 24.14) < 0.02)
old = [find_line('+5V', 1, (2.93, -24.14), (3.03, -24.04)), find_line('+5V', 2, (2.93, -24.14), (3.56, -24.77)),
       find_line('+5V', 2, (3.56, -25.39), (3.56, -24.77))]
rows[:] = [r for r in rows if not any(r is o for o in old)]
NV = (3.31, -24.06)
vr[5], vr[6] = round(mil(NV[0]), 4), round(mil(NV[1]), 4)
line('+5V', 2, [NV, (3.56, -24.31), (3.56, -25.39)], 0.5)
assert free(Point(NV).buffer(0.3), '+5V'), 'via +5V sem folga'
assert free(LineString([NV, (3.56, -24.31), (3.56, -25.39)]).buffer(0.25), '+5V', layers=(2,)), 'trilha +5V sem folga'
log.append('+5V: via de (2,93; −24,14) para (3,31; −24,06); trecho de baixo refeito (abre o GND do J3)')

# 2) R3: via de GND ao lado do pad −, ligada por trilha curta (o pad ficou ilhado na face de cima)
comp = {r[1]: r for r in rows if r[0] == 'COMPONENT'}
des = {r[3]: r[8] for r in rows if r[0] == 'ATTR' and r[3] in comp and r[7] == 'Designator'}
def gnd_pad_via(d, rmax=2.2):
    cid = next(c for c, n in des.items() if n == d)
    gp = next(g for l, n, g, i in check.pad_geoms(rows, fps) if i.startswith(cid + ':') and n == 'GND')
    L = next(l for l, n, g, i in check.pad_geoms(rows, fps) if i.startswith(cid + ':') and n == 'GND')
    pads = unary_union([g for l, n, g, i in check.pad_geoms(rows, fps)])
    c = gp.centroid; best = None
    for ang in range(0, 360, 45):
        for rr in np.arange(0.6, rmax, 0.05):
            p = (c.x + rr * math.cos(math.radians(ang)), c.y + rr * math.sin(math.radians(ang)))
            v = Point(p).buffer(0.3)
            if Point(p).distance(pads) < 0.15 + 0.15: continue
            tr = LineString([(c.x, c.y), p])
            if not free(v, 'GND') or not free(tr.buffer(0.15), 'GND', layers=(L,)): continue
            best = (rr, p); break
        if best: break
    assert best, f'{d}: sem lugar para via'
    p = best[1]
    via('GND', p[0], p[1], 0.6, 0.3); line('GND', L, [(c.x, c.y), p], 0.3)
    log.append(f'{d}: via de GND 0,6/0,3 em ({p[0]:.2f}; {p[1]:.2f}) com trilha de 0,3 mm até o pad')
cu, pcs, f, main = G.pieces(rows, fps, outer)
lost = [i for l, nn, g, i in cu if nn == 'GND' and not any(f(k) == main for k, (Lp, p) in enumerate(pcs) if Lp == l and p.intersects(g))]
for i in lost:
    c = i.split(':')[0]
    if ':' in i and des.get(c) not in (None, 'J3'): gnd_pad_via(des[c])

# 3) rótulos dos QRE
LBL = {'S1': (-83.0, 13.75), 'S2': (-55.0, 15.6), 'S3': (55.0, 15.6), 'S4': (83.0, 13.75)}
for a in rows:
    if a[0] == 'ATTR' and a[7] == 'Designator' and a[8] in LBL:
        a[5], a[6] = round(mil(LBL[a[8]][0]), 4), round(mil(LBL[a[8]][1]), 4)
log.append('rótulos S1–S4 dentro da placa')

cu, pcs, f, main = G.pieces(rows, fps, outer)
log.append('GND fora do plano (simulado): ' + str([i for l, nn, g, i in cu if nn == 'GND' and not any(f(k) == main for k, (Lp, p) in enumerate(pcs) if Lp == l and p.intersects(g))]))
rows[:] = [r for r in rows if r[0] != 'POURED']
with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zo:
    for info in z.infolist():
        if info.is_dir(): zo.writestr(info, b''); continue
        data = z.read(info.filename)
        if info.filename == PCBN:
            data = ''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n' for r in rows).encode('utf-8')
        zo.writestr(info, data)
print('\n'.join(log)); print('arquivo:', DST)
