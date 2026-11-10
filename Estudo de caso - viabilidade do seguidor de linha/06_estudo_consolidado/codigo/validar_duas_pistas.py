"""Recalcula cruzamentos geométricos nos modelos TRIF 2025 e 2024."""
from pathlib import Path
import json
import math
import numpy as np
from shapely.geometry import LineString,box
import simular_comparar as sim
import pista_trif2025 as pista25
import pista_c_regulamentar as pista24

HERE=Path(__file__).resolve().parent
OUT=(HERE.parent/'dados') if HERE.name=='codigo' else HERE
OUT.mkdir(parents=True,exist_ok=True)
STEP=.25
CASES=[('63,14 · QRE originais',63.141,69.5),('63,14 · esquerdo 68',63.141,68.),
       ('63,14 · esquerdo +1 para fora',63.141,70.5),('60 · QRE originais',60.,69.5)]


def length_from_holes(mm):
    dy=math.sqrt(mm*mm-(sim.X_HOLE_V1-sim.X_HOLE_BASE)**2)
    return sim.Y_HOLE_BASE+dy-sim.Y_HOLE_V1+sim.Y_SENSOR_V1-sim.AXLE


def main():
    b,bc,bm,_=pista25.build(STEP);c,cc,cm,_=pista24.build(STEP)
    rows=[]
    for name,track,marks in [('2025',b,bm),('2024',c,cm)]:
        cache={}
        for label,holes,left in CASES:
            L=length_from_holes(holes)
            if holes not in cache:
                alpha=sim.old.pose(track,L)
                cache[holes]={'alpha':alpha,'right':sim.old.sensor_xy(track,alpha,L,-69.5,4.5-sim.AXLE),'left':{}}
            slot=cache[holes]
            if left not in slot['left']:
                slot['left'][left]=sim.old.sensor_xy(track,slot['alpha'],L,left,4.5-sim.AXLE)
            events=[]
            for m in sorted(marks,key=lambda v:v['s']):
                lo=int(np.searchsorted(track[:,0],m['s']-200));hi=int(np.searchsorted(track[:,0],m['s']+300))
                pts=(slot['left'][left] if m['side']>0 else slot['right'])[lo:hi]
                dx=pts[:,0]-m['x'];dy=pts[:,1]-m['y'];co,si=math.cos(m['phi']),math.sin(m['phi'])
                u=dx*co+dy*si;v=m['side']*(-dx*si+dy*co);path=LineString(np.column_stack((u,v)))
                nominal=path.intersection(box(-9.5,49.5,9.5,89.5)).length>1e-8
                common=path.intersection(box(-9.,53.,9.,83.)).length>1e-8
                events.append(dict(mark=m['label'],side=m['side'],kind=m['kind'],nominal=bool(nominal),common=bool(common)))
            row=dict(track=name,configuration=label,hole_distance_mm=holes,left_abs_mm=left,right_abs_mm=69.5,
                     L_mm=L,nominal=sum(e['nominal'] for e in events),common=sum(e['common'] for e in events),
                     total=len(events),misses=[e['mark'] for e in events if not e['nominal']],
                     start_finish=[e for e in events if e['kind'] in ('partida','chegada')])
            rows.append(row);print(name,label,row['nominal'],'/',row['total'],'comum',row['common'],flush=True)
    output=dict(step_mm=STEP,offset_mm=0,mark_model='19 × 40 mm, 40 mm da borda da linha',
                note='Interseções geométricas apenas; não modela sinal óptico, dinâmica ou PID.',results=rows)
    (OUT/'resultados_duas_pistas.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf8',newline='\n')


if __name__=='__main__':main()
