"""Modelo aproximado da pista TRIF 2025 a partir das fotos do usuário.

Retas e arcos são hipóteses em milímetros, não medidas da fotografia. O laço
à esquerda da imagem continua fora do enquadramento e é fechado por hipótese.
As marcações são reconstruídas segundo o modelo nominal de 2026, não copiadas
uma a uma da imagem. Um cruzamento tem a passagem previamente determinada.
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
START_X=1900.
FINISH_X=900.
CROSSING=np.array([1900.,1600.])

# Coordenadas giradas 90° em relação à visualização da foto. O percurso segue
# a reta longa, o trecho superior parcialmente encoberto, o S, o cruzamento,
# a alça superior e a reta interna até a curva larga de retorno.
VERTICES=np.array([
 (0,0),(3300,0),(3300,3500),(2900,3500),(2900,2600),
 (2600,2600),(2600,2200),(2300,2200),(2300,2500),
 (1900,2500),(1900,800),(2850,800),(2850,1600),(0,1600)
],dtype=float)
RADII=np.array([500.]+[150.]*12+[500.])


def pieces():
    corners=[];n=len(VERTICES)
    for i,v in enumerate(VERTICES):
        before=v-VERTICES[i-1];after=VERTICES[(i+1)%n]-v
        before/=np.linalg.norm(before);after/=np.linalg.norm(after)
        dot=float(np.dot(before,after));cross=float(before[0]*after[1]-before[1]*after[0])
        if abs(dot)>1e-12 or abs(abs(cross)-1)>1e-12:
            raise ValueError(f'Vertice {i} não é ortogonal')
        radius=RADII[i]
        corners.append(dict(entry=v-radius*before,exit=v+radius*after,
            angle=math.atan2(before[1],before[0]),length=math.pi*radius/2,
            k=math.copysign(1/radius,cross)))
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
    start_phase=START_X-RADII[0];finish_phase=FINISH_X-RADII[0]
    def abs_s(s):return period+start_phase+((s-start_phase)%period)
    marks=[]
    for b in boundaries:
        if abs(b['previous_k']-b['next_k'])<1e-12:continue
        marks.append(dict(s=float(abs_s(b['s'])),x=b['x'],y=b['y'],phi=b['phi'],side=1,
            kind='curva',label='C',transition=f"{b['previous_k']:.6g} → {b['next_k']:.6g}",
            halfWidth=9.5,inner=49.5,outer=89.5,piece_id=b['piece_id']))
    marks.extend([
        dict(s=float(abs_s(start_phase)),x=START_X,y=0.,phi=0.,side=-1,kind='partida',label='Partida',halfWidth=9.5,inner=49.5,outer=89.5),
        dict(s=float(abs_s(finish_phase)),x=FINISH_X,y=0.,phi=0.,side=-1,kind='chegada',label='Chegada',halfWidth=9.5,inner=49.5,outer=89.5)])
    marks.sort(key=lambda m:m['s']);count=0
    for m in marks:
        if m['kind']=='curva':count+=1;m['label']=f'C{count:02d}'
    times=[]
    for p,b in zip(blocks,boundaries):
        if p['kind']!='reta':continue
        line=LineString(_sample(p,max(step,2.))[:,1:3]);point=Point(*CROSSING)
        if line.distance(point)<1e-6:times.append(float(abs_s(b['s']+line.project(point))))
    if len(times)!=2:raise ValueError(f'Cruzamento inesperado: {times}')
    # Parte à esquerda da fotografia está fora de quadro, inclusive o retorno.
    estimated=[]
    for p in blocks:
        a=_sample(p,4.)[:,1:3];keep=a[:,1]>=2900
        if np.count_nonzero(keep)>=2:estimated.append(a[keep].tolist())
    return track,cycle,marks,dict(start=float(abs_s(start_phase)-250),
        end=float(abs_s(finish_phase)+180),period=period,crossing=CROSSING.tolist(),
        crossing_s=min(times),crossing_second_s=max(times),estimated=estimated,
        blocks=blocks,boundaries=boundaries,note='Modelo inspirado na foto; retorno fora do enquadramento é hipotético.')


def check_geometry(cycle,marks,meta):
    blocks=meta['blocks'];lines=[LineString(_sample(p,2.)[:,1:3]) for p in blocks]
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
    polys=[_polygon(m) for m in marks]
    overlaps=[(marks[a]['label'],marks[b]['label']) for a in range(len(polys)) for b in range(a+1,len(polys))
              if polys[a].intersection(polys[b]).area>1e-7]
    guide=LineString(cycle[:,1:3]);gaps=[guide.distance(p)-9.5 for p in polys]
    closure=float(np.linalg.norm(cycle[-1,1:3]-cycle[0,1:3]))
    joins=[float(np.linalg.norm(_sample(p,2.)[-1,1:3]-blocks[(i+1)%n]['start'])) for i,p in enumerate(blocks)]
    result=dict(period_mm=meta['period'],marks=len(marks),curve_marks=len(marks)-2,
        closure_mm=closure,max_join_error_mm=max(joins),line_width_mm=19,minimum_radius_mm=float(min(RADII)),
        crossings=1,crossing_angle_degrees=angle,crossing_straight_clearance_mm=clearance,
        start_finish_distance_mm=START_X-FINISH_X,marker_overlaps=overlaps,
        min_marker_gap_mm=min(gaps),max_marker_gap_mm=max(gaps),
        estimated='Trecho à esquerda fora da fotografia; geometria e demais medidas aproximadas.',
        limitations='Modelo hipotético, não planta medida ou certificação oficial.')
    assert closure<1e-6 and max(joins)<1e-6 and abs(angle-90)<1e-8 and clearance>=250
    assert not overlaps and min(gaps)>=37-.05 and max(gaps)<=43+.05
    assert all(m['side']==1 for m in marks if m['kind']=='curva')
    assert all(m['side']==-1 for m in marks if m['kind'] in ('partida','chegada'))
    return result


if __name__=='__main__':
    _,cycle,marks,meta=build(.5);result=check_geometry(cycle,marks,meta)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'validacao_pista_trif2025.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8',newline='\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
