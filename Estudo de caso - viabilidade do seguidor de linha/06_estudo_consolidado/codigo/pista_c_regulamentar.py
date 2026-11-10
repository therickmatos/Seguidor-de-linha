"""Pista C: modelo geométrico inspirado na foto e desenhado para o TRIF.

Retas e arcos exatos; a fotografia não fornece planta nem dimensões reais.
Não há portas físicas, superfícies, eletrônica ou controle de robô modelados.
"""
from pathlib import Path
import json
import math
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Polygon, Point
from simular_comparar import lap

HERE=Path(__file__).resolve().parent
OUT=(HERE.parent/'dados') if HERE.name=='codigo' else HERE
LINE_WIDTH=19.
MARK_WIDTH=19.
MARK_LENGTH=40.
MARK_GAP=40.
FINISH_X=900.
START_X=1900.
RADIUS=150.

# Polígono orientado no sentido de prova. A seção (x=1900, y=2500)
# é cruzada uma vez em cada direção, por segmentos retos perpendiculares.
VERTICES=np.array([
 (0,0),(3300,0),(3300,1750),(2300,1750),(2300,800),
 (1300,800),(1300,1100),(1600,1100),(1600,1400),(1900,1400),
 (1900,3100),(1300,3100),(1300,2500),(2900,2500),(2900,3400),
 (950,3400),(950,350),(500,350),(500,700),(0,700)
],dtype=float)
RADII=np.array([150.,150.,500.,500.]+[RADIUS]*16)


def _corners():
    result=[];n=len(VERTICES)
    for i,v in enumerate(VERTICES):
        before=v-VERTICES[i-1];after=VERTICES[(i+1)%n]-v
        before/=np.linalg.norm(before);after/=np.linalg.norm(after)
        dot=float(np.dot(before,after));cross=float(before[0]*after[1]-before[1]*after[0])
        assert abs(dot)<1e-12 and abs(abs(cross)-1)<1e-12
        r=RADII[i]
        result.append(dict(entry=v-r*before,exit=v+r*after,
                           angle=math.atan2(before[1],before[0]),
                           length=math.pi*r/2,k=math.copysign(1/r,cross)))
    return result


def pieces():
    corners=_corners();n=len(corners);raw=[]
    for i,c in enumerate(corners):
        j=(i+1)%n;d=corners[j]['entry']-c['exit'];distance=float(np.linalg.norm(d))
        direction=(VERTICES[j]-VERTICES[i]);direction/=np.linalg.norm(direction)
        assert float(np.dot(d,direction))>=-1e-8, f'Curvas sobrepostas no trecho {i}'
        if distance>1e-8:
            raw.append(dict(start=c['exit'].copy(),phi=math.atan2(direction[1],direction[0]),
                            length=distance,k=0.,kind='reta'))
        v=corners[j]
        raw.append(dict(start=v['entry'].copy(),phi=v['angle'],length=v['length'],k=v['k'],kind='arco'))
    # Arcos consecutivos da mesma circunferência são um único arco e não
    # recebem uma marcação fictícia no ponto intermediário.
    merged=[]
    for p in raw:
        if merged and abs(merged[-1]['k']-p['k'])<1e-12:
            merged[-1]['length']+=p['length']
        else:
            merged.append(p.copy())
    for i,p in enumerate(merged):p['id']=i
    return merged


def _sample(p,step):
    return lap.integrate(p['start'],p['phi'],p['length'],p['k'],step)


def _polygon(m):
    co,si=math.cos(m['phi']),math.sin(m['phi']);side=m['side']
    return Polygon([(m['x']+u*co-v*side*si,m['y']+u*si+v*side*co)
                    for u,v in [(-9.5,49.5),(9.5,49.5),(9.5,89.5),(-9.5,89.5)]])


def build(step=.5):
    blocks=pieces();cycle_list=[];boundaries=[];offset=0.
    for i,p in enumerate(blocks):
        arr=_sample(p,step);arr[:,0]+=offset
        boundaries.append(dict(s=offset,x=float(arr[0,1]),y=float(arr[0,2]),phi=float(arr[0,3]),
                               previous_k=float(blocks[i-1]['k']),next_k=float(p['k']),piece_id=i))
        cycle_list.extend(arr[:-1].tolist());offset=float(arr[-1,0])
    cycle_list.append(arr[-1].tolist());cycle=np.array(cycle_list);cycle[:,3]=np.unwrap(cycle[:,3])
    period=float(cycle[-1,0]);assert np.linalg.norm(cycle[-1,1:3]-cycle[0,1:3])<1e-6
    turns=round((cycle[-1,3]-cycle[0,3])/(2*math.pi))*2*math.pi
    track=[]
    for i in range(3):
        a=cycle[:-1].copy();a[:,0]+=i*period;a[:,3]+=i*turns;track.append(a)
    end=cycle[-1:].copy();end[:,0]+=2*period;end[:,3]+=2*turns;track.append(end)
    track=np.vstack(track)
    # Primeira reta inicia na saída da curva em (150, 0).
    start_phase=START_X-RADII[0];finish_phase=FINISH_X-RADII[0]
    def abs_s(s):return period+start_phase+((s-start_phase)%period)
    marks=[]
    for b in boundaries:
        if abs(b['previous_k']-b['next_k'])<1e-12:continue
        marks.append(dict(s=float(abs_s(b['s'])),x=b['x'],y=b['y'],phi=b['phi'],
            side=1,kind='curva',label='M',transition=f"{b['previous_k']:.6g} → {b['next_k']:.6g}",
            halfWidth=9.5,inner=49.5,outer=89.5,piece_id=b['piece_id']))
    marks.extend([
        dict(s=float(abs_s(start_phase)),x=START_X,y=0.,phi=0.,side=-1,kind='partida',label='Partida',halfWidth=9.5,inner=49.5,outer=89.5),
        dict(s=float(abs_s(finish_phase)),x=FINISH_X,y=0.,phi=0.,side=-1,kind='chegada',label='Chegada',halfWidth=9.5,inner=49.5,outer=89.5)
    ])
    marks.sort(key=lambda m:m['s']);count=0
    for m in marks:
        if m['kind']=='curva':count+=1;m['label']=f'C{count:02d}'
    crossing=np.array([1900.,2500.]);times=[]
    for p,b in zip(blocks,boundaries):
        if p['kind']!='reta':continue
        line=LineString(_sample(p,max(step,2.))[:,1:3]);point=Point(*crossing)
        if line.distance(point)<1e-6:
            local=line.project(point);times.append(abs_s(b['s']+local))
    assert len(times)==2
    times.sort()
    # O fecho superior é hipotético porque parte da linha sai da foto.
    estimated=[]
    for p in blocks:
        if p['kind']=='reta' and abs(p['start'][1]-3400)<1e-7:
            ar=_sample(p,4.)[:,1:3];keep=ar[:,0]>=1750
            if keep.any():estimated.append(ar[keep].tolist())
    extrema=cycle[:,1:3];minx,miny=extrema.min(axis=0)-250;maxx,maxy=extrema.max(axis=0)+250
    return track,cycle,marks,dict(start=float(abs_s(start_phase)-250),end=float(abs_s(finish_phase)+180),
        period=period,crossing=crossing.tolist(),crossing_s=float(times[0]),crossing_second_s=float(times[1]),
        estimated=estimated,mat=[float(minx),float(miny),float(maxx),float(maxy)],
        blocks=blocks,boundaries=boundaries,note='Pista simulada inspirada na foto; não é planta oficial.')


def check(step=2.):
    track,cycle,marks,meta=build(step);blocks=meta['blocks'];boundaries=meta['boundaries']
    straight_errors=[];arc_errors=[];join_errors=[];angle_errors=[]
    for idx,p in enumerate(blocks):
        pts=_sample(p,step)[:,1:3]
        next_start=blocks[(idx+1)%len(blocks)]['start']
        join_errors.append(float(np.linalg.norm(pts[-1]-next_start)))
        end_phi=p['phi']+p['k']*p['length'];next_phi=blocks[(idx+1)%len(blocks)]['phi']
        angle_errors.append(abs(math.atan2(math.sin(end_phi-next_phi),math.cos(end_phi-next_phi))))
        if p['k']==0:
            vec=pts[-1]-pts[0];rel=pts-pts[0]
            straight_errors.append(float(np.max(np.abs(vec[0]*rel[:,1]-vec[1]*rel[:,0]))/np.linalg.norm(vec)))
        else:
            normal=np.array([-math.sin(p['phi']),math.cos(p['phi'])])
            center=np.asarray(p['start'])+normal/p['k']
            arc_errors.append(float(np.max(np.abs(np.linalg.norm(pts-center,axis=1)-1/abs(p['k'])))))
    lines=[LineString(_sample(p,2.)[:,1:3]).simplify(.02,preserve_topology=True) for p in blocks];n=len(lines);crossings=[]
    for i in range(n):
        for j in range(i+1,n):
            if min(j-i,n-(j-i))<=1:continue
            x=lines[i].intersection(lines[j])
            if not x.is_empty:
                if x.geom_type!='Point':raise ValueError(f'Interseção inesperada: {i}/{j}: {x.geom_type}')
                crossings.append((i,j,x))
    assert len(crossings)==1, f'Esperado 1 cruzamento: {[(i,j,p.wkt) for i,j,p in crossings]}'
    i,j,point=crossings[0];assert blocks[i]['k']==0 and blocks[j]['k']==0
    angle=abs(math.degrees(math.atan2(math.sin(blocks[i]['phi']-blocks[j]['phi']),math.cos(blocks[i]['phi']-blocks[j]['phi']))))
    angle=min(angle,180-angle)
    straight_clearance=min(lines[k].project(point) for k in (i,j))
    straight_clearance=min(straight_clearance,*[lines[k].length-lines[k].project(point) for k in (i,j)])
    poly=[_polygon(m) for m in marks];overlaps=[]
    for a in range(len(poly)):
        for b in range(a+1,len(poly)):
            if poly[a].intersection(poly[b]).area>1e-7:overlaps.append((marks[a]['label'],marks[b]['label']))
    centre_line=LineString(cycle[:,1:3]).simplify(.01,preserve_topology=True)
    actual_gaps=[centre_line.distance(p)-LINE_WIDTH/2 for p in poly]
    # Peças separadas por mais de dois elementos são trechos independentes;
    # a única dupla que se cruza é tratada à parte, conforme o item 4.6.
    independent=[]
    for a in range(n):
        for b in range(a+1,n):
            if min(b-a,n-(b-a))<=2 or (a,b)==(i,j):continue
            independent.append((float(lines[a].distance(lines[b])),a,b))
    min_pieces,closest_a,closest_b=min(independent)
    # Amostras densas de pares não locais; o cruzamento está explicitamente
    # excluído da regra de afastamento por ser permitido pelo item 4.6.
    sample=cycle[::max(1,round(5/step))];xy=sample[:,1:3];tree=cKDTree(xy)
    close=[];min_nonlocal=float('inf');period=meta['period'];c=np.array(meta['crossing'])
    for a,b in tree.query_pairs(260.,output_type='ndarray'):
        along=abs(float(sample[a,0]-sample[b,0]));along=min(along,period-along)
        if along<500:continue
        da=np.linalg.norm(xy[a]-c);db=np.linalg.norm(xy[b]-c)
        if da<=250.1 and db<=250.1:continue
        dist=float(np.linalg.norm(xy[a]-xy[b]));min_nonlocal=min(min_nonlocal,dist)
        if dist<219.-.01:close.append((int(a),int(b),round(dist,3),round(along,1)))
    result=dict(period_mm=meta['period'],marks=len(marks),curve_marks=len(marks)-2,
        closure_mm=float(np.linalg.norm(cycle[-1,1:3]-cycle[0,1:3])),
        max_straight_deviation_mm=max(straight_errors),max_arc_radius_error_mm=max(arc_errors),
        max_join_error_mm=max(join_errors),max_join_angle_error_rad=max(angle_errors),
        min_radius_mm=float(min(1/abs(p['k']) for p in blocks if p['k'])),
        crossing_angle_degrees=angle,crossing_straight_clearance_mm=straight_clearance,
        start_finish_distance_mm=START_X-FINISH_X,start_before_mm=FINISH_X-RADII[0],
        start_after_mm=VERTICES[1,0]-RADII[1]-START_X,
        line_width_mm=LINE_WIDTH,mark_width_mm=MARK_WIDTH,mark_length_mm=MARK_LENGTH,
        mark_gap_from_line_edge_mm=MARK_GAP,edge_clearance_mm=250-LINE_WIDTH/2,
        marker_overlaps=overlaps,min_actual_marker_gap_mm=min(actual_gaps),max_actual_marker_gap_mm=max(actual_gaps),
        min_independent_centreline_mm=min_pieces,
        min_independent_tape_edge_mm=min_pieces-LINE_WIDTH,
        min_independent_pair=[closest_a,closest_b],
        nonlocal_pairs_under_219mm=len(close),
        examples_nonlocal_pairs=close[:12],min_nonlocal_found_mm=(min_nonlocal if min_nonlocal!=float('inf') else None),
        gates_modelled=False,limitations='Validação geométrica discreta e sem portas físicas, não certificação oficial.')
    assert result['period_mm']<=60000 and result['closure_mm']<1e-6
    assert result['max_straight_deviation_mm']<1e-6 and result['max_arc_radius_error_mm']<1e-6 and result['max_join_error_mm']<1e-6 and result['max_join_angle_error_rad']<1e-8
    assert result['min_radius_mm']>=100 and 85<=angle<=95 and straight_clearance>=250
    assert result['start_finish_distance_mm']==1000 and result['start_before_mm']>=250 and result['start_after_mm']>=250
    assert result['edge_clearance_mm']>=200 and result['min_independent_tape_edge_mm']>=200.1
    assert not overlaps and not close and min(actual_gaps)>=37-.05 and max(actual_gaps)<=43+.05
    assert all(m['side']==1 for m in marks if m['kind']=='curva')
    assert all(m['side']==-1 for m in marks if m['kind'] in ('partida','chegada'))
    assert len([b for b in boundaries if abs(b['previous_k']-b['next_k'])>1e-12])==sum(m['kind']=='curva' for m in marks)
    for m in (x for x in marks if x['kind']=='curva'):
        b=boundaries[m['piece_id']]
        assert math.hypot(m['x']-b['x'],m['y']-b['y'])<1e-6
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'validacao_pista_c_regulamentar.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8',newline='\n')
    return result


if __name__=='__main__':check()
