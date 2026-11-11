"""Pista de testes do EVA-RT: modelo APROXIMADO reconstruído de um quadro de vídeo.

Fonte: ``imagens/referencia_pista_teste_eva_rt.png`` (vídeo de teste do EVA-RT,
EXOTIC TEAM MX, 1920x1080, em perspectiva). Não há planta nem cotas oficiais.

Como foi obtido (ver ``dados/validacao_pista_eva_rt_teste.json``):
 * os cantos da placa NÃO aparecem inteiros no quadro (só o canto superior
   esquerdo); a retificação usou um modelo de câmera (f, pose do plano) ajustado
   para que as 27 marcas fiquem retangulares e congruentes; os bordos da placa
   (esquerdo perpendicular ao superior em 0,1°) serviram de conferência;
 * a escala foi ajustada para a linha branca medir 19 mm (fator 0,96 sobre a
   escala com marcas 19 x 40 mm); com ela a placa mede ~2440 x 1221 mm
   (chapa padrão), o que concorda com a conferência independente;
 * a linha central foi extraída da imagem retificada e ajustada por retas e
   arcos exatos (ajuste por mínimos quadrados, erro RMS ~1,3 mm no plano);
   as junções são tangentes e a pista é fechada por construção: três peças
   (retas 0 e 10 e arco 23) têm o comprimento calculado para fechar a volta;
 * os trechos escondidos pelo robô (reta de baixo) e cortados pela borda da
   imagem (grampo de baixo à direita) são completados por hipótese.

Referencial: x para a direita, y para cima na foto; origem no canto inferior
esquerdo da placa (suposta 2440 x 1220 mm). O robô corre para a direita na
reta de baixo (partida/chegada à direita dele, abaixo da linha na foto).
As marcas são geradas pela regra (curva à esquerda, partida/chegada à direita),
NÃO copiadas da foto. A pista pode violar itens do regulamento (raio < 100 mm,
trechos a < 200 mm); isso é apenas medido, não imposto.
"""
from pathlib import Path
import json
import math
import numpy as np
from scipy.optimize import fsolve
from shapely.geometry import LineString, Point
from simular_comparar import lap
from pista_c_regulamentar import _polygon

HERE=Path(__file__).resolve().parent
OUT=(HERE.parent/'dados') if HERE.name=='codigo' else HERE
SCALE_FACTOR=0.96          # sobre a escala "marcas 19 x 40 mm"; linha = 19 mm
LINE_WIDTH=19.
BOARD=(2440.,1220.)        # chapa padrão, suposta (só um canto aparece na foto)
START_POSE=(325.97009861,194.06289333,math.radians(0.2356641519483))
# Peças em ordem de percurso: (tipo, raio com sinal [mm; + = esquerda], comprimento [mm]).
# None = calculado para fechar a volta.
PIECES=[
 ('reta',None,None),                       # 0 reta de baixo (fecho)
 ('arco',170.06,140.20),('arco',-151.79,251.76),('arco',156.04,259.09),
 ('arco',-154.04,255.03),('arco',154.24,128.06),   # 1-5 sequência ondulada
 ('reta',None,125.58),                     # 6
 ('arco',208.20,653.48),                   # 7 grampo grande de baixo à direita (180°)
 ('reta',None,1312.25),                    # 8 reta central (3 cruzamentos)
 ('arco',101.35,476.71),                   # 9 laço esquerdo central
 ('reta',None,None),                       # 10 perna (fecho)
 ('arco',-102.09,321.07),                  # 11 laço superior central
 ('reta',None,193.81),                     # 12
 ('arco',102.08,321.11),                   # 13 laço inferior central
 ('reta',None,195.87),                     # 14
 ('arco',-105.01,164.65),                  # 15 curva para a reta de cima
 ('reta',None,808.68),                     # 16 segunda reta
 ('arco',101.08,317.76),                   # 17 grampo da direita (180°, anti-horário)
 ('reta',None,1882.56),                    # 18 reta longa de cima
 ('arco',102.06,396.38),('arco',-102.76,475.08),('arco',102.58,477.53),
 ('arco',-102.27,469.98),('arco',110.91,None),     # 19-23 curvas em S da esquerda
]
CLOSERS=(0,10,23)
# Centros das 27 marcas da foto, no mesmo referencial (mm, aproximados).
PHOTO_MARKS=[[317.4,953.0],[422.5,952.5],[339.3,897.2],[1388.0,888.9],[2202.0,950.1],[805.1,718.1],[337.3,641.4],[2200.4,886.9],[338.6,594.7],[1151.6,719.6],[1213.8,719.1],[774.9,548.0],[806.2,516.8],[1149.2,518.6],[1212.2,517.9],[351.0,337.9],[326.3,265.0],[2084.8,551.6],[1109.2,295.2],[1046.8,266.2],[427.7,125.6],[1444.4,296.7],[1566.4,296.5],[943.2,127.1],[1902.2,298.4],[1963.0,271.9],[2083.2,271.6]]
FINISH_PHOTO=(427.7,125.6)   # marca isolada mais atrás (chegada)
START_PHOTO=(943.2,127.1)    # marca isolada mais à frente (partida)
ESTIMATED_BOXES=[(2240.,335.,2400.,455.),(553.,150.,784.,240.)]  # grampo cortado; robô


def _chain(lengths):
    x,y,th=START_POSE;out=[]
    for (kind,r,_),L in zip(PIECES,lengths):
        k=0. if kind=='reta' else 1./r
        out.append(dict(start=np.array([x,y]),phi=th,length=L,k=k,kind=kind))
        if k:x+=(math.sin(th+k*L)-math.sin(th))/k;y-=(math.cos(th+k*L)-math.cos(th))/k
        else:x+=L*math.cos(th);y+=L*math.sin(th)
        th+=k*L
    return out,(x,y,th)


def _lengths():
    base=np.array([p[2] if p[2] is not None else 0. for p in PIECES],float)
    def f(v):
        L=base.copy();L[list(CLOSERS)]=v
        _,(x,y,th)=_chain(L)
        return [x-START_POSE[0],y-START_POSE[1],th-START_POSE[2]-2*math.pi*N_TURNS]
    v=fsolve(f,[717.,201.,424.],xtol=1e-13)
    L=base.copy();L[list(CLOSERS)]=v;return L


N_TURNS=2   # a tangente gira +720° na volta toda (laços e S)


def pieces():
    blocks,_=_chain(_lengths())
    for i,p in enumerate(blocks):p['id']=i
    return blocks


def _sample(p,step):
    return lap.integrate(p['start'],p['phi'],p['length'],p['k'],step)


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
    # Partida e chegada na reta 0, à direita; posições projetadas das marcas da foto.
    first=blocks[0];d=np.array([math.cos(first['phi']),math.sin(first['phi'])])
    start_phase=float(np.dot(np.array(START_PHOTO)-first['start'],d))
    finish_phase=float(np.dot(np.array(FINISH_PHOTO)-first['start'],d))
    start_pt=first['start']+start_phase*d;finish_pt=first['start']+finish_phase*d
    if not (0<finish_phase<start_phase<first['length']):raise ValueError('Partida/chegada fora da reta')
    def abs_s(s):return period+start_phase+((s-start_phase)%period)
    marks=[]
    for b in boundaries:
        if abs(b['previous_k']-b['next_k'])<1e-12:continue
        marks.append(dict(s=float(abs_s(b['s'])),x=b['x'],y=b['y'],phi=b['phi'],side=1,kind='curva',label='C',
            transition=f"{b['previous_k']:.6g} → {b['next_k']:.6g}",halfWidth=9.5,inner=49.5,outer=89.5,piece_id=b['piece_id']))
    marks.extend([
        dict(s=float(abs_s(start_phase)),x=float(start_pt[0]),y=float(start_pt[1]),phi=first['phi'],side=-1,kind='partida',label='Partida',halfWidth=9.5,inner=49.5,outer=89.5),
        dict(s=float(abs_s(finish_phase)),x=float(finish_pt[0]),y=float(finish_pt[1]),phi=first['phi'],side=-1,kind='chegada',label='Chegada',halfWidth=9.5,inner=49.5,outer=89.5)])
    marks.sort(key=lambda m:m['s']);count=0
    for m in marks:
        if m['kind']=='curva':count+=1;m['label']=f'C{count:02d}'
    # Cruzamentos: pares de retas que se cortam.
    straights=[(i,LineString(_sample(p,max(step,2.))[:,1:3])) for i,p in enumerate(blocks) if p['kind']=='reta']
    crossings=[]
    for a_i in range(len(straights)):
        for b_i in range(a_i+1,len(straights)):
            ia,la=straights[a_i];ib,lb=straights[b_i]
            x=la.intersection(lb)
            if x.is_empty or x.geom_type!='Point':continue
            times=sorted(float(abs_s(boundaries[i]['s']+l.project(x))) for i,l in ((ia,la),(ib,lb)))
            crossings.append(dict(x=float(x.x),y=float(x.y),s=times[0],second_s=times[1],pieces=[ia,ib]))
    crossings.sort(key=lambda c:c['s'])
    estimated=[]
    for p in blocks:
        ar=_sample(p,4.)[:,1:3]
        for x0,y0,x1,y1 in ESTIMATED_BOXES:
            keep=(ar[:,0]>=x0)&(ar[:,0]<=x1)&(ar[:,1]>=y0)&(ar[:,1]<=y1)
            if keep.sum()>1:estimated.append(ar[keep].tolist())
    first_c=crossings[0]
    meta=dict(start=float(abs_s(start_phase)-250),end=float(abs_s(finish_phase)+180),period=period,
        crossing=[first_c['x'],first_c['y']],crossing_s=first_c['s'],crossing_second_s=first_c['second_s'],
        crossings=crossings,estimated=estimated,mat=[0.,0.,BOARD[0],BOARD[1]],
        start_finish_distance_mm=float(start_phase-finish_phase),
        blocks=blocks,boundaries=boundaries,
        note='Modelo aproximado reconstruído de um quadro de vídeo; dimensões estimadas.')
    return track,cycle,marks,meta


def check(step=2.):
    track,cycle,marks,meta=build(step);blocks=meta['blocks'];boundaries=meta['boundaries'];n=len(blocks)
    joins=[float(np.linalg.norm(_sample(p,step)[-1,1:3]-blocks[(i+1)%n]['start'])) for i,p in enumerate(blocks)]
    def wrap(a):return abs(math.atan2(math.sin(a),math.cos(a)))
    angles=[wrap(p['phi']+p['k']*p['length']-blocks[(i+1)%n]['phi']) for i,p in enumerate(blocks)]
    closure=float(np.linalg.norm(cycle[-1,1:3]-cycle[0,1:3]))
    cross_angles=[]
    for c in meta['crossings']:
        i,j=c['pieces'];ang=math.degrees(wrap(blocks[i]['phi']-blocks[j]['phi']));cross_angles.append(min(ang,180-ang))
    arcs=[p for p in blocks if p['k']];straights=[p for p in blocks if not p['k']]
    radii=sorted({round(1/abs(p['k']),1) for p in arcs})
    lines=[LineString(_sample(p,2.)[:,1:3]).simplify(.02,preserve_topology=True) for p in blocks]
    cumulative=np.r_[0.,np.cumsum([p['length'] for p in blocks])];independent=[]
    for a in range(n):
        for b in range(a+1,n):
            along=min(cumulative[b]-cumulative[a+1],cumulative[-1]-cumulative[b+1]+cumulative[a])
            if along<500:continue
            x=lines[a].intersection(lines[b])
            if not x.is_empty:continue
            independent.append((float(lines[a].distance(lines[b])),a,b))
    min_ind=min(independent)
    polys=[_polygon(m) for m in marks]
    overlaps=[(marks[a]['label'],marks[b]['label']) for a in range(len(polys)) for b in range(a+1,len(polys))
              if polys[a].intersection(polys[b]).area>1e-7]
    # Comparação com as marcas da foto: centro de cada marca gerada x marca da foto mais próxima.
    centres=np.array([[m['x']+m['side']*(-math.sin(m['phi']))*69.5,m['y']+m['side']*math.cos(m['phi'])*69.5] for m in marks])
    photo=np.array(PHOTO_MARKS);dist=np.linalg.norm(centres[:,None]-photo[None],axis=2)
    gen_to_photo=dist.min(axis=1);photo_to_gen=dist.min(axis=0)
    first=blocks[0]
    result=dict(modelo='aproximado, reconstruído de um quadro de vídeo (perspectiva retificada)',
        period_mm=meta['period'],closure_mm=closure,max_join_error_mm=max(joins),max_join_angle_error_rad=max(angles),
        pieces=n,arcs=len(arcs),straights=len(straights),min_radius_mm=float(min(1/abs(p['k']) for p in arcs)),
        radii_mm=radii,largest_radius_mm=max(radii),hairpin_right_radius_mm=round(1/abs(blocks[17]['k']),2),
        hairpin_lower_radius_mm=round(1/abs(blocks[7]['k']),2),
        shortest_straight_mm=float(min(p['length'] for p in straights)),
        crossings=len(meta['crossings']),crossing_angles_degrees=cross_angles,
        crossing_points_mm=[[round(c['x'],1),round(c['y'],1)] for c in meta['crossings']],
        scale_factor_adopted=SCALE_FACTOR,line_width_adopted_mm=LINE_WIDTH,board_assumed_mm=list(BOARD),
        start_finish_distance_mm=meta['start_finish_distance_mm'],
        start_finish_distance_note='medida entre as duas marcas isoladas da reta de baixo na foto (centros projetados na reta); inferior a 1 m',
        marks=len(marks),curve_marks=len(marks)-2,photo_marks=len(PHOTO_MARKS),
        photo_curve_marks=len(PHOTO_MARKS)-2,
        generated_marks_within_80mm_of_a_photo_mark=int((gen_to_photo<=80).sum()),
        photo_marks_within_80mm_of_a_generated_mark=int((photo_to_gen<=80).sum()),
        median_generated_to_photo_mm=float(np.median(gen_to_photo)),
        generated_marks_without_photo_mark=[marks[i]['label'] for i in np.nonzero(gen_to_photo>80)[0]],
        photo_marks_without_generated_mark=[PHOTO_MARKS[i] for i in np.nonzero(photo_to_gen>80)[0]],
        marker_overlaps=overlaps,
        min_independent_centreline_mm=min_ind[0],min_independent_tape_edge_mm=min_ind[0]-LINE_WIDTH,min_independent_pair=[min_ind[1],min_ind[2]],
        straight_before_finish_mm=float(np.dot(np.array(FINISH_PHOTO)-first['start'],[math.cos(first['phi']),math.sin(first['phi'])])),
        regulation_violations=dict(radius_below_100=bool(min(1/abs(p['k']) for p in arcs)<100),
            straight_below_200=bool(min(p['length'] for p in straights)<200),
            independent_edge_below_200=bool(min_ind[0]-LINE_WIDTH<200),start_finish_not_1m=True),
        estimated='escala (linha 19 mm; placa suposta 2440 x 1220); trecho do grampo de baixo cortado pela borda da imagem; reta de baixo sob o robô; raios e comprimentos ajustados à imagem (~1,3 mm RMS); marcas geradas pela regra, não copiadas',
        gates_modelled=False,limitations='Aproximação de um quadro de vídeo, não planta nem medição; checagem só geométrica.')
    assert closure<1e-6 and max(joins)<1e-6 and max(angles)<1e-8
    assert len(meta['crossings'])>=1 and all(85<=a<=95 for a in cross_angles)
    assert sum(abs(b['previous_k']-b['next_k'])>1e-12 for b in boundaries)==sum(m['kind']=='curva' for m in marks)
    assert all(m['side']==1 for m in marks if m['kind']=='curva')
    assert all(m['side']==-1 for m in marks if m['kind'] in ('partida','chegada'))
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'validacao_pista_eva_rt_teste.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8',newline='\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return result


if __name__=='__main__':check()
