"""Copia do Dreamcast para o Saturn os textos de serigrafia de polaridade (+/−) e os nomes dos pinos do J5 (ICSP).

Os componentes envolvidos (M1, M2, M3, J1, J2, J4/R20, J3, J5) estão nas mesmas posições e rotações nas duas placas
(conferido pelo script), então os textos vão nas mesmas coordenadas.
Uso: python3 copia_serigrafia_dreamcast.py <dreamcast.epro> <saturn.epro> <saida.epro>
Baseado no EVA-RT, (c) EXOTIC TEAM MX, AGPL-3.0.
"""
import sys, json, zipfile, re
M = 0.0254
DC, SAT, DST = sys.argv[1:4]
def load(p):
    z = zipfile.ZipFile(p); n = [x for x in z.namelist() if x.endswith('.epcb')][0]
    return z, n, [json.loads(l) for l in z.read(n).decode('utf-8-sig').splitlines() if l.strip()]
_, _, A = load(DC)
z, PCBN, B = load(SAT)
def comps(R):
    c = {r[1]: r for r in R if r[0] == 'COMPONENT'}
    d = {r[3]: r[8] for r in R if r[0] == 'ATTR' and r[3] in c and r[7] == 'Designator'}
    return {d[k]: (round(v[4], 2), round(v[5], 2), v[6], v[3]) for k, v in c.items() if k in d}
ca, cb = comps(A), comps(B)
for d in ('M1', 'M2', 'M3', 'J1', 'J2', 'J3', 'J4', 'J5', 'R20'):
    assert ca[d] == cb[d], (d, ca[d], cb[d])
textos = [r for r in A if r[0] == 'STRING' and not r[6].startswith('Projetado')]
ja = {(r[3], round(r[4], 1), round(r[5], 1), r[6]) for r in B if r[0] == 'STRING'}
n_id = max(int(r[1][1:]) for r in B if len(r) > 1 and isinstance(r[1], str) and re.fullmatch(r'e\d+', r[1]))
novos = 0
for r in textos:
    if (r[3], round(r[4], 1), round(r[5], 1), r[6]) in ja: continue
    n_id += 1; q = list(r); q[1] = f'e{n_id}'; B.append(q); novos += 1
print(f'{novos} textos copiados:', ', '.join(f"{r[6]}" for r in textos))
with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zo:
    for info in z.infolist():
        if info.is_dir(): zo.writestr(info, b''); continue
        data = z.read(info.filename)
        if info.filename == PCBN:
            data = ''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n' for r in B).encode('utf-8')
        zo.writestr(info, data)
print('arquivo:', DST)
