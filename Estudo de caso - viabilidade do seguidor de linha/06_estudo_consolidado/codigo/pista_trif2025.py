"""Pista B inspirada em fotos do TRIF 2025, não reprodução metrológica.

A geometria é hipotética. Constrói retas, curvas R200, um S e um
cruzamento; aplica o mesmo modelo de marcações do TRIF 2026.
"""
import json,math
from pathlib import Path
import numpy as np
from shapely.geometry import LineString,Polygon,Point
import simular_comparar as model

HERE=Path(__file__).resolve().parent
RADIUS=200.
CORNER=RADIUS*math.pi/2
DIAGONAL=RADIUS*math.pi/4
SHIFT=2*RADIUS*(1-math.cos(math.pi/4))
S_ADVANCE=2*RADIUS*math.sin(math.pi/4)

def segments():
    # Início: (0,900), norte. Os módulos retornam para o início com a
    # mesma orientação. O S desloca-se para leste e depois retorna.
    end_vertical=1400-S_ADVANCE-350-S_ADVANCE+400
    return [(2300,0),(CORNER,-1/RADIUS),(800,0),(CORNER,-1/RADIUS),
      (1200,0),(CORNER,-1/RADIUS),(2000,0),(CORNER,1/RADIUS),(200,0),
      (DIAGONAL,1/RADIUS),(DIAGONAL,-1/RADIUS),(350,0),
      (DIAGONAL,-1/RADIUS),(DIAGONAL,1/RADIUS),(end_vertical,0),
      (CORNER,1/RADIUS),(800,0),(CORNER,1/RADIUS),(1300,0)]

def orient(tr):
    z=tr.copy();z[:,1]=-tr[:,2];z[:,2]=900+tr[:,1];z[:,3]=tr[:,3]+math.pi/2
    return z

def build(step=.5):
    seg=segments();cycle,_=model.old.path(seg,step);cycle=orient(cycle)
    track,_=model.old.path(seg*3,step);track=orient(track)
    period=float(cycle[-1,0]);ends=np.cumsum([s[0] for s in seg]);marks=[]
    def at(s):return track[int(np.argmin(abs(track[:,0]-s)))]
    def mk(s,label,side,kind,transition):
        p=at(s)
        return dict(s=float(p[0]),x=float(p[1]),y=float(p[2]),phi=float(p[3]),side=side,
                    label=label,kind=kind,transition=transition)
    marks.append(mk(period,'Partida',-1,'partida','reta principal'))
    for i,s in enumerate(ends[:-1]):
        if abs(seg[i][1]-seg[i+1][1])>1e-12:
            def desc(k):return 'reta' if not k else f'R{round(abs(1/k))} '+('esquerda' if k>0 else 'direita')
            marks.append(mk(period+s,f'T{i+1}',1,'curva',desc(seg[i][1])+' → '+desc(seg[i+1][1])))
    marks.append(mk(2*period-1000,'Chegada',-1,'chegada','reta principal'))
    marks.sort(key=lambda m:m['s'])
    return track,cycle,marks,dict(start=period,end=2*period-1000+180,
        crossing_s=period+900,crossing=[0,1800],period=period,segments=seg,
        crossing_second_s=period+ends[5]+1000)

def check_geometry(cycle,marks,meta):
    ends=np.r_[0,np.cumsum([p[0] for p in meta['segments']])]
    parts=[]
    for a,b in zip(ends[:-1],ends[1:]):
        start=int(np.argmin(abs(cycle[:,0]-a)));end=int(np.argmin(abs(cycle[:,0]-b)))
        parts.append(LineString(cycle[start:end+1,1:3]))
    found=[]
    for i in range(len(parts)):
        for j in range(i+1,len(parts)):
            if j==i+1 or (i==0 and j==len(parts)-1):continue
            xy=parts[i].intersection(parts[j])
            if not xy.is_empty:
                if xy.geom_type!='Point':raise ValueError(f'Interseção inesperada: {i}, {j}: {xy.geom_type}')
                found.append(dict(piece_a=i,piece_b=j,x=xy.x,y=xy.y))
    if len(found)!=1 or Point(found[0]['x'],found[0]['y']).distance(Point(meta['crossing']))>1e-6:
        raise ValueError(f'Esperado um só cruzamento: {found}')
    line=LineString(cycle[:,1:3]);polys=[]
    for m in marks:
        t=np.array([math.cos(m['phi']),math.sin(m['phi'])]); n=np.array([-t[1],t[0]])*m['side']
        polys.append(Polygon([np.array([m['x'],m['y']])+u*t+v*n for u,v in [(-9.5,49.5),(9.5,49.5),(9.5,89.5),(-9.5,89.5)]]))
    overlaps=[(marks[i]['label'],marks[j]['label']) for i in range(len(polys)) for j in range(i+1,len(polys)) if polys[i].intersection(polys[j]).area>1e-7]
    gaps=[line.distance(p)-9.5 for p in polys]
    closure=float(np.linalg.norm(cycle[-1,1:3]-cycle[0,1:3]))
    result=dict(length_mm=meta['period'],start_to_finish_mm=meta['period']-1000,
       closure_error_mm=closure,line_width_mm=19,minimum_radius_mm=RADIUS,
       n_crossings=len(found),crossings=found,crossing_angle_degrees=90,
       main_straight_before_cross_mm=1800-(-400),main_straight_after_cross_mm=3200-1800,
       other_straight_before_cross_mm=1000,other_straight_after_cross_mm=1000,
       finish_to_start_mm=1000,straight_before_finish_mm=300,straight_after_start_before_cross_mm=900,
       marks=len(marks),mark_overlaps=overlaps,min_mark_edge_to_line_mm=min(gaps),max_mark_edge_to_line_mm=max(gaps),
       fully_certified_against_rules=False)
    assert closure<1e-6 and not overlaps and min(gaps)>=37-.02 and max(gaps)<=43+.02
    return result

def report():
    track,cycle,marks,meta=build(.25)
    checks=check_geometry(cycle,marks,meta)
    cases=[]
    for label,L,x,y in [('63 mm entre furos',model.L_HOLE,69.5,4.5),('Vão EVA',model.L_GAP,69.5,4.5),
        ('Ajuste anterior −8/+1',84.79548357898653,69.5,5.5),('L70',70,69.5,4.5),
        ('L65',65,69.5,4.5),('L60',60,69.5,4.5)]:
        result=model.candidate(label,L,x,y,[(track,cycle,marks)])
        q=result['tracks'][0]
        cases.append(dict(label=label,L=L,x=x,y=y,nominal=q['read'],common=q['common'],total=q['total'],
            missed=q['missed'],events=q['events']))
        print(label,'nominal',q['read'],'/',q['total'],'comum',q['common'],'falhas',q['missed'],flush=True)
    out=dict(warning='Pista aproximada a partir de fotos, não é a planta oficial nem prova de controle em cruzamentos.',
      source_images='Duas imagens fornecidas pelo usuário, TRIF 2025 Campus Votuporanga',
      checked=checks,cases=cases)
    (HERE/'resultados_pista_trif2025.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
    print('VERIFICAÇÃO',json.dumps(checks,ensure_ascii=False),flush=True)

if __name__=='__main__':report()
