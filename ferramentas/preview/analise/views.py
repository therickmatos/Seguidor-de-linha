import sys, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from stlcheck import load
names=sys.argv[1:]
fig,axes=plt.subplots(len(names),3,figsize=(15,4.6*len(names)))
if len(names)==1: axes=np.array([axes])
for row,name in zip(axes,names):
    V,N=load(name)
    for ax,(a,b,lab) in zip(row,[(0,1,"XY (topo)"),(0,2,"XZ (frente)"),(1,2,"YZ (lado)")]):
        # draw faces coloured by normal z
        polys=V[:,:,[a,b]]
        shade=np.clip(0.5+0.5*N[:,2],0,1) if (a,b)==(0,1) else np.clip(0.5+0.5*np.abs(N[:,2]),0,1)
        pc=PolyCollection(polys,facecolors=plt.cm.viridis(shade*0.9),edgecolors="none",alpha=0.85)
        ax.add_collection(pc)
        mn=V.reshape(-1,3).min(0); mx=V.reshape(-1,3).max(0)
        ax.set_xlim(mn[a]-2,mx[a]+2); ax.set_ylim(mn[b]-2,mx[b]+2)
        ax.set_aspect("equal"); ax.grid(True,alpha=.3); ax.set_title(f"{name} - {lab}",fontsize=9)
        ax.axhline(0,color="r",lw=.6); ax.axvline(0,color="r",lw=.6)
plt.tight_layout()
out=__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), f"views_{'_'.join(names)}.png")
plt.savefig(out,dpi=70)
print(out)
