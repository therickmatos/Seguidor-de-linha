"""Extrai e classifica cobre EVA-RT; calcula ligacoes ainda desconectadas.

As primitivas de origem e suas redes sao preservadas em trilhas_classificadas.json.
Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import collections
import json
import math
from pathlib import Path

from shapely.geometry import LineString, Point
from shapely.ops import nearest_points, unary_union
from shapely.strtree import STRtree

import layout_placa as M

MIL = 0.0254
GAP = 0.20
PCB = M.HERE / 'eprj' / 'eva_rt_pcb_b73a4a.txt'

MAP = {
    'VCC': 'VBAT', '+5V': '+5V', 'GND': 'GND', 'RESET': 'RESET',
    'Y0/A5': 'MARK_L_A5', 'Y1/A6': 'MARK_R_A6', 'C0/A4': 'C0_A4',
    'RX/D0': 'RX_D0', 'TX/D1': 'TX_D1',
    'LED1/D2': 'LEDA_D2', 'LED2/D7': 'LEDB_D7', 'LED3/D13': 'LEDC_D13',
    '$U1_7': 'XTAL1', '$U1_8': 'XTAL2', '$C10_1': 'AREF',
    '$Q1_1': 'Net-(Q1-G)', '$R20_2': 'Net-(S0-A)', '$R21_2': 'Net-(S1-A)',
}
for old, new in [('DIRA/D3','DIRA_D3'), ('DIRB/D4','DIRB_D4'),
                 ('PWMA/D5','PWMA_D5'), ('PWMB/D6','PWMB_D6'),
                 ('PWMC/D10','PWMC_D10'), ('B1/D11','B1_D11'), ('B2/D12','B2_D12')]:
    MAP[old] = new
for i in range(4):
    MAP[f'S{i}/A{i}'] = f'S{i}_A{i}'
for s in ('OUT_A1','OUT_A2','OUT_B1','OUT_B2','OUT_C'):
    MAP[s] = s
for i in (1,2,4,5,6,7):
    MAP[f'$LED{i}_2'] = f'Net-(LED{i}-A)'

def records():
    if not PCB.exists():
        import extrair_eprj
        extrair_eprj.decodificar()
    lines = PCB.read_text(encoding='utf8').splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith('["DOCTYPE","PCB"'))
    out = []
    for line in lines[start:]:
        try:
            out.append(json.loads(line))
        except (ValueError, TypeError):
            continue
    return out

def extract():
    lines, vias = [], []
    counts = collections.Counter()
    for row in records():
        typ = row[0]
        if typ == 'LINE' and row[4] in (1,2):
            counts['LINE'] += 1
            _, ident, _, oldnet, layer, x1, y1, x2, y2, width, *_ = row
            lines.append({'id': ident, 'old_net': oldnet, 'net': MAP.get(oldnet),
                          'layer': layer, 'width': width*MIL,
                          'xy': [[x1*MIL,y1*MIL], [x2*MIL,y2*MIL]], 'type':'LINE'})
        elif typ == 'POLY' and row[4] in (1,2):
            counts['POLY'] += 1
            _, ident, _, oldnet, layer, width, path, *_ = row
            # Os dois POLY de cobre do projeto sao polilinhas com comando L.
            if len(path) < 5 or path[2] != 'L':
                raise ValueError(f'POLY de cobre desconhecido: {ident}')
            nums = [v for v in path if isinstance(v, (int,float))]
            points = [[nums[i]*MIL, nums[i+1]*MIL] for i in range(0,len(nums),2)]
            for i, (a,b) in enumerate(zip(points,points[1:])):
                lines.append({'id': f'{ident}:{i}', 'old_net': oldnet, 'net': MAP.get(oldnet),
                              'layer': layer, 'width': width*MIL, 'xy': [a,b], 'type':'POLY'})
        elif typ == 'VIA':
            counts['VIA'] += 1
            _, ident, _, oldnet, _, x, y, drill, diameter, *_ = row
            vias.append({'id':ident, 'old_net':oldnet, 'net':MAP.get(oldnet),
                         'xy':[x*MIL,y*MIL], 'drill':drill*MIL, 'diameter':diameter*MIL})
    return lines, vias, counts

def parts(g):
    if g.is_empty:
        return []
    if g.geom_type == 'LineString':
        return [g]
    if hasattr(g, 'geoms'):
        return [x for item in g.geoms for x in parts(item)]
    return []

def _blocker(pads, net, layers):
    geoms = [p['shape'] for p in pads if set(p['layers']).intersection(layers)
             and (p['net'] != net or p['net'] is None)]
    return unary_union(geoms) if geoms else None

def classify(positions):
    originals, original_vias, counts = extract()
    pads = M.all_pads(positions)
    netnames = {x['net'] for x in originals+original_vias if x['net']}
    blockers = {(net,layer): _blocker(pads,net,(layer,)) for net in netnames for layer in (1,2)}
    via_blockers = {net: _blocker(pads,net,(1,2)) for net in netnames}
    via_out = []
    # Aceita primeiro vias de maior diametro; nenhuma pode tocar pad de outra rede.
    accepted_vias = []
    for v in sorted(original_vias,key=lambda v:-v['diameter']):
        point = Point(v['xy'])
        copper = point.buffer(v['diameter']/2,quad_segs=12)
        why = ''
        if not v['net']:
            why = 'rede removida ou sem correspondencia'
        elif not M.BOARD.buffer(-GAP).covers(copper):
            why = 'contorno/furo'
        elif via_blockers[v['net']] is not None and copper.distance(via_blockers[v['net']]) < GAP-1e-7:
            why = 'conflito com pad novo'
        elif any(v['net'] != old['net'] and copper.distance(old['geom']) < GAP-1e-7 for old in accepted_vias):
            why = 'folga para outra via'
        v['status'] = 'removida' if why else 'mantida'
        v['motivo'] = why
        if not why:
            accepted_vias.append({'net':v['net'],'geom':copper})
        via_out.append(v)

    # Cortamos somente o trecho que colidiria, mantendo os segmentos restantes.
    accepted = []
    classified = []
    for r in sorted(originals,key=lambda r:-math.dist(*r['xy'])):
        original = LineString(r['xy'])
        width = r['width']
        if not r['net']:
            classified.append({**r,'status':'removida','motivo':'rede removida ou sem correspondencia'})
            continue
        valid = original.intersection(M.BOARD.buffer(-(width/2+GAP)))
        blocker = blockers[(r['net'],r['layer'])]
        if blocker is not None and not valid.is_empty:
            valid = valid.difference(blocker.buffer(width/2+GAP))
        for via in accepted_vias:
            if via['net'] != r['net'] and not valid.is_empty and valid.distance(via['geom']) < width/2+GAP:
                valid = valid.difference(via['geom'].buffer(width/2+GAP))
        # Mantem a folga mesmo onde o desenho original era mais apertado.
        if not valid.is_empty:
            for old in accepted:
                if old['layer'] != r['layer'] or old['net'] == r['net']:
                    continue
                if valid.distance(old['geom']) < width/2+GAP:
                    valid = valid.difference(old['geom'].buffer(width/2+GAP))
                    if valid.is_empty:
                        break
        pieces = [p for p in parts(valid) if p.length >= 0.15]
        if not pieces:
            classified.append({**r,'status':'removida','motivo':'colisao/folga apos mudancas'})
            continue
        changed = sum(p.length for p in pieces) < original.length-0.01 or len(pieces)>1
        for p in pieces:
            xy = [[float(x),float(y)] for x,y in p.coords]
            item = {**r,'xy':xy,'status':'ajustada' if changed else 'mantida',
                    'motivo':'recortada para nova geometria e folga' if changed else ''}
            classified.append(item)
            accepted.append({'net':r['net'],'layer':r['layer'],
                             'geom':p.buffer(width/2,cap_style='round',quad_segs=8)})
        if changed:
            classified.append({**r,'status':'removida','motivo':'trecho original substituido/recortado', 'original_recortado':True})
    return {'source_counts':dict(counts),'tracks':classified,'vias':via_out}

def connectivity(positions, tracks, vias):
    """Agrupa pads e cobre efetivamente encostados; devolve ratsnest por MST."""
    nets = collections.defaultdict(list)
    for p in M.all_pads(positions):
        if p['net']:
            nets[p['net']].append({'geom':p['shape'], 'layers':set(p['layers']),
                                   'pad':f"{p['ref']}.{p['pin']}"})
    for t in tracks:
        if t['status'] in ('mantida','ajustada','nova'):
            nets[t['net']].append({'geom':LineString(t['xy']).buffer(t['width']/2,quad_segs=8),
                                   'layers':{t['layer']}, 'pad':None})
    for v in vias:
        if v['status'] in ('mantida','nova'):
            nets[v['net']].append({'geom':Point(v['xy']).buffer(v['diameter']/2,quad_segs=8),
                                   'layers':{1,2}, 'pad':None})
    all_edges = []
    summary = {}
    for net, nodes in nets.items():
        parent=list(range(len(nodes)))
        def find(i):
            while parent[i]!=i:
                parent[i]=parent[parent[i]]; i=parent[i]
            return i
        def union(i,j):
            a,b=find(i),find(j)
            if a!=b: parent[b]=a
        geoms=[n['geom'] for n in nodes]
        tree=STRtree(geoms)
        for i,n in enumerate(nodes):
            for j0 in tree.query(n['geom'].buffer(0.002)):
                j=int(j0)
                if j <= i or not n['layers'].intersection(nodes[j]['layers']):
                    continue
                if n['geom'].distance(nodes[j]['geom']) < 0.002:
                    union(i,j)
        groups=collections.defaultdict(list)
        for i,n in enumerate(nodes):groups[find(i)].append(n)
        groups=[v for v in groups.values() if any(n['pad'] for n in v)]
        cluster=[unary_union([n['geom'] for n in g]) for g in groups]
        padgroups=[[n['pad'] for n in g if n['pad']] for g in groups]
        if len(cluster)>1:
            used={0}
            while len(used)<len(cluster):
                best=None
                for a in used:
                    for b in range(len(cluster)):
                        if b in used:continue
                        dist=cluster[a].distance(cluster[b])
                        if best is None or dist<best[0]:best=(dist,a,b)
                dist,a,b=best
                p,q=nearest_points(cluster[a],cluster[b])
                all_edges.append({'net':net,'xy':[[p.x,p.y],[q.x,q.y]],
                                  'distance':dist,'from':padgroups[a], 'to':padgroups[b]})
                used.add(b)
        summary[net]={'grupos':len(cluster),'pads':sum(len(x) for x in padgroups),
                      'pendencias':max(0,len(cluster)-1)}
    return all_edges, summary

if __name__ == '__main__':
    positions=M.load_positions()
    result=classify(positions)
    edges, summary=connectivity(positions,result['tracks'],result['vias'])
    result['ratsnest']=edges
    result['redes']=summary
    path=M.HERE/'trilhas_classificadas.json'
    path.write_text(json.dumps(result,indent=1,ensure_ascii=False),encoding='utf8')
    print('originais:',result['source_counts'])
    print('trilhas:',dict(collections.Counter(t['status'] for t in result['tracks'])))
    print('vias:',dict(collections.Counter(t['status'] for t in result['vias'])))
    print('pendencias:',len(edges),'em',sum(s['pendencias']>0 for s in summary.values()),'redes')
