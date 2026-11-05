import sys, numpy as np, collections
sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from stlcheck import load
name=sys.argv[1]
V,N=load(name)
hor=np.abs(N[:,2])>0.97
A=0.5*np.linalg.norm(np.cross(V[:,1]-V[:,0],V[:,2]-V[:,0]),axis=1)
rows=collections.defaultdict(lambda:[0.0,0.0,0,0])  # area_up, area_down, n_up, n_down
for t in np.where(hor)[0]:
    z=round(float(V[t,:,2].mean()),2)
    if N[t,2]>0: rows[z][0]+=A[t]; rows[z][2]+=1
    else: rows[z][1]+=A[t]; rows[z][3]+=1
print(f"== {name}: horizontal faces by z (area mm2): up(+z) / down(-z)")
for z in sorted(rows):
    au,ad,nu,nd=rows[z]
    if au+ad<0.5: continue
    print(f"  z={z:7.2f}  up={au:9.2f} ({nu:4d})  down={ad:9.2f} ({nd:4d})")
