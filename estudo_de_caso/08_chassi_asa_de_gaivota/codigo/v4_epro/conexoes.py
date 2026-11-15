"""Conectividade por rede com o cobre real do arquivo (trilhas, vias, pads e áreas POURED) — como o 'Connection Error' do DRC."""
import sys, collections
from shapely.strtree import STRtree
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import verifica_placa as V, check, poured
def items(rows, fps, use_poured=True):
    cu = [(l, n, g, str(i)) for l, n, g, i in check.copper(rows, fps)]
    if use_poured:
        lay = {r[1]: (r[3], r[4]) for r in rows if r[0] == 'POUR'}
        for k, (pid, L, kind, g) in enumerate(poured.poured(rows)):
            for j, gg in enumerate(getattr(g, 'geoms', [g])):
                cu.append((L, lay[pid][0], gg, f'cobre:{pid}:{k}:{j}'))
    return cu
def groups(rows, fps, use_poured=True):
    cu = items(rows, fps, use_poured)
    n = len(cu); par = list(range(n))
    def f(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    for L in (1, 2):
        idx = [k for k in range(n) if cu[k][0] == L]
        tree = STRtree([cu[k][2] for k in idx])
        for a in idx:
            for b in tree.query(cu[a][2]):
                b = idx[b]
                if b > a and cu[a][1] == cu[b][1] and cu[a][1] and cu[a][2].intersects(cu[b][2]): par[f(a)] = f(b)
    byid = collections.defaultdict(list)
    for k in range(n): byid[cu[k][3]].append(k)
    for i, ks in byid.items():          # mesmo item nas duas faces (via, pad PTH)
        for a, b in zip(ks, ks[1:]): par[f(a)] = f(b)
    out = collections.defaultdict(lambda: collections.defaultdict(list))
    for k in range(n):
        if cu[k][1]: out[cu[k][1]][f(k)].append(k)
    return cu, out
def report(path, use_poured=True):
    rows, fps, outer = V.board(path)
    cu, out = groups(rows, fps, use_poured)
    res = {}
    for net, gs in out.items():
        if len(gs) < 2: continue
        main = max(gs.values(), key=lambda ks: sum(1 for k in ks if not cu[k][3].startswith('cobre')) + 0.001 * len(ks))
        lost = []
        for ks in gs.values():
            if ks is main: continue
            its = sorted({cu[k][3] for k in ks if not cu[k][3].startswith('cobre')})
            if its: lost.append([(i, round(cu[k][2].centroid.x, 2), round(cu[k][2].centroid.y, 2)) for i in its for k in ks if cu[k][3] == i][:len(its)])
        if lost: res[net] = lost
    return res
if __name__ == '__main__':
    for net, lost in report(sys.argv[1], len(sys.argv) < 3).items():
        print(net); [print('   ', g) for g in lost]
