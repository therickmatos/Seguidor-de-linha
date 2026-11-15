"""Geometria de marcas TRIF 2026; não simula eletrônica ou aderência.

Projeto baseado no EVA-RT, (c) EXOTIC TEAM MX, AGPL-3.0.
Modelo: centro da barra sobre a linha, eixo sem escorregamento, corpo rígido.
Integra orientação em função do avanço da barra: d(alpha)/ds=sin(phi-alpha)/L.
As trajetórias são ensaios locais, não o desenho da pista oficial.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import zipfile
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/simulacao_marcas_TRIF_2026'
SOURCE = Path(r'C:\Users\oeric\Downloads\ProPrj_RUSH - SATURN - v3_2026-11-09.epro')
AXLE_Y = -22.56  # STL/decisões do projeto; montagem ainda precisa ser medida.


def read_geometry():
    with zipfile.ZipFile(SOURCE) as z:
        name = next(n for n in z.namelist() if n.endswith('.epcb'))
        rows = [json.loads(l) for l in z.read(name).decode('utf-8-sig').splitlines() if l.strip()]
        attrs = {(r[3], r[7]): r[8] for r in rows if r[0] == 'ATTR'}
        sensors = []
        for r in rows:
            if r[0] == 'COMPONENT' and r[7].get('Name') == 'QRE1113GR':
                sensors.append(dict(id=r[1], ref=attrs[r[1], 'Designator'],
                                    x=r[4]*.0254, y=r[5]*.0254, layer=r[3], rotation=r[6]))
        outline = [r[6] for r in rows if r[0] == 'POLY' and r[4] == 11]
        segments = [[p[0]*.0254, p[1]*.0254, p[3]*.0254, p[4]*.0254] for p in outline if len(p)==5 and p[2]=='L']
        return dict(source=str(SOURCE), sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                    pcb=name, sensors=sensors, outline_segments=segments, axle_y=AXLE_Y,
                    optical_model='Centro do encapsulamento; janelas ópticas e altura não modeladas')


def path(segments, ds=.5):
    # Colunas: s, X para frente, Y para esquerda, phi tangente.
    data = [[0., 0., 0., 0.]]
    marks = []
    for i, (length, k) in enumerate(segments):
        s0,x0,y0,p0 = data[-1]
        n=math.ceil(length/ds)
        for t in np.linspace(0, length, n+1)[1:]:
            p=p0+k*t
            x=x0+(math.sin(p)-math.sin(p0))/k if k else x0+t*math.cos(p0)
            y=y0+(-math.cos(p)+math.cos(p0))/k if k else y0+t*math.sin(p0)
            data.append([s0+t,x,y,p])
        if i < len(segments)-1 and k != segments[i+1][1]: marks.append(len(data)-1)
    return np.array(data), marks


def pose(track, L):
    alpha=np.zeros(len(track))
    for i in range(1,len(track)):
        h=track[i,0]-track[i-1,0]; p=track[i-1,3]; dp=track[i,3]-p; a=alpha[i-1]
        k1=math.sin(p-a)/L
        k2=math.sin(p+dp/2-a-h*k1/2)/L
        k3=math.sin(p+dp/2-a-h*k2/2)/L
        k4=math.sin(p+dp-a-h*k3)/L
        alpha[i]=a+h*(k1+2*k2+2*k3+k4)/6
    return alpha


def sensor_xy(track, alpha, L, lateral, ahead):
    e=np.column_stack((np.cos(alpha),np.sin(alpha)))
    n=np.column_stack((-np.sin(alpha),np.cos(alpha)))
    return track[:,1:3]+(ahead-L)*e+lateral*n


def crossings(track, alpha, L, mark_i, lateral, ahead):
    m=track[mark_i]; p=m[3]; t=np.array([math.cos(p),math.sin(p)]); n=np.array([-math.sin(p),math.cos(p)])
    xy=sensor_xy(track,alpha,L,lateral,ahead)-m[1:3]
    u=xy@t; v=xy@n
    candidates=np.where((u[:-1]<=0)&(u[1:]>0)&(np.abs(track[:-1,0]-m[0])<180))[0]
    center_crossing=bool(len(candidates))
    if center_crossing:
        i=min(candidates,key=lambda j:abs(track[j,0]-m[0]))
        f=-u[i]/(u[i+1]-u[i]); vc=v[i]+f*(v[i+1]-v[i]); sc=track[i,0]+f*(track[i+1,0]-track[i,0])
    else:
        # A path can clip a rectangle corner without crossing its middle plane.
        # In the long L100 case this occurs on tight inner curves. Do not call
        # it a miss solely because the centre-plane crossing does not exist.
        near=np.where(np.abs(track[:,0]-m[0])<180)[0]
        i=near[np.argmin(np.abs(u[near]))];sc=track[i,0];vc=float('nan')
    side=1 if lateral>0 else -1
    distance=side*vc
    # Worst common lateral interval: 18..20mm line, gap 40±3, mark length 40±3.
    # Inner max=10+43=53; outer min=9+37+37=83.
    local=(np.abs(track[:,0]-sc)<70) if center_crossing else (np.abs(track[:,0]-m[0])<180)
    def rectangle(halfwidth,inner,outer):
        # Clip each polyline segment exactly to the rectangle; includes corner hits.
        dwell=0.; best=-1e6
        for j in np.where(local[:-1]&local[1:])[0]:
            lo=0.;hi=1.
            for start,delta,mn,mx in [(u[j],u[j+1]-u[j],-halfwidth,halfwidth)]:
                if abs(delta)<1e-12:
                    if not mn<=start<=mx:hi=-1
                else:
                    a=(mn-start)/delta;c=(mx-start)/delta
                    lo=max(lo,min(a,c));hi=min(hi,max(a,c))
            if hi<lo:continue
            v0=side*(v[j]+lo*(v[j+1]-v[j]));v1=side*(v[j]+hi*(v[j+1]-v[j]))
            nearest=min(max((inner+outer)/2,min(v0,v1)),max(v0,v1))
            best=max(best,min(nearest-inner,outer-nearest))
            delta=side*(v[j+1]-v[j]);start=side*v[j]
            if abs(delta)<1e-12:
                if not inner<=start<=outer:hi=-1
            else:
                a=(inner-start)/delta;c=(outer-start)/delta
                lo=max(lo,min(a,c));hi=min(hi,max(a,c))
            if hi>lo:dwell+=(hi-lo)*(track[j+1,0]-track[j,0])
        return round(float(dwell),4),round(float(best),5)
    dwell,best=rectangle(9.5,49.5,89.5)
    robust_dwell,robust_best=rectangle(9.,53.,83.)
    return dict(distance=round(float(distance),5) if center_crossing else None,
                margin=round(float(min(distance-49.5,89.5-distance)),5) if center_crossing else None,
                tolerance_margin=round(float(min(distance-53,83-distance)),5) if center_crossing else None,
                s_cross=float(sc), bar_travel_on_mark_mm=dwell, best_margin=best,
                robust_bar_travel_mm=robust_dwell, robust_best_margin=robust_best, mark_i=int(mark_i),center_crossing=center_crossing)


def curve(k, angle=math.pi/2):
    return (angle/abs(k),k) if k else (300.,0.)


def run(ds=.5):
    OUT.mkdir(parents=True, exist_ok=True)
    geo=read_geometry(); (OUT/'geometria.json').write_text(json.dumps(geo,ensure_ascii=False,indent=2),encoding='utf-8')
    sensors=geo['sensors']; left=next(s for s in sensors if s['x']<0); right=next(s for s in sensors if s['x']>0)
    ahead=left['y']-AXLE_Y; b=abs(left['x'])
    ks=[0]+[sign/r for r in [100,150,200,300,500] for sign in [-1,1]]
    cases=[]
    # All 110 ordered unequal curvature pairs, approached after 90° or 180° arcs.
    for angle in [math.pi/2,math.pi]:
        for k0 in ks:
            for k1 in ks:
                if k0==k1:continue
                segments=[(400.,0.),curve(k0,angle),curve(k1), (400.,0.)]
                tr,marks=path(segments,ds)
                # Target is the boundary after segment 1, not the two other marks.
                boundary=400+curve(k0,angle)[0]
                mi=int(np.argmin(abs(tr[:,0]-boundary)))
                cases.append((f'{"reta" if not k0 else str(round(1/k0))} → {"reta" if not k1 else str(round(1/k1))}; pré {round(angle*180/math.pi)}°',tr,mi))
    result=[]
    for L in [58,60,62,64,67,70,73,76,82]:
        events=[]
        for name,tr,mi in cases:
            a=pose(tr,L); c=crossings(tr,a,L,mi,b,ahead)
            events.append(dict(case=name,**c))
        summary=dict(L=L,count=len(events),nominal_hits=sum(e['bar_travel_on_mark_mm']>0 for e in events),
                     tolerance_hits=sum(e['robust_bar_travel_mm']>0 for e in events),
                     min_distance=min(e['distance'] for e in events),max_distance=max(e['distance'] for e in events),
                     min_margin=min(e['margin'] for e in events),
                     min_tolerance_margin=min(e['tolerance_margin'] for e in events),
                     min_best_margin=min(e['best_margin'] for e in events),
                     min_robust_best_margin=min(e['robust_best_margin'] for e in events),
                     min_bar_travel=min(e['bar_travel_on_mark_mm'] for e in events),
                     min_robust_bar_travel=min(e['robust_bar_travel_mm'] for e in events),
                     worst=min(events,key=lambda e:e['best_margin']))
        result.append(summary)
        with (OUT/f'eventos_L{L}.csv').open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.DictWriter(f,fieldnames=events[0]);w.writeheader();w.writerows(events)
    (OUT/'resultados.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    # Compact input tracks for interactive view. Signed radius: positive=left.
    examples=[('reta','Reta · partida/chegada',[(700.,0.)],350,-b),
              ('entrada-direita','Entrada em R100 à direita',[(400.,0.),curve(-.01),(350.,0.)],400,b),
              ('saida-direita','Saída de R100 à direita',[(400.,0.),curve(-.01,math.pi),(400.,0.)],400+100*math.pi,b),
              ('entrada-esquerda','Entrada em R100 à esquerda',[(400.,0.),curve(.01),(350.,0.)],400,b),
              ('saida-esquerda','Saída de R100 à esquerda',[(400.,0.),curve(.01,math.pi),(400.,0.)],400+100*math.pi,b),
              ('s-direita-esquerda','S · R100 direita → esquerda',[(400.,0.),curve(-.01),(curve(.01)),(350.,0.)],400+50*math.pi,b),
              ('s-esquerda-direita','S · R100 esquerda → direita',[(400.,0.),curve(.01),(curve(-.01)),(350.,0.)],400+50*math.pi,b)]
    examples.append(('r100-r150-direita','Curvas à direita · R100 → R150',[(400.,0.),curve(-.01,math.pi),curve(-1/150),(400.,0.)],400+100*math.pi,b))
    ui=[]
    for id,label,segs,sm,side in examples:
        tr,_=path(segs,.5); mi=int(np.argmin(abs(tr[:,0]-sm)))
        ui.append(dict(id=id,label=label,track=np.round(tr,5).tolist(),mark_i=mi,lateral=side))
    (OUT/'cenarios.json').write_text(json.dumps(ui,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(json.dumps(dict(sensors=sensors,ahead=ahead,results=result),ensure_ascii=False,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--ds',type=float,default=.5);args=p.parse_args();run(args.ds)
