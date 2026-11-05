import sys, numpy as np, collections
sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from stlcheck import load, key
V,N=load("impeller_base_1")
# contact triangles: all vertices z<=1.0
cont=np.where(np.all(V[:,:,2]<=1.0,axis=1))[0]
print("contact tris (z<=1):", len(cont), "area", round(float(0.5*np.linalg.norm(np.cross(V[cont,1]-V[cont,0],V[cont,2]-V[cont,0]),axis=1).sum()),2))
# connected components by shared vertices (xy-based union-find)
parent={}
def find(a):
    while parent[a]!=a:
        parent[a]=parent[parent[a]]; a=parent[a]
    return a
for t in cont:
    vs=[key(V[t,k]) for k in range(3)]
    for v in vs: parent.setdefault(v,v)
    for v in vs[1:]:
        ra,rb=find(vs[0]),find(v)
        if ra!=rb: parent[ra]=rb
comps=collections.defaultdict(list)
for t in cont:
    comps[find(key(V[t,0]))].append(t)
for c,ts in comps.items():
    P=V[ts].reshape(-1,3)
    A=0.5*np.linalg.norm(np.cross(V[ts,1]-V[ts,0],V[ts,2]-V[ts,0]),axis=1).sum()
    print(f"comp n={len(ts):3d} area={A:6.2f} xy-bbox x[{P[:,0].min():7.3f},{P[:,0].max():7.3f}] y[{P[:,1].min():7.3f},{P[:,1].max():7.3f}] zmax={P[:,2].max():.2f} centroid=({P[:,0].mean():.2f},{P[:,1].mean():.2f})")
# tabs: vertices of housing outside r=22.5 region, z range
R=np.hypot(V[:,:,0],V[:,:,1])
for name,(cx,cy) in {"-x arm end":(-22,0),"-y arm end":(0,-22),"+x arm end":(22,0),"+y arm end":(0,22)}.items():
    m=np.hypot(V[:,:,0]-cx,V[:,:,1]-cy)<4.5
    tri=np.where(np.any(m,axis=1))[0]
    P=V[tri].reshape(-1,3)
    print(f"{name}: tris={len(tri)} x[{P[:,0].min():.2f},{P[:,0].max():.2f}] y[{P[:,1].min():.2f},{P[:,1].max():.2f}] z[{P[:,2].min():.2f},{P[:,2].max():.2f}]")
# tab region: vertices with r>22.5 and z<=6
m=(R>22.6)&(V[:,:,2]<=8)
tri=np.where(np.any(m,axis=(1)))[0]
P=V[tri][m[tri]] if len(tri) else np.zeros((0,3))
for ang in [0,90,180,270]:
    pass
import math
ang=np.degrees(np.arctan2(P[:,1],P[:,0])) % 360
print("outer low vertices (r>22.6,z<=8) angle histogram (deg bins of 15):")
h,_=np.histogram(ang,bins=24,range=(0,360))
print(list(zip(range(0,360,15),h)))
