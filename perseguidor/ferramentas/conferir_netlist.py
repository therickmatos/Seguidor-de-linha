"""Extrai a netlist do esquemático EasyEDA Pro (.esch) e compara com as redes do
PCB (.epcb, PAD_NET) do mesmo .epro. Uso:
    python3 perseguidor/ferramentas/conferir_netlist.py "perseguidor/RUSH - Dreamcast.epro"
"""
import collections, glob, json, math, os, sys, tempfile, zipfile


def rows(path):
    return [json.loads(l) for l in open(path, encoding='utf-8') if l.strip()]


def pins_do_simbolo(d, uuid):
    out = {}
    attrs = collections.defaultdict(dict)
    rs = rows(f'{d}/SYMBOL/{uuid}.esym')
    for r in rs:
        if r[0] == 'ATTR':
            attrs[r[2]][r[3]] = r[4]
    for r in rs:
        if r[0] == 'PIN':
            out[r[1]] = (attrs[r[1]].get('NUMBER'), r[4], r[5])
    return out


def netlist_esquematico(d, rot_sign=1, flip=False):
    sch = glob.glob(f'{d}/SHEET/*/*.esch')[0]
    rs = rows(sch)
    attrs = collections.defaultdict(dict)
    for r in rs:
        if r[0] == 'ATTR':
            attrs[r[2]][r[3]] = r[4]
    pai = {}

    def find(a):
        pai.setdefault(a, a)
        while pai[a] != a:
            pai[a] = pai[pai[a]]; a = pai[a]
        return a

    def union(a, b):
        pai[find(a)] = find(b)
    P = lambda x, y: ('p', round(x, 2), round(y, 2))
    segs = []
    for r in rs:
        if r[0] == 'WIRE':
            for seg in r[2]:
                pts = list(zip(seg[0::2], seg[1::2]))
                for a, b in zip(pts, pts[1:]):
                    union(P(*a), P(*b)); segs.append((a, b))
                if len(pts) == 1:
                    find(P(*pts[0]))
                if attrs[r[1]].get('NET'):
                    union(P(*pts[0]), ('net', attrs[r[1]]['NET']))
    pinpts = {}
    for r in rs:
        if r[0] != 'COMPONENT':
            continue
        a = attrs[r[1]]
        sym = a.get('Symbol')
        if not sym or not os.path.exists(f'{d}/SYMBOL/{sym}.esym'):
            continue
        ang = math.radians(r[5] * rot_sign)
        for pid, (num, px, py) in pins_do_simbolo(d, sym).items():
            if r[6]:
                px = -px
            x = r[3] + px * math.cos(ang) - py * math.sin(ang)
            y = r[4] + px * math.sin(ang) + py * math.cos(ang)
            k = P(x, y)
            find(k)
            des = a.get('Designator') or ''
            if des.startswith('#') or a.get('Add into BOM') == 'no' and not des[:1].isalpha():
                nm = a.get('Value') or a.get('Name')
                if nm:
                    union(k, ('net', nm))
            else:
                pinpts[(des, num)] = k
                if attrs.get(r[1] + pid, {}).get('NO_CONNECT') == 'yes':
                    pinpts[(des, num)] = ('nc', des, num)
    # derivações em T: ponto sobre o meio de um segmento
    allpts = [k for k in list(pai) if k[0] == 'p']
    for (x0, y0), (x1, y1) in segs:
        for k in allpts:
            x, y = k[1], k[2]
            if min(x0, x1) - .01 <= x <= max(x0, x1) + .01 and min(y0, y1) - .01 <= y <= max(y0, y1) + .01:
                if abs((x1 - x0) * (y - y0) - (y1 - y0) * (x - x0)) < 0.01:
                    union(k, P(x0, y0))
    grupos = collections.defaultdict(set)
    for key, k in pinpts.items():
        grupos[find(k)].add(key)
    nomes = {}
    for k in list(pai):
        if k[0] == 'net':
            nomes.setdefault(find(k), set()).add(k[1])
    return grupos, nomes


def netlist_pcb(d):
    pcb = glob.glob(f'{d}/PCB/*.epcb')[0]
    rs = rows(pcb)
    des = {r[3]: r[8] for r in rs if r[0] == 'ATTR' and r[7] == 'Designator' and r[8]}
    nets = collections.defaultdict(set)
    for r in rs:
        if r[0] == 'PAD_NET' and r[2]:
            nets[r[3] or ('sem rede', des.get(r[1]), r[2])].add((des.get(r[1]), r[2]))
    return nets


def comparar(d):
    pcb = netlist_pcb(d)
    melhor = None
    for rs_ in (1, -1):
        for fl in (False, True):
            g, n = netlist_esquematico(d, rs_, fl)
            part_s = {frozenset(v) for v in g.values() if len(v) > 1}
            part_p = {frozenset(v) for v in pcb.values() if len(v) > 1}
            dif = part_s ^ part_p
            if melhor is None or len(dif) < len(melhor[0]):
                melhor = (dif, g, n, part_s, part_p)
    dif, g, n, part_s, part_p = melhor
    return dif, g, n, pcb


if __name__ == '__main__':
    tmp = tempfile.mkdtemp()
    zipfile.ZipFile(sys.argv[1]).extractall(tmp)
    dif, g, n, pcb = comparar(tmp)
    multi = [v for v in g.values() if len(v) > 1]
    print(f'esquemático: {len(multi)} redes com 2+ pinos; PCB: {sum(1 for v in pcb.values() if len(v) > 1)}')
    if not dif:
        print('Esquemático e PCB têm exatamente as mesmas ligações.')
    else:
        print('Diferenças (grupos de pinos que só existem de um lado):')
        for s in sorted(dif, key=lambda s: sorted(s)):
            print('   ', sorted(s))
