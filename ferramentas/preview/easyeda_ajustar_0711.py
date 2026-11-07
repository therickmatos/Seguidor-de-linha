# Correcoes de 07/11 aprovadas pelo Erick no projeto RUSH (pcb_2026-11-07.epro). Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""Aplica as correcoes aprovadas pelo Erick no .epro (formato 2) e confere. Uso: ajustar_v4.py entrada saida"""
import sys, json, math, collections, io, zipfile
sys.path.insert(0, '/home/user/Seguidor-de-linha/ferramentas/preview')
import easyeda_posicionar as E, placa_v2 as V, footprints as F, layout_placa as M
from shapely.geometry import Point
MIL = E.MIL
ent, sai = sys.argv[1], sys.argv[2]
z, dados = E.ler_epro(ent)
pcb_nome = next(n for n in dados if n.startswith('PCB/') and n.endswith('.epcb'))
pcb = E.linhas_json(dados[pcb_nome])
attr = collections.defaultdict(dict)
for r in pcb:
    if r[0] == 'ATTR': attr[r[3]][r[7]] = r[8]
cid = {attr[r[1]].get('Designator'): r[1] for r in pcb if r[0] == 'COMPONENT'}
comp = {r[1]: r for r in pcb if r[0] == 'COMPONENT'}
fp = {d: E.pads_footprint(dados, attr[c]['Footprint']) for d, c in cid.items()}
ref = E.referencia()

def pos_ref(des, dx=0.0, dy=0.0):
    """posicao (mm) e rotacao do footprint DELE que poe os pads nos pads da referencia"""
    baixo = ref[des]['face'] == 'BOTTOM'
    pinos = [p for p in sorted(ref[des]['pinos']) if p in fp[des]]
    x, y, rot = E.ajustar([(fp[des][p][0]['x'], fp[des][p][0]['y']) for p in pinos], [ref[des]['pinos'][p][:2] for p in pinos], baixo)
    return x + dx, y + dy, rot

NOVO = {}   # des -> (x_mm, y_mm, rot)
def atual(des):
    r = comp[cid[des]]; return r[4]*MIL, r[5]*MIL, r[6]
# 1) ATmega: so desce ate y = -23,0 (fora do disco do rotor, mesmo x e rotacao)
x, y, rot = atual('U2'); NOVO['U2'] = (x, -23.0, rot)
# 2) cristal junto dos pinos 7/8 (posicao da referencia, ajustada ao footprint da LCSC) e os 22 pF colados nele
NOVO['X1'] = pos_ref('X1', -0.6, 0.2)
NOVO['C9'] = pos_ref('C9')
NOVO['C10'] = pos_ref('C10', 0.0, -0.05)
# 3) 100 nF do AVCC junto dos pinos 18/21
NOVO['C7'] = pos_ref('C7')
# 4) ventoinha na disposicao da referencia (M3, D1 embaixo, Q1); C17 ja esta no lugar
for d in ('M3', 'D1', 'Q1'): NOVO[d] = pos_ref(d)
# 5) R10 fora do pe da carcaca (desce 0,13 mm; continua alinhado na pratica)
x, y, rot = atual('R10'); NOVO['R10'] = (x, -18.75, rot)
# 6) SW2/SW3 juntos para x = 36,10 (SW3 sai da area da presilha; a coluna continua alinhada)
for d in ('SW2', 'SW3'):
    x, y, rot = atual(d); NOVO[d] = (36.10, y, rot)
for d, v in NOVO.items():
    print(f'{d:4s} de ({atual(d)[0]:7.2f}; {atual(d)[1]:7.2f}) {atual(d)[2]:6.1f}  para ({v[0]:7.2f}; {v[1]:7.2f}) {v[2]:6.1f}')

# ---- escreve
out = []
velcro = [h for h in M.BOARD_DATA['furos'] if h['tipo'] == 'rasgo']
def eh_rasgo(r):
    if r[0] != 'POLY' or r[4] != 11: return False
    xs = [r[6][0]*MIL, r[6][3]*MIL]; ys = [r[6][1]*MIL, r[6][4]*MIL]
    return any(all(abs(xx - h['x']) <= h['w']/2 + 0.05 for xx in xs) and all(abs(yy - h['y']) <= h['h']/2 + 0.05 for yy in ys) for h in velcro)
removidos = 0; pad_velcro = None
for r in pcb:
    if eh_rasgo(r):
        removidos += 1; continue
    if r[0] == 'COMPONENT' and r[1] in comp:
        d = attr[r[1]].get('Designator')
        if d in NOVO:
            r = list(r); x0, y0 = r[4], r[5]; r[4], r[5], r[6] = round(NOVO[d][0]/MIL, 4), round(NOVO[d][1]/MIL, 4), NOVO[d][2]
            if d == 'D1': r[3] = 2
            NOVO[d] = NOVO[d] + ((r[4]-x0), (r[5]-y0))
    if r[0] == 'PAD' and r[4] == 12 and r[9] and r[9][0] == 'SLOT':
        pad_velcro = r; continue
    out.append(r)
# designador acompanha a peca (mesmo deslocamento)
for i, r in enumerate(out):
    if r[0] == 'ATTR' and r[7] == 'Designator':
        d = attr[r[3]].get('Designator')
        if d in NOVO and r[5] is not None:
            r = list(r); r[5] = round(r[5] + NOVO[d][3], 4); r[6] = round(r[6] + NOVO[d][4], 4); out[i] = r
# velcro: o pad dele duplicado nos dois rasgos
usados = {r[1] for r in pcb if len(r) > 1 and isinstance(r[1], str)}
for k, h in enumerate(sorted(velcro, key=lambda h: h['x'])):
    p = list(pad_velcro); p[6], p[7] = round(h['x']/MIL, 4), round(h['y']/MIL, 4)
    if k == 1: p[1] = pad_velcro[1]
    else:
        n = 95000
        while f'e{n}' in usados: n += 1
        p[1] = f'e{n}'
    out.append(p)
print('segmentos de rasgo retirados do contorno:', removidos)
dados[pcb_nome] = '\n'.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) for r in out).encode('utf8')
buf = io.BytesIO()
with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zo:
    for info in z.infolist(): zo.writestr(info, dados[info.filename])
open(sai, 'wb').write(buf.getvalue())
