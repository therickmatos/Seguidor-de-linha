"""Roteamento da placa base do RUSH a partir do .epro do Erick (08/11/2026).

  python rush_rotear.py sinais  entrada.epro pasta   # etapa 1: sinais e +5V no FreeRouting
  python rush_rotear.py aplicar entrada.epro pasta saida.epro

Etapa 1: mantem a potencia e o cristal roteados pelo agente anterior (VBAT, OUT_A1/A2/B1/B2, OUT_C,
XTAL1, XTAL2) como cobre fixo; apaga o resto (sinais, +5V, tocos de GND) e roteia de novo com o
FreeRouting 1.9.0, com a face de baixo mais cara para ela ficar livre para o plano de GND.
O GND nao entra nesta etapa (vira pinos isolados = obstaculos).

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import collections
import json
import os
import sys

import easyeda_cobre as C
import easyeda_rotear as R

FIXAS = {'VBAT', 'OUT_A1', 'OUT_A2', 'OUT_B1', 'OUT_B2', 'OUT_C', 'XTAL1', 'XTAL2'}


def larguras(redes):
    w = {n: (0.5 if n == '+5V' else 0.25) for n in redes}
    w.update({'VBAT': 1.5, 'OUT_A1': 1.5, 'OUT_A2': 1.5, 'OUT_B1': 1.5, 'OUT_B2': 1.5, 'OUT_C': 1.0})
    return w


def autoroute(custo_b=3.0, via=50):
    """Custos do FreeRouting (bloco logo depois das camadas): face de baixo mais cara."""
    return [
        '    (autoroute_settings',
        '      (fanout off)', '      (autoroute on)', '      (postroute on)', '      (vias on)',
        f'      (via_costs {via})', '      (plane_via_costs 5)', '      (start_ripup_costs 100)', '      (start_pass_no 1)',
        '      (layer_rule F', '        (active on)', '        (preferred_direction horizontal)',
        '        (preferred_direction_trace_costs 1.0)', '        (against_preferred_direction_trace_costs 1.5)', '      )',
        '      (layer_rule B', '        (active on)', '        (preferred_direction vertical)',
        f'        (preferred_direction_trace_costs {custo_b})',
        f'        (against_preferred_direction_trace_costs {custo_b * 1.3:.2f})', '      )',
        '    )']


def etapa_sinais(entrada, pasta, passes=60, custo_b=3.0, via=50, continuar=None):
    os.makedirs(pasta, exist_ok=True)
    placa = C.Placa(entrada)
    redes = sorted({p['net'] for p in placa.pads if p['net']})
    rotear = set(redes) - FIXAS - {'GND'}
    fixo = lambda o: o['net'] in FIXAS or o['net'] == 'GND'     # GND: so o fanout feito antes
    dsn = os.path.join(pasta, 'sinais.dsn')
    ses = os.path.join(pasta, 'sinais.ses')
    livres = None
    if continuar:
        ids0 = json.load(open(os.path.join(continuar, 'ids.json')))
        tr, vi = R.ler_ses(os.path.join(continuar, 'sinais.ses'), ids0)
        livres = {'trilhas': [t for t in tr if not t['fixo'] and t['net'] in rotear],
                  'vias': [v for v in vi if not v['fixo'] and v['net'] in rotear]}
        # RIP="x,y,r;...": arranca as trilhas/vias que passam a menos de r de (x, y)
        from shapely.geometry import LineString, Point
        for zona in filter(None, os.environ.get('RIP', '').split(';')):
            x, y, r = map(float, zona.split(','))
            P = Point(x, y)
            livres['trilhas'] = [t for t in livres['trilhas']
                                 if (LineString(t['pts']) if len(t['pts']) > 1 else Point(t['pts'][0])).distance(P) > r]
            livres['vias'] = [v for v in livres['vias'] if Point(v['x'], v['y']).distance(P) > r]
    ids = R.escrever_dsn(placa, dsn, fixo, rotear | (FIXAS & set(redes)), larguras(rotear),
                         autoroute=autoroute(custo_b, via), livres=livres)
    json.dump(ids, open(os.path.join(pasta, 'ids.json'), 'w'), indent=1)
    ok = R.rodar(dsn, ses, passes=passes, log=os.path.join(pasta, 'sinais.log'))
    print('SES gerado' if ok else 'FreeRouting sem SES')


def aplicar(entrada, pasta, saida, nome_ses='sinais.ses'):
    placa = C.Placa(entrada)
    ids = json.load(open(os.path.join(pasta, 'ids.json')))
    tr, vi = R.ler_ses(os.path.join(pasta, nome_ses), ids)
    tr = [t for t in tr if not t['fixo'] and t['net'] and t['net'] not in FIXAS]
    vi = [v for v in vi if not v['fixo'] and v['net'] and v['net'] not in FIXAS]
    manter = lambda r: r[3] in FIXAS or r[3] == 'GND'
    R.gravar_epro(placa, saida, manter, tr, vi)
    print(f'{len(tr)} trilhas, {len(vi)} vias novas -> {saida}')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'sinais':
        etapa_sinais(sys.argv[2], sys.argv[3], int(os.environ.get('PASSES', 60)), float(os.environ.get('CUSTO_B', 3.0)),
                     int(os.environ.get('VIA', 50)), os.environ.get('CONTINUAR'))
    elif cmd == 'aplicar':
        aplicar(sys.argv[2], sys.argv[3], sys.argv[4], *sys.argv[5:])


def fechar(entrada, saida, custo_b=2.0):
    """Fecha as ligacoes de sinal que o FreeRouting deixou abertas, com o roteador de grade."""
    import grade as G
    placa = C.Placa(entrada)
    objs = placa.objetos()
    redes = sorted({p['net'] for p in placa.pads if p['net']} - FIXAS - {'GND'})
    novas_t, novas_v = [], []
    for net in redes:
        while True:
            ilhas = G.ilhas_da_rede(placa, objs, net)
            if len(ilhas) < 2:
                break
            ilhas.sort(key=lambda g: len(g))
            orig = G.por_camada(ilhas[0])
            alvo = G.por_camada([o for g in ilhas[1:] for o in g])
            w = larguras({net})[net]
            r = None
            for margem in (4.0, 10.0, 25.0):
                r = G.rotear(placa, objs, net, orig, alvo, w, margem=margem,
                             custo_camada={C.TOP: 1.0, C.BOT: custo_b})
                if r:
                    break
            if not r:
                print('sem caminho:', net, [o['ref'] for o in ilhas[0] if o['tipo'] == 'pad'])
                break
            print(f"{net}: {len(r['trilhas'])} trilhas, {len(r['vias'])} vias")
            novas_t += r['trilhas']
            novas_v += r['vias']
            # acrescenta o cobre novo aos objetos (para as proximas ligacoes)
            for t in r['trilhas']:
                for a, b in zip(t['pts'], t['pts'][1:]):
                    tt = {'id': 'novo', 'net': net, 'layer': t['layer'], 'a': a, 'b': b, 'w': w}
                    objs.append({'tipo': 'trilha', 'net': net, 'layers': {t['layer']},
                                 'geom': C.LineString([a, b]).buffer(w / 2, quad_segs=8), 'ref': 'novo', 'obj': tt})
            for v in r['vias']:
                objs.append({'tipo': 'via', 'net': net, 'layers': {C.TOP, C.BOT},
                             'geom': C.Point(v['x'], v['y']).buffer(v['d'] / 2, quad_segs=12), 'ref': 'novo', 'obj': v})
    R.gravar_epro(placa, saida, lambda r: True, novas_t, novas_v, prefixo='c')
    return novas_t, novas_v


if __name__ == '__main__' and sys.argv[1] == 'fechar':
    fechar(sys.argv[2], sys.argv[3])


def fanout(entrada, saida):
    """Toco curto + via em cada pad SMD de GND, antes dos sinais (so a potencia e o cristal ficam)."""
    import grade as G
    p0 = C.Placa(entrada)
    base = saida + '.base.tmp'
    R.gravar_epro(p0, base, lambda r: r[3] in FIXAS, [], [])
    placa = C.Placa(base)
    objs = placa.objetos()
    novas_t, novas_v, falhas = [], [], []
    pads = [p for p in placa.pads if p['net'] == 'GND' and len(p['layers']) == 1
            and (p['des'], p['num']) not in (('U3', '17'), ('U4', '17'))]
    for p in sorted(pads, key=lambda q: (q['des'], q['num'])):
        lay = next(iter(p['layers']))
        outra = C.BOT if lay == C.TOP else C.TOP
        r = G.rotear(placa, objs, 'GND', {lay: p['geom']}, {outra: placa.borda}, 0.3, via=(0.6, 0.3),
                     margem=3.0, passo=0.05, custo_via=20)
        if not r:
            falhas.append(f"{p['des']}.{p['num']}")
            continue
        novas_t += r['trilhas']
        novas_v += r['vias']
        for t in r['trilhas']:
            for a, b in zip(t['pts'], t['pts'][1:]):
                objs.append({'tipo': 'trilha', 'net': 'GND', 'layers': {t['layer']},
                             'geom': C.LineString([a, b]).buffer(0.15, quad_segs=8), 'ref': 'fan', 'obj': None})
        for v in r['vias']:
            objs.append({'tipo': 'via', 'net': 'GND', 'layers': {C.TOP, C.BOT},
                         'geom': C.Point(v['x'], v['y']).buffer(0.3, quad_segs=12), 'ref': 'fan', 'obj': v})
    print(f'fanout: {len(pads)} pads, {len(novas_v)} vias, falhas {falhas}')
    R.gravar_epro(placa, saida, lambda r: True, novas_t, novas_v, prefixo='n')
    os.remove(base)


if __name__ == '__main__' and sys.argv[1] == 'fanout':
    fanout(sys.argv[2], sys.argv[3])


def podar(placa):
    """Ids de trilhas e vias de sinal mortas: trilha com ponta que nao encosta em nada da rede
    (repetido ate estabilizar) e via que so toca cobre de uma face."""
    from shapely.geometry import Point
    mortos = set()
    sinal = lambda n: n and n not in FIXAS and n != 'GND'
    while True:
        objs = [o for o in placa.objetos() if not (o['tipo'] in ('trilha', 'via') and o['ref'] in mortos)]
        por_rede = collections.defaultdict(list)
        for o in objs:
            por_rede[o['net']].append(o)
        novos = set()
        for o in objs:
            if o['tipo'] == 'trilha' and sinal(o['net']):
                t = o['obj']
                for ponta in (t['a'], t['b']):
                    P = Point(ponta)
                    if not any(q is not o and t['layer'] in q['layers'] and q['geom'].distance(P) < 0.01
                               for q in por_rede[o['net']]):
                        novos.add(o['ref'])
            elif o['tipo'] == 'via' and sinal(o['net']) and not o['obj']['comp']:
                faces = {lay for q in por_rede[o['net']] if q is not o and q['tipo'] != 'via'
                         for lay in q['layers'] if q['geom'].intersects(o['geom'])}
                if len(faces) < 2:
                    novos.add(o['ref'])
        if not novos - mortos:
            return mortos
        mortos |= novos


def finalizar(entrada, saida):
    """Planos de GND (POUR nas duas faces, retangulo que cobre a placa: o EasyEDA recorta pelo contorno)
    e pontas de VBAT do agente que so encostavam na borda do pad levadas ao centro do pad."""
    placa = C.Placa(entrada)
    centro = {f"{p['des']}.{p['num']}": p['centro'] for p in placa.pads}
    # trilha -> (ponta, pad): pontas a menos de 0,7 mm do centro de um pad da mesma rede, fora dele
    ajustes = {'e100245': ('b', 'C17.1'), 'e100256': ('b', 'D1.1')}
    rows = []
    for r in placa.rows:
        if r[0] == 'LINE' and r[1] in ajustes:
            ponta, pad = ajustes[r[1]]
            x, y = centro[pad]
            r = list(r)
            if ponta == 'b':
                r[7], r[8] = R.mil(x), R.mil(y)
            else:
                r[5], r[6] = R.mil(x), R.mil(y)
        rows.append(r)
    placa.rows = rows
    mortos = podar(placa)
    print('trilhas/vias de sinal mortas retiradas:', sorted(mortos))
    placa.rows = [r for r in rows if not (r[0] in ('LINE', 'VIA') and r[1] in mortos)]
    x0, y0, x1, y1 = placa.borda.bounds
    m = 2.0
    ret = ['R', R.mil(x0 - m), R.mil(y1 + m), R.mil(x1 - x0 + 2 * m), R.mil(y1 - y0 + 2 * m), 0, 0]
    pours = [['POUR', None, 0, 'GND', C.TOP, 0.2, 'GND_CIMA', 0, [ret], ['SOLID', 8], 0, 0],
             ['POUR', None, 0, 'GND', C.BOT, 0.2, 'GND_BAIXO', 0, [ret], ['SOLID', 8], 0, 0]]
    R.gravar_epro(placa, saida, lambda r: True, [], [], pours=pours, prefixo='z')


if __name__ == '__main__' and sys.argv[1] == 'finalizar':
    finalizar(sys.argv[2], sys.argv[3])


def refazer_rede(entrada, saida, net, custo_b=3.0, custo_via=250):
    """Arranca uma rede de sinal inteira e refaz com o roteador de grade (face de baixo custo_b vezes
    mais cara, via custando custo_via passos de grade)."""
    import grade as G
    p0 = C.Placa(entrada)
    ids = {t['id'] for t in p0.tracks if t['net'] == net} | {v['id'] for v in p0.vias if v['net'] == net and not v['comp']}
    tmp = saida + '.tmp'
    R.gravar_epro(p0, tmp, lambda r: not (r[0] in ('LINE', 'VIA') and r[1] in ids), [], [])
    placa = C.Placa(tmp)
    objs = placa.objetos()
    w = larguras({net})[net]
    tr, vi = [], []
    while True:
        ilhas = G.ilhas_da_rede(placa, objs, net)
        if len(ilhas) < 2:
            break
        ilhas.sort(key=len)
        r = None
        for margem in (4.0, 10.0, 25.0):
            r = G.rotear(placa, objs, net, G.por_camada(ilhas[0]), G.por_camada([o for g in ilhas[1:] for o in g]), w,
                         margem=margem, custo_camada={C.TOP: 1.0, C.BOT: custo_b}, custo_via=custo_via)
            if r:
                break
        if not r:
            raise SystemExit(f'sem caminho para {net}')
        tr += r['trilhas']
        vi += r['vias']
        for t in r['trilhas']:
            for a, b in zip(t['pts'], t['pts'][1:]):
                objs.append({'tipo': 'trilha', 'net': net, 'layers': {t['layer']},
                             'geom': C.LineString([a, b]).buffer(w / 2, quad_segs=8), 'ref': 'novo', 'obj': None})
        for v in r['vias']:
            objs.append({'tipo': 'via', 'net': net, 'layers': {C.TOP, C.BOT},
                         'geom': C.Point(v['x'], v['y']).buffer(v['d'] / 2, quad_segs=12), 'ref': 'novo', 'obj': v})
    R.gravar_epro(placa, saida, lambda r: True, tr, vi)
    os.remove(tmp)
    print(f'{net}: {len(tr)} trilhas, {len(vi)} vias')


if __name__ == '__main__' and sys.argv[1] == 'refazer':
    refazer_rede(sys.argv[2], sys.argv[3], sys.argv[4])
