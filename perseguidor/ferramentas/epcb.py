import json,math,glob,collections
from shapely.geometry import Polygon,LineString,Point
from shapely.ops import polygonize,unary_union
MIL=0.0254
def load(d):
    f=glob.glob(d+'/PCB/*.epcb')[0]
    lines=open(f,encoding='utf-8').read().split('\n')
    rows=[]
    for l in lines:
        if not l.strip(): rows.append(None); continue
        rows.append(json.loads(l))
    return f,lines,rows
def arcpts(x0,y0,ang,x1,y1,n=16):
    # arc from p0 to p1 sweeping ang degrees
    a=math.radians(ang)
    if abs(a)<1e-9: return [(x0,y0),(x1,y1)]
    dx,dy=x1-x0,y1-y0; c=math.hypot(dx,dy); r=c/2/math.sin(abs(a)/2)
    mx,my=(x0+x1)/2,(y0+y1)/2; h=math.sqrt(max(r*r-(c/2)**2,0))
    # center to the left or right depending on sign
    nx,ny=-dy/c,dx/c
    s=1 if a>0 else -1
    cx,cy=mx+s*nx*h*(1 if abs(a)<=math.pi else -1),my+s*ny*h*(1 if abs(a)<=math.pi else -1)
    t0=math.atan2(y0-cy,x0-cx)
    return [(cx+r*math.cos(t0+a*i/n),cy+r*math.sin(t0+a*i/n)) for i in range(n+1)]
def pathpts(p):
    pts=[];i=0
    x,y=p[0],p[1];pts.append((x,y));i=2
    mode=None
    while i<len(p):
        if isinstance(p[i],str): mode=p[i];i+=1;continue
        if mode=='L': x,y=p[i],p[i+1];pts.append((x,y));i+=2
        elif mode=='ARC':
            ang,x1,y1=p[i],p[i+1],p[i+2]; pts+=arcpts(x,y,ang,x1,y1)[1:-1]+[(x1,y1)]; x,y=x1,y1;i+=3
        else: raise ValueError(p)
    return pts
def outline(rows):
    segs=[]
    for r in rows:
        if r and r[0]=='POLY' and r[4]==11:
            segs.append(LineString([(round(a,1),round(b,1)) for a,b in pathpts(r[6])]))
    polys=list(polygonize(unary_union(segs)))
    polys.sort(key=lambda p:-p.area)
    return polys

def fp_pads(d,uuid):
    out=[]
    for l in open(f"{d}/FOOTPRINT/{uuid}.efoo",encoding='utf-8'):
        try:r=json.loads(l)
        except:continue
        if r[0]=='PAD': out.append(r)
    return out
def comp_pads(d,rows,mirror_sign=1,rot_sign=1):
    """returns list of (compid, padnum, x, y, layer, w, h, rot) in board mils"""
    comp={};fp={}
    for r in rows:
        if r and r[0]=='COMPONENT': comp[r[1]]=r
        if r and r[0]=='ATTR' and r[7]=='Footprint' and r[8]: fp[r[3]]=r[8]
    res=[]
    for cid,c in comp.items():
        if cid not in fp: continue
        try: pads=fp_pads(d,fp[cid])
        except FileNotFoundError: continue
        L,cx,cy,rot=c[3],c[4],c[5],c[6]
        for p in pads:
            px,py=p[6],p[7]
            if L==2: py=-py
            a=math.radians(rot)
            x=cx+px*math.cos(a)-py*math.sin(a); y=cy+px*math.sin(a)+py*math.cos(a)
            sh=p[10]
            w=h=20
            if sh and sh[0] in('RECT','OVAL','ELLIPSE'): w,h=sh[1],sh[2]
            elif sh and sh[0]=='POLY': w=h=40
            pl=12 if p[4]==12 else ((3-p[4]) if L==2 and p[4] in (1,2) else p[4])
            res.append((cid,p[5],x,y,pl,w,h))
    return res
