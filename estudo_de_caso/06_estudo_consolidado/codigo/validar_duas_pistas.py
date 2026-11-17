"""Recalcula cruzamentos geométricos nos modelos TRIF 2025, TRIF 2024 e pista de teste do EVA-RT."""
from pathlib import Path
import json
import math
import numpy as np
from shapely.geometry import LineString,box
import simular_comparar as sim
import pista_trif2025 as pista25
import pista_c_regulamentar as pista24
import pista_eva_rt_teste as pistaeva
from chassi_dois_sensores import SENSOR_X, SENSOR_Y, length_from_holes

HERE=Path(__file__).resolve().parent
OUT=(HERE.parent/'dados') if HERE.name=='codigo' else HERE
OUT.mkdir(parents=True,exist_ok=True)
STEP=.25
CASES=[('holes','63,14 · QRE originais',63.141,[69.5],[69.5],4.5),
       ('one_asym68','63,14 · esquerdo 68',63.141,[68.],[69.5],4.5),
       ('one_out1','63,14 · esquerdo +1 para fora',63.141,[70.5],[69.5],4.5),
       ('one_60','60 · QRE originais',60.,[69.5],[69.5],4.5),
       ('chassi_baixo_2','Chassi baixo · dois QRE por lado · 60 mm',60.,SENSOR_X,SENSOR_X,SENSOR_Y),
       ('chassi_baixo_2_65','Chassi baixo · dois QRE por lado · 65 mm',65.,SENSOR_X,SENSOR_X,SENSOR_Y),
       ('chassi_baixo_2_70','Chassi baixo · dois QRE por lado · 70 mm',70.,SENSOR_X,SENSOR_X,SENSOR_Y),
       # 7º campo opcional: L explícito (eixo → centro da barra), sem passar pela distância entre furos.
       ('eva_rt_original','EVA-RT original · L 100 mm · 1 sensor por lado',None,[69.5],[69.5],4.5,100.),
       ('v3_l85','v3 atual · L 85 mm · 1 sensor por lado',None,[69.5],[69.5],4.5,85.),
       ('v3_l70','v3 atual · L 70 mm · 1 sensor por lado',None,[69.5],[69.5],4.5,70.)]


def main():
    b,bc,bm,_=pista25.build(STEP);c,cc,cm,_=pista24.build(STEP);e,ec,em,_=pistaeva.build(STEP)
    rows=[]
    for name,track,marks in [('2025',b,bm),('2024',c,cm),('EVA-RT',e,em)]:
        cache={}
        for preset,label,holes,left,right,sensor_y,*explicit in CASES:
            L=explicit[0] if explicit else length_from_holes(holes)
            if L not in cache:
                alpha=sim.old.pose(track,L)
                cache[L]={'alpha':alpha,'paths':{}}
            slot=cache[L]
            for side,positions in [(1,left),(-1,right)]:
                for x in positions:
                    key=(side,x,sensor_y)
                    if key not in slot['paths']:
                        slot['paths'][key]=sim.old.sensor_xy(track,slot['alpha'],L,side*x,sensor_y-sim.AXLE)
            events=[]
            for m in sorted(marks,key=lambda v:v['s']):
                lo=int(np.searchsorted(track[:,0],m['s']-200));hi=int(np.searchsorted(track[:,0],m['s']+300))
                hits=[];common_hits=[]
                for x in (left if m['side']>0 else right):
                    pts=slot['paths'][(m['side'],x,sensor_y)][lo:hi]
                    dx=pts[:,0]-m['x'];dy=pts[:,1]-m['y'];co,si=math.cos(m['phi']),math.sin(m['phi'])
                    u=dx*co+dy*si;v=m['side']*(-dx*si+dy*co);path=LineString(np.column_stack((u,v)))
                    if path.intersection(box(-9.5,49.5,9.5,89.5)).length>1e-8:hits.append(x)
                    if path.intersection(box(-9.,53.,9.,83.)).length>1e-8:common_hits.append(x)
                events.append(dict(mark=m['label'],side=m['side'],kind=m['kind'],nominal=bool(hits),common=bool(common_hits),
                                   sensors_hit_mm=hits,sensors_common_mm=common_hits))
            row=dict(track=name,preset=preset,configuration=label,hole_distance_mm=holes,
                     left_abs_mm=left[0] if len(left)==1 else list(left),right_abs_mm=right[0] if len(right)==1 else list(right),sensor_y_mm=sensor_y,
                     L_mm=L,nominal=sum(e['nominal'] for e in events),common=sum(e['common'] for e in events),
                     left_nominal=sum(e['nominal'] and e['side']>0 for e in events),right_nominal=sum(e['nominal'] and e['side']<0 for e in events),
                     left_common=sum(e['common'] and e['side']>0 for e in events),right_common=sum(e['common'] and e['side']<0 for e in events),
                     total=len(events),misses=[e['mark'] for e in events if not e['nominal']],
                     start_finish=[e for e in events if e['kind'] in ('partida','chegada')],events=events)
            rows.append(row);print(name,label,row['nominal'],'/',row['total'],'comum',row['common'],flush=True)
    output=dict(step_mm=STEP,offset_mm=0,mark_model='19 × 40 mm, 40 mm da borda da linha',
                note='Interseções geométricas apenas; não modela sinal óptico, dinâmica ou PID.',results=rows)
    (OUT/'resultados_duas_pistas.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf8',newline='\n')


if __name__=='__main__':main()
