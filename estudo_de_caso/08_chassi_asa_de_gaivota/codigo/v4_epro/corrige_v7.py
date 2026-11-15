"""Correções no arquivo v7 do Erick (13/11/2026): erros do DRC, GND na placa toda e furo de 1 mm nos motores.

Uso: python3 corrige_v7.py <entrada.epro> <saida.epro>
Baseado no EVA-RT, (c) EXOTIC TEAM MX, AGPL-3.0.
"""
import sys, os, json, math, zipfile, re, collections
from shapely.geometry import LineString, Point
from shapely.ops import unary_union, nearest_points
from shapely.strtree import STRtree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check, angulos, route as R, verifica_placa as V
M = 0.0254
mil = lambda v: v / M
SRC, DST = sys.argv[1], sys.argv[2]
W_MIN = 0.25                      # regra do arquivo (copperThickness1oz): trilha de 0,25 mm a 3 mm
POUR_CLR, POUR_EDGE = 0.35, 0.35  # medido no cobre que o EasyEDA gravou no v7
MOTOR_FP, FURO_MOTOR = '9a3f054adb3bf538', 1.0

z = zipfile.ZipFile(SRC)
PCBN = [n for n in z.namelist() if n.endswith('.epcb')][0]
rows = [json.loads(l) for l in z.read(PCBN).decode('utf-8-sig').splitlines() if l.strip()]
fps = {n.split('/')[1][:-5]: [json.loads(l) for l in z.read(n).decode('utf-8-sig').splitlines() if l.strip()]
       for n in z.namelist() if n.endswith('.efoo')}
outer = V.board(SRC)[2]
inner = outer.buffer(-0.3)
n_id = max(int(r[1][1:]) for r in rows if len(r) > 1 and isinstance(r[1], str) and re.fullmatch(r'e\d+', r[1]))
def nid():
    global n_id
    n_id += 1; return f'e{n_id}'
def line(net, L, pts, w):
    for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):
        if math.hypot(x2 - x1, y2 - y1) < 1e-4: continue
        rows.append(['LINE', nid(), 0, net, L, round(mil(x1), 4), round(mil(y1), 4), round(mil(x2), 4), round(mil(y2), 4), round(mil(w), 4), 0])
def via(net, x, y, d=0.6, h=0.3):
    rows.append(['VIA', nid(), 0, net, '', round(mil(x), 4), round(mil(y), 4), round(mil(h), 4), round(mil(d), 4), 0, None, None, 0, []])
def obstacles(net, L, skip=()):
    gs = [g for l, n, g, i in check.copper(rows, fps) if l == L and n != net and i not in skip]
    return STRtree(gs), gs
def free(geom, net, L, clr=0.2, skip=()):
    t, gs = obstacles(net, L, skip)
    b = geom.buffer(clr)
    return inner.contains(geom) and not any(gs[k].intersects(b) for k in t.query(b))
log = []

# 1) furo dos pads dos motores: 0,9 → 1,0 mm (footprint MOTOR_1020_2P, usado por M1, M2 e M3)
fp_rows = fps[MOTOR_FP]
for p in fp_rows:
    if p[0] == 'PAD' and p[9][0] == 'ROUND':
        old = p[9][1] * M; p[9][1] = p[9][2] = round(mil(FURO_MOTOR), 4)
log.append(f'furo dos motores: {old:.2f} → {FURO_MOTOR:.2f} mm (pad oval 3,0 × 2,0 mm mantido)')

# 2) trilhas abaixo de 0,25 mm → 0,25 mm (Physical Error)
for r in rows:
    if r[0] == 'LINE' and r[4] in (1, 2) and r[9] * M < W_MIN - 1e-4:
        g = LineString([(r[5] * M, r[6] * M), (r[7] * M, r[8] * M)]).buffer(W_MIN / 2)
        okk = free(g, r[3], r[4])
        log.append(f"largura {r[3]} {r[1]}: {r[9] * M:.2f} → {W_MIN} mm" + ('' if okk else ' (FOLGA < 0,2!)'))
        r[9] = round(mil(W_MIN), 4)

# 3) MARK_L2_D8: R24.1 (e290:1) e C19.2 (e294:2) estavam sem ligação na face de baixo
line('MARK_L2_D8', 2, [(-46.17, 6.6), (-43.6, 6.6)], W_MIN)
log.append('E1: ligação R24.1 → C19 (face de baixo, y = 6,6)')

# 3b) E1 junto ao ATmega: a via e1300 e a trilha de baixo e965/e1112 fechavam o GND dos pads de gravação (e85:2).
#     A troca de face passa para (3,96; −27,465), na linha do pino 12 (45°), e a trilha de cima vai direto ao pad.
DROP = {'e1112', 'e965', 'e966', 'e1300', 'e934', 'e1164', 'e935', 'e1165'}
rows[:] = [r for r in rows if not (isinstance(r[1], str) and r[1] in DROP)]
VE1 = (3.82, -27.38)
for r in rows:
    if r[0] == 'LINE' and r[1] == 'e1111': r[7], r[8] = round(mil(3.96), 4), round(mil(-27.52), 4)
line('MARK_L2_D8', 2, [(3.96, -27.52), VE1], W_MIN)
assert free(LineString([(3.96, -27.52), VE1]).buffer(W_MIN / 2), 'MARK_L2_D8', 2), 'trilha E1 face de baixo'
via('MARK_L2_D8', *VE1)
line('MARK_L2_D8', 1, [VE1, (2.82, -26.38)], W_MIN)
for L in (1, 2):
    assert free(Point(VE1).buffer(0.3), 'MARK_L2_D8', L), ('via E1', L)
assert free(LineString([VE1, (2.82, -26.38)]).buffer(W_MIN / 2), 'MARK_L2_D8', 1), 'trilha E1 face de cima'
pads_other = [g for l, n, g, i in check.pad_geoms(rows, fps) if i != 'e238:12']
assert min(g.distance(Point(VE1)) for g in pads_other) >= 0.3 + 0.2 and \
       next(g for l, n, g, i in check.pad_geoms(rows, fps) if i == 'e238:12').distance(Point(VE1)) >= 0.5, 'via E1 perto de pad'
log.append(f'E1: troca de face no pino 12 passa para {VE1} (sai a via e1300 e a trilha que fechava o GND do conector de gravação)')

# 4) MARK_R2_D9: o trecho de baixo passava sobre o pad do rasgo traseiro direito (e311) → refaz
CUT = {'e1148', 'e1149', 'e1150', 'e1151', 'e1152', 'e1153', 'e1154'}
rows[:] = [r for r in rows if not (r[0] == 'LINE' and r[1] in CUT)]
# rota: desce em 45° da borda direita e passa ACIMA do rasgo, entre LEDB_D7 (y −26,64) e B1_D11 (y −25,58),
# entrando em 45° na via e1310 (10,55; −27,17), que já leva ao pino 13 pela face de cima.
D9 = [(39.37, -15.37), (28.69, -26.05), (11.67, -26.05), (10.55, -27.17)]
for p, q in zip(D9, D9[1:]):
    g = LineString([p, q]).buffer(W_MIN / 2)
    assert free(g, 'MARK_R2_D9', 2), ('folga', p, q)
line('MARK_R2_D9', 2, D9, W_MIN)
log.append('D1: MARK_R2_D9 refeito na face de baixo, acima do rasgo: ' + ' → '.join(f'({x:.2f}; {y:.2f})' for x, y in D9))

# 5) acabamento a 45°: chanfro dos cantos ≤ 90° e "dogleg" dos trechos fora de 0/45/90°
def chamfer_all():
    for it in range(40):
        cs = angulos.corners(rows, fps)
        if not cs: return
        c = cs[0]; done = False
        (k1, s1), (k2, s2) = c['segs']
        r1, r2 = rows[k1], rows[k2]
        V0 = (c['x'], c['y'])
        far = lambda r, s: (r[7] * M, r[8] * M) if s == 'a' else (r[5] * M, r[6] * M)
        F1, F2 = far(r1, s1), far(r2, s2)
        w = max(r1[9], r2[9]) * M
        for cc in (0.6, 0.45, 0.3, 0.2):
            ce = min(cc, c['la'], c['lb'])
            at = lambda F, l: (V0[0] + (F[0] - V0[0]) * ce / l, V0[1] + (F[1] - V0[1]) * ce / l)
            P1, P2 = at(F1, c['la']), at(F2, c['lb'])
            seg = LineString([P1, P2])
            if free(seg.buffer(w / 2), c['net'], c['layer']):
                for r, s, P in ((r1, s1, P1), (r2, s2, P2)):
                    if s == 'a': r[5], r[6] = round(mil(P[0]), 4), round(mil(P[1]), 4)
                    else: r[7], r[8] = round(mil(P[0]), 4), round(mil(P[1]), 4)
                line(c['net'], c['layer'], [P1, P2], w)
                rows[:] = [r for r in rows if not (r[0] == 'LINE' and abs(r[5] - r[7]) < 1e-3 and abs(r[6] - r[8]) < 1e-3)]
                log.append(f"chanfro 45° {c['net']} face {c['layer']} ({c['x']:.2f}; {c['y']:.2f})"); done = True; break
        if not done:
            log.append(f"NÃO chanfrado: {c['net']} ({c['x']:.2f}; {c['y']:.2f})"); return
def off45(r):
    dx, dy = (r[7] - r[5]) * M, (r[8] - r[6]) * M
    if math.hypot(dx, dy) < 0.3: return False
    a = math.degrees(math.atan2(dy, dx)) % 45
    return min(a, 45 - a) > 2
def dogleg_all():
    for r in [r for r in rows if r[0] == 'LINE' and r[4] in (1, 2) and off45(r)]:
        A = (r[5] * M, r[6] * M); Bp = (r[7] * M, r[8] * M)
        dx, dy = Bp[0] - A[0], Bp[1] - A[1]
        d = min(abs(dx), abs(dy)); sx, sy = math.copysign(1, dx), math.copysign(1, dy)
        before = len(angulos.corners(rows, fps)); ok = False
        for K in ((A[0] + sx * d, A[1] + sy * d), (Bp[0] - sx * d, Bp[1] - sy * d)):
            sg = [LineString([A, K]), LineString([K, Bp])]
            if all(free(s.buffer(r[9] * M / 2), r[3], r[4], skip=(r[1],)) for s in sg):
                old = list(r)
                r[7], r[8] = round(mil(K[0]), 4), round(mil(K[1]), 4)
                rows.append(['LINE', nid(), 0, r[3], r[4], r[7], r[8], round(mil(Bp[0]), 4), round(mil(Bp[1]), 4), r[9], 0])
                if len(angulos.corners(rows, fps)) > before: rows.pop(); r[:] = old; continue
                ok = True; log.append(f'45°: {r[3]} ({A[0]:.2f}; {A[1]:.2f})→({Bp[0]:.2f}; {Bp[1]:.2f})'); break
        if not ok: log.append(f'mantido fora de 45°: {r[3]} ({A[0]:.2f}; {A[1]:.2f})→({Bp[0]:.2f}; {Bp[1]:.2f})')

# 6) GND na placa toda: simula o "reconstruir cobre" e põe vias de GND nas ilhas que o EasyEDA apagaria
import plano_gnd
POUR_CLR, POUR_EDGE = plano_gnd.POUR_CLR, plano_gnd.POUR_EDGE
def pour_pieces(): return plano_gnd.pieces(rows, fps, outer)
def stitch(min_area=2.0, via_d=0.6):
    added = []
    for _ in range(120):
        cu, pcs, f, main = pour_pieces()
        isl = sorted([(p.area, L, p) for k, (L, p) in enumerate(pcs) if f(k) != main and p.area >= min_area], key=lambda t: -t[0])
        if not isl: break
        pads = unary_union([g for l, n, g, i in check.pad_geoms(rows, fps)])
        hs = unary_union(check.holes(rows))
        vias_g = unary_union([Point(r[5] * M, r[6] * M).buffer(r[8] * M / 2) for r in rows if r[0] == 'VIA'])
        placed = False
        for a, L, p in isl:
            mainp = unary_union([q for k, (LL, q) in enumerate(pcs) if LL == 3 - L and f(k) == main])
            cand = p.buffer(-0.16).intersection(mainp.buffer(-0.16))   # via a ≥ 0,2 mm do cobre de outras redes
            cand = cand.difference(pads.buffer(via_d / 2 + 0.2)).difference(hs.buffer(via_d / 2 + 0.4)) \
                       .difference(vias_g.buffer(via_d / 2 + 0.3)).intersection(outer.buffer(-(0.4 + via_d / 2)))
            if cand.is_empty: continue
            q = nearest_points(cand, p.representative_point())[0]
            if not all(free(Point(q.x, q.y).buffer(via_d / 2), 'GND', LL) for LL in (1, 2)): continue
            via('GND', q.x, q.y); added.append((L, round(a, 1), round(q.x, 2), round(q.y, 2))); placed = True; break
        if not placed: break
    cu, pcs, f, main = pour_pieces()
    left = [(L, round(p.area, 1), round(p.centroid.x, 1), round(p.centroid.y, 1)) for k, (L, p) in enumerate(pcs) if f(k) != main and p.area >= min_area]
    lost = [(l, i) for l, nn, g, i in cu if nn == 'GND' and not any(f(k) == main for k, (L, p) in enumerate(pcs) if L == l and p.intersects(g))]
    return added, left, lost
added, left, lost = stitch()
# itens de GND que nenhuma via resolve: trilha de GND (roteador) até o plano principal
R.W, R.CLR, R.EDGE, R.VIA_COST = W_MIN, 0.21, 0.35, 80
gnd_routes = []
for _ in range(6):
    cu, pcs, f, main = pour_pieces()
    lost = [(l, i, g) for l, nn, g, i in cu if nn == 'GND' and not any(f(k) == main for k, (L, p) in enumerate(pcs) if L == l and p.intersects(g))]
    if not lost: break
    l, i, g = lost[0]
    src = [(LL, gg) for LL, nn, gg, ii in cu if ii == i]
    dst = [(L, p.buffer(-0.2)) for k, (L, p) in enumerate(pcs) if f(k) == main and p.distance(g) < 8 and p.area > 3]
    dst = [(L, p) for L, p in dst if not p.is_empty]
    tgt = nearest_points(unary_union([p for L, p in dst]), g.centroid)[0]
    segs, nexp = R.route(rows, fps, outer, 'GND', src, dst, (tgt.x, tgt.y))
    if not segs:
        gnd_routes.append((i, 'sem rota')); break
    for k, (L, pts) in enumerate(segs):
        if k: via('GND', *pts[0])
        line('GND', L, pts, W_MIN)
    gnd_routes.append((i, [(L, [(round(x, 2), round(y, 2)) for x, y in p]) for L, p in segs]))
log.append(f'trilhas de GND acrescentadas: {gnd_routes}')
added2, left, lost = stitch()
added += added2
chamfer_all(); dogleg_all(); chamfer_all()
cu, pcs, f, main = pour_pieces()
left = [(L, round(p.area, 1), round(p.centroid.x, 1), round(p.centroid.y, 1)) for k, (L, p) in enumerate(pcs) if f(k) != main and p.area >= 2]
lost = [(l, i) for l, nn, g, i in cu if nn == 'GND' and not any(f(k) == main for k, (L, p) in enumerate(pcs) if L == l and p.intersects(g))]
log.append(f'vias de GND acrescentadas: {len(added)} → ' + '; '.join(f'face {L} ilha {a} mm² em ({x}; {y})' for L, a, x, y in added))
log.append(f'ilhas ≥ 2 mm² ainda sem GND: {left}')
log.append(f'itens de GND fora do plano principal: {lost}')

# 7) apaga o cobre antigo (POURED): o EasyEDA refaz com Shift+B
npd = sum(1 for r in rows if r[0] == 'POURED')
rows[:] = [r for r in rows if r[0] != 'POURED']
log.append(f'{npd} linhas POURED apagadas (refazer o cobre no EasyEDA)')

with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zo:
    for info in z.infolist():
        if info.is_dir(): zo.writestr(info, b''); continue
        data = z.read(info.filename)
        if info.filename == PCBN:
            data = ''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n' for r in rows).encode('utf-8')
        elif info.filename == f'FOOTPRINT/{MOTOR_FP}.efoo':
            data = ''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n' for r in fp_rows).encode('utf-8')
        zo.writestr(info, data)
print('\n'.join(log)); print('arquivo:', DST)
