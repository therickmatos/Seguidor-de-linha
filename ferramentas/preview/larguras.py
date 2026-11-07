"""Conferencia das larguras das trilhas de corrente da placa (07/11/2026).

Para cada rede de potencia:
  1. monta o grafo do cobre (pads, trilhas, vias) e poda os ramos sem saida que nao levam a um
     terminal de corrente (capacitor de 100 nF, divisor de tensao...): o que sobra e o caminho por
     onde a corrente passa de fato;
  2. nesse caminho, mede cada trilha abaixo da largura minima da rede, descontando o "pescoco"
     junto dos pinos de passo fino (DRV8874, 0,65 mm), onde a trilha nao pode ser mais larga
     que o proprio pino;
  3. estima a capacidade pela IPC-2221 (camada externa, 1 oz) e a queda de tensao.

Uso:  python larguras.py [v2/cobre_v2.json]

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import collections
import json
import math
import sys

from shapely.geometry import LineString, Point
from shapely.ops import substring
from shapely.ops import unary_union
from shapely.strtree import STRtree

import layout_placa as M
import placa_v2 as V
import rotear_v2 as R

RHO_CU = 1.72e-8            # ohm.m (20 C)
ESPESSURA_1OZ = 0.035       # mm

# rede: (terminais de corrente, corrente tipica A, pico A, largura minima no caminho mm)
REDES = {
    'VBAT': (['J1.1', 'U3.11', 'U4.11', 'M3.1', 'D1.1', 'C1.1', 'C2.1'], 3.0, 8.0, 1.0),
    'VBAT ao 78M05': (['J1.1', 'U1.1'], 0.25, 0.4, 0.4),
    'OUT_A1': (['U3.8', 'M1.2'], 1.0, 3.0, 1.0),
    'OUT_A2': (['U3.10', 'M1.1'], 1.0, 3.0, 1.0),
    'OUT_B1': (['U4.8', 'M2.2'], 1.0, 3.0, 1.0),
    'OUT_B2': (['U4.10', 'M2.1'], 1.0, 3.0, 1.0),
    'OUT_C': (['M3.2', 'Q1.3', 'D1.2'], 1.5, 3.0, 1.0),
    '+5V': (None, 0.25, 0.4, 0.4),      # None: todos os pads da rede sao terminais
}
PASSO_FINO = ('U3', 'U4')    # pinos de 0,45 mm: a trilha sai na largura do pino
PESCOCO_MM = 2.6             # distancia ao centro do pino de passo fino em que o pescoco e aceito


def ipc2221_externa(largura_mm, dt=10.0, oz=1.0):
    """Corrente (A) para elevacao `dt` (C) numa trilha externa (IPC-2221: I = 0,048 dT^0,44 A^0,725)."""
    area_mil2 = (largura_mm / 0.0254) * (1.378 * oz)
    return 0.048 * dt ** 0.44 * area_mil2 ** 0.725


def mohm_por_mm(largura_mm, oz=1.0):
    return RHO_CU / (largura_mm * 1e-3 * ESPESSURA_1OZ * oz * 1e-3) * 1e3 * 1e-3


def caminho_de_corrente(objs, net, terminais):
    """Objetos da rede por onde a corrente pode passar entre terminais.

    Um objeto fica de fora quando existe um ponto de articulacao do grafo que o separa de todos os
    terminais (ramo sem saida: capacitor de 100 nF, divisor de tensao...). Isso funciona mesmo com
    pedacos curtos de trilha que se tocam em triangulo.
    """
    itens = [o for o in objs if o['net'] == net]
    viz = collections.defaultdict(set)
    tree = STRtree([o['geom'] for o in itens])
    for i, o in enumerate(itens):
        for j in tree.query(o['geom'].buffer(0.001)):
            j = int(j)
            if j != i and o['layers'] & itens[j]['layers'] and o['geom'].distance(itens[j]['geom']) < 0.001:
                viz[i].add(j)
                viz[j].add(i)
    term = {i for i, o in enumerate(itens) if o['pad'] in terminais}
    mortos = set()
    for a in range(len(itens)):
        vistos = {a}
        for s in viz[a]:
            if s in vistos:
                continue
            comp, pilha = {s}, [s]
            while pilha:
                u = pilha.pop()
                for w in viz[u]:
                    if w not in vistos and w not in comp:
                        comp.add(w)
                        pilha.append(w)
            vistos |= comp
            if not comp & term:
                mortos |= comp
    # cobre solto (sem ligacao a nada) tambem nao conduz
    return [o for i, o in enumerate(itens) if i not in mortos and (viz[i] or i in term)]


def trecho_percorrido(L, largura, vizinhos):
    """Parte da linha central que a corrente percorre: entre os dois contatos mais afastados com o resto
    do caminho. Um ramo que so encosta no tronco por uma ponta nao e percorrido."""
    ints = []
    for g in vizinhos:
        c = L.intersection(g.buffer(largura / 2 + 0.001))
        if c.is_empty:
            continue
        ds = [L.project(Point(xy)) for part in getattr(c, 'geoms', [c]) for xy in part.coords]
        ints.append((min(ds), max(ds)))
    if len(ints) < 2:
        return None
    a = min(hi for lo, hi in ints)
    b = max(lo for lo, hi in ints)
    return substring(L, a, b) if b - a > 1e-3 else None


def analisar(cobre, positions=None):
    positions = positions or V.load()
    tracks, vias = cobre['tracks'], cobre['vias']
    objs = R.copper_objects(positions, tracks, vias)
    por_id = {t['id']: t for t in tracks}
    pinos_finos = [p['shape'].centroid for p in M.all_pads(positions) if p['ref'] in PASSO_FINO]
    zona_pescoco = unary_union([c.buffer(PESCOCO_MM) for c in pinos_finos])
    out = {}
    for nome, (terminais, i_tip, i_pico, minimo) in REDES.items():
        net = nome.split()[0]
        if terminais is None:
            terminais = [o['pad'] for o in objs if o['net'] == net and o['pad']]
        caminho = caminho_de_corrente(objs, net, terminais)
        trilhas = [por_id[o['name']] for o in caminho if o['name'] in por_id]
        largos = [o['geom'] for o in caminho
                  if o['pad'] or (o['name'] in por_id and por_id[o['name']]['width'] + 1e-6 >= minimo)]
        cobre_largo = unary_union(largos) if largos else None
        hist = collections.Counter()
        finas, pescocos, percorridas = [], [], []
        for t in trilhas:
            L = LineString(t['xy'])
            # so o trecho que a corrente atravessa (entre os contatos com o resto do caminho)
            g = L.buffer(t['width'] / 2)
            viz = [o['geom'] for o in caminho if o['name'] != t['id'] and t['layer'] in o['layers']
                   and o['geom'].distance(g) < 0.001]
            perc = trecho_percorrido(L, t['width'], viz)
            if perc is None:
                continue
            percorridas.append(t)
            hist[round(t['width'], 2)] += L.length
            if t['width'] + 1e-6 >= minimo:
                continue
            # o que estiver coberto por cobre largo da mesma rede (pad ou trilha larga) nao conta
            resto = perc.difference(zona_pescoco)
            if cobre_largo is not None:
                resto = resto.difference(cobre_largo)
            fora = resto.length
            item = {'id': t['id'], 'face': 'cima' if t['layer'] == 1 else 'baixo', 'largura': t['width'],
                    'comprimento': round(perc.length, 2), 'fora_do_pescoco': round(fora, 2),
                    'de': [round(v, 2) for v in t['xy'][0]], 'ate': [round(v, 2) for v in t['xy'][-1]]}
            (finas if fora > 0.3 else pescocos).append(item)
        trilhas = percorridas
        vias_net = [o for o in caminho if o['name'] in {v['id'] for v in vias}]
        mais_fina = min((t['width'] for t in trilhas), default=None)
        out[nome] = {
            'terminais': REDES[nome][0] or 'todos os pads', 'corrente_tipica_A': i_tip, 'pico_A': i_pico, 'largura_minima_mm': minimo,
            'comprimento_por_largura_mm': {f'{w:.2f}': round(l, 1) for w, l in sorted(hist.items())},
            'trilha_mais_fina_mm': mais_fina,
            'capacidade_da_mais_fina_A_10C': round(ipc2221_externa(mais_fina), 2) if mais_fina else None,
            'pescocos_nos_pinos': pescocos,
            'finas_fora_dos_pinos': finas,
            'vias_no_caminho': len(vias_net),
        }
    return out


def tabela_ipc():
    return [(w, round(ipc2221_externa(w, 10), 1), round(ipc2221_externa(w, 20), 1), round(mohm_por_mm(w), 2))
            for w in (0.25, 0.4, 0.6, 0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0)]


def main():
    arq = sys.argv[1] if len(sys.argv) > 1 else str(M.HERE / 'v2' / 'cobre_v2.json')
    res = analisar(json.load(open(arq, encoding='utf8')))
    print('IPC-2221, externa, 1 oz: largura -> A (+10 C) / A (+20 C) / mohm por mm')
    for w, a10, a20, r in tabela_ipc():
        print(f'  {w:4.2f} mm -> {a10:4.1f} / {a20:4.1f} A   {r:5.2f} mohm/mm')
    for net, r in res.items():
        print(f"\n{net}: tipica {r['corrente_tipica_A']} A, pico {r['pico_A']} A, minimo {r['largura_minima_mm']} mm")
        print('  caminho da corrente (mm de trilha por largura):', r['comprimento_por_largura_mm'])
        print('  pescocos nos pinos do DRV8874:', [(p['largura'], p['comprimento']) for p in r['pescocos_nos_pinos']])
        print('  FINAS FORA DOS PINOS:', r['finas_fora_dos_pinos'] or 'nenhuma')
        print('  vias no caminho:', r['vias_no_caminho'])
    return res


if __name__ == '__main__':
    main()
