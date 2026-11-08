"""GND da placa base do RUSH: planos nas duas faces, vias de costura e ligacao dos pads (08/11/2026).

  python rush_gnd.py costura entrada.epro saida.epro     # vias de costura entre as ilhas dos planos
  python rush_gnd.py pads    entrada.epro pasta saida.epro   # FreeRouting so para os pads de GND soltos

O plano e simulado de forma conservadora (easyeda_cobre.Placa.planos_gnd: 0,3 mm do cobre de outras
redes e da borda, sem sobras com menos de 0,25 mm). Se o GND fica todo ligado nesta simulacao, fica
ligado tambem no preenchimento do EasyEDA com folga <= 0,3 mm.

Vias de costura: 0,8/0,4 onde cabem (centro a >= 0,7 mm do cobre de outras redes e da borda), senao
0,6/0,3. Primeiro as que unem ilhas diferentes (duas por ligacao quando ha espaco), depois uma malha
de ~5 mm e um reforco junto dos terminais de corrente (J1.2, PGND e pad termico dos drivers, Q1.2,
C1.2, C2.2, C13.2, C16.2, C17.2).

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import collections
import json
import math
import os
import sys

import shapely
from shapely.geometry import MultiPolygon, Point
from shapely.ops import nearest_points, unary_union
from shapely.strtree import STRtree

import easyeda_cobre as C
import easyeda_rotear as R

TERMINAIS_CORRENTE = ['J1.2', 'U3.9', 'U3.17', 'U4.9', 'U4.17', 'Q1.2', 'C1.2', 'C2.2', 'C13.2', 'C16.2', 'C17.2']
MALHA = 5.0
SOBREPOSICAO_MIN = 0.1      # mm2 de plano sobre o pad para contar como ligado (sem depender de raspas)


def _partes(g):
    return [p for p in (g.geoms if isinstance(g, MultiPolygon) else [g]) if not p.is_empty]


class UF:
    def __init__(self):
        self.p = {}

    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb
            return True
        return False


def estado(placa, objs=None):
    """Planos, ilhas e componentes conexos do GND (ilhas + pads + vias)."""
    objs = objs or placa.objetos()
    pl = placa.planos_gnd(objs)
    ilhas = {lay: _partes(pl[lay]) for lay in (C.TOP, C.BOT)}
    arv = {lay: STRtree(ilhas[lay]) for lay in ilhas}
    uf = UF()
    gnd = [o for o in objs if o['net'] == 'GND']
    for k, o in enumerate(gnd):
        no = ('obj', k)
        uf.find(no)
        for lay in o['layers']:
            for j in arv[lay].query(o['geom'], predicate='intersects'):
                j = int(j)
                if ilhas[lay][j].intersection(o['geom']).area > SOBREPOSICAO_MIN or o['tipo'] == 'via':
                    uf.union(no, (lay, j))
    # objetos de GND que se tocam entre si (trilhas de GND, pads e vias)
    tree = STRtree([o['geom'] for o in gnd])
    for k, o in enumerate(gnd):
        for j in tree.query(o['geom'], predicate='intersects'):
            j = int(j)
            if j != k and o['layers'] & gnd[j]['layers']:
                uf.union(('obj', k), ('obj', j))
    return pl, ilhas, gnd, uf


def pads_soltos(placa, gnd, uf):
    """Grupos de pads de GND que nao estao no componente principal (o do J1.2)."""
    principal = None
    for k, o in enumerate(gnd):
        if o['ref'] == 'J1.2':
            principal = uf.find(('obj', k))
    grupos = collections.defaultdict(list)
    for k, o in enumerate(gnd):
        if o['tipo'] == 'pad':
            r = uf.find(('obj', k))
            if r != principal:
                grupos[r].append(o['ref'])
    return list(grupos.values())


def regiao_via(placa, pl, objs, d):
    """Onde cabe o centro de uma via de GND de diametro d: dentro dos dois planos com margem,
    longe de pads (sem via no pad) e de vias existentes."""
    m = d / 2 + 0.2 - C.FOLGA_PLANO + 0.1      # folga extra de 0,1 mm (o plano ja esta a 0,3 do resto)
    m = max(m, d / 2)                           # e a borda: plano a 0,3 + d/2 => 0,3 + d/2 da borda
    v = pl[C.TOP].buffer(-m).intersection(pl[C.BOT].buffer(-m))
    proibido = [o['geom'].buffer(d / 2 + 0.25) for o in objs if o['tipo'] == 'pad']
    proibido += [o['geom'].buffer(d / 2 + 0.3) for o in objs if o['tipo'] == 'via']
    if proibido:
        v = v.difference(unary_union(proibido))
    return v


def pontos(regiao, passo):
    if regiao.is_empty:
        return []
    x0, y0, x1, y1 = regiao.bounds
    import numpy as np
    xs = np.arange(math.floor(x0 / passo) * passo, x1 + passo, passo)
    ys = np.arange(math.floor(y0 / passo) * passo, y1 + passo, passo)
    X, Y = np.meshgrid(xs, ys)
    pts = shapely.points(X.ravel(), Y.ravel())
    shapely.prepare(regiao)
    dentro = shapely.contains(regiao, pts)
    return [(p.x, p.y) for p in pts[dentro]]


def costura(entrada, saida):
    placa = C.Placa(entrada)
    objs = placa.objetos()
    pl, ilhas, gnd, uf = estado(placa, objs)
    print('ilhas: cima', len(ilhas[C.TOP]), 'baixo', len(ilhas[C.BOT]))
    print('pads de GND fora do principal (antes):', pads_soltos(placa, gnd, uf))
    novas = []

    def ilha_de(lay, x, y):
        P = Point(x, y)
        for j, g in enumerate(ilhas[lay]):
            if g.contains(P):
                return j
        return None

    ocupado = []

    def livre(x, y, d):
        return all(math.dist((x, y), q) >= (d + dq) / 2 + 0.6 for q, dq in ocupado)

    def por(x, y, d):
        furo = 0.4 if d > 0.7 else 0.3
        novas.append({'net': 'GND', 'x': x, 'y': y, 'd': d, 'furo': furo})
        ocupado.append(((x, y), d))

    candidatos = {}
    for d in (0.8, 0.6):
        reg = regiao_via(placa, pl, objs, d)
        pts = pontos(reg, 0.25)
        cands = []
        for x, y in pts:
            it, ib = ilha_de(C.TOP, x, y), ilha_de(C.BOT, x, y)
            if it is None or ib is None:
                continue
            # profundidade: distancia ate a borda da regiao (centralizar a via)
            prof = reg.boundary.distance(Point(x, y))
            cands.append((x, y, it, ib, prof))
        candidatos[d] = cands
        print(f'candidatos {d}: {len(cands)}')
    # 1) ligar ilhas diferentes (preferindo 0,8; duas vias por ligacao quando possivel)
    for d in (0.8, 0.6):
        por_par = collections.defaultdict(list)
        for c in candidatos[d]:
            por_par[(c[2], c[3])].append(c)
        # pares por tamanho da sobreposicao (maior primeiro)
        for (it, ib), cs in sorted(por_par.items(), key=lambda kv: -len(kv[1])):
            if uf.find((C.TOP, it)) == uf.find((C.BOT, ib)):
                continue
            cs = sorted(cs, key=lambda c: -c[4])
            n = 0
            for x, y, _, _, _ in cs:
                if livre(x, y, d):
                    por(x, y, d)
                    n += 1
                    if n == 2:
                        break
            if n:
                uf.union((C.TOP, it), (C.BOT, ib))
    # 2) reforco junto dos terminais de corrente (ate 3 vias a <= 3,5 mm de cada um)
    cent = {o['ref']: o['geom'] for o in gnd if o['tipo'] == 'pad'}
    for ref in TERMINAIS_CORRENTE:
        g = cent.get(ref)
        if g is None:
            continue
        cs = sorted((c for c in candidatos[0.8] if g.distance(Point(c[0], c[1])) <= 3.5),
                    key=lambda c: g.distance(Point(c[0], c[1])))
        n = 0
        for x, y, *_ in cs:
            if livre(x, y, 0.8):
                por(x, y, 0.8)
                n += 1
                if n == 3:
                    break
    # 3) malha de ~5 mm
    for d in (0.8,):
        for x, y, it, ib, prof in sorted(candidatos[d], key=lambda c: -c[4]):
            if all(math.dist((x, y), q) >= MALHA for q, _ in ocupado):
                por(x, y, d)
    print('vias de costura:', len(novas), {d: sum(1 for v in novas if v['d'] == d) for d in (0.8, 0.6)})
    R.gravar_epro(placa, saida, lambda r: True, [], novas, prefixo='g')
    p2 = C.Placa(saida)
    _, _, gnd2, uf2 = estado(p2)
    soltos = pads_soltos(p2, gnd2, uf2)
    print('pads de GND fora do principal (depois):', soltos)
    return soltos


if __name__ == '__main__':
    if sys.argv[1] == 'costura':
        costura(sys.argv[2], sys.argv[3])



# ------------------------------------------------------------------ roteador de grade para o GND
W_GND = 0.3
VIA_GND = (0.6, 0.3)
CUSTO_VIA = 300          # em passos de grade de 0,05 mm (15 mm de trilha)


FOLGA_TRILHA = 0.2


def ligar_pads(entrada, saida, max_rodadas=6):
    atual = entrada
    for rodada in range(max_rodadas):
        placa = C.Placa(atual)
        objs = placa.objetos()
        pl, ilhas, gnd, uf = estado(placa, objs)
        principal = next(uf.find(('obj', k)) for k, o in enumerate(gnd) if o['ref'] == 'J1.2')
        soltos = [o for k, o in enumerate(gnd) if o['tipo'] == 'pad' and uf.find(('obj', k)) != principal]
        print(f'rodada {rodada}: pads de GND soltos', [o['ref'] for o in soltos])
        if not soltos:
            if atual != saida:
                import shutil
                shutil.copy(atual, saida)
            return []
        alvo = {}
        for lay in (C.TOP, C.BOT):
            partes = [g for j, g in enumerate(ilhas[lay]) if uf.find((lay, j)) == principal]
            partes += [o['geom'] for k, o in enumerate(gnd) if lay in o['layers'] and uf.find(('obj', k)) == principal]
            alvo[lay] = unary_union(partes)
        novas_t, novas_v, feitos = [], [], set()
        grupos_feitos = set()
        for o in soltos:
            k = next(k for k, q in enumerate(gnd) if q is o)
            g = uf.find(('obj', k))
            if g in grupos_feitos:
                continue
            import grade as G
            r = None
            for margem in (4.0, 9.0):
                r = G.rotear(placa, objs, 'GND', {lay: o['geom'] for lay in o['layers']}, alvo, W_GND,
                             via=VIA_GND, margem=margem, custo_via=CUSTO_VIA)
                if r:
                    break
            if r is None:
                print('  sem caminho:', o['ref'])
                continue
            t, v = r['trilhas'], r['vias']
            print(f"  {o['ref']}: {len(t)} trilhas, {len(v)} vias")
            novas_t += t
            novas_v += v
            grupos_feitos.add(g)
            for tt in t:
                for a, b in zip(tt['pts'], tt['pts'][1:]):
                    objs.append({'tipo': 'trilha', 'net': 'GND', 'layers': {tt['layer']},
                                 'geom': C.LineString([a, b]).buffer(W_GND / 2, quad_segs=8), 'ref': 'novo', 'obj': None})
            for vv in v:
                objs.append({'tipo': 'via', 'net': 'GND', 'layers': {C.TOP, C.BOT},
                             'geom': Point(vv['x'], vv['y']).buffer(vv['d'] / 2, quad_segs=12), 'ref': 'novo', 'obj': vv})
            # o cobre novo vira obstaculo para os proximos (mesma rede: nao precisa)
            break_ok = True
        if not novas_t and not novas_v:
            print('nada mais a ligar')
            if atual != saida:
                import shutil
                shutil.copy(atual, saida)
            return [o['ref'] for o in soltos]
        prox = saida + f'.r{rodada}.tmp'
        R.gravar_epro(placa, prox, lambda r: True, novas_t, novas_v, prefixo=f'f{rodada}_')
        atual = prox
    return None


if __name__ == '__main__' and sys.argv[1] == 'pads':
    ligar_pads(sys.argv[2], sys.argv[3])


def _unir_itens(itens, partes, uf):
    """Itens de GND ligados aos corredores largos que tocam (>= 0,05 mm2) e entre si quando se tocam."""
    for k, o in enumerate(itens):
        for lay in o['layers']:
            for j, g in enumerate(partes[lay]):
                if g.intersection(o['geom']).area > 0.05:
                    uf.union(('o', k), (lay, j))
    tree = STRtree([o['geom'] for o in itens])
    for k, o in enumerate(itens):
        for j in tree.query(o['geom'], predicate='intersects'):
            j = int(j)
            if j != k and o['layers'] & itens[j]['layers']:
                uf.union(('o', k), ('o', j))


def retorno_largo(caminho, largura=1.0):
    """Terminais de corrente ligados ao J1.2 so por corredores de plano com >= largura (mm) e vias."""
    placa = C.Placa(caminho)
    objs = placa.objetos()
    pl = placa.planos_gnd(objs)
    partes = {}
    for lay in (C.TOP, C.BOT):
        g = pl[lay].buffer(-largura / 2, quad_segs=4).buffer(largura / 2, quad_segs=4)
        partes[lay] = _partes(g)
    uf = UF()
    gnd = [o for o in objs if o['net'] == 'GND']
    _unir_itens(gnd, partes, uf)
    ref = {o['ref']: k for k, o in enumerate(gnd) if o['tipo'] == 'pad'}
    raiz = uf.find(('o', ref['J1.2']))
    ok = {t: uf.find(('o', ref[t])) == raiz for t in TERMINAIS_CORRENTE if t in ref}
    return ok


if __name__ == '__main__' and sys.argv[1] == 'retorno':
    print(retorno_largo(sys.argv[2]))


def ligar_com_arranque(entrada, saida, so=None, pen=400.0, custo_via=40):
    """Para cada grupo de pads de GND ainda solto: caminho ate o GND principal que pode cruzar trilhas
    de sinal; as trilhas cruzadas sao arrancadas e o GND novo entra. Depois e preciso refazer os
    sinais arrancados (rush_rotear.py fechar)."""
    import grade as G
    import rush_rotear as RR
    placa = C.Placa(entrada)
    objs = placa.objetos()
    pl, ilhas, gnd, uf = estado(placa, objs)
    principal = next(uf.find(('obj', k)) for k, o in enumerate(gnd) if o['ref'] == 'J1.2')
    grupos = collections.defaultdict(list)
    for k, o in enumerate(gnd):
        r = uf.find(('obj', k))
        if r != principal:
            grupos[r].append(o)
    alvo = {}
    for lay in (C.TOP, C.BOT):
        partes = [g for j, g in enumerate(ilhas[lay]) if uf.find((lay, j)) == principal]
        partes += [o['geom'] for k, o in enumerate(gnd) if lay in o['layers'] and uf.find(('obj', k)) == principal]
        alvo[lay] = unary_union(partes)
    sinais = {p['net'] for p in placa.pads if p['net']} - RR.FIXAS - {'GND'}
    arrancar, novas_t, novas_v = set(), [], []
    for g in grupos.values():
        if not any(o['tipo'] == 'pad' for o in g):
            continue
        if so and not any(o['ref'] in so for o in g):
            continue
        orig = {}
        for lay in (C.TOP, C.BOT):
            gs = [o['geom'] for o in g if lay in o['layers']]
            # inclui as ilhas de plano do grupo
            gs += [ilhas[lay][j] for j in range(len(ilhas[lay])) if uf.find((lay, j)) == uf.find(('obj', gnd.index(g[0])))]
            if gs:
                orig[lay] = unary_union(gs)
        r = None
        for margem in (4.0, 9.0):
            r = G.rotear(placa, objs, 'GND', orig, alvo, W_GND, via=VIA_GND, margem=margem, macio=sinais,
                         custo_via=custo_via, pen=pen)
            if r:
                break
        if not r:
            print('sem caminho mesmo arrancando:', [o['ref'] for o in g if o['tipo'] == 'pad'])
            continue
        print([o['ref'] for o in g if o['tipo'] == 'pad'], '-> arranca', sorted(r['cruzadas']))
        arrancar |= r['cruzadas']
        novas_t += r['trilhas']
        novas_v += r['vias']
    R.gravar_epro(placa, saida, lambda row: not (row[0] == 'LINE' and row[1] in arrancar), novas_t, novas_v, prefixo='k')
    return arrancar


if __name__ == '__main__' and sys.argv[1] == 'arrancar':
    ligar_com_arranque(sys.argv[2], sys.argv[3])


def limpar_gnd(entrada, saida):
    """Retira vias e trilhas de GND da placa que nao chegam ao GND principal (bolsoes isolados)."""
    placa = C.Placa(entrada)
    objs = placa.objetos()
    pl, ilhas, gnd, uf = estado(placa, objs)
    principal = next(uf.find(('obj', k)) for k, o in enumerate(gnd) if o['ref'] == 'J1.2')
    fora = {o['ref'] for k, o in enumerate(gnd) if o['tipo'] in ('via', 'trilha')
            and uf.find(('obj', k)) != principal and not (o['tipo'] == 'via' and o['obj']['comp'])}
    pads_fora = [o['ref'] for k, o in enumerate(gnd) if o['tipo'] == 'pad' and uf.find(('obj', k)) != principal]
    print('GND fora do principal retirado:', sorted(fora), '| pads fora:', pads_fora)
    R.gravar_epro(placa, saida, lambda r: not (r[0] in ('LINE', 'VIA') and r[1] in fora), [], [], prefixo='l')
    return fora


if __name__ == '__main__' and sys.argv[1] == 'limpar':
    limpar_gnd(sys.argv[2], sys.argv[3])


def fundir_vias(entrada, saida):
    """Vias da mesma rede com furos perto demais (C.furos): fica a primeira; as trilhas que terminavam
    na outra passam a terminar no centro da que ficou."""
    placa = C.Placa(entrada)
    vias = {v['id']: v for v in placa.vias if not v['comp']}
    troca = {}
    for d, a, b in C.furos(placa):
        if a in vias and b in vias and vias[a]['net'] == vias[b]['net'] and a not in troca and b not in troca:
            troca[b] = a
    print('vias fundidas:', troca)
    centro = {b: (vias[a]['x'], vias[a]['y']) for b, a in troca.items()}
    rows = []
    for r in placa.rows:
        if r[0] == 'VIA' and r[1] in troca:
            continue
        if r[0] == 'LINE':
            for b, (x, y) in centro.items():
                vb = vias[b]
                r = list(r)
                if math.dist((r[5] * C.MIL, r[6] * C.MIL), (vb['x'], vb['y'])) < 1e-3:
                    r[5], r[6] = R.mil(x), R.mil(y)
                if math.dist((r[7] * C.MIL, r[8] * C.MIL), (vb['x'], vb['y'])) < 1e-3:
                    r[7], r[8] = R.mil(x), R.mil(y)
        rows.append(r)
    placa.rows = rows
    R.gravar_epro(placa, saida, lambda r: True, [], [], prefixo='u')


if __name__ == '__main__' and sys.argv[1] == 'fundir':
    fundir_vias(sys.argv[2], sys.argv[3])


# ------------------------------------------------------------- so o plano + as vias que faltam
FOLGA_VIA_PAD = 0.2     # borda da via ate a borda de pad SMD (regra "SMD Pad to Via" do EasyEDA)


def _via_valida(placa, objs_outros, furos, x, y, d, furo):
    """Via de GND em (x, y): folga de 0,2 do cobre de outras redes nas duas faces, 0,3 da borda e dos
    furos sem cobre, furo a >= 0,3 de outros furos."""
    P = Point(x, y)
    r = d / 2
    if not placa.borda.buffer(-(C.FOLGA_BORDA + r)).contains(P):
        return False
    if placa.npth and unary_union(placa.npth).distance(P) < C.FOLGA_BORDA + r:
        return False
    for lay in (C.TOP, C.BOT):
        if objs_outros[lay] is not None and objs_outros[lay].distance(P) < r + 0.2 + 0.01:
            return False
    for (hx, hy), hf in furos:
        if math.dist((x, y), (hx, hy)) - hf / 2 - furo / 2 < 0.3 + 0.01:
            return False
    return True


def vias_minimas(entrada, saida, via_no_pad=False, arrancar_sinais=False):
    """Parte do plano puro (sem vias nem trilhas de GND da placa) e poe so as vias que faltam:
    para cada grupo de pads de GND fora do GND principal (o do J1.2), uma via a FOLGA_VIA_PAD da borda
    do pad, ligada a ele por um toco de trilha, que caia num pedaco do plano principal na outra face
    (o EasyEDA acusa via encostada em pad SMD, mesmo da mesma rede). Sem lugar perto do pad: via em
    qualquer ponto do pedaco de plano do grupo e, por ultimo, trilha + via pelo roteador de grade."""
    import grade as G
    placa = C.Placa(entrada)
    objs = placa.objetos()
    pl, ilhas, gnd, uf = estado(placa, objs)
    outros = {}
    for lay in (C.TOP, C.BOT):
        gs = [o['geom'] for o in objs if lay in o['layers'] and o['net'] != 'GND']
        outros[lay] = unary_union(gs) if gs else None
    furos = [((v['x'], v['y']), v['furo']) for v in placa.vias]
    furos += [(p['centro'], p['furo']) for p in placa.pads if p['furo'] and not p['des'].startswith('PAD:')]
    k_de = {id(o): k for k, o in enumerate(gnd)}
    smd = unary_union([p['geom'] for p in placa.pads if len(p['layers']) == 1])
    principal = lambda: uf.find(('obj', next(k for k, o in enumerate(gnd) if o['ref'] == 'J1.2')))

    def ilha_em(lay, P):
        for j, g in enumerate(ilhas[lay]):
            if g.contains(P):
                return j, g.boundary.distance(P)
        return None, 0
    novas_v, novas_t, relato = [], [], []
    import rush_rotear as RR
    sinais = {p['net'] for p in placa.pads if p['net']} - RR.FIXAS - {'GND'}
    arrancadas = set()
    for rodada in range(40):
        raiz = principal()
        soltos = collections.defaultdict(list)
        for k, o in enumerate(gnd):
            if o['tipo'] == 'pad' and uf.find(('obj', k)) != raiz:
                soltos[uf.find(('obj', k))].append(o)
        if not soltos:
            break
        # o grupo com o pad mais perto de cobre principal primeiro (qualquer ordem serve)
        grupo = sorted(soltos.values(), key=lambda g: g[0]['ref'])[0]
        feito = False
        for d, furo in ((0.8, 0.4), (0.6, 0.3)):
            melhores = []
            for o in grupo:
                pad = o['obj']
                if len(pad['layers']) != 1:
                    continue
                lay = next(iter(pad['layers']))
                dest = C.BOT if lay == C.TOP else C.TOP
                # via afastada do pad (borda a FOLGA_VIA_PAD) e um toco de trilha do pad ate ela
                anel = pad['geom'].buffer(d / 2 + FOLGA_VIA_PAD + 0.01).exterior
                for t in [i / 64 for i in range(64)]:
                    P = anel.interpolate(t, normalized=True)
                    if not _via_valida(placa, outros, furos, P.x, P.y, d, furo) or smd.distance(P) < d / 2 + FOLGA_VIA_PAD:
                        continue
                    a, _ = nearest_points(pad['geom'].buffer(-0.05), P)
                    toco = C.LineString([(a.x, a.y), (P.x, P.y)])
                    if outros[lay] is not None and outros[lay].distance(toco) < W_GND / 2 + 0.2 + 0.01:
                        continue
                    jj, prof = ilha_em(dest, P)
                    if jj is not None and uf.find((dest, jj)) == raiz:
                        melhores.append((round(toco.length, 2), -prof, P.x, P.y, o['ref'], [(a.x, a.y), (P.x, P.y)], lay))
            if melhores:
                melhores.sort()
                comp, prof, x, y, ref, pts, lay_t = melhores[0]
                novas_v.append({'net': 'GND', 'x': x, 'y': y, 'd': d, 'furo': furo})
                novas_t.append({'net': 'GND', 'layer': lay_t, 'w': W_GND, 'pts': pts})
                furos.append(((x, y), furo))
                objs.append({'tipo': 'via', 'net': 'GND', 'layers': {C.TOP, C.BOT},
                             'geom': Point(x, y).buffer(d / 2, quad_segs=12), 'ref': 'novo', 'obj': novas_v[-1]})
                objs.append({'tipo': 'trilha', 'net': 'GND', 'layers': {lay_t},
                             'geom': C.LineString(pts).buffer(W_GND / 2, quad_segs=8), 'ref': 'novo', 'obj': None})
                relato.append((ref, f'via {d}/{furo} com toco de {comp} mm', [g['ref'] for g in grupo]))
                k = k_de[id(next(o for o in grupo if o['ref'] == ref))]
                uf.union(('obj', k), ('obj', next(kk for kk, o in enumerate(gnd) if o['ref'] == 'J1.2')))
                # a via tambem liga as ilhas que toca
                P = Point(x, y)
                for lay in (C.TOP, C.BOT):
                    j, _ = ilha_em(lay, P)
                    if j is not None:
                        uf.union(('obj', k), (lay, j))
                feito = True
                break
        if feito:
            continue
        # via em qualquer ponto das ilhas do grupo que caia em plano principal na outra face
        g_raiz = uf.find(('obj', k_de[id(grupo[0])]))
        cand = []
        for lay in (C.TOP, C.BOT):
            outra = C.BOT if lay == C.TOP else C.TOP
            for j, g in enumerate(ilhas[lay]):
                if uf.find((lay, j)) != g_raiz:
                    continue
                for x, y in pontos(g.buffer(-0.3), 0.25):
                    P = Point(x, y)
                    jj, prof = ilha_em(outra, P)
                    if jj is not None and uf.find((outra, jj)) == raiz and _via_valida(placa, outros, furos, x, y, 0.6, 0.3) \
                            and smd.distance(P) >= 0.3 + FOLGA_VIA_PAD:
                        dist = min(o['geom'].distance(P) for o in grupo)
                        cand.append((dist, -prof, x, y, lay, j, outra, jj))
        if cand:
            cand.sort()
            dist, _, x, y, lay, j, outra, jj = cand[0]
            novas_v.append({'net': 'GND', 'x': x, 'y': y, 'd': 0.6, 'furo': 0.3})
            furos.append(((x, y), 0.3))
            objs.append({'tipo': 'via', 'net': 'GND', 'layers': {C.TOP, C.BOT},
                         'geom': Point(x, y).buffer(0.3, quad_segs=12), 'ref': 'novo', 'obj': novas_v[-1]})
            uf.union((lay, j), (outra, jj))
            relato.append((grupo[0]['ref'], f'via 0.6/0.3 no plano do grupo, a {dist:.1f} mm do pad', [g['ref'] for g in grupo]))
            continue
        # trilha + via pelo roteador de grade, ate o GND principal
        alvo = {}
        for lay in (C.TOP, C.BOT):
            partes = [g for j, g in enumerate(ilhas[lay]) if uf.find((lay, j)) == raiz]
            partes += [o['geom'] for k, o in enumerate(gnd) if lay in o['layers'] and uf.find(('obj', k)) == raiz]
            alvo[lay] = unary_union(partes)
        orig = {}
        for lay in (C.TOP, C.BOT):
            gs = [o['geom'] for o in grupo if lay in o['layers']]
            gs += [g for j, g in enumerate(ilhas[lay]) if uf.find((lay, j)) == g_raiz]
            if gs:
                orig[lay] = unary_union(gs)
        r = None
        for margem in (4.0, 9.0):
            r = G.rotear(placa, objs, 'GND', orig, alvo, W_GND, via=VIA_GND, margem=margem, custo_via=CUSTO_VIA,
                         macio=sinais if arrancar_sinais else None)
            if r:
                break
        if r and r['cruzadas']:
            # trilhas de sinal no caminho: saem (sao refeitas depois por outro caminho)
            arrancadas.update(r['cruzadas'])
            objs[:] = [o for o in objs if not (o['tipo'] == 'trilha' and o['ref'] in r['cruzadas'])]
        if not r:
            relato.append((grupo[0]['ref'], 'SEM SAIDA', [g['ref'] for g in grupo]))
            for o in grupo:       # nao tenta de novo
                uf.union(('obj', k_de[id(o)]), ('obj', next(kk for kk, q in enumerate(gnd) if q['ref'] == 'J1.2')))
            continue
        novas_t += r['trilhas']
        novas_v += r['vias']
        for v in r['vias']:
            furos.append(((v['x'], v['y']), v['furo']))
            objs.append({'tipo': 'via', 'net': 'GND', 'layers': {C.TOP, C.BOT},
                         'geom': Point(v['x'], v['y']).buffer(v['d'] / 2, quad_segs=12), 'ref': 'novo', 'obj': v})
        uf.union(('obj', k_de[id(grupo[0])]), ('obj', next(kk for kk, o in enumerate(gnd) if o['ref'] == 'J1.2')))
        relato.append((grupo[0]['ref'], f"trilha + {len(r['vias'])} via(s)" +
                       (f", arrancando {len(r['cruzadas'])} trecho(s) de sinal" if r['cruzadas'] else ''),
                       [g['ref'] for g in grupo]))
        for t in r['trilhas']:
            for a, b in zip(t['pts'], t['pts'][1:]):
                objs.append({'tipo': 'trilha', 'net': 'GND', 'layers': {t['layer']},
                             'geom': C.LineString([a, b]).buffer(W_GND / 2, quad_segs=8), 'ref': 'novo', 'obj': None})
    for x in relato:
        print(*x)
    print('vias novas:', len(novas_v), '| trilhas novas:', sum(len(t['pts']) - 1 for t in novas_t))
    if arrancadas:
        print('trechos de sinal arrancados (refazer com rush_rotear.fechar):', sorted(arrancadas))
    R.gravar_epro(placa, saida, lambda r: not (r[0] == 'LINE' and r[1] in arrancadas), novas_t, novas_v)
    return relato


if __name__ == '__main__' and sys.argv[1] == 'minimas':
    vias_minimas(sys.argv[2], sys.argv[3], via_no_pad='--sem-via-no-pad' not in sys.argv)


def reforco_retorno(entrada, saida, largura=1.0, raio=4.0, max_vias=6):
    """Terminais de corrente sem caminho largo (>= largura) ate o J1.2: poe a via (0,8/0,4) mais perto do
    terminal que ligue um corredor largo do terminal a um corredor largo do J1.2 na outra face."""
    placa = C.Placa(entrada)
    objs = placa.objetos()
    pl = placa.planos_gnd(objs)
    outros = {}
    for lay in (C.TOP, C.BOT):
        gs = [o['geom'] for o in objs if lay in o['layers'] and o['net'] != 'GND']
        outros[lay] = unary_union(gs) if gs else None
    furos = [((v['x'], v['y']), v['furo']) for v in placa.vias]
    furos += [(p['centro'], p['furo']) for p in placa.pads if p['furo'] and not p['des'].startswith('PAD:')]
    largos = {lay: _partes(pl[lay].buffer(-largura / 2, quad_segs=4).buffer(largura / 2, quad_segs=4)) for lay in (C.TOP, C.BOT)}
    gnd = [o for o in objs if o['net'] == 'GND']
    novas = []
    for _ in range(max_vias):
        uf = UF()
        itens = gnd + [{'tipo': 'via', 'geom': Point(v['x'], v['y']).buffer(v['d'] / 2), 'layers': {C.TOP, C.BOT}, 'ref': 'nova'} for v in novas]
        _unir_itens(itens, largos, uf)
        ref = {o['ref']: k for k, o in enumerate(itens) if o['tipo'] == 'pad'}
        raiz = uf.find(('o', ref['J1.2']))
        falta = [t for t in TERMINAIS_CORRENTE if t in ref and uf.find(('o', ref[t])) != raiz]
        if not falta:
            break
        t = falta[0]
        g_t = next(o['geom'] for o in itens if o['ref'] == t)
        rt = uf.find(('o', ref[t]))
        cand = []
        smd = unary_union([p['geom'] for p in placa.pads if len(p['layers']) == 1])
        # via perto do terminal (sem encostar em pad SMD) ligando o corredor largo dele ao do J1.2
        if True:
            for x, y in pontos(g_t.buffer(raio), 0.25):
                P = Point(x, y)
                if not _via_valida(placa, outros, furos, x, y, 0.8, 0.4) or smd.distance(P) < 0.4 + FOLGA_VIA_PAD:
                    continue
                lados = {}
                for lay in (C.TOP, C.BOT):
                    for j, g in enumerate(largos[lay]):
                        if g.buffer(-0.4).contains(P):
                            lados[lay] = uf.find((lay, j))
                if len(lados) == 2 and set(lados.values()) == {rt, raiz}:
                    cand.append((g_t.distance(P), x, y))
        if not cand:
            print('sem via de reforco para', t)
            break
        _, x, y = min(cand)
        novas.append({'net': 'GND', 'x': x, 'y': y, 'd': 0.8, 'furo': 0.4})
        furos.append(((x, y), 0.4))
        print(f'reforco do retorno: via 0,8/0,4 em ({x:.2f}; {y:.2f}) para {t}')
    pours = [r for r in placa.rows if r[0] == 'POUR']
    R.gravar_epro(placa, saida, lambda r: True, [], novas, pours=pours)
    return novas


if __name__ == '__main__' and sys.argv[1] == 'reforco':
    reforco_retorno(sys.argv[2], sys.argv[3])


def podar_gnd(entrada, saida, base=None, largura=1.0):
    """Tira vias e trechos de GND redundantes (os que nao sao do arquivo `base`), um por vez, do ultimo
    para o primeiro: fica de fora se todos os pads de GND continuam ligados ao J1.2 pelos planos
    simulados e os terminais de corrente continuam com caminho largo (>= largura) ate o J1.2.
    O cobre de GND nao muda os planos (eles so desviam de outras redes), entao os planos sao
    calculados uma vez so."""
    placa = C.Placa(entrada)
    objs = placa.objetos()
    pl = placa.planos_gnd(objs)
    ilhas = {lay: _partes(pl[lay]) for lay in (C.TOP, C.BOT)}
    largos = {lay: _partes(pl[lay].buffer(-largura / 2, quad_segs=4).buffer(largura / 2, quad_segs=4)) for lay in (C.TOP, C.BOT)}
    antigos = set()
    if base:
        pb = C.Placa(base)
        antigos = {t['id'] for t in pb.tracks} | {v['id'] for v in pb.vias}
    gnd = [o for o in objs if o['net'] == 'GND']
    candidatos = [k for k, o in enumerate(gnd) if o['tipo'] in ('via', 'trilha') and o['ref'] not in antigos
                  and not (o['tipo'] == 'via' and o['obj']['comp'])]

    def ok(fora):
        itens = [o for k, o in enumerate(gnd) if k not in fora]
        for partes, so_terminais in ((ilhas, False), (largos, True)):
            uf = UF()
            # ilhas: liga se o item toca a ilha com area (como em estado())
            for k, o in enumerate(itens):
                for lay in o['layers']:
                    for j, g in enumerate(partes[lay]):
                        if g.intersects(o['geom']) and (o['tipo'] == 'via' or g.intersection(o['geom']).area > (0.05 if so_terminais else SOBREPOSICAO_MIN)):
                            uf.union(('o', k), (lay, j))
            tree = STRtree([o['geom'] for o in itens])
            for k, o in enumerate(itens):
                for j in tree.query(o['geom'], predicate='intersects'):
                    j = int(j)
                    if j != k and o['layers'] & itens[j]['layers']:
                        uf.union(('o', k), ('o', j))
            ref = {o['ref']: k for k, o in enumerate(itens) if o['tipo'] == 'pad'}
            raiz = uf.find(('o', ref['J1.2']))
            alvo = TERMINAIS_CORRENTE if so_terminais else [o['ref'] for o in itens if o['tipo'] == 'pad']
            if any(uf.find(('o', ref[t])) != raiz for t in alvo if t in ref):
                return False
        return True
    if not ok(set()):
        print('aviso: a placa de entrada ja nao estava toda ligada')
    fora = set()
    for k in reversed(candidatos):
        if ok(fora | {k}):
            fora.add(k)
    retirar = {gnd[k]['ref'] for k in fora}
    print(f'GND redundante retirado: {sum(1 for k in fora if gnd[k]["tipo"] == "via")} vias, '
          f'{sum(1 for k in fora if gnd[k]["tipo"] == "trilha")} trechos')
    R.gravar_epro(placa, saida, lambda r: not (r[0] in ('LINE', 'VIA') and r[1] in retirar), [], [])
    return retirar


if __name__ == '__main__' and sys.argv[1] == 'podar':
    podar_gnd(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)


def ligar_drv(entrada, saida, w=0.3):
    """Pinos de GND do DRV8874 (U3, U4) ligados ao pad termico do proprio CI por dentro: trilha reta da
    ponta interna do pino ate o pad termico, para os pinos alinhados com ele; o pino vizinho de GND que
    nao fica alinhado (16) e ligado ao 15 por uma ponte nas pontas internas. Sem via. Recomendacao do
    datasheet; no EasyEDA o plano nao entra entre pinos a 0,65 mm (U3.7, U4.15/U4.16 ficavam soltos)."""
    placa = C.Placa(entrada)
    objs = placa.objetos()
    outros_top = unary_union([o['geom'] for o in objs if C.TOP in o['layers'] and o['net'] != 'GND'])
    livre = lambda pts: outros_top.distance(C.LineString(pts).buffer(w / 2, quad_segs=8)) >= 0.2 + 0.01
    novas = []
    for des in ('U3', 'U4'):
        pads = {p['num']: p for p in placa.pads if p['des'] == des}
        tp = pads['17']['geom']
        tx0, ty0, tx1, ty1 = tp.bounds
        tcy = (ty0 + ty1) / 2
        def ponta(p):
            x0, y0, x1, y1 = p['geom'].bounds
            cx = (x0 + x1) / 2
            return cx, (y0 + 0.1 if abs(y0 - tcy) < abs(y1 - tcy) else y1 - 0.1)
        alinhados = []
        for num, p in pads.items():
            if num == '17' or p['net'] != 'GND':
                continue
            cx, cy = ponta(p)
            if tx0 + 0.05 <= cx <= tx1 - 0.05:     # a ponta da trilha cai no pad termico
                ty = ty1 - 0.2 if cy > tcy else ty0 + 0.2
                if not livre([(cx, cy), (cx, ty)]):
                    print(f'  {des}.{num}: trilha de outra rede entre o pino e o pad termico; fica para as vias')
                    continue
                novas.append({'net': 'GND', 'layer': C.TOP, 'w': w, 'pts': [(cx, cy), (cx, ty)]})
                alinhados.append(num)
        def ponta_fora(p):
            x0, y0, x1, y1 = p['geom'].bounds
            return (x0 + x1) / 2, (y1 - 0.1 if abs(y1 - tcy) > abs(y0 - tcy) else y0 + 0.1)
        feitos = set()
        for num, p in pads.items():
            if num == '17' or p['net'] != 'GND' or num in alinhados:
                continue
            cx, cy = ponta(p)
            # pino de GND vizinho (passo 0,65): ponte nas pontas de dentro se o vizinho vai ao pad termico,
            # senao ponte nas pontas de fora (os dois ficam juntos para a via que vier depois)
            viz = [(n, q) for n, q in pads.items() if n != num and n != '17' and q['net'] == 'GND'
                   and abs(ponta(q)[1] - cy) < 1e-6 and abs(ponta(q)[0] - cx) < 0.7]
            for n, q in viz:
                if frozenset((num, n)) in feitos:
                    continue
                if n in alinhados:
                    pts = [(cx, cy), ponta(q)]
                else:
                    pts = [ponta_fora(p), ponta_fora(q)]
                if livre(pts):
                    novas.append({'net': 'GND', 'layer': C.TOP, 'w': w, 'pts': pts})
                    feitos.add(frozenset((num, n)))
        print(des, 'pinos de GND ligados ao pad termico:', alinhados)
    R.gravar_epro(placa, saida, lambda r: True, novas, [])
    return novas


if __name__ == '__main__' and sys.argv[1] == 'drv':
    ligar_drv(sys.argv[2], sys.argv[3])


def afastar_vias(entrada, saida, raio=1.6, passo=0.05):
    """Vias a menos de FOLGA_VIA_PAD de um pad SMD (regra "SMD Pad to Via" do EasyEDA, mesmo da mesma
    rede) vao para o ponto mais perto que respeite a regra, sem mudar as ligacoes: a via nova fica no
    mesmo pedaco de plano das duas faces; trilhas que terminavam nela sao esticadas ate o lugar novo; e,
    se a via encostava num pad da mesma rede, um toco de trilha liga o pad a ela."""
    import numpy as np
    placa = C.Placa(entrada)
    objs = placa.objetos()
    pl = placa.planos_gnd(objs)
    ilhas = {lay: _partes(pl[lay]) for lay in (C.TOP, C.BOT)}
    smd = [p for p in placa.pads if len(p['layers']) == 1]
    smd_u = unary_union([p['geom'] for p in smd])
    furos = [((v['x'], v['y']), v['furo'], v['id']) for v in placa.vias]
    furos += [(p['centro'], p['furo'], None) for p in placa.pads if p['furo'] and not p['des'].startswith('PAD:')]
    mover, novas_t = {}, []
    linhas_mod = {}
    for v in placa.vias:
        if v['comp']:
            continue
        P0 = Point(v['x'], v['y'])
        r = v['d'] / 2
        if smd_u.distance(P0) >= r + FOLGA_VIA_PAD - 1e-4:
            continue
        net = v['net']
        outros = {}
        for lay in (C.TOP, C.BOT):
            gs = [o['geom'] for o in objs if lay in o['layers'] and o['net'] != net and o['ref'] != v['id']]
            outros[lay] = unary_union(gs) if gs else None
        tocados = [p for p in smd if p['net'] == net and p['geom'].distance(P0) < r + 1e-3]
        ligadas = [t for t in placa.tracks if t['net'] == net and
                   min(math.dist(t['a'], (v['x'], v['y'])), math.dist(t['b'], (v['x'], v['y']))) < 1e-3]
        ilha0 = {}
        for lay in (C.TOP, C.BOT):
            ilha0[lay] = next((j for j, g in enumerate(ilhas[lay]) if g.contains(P0)), None)
        melhor = None
        for dx in np.arange(-raio, raio + 1e-9, passo):
            for dy in np.arange(-raio, raio + 1e-9, passo):
                d0 = math.hypot(dx, dy)
                if d0 > raio or (melhor and d0 >= melhor[0]):
                    continue
                x, y = v['x'] + dx, v['y'] + dy
                P = Point(x, y)
                if smd_u.distance(P) < r + FOLGA_VIA_PAD:
                    continue
                if not placa.borda.buffer(-(C.FOLGA_BORDA + r)).contains(P):
                    continue
                if any(outros[lay] is not None and outros[lay].distance(P) < r + 0.2 + 0.01 for lay in (C.TOP, C.BOT)):
                    continue
                if any(fid != v['id'] and math.dist((x, y), c) - f / 2 - v['furo'] / 2 < 0.3 + 0.01 for c, f, fid in furos):
                    continue
                if net == 'GND' and any(ilha0[lay] is not None and not ilhas[lay][ilha0[lay]].contains(P) for lay in (C.TOP, C.BOT)):
                    continue
                ok = True
                novos_pts = []
                for t in ligadas:
                    a = (x, y) if math.dist(t['a'], (v['x'], v['y'])) < 1e-3 else t['a']
                    b = (x, y) if math.dist(t['b'], (v['x'], v['y'])) < 1e-3 else t['b']
                    g = C.LineString([a, b]).buffer(t['w'] / 2, quad_segs=8)
                    if outros[t['layer']] is not None and outros[t['layer']].distance(g) < 0.2 + 0.01:
                        ok = False
                        break
                    novos_pts.append((t['id'], a, b))
                if not ok:
                    continue
                tocos = []
                for p in tocados:
                    lay = next(iter(p['layers']))
                    a, _ = nearest_points(p['geom'].buffer(-0.05), P)
                    toco = C.LineString([(a.x, a.y), (x, y)])
                    if outros[lay] is not None and outros[lay].distance(toco.buffer(W_GND / 2)) < 0.2 + 0.01:
                        ok = False
                        break
                    tocos.append({'net': net, 'layer': lay, 'w': W_GND, 'pts': [(a.x, a.y), (x, y)]})
                if ok:
                    melhor = (d0, x, y, novos_pts, tocos)
        if melhor is None:
            print('sem lugar para afastar a via', v['id'], net, (round(v['x'], 2), round(v['y'], 2)))
            continue
        d0, x, y, novos_pts, tocos = melhor
        mover[v['id']] = (x, y)
        for tid, a, b in novos_pts:
            linhas_mod[tid] = (a, b)
        novas_t += tocos
        furos = [(c, f, fid) if fid != v['id'] else ((x, y), f, fid) for c, f, fid in furos]
        print(f"via {v['id']} ({net}) movida {d0:.2f} mm; {len(tocos)} toco(s), {len(novos_pts)} trilha(s) esticada(s)")
    rows = []
    for r in placa.rows:
        if r[0] == 'VIA' and r[1] in mover:
            r = list(r)
            r[5], r[6] = R.mil(mover[r[1]][0]), R.mil(mover[r[1]][1])
        elif r[0] == 'LINE' and r[1] in linhas_mod:
            r = list(r)
            (ax, ay), (bx, by) = linhas_mod[r[1]]
            r[5], r[6], r[7], r[8] = R.mil(ax), R.mil(ay), R.mil(bx), R.mil(by)
        rows.append(r)
    placa.rows = rows
    R.gravar_epro(placa, saida, lambda r: True, novas_t, [])


if __name__ == '__main__' and sys.argv[1] == 'afastar':
    afastar_vias(sys.argv[2], sys.argv[3])


# ---------------------------------------------- EasyEDA: vias termicas como pads e ilhas sem pad
def vias_termicas_para_pads(entrada, saida, fp_uuid='77b480dde1d158db', numero='17'):
    """As vias do footprint do DRV8874 (dentro do pad termico) viram pads passantes com o numero do pad
    termico (17). A rede delas passa a vir do pino 17 do esquematico (GND), e nao de uma atribuicao feita
    na placa, que o EasyEDA apaga ao sincronizar com o esquematico ("Import Changes")."""
    import io
    import zipfile
    placa = C.Placa(entrada)
    nome_fp = f'FOOTPRINT/{fp_uuid}.efoo'
    linhas = C.linhas_json(placa.dados[nome_fp])
    novas, ids = [], []
    for r in linhas:
        if r[0] == 'VIA':
            # ["VIA", id, 0, rede, "", x, y, furo, diametro, ...] -> pad passante redondo
            novas.append(['PAD', r[1], 0, '', 12, numero, r[5], r[6], 0, ['ROUND', r[7], r[7]],
                          ['ELLIPSE', r[8], r[8]], [], 0, 0, 0, 1, 0, None, None, None, None, 0])
            ids.append(r[1])
        else:
            novas.append(r)
    print('vias do footprint convertidas em pads', numero, ':', ids)
    placa.dados[nome_fp] = ('\n'.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) for r in novas) + '\n').encode('utf8')
    comps = {c['id'] for c in placa.comps.values() if c['fp'] == fp_uuid}
    rows = []
    for r in placa.rows:
        if r[0] == 'PAD_NET' and r[1] in comps and r[4] in ids:
            r = [r[0], r[1], numero, 'GND', r[4], r[5]]
        rows.append(r)
    placa.rows = rows
    R.gravar_epro(placa, saida, lambda r: True, [], [])


def estado_estrito(placa, objs=None, folga=0.254, largura_min=0.15):
    """Como estado(), mas um pedaco de plano so conta se encostar num pad de GND (o EasyEDA, com a
    remocao de ilhas, apaga pedacos que so tem via ou trilha)."""
    objs = objs or placa.objetos()
    pl = placa.planos_gnd(objs, folga=folga, largura_min=largura_min)
    ilhas = {lay: _partes(pl[lay]) for lay in (C.TOP, C.BOT)}
    gnd = [o for o in objs if o['net'] == 'GND']
    pads = [o for o in gnd if o['tipo'] == 'pad']
    vivas = {}
    for lay in (C.TOP, C.BOT):
        vivas[lay] = [g for g in ilhas[lay] if any(lay in o['layers'] and g.intersection(o['geom']).area > 0.01 for o in pads)]
    uf = UF()
    for k, o in enumerate(gnd):
        uf.find(('obj', k))
        for lay in o['layers']:
            for j, g in enumerate(vivas[lay]):
                if g.intersects(o['geom']) and (o['tipo'] == 'via' or g.intersection(o['geom']).area > 0.01):
                    uf.union(('obj', k), (lay, j))
    tree = STRtree([o['geom'] for o in gnd])
    for k, o in enumerate(gnd):
        for j in tree.query(o['geom'], predicate='intersects'):
            j = int(j)
            if j != k and o['layers'] & gnd[j]['layers']:
                uf.union(('obj', k), ('obj', j))
    return vivas, gnd, uf


def ligar_estrito(entrada, saida, w=0.3, rodadas=8):
    """Liga, por trilha (e via, se precisar, sempre com trilha dos dois lados), cada grupo de GND que fica
    solto no modelo estrito ao grupo do J1.2. Devolve a lista dos grupos que nao deu para ligar ([] = ok)."""
    import grade as G
    atual = entrada
    for rodada in range(rodadas):
        placa = C.Placa(atual)
        objs = placa.objetos()
        vivas, gnd, uf = estado_estrito(placa, objs)
        raiz = uf.find(('obj', next(k for k, o in enumerate(gnd) if o['ref'] == 'J1.2')))
        grupos = collections.defaultdict(list)
        for k, o in enumerate(gnd):
            if uf.find(('obj', k)) != raiz:
                grupos[uf.find(('obj', k))].append(o)
        soltos = [g for g in grupos.values() if any(o['tipo'] == 'pad' for o in g)]
        print(f'rodada {rodada}: grupos de GND soltos (modelo estrito):', [[o['ref'] for o in g if o['tipo'] == 'pad'] for g in soltos])
        if not soltos:
            break
        alvo = {}
        for lay in (C.TOP, C.BOT):
            partes = [g for j, g in enumerate(vivas[lay]) if uf.find((lay, j)) == raiz]
            partes += [o['geom'] for k, o in enumerate(gnd) if lay in o['layers'] and uf.find(('obj', k)) == raiz]
            alvo[lay] = unary_union(partes)
        novas_t, novas_v = [], []
        falhas = []
        for g in soltos:          # liga o primeiro que der (o cobre novo muda o resto)
            r0 = uf.find(('obj', gnd.index(g[0])))
            orig = {}
            for lay in (C.TOP, C.BOT):
                gs = [o['geom'] for o in g if lay in o['layers']]
                gs += [h for j, h in enumerate(vivas[lay]) if uf.find((lay, j)) == r0]
                if gs:
                    orig[lay] = unary_union(gs)
            r = None
            for margem in (4.0, 9.0):
                r = G.rotear(placa, objs, 'GND', orig, alvo, w, via=VIA_GND, margem=margem, custo_via=200)
                if r:
                    break
            nomes = [o['ref'] for o in g if o['tipo'] == 'pad']
            if not r:
                falhas.append(nomes)
                continue
            print('  ', nomes, f"-> {len(r['trilhas'])} trilha(s), {len(r['vias'])} via(s)")
            novas_t += r['trilhas']
            novas_v += r['vias']
            break
        if not novas_t and not novas_v:
            print('  sem caminho para', falhas)
            import shutil
            shutil.copy(atual, saida)
            if atual != entrada:
                os.remove(atual)
            return falhas
        prox = saida + f'.e{rodada}.tmp'
        R.gravar_epro(placa, prox, lambda r: True, novas_t, novas_v)
        if atual != entrada:
            os.remove(atual)
        atual = prox
    import shutil
    shutil.copy(atual, saida)
    if atual != entrada:
        os.remove(atual)
    return []
