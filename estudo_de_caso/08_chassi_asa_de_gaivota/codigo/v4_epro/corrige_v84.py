"""v8.4 (14/11/2026): C2 fora do giro da hélice da ventoinha.

O impeller_fan do EVA-RT tem Ø34 (raio 17) e gira logo acima da placa, entre os pés da carcaça.
No v8.3 o corpo do C2 (eletrolítico SMD 6,3 × 7,7) chegava a r = 16,5 mm: a hélice batia nele.
- C2 vai para (21,72; 1,30), espelhado com o C1 em x: base a 1,4 mm e lata a 1,6 mm da ponta da hélice
  (o EVA-RT deixa ~1,9 mm com os radiais em (±22,0; 2,06)).
- M3 (pads do fio da ventoinha) desce 1,016 mm para abrir espaço ao corpo do C2; trilhas ligadas a ele ajustadas.
- As duas vias de VBAT saem de baixo do pad + do C2: (23,35; 2,09) e (24,64; 0,30); trilha de baixo refeita.
Uso: python3 corrige_v84.py <entrada.epro> <saida.epro>
Baseado no EVA-RT, (c) EXOTIC TEAM MX, AGPL-3.0.
"""
import sys, os, json, math, zipfile, re, pickle
from shapely.geometry import Point, LineString, box
from shapely import affinity
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
P = lambda r, k: (round(r[k] * M, 2), round(r[k + 1] * M, 2))
def get_line(net, L, a, b):
    m = [r for r in rows if r[0] == 'LINE' and r[3] == net and r[4] == L and {P(r, 5), P(r, 7)} == {a, b}]
    assert m, (net, L, a, b); return m
def drop(rs):
    ids = {id(r) for r in rs}; rows[:] = [r for r in rows if id(r) not in ids]
def set_end(r, old, new):
    k = 5 if P(r, 5) == old else 7
    assert P(r, k) == old, (r[1], old)
    r[k], r[k + 1] = round(mil(new[0]), 4), round(mil(new[1]), 4)
def move_comp(cid, dx, dy):
    for r in rows:
        if r[0] == 'COMPONENT' and r[1] == cid: r[4] = round(r[4] + mil(dx), 4); r[5] = round(r[5] + mil(dy), 4)
        if r[0] == 'ATTR' and r[3] == cid and r[5] is not None: r[5] = round(r[5] + mil(dx), 4); r[6] = round(r[6] + mil(dy), 4)
comp = {r[1]: r for r in rows if r[0] == 'COMPONENT'}
des = {r[3]: r[8] for r in rows if r[0] == 'ATTR' and r[3] in comp and r[7] == 'Designator'}
inv = {v: k for k, v in des.items()}
log = []

# 1) M3 desce 1,016 mm (40 mil)
DY = -40 * M
m3 = inv['M3']; y0, y1 = -2.67, round(-2.67 + DY, 2)
move_comp(m3, 0, DY)
for net, L, a, b in [('VBAT', 1, (24.64, 0.82), (24.64, -2.67)), ('VBAT', 1, (24.64, -2.67), (24.64, -5.97)),
                     ('VBAT', 2, (24.64, -2.67), (24.64, -4.8)), ('OUT_C', 2, (27.18, -2.67), (27.18, -6.17))]:
    for r in get_line(net, L, a, b): set_end(r, (a[0], y0) if a[1] == y0 else (b[0], y0), (a[0] if a[1] == y0 else b[0], y1))
drop(get_line('OUT_C', 1, (27.18, -2.67), (27.5, -2.34)))
line('OUT_C', 1, [(27.18, y1), (27.18, -2.66), (27.5, -2.34)], 1.0)
log.append(f'M3: desce 1,016 mm (pads em y = {y1}); trilhas de VBAT e OUT_C ajustadas')

# 2) C2 para (21,72; 1,30)
c2 = inv['C2']; X, Y = 21.72, 1.30
move_comp(c2, X - comp[c2][4] * M, Y - comp[c2][5] * M)
drop(get_line('VBAT', 1, (21.79, 2.09), (19.94, 3.94)))                 # ia ao pad + antigo
r = get_line('VBAT', 1, (25.91, 2.09), (21.79, 2.09))[0]; set_end(r, (21.79, 2.09), (21.72, 2.09))
line('VBAT', 1, [(21.72, 2.09), (21.72, 3.40)], 1.2)                      # entra no pad +
log.append(f'C2: ({X}; {Y}), rotação 270°; trilha de cima de VBAT termina no pad +')

# 3) vias de VBAT fora do pad + e trilha de baixo refeita
for (x, y) in [(21.35, 2.40), (23.00, 2.09)]:
    drop([q for q in rows if q[0] == 'VIA' and q[3] == 'VBAT' and P(q, 5) == (x, y)])
drop(get_line('VBAT', 2, (19.81, 3.94), (21.35, 2.40)) + get_line('VBAT', 2, (21.35, 2.40), (21.66, 2.09)) + get_line('VBAT', 2, (21.66, 2.09), (23.00, 2.09)))
V1, V2 = (23.35, 2.09), (24.64, 0.30)
via('VBAT', *V1, 1.6, 1.0); via('VBAT', *V2, 1.6, 1.0)
line('VBAT', 2, [(19.81, 3.94), (21.66, 2.09), V1, (24.64, 0.80), V2], 1.5)
log.append('VBAT: vias 1,6/1,0 em (23,35; 2,09) e (24,64; 0,30), fora do pad + do C2; trilha de baixo de 1,5 mm')

# checagens locais
cu = check.copper(rows, fps)
pg = [(l, n, g, i) for l, n, g, i in check.pad_geoms(rows, fps)]
def clash(cid):
    out = []
    for l, n, g, i in pg:
        if not i.startswith(cid + ':'): continue
        for l2, n2, g2, i2 in cu:
            if l2 == l and n2 != n and n2 != '' and g2.distance(g) < 0.2: out.append((i, i2, n2, round(g2.distance(g), 3)))
    return out
assert not clash(c2) and not clash(m3), (clash(c2), clash(m3))
pad_plus = next(g for l, n, g, i in pg if i.startswith(c2 + ':') and n == 'VBAT')
for v in (V1, V2):
    assert Point(v).buffer(0.8).distance(pad_plus) >= 0.2, ('via no pad', v)
body = affinity.translate(box(-3.3, -3.3, 3.3, 3.3), X, Y)
fan_gap = body.distance(Point(0, 0)) - 17.0
can_gap = math.hypot(X, Y) - 3.15 - 17.0
casing = pickle.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'carcaca_ate_8mm.pkl'), 'rb'))
assert fan_gap > 1.0 and not body.intersects(casing)
m3pads = [g for l, n, g, i in pg if i.startswith(m3 + ':')]
log.append(f'folga até a hélice: base {fan_gap:.2f} mm, lata {can_gap:.2f} mm; corpo do C2 a {min(body.distance(g) for g in m3pads):.2f} mm dos pads do M3')

# 4) GND do pad − do C2: via ao lado, com trilha curta (o plano não chegava ao pad no lugar novo)
import numpy as np, plano_gnd as G
from shapely.ops import unary_union
def free(g, net, layers=(1, 2), clr=0.2):
    cu = check.copper(rows, fps)
    return all(not any(gg.intersects(g.buffer(clr)) for l, n, gg, i in cu if l == L and n != net) for L in layers)
cu_, pcs, f, main = G.pieces(rows, fps, outer)
lost = [i for l, nn, g, i in cu_ if nn == 'GND' and not any(f(k) == main for k, (Lp, p) in enumerate(pcs) if Lp == l and p.intersects(g))]
if any(i.startswith(c2 + ':') for i in lost):
    gp = next(g for l, n, g, i in check.pad_geoms(rows, fps) if i.startswith(c2 + ':') and n == 'GND')
    pads = unary_union([g for l, n, g, i in check.pad_geoms(rows, fps)])
    c = gp.centroid; best = None
    for ang in (180, 135, 225, 90, 270, 0, 45, 315):
        for rr in np.arange(0.9, 2.6, 0.05):
            p = (round(c.x + rr * math.cos(math.radians(ang)), 2), round(c.y + rr * math.sin(math.radians(ang)), 2))
            if Point(p).distance(pads) < 0.3 + 0.15: continue
            if not free(Point(p).buffer(0.4), 'GND') or not free(LineString([(c.x, c.y), p]).buffer(0.2), 'GND', layers=(1,)): continue
            best = (float(p[0]), float(p[1])); break
        if best: break
    assert best, 'C2: sem lugar para a via de GND'
    via('GND', *best, 0.8, 0.4); line('GND', 1, [(round(c.x, 2), round(c.y, 2)), best], 0.4)
    log.append(f'C2: via de GND 0,8/0,4 em {best}, trilha de 0,4 mm até o pad −')
cu_, pcs, f, main = G.pieces(rows, fps, outer)
log.append('GND fora do plano (simulado): ' + str([i for l, nn, g, i in cu_ if nn == 'GND' and not any(f(k) == main for k, (Lp, p) in enumerate(pcs) if Lp == l and p.intersects(g))]))

for r in rows:
    k = {'COMPONENT': 8, 'LINE': 10, 'VIA': 12, 'ATTR': 20}.get(r[0])
    if k is not None and len(r) > k and r[k] == 1: r[k] = 0
rows[:] = [r for r in rows if r[0] != 'POURED']
with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zo:
    for info in z.infolist():
        if info.is_dir(): zo.writestr(info, b''); continue
        data = z.read(info.filename)
        if info.filename == PCBN:
            data = ''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n' for r in rows).encode('utf-8')
        zo.writestr(info, data)
print('\n'.join(log)); print('arquivo:', DST)
