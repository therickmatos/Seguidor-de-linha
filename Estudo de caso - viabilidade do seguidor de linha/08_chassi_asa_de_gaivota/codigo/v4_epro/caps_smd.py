"""C1/C2 SMD (220 µF 6,3 × 7,7) no lugar dos radiais: posição, via de VBAT e checagens.

Os radiais antigos faziam a passagem de face do VBAT pelo próprio furo (pad Ø1,6, furo 1,0).
Aqui uma via VBAT de 1,6/1,0 mm fica exatamente no lugar desse pad, para não mexer nas trilhas.
O capacitor SMD vai na face de cima, na posição livre mais próxima da antiga, com o pad + tocando
o cobre de VBAT de cima já existente.

Uso: python3 caps_smd.py <entrada.epro> <saida.epro>
Baseado no EVA-RT, (c) EXOTIC TEAM MX, AGPL-3.0.
"""
import sys, os, json, math, zipfile, re, copy, pickle
import numpy as np
from shapely.geometry import Point, LineString, box
from shapely.ops import unary_union
from shapely import affinity
from shapely.strtree import STRtree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check, verifica_placa as V, plano_gnd as G
M = 0.0254
mil = lambda v: v / M
SRC, DST = sys.argv[1], sys.argv[2]
z = zipfile.ZipFile(SRC)
PCBN = [n for n in z.namelist() if n.endswith('.epcb')][0]
rows = [json.loads(l) for l in z.read(PCBN).decode('utf-8-sig').splitlines() if l.strip()]
fps = {n.split('/')[1][:-5]: [json.loads(l) for l in z.read(n).decode('utf-8-sig').splitlines() if l.strip()]
       for n in z.namelist() if n.endswith('.efoo')}
outer = V.board(SRC)[2]
inner = outer.buffer(-0.35)
n_id = max(int(r[1][1:]) for r in rows if len(r) > 1 and isinstance(r[1], str) and re.fullmatch(r'e\d+', r[1]))
def nid():
    global n_id
    n_id += 1; return f'e{n_id}'
comp = {r[1]: r for r in rows if r[0] == 'COMPONENT'}
des = {r[3]: r[8] for r in rows if r[0] == 'ATTR' and r[3] in comp and r[7] == 'Designator'}
inv = {v: k for k, v in des.items()}
log = []

# posição dos pads dos radiais antigos (v8): VBAT = passagem de face
OLD = {'C1': dict(vbat=(-20.447, 1.27), gnd=(-22.987, 1.27)),
       'C2': dict(vbat=(20.574, 1.016), gnd=(20.574, 3.556))}
VIA_D, VIA_H = 1.6, 1.0
for d, o in OLD.items():
    rows.append(['VIA', nid(), 0, 'VBAT', '', round(mil(o['vbat'][0]), 4), round(mil(o['vbat'][1]), 4),
                 round(mil(VIA_H), 4), round(mil(VIA_D), 4), 0, None, None, 1, []])
    log.append(f"{d}: via VBAT {VIA_D}/{VIA_H} mm no lugar do pad + do radial, em {o['vbat']}")

p11 = None
try:
    p11 = pickle.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'carcaca_ate_8mm.pkl'), 'rb'))
except Exception:
    pass

_cache = {}
def pads_at(cid, x, y, rot, commit=False):
    r = comp[cid]
    if commit:
        r[4], r[5], r[6] = round(mil(x), 4), round(mil(y), 4), rot
        return [(l, n, g, i) for l, n, g, i in check.pad_geoms(rows, fps) if i.startswith(cid + ':')]
    if (cid, rot) not in _cache:
        sv = r[4:7]; r[4], r[5], r[6] = 0, 0, rot
        _cache[(cid, rot)] = [(l, n, g, i) for l, n, g, i in check.pad_geoms(rows, fps) if i.startswith(cid + ':')]
        r[4], r[5], r[6] = sv
    return [(l, n, affinity.translate(g, x, y), i) for l, n, g, i in _cache[(cid, rot)]]
BODY = box(-3.3, -3.3, 3.3, 3.3)
def body_at(x, y, rot):
    return affinity.translate(affinity.rotate(BODY, rot, origin=(0, 0)), x, y)

CLR = 0.2          # regra do arquivo
W_VBAT = 1.0       # trilha nova de VBAT (pad + → via), se o pad não encostar no VBAT de cima
def place(d):
    cid = inv[d]; o = OLD[d]
    others = [c for c in check.copper(rows, fps) if not str(c[3]).startswith(cid + ':')]
    top = [(n, g, i) for l, n, g, i in others if l == 1]
    t_vbat = unary_union([g for n, g, i in top if n == 'VBAT'])
    tree = STRtree([g for n, g, i in top]); tg = [(n, g) for n, g, i in top]
    def clear(g, net):
        sb = g.buffer(CLR)
        return not any(tg[k][0] != net and tg[k][1].intersects(sb) for k in tree.query(sb))
    hulls = {}
    for l, n, g, i in check.pad_geoms(rows, fps):
        c = i.split(':')[0]
        if c != cid and c in comp and comp[c][3] == 1: hulls.setdefault(c, []).append(g)
    occ = unary_union([unary_union(v).convex_hull.buffer(0.2) for v in hulls.values()])
    holes = unary_union(check.holes(rows))
    vias = [Point(r[5] * M, r[6] * M) for r in rows if r[0] == 'VIA']
    via = Point(o['vbat'])
    best = None
    x0, y0 = (o['vbat'][0] + o['gnd'][0]) / 2, (o['vbat'][1] + o['gnd'][1]) / 2
    for rot in range(0, 360, 45):
        for dx in np.arange(-7, 7.01, 0.254):
            for dy in np.arange(-7, 7.01, 0.254):
                x, y = x0 + dx, y0 + dy
                b = body_at(x, y, rot)
                if not inner.contains(b) or b.intersects(occ) or b.distance(holes) < 0.3: continue
                if p11 is not None and b.intersects(p11): continue
                ps = pads_at(cid, x, y, rot)
                if not all(clear(g, n) for l, n, g, i in ps): continue
                if any(g.buffer(0.3).intersects(occ) for l, n, g, i in ps): continue   # ≥ 0,5 mm dos pads vizinhos (solda à mão)
                if any(v.distance(g) < VIA_H / 2 + 0.15 for l, n, g, i in ps for v in vias): continue
                gp = next(g for l, n, g, i in ps if n == 'GND')
                if gp.distance(via) < VIA_D / 2 + CLR: continue
                vb = next(g for l, n, g, i in ps if n == 'VBAT')
                trace = None
                if not vb.intersects(t_vbat):
                    c = vb.centroid
                    tr = LineString([(c.x, c.y), (via.x, via.y)])
                    tb = tr.buffer(W_VBAT / 2)
                    if not clear(tb, 'VBAT') or tb.distance(gp) < CLR: continue
                    ang = math.degrees(math.atan2(via.y - c.y, via.x - c.x)) % 45
                    if min(ang, 45 - ang) > 0.5: continue          # só 0/45/90°
                    trace = [(c.x, c.y), (via.x, via.y)]
                score = math.hypot(dx, dy) + (LineString(trace).length * 0.5 + 1 if trace else 0)
                if best is None or score < best[0]: best = (score, x, y, rot, trace)
    return best

for d in ('C1', 'C2'):
    b = place(d)
    assert b, f'{d}: sem posição'
    s, x, y, rot, trace = b
    pads_at(inv[d], x, y, rot, commit=True)
    if trace:
        (x1, y1), (x2, y2) = trace
        rows.append(['LINE', nid(), 0, 'VBAT', 1, round(mil(x1), 4), round(mil(y1), 4), round(mil(x2), 4), round(mil(y2), 4), round(mil(W_VBAT), 4), 0])
        log.append(f'{d}: trilha VBAT de {W_VBAT} mm do pad + até a via ({LineString(trace).length:.2f} mm)')
    # contato pad + × VBAT de cima: se for só de raspão, trilha horizontal de 1 mm do pad até a via
    cid = inv[d]
    cu = check.copper(rows, fps)
    vb = next(g for l, n, g, i in cu if i.startswith(cid + ':') and n == 'VBAT')
    tv = unary_union([g for l, n, g, i in cu if l == 1 and n == 'VBAT' and not str(i).startswith(cid + ':')])
    if vb.intersection(tv).area < 0.5:
        vx, vy = OLD[d]['vbat']
        seg = LineString([(vx - 6, vy), (vx, vy)]).intersection(vb.buffer(-0.3))
        assert not seg.is_empty, f'{d}: pad + não cruza a horizontal da via'
        px = min(c[0] for c in seg.coords)
        tr = LineString([(px, vy), (vx, vy)])
        others = [g for l, n, g, i in cu if l == 1 and n != 'VBAT']
        assert not any(g.intersects(tr.buffer(W_VBAT / 2 + CLR)) for g in others), f'{d}: trilha VBAT sem folga'
        rows.append(['LINE', nid(), 0, 'VBAT', 1, round(mil(px), 4), round(mil(vy), 4), round(mil(vx), 4), round(mil(vy), 4), round(mil(W_VBAT), 4), 0])
        log.append(f'{d}: trilha VBAT de {W_VBAT} mm, ({px:.2f}; {vy:.2f}) → via ({vx:.2f}; {vy:.2f})')
    # designador: logo acima do corpo
    for r in rows:
        if r[0] == 'ATTR' and r[3] == inv[d] and r[7] == 'Designator':
            r[5], r[6] = round(mil(x), 4), round(mil(y + 4.4), 4)
    log.append(f'{d}: SMD em ({x:.2f}; {y:.2f}), rotação {rot}°, {s:.2f} mm do centro antigo')

# GND: os pads PTH antigos também ligavam o GND das duas faces. Via de GND junto ao pad − de cada capacitor.
GV_D, GV_H = 0.8, 0.4
def gnd_via(d):
    cid = inv[d]
    cu = check.copper(rows, fps)
    gp = next(g for l, n, g, i in cu if i.startswith(cid + ':') and n == 'GND')
    pads = unary_union([g for l, n, g, i in check.pad_geoms(rows, fps)])
    holes = unary_union(check.holes(rows))
    vias = [Point(r[5] * M, r[6] * M) for r in rows if r[0] == 'VIA']
    obst = {L: [g for l, n, g, i in cu if l == L and n != 'GND'] for L in (1, 2)}
    trees = {L: STRtree(obst[L]) for L in (1, 2)}
    best = None
    c = gp.centroid
    for ang in range(0, 360, 15):
        for rr in np.arange(0.5, 3.0, 0.1):
            p = Point(c.x + rr * math.cos(math.radians(ang)), c.y + rr * math.sin(math.radians(ang)))
            v = p.buffer(GV_D / 2)
            if not v.intersects(gp.buffer(0.05)) and v.distance(gp) > 0.4: continue      # encostada no pad −
            if p.distance(pads) < GV_H / 2 + 0.15: continue                                 # furo fora de pad
            if v.difference(gp).area < 1e-6: continue
            if not inner.contains(v) or v.distance(holes) < 0.3 or any(p.distance(q) < GV_D + 0.2 for q in vias): continue
            ok = all(not any(obst[L][k].intersects(v.buffer(CLR)) for k in trees[L].query(v.buffer(CLR))) for L in (1, 2))
            if ok:
                sc = v.distance(gp) + 0.1 * rr
                if best is None or sc < best[0]: best = (sc, p)
    assert best, f'{d}: sem lugar para via de GND'
    p = best[1]
    rows.append(['VIA', nid(), 0, 'GND', '', round(mil(p.x), 4), round(mil(p.y), 4), round(mil(GV_H), 4), round(mil(GV_D), 4), 0, None, None, 1, []])
    if not Point(p).buffer(GV_D / 2).intersects(gp):
        q = nearest = gp.exterior.interpolate(gp.exterior.project(p))
        rows.append(['LINE', nid(), 0, 'GND', 1, round(mil(p.x), 4), round(mil(p.y), 4), round(mil(q.x), 4), round(mil(q.y), 4), round(mil(0.5), 4), 0])
    log.append(f'{d}: via de GND {GV_D}/{GV_H} mm junto ao pad −, em ({p.x:.2f}; {p.y:.2f})')
for d in ('C1', 'C2'): gnd_via(d)
cu, pcs, f, main = G.pieces(rows, fps, outer)
lost = [i for l, nn, g, i in cu if nn == 'GND' and not any(f(k) == main for k, (L, p) in enumerate(pcs) if L == l and p.intersects(g))]
log.append(f'GND fora do plano (simulado): {lost}')

# C20 passa a montado (PCB); o esquemático é ajustado abaixo
DESC20 = 'filtro RC com o 47k (trilha do pino 13), igual ao C19; ver PINOS.md'
for r in rows:
    if r[0] == 'COMPONENT' and des.get(r[1]) == 'C20' and isinstance(r[7], dict):
        if 'DNP' in r[7]: r[7]['DNP'] = 'no'; log.append('C20: DNP → no (PCB)')
        if 'Description' in r[7]: r[7]['Description'] = DESC20
    if r[0] == 'ATTR' and des.get(r[3]) == 'C20' and r[7] == 'DNP':
        r[8] = 'no'; log.append('C20: DNP → no (atributo da PCB)')

with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zo:
    for info in z.infolist():
        if info.is_dir(): zo.writestr(info, b''); continue
        data = z.read(info.filename)
        if info.filename == PCBN:
            data = ''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n' for r in rows).encode('utf-8')
        elif info.filename.endswith('.esch'):
            lines = [json.loads(l) for l in data.decode('utf-8-sig').splitlines() if l.strip()]
            c20 = [r[2] for r in lines if r[0] == 'ATTR' and r[3] == 'Designator' and r[4] == 'C20']
            for r in lines:
                if r[0] == 'ATTR' and r[2] in c20 and r[3] == 'DNP' and r[4] != 'no':
                    r[4] = 'no'; log.append('C20: DNP → no (esquemático)')
                if r[0] == 'ATTR' and r[2] in c20 and r[3] == 'Description':
                    r[4] = DESC20
            data = ''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n' for r in lines).encode('utf-8')
        zo.writestr(info, data)
print('\n'.join(log)); print('arquivo:', DST)
