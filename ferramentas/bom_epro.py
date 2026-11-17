"""BOM a partir do .epro do EasyEDA Pro (o que está colocado na PCB).

Uso: python3 ferramentas/bom_epro.py <projeto.epro> <saida.csv>

Lê os componentes da PCB (designador, valor, encapsulamento, DNP, face) e o
título do footprint em project.json. Agrupa por valor + footprint + DNP.
"""
import csv, json, re, sys, zipfile
from collections import defaultdict

SRC, DST = sys.argv[1], sys.argv[2]
z = zipfile.ZipFile(SRC)
proj = json.loads(z.read('project.json'))
fp_title = {k: v.get('title', '') for k, v in proj.get('footprints', {}).items()}
dev = proj.get('devices', {})

pcb = [n for n in z.namelist() if n.startswith('PCB/') and n.endswith('.epcb')]
assert len(pcb) == 1, pcb
rows = []
for l in z.read(pcb[0]).decode('utf-8').splitlines():
    l = l.strip()
    if l.startswith('['):
        try:
            rows.append(json.loads(l))
        except ValueError:
            pass

comp = {r[1]: r for r in rows if r[0] == 'COMPONENT'}
attr = defaultdict(dict)
for r in rows:
    if r[0] == 'ATTR' and r[3] in comp:
        attr[r[3]][r[7]] = r[8]

def chave(d):
    m = re.match(r'([A-Za-z]+)(\d+)', d)
    return (m.group(1), int(m.group(2))) if m else (d, 0)

grupos = defaultdict(list)
for cid, r in comp.items():
    a, p = attr[cid], (r[7] if isinstance(r[7], dict) else {})
    des = a.get('Designator', '')
    if not des or des.startswith('#'):
        continue
    d = dev.get(a.get('Device', ''), {}).get('attributes', {})
    valor = p.get('Value') or p.get('Name') or a.get('Name') or d.get('Value') or d.get('Name', '')
    m = re.fullmatch(r'=\{(.+)\}', valor or '')
    if m:  # valor do tipo ={Manufacturer Part}: vem dos atributos do device
        valor = p.get(m.group(1)) or d.get(m.group(1), valor)
    fp = fp_title.get(a.get('Footprint', ''), '')
    enc = p.get('Encapsulamento', '')
    dnp = 'sim' if str(p.get('DNP', 'no')).lower() in ('yes', 'sim', 'true', '1') else ''
    lcsc = p.get('Supplier Part') or d.get('Supplier Part', '')
    face = 'cima' if r[3] == 1 else 'baixo'
    grupos[(valor, fp, enc, dnp, lcsc)].append((des, face))

with open(DST, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['Designadores', 'Qtd', 'Valor', 'Encapsulamento', 'Footprint', 'Face', 'DNP', 'LCSC'])
    for (valor, fp, enc, dnp, lcsc), it in sorted(grupos.items(), key=lambda g: chave(min(g[1], key=lambda x: chave(x[0]))[0])):
        it.sort(key=lambda x: chave(x[0]))
        faces = sorted({fc for _, fc in it})
        w.writerow([', '.join(d for d, _ in it), len(it), valor, enc, fp, '/'.join(faces), dnp, lcsc])
print(DST, sum(len(v) for v in grupos.values()), 'componentes em', len(grupos), 'linhas')
