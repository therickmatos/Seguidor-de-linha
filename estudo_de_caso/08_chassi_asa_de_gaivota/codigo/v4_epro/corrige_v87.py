"""v8.7 (14/11/2026): correções sobre o v8.6 do Erick + trilhas de potência para 5,5 A contínuos.

1. VBAT esquerdo: trilha de cima de 1,6 mm da via (−19,56; 1,14) até a trilha de y ≈ 3,3 (C1, C3 e 78M05 sem bateria).
2. LEDC_D13: trilha de cima prolongada até a via em (13,07; 3,30).
3. R10: em pé em (−13,033; −18,829), como no v8.5 (o pé da carcaça ficava a 0,14 mm).
4. Trilhas de potência alargadas no mesmo traçado, até onde a folga de 0,25 mm deixa
   (rodadas de +0,1 mm em todas ao mesmo tempo, folga 0,2 mm da regra; alvo pela IPC-2221, cobre 1 oz externo, ΔT 20 °C): saídas dos motores 2,5 mm (≥ 2,1 mm = 5,5 A),
   VBAT 3,0 mm (U4 + ventoinha), OUT_C 2,0 mm.
5. Vias de VBAT em paralelo na troca de face do lado direito (U4 + ventoinha).
6. J1 (XT30): trilhas curtas de GND de 2 mm saindo do pad nas duas faces, ligando o plano direto ao pad (sem depender dos raios térmicos).
Uso: python3 corrige_v87.py <entrada.epro> <saida.epro>
Baseado no EVA-RT, (c) EXOTIC TEAM MX, AGPL-3.0.
"""
import sys, os, json, zipfile, re, math
import numpy as np
from shapely.geometry import Point, LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check, verifica_placa as V
M = 0.0254
mil = lambda v: v / M
SRC, DST = sys.argv[1], sys.argv[2]
z = zipfile.ZipFile(SRC)
PCBN = [n for n in z.namelist() if n.endswith('.epcb')][0]
load = lambda n: [json.loads(l) for l in z.read(n).decode('utf-8-sig').splitlines() if l.strip()]
rows = load(PCBN)
fps = {n.split('/')[1][:-5]: load(n) for n in z.namelist() if n.endswith('.efoo')}
outer = V.board(SRC)[2]
n_id = max(int(r[1][1:]) for r in rows if len(r) > 1 and isinstance(r[1], str) and re.fullmatch(r'e\d+', r[1]))
def nid():
    global n_id
    n_id += 1; return f'e{n_id}'
def line(net, L, pts, w):
    for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):
        rows.append(['LINE', nid(), 0, net, L, round(mil(x1), 4), round(mil(y1), 4), round(mil(x2), 4), round(mil(y2), 4), round(mil(w), 4), 0])
def via(net, x, y, d, h):
    rows.append(['VIA', nid(), 0, net, '', round(mil(x), 4), round(mil(y), 4), round(mil(h), 4), round(mil(d), 4), 0, None, None, 0, []])
P = lambda r, k: (round(r[k] * M, 3), round(r[k + 1] * M, 3))
comp = {r[1]: r for r in rows if r[0] == 'COMPONENT'}
des = {r[3]: r[8] for r in rows if r[0] == 'ATTR' and r[3] in comp and r[7] == 'Designator'}
inv = {v: k for k, v in des.items()}
CLR = 0.25
def free(g, net, layers=(1, 2), clr=CLR):
    cu = check.copper(rows, fps)
    return all(not any(gg.intersects(g.buffer(clr)) for l, n, gg, i in cu if l == L and n != net) for L in layers)
log = []

# 1) VBAT esquerdo
tr = LineString([(-19.56, 1.14), (-19.56, 3.31)])
assert any(r[0] == 'VIA' and r[3] == 'VBAT' and P(r, 5) == (-19.558, 1.143) or (r[0] == 'VIA' and r[3] == 'VBAT' and abs(r[5] * M + 19.56) < 0.02 and abs(r[6] * M - 1.14) < 0.02) for r in rows)
assert free(tr.buffer(0.8), 'VBAT', layers=(1,))
line('VBAT', 1, [(-19.56, 1.14), (-19.56, 3.31)], 1.6)
log.append('VBAT: trilha de cima de 1,6 mm da via (−19,56; 1,14) até y = 3,31 (C1, C3 e 78M05 voltam a ter bateria)')

# 2) LEDC_D13
r = next(r for r in rows if r[0] == 'LINE' and r[3] == 'LEDC_D13' and r[4] == 1 and (abs(r[5] * M - 13.07) < 0.02 and abs(r[6] * M - 4.08) < 0.05 or abs(r[7] * M - 13.07) < 0.02 and abs(r[8] * M - 4.08) < 0.05))
lv = next(q for q in rows if q[0] == 'VIA' and q[3] == 'LEDC_D13' and abs(q[6] * M - 3.30) < 0.05)
k = 5 if abs(r[6] * M - 4.08) < 0.05 and abs(r[5] * M - 13.07) < 0.02 else 7
x0, y0 = r[k] * M, r[k + 1] * M
line('LEDC_D13', 1, [(x0, y0), (lv[5] * M, lv[6] * M)], round(r[9] * M, 3))
log.append(f'LEDC_D13: trilha de cima de ({x0:.2f}; {y0:.2f}) até a via ({lv[5] * M:.2f}; {lv[6] * M:.2f})')

# 3) R10 em pé
def move(d, dx, dy, rot=None):
    cid = inv[d]
    for q in rows:
        if q[0] == 'COMPONENT' and q[1] == cid:
            q[4] = round(q[4] + mil(dx), 4); q[5] = round(q[5] + mil(dy), 4)
            if rot is not None: q[6] = rot
        if q[0] == 'ATTR' and q[3] == cid and q[5] is not None: q[5] = round(q[5] + mil(dx), 4); q[6] = round(q[6] + mil(dy), 4)
r10 = comp[inv['R10']]
move('R10', -13.033 - r10[4] * M, -18.829 - r10[5] * M, rot=90)
rows[:] = [q for q in rows if not (q[0] == 'LINE' and q[3] == 'RESET' and {P(q, 5), P(q, 7)} == {(-13.171, -18.75), (-13.217, -18.796)})]
p2 = next(g for l, n, g, i in check.pad_geoms(rows, fps) if i.startswith(inv['R10'] + ':') and n == 'RESET').centroid
line('RESET', 1, [(round(p2.x, 3), round(p2.y, 3)), (round(p2.x + (p2.y + 18.75), 3), -18.75)], 0.25)
log.append('R10: em pé em (−13,033; −18,829), RESET em 45° até a trilha de y = −18,75')

# 4a0) MARK_L_A5: o trecho vertical em x = −31,73 vai 0,25 mm para a esquerda (as diagonais seguem nas mesmas retas),
#      abrindo espaço para a OUT_A2; fica a 0,23 mm da LEDA_D2
def seg_by(net, a, b):
    return next(q for q in rows if q[0] == 'LINE' and q[3] == net and q[4] == 1 and {P(q, 5), P(q, 7)} == {a, b})
v = seg_by('MARK_L_A5', (-31.73, -14.827), (-31.73, -9.949))
d1 = seg_by('MARK_L_A5', (-31.73, -9.949), (-44.831, 3.151))
d2 = seg_by('MARK_L_A5', (-31.73, -14.827), (-29.016, -17.541))
T, B = (-31.98, -9.699), (-31.98, -14.577)
for q, old, new in ((v, (-31.73, -9.949), T), (v, (-31.73, -14.827), B), (d1, (-31.73, -9.949), T), (d2, (-31.73, -14.827), B)):
    k = 5 if P(q, 5) == old else 7; q[k], q[k + 1] = round(mil(new[0]), 4), round(mil(new[1]), 4)
log.append('MARK_L_A5: trecho vertical 0,25 mm para a esquerda (x = −31,98), abrindo espaço para a OUT_A2')

# 4a) vias de costura de GND encostadas nas saídas do motor direito: afastadas para dar lugar às trilhas largas
OUTS = [LineString([P(q, 5), P(q, 7)]) for q in rows if q[0] == 'LINE' and q[3] in ('OUT_B1', 'OUT_B2') and q[4] == 1 and q[9] * M >= 1.0]
moved = []
for (vx, vy) in [(28.575, -5.588), (37.452, -7.112)]:
    v = next(q for q in rows if q[0] == 'VIA' and q[3] == 'GND' and abs(q[5] * M - vx) < 0.01 and abs(q[6] * M - vy) < 0.01)
    rows.remove(v)
    allp = unary_union([g for l, n, g, i in check.pad_geoms(rows, fps)])
    hs = [(q[5] * M, q[6] * M, q[7] * M) for q in rows if q[0] == 'VIA']
    best = None
    for rr in np.arange(0.2, 3.0, 0.1):
        for ang in range(0, 360, 15):
            x, y = vx + rr * math.cos(math.radians(ang)), vy + rr * math.sin(math.radians(ang))
            p = Point(x, y)
            if min(p.distance(s) for s in OUTS) < 1.25 + 0.2 + 0.3: continue
            if p.distance(allp) < 0.45 or not outer.buffer(-0.5).contains(p): continue
            if any(math.hypot(x - a, y - b) - h / 2 - 0.15 < 0.5 for a, b, h in hs): continue
            if not free(p.buffer(0.3), 'GND'): continue
            best = (round(float(x), 3), round(float(y), 3)); break
        if best: break
    assert best, (vx, vy)
    via('GND', *best, 0.6, 0.3); moved.append(((vx, vy), best))
log.append(f'vias de costura de GND afastadas das saídas do motor direito: {moved}')

# 4) alargamento no mesmo traçado
TARGET = {'VBAT': 3.0, 'OUT_A1': 2.5, 'OUT_A2': 2.5, 'OUT_B1': 2.5, 'OUT_B2': 2.5, 'OUT_C': 2.0}
def skip(q):
    (xa, ya), (xb, yb) = P(q, 5), P(q, 7)
    if q[3] != 'VBAT': return False
    if xa < -15 and xb < -15 and ya > 0 and yb > 0: return True                       # C1/C3/78M05 (pouca corrente)
    if q[4] == 2 and 12 <= min(xa, xb) and max(xa, xb) <= 19.5 and min(ya, yb) < 2.6 and max(ya, yb) < 3.5: return True   # ramo da medição (R2)
    if q[9] * M < 0.9: return True                                                    # trilhas finas de sinal
    return False
inner = outer.buffer(-0.3)
holes = unary_union(check.holes(rows))
WCLR = 0.2          # folga da regra do arquivo
cand = [q for q in rows if q[0] == 'LINE' and q[3] in TARGET and not skip(q) and q[9] * M < TARGET[q[3]] - 1e-3
        and LineString([P(q, 5), P(q, 7)]).length > 1e-3]
w_start = {id(q): q[9] * M for q in cand}
active = list(cand)
while active:          # rodadas: todas crescem 0,1 mm juntas, para dividir o espaço entre vizinhas
    nxt = []
    for q in active:
        w = round(q[9] * M + 0.1, 2)
        if w > TARGET[q[3]] + 1e-6: continue
        seg = LineString([P(q, 5), P(q, 7)]); b = seg.buffer(w / 2)
        if not inner.contains(b) or b.distance(holes) < 0.3: continue
        cu = [c for c in check.copper(rows, fps) if c[0] == q[4] and c[1] != q[3]]
        if any(g.distance(b) < WCLR for l, n, g, i in cu if g.distance(seg) < w / 2 + WCLR + 0.01): continue
        q[9] = round(mil(w), 4); nxt.append(q)
    active = nxt
# 4b) trechos longos (> 3 mm) ainda abaixo do alvo: divididos em três (1,2 mm em cada ponta) e o meio cresce de novo
split = []
for q in list(cand):
    if q[9] * M >= TARGET[q[3]] - 1e-3: continue
    (xa, ya), (xb, yb) = P(q, 5), P(q, 7); Ls = math.hypot(xb - xa, yb - ya)
    if Ls <= 3.0: continue
    t1, t2 = 1.2 / Ls, 1 - 1.2 / Ls
    pa = (round(xa + (xb - xa) * t1, 3), round(ya + (yb - ya) * t1, 3)); pb = (round(xa + (xb - xa) * t2, 3), round(ya + (yb - ya) * t2, 3))
    k = rows.index(q)
    mid = ['LINE', nid(), 0, q[3], q[4], round(mil(pa[0]), 4), round(mil(pa[1]), 4), round(mil(pb[0]), 4), round(mil(pb[1]), 4), q[9], 0]
    tail = ['LINE', nid(), 0, q[3], q[4], round(mil(pb[0]), 4), round(mil(pb[1]), 4), q[7], q[8], q[9], 0]
    q[7], q[8] = round(mil(pa[0]), 4), round(mil(pa[1]), 4)
    rows[k + 1:k + 1] = [mid, tail]; split.append(mid); w_start[id(mid)] = w_start[id(q)]; w_start[id(tail)] = w_start[id(q)]
    cand += [mid, tail]
active = list(split)
while active:
    nxt = []
    for q in active:
        w = round(q[9] * M + 0.1, 2)
        if w > TARGET[q[3]] + 1e-6: continue
        seg = LineString([P(q, 5), P(q, 7)]); b = seg.buffer(w / 2)
        if not inner.contains(b) or b.distance(holes) < 0.3: continue
        cu = [c for c in check.copper(rows, fps) if c[0] == q[4] and c[1] != q[3]]
        if any(g.distance(b) < WCLR for l, n, g, i in cu if g.distance(seg) < w / 2 + WCLR + 0.01): continue
        q[9] = round(mil(w), 4); nxt.append(q)
    active = nxt
log.append(f'{len(split)} trechos longos divididos (meio alargado)')
changed = [(q[3], q[4], round(w_start[id(q)], 2), round(q[9] * M, 2), round(LineString([P(q, 5), P(q, 7)]).length, 1)) for q in cand if q[9] * M > w_start[id(q)] + 1e-3]
log.append(f'alargadas {len(changed)} trilhas de potência')

# 5) vias de VBAT em paralelo no lado direito
cu = check.copper(rows, fps)
top = unary_union([g for l, n, g, i in cu if l == 1 and n == 'VBAT'])
bot = unary_union([g for l, n, g, i in cu if l == 2 and n == 'VBAT'])
pads = unary_union([g for l, n, g, i in check.pad_geoms(rows, fps)])
ref = next(q for q in rows if q[0] == 'VIA' and q[3] == 'VBAT' and abs(q[5] * M - 24.13) < 0.05)
added = []
for _ in range(2):
    vias = [(q[5] * M, q[6] * M, q[7] * M) for q in rows if q[0] == 'VIA']
    best = None
    for x in np.arange(19.5, 27.0, 0.05):
        for y in np.arange(-3.5, 5.0, 0.05):
            v = Point(x, y).buffer(0.8)
            if not top.buffer(0.02).contains(v) or not bot.buffer(0.02).contains(v): continue
            if v.distance(pads) < 0.25 or v.distance(holes) < 0.5: continue
            if any(math.hypot(x - a, y - b) - 0.5 - h / 2 < 0.5 for a, b, h in vias): continue
            d = math.hypot(x - ref[5] * M, y - ref[6] * M)
            if best is None or d < best[0]: best = (d, round(float(x), 2), round(float(y), 2))
    if not best: break
    via('VBAT', best[1], best[2], 1.6, 1.0); added.append(best[1:])
log.append(f'vias de VBAT 1,6/1,0 acrescentadas no lado direito: {added} (agora {1 + len(added)} em paralelo)')

# 6) J1: GND direto no pad
j1 = inv['J1']
gp = next(g for l, n, g, i in check.pad_geoms(rows, fps) if i.startswith(j1 + ':') and n == 'GND' and l == 1)
c = gp.centroid; stubs = []
for L in (1, 2):
    n = 0
    for ang in (270, 180, 0, 90, 225, 315, 135, 45):
        e = (round(c.x + 2.6 * math.cos(math.radians(ang)), 3), round(c.y + 2.6 * math.sin(math.radians(ang)), 3))
        t = LineString([(c.x, c.y), e]).buffer(1.0)
        if not inner.contains(t) or not free(t, 'GND', layers=(L,), clr=0.3): continue
        line('GND', L, [(round(c.x, 3), round(c.y, 3)), e], 2.0); n += 1; stubs.append((L, ang))
        if n == 3: break
log.append(f'J1: {len(stubs)} trilhas de GND de 2,0 × 2,6 mm saindo do pad (face, ângulo): {stubs}')

for q in rows:
    k = {'COMPONENT': 8, 'LINE': 10, 'VIA': 12, 'ATTR': 20}.get(q[0])
    if k is not None and len(q) > k and q[k] == 1: q[k] = 0
rows[:] = [q for q in rows if q[0] != 'POURED']
with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zo:
    for info in z.infolist():
        if info.is_dir(): zo.writestr(info, b''); continue
        data = z.read(info.filename)
        if info.filename == PCBN:
            data = ''.join(json.dumps(q, ensure_ascii=False, separators=(',', ':')) + '\n' for q in rows).encode('utf-8')
        zo.writestr(info, data)
print('\n'.join(log))
for ch in changed: print('   ', ch)
print('arquivo:', DST)
