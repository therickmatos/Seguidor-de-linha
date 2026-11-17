"""v8.3 (14/11/2026): pedidos do Erick depois da comparação com o EVA-RT e o HyperLine.

- Segunda via de VBAT (1,6/1,0) junto ao C2, em paralelo com a que já existe, como o EVA-RT
  faz nas trocas de face da potência; trilha de baixo de 1,5 mm até ela.
- R14/R15 (IPROPI) de 1,5k para 910 Ω 1%: ITRIP ≈ 4,8 A (abaixo do OCP de 6 A do DRV8874).
Nada travado; o resto da placa fica como está.
Uso: python3 corrige_v83.py <entrada.epro> <saida.epro>
Baseado no EVA-RT, (c) EXOTIC TEAM MX, AGPL-3.0.
"""
import sys, os, json, math, zipfile, re
from shapely.geometry import Point, LineString
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check, verifica_placa as V
M = 0.0254
mil = lambda v: v / M
SRC, DST = sys.argv[1], sys.argv[2]
z = zipfile.ZipFile(SRC)
PCBN = [n for n in z.namelist() if n.endswith('.epcb')][0]
SCHN = [n for n in z.namelist() if n.endswith('.esch')][0]
load = lambda n: [json.loads(l) for l in z.read(n).decode('utf-8-sig').splitlines() if l.strip()]
rows, sch = load(PCBN), load(SCHN)
fps = {n.split('/')[1][:-5]: load(n) for n in z.namelist() if n.endswith('.efoo')}
n_id = max(int(r[1][1:]) for r in rows if len(r) > 1 and isinstance(r[1], str) and re.fullmatch(r'e\d+', r[1]))
def nid():
    global n_id
    n_id += 1; return f'e{n_id}'
def line(net, L, pts, w):
    for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):
        rows.append(['LINE', nid(), 0, net, L, round(mil(x1), 4), round(mil(y1), 4), round(mil(x2), 4), round(mil(y2), 4), round(mil(w), 4), 0])
def via(net, x, y, d, h):
    rows.append(['VIA', nid(), 0, net, '', round(mil(x), 4), round(mil(y), 4), round(mil(h), 4), round(mil(d), 4), 0, None, None, 0, []])
def free(g, net, layers=(1, 2), clr=0.2):
    cu = check.copper(rows, fps)
    return all(not any(gg.intersects(g.buffer(clr)) for l, n, gg, i in cu if l == L and n != net) for L in layers)
log = []

# 1) segunda via de VBAT junto ao C2
v1 = next(r for r in rows if r[0] == 'VIA' and r[3] == 'VBAT' and abs(r[5] * M - 21.35) < 0.05 and abs(r[6] * M - 2.40) < 0.05)
A = (21.35, 2.40); B = (21.66, 2.09); V2 = (23.00, 2.09)
assert free(Point(V2).buffer(0.8), 'VBAT'), 'via 2 sem folga'
assert free(LineString([A, B, V2]).buffer(0.75), 'VBAT', layers=(2,)), 'trilha de baixo sem folga'
hole_gap = math.dist(A, V2) - 1.0
assert hole_gap >= 0.5, hole_gap
via('VBAT', *V2, 1.6, 1.0)
line('VBAT', 2, [A, B, V2], 1.5)
log.append(f'VBAT: via 1,6/1,0 em (23,00; 2,09), sobre a trilha de cima de 1,6 mm; trilha de baixo 1,5 mm desde a via do C2 (furo a furo {hole_gap:.2f} mm)')

# 2) R14/R15 = 910 Ω 1% (esquemático; na PCB o valor não fica no footprint)
par = {r[2] for r in sch if r[0] == 'ATTR' and r[3] == 'Designator' and r[4] in ('R14', 'R15')}
assert len(par) == 2
n = 0
for r in sch:
    if r[0] == 'ATTR' and r[2] in par and r[3] in ('Name', 'Value'):
        assert r[4] == '1.5k 1%', r[4]; r[4] = '910 1%'; n += 1
assert n == 4
log.append('R14/R15: 1.5k 1% -> 910 1% (Name e Value no esquemático)')

# nada travado
for r in rows:
    k = {'COMPONENT': 8, 'LINE': 10, 'VIA': 12, 'ATTR': 20}.get(r[0])
    if k is not None and len(r) > k and r[k] == 1: r[k] = 0
rows[:] = [r for r in rows if r[0] != 'POURED']
dump = lambda rr: ''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n' for r in rr).encode('utf-8')
with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zo:
    for info in z.infolist():
        if info.is_dir(): zo.writestr(info, b''); continue
        data = z.read(info.filename)
        if info.filename == PCBN: data = dump(rows)
        elif info.filename == SCHN: data = dump(sch)
        zo.writestr(info, data)
print('\n'.join(log)); print('arquivo:', DST)
