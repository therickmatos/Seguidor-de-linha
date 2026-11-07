# Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""Revisao de um .epro (formato EasyEDA Pro 2) contra a referencia: posicoes, mecanica, folgas, distancias."""
import sys, json, math, collections
sys.path.insert(0, '/home/user/Seguidor-de-linha/ferramentas/preview')
import easyeda_posicionar as E, placa_v2 as V, footprints as F, layout_placa as M
from shapely.geometry import Point, LineString
entrada = sys.argv[1]
z, dados = E.ler_epro(entrada)
pcb_nome = next(n for n in dados if n.startswith('PCB/') and n.endswith('.epcb'))
pcb = E.linhas_json(dados[pcb_nome])
print('tipos no PCB:', dict(collections.Counter(r[0] for r in pcb)))
attr = collections.defaultdict(dict)
for r in pcb:
    if r[0] == 'ATTR': attr[r[3]][r[7]] = r[8]
comps = {}
for r in pcb:
    if r[0] == 'COMPONENT':
        des = attr[r[1]].get('Designator')
        comps[des] = (r[1], r[4]*E.MIL, r[5]*E.MIL, r[6], r[3] == 2, E.pads_footprint(dados, attr[r[1]]['Footprint']))
ref = E.referencia()
print('\n== desvio de cada peca em relacao a referencia (mm, maior pad) ==')
mud = []
for des, (cid, x, y, ang, baixo, fp) in comps.items():
    dev = max(math.dist(E.transformar(fp[p][0]['x'], fp[p][0]['y'], x, y, ang, baixo), ref[des]['pinos'][p][:2]) for p in ref[des]['pinos'] if p in fp)
    if dev > 0.25 or baixo != (ref[des]['face'] == 'BOTTOM'):
        mud.append((round(dev, 2), des, 'FACE!' if baixo != (ref[des]['face'] == 'BOTTOM') else ''))
print(sorted(mud, reverse=True))
novo = {cid: (x, y, ang, baixo, des, fp) for des, (cid, x, y, ang, baixo, fp) in comps.items()}
print('\n== folgas com os footprints do EasyEDA ==', E.conferir(novo) or 'ok')
# mecanica: ajusta nossos footprints aos pads dele e roda as checagens da referencia
pos = V.load(); novo2 = []
for c in pos:
    cid, x, y, ang, baixo, fp = comps[c['ref']]
    ours = F.FOOTPRINTS[c['footprint']]['pads']
    pares = [((p['x'], p['y']), E.transformar(fp[str(p['rede_pino'])][0]['x'], fp[str(p['rede_pino'])][0]['y'], x, y, ang, baixo), str(p['rede_pino'])) for p in ours if str(p['rede_pino']) in fp]
    if c['ref'] == 'U1': pares = [t for t in pares if t[2] in ('1', '3')]
    X, Y, R = E.ajustar([t[0] for t in pares], [t[1] for t in pares], baixo)
    c2 = dict(c); c2['x'], c2['y'], c2['rot'] = X, Y, R; c2['face'] = 'BOTTOM' if baixo else 'TOP'; novo2.append(c2)
print('\n== mecanica (rotor, carcaca, suportes, presilhas, bateria, succao, engrenagem) ==', V.check(novo2) or 'ok')
f = V.folgas_j1(novo2); print('J1:', {k: v for k, v in f.items() if k in ('corpo_suporte', 'corpo_motor', 'corpo_bateria', 'cobre_borda')})
def pad(des, pin):
    cid, x, y, ang, baixo, fp = comps[des]; p = fp[pin][0]; return E.transformar(p['x'], p['y'], x, y, ang, baixo)
def rpad(des, pin): return ref[des]['pinos'][pin][:2]
pares = [('X1','1','U2','7'),('X1','2','U2','8'),('C9','1','X1','1'),('C10','1','X1','2'),('C7','1','U2','18'),
 ('C11','1','U3','11'),('C13','1','U3','11'),('C14','1','U4','11'),('C16','1','U4','11'),
 ('D1','1','M3','1'),('D1','2','M3','2'),('Q1','3','M3','2'),('C17','1','M3','1')]
print('\n== distancias pino a pino: referencia -> arquivo ==')
for a, pa, b, pb in pares:
    r = math.dist(rpad(a, pa), rpad(b, pb)); h = math.dist(pad(a, pa), pad(b, pb))
    print(f'  {a}.{pa}-{b}.{pb}: {r:5.1f} -> {h:5.1f}' + ('  <<' if h > r + 1.5 else ''))
print('J4.1', tuple(round(v, 2) for v in pad('J4', '1')), '(ref', rpad('J4', '1'), ')')
# furos/rasgos
print('\n== furos e rasgos ==')
livres = [r for r in pcb if r[0] == 'PAD']
for r in livres: print('PAD livre', r[5], 'em', round(r[6]*E.MIL, 3), round(r[7]*E.MIL, 3), 'rot', r[8], 'furo', r[9], 'pad', r[10][:3], 'dentro da placa' if M.OUTLINE.contains(Point(r[6]*E.MIL, r[7]*E.MIL)) else 'FORA DA PLACA')
fills = [r for r in pcb if r[0] == 'FILL' and r[4] == 12]
print('furos (FILL multi):', len(fills))
segs = [r for r in pcb if r[0] == 'POLY' and r[4] == 11]
print('segmentos no Board Outline:', len(segs))
for h in M.BOARD_DATA['furos']:
    if h['tipo'] == 'rasgo':
        dentro = [s for s in segs if abs(s[6][1]*E.MIL - h['y']) < 1.0 and abs(s[6][0]*E.MIL - h['x']) < 4]
        print(' rasgo', h['nome'], 'contorno ainda la:', len(dentro), 'segmentos')
print('trilhas:', sum(1 for r in pcb if r[0] == 'LINE'), 'vias:', sum(1 for r in pcb if r[0] == 'VIA'))
