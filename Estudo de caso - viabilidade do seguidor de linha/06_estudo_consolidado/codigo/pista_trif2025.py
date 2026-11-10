"""Modelo aproximado da pista TRIF 2025 a partir das fotos do usuário.

Retas e arcos são hipóteses em milímetros, não medidas das fotografias. O
rascunho aéreo fornecido pelo usuário orienta o desenho também nas partes que
estão fora de cada foto. As marcações seguem as dimensões nominais de 2026,
não são copiadas do rascunho. O percurso no cruzamento é imposto pelo modelo.
"""
import json
import math
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, Point
from simular_comparar import lap
from pista_c_regulamentar import _polygon

HERE=Path(__file__).resolve().parent
OUT=(HERE.parent/'dados') if HERE.name=='codigo' else HERE
SCALE=4.25  # mm por unidade do desenho; escala escolhida, não medida
SCREEN_HEIGHT=1050.
SKETCH_VERTICES=np.array([
 (1280,1023),(1280,55),(108,55),(108,230),
 (260,230),(260,148),(605,148),(605,228),
 (765,228),(640,510),(1150,510),(1150,440),
 (1120,400),(1120,108),(830,108),(830,228),
 (935,228),(880,1023)
],dtype=float)
VERTICES=np.column_stack((SKETCH_VERTICES[:,0]*SCALE,(SCREEN_HEIGHT-SKETCH_VERTICES[:,1])*SCALE))
# Na saída da pequena alça superior, as curvas de sentidos opostos se tocam
# com tangente comum: uma única transição de curvatura, sem reta fictícia.
_turn=abs(math.atan2(SKETCH_VERTICES[17,1]-SKETCH_VERTICES[16,1],
                     SKETCH_VERTICES[17,0]-SKETCH_VERTICES[16,0]))
_radius16=(SKETCH_VERTICES[16,0]-SKETCH_VERTICES[15,0]-60.)/math.tan(_turn/2)
RADII=np.array([125.,75.,87.5,87.5,41.,41.,40.,40.,40.,60.,50.,40.,40.,75.,60.,60.,_radius16,125.])*SCALE
START_POINT=np.array([1280.*SCALE,(SCREEN_HEIGHT-360.)*SCALE])
FINISH_POINT=START_POINT-np.array([0.,1000.])
_cross=LineString(VERTICES[9:11]).intersection(LineString(VERTICES[16:18]))
if _cross.geom_type!='Point':raise ValueError('O esboço deve conter um cruzamento simples')
CROSSING=np.array([_cross.x,_cross.y])


def pieces():
    corners=[];n=len(VERTICES)
    for i,v in enumerate(VERTICES):
        before=v-VERTICES[i-1];after=VERTICES[(i+1)%n]-v
        before/=np.linalg.norm(before);after/=np.linalg.norm(after)
        dot=float(np.dot(before,after));cross=float(before[0]*after[1]-before[1]*after[0])
        turn=math.atan2(cross,dot)
        if abs(turn)<1e-8 or abs(turn)>math.pi-1e-8:
            raise ValueError(f'Vertice {i} não define curva finita')
        radius=RADII[i]
        tangent=radius*math.tan(abs(turn)/2)
        corners.append(dict(entry=v-tangent*before,exit=v+tangent*after,
            angle=math.atan2(before[1],before[0]),length=abs(turn)*radius,
            k=math.copysign(1/radius,turn)))
    raw=[]
    for i,c in enumerate(corners):
        j=(i+1)%n;d=corners[j]['entry']-c['exit']
        direction=VERTICES[j]-VERTICES[i];direction/=np.linalg.norm(direction)
        if float(np.dot(d,direction)) < -1e-8:
            raise ValueError(f'Arcos sobrepostos no trecho {i}')
        distance=float(np.linalg.norm(d))
        if distance>1e-8:
            raw.append(dict(start=c['exit'].copy(),phi=math.atan2(direction[1],direction[0]),
                length=distance,k=0.,kind='reta'))
        nxt=corners[j]
        raw.append(dict(start=nxt['entry'].copy(),phi=nxt['angle'],length=nxt['length'],
                        k=nxt['k'],kind='arco'))
    merged=[]
    for p in raw:
        if merged and abs(merged[-1]['k']-p['k'])<1e-12:
            merged[-1]['length']+=p['length']
        else:
            merged.append(p.copy())
    for i,p in enumerate(merged):p['id']=i
    return merged


def _sample(piece,step):
    return lap.integrate(piece['start'],piece['phi'],piece['length'],piece['k'],step)


def build(step=.5):
    blocks=pieces();parts=[];boundaries=[];offset=0.
    for i,p in enumerate(blocks):
        a=_sample(p,step);a[:,0]+=offset
        boundaries.append(dict(s=offset,x=float(a[0,1]),y=float(a[0,2]),phi=float(a[0,3]),
            previous_k=float(blocks[i-1]['k']),next_k=float(p['k']),piece_id=i))
        parts.append(a[:-1]);offset=float(a[-1,0])
    cycle=np.vstack(parts+[a[-1:]]);cycle[:,3]=np.unwrap(cycle[:,3])
    period=float(cycle[-1,0])
    if np.linalg.norm(cycle[-1,1:3]-cycle[0,1:3])>1e-6:raise ValueError('Pista aberta')
    turns=round((cycle[-1,3]-cycle[0,3])/(2*math.pi))*2*math.pi
    laps=[]
    for i in range(3):
        a=cycle[:-1].copy();a[:,0]+=i*period;a[:,3]+=i*turns;laps.append(a)
    a=cycle[-1:].copy();a[:,0]+=2*period;a[:,3]+=2*turns;laps.append(a)
    track=np.vstack(laps)
    first=blocks[0];direction=np.array([math.cos(first['phi']),math.sin(first['phi'])])
    start_phase=float(np.dot(START_POINT-first['start'],direction))
    finish_phase=float(np.dot(FINISH_POINT-first['start'],direction))
    if not (0<=finish_phase<start_phase<first['length']):raise ValueError('Partida/chegada fora da reta')
    def abs_s(s):return period+start_phase+((s-start_phase)%period)
    marks=[]
    for b in boundaries:
        if abs(b['previous_k']-b['next_k'])<1e-12:continue
        marks.append(dict(s=float(abs_s(b['s'])),x=b['x'],y=b['y'],phi=b['phi'],side=1,
            kind='curva',label='C',transition=f"{b['previous_k']:.6g} → {b['next_k']:.6g}",
            halfWidth=9.5,inner=49.5,outer=89.5,piece_id=b['piece_id']))
    marks.extend([
        dict(s=float(abs_s(start_phase)),x=float(START_POINT[0]),y=float(START_POINT[1]),phi=first['phi'],side=-1,kind='partida',label='Partida',halfWidth=9.5,inner=49.5,outer=89.5),
        dict(s=float(abs_s(finish_phase)),x=float(FINISH_POINT[0]),y=float(FINISH_POINT[1]),phi=first['phi'],side=-1,kind='chegada',label='Chegada',halfWidth=9.5,inner=49.5,outer=89.5)])
    marks.sort(key=lambda m:m['s']);count=0
    for m in marks:
        if m['kind']=='curva':count+=1;m['label']=f'C{count:02d}'
    times=[]
    for p,b in zip(blocks,boundaries):
        if p['kind']!='reta':continue
        line=LineString(_sample(p,max(step,2.))[:,1:3]);point=Point(*CROSSING)
        if line.distance(point)<1e-6:times.append(float(abs_s(b['s']+line.project(point))))
    if len(times)!=2:raise ValueError(f'Cruzamento inesperado: {times}')
    return track,cycle,marks,dict(start=float(abs_s(start_phase)-250),
        end=float(abs_s(finish_phase)+180),period=period,crossing=CROSSING.tolist(),
        crossing_s=min(times),crossing_second_s=max(times),estimated=[],
        blocks=blocks,boundaries=boundaries,note='Modelo baseado no rascunho aéreo e fotos; dimensões estimadas.')


def check_geometry(cycle,marks,meta):
    blocks=meta['blocks'];lines=[LineString(_sample(p,2.)[:,1:3]).simplify(.02,preserve_topology=True) for p in blocks]
    crossings=[];n=len(lines)
    for i in range(n):
        for j in range(i+1,n):
            if min(j-i,n-(j-i))<=1:continue
            inter=lines[i].intersection(lines[j])
            if not inter.is_empty:
                if inter.geom_type!='Point':raise ValueError(f'Interseção inesperada {i}/{j}: {inter.geom_type}')
                crossings.append((i,j,inter))
    if len(crossings)!=1 or crossings[0][2].distance(Point(*CROSSING))>1e-6:
        raise ValueError(f'Cruzamentos inesperados: {crossings}')
    i,j,point=crossings[0]
    if blocks[i]['k'] or blocks[j]['k']:raise ValueError('Cruzamento não está em retas')
    angle=abs(math.degrees(math.atan2(math.sin(blocks[i]['phi']-blocks[j]['phi']),
                                     math.cos(blocks[i]['phi']-blocks[j]['phi']))))
    angle=min(angle,180-angle)
    clearance=min(min(lines[k].project(point),lines[k].length-lines[k].project(point)) for k in (i,j))
    independent=[]
    cumulative=np.r_[0.,np.cumsum([p['length'] for p in blocks])]
    for a in range(n):
        for b in range(a+1,n):
            # Seções próximas ao longo da própria curva não são pistas
            # independentes. O cruzamento único permitido é excluído à parte.
            along=min(cumulative[b]-cumulative[a+1],cumulative[-1]-cumulative[b+1]+cumulative[a])
            if along<500 or (a,b)==(i,j):continue
            independent.append((float(lines[a].distance(lines[b])),a,b))
    min_distance,closest_a,closest_b=min(independent)
    first=blocks[0];direction=np.array([math.cos(first['phi']),math.sin(first['phi'])])
    before_finish=float(np.dot(FINISH_POINT-first['start'],direction))
    after_start=float(first['length']-np.dot(START_POINT-first['start'],direction))
    polys=[_polygon(m) for m in marks]
    overlaps=[(marks[a]['label'],marks[b]['label']) for a in range(len(polys)) for b in range(a+1,len(polys))
              if polys[a].intersection(polys[b]).area>1e-7]
    guide=LineString(cycle[:,1:3]);gaps=[guide.distance(p)-9.5 for p in polys]
    closure=float(np.linalg.norm(cycle[-1,1:3]-cycle[0,1:3]))
    joins=[float(np.linalg.norm(_sample(p,2.)[-1,1:3]-blocks[(i+1)%n]['start'])) for i,p in enumerate(blocks)]
    angles=[abs(math.atan2(math.sin(p['phi']+p['k']*p['length']-blocks[(i+1)%n]['phi']),
                           math.cos(p['phi']+p['k']*p['length']-blocks[(i+1)%n]['phi']))) for i,p in enumerate(blocks)]
    result=dict(period_mm=meta['period'],marks=len(marks),curve_marks=len(marks)-2,
        closure_mm=closure,max_join_error_mm=max(joins),max_join_angle_error_rad=max(angles),line_width_mm=19,minimum_radius_mm=float(min(RADII)),
        crossings=1,crossing_angle_degrees=angle,crossing_straight_clearance_mm=clearance,
        start_finish_distance_mm=float(np.linalg.norm(START_POINT-FINISH_POINT)),marker_overlaps=overlaps,
        straight_before_finish_mm=before_finish,straight_after_start_mm=after_start,
        min_independent_centreline_mm=min_distance,min_independent_tape_edge_mm=min_distance-19.,
        min_independent_pair=[closest_a,closest_b],max_pro_mm=60000,max_junior_mm=20000,
        within_pro_limit=meta['period']<=60000,within_junior_limit=meta['period']<=20000,
        min_marker_gap_mm=min(gaps),max_marker_gap_mm=max(gaps),
        estimated='Traçado baseado no rascunho e nas fotos; dimensões e raios aproximados.',
        gates_modelled=False,limitations='Modelo hipotético; checagem discretizada, exclui cruzamento e trechos separados por menos de 500 mm ao longo da linha; sem portas físicas, não certificação oficial.')
    assert closure<1e-6 and max(joins)<1e-6 and max(angles)<1e-8 and 85<=angle<=95 and clearance>=250
    assert min(RADII)>=100 and min_distance-19>=200 and before_finish>=250 and after_start>=250
    assert abs(result['start_finish_distance_mm']-1000)<1e-8 and result['within_pro_limit']
    assert not overlaps and min(gaps)>=37-.05 and max(gaps)<=43+.05
    assert all(m['side']==1 for m in marks if m['kind']=='curva')
    assert all(m['side']==-1 for m in marks if m['kind'] in ('partida','chegada'))
    boundaries=meta['boundaries']
    assert sum(abs(b['previous_k']-b['next_k'])>1e-12 for b in boundaries)==sum(m['kind']=='curva' for m in marks)
    for m in (v for v in marks if v['kind']=='curva'):
        b=boundaries[m['piece_id']]
        assert math.hypot(m['x']-b['x'],m['y']-b['y'])<1e-6
    return result


if __name__=='__main__':
    _,cycle,marks,meta=build(.5);result=check_geometry(cycle,marks,meta)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'validacao_pista_trif2025.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8',newline='\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
