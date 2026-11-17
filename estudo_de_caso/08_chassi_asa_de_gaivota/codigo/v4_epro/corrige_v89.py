"""v8.9 (15/11/2026): J3 (gravação, embaixo) entre a borda traseira e a placa de sucção.

Entre a borda (y ≈ −30,0 no centro) e a placa de sucção (y = −27,5) há 2,5 mm, e os pads tinham 2,25 mm:
não cabia a folga de borda (0,3 mm, regra do arquivo) e a da placa de sucção ao mesmo tempo.
Pads do J3 encurtados para 1,9 mm (largura igual, 1,25 mm) e J3 em y = −28,75: 0,30 mm até a borda e 0,30 mm até a placa de sucção.
Uso: python3 corrige_v89.py <entrada.epro> <saida.epro>
Baseado no EVA-RT, (c) EXOTIC TEAM MX, AGPL-3.0.
"""
import sys, os, json, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
M = 0.0254
SRC, DST = sys.argv[1], sys.argv[2]
z = zipfile.ZipFile(SRC)
load = lambda n: [json.loads(l) for l in z.read(n).decode('utf-8-sig').splitlines() if l.strip()]
PCBN = [n for n in z.namelist() if n.endswith('.epcb')][0]
rows = load(PCBN)
comp = {r[1]: r for r in rows if r[0] == 'COMPONENT'}
des = {r[3]: r[8] for r in rows if r[0] == 'ATTR' and r[3] in comp and r[7] == 'Designator'}
fp = {r[3]: r[8] for r in rows if r[0] == 'ATTR' and r[7] == 'Footprint'}
j3 = next(k for k, v in des.items() if v == 'J3')
FPN = f'FOOTPRINT/{fp[j3]}.efoo'
assert [c for c, v in fp.items() if v == fp[j3]] == [j3]
foot = load(FPN)
for p in foot:
    if p[0] == 'PAD': p[10][2] = round(1.9 / M, 4)
dy = -28.75 / M - comp[j3][5]
for r in rows:
    if r[0] == 'COMPONENT' and r[1] == j3: r[5] = round(r[5] + dy, 4)
    if r[0] == 'ATTR' and r[3] == j3 and r[5] is not None: r[6] = round(r[6] + dy, 4)
dump = lambda rr: ''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n' for r in rr).encode('utf-8')
with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zo:
    for info in z.infolist():
        if info.is_dir(): zo.writestr(info, b''); continue
        data = z.read(info.filename)
        if info.filename == PCBN: data = dump(rows)
        elif info.filename == FPN: data = dump(foot)
        zo.writestr(info, data)
print('arquivo:', DST)
