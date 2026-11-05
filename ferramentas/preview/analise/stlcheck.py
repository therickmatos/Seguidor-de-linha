import numpy as np, collections, sys
import os
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","..","..","referencias","eva-rt","3d_models")
dt=np.dtype([("n","<f4",(3,)),("v","<f4",(3,3)),("a","<u2")])

def load(name):
    b=open(f"{D}/{name}.stl","rb").read()
    n=int(np.frombuffer(b[80:84],"<u4")[0])
    T=np.frombuffer(b[84:84+50*n],dtype=dt)
    V=T["v"].astype(np.float64)            # (N,3,3)
    e1=V[:,1]-V[:,0]; e2=V[:,2]-V[:,0]
    cr=np.cross(e1,e2)
    ln=np.linalg.norm(cr,axis=1); ln[ln==0]=1
    N=cr/ln[:,None]                         # recomputed normals (right-hand rule)
    return V,N

def key(p):
    return tuple(np.round(p,4))

def vertical_components(V,N,zmin_span=0.5,nz_max=0.25):
    """Connected components of near-vertical triangles (shared edges)."""
    idx=np.where(np.abs(N[:,2])<nz_max)[0]
    # edge -> triangles
    edge_map=collections.defaultdict(list)
    for t in idx:
        vs=[key(V[t,k]) for k in range(3)]
        for a,b in ((0,1),(1,2),(2,0)):
            e=tuple(sorted((vs[a],vs[b])))
            edge_map[e].append(t)
    parent={t:t for t in idx}
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]]; x=parent[x]
        return x
    for e,ts in edge_map.items():
        for i in range(1,len(ts)):
            ra,rb=find(ts[0]),find(ts[i])
            if ra!=rb: parent[ra]=rb
    comps=collections.defaultdict(list)
    for t in idx: comps[find(t)].append(t)
    return list(comps.values())

def fit_circle(xy):
    x=xy[:,0]; y=xy[:,1]
    A=np.c_[2*x,2*y,np.ones(len(x))]
    b=x*x+y*y
    sol,*_=np.linalg.lstsq(A,b,rcond=None)
    cx,cy=sol[0],sol[1]
    r=np.sqrt(max(sol[2]+cx*cx+cy*cy,0))
    res=np.abs(np.hypot(x-cx,y-cy)-r)
    return cx,cy,r,res.max()

def describe_components(V,N,min_tris=8):
    out=[]
    for comp in vertical_components(V,N):
        if len(comp)<min_tris: continue
        pts=V[comp].reshape(-1,3)
        xy=np.unique(np.round(pts[:,:2],4),axis=0)
        if len(xy)<6: continue
        cx,cy,r,err=fit_circle(xy)
        # normal direction test: do wall normals point toward axis?
        nxy=N[comp][:,:2]; cen=np.array([cx,cy])
        mid=V[comp].mean(axis=1)[:,:2]
        toward=np.sum(nxy*(cen-mid),axis=1)
        frac_in=float(np.mean(toward>0))
        ang=np.arctan2(xy[:,1]-cy,xy[:,0]-cx)
        cover=np.degrees(np.ptp(np.unwrap(np.sort(ang))))
        # max angular gap
        s=np.sort(ang); gaps=np.diff(np.r_[s,s[0]+2*np.pi]); maxgap=np.degrees(gaps.max())
        out.append(dict(n=len(comp),cx=cx,cy=cy,r=r,err=err,frac_in=frac_in,
                        zmin=pts[:,2].min(),zmax=pts[:,2].max(),maxgap=maxgap,nxy=len(xy)))
    return out

if __name__=="__main__":
    name=sys.argv[1]
    V,N=load(name)
    rows=describe_components(V,N)
    rows=[r for r in rows if r["err"]<0.05 and r["maxgap"]<120]
    rows.sort(key=lambda r:(round(r["r"],2),r["cx"],r["cy"]))
    print(f"== {name}: circular vertical walls (err<0.05, gap<120deg)")
    for r in rows:
        kind="FURO(normais p/ dentro)" if r["frac_in"]>0.5 else "PINO(normais p/ fora)"
        print(f"  c=({r['cx']:8.3f},{r['cy']:8.3f}) r={r['r']:6.3f} d={2*r['r']:6.3f} z=[{r['zmin']:.2f},{r['zmax']:.2f}] n={r['n']} err={r['err']:.4f} gap={r['maxgap']:.0f} in={r['frac_in']:.2f} {kind}")
