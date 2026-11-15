import re, sys, numpy as np
from svgpathtools import parse_path
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
s=open('logo_if_completo.svg').read()
paths=re.findall(r'<path [^>]*d="([^"]*)"[^>]*/>',s)
def to_geom(d):
    p=parse_path(d); rings=[]
    for sub in p.continuous_subpaths():
        pts=[]
        for seg in sub:
            n=max(4,int(seg.length()/0.3))
            for t in np.linspace(0,1,n,endpoint=False): z=seg.point(t); pts.append((z.real,z.imag))
        if len(pts)>2: rings.append(Polygon(pts).buffer(0))
    g=None
    for r in sorted(rings,key=lambda r:-r.area): g=r if g is None else g.symmetric_difference(r)
    return g
sym=[];bold=[];reg=[]
for d in paths:
    g=to_geom(d)
    if g is None or g.is_empty: continue
    cy=g.centroid.y
    (sym if cy<110 else bold if cy<158 else reg).append(g)
mm=8.01/149.0
regu=unary_union(reg); boldu=unary_union(bold); symu=unary_union(sym)
ero=lambda g,t: round(100*g.buffer(-t/2/mm).area/g.area)
holes=lambda g: (sum(len(p.interiors) for p in getattr(g,'geoms',[g])), round(min([Polygon(h).area for p in getattr(g,'geoms',[g]) for h in p.interiors])*mm*mm,4))
for Rmm in (0.03,0.04,0.05,0.06):
    g=regu.buffer(Rmm/mm,join_style=1)
    print(f'engrossa {Rmm} mm/lado: erosão 0,15 → {ero(g,0.15)}% | furos {holes(g)} | negrito erosão 0,15 → {ero(boldu,0.15)}%')
if len(sys.argv)>1:
    Rmm=float(sys.argv[1]); reg2=regu.buffer(Rmm/mm,join_style=1)
    line=box(35.164,187.745-0.3,35.164+146.25,187.745+2.7)
    def svgpath(g):
        out=[]
        for p in getattr(g,'geoms',[g]):
            for ring in [p.exterior]+list(p.interiors):
                out.append('M '+' L '.join(f'{x:.3f} {y:.3f}' for x,y in ring.coords)+' Z')
        return ' '.join(out)
    body=''.join(f'<path fill-rule="evenodd" d="{svgpath(g)}"/>' for g in (symu,boldu,reg2,line))
    open('logo_if_completo_8mm.svg','w').write('<svg xmlns="http://www.w3.org/2000/svg" width="149" height="213" viewBox="34 21 149 213"><g fill="#000">'+body+'</g></svg>\n')
    print('gravado com',Rmm)
