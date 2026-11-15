"""Gera as prévias das pistas a partir dos dados usados no simulador."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Patch
from matplotlib.lines import Line2D
import pista_trif2025 as track25
import pista_c_regulamentar as track24
import pista_eva_rt_teste as trackeva

HERE=Path(__file__).resolve().parent
OUT=HERE.parent/'imagens'


def draw(module,year,rotate,title=None,filename=None):
    track,cycle,marks,meta=module.build(1.)
    def project(points):
        a=np.asarray(points)
        return np.stack((-a[...,1],a[...,0]),axis=-1) if rotate else a
    fig,ax=plt.subplots(figsize=(10,10),facecolor='#101820')
    ax.set_facecolor('#101820')
    points=project(cycle[:,1:3]);ax.plot(points[:,0],points[:,1],color='white',lw=2)
    for m in marks:
        co,si=np.cos(m['phi']),np.sin(m['phi']);corners=[]
        for u,v in [(-9.5,49.5),(9.5,49.5),(9.5,89.5),(-9.5,89.5)]:
            corners.append((m['x']+u*co-v*m['side']*si,m['y']+u*si+v*m['side']*co))
        ax.add_patch(Polygon(project(corners),color='#ffc47b' if m['side']<0 else '#a3d4ff'))
    for segment in meta['estimated']:
        pts=project(segment);ax.plot(pts[:,0],pts[:,1],color='#ffc47b',linestyle='--',lw=2)
    crossing=project([[c['x'],c['y']] for c in meta['crossings']] if 'crossings' in meta else [meta['crossing']])
    ax.scatter(*np.atleast_2d(crossing).T,facecolor='none',edgecolor='#58cfff',s=80)
    indices=[int(np.argmin(abs(track[:,0]-(meta['start']+ds)))) for ds in (100,350)]
    begin,end=project(track[indices,1:3])
    ax.annotate('',xy=end,xytext=begin,arrowprops=dict(arrowstyle='->',color='#8bf0c9',lw=3))
    ax.set_aspect('equal');ax.axis('off')
    ax.set_title(title or f'TRIF {year} — modelo aproximado',color='white',fontsize=20)
    legend=[Patch(color='#a3d4ff',label='marcas de curva'),Patch(color='#ffc47b',label='partida / chegada')]
    if meta['estimated']:legend.insert(0,Line2D([0],[0],color='#ffc47b',ls='--',label='trecho hipotético'))
    fig.legend(handles=legend,loc='lower center',ncol=len(legend),frameon=False,labelcolor='white',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,1));OUT.mkdir(parents=True,exist_ok=True)
    fig.savefig(OUT/(filename or f'trif_{year}.png'),dpi=120,facecolor=fig.get_facecolor());plt.close(fig)


if __name__=='__main__':
    draw(track25,'2025',False);draw(track24,'2024',False,title='TRIF 2024 — sentido corrigido (modelo aproximado)',filename='trif_2024.png')
    draw(trackeva,'EVA-RT',False,title='Pista de teste do EVA-RT — modelo aproximado da foto',filename='pista_teste_eva_rt.png')
