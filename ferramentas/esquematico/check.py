import json, re, sys
from collections import defaultdict
d = json.load(open('intent.json'))
# parse kicad netlist
txt = open('seguidor_base.net').read()
nets = {}
for m in re.finditer(r'\(net \(code "?(\d+)"?\) \(name "([^"]*)"\)(.*?)\)\s*(?=\(net \(code|\)\s*\)\s*$)', txt, re.S):
    name = m.group(2)
    nodes = set(re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', m.group(3)))
    nets[name] = nodes
# all component pins in netlist
comps = set(re.findall(r'\(comp \(ref "([^"]+)"\)', txt))
# expected via union-find
par = {}
def f(a):
    par.setdefault(a, a)
    while par[a] != a: par[a] = par[par[a]]; a = par[a]
    return a
def u(a, b): par[f(a)] = f(b)
for r, p, n in d['intent']: u((r, p), ('NET', n))
for ra, pa, rb, pb in d['links']: u((ra, pa), (rb, pb))
groups = defaultdict(set); names = defaultdict(set)
for k in list(par):
    if k[0] == 'NET': names[f(k)].add(k[1])
    else: groups[f(k)].add(k)
errs = 0
stacked = {('U1','5'),('U1','6'),('U1','21')}  # GND/VCC empilhados no simbolo
for root, nm in names.items():
    if len(nm) > 1: print('ERRO: nomes fundidos no intent:', nm); errs += 1
exp = {}
for root, pins in groups.items():
    nm = '/'.join(sorted(names[root])) if root in names else '~' + '+'.join(sorted(f'{r}.{p}' for r, p in pins))
    exp[nm] = pins
# compare
kpin2net = {}
for n, nodes in nets.items():
    for nd in nodes: kpin2net[nd] = n
for nm, pins in sorted(exp.items()):
    kn = {kpin2net.get(p, 'AUSENTE') for p in pins}
    if len(kn) != 1: print('ERRO: grupo', nm, 'separado em', kn); errs += 1; continue
    kn = kn.pop()
    extra = nets.get(kn, set()) - pins - stacked
    if extra: print('ERRO: rede', nm, '(kicad', kn, ') tem pinos extras', extra); errs += 1
    if len(pins) < 2 and nm not in ('VBAT_A7',): print('AVISO: rede de 1 pino:', nm, pins)
# NCs
for r, p in d['ncs']:
    n = kpin2net.get((r, p))
    if n and len(nets[n]) > 1: print('ERRO: NC conectado', r, p, n); errs += 1
# pins not covered
covered = set(kpin2net)
known = set(map(tuple, [(r, p) for r, p, _ in d['intent']])) | {(a, b) for a, b, _, _ in d['links']} | {(c, e) for _, _, c, e in d['links']} | set(map(tuple, d['ncs']))

for pin in covered - known - stacked: print('AVISO: pino nao previsto', pin, kpin2net[pin])
print('redes kicad:', len(nets), '| grupos esperados:', len(exp), '| componentes:', len(comps), '| erros:', errs)
for nm in sorted(exp): print(f'  {nm:12s} {len(exp[nm]):2d}', ' '.join(sorted(f"{r}.{p}" for r, p in exp[nm])))
