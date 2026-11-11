"""Verificação da placa inteira (aproximação do DRC) e comparação v3 × v4."""
import json, zipfile, collections, sys
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import polygonize, unary_union
from shapely.strtree import STRtree
import check
M = 0.0254
def load(z, n): return [json.loads(l) for l in z.read(n).decode('utf-8-sig').splitlines() if l.strip()]
def board(path):
    z = zipfile.ZipFile(path)
    rows = load(z, [n for n in z.namelist() if n.endswith('.epcb')][0])
    fps = {n.split('/')[1][:-5]: load(z, n) for n in z.namelist() if n.endswith('.efoo')}
    segs = [r[6] for r in rows if r[0] == 'POLY' and r[4] == 11]
    outer = list(polygonize([LineString([(s[0] * M, s[1] * M), (s[3] * M, s[4] * M)]) for s in segs]))
    outer = max(outer, key=lambda p: p.area)
    return rows, fps, outer
def run(path, clr=0.2, edge=0.3, hole=0.3):
    rows, fps, outer = board(path)
    cu = check.copper(rows, fps)
    hs = check.holes(rows)
    probs = set()
    for L in (1, 2):
        items = [c for c in cu if c[0] == L]
        tree = STRtree([c[2] for c in items])
        for a, (La, na, ga, ia) in enumerate(items):
            for b in tree.query(ga.buffer(clr)):
                if b <= a: continue
                Lb, nb, gb, ib = items[b]
                if na and na == nb: continue
                if str(ia).split(':')[0] == str(ib).split(':')[0] and ':' in str(ia): continue   # pads do mesmo componente sem rede
                d = ga.distance(gb)
                if d < clr: probs.add(('folga', L, tuple(sorted([str(ia), str(ib)])), tuple(sorted([na, nb])), round(d, 3)))
    ring = outer.exterior
    for L, n, g, i in cu:
        d = g.distance(ring) if outer.contains(g) else -1
        if d < edge: probs.add(('borda', L, str(i), n, round(d, 3)))
        for h in hs:
            dh = g.distance(h)
            if dh < hole: probs.add(('furo', L, str(i), n, round(dh, 3)))
    # pontas soltas de trilhas
    ends = collections.Counter()
    for r in rows:
        if r[0] == 'LINE' and r[4] in (1, 2):
            for p in ((r[5], r[6]), (r[7], r[8])):
                pt = Point(p[0] * M, p[1] * M)
                touch = [c for c in cu if c[0] == r[4] and c[1] == r[3] and c[3] != r[1] and c[2].distance(pt) < 0.01]
                if not touch: probs.add(('ponta solta', r[4], r[1], r[3], (round(p[0] * M, 2), round(p[1] * M, 2))))
    # designadores fora da placa
    for r in rows:
        if r[0] == 'ATTR' and r[7] == 'Designator' and r[5] is not None:
            if not outer.buffer(-0.2).contains(Point(r[5] * M, r[6] * M)): probs.add(('designador fora', r[8], (round(r[5] * M, 2), round(r[6] * M, 2))))
    # componentes sobrepostos (envoltória dos pads + 0,25 mm), mesma face
    comps = collections.defaultdict(list)
    side = {r[1]: r[3] for r in rows if r[0] == 'COMPONENT'}
    names = {}
    for r in rows:
        if r[0] == 'ATTR' and r[7] == 'Designator': names[r[3]] = r[8]
    for L, n, g, i in check.pad_geoms(rows, fps):
        comps[i.split(':')[0]].append(g)
    hulls = {c: unary_union(gs).convex_hull.buffer(0.25) for c, gs in comps.items()}
    keys = list(hulls)
    for a in range(len(keys)):
        for b in range(a + 1, len(keys)):
            ca, cb = keys[a], keys[b]
            if side.get(ca) != side.get(cb): continue
            if hulls[ca].intersects(hulls[cb]) and hulls[ca].intersection(hulls[cb]).area > 0.05:
                probs.add(('componentes encostados', tuple(sorted([names.get(ca, ca), names.get(cb, cb)]))))
    return probs
if __name__ == '__main__':
    v3 = run('/home/user/Seguidor-de-linha/ProPrj_RUSH - SATURN - v3_2026-11-09.epro')
    v4 = run('/home/user/Seguidor-de-linha/ProPrj_RUSH - SATURN - v4_asa_gaivota_2026-11-11.epro')
    def key(p):   # compara sem o valor numérico
        return p[:-1] if p[0] in ('folga', 'borda', 'furo') else p
    k3 = {key(p) for p in v3}
    print('v3:', len(v3), 'itens;', 'v4:', len(v4), 'itens')
    print('--- só na v4 ---')
    for p in sorted(v4, key=str):
        if key(p) not in k3: print(p)
    print('--- na v3 e na v4 (já existiam) ---')
    c = collections.Counter(p[0] for p in v4 if key(p) in k3); print(dict(c))
