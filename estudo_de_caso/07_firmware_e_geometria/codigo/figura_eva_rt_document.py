"""Desenha o contorno e a camada Document do EVA_RT_PCB, lidos de EVA_RT.eprj.

EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0 (github.com/EXOTIC-TEAM-MX/EVA-RT).
Uso: cd codigo && python3 figura_eva_rt_document.py
"""
import base64,gzip,json,math,sqlite3
from pathlib import Path
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent
EPRJ=HERE.parents[2]/'referencias'/'eva-rt'/'pcb_files'/'EVA_RT.eprj'
OUT=HERE.parent/'imagens'/'eva_rt_camada_document.png'
data=sqlite3.connect(EPRJ).execute("select dataStr from documents where title='eva_rt_pcb'").fetchone()[0]
rows=[json.loads(l) for l in gzip.decompress(base64.b64decode(data[6:])).decode('utf8').splitlines() if l.strip()]
M=.0254
fig,ax=plt.subplots(figsize=(11,9.5))
def rect(p,c,lw,ls='-'):
    x,y,w,h,rot=p[1]*M,p[2]*M,p[3]*M,p[4]*M,p[5]
    pts=[(0,0),(w,0),(w,-h),(0,-h),(0,0)]
    a=math.radians(rot);pts=[(x+u*math.cos(a)-v*math.sin(a),y+u*math.sin(a)+v*math.cos(a)) for u,v in pts]
    ax.plot([q[0] for q in pts],[q[1] for q in pts],color=c,lw=lw,ls=ls)
def path(p,c,lw):
    if p[0]=='CIRCLE': ax.add_patch(plt.Circle((p[1]*M,p[2]*M),p[3]*M,fill=False,color=c,lw=lw));return
    if p[0]=='R': rect(p,c,lw);return
    pts=[];i=0;cur=None
    while i<len(p):
        t=p[i]
        if isinstance(t,(int,float)): cur=(p[i]*M,p[i+1]*M);pts.append(cur);i+=2
        elif t=='L': i+=1
        elif t in('ARC','CARC'):
            ang=p[i+1];ex,ey=p[i+2]*M,p[i+3]*M;sx,sy=cur;a=math.radians(ang);d=math.hypot(ex-sx,ey-sy)
            if abs(a)>1e-9 and d>0:
                r=d/2/math.sin(abs(a)/2);mx,my=(sx+ex)/2,(sy+ey)/2;h=r*math.cos(abs(a)/2);nx,ny=-(ey-sy)/d,(ex-sx)/d
                sg=1 if a>0 else -1;cx,cy=mx+sg*h*nx,my+sg*h*ny;a0=math.atan2(sy-cy,sx-cx)
                for k in range(1,25): pts.append((cx+r*math.cos(a0+a*k/24),cy+r*math.sin(a0+a*k/24)))
            cur=(ex,ey);pts.append(cur);i+=4
        else: i+=1
    ax.plot([q[0] for q in pts],[q[1] for q in pts],color=c,lw=lw)
for r in rows:
    if r[0]=='POLY' and r[4]==11: path(r[6],'black',1.6)
    if r[0]=='POLY' and r[4]==13: path(r[6],'tab:blue',0.9)
attrs={}
for r in rows:
    if r[0]=='ATTR': attrs.setdefault(r[3],{})[r[7]]=r[8]
ax.set_aspect('equal');ax.grid(True,lw=.3);ax.set_xlim(-95,115);ax.set_ylim(-40,98)
ax.set_xticks(range(-90,115,10));ax.set_yticks(range(-40,100,10));ax.tick_params(labelsize=7)
ax.annotate('eixo das rodas\ny = −22,6',xy=(0,-22.6),xytext=(-88,-36),fontsize=8,arrowprops=dict(arrowstyle='->',lw=.6))
ax.annotate('linha dos sensores\ny = 77,4  →  L = 100,0 mm',xy=(0,77.4),xytext=(-90,90),fontsize=8,arrowprops=dict(arrowstyle='->',lw=.6))
ax.annotate('linha da pista (19 mm)',xy=(9.5,50),xytext=(14,52),fontsize=8,arrowprops=dict(arrowstyle='->',lw=.6))
ax.annotate('marca de 19 × 40 mm:\n49,5 a 89,5 mm do centro da linha',xy=(70,40),xytext=(52,84),fontsize=8,arrowprops=dict(arrowstyle='->',lw=.6))
ax.annotate('abertura da aba do sensor lateral\n(y = 2…7; QRE montado em ≈ ±69,5; 4,5)',xy=(50,4.5),xytext=(58,-14),fontsize=8,arrowprops=dict(arrowstyle='->',lw=.6))
ax.set_title('EVA_RT_PCB (EVA_RT.eprj): contorno (preto) e camada Document (azul), em mm\nEVA-RT © EXOTIC TEAM MX, AGPL-3.0',fontsize=10)
ax.set_xlabel('x (mm), origem no centro da ventoinha');ax.set_ylabel('y (mm), frente para cima')
fig.tight_layout();OUT.parent.mkdir(parents=True,exist_ok=True);fig.savefig(OUT,dpi=110);print(OUT)
