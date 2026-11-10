"""Comparação cinemática espacial de duas pistas, não modelo de PID ou ótica.

Reutiliza a construção de pista arquivada por therickmatos, baseada no EVA-RT,
© EXOTIC TEAM MX, sob AGPL-3.0-or-later. A busca e a checagem de limites são
novas; as pistas são hipóteses, não o circuito oficial do evento.
"""
from pathlib import Path
import json, math, sys
import numpy as np
from scipy.integrate import solve_ivp
from shapely.geometry import LineString, Polygon, box

def _study_root():
    for parent in Path(__file__).resolve().parents:
        if (parent / '05_codigo' / 'originais').is_dir() and (parent / '03_simulacoes').is_dir():
            return parent
        candidate = parent / 'Estudo de caso - viabilidade do seguidor de linha'
        if (candidate / '05_codigo' / 'originais').is_dir():
            return candidate
    raise FileNotFoundError('Pasta do estudo e 05_codigo/originais não encontrados.')

CASE = _study_root()
ROOT = CASE.parent
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(CASE / '05_codigo' / 'originais'))
import simular_marcas_trif as old
import simular_volta_trif as lap

AXLE = -22.587743818986525
Y_HOLE_BASE = 10.75
X_HOLE_BASE = 43.75
X_HOLE_V1 = 44.62624
Y_HOLE_V1 = -3.68496
Y_SENSOR_V1 = 6.9577325
Y_NOTCH_V1 = -2.76151
NOSE = 25.6
HOLE_DIST = 63.141
HOLE_DY = math.sqrt(HOLE_DIST**2 - (X_HOLE_V1-X_HOLE_BASE)**2)
L_HOLE = Y_HOLE_BASE+HOLE_DY-Y_HOLE_V1+Y_SENSOR_V1-AXLE
L_GAP = 92.79548357898653

def oval(step):
    archive = json.loads((CASE/'03_simulacoes/02_ajuste_8mm_1mm/verificacao_circuito_6_de_7.json').read_text(encoding='utf8'))
    seg = archive['segments']
    cycle,_ = old.path(seg,step)
    period=cycle[-1,0]
    track,_=old.path(seg*3,step)
    boundaries=np.r_[0,np.cumsum([e[0] for e in seg])]
    marks=[]
    for i,ph in enumerate(boundaries[1:]):
        p=track[np.argmin(abs(track[:,0]-(period+ph)))]
        marks.append(dict(s=float(p[0]),x=float(p[1]),y=float(p[2]),phi=float(p[3]),side=1,label=f'C{i+1}',kind='curva'))
    for label,dist,kind in [('Partida',period+1500,'partida'),('Chegada',2*period+500,'chegada')]:
        p=track[np.argmin(abs(track[:,0]-dist))]
        marks.append(dict(s=float(p[0]),x=float(p[1]),y=float(p[2]),phi=float(p[3]),side=-1,label=label,kind=kind))
    return track,cycle,marks

def tracks(step):
    a,cycle,marks,checks=lap.build_course(step)
    b,ovalcycle,omarks=oval(step)
    return [(a,cycle,marks),(b,ovalcycle,omarks)]

def evaluate(track, marks, alpha, L, xs, ys):
    """Margem L-infinito ao melhor ponto da trajetória: positiva dentro da fita.

    O máximo é amostrado; será mais conservador até aprox. meio passo espacial.
    A região comum de tolerâncias é 53..83 mm por ±9 mm longitudinal.
    """
    xs=np.atleast_1d(xs); ys=np.atleast_1d(ys)
    ca=np.cos(alpha); sa=np.sin(alpha); all_nom=[]; all_common=[]
    for m in marks:
        mask=(track[:,0]>m['s']-200)&(track[:,0]<m['s']+300)
        z=track[mask]; c=ca[mask]; s=sa[mask]
        ct,st=math.cos(m['phi']),math.sin(m['phi']); side=m['side']
        dx=z[:,1]-m['x']; dy=z[:,2]-m['y']
        eu=c*ct+s*st; ev=side*(-c*st+s*ct)
        nu=-s*ct+c*st; nv=side*(s*st+c*ct)
        lead=(ys-AXLE-L)[None,:]; lateral=side*xs[None,:]
        u=(dx*ct+dy*st)[:,None]+lead*eu[:,None]+lateral*nu[:,None]
        v=(side*(-dx*st+dy*ct))[:,None]+lead*ev[:,None]+lateral*nv[:,None]
        nom=np.minimum(np.minimum(9.5-np.abs(u),v-49.5),89.5-v)
        common=np.minimum(np.minimum(9-np.abs(u),v-53),83-v)
        all_nom.append(np.max(nom,axis=0)); all_common.append(np.max(common,axis=0))
    return np.array(all_nom),np.array(all_common)

def detail(track,marks,L,x,y):
    alpha=old.pose(track,L)
    left=old.sensor_xy(track,alpha,L,x,y-AXLE); right=old.sensor_xy(track,alpha,L,-x,y-AXLE)
    nom,common=evaluate(track,marks,alpha,L,[x],[y]); events=[]
    for i,m in enumerate(marks):
        coords=left if m['side']>0 else right
        event=lap.inspect_mark(track,coords,m)
        t=np.array([math.cos(m['phi']),math.sin(m['phi'])]); n=np.array([-t[1],t[0]])
        poly=Polygon([np.array([m['x'],m['y']])+u*t+v*m['side']*n for u,v in [(-9.5,49.5),(9.5,49.5),(9.5,89.5),(-9.5,89.5)]])
        sel=(track[:,0]>m['s']-200)&(track[:,0]<m['s']+300)
        intersection=LineString(coords[sel]).intersection(poly)
        hit=intersection.length>1e-8
        if hit!=event['read']:
            raise ValueError(f'Interseção divergente {m["label"]}: {hit} vs {event["read"]}')
        events.append({k:v for k,v in event.items() if k not in ('spans','robust_spans')})
        events[-1].update(nominal_margin_sampled_mm=float(nom[i,0]),common_margin_sampled_mm=float(common[i,0]),shapely_hit=hit)
    return events,alpha,left,right

def candidate(label,L,x,y,data):
    results=[]
    for track,_,marks in data:
        events,*_=detail(track,marks,L,x,y)
        results.append(dict(total=len(events),read=sum(e['read'] for e in events),
            common=sum(e['common_tolerance_read'] for e in events),
            missed=[e['label'] for e in events if not e['read']],
            worst_nominal=min(events,key=lambda e:e['nominal_margin_sampled_mm'])['label'],
            min_margin_nominal=min(e['nominal_margin_sampled_mm'] for e in events),
            min_margin_common=min(e['common_margin_sampled_mm'] for e in events),events=events))
    translation=L+AXLE-Y_SENSOR_V1
    return dict(label=label,L=L,x=x,y=y,gap=translation+Y_NOTCH_V1-NOSE,
                hole_dy=translation+Y_HOLE_V1-Y_HOLE_BASE,
                hole_distance=math.hypot(translation+Y_HOLE_V1-Y_HOLE_BASE,X_HOLE_V1-X_HOLE_BASE),tracks=results)

