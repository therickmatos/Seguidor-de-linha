"""Gera a v3 com o contorno asa de gaivota e os 4 QRE. Baseado no EVA-RT (AGPL-3.0)."""
import json, math, os, re, sys, copy, shutil, zipfile
import numpy as np
from shapely.geometry import LineString, Point, Polygon
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import contorno as C
M = 0.0254
mil = lambda v: v / M
import tempfile
REPO = '/home/user/Seguidor-de-linha'
for _p in __import__('pathlib').Path(__file__).resolve().parents:
    if (_p / 'CLAUDE.md').exists(): REPO = str(_p); break
SRC = os.path.join(REPO, 'ProPrj_RUSH - SATURN - v3_2026-11-09.epro')
DST = os.path.join(REPO, 'ProPrj_RUSH - SATURN - v4_asa_gaivota_2026-11-11.epro')
ORIG = tempfile.mkdtemp(prefix='v3_')
zipfile.ZipFile(SRC).extractall(ORIG)
PCBF = 'PCB/888586395c7d5a9b1bb99ffcd1d10b35.epcb'
SCHF = 'SHEET/1306c329742b557c/1.esch'

def load(path): return [json.loads(l) for l in open(path, encoding='utf-8-sig') if l.strip()]
pcb = load(os.path.join(ORIG, PCBF))
sch = load(os.path.join(ORIG, SCHF))

class Ids:
    def __init__(self, rows):
        n = 0
        for r in rows:
            for v in r[1:3]:
                if isinstance(v, str) and re.fullmatch(r'e\d+', v): n = max(n, int(v[1:]))
        self.n = n + 1000
    def __call__(self):
        self.n += 1; return f'e{self.n}'
pid, sid = Ids(pcb), Ids(sch)

# ---------------- PCB ----------------
DX, DY = C.SENSOR_OUT[0] - 69.5, C.SENSOR_OUT[1] - 4.5          # 12,0 ; 11,5
ARM = {1: ['e107', 'e162', 'e166', 'e170', 'e230'], -1: ['e103', 'e150', 'e154', 'e158', 'e226']}
ARM_NETS = {'+5V', 'GND', 'MARK_R_A6', 'MARK_L_A5', 'LEDA_D2', 'LEDB_D7', '$1N2048', '$1N2069', '$1N2073', '$1N2082'}

def pts_of(r):
    if r[0] == 'LINE': return [(r[5], r[6]), (r[7], r[8])]
    if r[0] == 'VIA': return [(r[5], r[6])]
    if r[0] == 'ARC': return [(r[5], r[6]), (r[7], r[8])]
    return []

out = []
removed, moved = [], []
for r in pcb:
    if r[0] == 'POLY' and r[4] == 11: continue                        # contorno antigo
    if r[0] == 'POURED': continue                                     # cobre já despejado: refazer no EasyEDA
    if r[0] == 'COMPONENT':
        for sx, ids in ARM.items():
            if r[1] in ids:
                r = copy.deepcopy(r); r[4] += mil(sx * DX); r[5] += mil(DY); moved.append(r[1])
    if r[0] == 'ATTR' and r[5] is not None:
        for sx, ids in ARM.items():
            if r[3] in ids:
                r = copy.deepcopy(r); r[5] += mil(sx * DX); r[6] += mil(DY)
    if r[0] in ('LINE', 'VIA', 'ARC') and r[3] in ARM_NETS:
        P = [(x * M, y * M) for x, y in pts_of(r)]
        far = [abs(x) >= 57.5 and -1 < y < 9 for x, y in P]
        mid = [abs(x) > 49.6 and -1 < y < 9 for x, y in P]
        if all(far):
            sx = 1 if P[0][0] > 0 else -1
            r = copy.deepcopy(r)
            if r[0] == 'VIA': r[5] += mil(sx * DX); r[6] += mil(DY)
            else:
                r[5] += mil(sx * DX); r[6] += mil(DY); r[7] += mil(sx * DX); r[8] += mil(DY)
        elif any(mid):
            removed.append((r[3], [(round(x, 2), round(y, 2)) for x, y in P])); continue
    out.append(r)
pcb = out

v3, outer, board, cuts, sensors, edge = C.build()
# rótulos do S1/S2 (externos): a translação os deixaria na borda de baixo da aba; ficam logo abaixo dos pads
for r in pcb:
    if r[0] == 'ATTR' and r[7] == 'Designator' and r[3] in ('e226', 'e230'):
        sx = -1 if r[3] == 'e226' else 1
        r[5] = round(mil(sx * 83.0), 4); r[6] = round(mil(13.75), 4)
for (x1, y1), (x2, y2) in zip(outer.exterior.coords[:-1], outer.exterior.coords[1:]):
    pcb.append(['POLY', pid(), 0, '', 11, 10, [round(mil(x1), 4), round(mil(y1), 4), 'L', round(mil(x2), 4), round(mil(y2), 4)], 0])

def line(net, layer, pts, w=0.254):
    for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):
        pcb.append(['LINE', pid(), 0, net, layer, round(mil(x1), 4), round(mil(y1), 4), round(mil(x2), 4), round(mil(y2), 4), round(mil(w), 4), 0])
def via(net, x, y, d=0.8, hole=0.4):
    pcb.append(['VIA', pid(), 0, net, '', round(mil(x), 4), round(mil(y), 4), round(mil(hole), 4), round(mil(d), 4), 0, None, None, 1, []])


# ---------------- trilhas das abas (camada de cima) ----------------
S2 = math.sqrt(2)
def lane(points, r=1.5):
    return [tuple(p) for p in C._fillet_polyline(points, r, n=8)]
NEW_LINES_START = len(pcb)
R_LANES = [  # (rede, largura, pontos)
    ('LEDB_D7', 0.254, [(49.47, 1.95), (49.47, 49.47 - 36.5 - 2.2 * S2), (14.48 + 36.5 + 2.2 * S2, 14.48), (72.57, 14.48)]),
    ('+5V', 0.5, [(43.62, 6.18), (6.18 + 36.5 + 1.0 * S2, 6.18), (17.68 + 36.5 + 1.0 * S2, 17.68), (74.9, 17.68)]),
    ('MARK_R_A6', 0.254, [(39.86, 6.86), (6.86 + 36.5, 6.86), (18.36 + 36.5, 18.36), (75.35, 18.36)]),
]
L_LANES = [
    ('LEDA_D2', 0.254, [(-45.7, 2.88), (-49.47, 2.88), (-49.47, 49.47 - 36.5 - 2.2 * S2), (-(14.38 + 36.5 + 2.2 * S2), 14.38), (-72.93, 14.38)]),
    ('+5V', 0.5, [(-48.4, 4.26), (-48.4, 48.4 - 36.5 - 1.0 * S2), (-(15.76 + 36.5 + 1.0 * S2), 15.76), (-74.78, 15.76)]),
    ('MARK_L_A5', 0.254, [(-45.36, 5.13), (-47.3, 5.13), (-47.3, 47.3 - 36.5), (-(18.33 + 36.5), 18.33), (-69.73, 18.33)]),
]
for net, w, P in R_LANES + L_LANES:
    line(net, 1, lane(P), w)
line('+5V', 1, [(-44.25, 4.26), (-48.4, 4.26)], 0.4)     # trecho mais fino entre as vias do MARK_L_A5 (folga 0,2)

# ---------------- QRE internos (E1/D1) ----------------
TPL = {}
for r in load(os.path.join(ORIG, PCBF)):
    if r[0] == 'COMPONENT' and r[1] in ('e230', 'e162', 'e13'): TPL[r[1]] = dict(row=r, attrs=[], padnet=[])
for r in load(os.path.join(ORIG, PCBF)):
    if r[0] == 'ATTR' and r[3] in TPL: TPL[r[3]]['attrs'].append(r)
    if r[0] == 'PAD_NET' and r[1] in TPL: TPL[r[1]]['padnet'].append(r)
NEW_COMPS = []   # (pcb id, sch id, designator, uid, info) para o esquemático
UID = [68]
def add_comp(tpl, des, x, y, rot, nets, name=None, value=None, dnp='no', desc=None):
    t = TPL[tpl]; cid = pid(); schid = sid()
    uid = f'gge{UID[0]}'; UID[0] += 1
    row = copy.deepcopy(t['row']); row[1] = cid; row[3] = 2; row[4] = round(mil(x), 4); row[5] = round(mil(y), 4); row[6] = rot
    a = row[7]; a['Unique ID'] = uid; a['Channel ID'] = f'$1{schid}'; a['DNP'] = dnp
    if name: a['Name'] = name
    if value: a['Value'] = value
    if desc is not None: a['Description'] = desc
    pcb.append(row)
    for at in t['attrs']:
        at = copy.deepcopy(at); at[1] = pid(); at[3] = cid
        if at[7] == 'Designator':
            at[8] = des; at[4] = 4; at[5] = round(mil(x), 4); at[6] = round(mil(y - 2.4), 4); at[17] = 0
        pcb.append(at)
    for pn in t['padnet']:
        pn = copy.deepcopy(pn); pn[1] = cid
        if pn[2]: pn[3] = nets[pn[2]]
        pcb.append(pn)
    NEW_COMPS.append(dict(pcb=cid, sch=schid, des=des, uid=uid, tpl=tpl, nets=nets, name=name, value=value, dnp=dnp))
    return cid

def arm_pt(sx, s, d):     # ponto no referencial do QRE interno (s ao longo da aba a 45°, d transversal)
    x = 50.5 + (s - d) / S2; y = 14 + (s + d) / S2
    return (sx * x, y)
# Posições conferidas com check.py (folga >= 0,2 mm, borda >= 0,3 mm). O QRE é quiral (só se espelha trocando de face),
# então o lado esquerdo tem rotação e roteamento próprios.
B5 = 0.3   # largura das trilhas novas de alimentação na camada de baixo
SIDES = {
  1: dict(des='S4', sig='MARK_R2_D9', anode='QRE_D1_A', r220='R25', r47='R26', cap='C20', rot=45,
          r220pos=(46.9, 11.3, 90), r47pos=(48.6, 5.6, 270), cappos=(47.1, 5.6, 90),
          vias=[('+5V', 46.9, 46.9 - 37.914), ('GND', 47.85, 3.6), ('GND', 51.98, 17.61), ('+5V', 53.6, 53.6 - 37.914)],
          lines=[('+5V', [(52.55, 14.78), (53.6, 53.6 - 37.914)], B5),
                 ('GND', [(51.28, 16.05), (51.98, 17.61)], B5),
                 ('QRE_D1_A', [(48.45, 13.22), (46.9, 12.05)], 0.254),
                 ('+5V', [(46.9, 10.55), (46.9, 46.9 - 37.914)], B5),
                 ('MARK_R2_D9', [(49.72, 11.95), (49.1, 11.33), (49.1, 7.0), (48.6, 6.5), (48.6, 6.35)], 0.254),
                 ('MARK_R2_D9', [(48.6, 6.35), (47.1, 6.35)], 0.254),
                 ('GND', [(48.6, 4.85), (47.85, 4.1), (47.85, 3.6)], B5),
                 ('GND', [(47.1, 4.85), (47.85, 4.1)], B5)]),
  -1: dict(des='S3', sig='MARK_L2_D8', anode='QRE_E1_A', r220='R23', r47='R24', cap='C19', rot=315,
          r220pos=(-57.5, 17.6, 0), r47pos=(-48.6, 5.6, 270), cappos=(-47.1, 5.6, 90),
          vias=[('+5V', -49.0, 49.0 - 37.914), ('GND', -47.4, 13.0), ('GND', -47.85, 1.9), ('+5V', -59.5, 15.76)],
          lines=[('+5V', [(-49.72, 11.95), (-49.0, 49.0 - 37.914)], B5),
                 ('GND', [(-48.45, 13.22), (-47.4, 13.0)], B5),
                 ('QRE_E1_A', [(-51.28, 16.05), (-52.83, 17.6), (-56.75, 17.6)], 0.254),
                 ('+5V', [(-58.25, 17.6), (-59.5, 16.35), (-59.5, 15.76)], B5),
                 ('MARK_L2_D8', [(-52.55, 14.78), (-53.33, 14.0), (-49.79, 10.46), (-49.3, 9.97), (-49.3, 7.0), (-48.6, 6.5), (-48.6, 6.35)], 0.254),
                 ('MARK_L2_D8', [(-48.6, 6.35), (-47.1, 6.35)], 0.254),
                 ('GND', [(-48.6, 4.85), (-47.85, 4.1), (-47.85, 1.9)], B5),
                 ('GND', [(-47.1, 4.85), (-47.85, 4.1)], B5)]),
}
# C19 (E1) montado: filtro RC (~0,5 ms) na trilha longa até o pino 12. C20 (D1) segue não montado.
CAP_DNP = {'C19': 'no', 'C20': 'yes'}
CAP_DESC = {'C19': 'filtro RC com o 47k (trilha longa ate o pino 12); ver PINOS.md',
            'C20': 'DNP: montar so para leitura por tempo de descarga (ver PINOS.md)'}
for sx, I in SIDES.items():
    add_comp('e230', I['des'], sx * 50.5, 14.0, I['rot'], {'1': I['anode'], '2': 'GND', '3': '+5V', '4': I['sig']})
    x, y, r = I['r220pos']; add_comp('e162', I['r220'], x, y, r, {'1': '+5V', '2': I['anode']}, name='220', value='220')
    x, y, r = I['r47pos']; add_comp('e162', I['r47'], x, y, r, {'1': I['sig'], '2': 'GND'}, name='47k', value='47k')
    x, y, r = I['cappos']; add_comp('e13', I['cap'], x, y, r, {'1': 'GND', '2': I['sig']}, name='10nF', value='10nF',
                                     dnp=CAP_DNP[I['cap']], desc=CAP_DESC[I['cap']])
    for net, vx, vy in I['vias']: via(net, vx, vy)
    for net, P, w in I['lines']: line(net, 2, P, w)

# pinos 12 (PB0) e 13 (PB1) do ATmega (e238) recebem as redes novas
for r in pcb:
    if r[0] == 'PAD_NET' and r[1] == 'e238' and r[2] in ('12', '13'):
        r[3] = 'MARK_L2_D8' if r[2] == '12' else 'MARK_R2_D9'
# redes novas na lista de redes da PCB (depois da última linha NET)
last = max(i for i, r in enumerate(pcb) if r[0] == 'NET')
for n in ('MARK_L2_D8', 'MARK_R2_D9', 'QRE_E1_A', 'QRE_D1_A'):
    last += 1; pcb.insert(last, ['NET', n, None, None, 1, None, 0, None])

# ---------------- roteamento automático do E1 (pino 12) ----------------
# Só cabe uma saída para os pinos 12/13 sem mexer no roteamento da v3: fica com o E1 (MARK_L2_D8).
# O D1 (MARK_R2_D9, pino 13) fica por rotear: ver PINOS.md.
ROUTE_REPORT = {}
if os.environ.get('V4_ROTEAR', '1') == '1':
    import route_v4
    _fps = {f[:-5]: load(os.path.join(ORIG, 'FOOTPRINT', f)) for f in os.listdir(os.path.join(ORIG, 'FOOTPRINT'))}
    ROUTE_REPORT = route_v4.route_all(sys.modules[__name__], _fps, (('MARK_L2_D8', '12'),), 150, verbose=False)
    import costura_gnd
    GND_STITCH = costura_gnd.stitch(sys.modules[__name__], _fps)

# ---------------- esquemático ----------------
BY = {}
for r in sch:
    if r[0] == 'ATTR': BY.setdefault(r[2], []).append(r)
def in_box(r, x0, x1, y0, y1):
    if r[0] == 'COMPONENT': return x0 <= r[3] <= x1 and y0 <= r[4] <= y1
    if r[0] == 'WIRE':
        return all(x0 <= p[i] <= x1 and y0 <= p[i + 1] <= y1 for p in r[2] for i in range(0, len(p), 2))
    return False
NEWC = {c['des']: c for c in NEW_COMPS}
PWR = [300]
def copy_block(box, dx, dy, ren, netmap, anode_net):
    """Copia os componentes/fios do bloco, deslocados. ren: designador antigo -> novo."""
    add = []
    for r in [r for r in sch if in_box(r, *box)]:
        if r[0] == 'COMPONENT':
            attrs = {a[3]: a[4] for a in BY.get(r[1], [])}
            des = attrs.get('Designator')
            if des in ren:
                new = NEWC[ren[des]]; cid = new['sch']
            else:
                cid = sid()
            c = copy.deepcopy(r); c[1] = cid; c[3] += dx; c[4] += dy; add.append(c)
            for a in BY.get(r[1], []):
                a = copy.deepcopy(a); a[1] = sid(); a[2] = cid
                if a[7] is not None: a[7] += dx; a[8] += dy
                if a[3] == 'Designator':
                    if des in ren: a[4] = ren[des]
                    elif str(des).startswith('#PWR'): a[4] = f'#PWR0{PWR[0]}'; PWR[0] += 1
                if a[3] == 'Unique ID' and des in ren: a[4] = NEWC[ren[des]]['uid']
                add.append(a)
        elif r[0] == 'WIRE':
            w = copy.deepcopy(r); w[1] = sid(); w[2] = [[v + (dx if i % 2 == 0 else dy) for i, v in enumerate(p)] for p in r[2]]
            add.append(w)
            ats = BY.get(r[1], [])
            for a in ats:
                a = copy.deepcopy(a); a[1] = sid(); a[2] = w[1]
                if a[3] == 'NET': a[4] = netmap.get(a[4], a[4])
                if a[7] is not None: a[7] += dx; a[8] += dy
                add.append(a)
            if not ats and anode_net:      # fio sem nome entre o 220 e o anodo: dá o nome usado na PCB
                p = w[2][0]
                add.append(['ATTR', sid(), w[1], 'NET', anode_net, 0, 0, p[0], p[1], 0, 'st14', 0])
    return add
def cap_block(rx, ry, des, net):
    """Capacitor DNP ao lado do 47k (pinos do 47k em ry±20), com fio do sinal e GND."""
    tpl = next(r for r in sch if r[0] == 'COMPONENT' and r[1] == 'e14')
    gtpl = next(r for r in sch if r[0] == 'COMPONENT' and r[1] == 'e51')
    new = NEWC[des]; cx = rx + 40
    add = [['COMPONENT', new['sch'], tpl[2], cx, ry, 270, 0, {}, 0]]
    for a in BY['e14']:
        a = copy.deepcopy(a); a[1] = sid(); a[2] = new['sch']
        v = {'Designator': des, 'Name': '10nF', 'Value': '10nF', 'Unique ID': new['uid'], 'DNP': CAP_DNP[des],
             'Description': CAP_DESC[des], 'Encapsulamento': '0603'}
        if a[3] in v: a[4] = v[a[3]]
        if a[3] == 'Designator': a[7], a[8] = cx + 10, ry + 5
        if a[3] == 'Name': a[7], a[8] = cx + 10, ry - 5
        add.append(a)
    gid = sid(); add.append(['COMPONENT', gid, gtpl[2], cx, ry - 30, 0, 0, {}, 0])
    for a in BY['e51']:
        a = copy.deepcopy(a); a[1] = sid(); a[2] = gid
        if a[7] is not None: a[7] += cx - 345; a[8] += ry - 30 - 395
        if a[3] == 'Designator': a[4] = f'#PWR0{PWR[0]}'; PWR[0] += 1
        add.append(a)
    for pts, n in (([cx, ry + 20, rx, ry + 20], net), ([cx, ry - 20, cx, ry - 30], 'GND')):
        wid = sid(); add.append(['WIRE', wid, [pts], 'st13', 0])
        add.append(['ATTR', sid(), wid, 'NET', n, 0, 1 if n != 'GND' else 0, pts[0], pts[1], 0, 'st14', 0])
    return add
SCH_ADD = []
SCH_ADD += copy_block((140, 360, 385, 485), 330, -30, {'S1': 'S3', 'R4': 'R23', 'R5': 'R24'}, {'MARK_L_A5': 'MARK_L2_D8'}, 'QRE_E1_A')
SCH_ADD += cap_block(345 + 330, 425 - 30, 'C19', 'MARK_L2_D8')
SCH_ADD += copy_block((140, 360, 245, 345), 330, -20, {'S2': 'S4', 'R7': 'R25', 'R8': 'R26'}, {'MARK_R_A6': 'MARK_R2_D9'}, 'QRE_D1_A')
SCH_ADD += cap_block(345 + 330, 285 - 20, 'C20', 'MARK_R2_D9')
for y, n in ((920, 'MARK_L2_D8'), (910, 'MARK_R2_D9')):          # pinos 12 (PB0) e 13 (PB1) do ATmega
    wid = sid(); SCH_ADD += [['WIRE', wid, [[765, y, 745, y]], 'st13', 0], ['ATTR', sid(), wid, 'NET', n, 0, 1, 765, y, 0, 'st17', 0]]
SCH_ADD.append(['TEXT', sid(), 560, 520, 0, 'E1/D1 internos (D8/D9) - asa de gaivota', 'st12'])
sch_out = sch + SCH_ADD

def write_epro(dst=DST):
    tmp = tempfile.mkdtemp(prefix='v4_'); write(tmp)
    pj = json.load(open(os.path.join(tmp, 'project.json'), encoding='utf-8'))
    pj['config']['title'] = 'RUSH - SATURN - v4 (asa de gaivota)'
    json.dump(pj, open(os.path.join(tmp, 'project.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    with zipfile.ZipFile(SRC) as zi, zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zo:
        for info in zi.infolist():
            if info.is_dir(): zo.writestr(info, b''); continue
            zo.writestr(info.filename, open(os.path.join(tmp, info.filename), 'rb').read())
    return dst

def write(dst):
    if os.path.exists(dst): shutil.rmtree(dst)
    shutil.copytree(ORIG, dst)
    for rel, rows in ((PCBF, pcb), (SCHF, sch_out)):
        with open(os.path.join(dst, rel), 'w', encoding='utf-8', newline='\n') as f:
            for r in rows: f.write(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n')

if __name__ == '__main__':
    print('componentes movidos:', moved)
    print('trilhas removidas (cruzavam do corpo para a aba antiga):'); [print('  ', x) for x in removed]
    print('arquivo:', write_epro())
