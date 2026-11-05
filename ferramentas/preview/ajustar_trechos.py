"""Libera conexoes locais recortando stubs, somente se reduzir ilhas abertas.

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
import json
import math
from shapely.geometry import LineString,Point
import layout_placa as M
import rotear as R
import trilhas_eva as T

P=M.load_positions();path=M.HERE/'trilhas_roteadas.json'
D=json.loads(path.read_text(encoding='utf8'));pads=M.all_pads(P);done=0
while True:
    edges,_=T.connectivity(P,D['tracks'],D['vias']);improved=False
    for e in sorted(edges,key=lambda v:v['distance']):
        if e['distance']>5:continue
        groups=R.groups_for(e['net'],P,D['tracks'],D['vias'])
        a=next((g for g in groups if set(g['pins'])==set(e['from'])),None)
        b=next((g for g in groups if set(g['pins'])==set(e['to'])),None)
        if not a or not b:continue
        x1,y1=e['xy'][0];x2,y2=e['xy'][1];dx=x2-x1;dy=y2-y1
        candidates=[]
        if abs(dx)<.03 or abs(dy)<.03 or abs(abs(dx)-abs(dy))<.03:candidates.append([(x1,y1),(x2,y2)])
        candidates.extend([[(x1,y1),(x1,y2),(x2,y2)],[(x1,y1),(x2,y1),(x2,y2)]])
        d=min(abs(dx),abs(dy))
        if d>.001:
            sx=math.copysign(1,dx);sy=math.copysign(1,dy)
            candidates.extend([[(x1,y1),(x1+sx*d,y1+sy*d),(x2,y2)],[(x1,y1),(x2-sx*d,y2-sy*d),(x2,y2)]])
        for layer in (1,2):
            if a['layers'][layer].is_empty or b['layers'][layer].is_empty:continue
            if Point(x1,y1).distance(a['layers'][layer])>.002 or Point(x2,y2).distance(b['layers'][layer])>.002:continue
            for coords in candidates:
                coords=[p for i,p in enumerate(coords) if i==0 or p!=coords[i-1]]
                if len(coords)<2:continue
                center=LineString(coords);copper=center.buffer(.15,quad_segs=8)
                if not M.BOARD.buffer(-.2).covers(copper):continue
                if any(p['net']!=e['net'] and layer in p['layers'] and copper.distance(p['shape'])<.2-1e-6 for p in pads):continue
                if any(v['status'] in ('mantida','nova') and v['net']!=e['net'] and copper.distance(R.geom_via(v))<.2-1e-6 for v in D['vias']):continue
                hits=[t for t in D['tracks'] if t['status'] in ('mantida','ajustada','nova') and t['layer']==layer and t['net']!=e['net'] and copper.distance(R.geom_tracks(t))<.2-1e-6]
                if not hits or len(hits)>2:continue
                victims={id(t) for t in hits};replacement=[]
                for t in D['tracks']:
                    if id(t) not in victims:replacement.append(t);continue
                    old=LineString(t['xy']);keep=old.difference(center.buffer(.15+.2+t['width']/2+.001))
                    for i,piece in enumerate(T.parts(keep)):
                        if piece.length<.05:continue
                        replacement.append({**t,'id':f"{t['id']}_aj{done}_{i}",
                                            'xy':[[float(x),float(y)] for x,y in piece.coords],
                                            'status':'nova' if t['status']=='nova' else 'ajustada',
                                            'motivo':'recorte local para liberar outra rede'})
                    if t['status']!='nova':
                        removed=old.difference(keep.buffer(.00001))
                        for i,piece in enumerate(T.parts(removed)):
                            if piece.length>.02:replacement.append({**t,'id':f"{t['id']}_rem{done}_{i}",
                                'xy':[[float(x),float(y)] for x,y in piece.coords],
                                'status':'removida','motivo':'recorte local para liberar outra rede'})
                replacement.append({'id':f'ajuste_local_{done}','old_net':None,'net':e['net'],
                    'layer':layer,'width':.3,'xy':[list(p) for p in coords], 'type':'LINE',
                    'status':'nova','motivo':'conexao local com recorte verificado'})
                after,_=T.connectivity(P,replacement,D['vias'])
                if len(after)>=len(edges):continue
                D['tracks']=replacement;done+=1;improved=True
                print('unida',e['net'],'reaproveitando apos recortar',[(h['id'],h['net']) for h in hits],flush=True)
                break
            if improved:break
        if improved:break
    if not improved:break
D['ratsnest'],D['redes']=T.connectivity(P,D['tracks'],D['vias'])
D['roteamento']['ajustes_locais']=done
if done:path.write_text(json.dumps(D,indent=1,ensure_ascii=False),encoding='utf8')
print('ajustes',done,'pendencias',len(D['ratsnest']))
