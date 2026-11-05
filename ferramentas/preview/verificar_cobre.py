"""Verificacao geometrica independente do cobre desenhado, nao e DRC de fabricacao.

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
import collections
import json
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

import layout_placa as M
import trilhas_eva as T

P=M.load_positions()
D=json.loads((M.HERE/'trilhas_roteadas.json').read_text(encoding='utf8'))
objs=[]
for p in M.all_pads(P):
    objs.append({'name':p['ref']+'.'+p['pin'],'net':p['net'],'layers':set(p['layers']),'geom':p['shape'],'tipo':'pad'})
for t in D['tracks']:
    if t['status'] in ('mantida','ajustada','nova'):
        objs.append({'name':t['id'],'net':t['net'],'layers':{t['layer']},
                     'geom':LineString(t['xy']).buffer(t['width']/2,quad_segs=8),'tipo':'trilha'})
for v in D['vias']:
    if v['status'] in ('mantida','nova'):
        objs.append({'name':v['id'],'net':v['net'],'layers':{1,2},
                     'geom':Point(v['xy']).buffer(v['diameter']/2,quad_segs=8),'tipo':'via'})
violations=[]
border=M.BOARD.buffer(-.19)
for ob in objs:
    if not border.covers(ob['geom']):
        violations.append({'tipo':'borda/furo','obj':ob['name'],'rede':ob['net']})
for layer in (1,2):
    subset=[o for o in objs if layer in o['layers']]
    tree=STRtree([o['geom'] for o in subset])
    for i,a in enumerate(subset):
        for j0 in tree.query(a['geom'].buffer(.19)):
            j=int(j0)
            if j<=i:continue
            b=subset[j]
            if a['net'] is not None and a['net']==b['net']:continue
            distance=a['geom'].distance(b['geom'])
            if distance < .19-1e-6:
                violations.append({'tipo':'folga/curto','camada':layer,'a':a['name'],'b':b['name'],
                                   'rede_a':a['net'],'rede_b':b['net'],'folga_mm':round(distance,4)})
counts=collections.Counter(v['tipo'] for v in violations)
report={'min_folga_avaliada_mm':.19,'objetos_de_cobre':len(objs),
        'contagem':dict(counts),'violacoes':violations,
        'ligacoes_abertas':len(D['ratsnest']),
        'redes_abertas':{k:v for k,v in D['redes'].items() if v['pendencias']}}
(M.HERE/'verificacao_cobre.json').write_text(json.dumps(report,indent=1,ensure_ascii=False),encoding='utf8')
print('objetos',len(objs),'violacoes',dict(counts),'ligacoes abertas',len(D['ratsnest']))
for v in violations[:30]:print(v)
if len(violations)>30:print('... ver verificacao_cobre.json')
