"""Volta geométrica numa pista de teste TRIF, sem modelo de motores/aderência.

Baseado no EVA-RT, © EXOTIC TEAM MX, AGPL-3.0.
Unidades mm. Mundo X,Y; heading CCW. PCB x direita, y frente.
"""
from pathlib import Path
import csv
import json
import math
import numpy as np
from shapely.geometry import LineString, Polygon, MultiPoint, box
import simular_marcas_trif as sim

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/volta_TRIF_2026'


def integrate(start,phi,length,k,step=.5):
    ss=np.linspace(0,length,math.ceil(length/step)+1)
    pp=phi+k*ss
    if k:
        xx=start[0]+(np.sin(pp)-math.sin(phi))/k
        yy=start[1]+(math.cos(phi)-np.cos(pp))/k
    else:xx=start[0]+ss*math.cos(phi);yy=start[1]+ss*math.sin(phi)
    return np.column_stack((ss,xx,yy,pp))


def build_course(step=.5):
    vertices=np.array([[0,0],[3000,0],[3000,1500],[1800,1500],[1800,700],[1200,700],[1200,2000],[0,2000]],float)
    # On the inside of a 90° corner, two short R100/R150 arcs made
    # neighbouring 40x19mm marks overlap. Use R200/R300 at this compound
    # corner; retain separate R100 left/right corners elsewhere.
    corner_radii=[[300],[200,300],[200],[100],[150],[100],[500],[300]]
    corners=[]
    for i,v in enumerate(vertices):
        ein=v-vertices[i-1];ein/=np.linalg.norm(ein)
        eout=vertices[(i+1)%len(vertices)]-v;eout/=np.linalg.norm(eout)
        sign=float(np.sign(np.cross(np.r_[ein,0],np.r_[eout,0])[2]))
        radii=corner_radii[i]; angle=math.pi/(2*len(radii));q=np.zeros(2);phi=0.;parts=[]
        for radius in radii:
            part=integrate(q,phi,radius*angle,sign/radius,step)
            q=part[-1,1:3];phi=part[-1,3];parts.append((radius*angle,sign/radius))
        din=float(q[0]);dout=float(abs(q[1]))
        entry=v-din*ein;exit=v+dout*eout
        corners.append(dict(entry=entry,exit=exit,phi=math.atan2(ein[1],ein[0]),parts=parts))
    # A periodic reference circuit starts after corner 0. Exact straight/arc closure.
    pieces=[]
    for i in range(len(vertices)):
        ni=(i+1)%len(vertices);p=corners[i]['exit'];target=corners[ni]['entry']
        vec=target-p;length=np.linalg.norm(vec);phi=math.atan2(vec[1],vec[0])
        pieces.append(dict(start=p,phi=phi,length=length,k=0.,group=2*i,name=f'Reta {i+1}'))
        q=target.copy();p0=phi
        for length,k in corners[ni]['parts']:
            pieces.append(dict(start=q,phi=p0,length=length,k=k,group=2*i+1,name=f'R{round(abs(1/k))} '+('esquerda' if k>0 else 'direita')))
            last=integrate(q,p0,length,k,step)[-1];q=last[1:3];p0=last[3]
    cycle=[];offset=0.;groups={}
    for p in pieces:
        a=integrate(p['start'],p['phi'],p['length'],p['k'],step);a[:,0]+=offset
        cycle.extend(a[:-1].tolist());offset=a[-1,0]
        groups.setdefault(p['group'],[]).extend(a[:,1:3].tolist())
    cycle.append(a[-1].tolist());cycle=np.array(cycle);cycle[:,3]=np.unwrap(cycle[:,3])
    closure=float(np.linalg.norm(cycle[-1,1:3]-cycle[0,1:3]))
    # Simulation starts in the 1m starting zone, before the start mark.
    # Start x=1800, finish x=800, travel direction +X on the bottom straight.
    initial=pieces[0].copy();initial['start']=np.array([1500.,0.]);initial['length']=float(corners[1]['entry'][0]-1500)
    runpieces=[initial]+pieces[1:]
    runpieces.append(dict(start=corners[0]['exit'],phi=0.,length=800.,k=0.,group=0,name='Reta de chegada'))
    track=[];offset=0.;boundaries=[]
    for i,p in enumerate(runpieces):
        a=integrate(p['start'],p['phi'],p['length'],p['k'],step);a[:,0]+=offset
        if i and p['k']!=runpieces[i-1]['k']:
            boundaries.append(dict(s=offset,x=float(a[0,1]),y=float(a[0,2]),phi=float(a[0,3]),
                                   label=f'M{len(boundaries)+1}',side=1,kind='curva',transition=runpieces[i-1]['name']+' → '+p['name']))
        track.extend(a[:-1].tolist());offset=a[-1,0]
    track.append(a[-1].tolist());track=np.array(track);track[:,3]=np.unwrap(track[:,3])
    finish_s=float(track[-1,0]-300)
    marks=[dict(s=300.,x=1800.,y=0.,phi=0.,label='Partida',side=-1,kind='partida',transition='reta')]+boundaries
    marks.append(dict(s=finish_s,x=800.,y=0.,phi=2*math.pi,label='Chegada',side=-1,kind='chegada',transition='reta'))
    marks.sort(key=lambda m:m['s'])
    for j,m in enumerate(marks):m['id']=j
    mark_polygons=[]
    for m in marks:
        co,si=math.cos(m['phi']),math.sin(m['phi']);side=m['side']
        polygon=Polygon([(m['x']+u*co-v*side*si,m['y']+u*si+v*side*co)
                         for u,v in [(-9.5,49.5),(9.5,49.5),(9.5,89.5),(-9.5,89.5)]])
        assert abs(polygon.area-40*19)<1e-5
        mark_polygons.append(polygon)
    overlaps=[];marker_clearances=[]
    for i,p in enumerate(mark_polygons):
        for j in range(i+1,len(mark_polygons)):
            q=mark_polygons[j];area=p.intersection(q).area
            if area>1e-7:overlaps.append(dict(a=marks[i]['label'],b=marks[j]['label'],area_mm2=area))
            marker_clearances.append(p.distance(q))
    line=LineString(cycle[:,1:3])
    x0,y0,x1,y1=line.bounds;manta=box(x0-300,y0-300,x1+300,y1+300)
    effective_gaps=[line.distance(p)-9.5 for p in mark_polygons]
    # Keep clearance verification independent of the integration sampling rate.
    # 0.01mm simplification is negligible beside the >200mm clearance requirement.
    group_lines=[LineString(groups[i]).simplify(.01,preserve_topology=True) for i in sorted(groups)]
    # Connected pieces and the two straight legs of one rounded corner are
    # neighbours; measure clearance between remaining independent sections.
    separations=[];ng=len(group_lines)
    for i in range(ng):
        for j in range(i+1,ng):
            if min(j-i,ng-(j-i))>2:separations.append(group_lines[i].distance(group_lines[j]))
    checks=dict(closed_error_mm=closure,is_simple=LineString(cycle[:,1:3]).is_simple,
                min_radius_mm=min(abs(1/p['k']) for p in pieces if p['k']),
                total_circuit_mm=float(cycle[-1,0]),start_to_finish_mm=finish_s-300,
                start_finish_spacing_mm=1000.,min_independent_sections_mm=min(separations),
                straight_before_finish_mm=800-corners[0]['exit'][0],
                straight_after_start_mm=corners[1]['entry'][0]-1800,
                track_border_margin_mm=300.,gate_inner_width_mm=400.,gate_inner_height_mm=200.,
                line_width_mm=19.,mark_width_mm=19.,mark_length_mm=40.,mark_gap_mm=40.,
                mark_overlap_count=len(overlaps),mark_overlaps=overlaps,
                min_gap_between_mark_polygons_mm=min(marker_clearances),
                effective_mark_to_line_edge_min_mm=min(effective_gaps),
                effective_mark_to_line_edge_max_mm=max(effective_gaps),
                min_line_edge_to_manta_border_mm=manta.boundary.distance(line)-9.5,
                gates_modelled=False,geometry_revision=2)
    assert closure<1e-7 and checks['is_simple'] and checks['min_radius_mm']>=100
    assert checks['min_independent_sections_mm']>=200
    assert checks['straight_before_finish_mm']>=250 and checks['straight_after_start_mm']>=250
    assert checks['total_circuit_mm']<=60000
    assert not overlaps, f'Marcações sobrepostas: {overlaps}'
    assert checks['min_line_edge_to_manta_border_mm']>=200
    assert min(effective_gaps)>=37-.01 and max(effective_gaps)<=43+.01
    return track,cycle,marks,checks


def clip_segment(a,b,xmin,xmax,ymin,ymax):
    lo=0.;hi=1.
    for start,delta,mn,mx in [(a[0],b[0]-a[0],xmin,xmax),(a[1],b[1]-a[1],ymin,ymax)]:
        if abs(delta)<1e-12:
            if not mn<=start<=mx:return None
        else:
            q0=(mn-start)/delta;q1=(mx-start)/delta
            lo=max(lo,min(q0,q1));hi=min(hi,max(q0,q1))
            if hi<lo:return None
    return lo,hi


def inspect_mark(track,xy,m):
    e=np.array([math.cos(m['phi']),math.sin(m['phi'])]);n=np.array([-e[1],e[0]])
    rel=xy-np.array([m['x'],m['y']])
    uv=np.column_stack((rel[:,0]*e[0]+rel[:,1]*e[1],m['side']*(rel[:,0]*n[0]+rel[:,1]*n[1])))
    # Covers the full physical passage, not only its centre-plane crossing.
    local=np.where((track[:,0]>m['s']-200)&(track[:,0]<m['s']+300))[0]
    spans=[];robust=[];cross=[];closest=(float('inf'),None,None)
    for j in local[:-1]:
        a,b=uv[j],uv[j+1];sa,sb=track[j,0],track[j+1,0]
        for target,box in [(spans,(-9.5,9.5,49.5,89.5)),(robust,(-9.,9.,53.,83.))]:
            clipped=clip_segment(a,b,*box)
            if clipped:
                l,h=clipped
                if h-l>1e-8:target.append((sa+l*(sb-sa),sa+h*(sb-sa)))
        if (a[0]<=0<b[0]) or (b[0]<=0<a[0]):
            f=-a[0]/(b[0]-a[0]);cross.append((sa+f*(sb-sa),float(a[1]+f*(b[1]-a[1]))))
        centre=np.array([0.,69.5]);delta=b-a
        f=float(np.clip(np.dot(centre-a,delta)/max(np.dot(delta,delta),1e-20),0,1))
        distance=float(np.linalg.norm(a+f*delta-centre))
        if distance<closest[0]:closest=(distance,sa+f*(sb-sa),a+f*delta)
    if cross:
        sc,radial=min(cross,key=lambda x:abs(x[0]-m['s']))
        error=radial-69.5
    else:sc=closest[1];radial=None;error=None
    hit=bool(spans)
    return dict(**m,read=hit,common_tolerance_read=bool(robust),
                centre_distance_mm=radial,centre_error_mm=error,centre_within_1mm=error is not None and abs(error)<=1,
                centre_plane_s=float(sc),closest_centre_distance_mm=closest[0],
                entry_s=spans[0][0] if spans else None,exit_s=spans[-1][1] if spans else None,
                bar_travel_on_mark_mm=sum(h-l for l,h in spans),
                spans=spans,robust_spans=robust)


def main(step=.5):
    OUT.mkdir(parents=True,exist_ok=True)
    mechanics=json.loads((ROOT/'output/simulacao_marcas_TRIF_2026/estimativa_mecanica_EVA.json').read_text(encoding='utf-8'))
    geo=sim.read_geometry();axis=mechanics['axle_from_stl_y_mm']
    # Actual top contour of received PCB, not the original EVA nose.
    nose=max(max(seg[1],seg[3]) for seg in geo['outline_segments'])
    gap=34.88849766;bar_rear=-2.76151;central=mechanics['V1_central_sensor_local_y_mm']
    translation=nose+gap-bar_rear;L=translation+central-axis;ahead=4.50000116-axis
    track,cycle,marks,checks=build_course(step);alpha=sim.pose(track,L)
    left=sim.sensor_xy(track,alpha,L,69.5000007,ahead);right=sim.sensor_xy(track,alpha,L,-69.5000007,ahead)
    events=[inspect_mark(track,left if m['side']>0 else right,m) for m in marks]
    config=dict(geometry_revision=2,gap_mm=gap,nose_y_mm=nose,axle_y_mm=axis,bar_translation_y_mm=translation,
                central_sensor_local_y_mm=central,L_mm=L,ahead_mm=ahead,side_sensor_offset_mm=69.5,
                model='Barra virtual ideal sobre o centro da linha, eixo sem escorregamento; sem dinâmica de motores',
                centre_criterion_mm=1.,step_mm=step,official_track=False,
                tyre_diameter_mm=None,physical_lap_time_s=None)
    summary=dict(mark_count=len(events),read=sum(e['read'] for e in events),missed=[e['label'] for e in events if not e['read']],
                 common_tolerance_read=sum(e['common_tolerance_read'] for e in events),
                 centred_within_1mm=sum(e['centre_within_1mm'] for e in events),
                 min_centre_offset_mm=min(e['centre_distance_mm'] for e in events if e['centre_distance_mm'] is not None),
                 max_centre_offset_mm=max(e['centre_distance_mm'] for e in events if e['centre_distance_mm'] is not None),
                 max_absolute_centre_error_mm=max(abs(e['centre_error_mm']) for e in events if e['centre_error_mm'] is not None))
    data=dict(config=config,checks=checks,summary=summary,events=events)
    (OUT/'analise_volta.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    with (OUT/'passagens_marcas.csv').open('w',newline='',encoding='utf-8-sig') as f:
        fields=[k for k in events[0] if k not in ['spans','robust_spans']];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:e[k] for k in fields} for e in events)
    with (OUT/'trajetoria_completa.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['bar_s_mm','bar_x_mm','bar_y_mm','heading_rad','left_x_mm','left_y_mm','right_x_mm','right_y_mm'])
        w.writerows(np.column_stack((track[:,:3],alpha,left,right)))
    # Compact animation data; keep exact event poses, and interpolate only drawing.
    stride=max(1,round(4/step));idx=set(range(0,len(track),stride));idx.add(len(track)-1)
    for e in events:idx.add(int(np.argmin(abs(track[:,0]-e['centre_plane_s']))))
    idx=sorted(idx)
    ui=dict(**data,frames=np.round(np.column_stack((track[idx,:3],alpha[idx])),5).tolist(),
            course=np.round(np.vstack((cycle[::stride,1:3],cycle[-1,1:3])),4).tolist(),
            geometry=dict(outline_segments=geo['outline_segments'],axle_y=axis,
                          front_sensor_centres=mechanics['front_sensor_centres'],
                          bar_translation=translation,
                          motor_blocks=[[-40,-28.5,-30.5,-1.8],[30.5,-28.5,40,-1.8]],
                          wheel_rim_max_diameter_mm=mechanics['wheel_stl_flange_diameter_mm']))
    # Rim silhouette from STL. Axial insertion is illustrative; only the shaft Y
    # is mechanically constrained and used in the mark calculations.
    b=(ROOT/'referencias/eva-rt/3d_models/wheel_rim.stl').read_bytes()
    dt=np.dtype([('normal','<f4',(3,)),('v','<f4',(3,3)),('a','<u2')])
    vv=np.frombuffer(b[84:],dtype=dt)['v'].reshape(-1,3)
    hull=np.array(MultiPoint(np.column_stack((60.5-vv[:,2],axis+vv[:,0]))).convex_hull.exterior.coords)
    ui['geometry']['wheel_hulls']=[hull.round(5).tolist(),(hull*np.array([-1,1])).round(5).tolist()]
    (OUT/'dados_animacao.json').write_text(json.dumps(ui,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(json.dumps(dict(config=config,checks=checks,summary=summary),ensure_ascii=False,indent=2))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--step',type=float,default=.5);args=p.parse_args();main(args.step)
