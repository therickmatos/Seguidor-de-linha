"""Alarga segmentos novos de potencia quando a folga geometrica permite.

Os escapes de 0,30 mm que nao puderem ser alargados ficam identificados para revisao.
Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
import collections
import json
from shapely.geometry import LineString
import layout_placa as M
import rotear as R
import trilhas_eva as T

P=M.load_positions()
path=M.HERE/'trilhas_roteadas.json'
D=json.loads(path.read_text(encoding='utf8'))
router=R.Router(P,D)
out=[]
stats=collections.Counter()
for t in D['tracks']:
    if t['status']!='nova' or not (t['net'] in ('VBAT','+5V','GND') or t['net'].startswith('OUT_')):
        out.append(t);continue
    net=t['net']; desired=1.0 if net=='VBAT' or net.startswith('OUT_') else (.6 if net=='+5V' else .5)
    for i,(a,b) in enumerate(zip(t['xy'],t['xy'][1:])):
        line=LineString([a,b]);width=.3
        for candidate in sorted({desired,.6,.5,.4},reverse=True):
            if candidate>desired:continue
            if router.exact_clear(net,t['layer'],line.buffer(candidate/2,quad_segs=8)):
                width=candidate;break
        r={**t,'id':f"{t['id']}_p{i}",'xy':[a,b],'width':width,
           'motivo':'potencia alargada quando possivel' if width>.3 else 'escape estreito: revisar largura/corrente'}
        out.append(r);stats[(net,width)]+=line.length
        # A nova largura passa a ser obstaculo para as redes seguintes.
        router.add_shape(t['layer'],net,line.buffer(width/2,quad_segs=8))
D['tracks']=out
D['ratsnest'],D['redes']=T.connectivity(P,D['tracks'],D['vias'])
D['roteamento']['larguras_mm_por_rede']={f'{net} / {width:g} mm':round(length,2) for (net,width),length in stats.items()}
path.write_text(json.dumps(D,indent=1,ensure_ascii=False),encoding='utf8')
print('segmentos de potencia novos:',len(out))
for (net,width),length in sorted(stats.items()):print(net,width,round(length,2),'mm')
print('pendencias',len(D['ratsnest']))
