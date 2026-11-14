"""Correções no arquivo do Erick (12/11/2026) e chanfro 45° dos cantos retos.

Entrada: o .epro enviado; saída: ProPrj_RUSH - SATURN - v4_asa_gaivota_2026-11-12.epro (raiz do repositório).
Baseado no EVA-RT, (c) EXOTIC TEAM MX, AGPL-3.0.
"""
import sys, os, json, math, zipfile, tempfile, copy, re
from shapely.geometry import LineString, Point
from shapely.ops import unary_union, nearest_points
from shapely.strtree import STRtree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check, angulos, costura_gnd, verifica_placa as V
M = 0.0254
mil = lambda v: v / M
SRC = sys.argv[1]
REPO = [p for p in __import__('pathlib').Path(__file__).resolve().parents if (p / 'CLAUDE.md').exists()][0]
DST = str(REPO / 'ProPrj_RUSH - SATURN - v4_asa_gaivota_2026-11-12.epro')
z = zipfile.ZipFile(SRC)
PCBN = [n for n in z.namelist() if n.endswith('.epcb')][0]
rows = [json.loads(l) for l in z.read(PCBN).decode('utf-8-sig').splitlines() if l.strip()]
fps = {n.split('/')[1][:-5]: [json.loads(l) for l in z.read(n).decode('utf-8-sig').splitlines() if l.strip()]
       for n in z.namelist() if n.endswith('.efoo')}
outer = V.board(SRC)[2]
n_id = max(int(r[1][1:]) for r in rows if len(r) > 1 and isinstance(r[1], str) and re.fullmatch(r'e\d+', r[1]))
def nid():
    global n_id
    n_id += 1; return f'e{n_id}'
def line(net, L, pts, w):
    for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):
        rows.append(['LINE', nid(), 0, net, L, round(mil(x1), 4), round(mil(y1), 4), round(mil(x2), 4), round(mil(y2), 4), round(mil(w), 4), 0])
def via(net, x, y, d=0.6, h=0.3):
    rows.append(['VIA', nid(), 0, net, '', round(mil(x), 4), round(mil(y), 4), round(mil(h), 4), round(mil(d), 4), 0, None, None, 0, []])
log = []

# 1) E1: S3.4 → R24.1 (trilha que terminava em (−49,3; 7,0)); 45°
line('MARK_L2_D8', 2, [(-49.3, 7.0), (-48.6, 6.3), (-48.47, 6.3)], 0.254); log.append('E1: (−49,3; 7,0) → R24.1')
# 2) D1: S4.1 → R25.2 (trilha que terminava em (46,90; 12,05)); 45°
line('QRE_D1_A', 2, [(46.9, 12.05), (46.26, 11.41), (46.26, 11.31)], 0.254); log.append('D1: (46,90; 12,05) → R25.2')
# 3) C20.2 → MARK_R2_D9 (encontra a trilha em (47,88; 6,35))
line('MARK_R2_D9', 2, [(46.19, 6.33), (46.21, 6.35), (47.88, 6.35)], 0.254); log.append('C20.2 → MARK_R2_D9')
# 5) rótulos
des = {r[3]: r for r in rows if r[0] == 'ATTR' and r[7] == 'Designator'}
for r in rows:
    if r[0] == 'ATTR' and r[7] == 'Designator' and r[8] in ('S1', 'S2', 'S4'):
        x, y = {'S1': (-83.0, 13.75), 'S2': (83.0, 13.75), 'S4': (55.0, 15.6)}[r[8]]
        r[5], r[6] = round(mil(x), 4), round(mil(y), 4); log.append(f'rótulo {r[8]} → ({x}; {y})')

# 4a) MARK_R2_D9: o trecho que atravessava a traseira em y ≈ −26 (face de baixo) isolava o GND do reset (SW1).
#     Passa a descer rente à borda direita e voltar pela borda traseira, em 45°.
CUT = {((39.37, -15.37), (28.70, -26.04)), ((28.70, -26.04), (23.00, -26.04)), ((23.00, -26.04), (22.99, -26.03)),
       ((22.99, -26.03), (22.47, -26.03)), ((22.47, -26.03), (22.47, -26.04)), ((11.69, -26.04), (22.47, -26.04)),
       ((10.55, -27.17), (11.69, -26.04))}
cut = 0
for r in rows:
    if r[0] == 'LINE' and r[3] == 'MARK_R2_D9' and r[4] == 2:
        k = ((round(r[5] * M, 2), round(r[6] * M, 2)), (round(r[7] * M, 2), round(r[8] * M, 2)))
        if k in CUT or k[::-1] in CUT: r[0] = 'APAGAR'; cut += 1
rows[:] = [r for r in rows if r[0] != 'APAGAR']
line('MARK_R2_D9', 2, [(39.37, -15.37), (39.37, -31.6), (38.67, -32.3), (24.3, -32.3), (21.3, -29.3),
                       (11.5, -29.3), (10.55, -28.35), (10.55, -27.17)], 0.254)
log.append(f'MARK_R2_D9: {cut} trechos da traseira trocados por rota rente à borda (face de baixo)')

# 6) cantos retos → chanfro 45°
def obstacles(net, L):
    cu = check.copper(rows, fps)
    gs = [g for l, n, g, i in cu if l == L and n != net]
    return STRtree(gs), gs
inner = outer.buffer(-0.3)
for it in range(10):
    cs = angulos.corners(rows, fps)
    if not cs: break
    c = cs[0]; done = False
    k1, s1 = c['segs'][0]; k2, s2 = c['segs'][1]
    r1, r2 = rows[k1], rows[k2]
    V0 = (c['x'], c['y'])
    def far(r, s): return ((r[7] * M, r[8] * M) if s == 'a' else (r[5] * M, r[6] * M))
    F1, F2 = far(r1, s1), far(r2, s2)
    w = max(r1[9], r2[9]) * M
    tree, gs = obstacles(c['net'], c['layer'])
    for cc in (0.6, 0.45, 0.3, 0.2):
        ce = min(cc, c['la'], c['lb'])          # mesmo recuo nos dois lados: chanfro exato de 45°
        def at(F, l): t = ce / l; return (V0[0] + (F[0] - V0[0]) * t, V0[1] + (F[1] - V0[1]) * t)
        P1, P2 = at(F1, c['la']), at(F2, c['lb'])
        seg = LineString([P1, P2])
        sb = seg.buffer(w / 2 + 0.2)
        if inner.contains(seg) and not any(gs[q].intersects(sb) for q in tree.query(sb)):
            for r, s, P in ((r1, s1, P1), (r2, s2, P2)):
                if s == 'a': r[5], r[6] = round(mil(P[0]), 4), round(mil(P[1]), 4)
                else: r[7], r[8] = round(mil(P[0]), 4), round(mil(P[1]), 4)
            line(c['net'], c['layer'], [P1, P2], w)
            # remove segmentos que ficaram com comprimento zero
            for r in (r1, r2):
                if abs(r[5] - r[7]) < 1e-3 and abs(r[6] - r[8]) < 1e-3: r[0] = 'APAGAR'
            log.append(f"chanfro 45° {c['net']} face {c['layer']} em ({c['x']:.2f}; {c['y']:.2f}), {cc} mm"); done = True; break
    if not done:
        log.append(f"NÃO chanfrado (folga): {c['net']} ({c['x']:.2f}; {c['y']:.2f})"); break
rows[:] = [r for r in rows if r[0] != 'APAGAR']

# 6b) trechos em ângulo quebrado (fora de 0/45/90°) das redes novas → reto + 45° ("dogleg"), se couber
def off45(r):
    dx, dy = (r[7] - r[5]) * M, (r[8] - r[6]) * M
    if math.hypot(dx, dy) < 0.3: return False
    a = math.degrees(math.atan2(dy, dx)) % 45
    return min(a, 45 - a) > 2
for net in sorted({r[3] for r in rows if r[0] == 'LINE' and r[3]}):
    for r in [r for r in rows if r[0] == 'LINE' and r[3] == net and off45(r)]:
        A = (r[5] * M, r[6] * M); Bp = (r[7] * M, r[8] * M)
        dx, dy = Bp[0] - A[0], Bp[1] - A[1]
        d = min(abs(dx), abs(dy)); sx, sy = math.copysign(1, dx), math.copysign(1, dy)
        options = [(A[0] + sx * d, A[1] + sy * d), (Bp[0] - sx * d, Bp[1] - sy * d)]   # 45° primeiro / reto primeiro
        tree, gs = obstacles(net, r[4]); ok = False
        before = len(angulos.corners(rows, fps))
        for K in options:
            segs = [LineString([A, K]), LineString([K, Bp])]
            if all(inner.contains(sg) and not any(gs[q].intersects(sg.buffer(r[9] * M / 2 + 0.2)) for q in tree.query(sg.buffer(r[9] * M / 2 + 0.2))) for sg in segs):
                old = list(r)
                r[7], r[8] = round(mil(K[0]), 4), round(mil(K[1]), 4)
                rows.append(['LINE', nid(), 0, net, r[4], r[7], r[8], round(mil(Bp[0]), 4), round(mil(Bp[1]), 4), r[9], 0])
                if len(angulos.corners(rows, fps)) > before:      # criou canto reto/agudo: desfaz
                    rows.pop(); r[:] = old; continue
                ok = True; log.append(f'45°: {net} ({A[0]:.2f}; {A[1]:.2f})→({Bp[0]:.2f}; {Bp[1]:.2f}) via ({K[0]:.2f}; {K[1]:.2f})'); break
        if not ok: log.append(f'mantido (sem espaço para 45°): {net} ({A[0]:.2f}; {A[1]:.2f})→({Bp[0]:.2f}; {Bp[1]:.2f})')

# 4) GND isolado: via de costura onde a ilha de uma face encontra o GND principal da outra
class B: pass
Bd = B(); Bd.pcb = rows; Bd.outer = outer; Bd.via = lambda net, x, y, d=0.6, hole=0.3: via(net, x, y, d, hole)
added = costura_gnd.stitch(Bd, fps); log.append(f'vias de costura de GND: {added}')

# grava
tmp = tempfile.mkdtemp()
with zipfile.ZipFile(SRC) as zi, zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zo:
    for info in zi.infolist():
        if info.is_dir(): zo.writestr(info, b''); continue
        data = zi.read(info.filename)
        if info.filename == PCBN:
            data = ''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n' for r in rows).encode('utf-8')
        zo.writestr(info.filename, data)
print('\n'.join(log)); print('arquivo:', DST)
