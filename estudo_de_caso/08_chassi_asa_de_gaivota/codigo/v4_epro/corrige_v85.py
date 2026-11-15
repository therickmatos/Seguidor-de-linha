"""v8.5 (14/11/2026): folgas com os STL do EVA-RT (ver interferencias_stl.py).

- R2 e R10 ficavam a 0,09 mm do pé traseiro da carcaça (impeller_base_1) na altura da placa:
  R2 desce 0,5 mm; R10 vai para (−13,033; −18,829) em pé (90°), com o pad de +5V na trilha
  larga de +5V e o RESET em 45° até a trilha que já existia.
- M1 (fio do motor esquerdo) invadia 0,25 mm a base da caixa de redução: sobe 0,762 mm (mesmo y do M2).
- J3 (gravação, embaixo): a ponta dos pads ficava 0,05 mm dentro da placa de sucção: vai 0,5 mm para trás.
Uso: python3 corrige_v85.py <entrada.epro> <saida.epro>
Baseado no EVA-RT, (c) EXOTIC TEAM MX, AGPL-3.0.
"""
import sys, os, json, zipfile, re
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
n_id = max(int(r[1][1:]) for r in rows if len(r) > 1 and isinstance(r[1], str) and re.fullmatch(r'e\d+', r[1]))
def nid():
    global n_id
    n_id += 1; return f'e{n_id}'
def line(net, L, pts, w):
    for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):
        rows.append(['LINE', nid(), 0, net, L, round(mil(x1), 4), round(mil(y1), 4), round(mil(x2), 4), round(mil(y2), 4), round(mil(w), 4), 0])
P = lambda r, k: (round(r[k] * M, 3), round(r[k + 1] * M, 3))
comp = {r[1]: r for r in rows if r[0] == 'COMPONENT'}
des = {r[3]: r[8] for r in rows if r[0] == 'ATTR' and r[3] in comp and r[7] == 'Designator'}
inv = {v: k for k, v in des.items()}
def move(d, dx, dy, rot=None):
    cid = inv[d]
    for r in rows:
        if r[0] == 'COMPONENT' and r[1] == cid:
            r[4] = round(r[4] + mil(dx), 4); r[5] = round(r[5] + mil(dy), 4)
            if rot is not None: r[6] = rot
        if r[0] == 'ATTR' and r[3] == cid and r[5] is not None: r[5] = round(r[5] + mil(dx), 4); r[6] = round(r[6] + mil(dy), 4)
log = []

# R2: desce 0,5 mm; a trilha de VBAT (1,0 mm) que entra por baixo acompanha
move('R2', 0, -0.5)
for r in rows:
    if r[0] == 'LINE' and r[3] == 'VBAT' and r[4] == 1 and {P(r, 5), P(r, 7)} == {(14.36, -20.3), (14.36, -18.75)}:
        k = 5 if P(r, 5) == (14.36, -18.75) else 7; r[k + 1] = round(mil(-19.25), 4)
log.append('R2: desce 0,5 mm (y = −19,25)')

# R10: em pé em (−13,033; −18,829)
r10 = comp[inv['R10']]
dx, dy = -13.033 - r10[4] * M, -18.829 - r10[5] * M
move('R10', dx, dy, rot=90)
rows[:] = [r for r in rows if not (r[0] == 'LINE' and r[3] == 'RESET' and {P(r, 5), P(r, 7)} == {(-13.217, -18.75), (-12.472, -18.75)})]
pg = check.pad_geoms(rows, fps)
p2 = next(g for l, n, g, i in pg if i.startswith(inv['R10'] + ':') and n == 'RESET').centroid
y2 = round(p2.y, 3); x2 = round(p2.x, 3)
line('RESET', 1, [(x2, y2), (x2 + (y2 + 18.75), -18.75)], 0.25)   # termina sobre a trilha e416
log.append(f'R10: em pé em (−13,033; −18,829); RESET do pad ({x2}; {y2}) em 45° até y = −18,75')

move('M1', 0, 0.762)
log.append('M1: sobe 0,762 mm (mesmo y do M2)')
move('J3', 0, -0.5)
log.append('J3: 0,5 mm para trás')

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
