"""Desenha as faces em escala igual, com o mesmo referencial do EasyEDA.

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as PatchPolygon, Circle
from matplotlib.collections import LineCollection
import matplotlib.patheffects as effects
from shapely.geometry import box

import layout_placa as M

BG='#101419'; BOARD='#1b3029'; GRID='#3c514a'; WHITE='#f3f5ee'
TOP='#ee705f'; BOTTOM='#60aaf2'; AIR='#ffe36f'; PAD='#f2d09a'

def polygon(ax,g,**kw):
    if g.is_empty:return
    if g.geom_type == 'Polygon':
        ax.add_patch(PatchPolygon(list(g.exterior.coords),closed=True,**kw))
    elif hasattr(g,'geoms'):
        for part in g.geoms:polygon(ax,part,**kw)

def mm_width(ax,w):
    return w*ax.figure.get_figwidth()*72*ax.get_position().width/(ax.get_xlim()[1]-ax.get_xlim()[0])

def label_placements(ax,components):
    used=[]
    # Em densidade alta os nomes sao deslocados e uma linha fina aponta ao corpo.
    important={'U1':0,'U2':0,'U3':0,'U5':0,'J1':0,'J2':0,'J3':0,'J4':0,'J5':0}
    for c in sorted(components,key=lambda c:(important.get(c['ref'],1), c['ref'])):
        ref=c['ref']; x,y=c['x'],c['y']
        rect=M.body(c)
        if rect is not None:
            x0,y0,x1,y1=rect.bounds
            sx=max(1.3,(x1-x0)/2+.6); sy=max(1.0,(y1-y0)/2+.65)
        else:sx,sy=1.5,1.5
        candidates=[(0,sy),(0,-sy),(sx,0),(-sx,0),(sx,sy),(-sx,sy),
                    (sx,-sy),(-sx,-sy),(0,sy+1.2),(0,-sy-1.2),
                    (sx+1.4,0),(-sx-1.4,0),(sx+1.5,sy+1),(-sx-1.5,sy+1)]
        w=max(.85,len(ref)*.37); h=.67
        best=None
        for dx,dy in candidates:
            px,py=x+dx,y+dy
            label=box(px-w/2,py-h/2,px+w/2,py+h/2)
            penalty=sum(label.intersection(k).area*100 for k in used)
            if abs(px)>76 or py < -33.3 or py > 27:penalty+=100
            penalty+=math.hypot(dx,dy)*.01
            if best is None or penalty<best[0]:best=(penalty,px,py,label)
        _,px,py,bb=best
        used.append(bb.buffer(.08))
        if math.hypot(px-x,py-y)>2.0:
            ax.plot([x,px],[y,py],color='#e2e8df',lw=.38,alpha=.7,zorder=15)
        t=ax.text(px,py,ref,fontsize=5.2,color=WHITE,ha='center',va='center',
                  zorder=17,fontweight='bold')
        t.set_path_effects([effects.withStroke(linewidth=1.5,foreground=BG)])

def draw_board(ax,positions,data,layer,air=True,mode='normal'):
    ax.set_facecolor(BG); ax.set_xlim(-77,77); ax.set_ylim(-34,28.5); ax.set_aspect('equal',adjustable='box')
    ax.set_xticks(range(-75,76,5)); ax.set_yticks(range(-30,26,5))
    ax.grid(color=GRID,alpha=.35,linewidth=.35,zorder=0)
    ax.tick_params(axis='both',colors='#abbab3',labelsize=5.5,length=2,pad=1)
    for spine in ax.spines.values():spine.set_color('#53645d')
    polygon(ax,M.OUTLINE,facecolor=BOARD,edgecolor='#e1e7db',linewidth=1.2,zorder=1)
    # Estruturas de contato do gearbox, desenhadas sem cobrir cobre.
    if layer==1:
        for a,b in [(-40,-30.5),(30.5,40)]:
            ax.plot([a,a,b,b,a],[-28.5,-1.8,-1.8,-28.5,-28.5],
                    color='#8fa68e',alpha=.42,lw=.65,ls='--',zorder=2)
    tracks=data['tracks']
    if mode=='mudancas':
        palette={'mantida':'#73d598','ajustada':'#f4c95d','removida':'#dd718d','nova':'#65c9f3'}
        for status in ('removida','mantida','ajustada','nova'):
            sub=[t for t in tracks if t['layer']==layer and t['status']==status]
            for t in sub:
                ax.plot(*zip(*t['xy']),color=palette[status],
                        linewidth=max(.45,mm_width(ax,t['width'])*(.45 if status=='removida' else 1)),
                        alpha=.52 if status=='removida' else .95,
                        linestyle='--' if status=='removida' else '-',solid_capstyle='round',zorder=3)
    else:
        for t in tracks:
            if t['layer']!=layer or t['status'] not in ('mantida','ajustada','nova'):continue
            ax.plot(*zip(*t['xy']),color=TOP if layer==1 else BOTTOM,
                    linewidth=max(.35,mm_width(ax,t['width'])),solid_capstyle='round',alpha=.88,zorder=3)
    for v in data['vias']:
        if v['status'] not in ('mantida','nova'):continue
        x,y=v['xy']; d=v['diameter']
        ax.add_patch(Circle((x,y),d/2,facecolor='#ceb47d',edgecolor='#f2e3be',linewidth=.18,zorder=5))
        ax.add_patch(Circle((x,y),v['drill']/2,facecolor=BG,edgecolor='none',zorder=6))
    if air:
        for e in data['ratsnest']:
            (x1,y1),(x2,y2)=e['xy']
            ax.plot([x1,x2],[y1,y2],color=AIR,linewidth=.45,alpha=.77,zorder=7)
    shown=[]
    for c in positions:
        if c['dnp']:continue
        relevant=(c['face']==('TOP' if layer==1 else 'BOTTOM') or c['tht'])
        if not relevant:continue
        b=M.body(c)
        if b is not None and c['face']==('TOP' if layer==1 else 'BOTTOM'):
            polygon(ax,b,facecolor='#d6ded5',edgecolor='#f6f0dc',linewidth=.55,alpha=.22,zorder=8)
            polygon(ax,b,facecolor='none',edgecolor='#e7eee5',linewidth=.48,alpha=.9,zorder=9)
        for p in M.get_pads(c):
            if layer not in p['layers']:continue
            polygon(ax,p['shape'],facecolor=PAD,edgecolor='#fff5d8',linewidth=.25,alpha=.98,zorder=10)
            if p['furo']:
                ax.add_patch(Circle((p['x'],p['y']),p['furo']/2,facecolor=BG,
                                    edgecolor='#e7dfcc',linewidth=.25,zorder=11))
            if p['pin']=='1':
                ax.plot(p['x'],p['y'],marker='.',ms=1.5,color='#fffdf0',zorder=12)
        shown.append(c)
    # Os furos reais sao desenhados por cima, inclusive o rasgo que conflita com J3.
    for name,h in M.HOLES:
        polygon(ax,h,facecolor=BG,edgecolor='#f2e5cd',linewidth=.65,zorder=13)
    label_placements(ax,shown)
    ax.plot([-1.1,1.1],[0,0],color='#ffdf80',lw=.55,zorder=14)
    ax.plot([0,0],[-1.1,1.1],color='#ffdf80',lw=.55,zorder=14)
    ax.text(1.5,.7,'(0,0)',fontsize=5,color='#ffdf80',zorder=14)
    if layer==1:
        # A geometria original fica intacta; o ponto de conflito fica inequivoco.
        ax.annotate('J3: PROPOSTA\ncolide com rasgo',xy=(14.08,-28.5),xytext=(20.5,-33.0),
                    color='#ffbd72',fontsize=5.8,fontweight='bold',ha='left',
                    arrowprops={'arrowstyle':'->','color':'#ffbd72','lw':.7},zorder=20)
        ax.text(-54,8.6,'J1: PROPOSTA',fontsize=5.3,color='#ffbd72',ha='center',zorder=20)
        ax.text(-11,-31.7,'X1 3225: PROPOSTA',fontsize=5.3,color='#ffbd72',ha='center',zorder=20)
    if mode=='mudancas':
        for c in shown:
            e=c.get('eva')
            if not e or c.get('mudou')=='nao':continue
            if (e['lado']=='BOT') != (layer==2):continue
            ax.plot(e['x'],e['y'],marker='x',ms=2.4,color='#ef9ab2',mew=.6,zorder=16)
            ax.plot([e['x'],c['x']],[e['y'],c['y']],color='#ef9ab2',lw=.35,ls=':',alpha=.7,zorder=14)

def header(fig,title,subtitle):
    fig.patch.set_facecolor(BG)
    fig.text(.045,.976,title,color=WHITE,fontsize=15,fontweight='bold',ha='left',va='top')
    fig.text(.045,.949,subtitle,color='#b8c7be',fontsize=8.4,ha='left',va='top')

def render_stage1(positions,data):
    fig=plt.figure(figsize=(21,17.2),dpi=200)
    header(fig,'ETAPA 1  |  Posicionamento + cobre do EVA-RT',
           'Primeira versão: vermelho = cobre superior · azul = inferior · amarelo = ligações pendentes · +y = frente · grade 5 mm')
    a=fig.add_axes([.045,.51,.91,.41]); b=fig.add_axes([.045,.065,.91,.41])
    draw_board(a,positions,data,1); draw_board(b,positions,data,2)
    a.set_title('FACE DE CIMA',loc='left',color=TOP,fontsize=10,fontweight='bold',pad=4)
    b.set_title('FACE DE BAIXO — vista através da placa, sem espelhar',loc='left',color=BOTTOM,fontsize=10,fontweight='bold',pad=4)
    fig.text(.047,.035,f"{len(data['ratsnest'])} ligações ainda abertas · J3 e XT30 são propostas · furo/rasgo original mostrado intacto · ponto branco = pino 1",
             color='#ffcf86',fontsize=8.2)
    fig.text(.047,.015,'Baseado no EVA-RT © EXOTIC TEAM MX — AGPL-3.0. Prévia para revisão no EasyEDA Pro.',
             color='#8ba198',fontsize=7)
    out=M.OUTPUT/'placa_etapa1.jpg'
    fig.savefig(out,dpi=200,facecolor=BG,pil_kwargs={'quality':92,'optimize':True})
    plt.close(fig)
    print(out)

if __name__=='__main__':
    positions=M.load_positions()
    M.export_positions(positions)
    data=json.loads((M.HERE/'trilhas_classificadas.json').read_text(encoding='utf8'))
    render_stage1(positions,data)
