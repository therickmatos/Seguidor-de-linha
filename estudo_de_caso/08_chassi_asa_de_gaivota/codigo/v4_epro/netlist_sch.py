"""Netlist do esquemático EasyEDA Pro (pinos × redes) para comparar com os PAD_NET da PCB."""
import json, math, zipfile, collections
def load(z, n): return [json.loads(l) for l in z.read(n).decode('utf-8-sig').splitlines() if l.strip()]
def sch_netlist(path, conv=0):
    z = zipfile.ZipFile(path)
    schn = [n for n in z.namelist() if n.endswith('.esch')][0]
    rows = load(z, schn)
    syms = {}
    for n in z.namelist():
        if n.endswith('.esym'):
            rr = load(z, n); at = collections.defaultdict(dict)
            for r in rr:
                if r[0] == 'ATTR': at[r[2]][r[3]] = r[4]
            syms[n.split('/')[1][:-5]] = [(r[4], r[5], at[r[1]].get('NUMBER')) for r in rr if r[0] == 'PIN']
    by = collections.defaultdict(dict)
    for r in rows:
        if r[0] == 'ATTR': by[r[2]][r[3]] = r[4]
    # nós: pontos (x,y). union-find sobre pontos de fios e pinos
    parent = {}
    def f(a):
        parent.setdefault(a, a)
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    def u(a, b): parent[f(a)] = f(b)
    names = collections.defaultdict(set)
    segs = []
    for r in rows:
        if r[0] == 'WIRE':
            for p in r[2]:
                pts = [(round(p[i], 3), round(p[i + 1], 3)) for i in range(0, len(p), 2)]
                for a, b in zip(pts, pts[1:]): u(a, b); segs.append((a, b))
                if 'NET' in by[r[1]]: names[pts[0]].add(by[r[1]]['NET'])
    pins = []
    for r in rows:
        if r[0] != 'COMPONENT': continue
        a = by[r[1]]; sym = a.get('Symbol')
        if sym not in syms: continue
        th = math.radians(r[5] if conv == 0 else -r[5])
        for px, py, num in syms[sym]:
            if r[6]: px = -px
            x = r[3] + px * math.cos(th) - py * math.sin(th); y = r[4] + px * math.sin(th) + py * math.cos(th)
            pt = (round(x, 3), round(y, 3)); f(pt)
            # pino tocando o meio de um fio
            for s0, s1 in segs:
                if (min(s0[0], s1[0]) - 1e-6 <= pt[0] <= max(s0[0], s1[0]) + 1e-6 and min(s0[1], s1[1]) - 1e-6 <= pt[1] <= max(s0[1], s1[1]) + 1e-6
                        and abs((s1[0] - s0[0]) * (pt[1] - s0[1]) - (s1[1] - s0[1]) * (pt[0] - s0[0])) < 1e-6): u(pt, s0)
            if a.get('Designator', '').startswith('#PWR') or a.get('Convert to PCB') == 'no' and a.get('Name') in ('GND', '+5V', 'VBAT'):
                names[pt].add(a.get('Name'))
            else:
                pins.append((a.get('Unique ID'), a.get('Designator'), num, pt))
    netname = collections.defaultdict(set)
    for pt, ns in names.items(): netname[f(pt)] |= ns
    out = {}
    for uid, des, num, pt in pins:
        root = f(pt)
        out[(uid, num)] = (des, frozenset(netname[root]) or root)
    return out
def pcb_padnets(path):
    z = zipfile.ZipFile(path)
    rows = load(z, [n for n in z.namelist() if n.endswith('.epcb')][0])
    comp = {r[1]: r[7].get('Unique ID') for r in rows if r[0] == 'COMPONENT'}
    return {(comp[r[1]], r[2]): r[3] for r in rows if r[0] == 'PAD_NET' and r[2] and r[1] in comp}
def compare(path, conv=0, verbose=False):
    S = sch_netlist(path, conv); P = pcb_padnets(path)
    # mapear grupos sem nome: para cada raiz sem nome, os nets da PCB devem ser consistentes
    bad = []; anon = collections.defaultdict(set)
    for k, (des, net) in S.items():
        if k not in P: continue
        pn = P[k]
        if isinstance(net, frozenset):
            if pn not in net: bad.append((des, k[1], sorted(net), pn))
        else:
            anon[net].add(pn)
    for root, pns in anon.items():
        if len(pns) > 1: bad.append(('grupo sem nome', root, sorted(pns), ''))
    return bad, len(S), len(P)
