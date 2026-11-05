"""Roteador de preview em duas camadas, conservador e com verificacao geometrica.

Nao substitui DRC nem verificacao de corrente. Linhas sem solucao permanecem no ratsnest.
Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations
import collections
import heapq
import json
import math
import sys
import time

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt
from shapely import intersects_xy
from shapely.geometry import Point, LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree

import layout_placa as M
import trilhas_eva as T

FINO='--fino' in sys.argv
RESERVAR='--reservar' in sys.argv
SAIDA='trilhas_reservadas.json' if '--saida-reservada' in sys.argv else 'trilhas_roteadas.json'
STEP=.1 if FINO else .2
X0,Y0=-75.0,-33.0
NX,NY=int(round(150/STEP))+1,int(round(60/STEP))+1
CLEAR=.2
SIGNAL=.30
VIA_D=.80
VIA_DRILL=.40

def pointxy(x,y):return ((x-X0)/STEP,(y-Y0)/STEP)
def world(ix,iy):return (X0+ix*STEP,Y0+iy*STEP)

def raster(g,drawer,fill):
    if g.is_empty:return
    if g.geom_type=='Polygon':
        drawer.polygon([pointxy(x,y) for x,y in g.exterior.coords],fill=fill)
        for interior in g.interiors:
            drawer.polygon([pointxy(x,y) for x,y in interior.coords],fill=0)
    elif hasattr(g,'geoms'):
        for part in g.geoms:raster(part,drawer,fill)

def board_mask():
    img=Image.new('L',(NX,NY),0);draw=ImageDraw.Draw(img)
    raster(M.OUTLINE,draw,255)
    for _,hole in M.HOLES:raster(hole,draw,0)
    return np.asarray(img)>0

def geom_tracks(t):
    return LineString(t['xy']).buffer(t['width']/2,quad_segs=8)
def geom_via(v):return Point(v['xy']).buffer(v['diameter']/2,quad_segs=8)

def groups_for(net,positions,tracks,vias):
    nodes=[]
    for p in M.all_pads(positions):
        if p['net']==net:
            nodes.append({'g':p['shape'],'layers':set(p['layers']), 'pad':f"{p['ref']}.{p['pin']}"})
    for t in tracks:
        if t['net']==net and t['status'] in ('mantida','ajustada','nova'):
            nodes.append({'g':geom_tracks(t),'layers':{t['layer']},'pad':None})
    for v in vias:
        if v['net']==net and v['status'] in ('mantida','nova'):
            nodes.append({'g':geom_via(v),'layers':{1,2},'pad':None})
    if not nodes:return []
    parent=list(range(len(nodes)))
    def find(a):
        while parent[a]!=a:
            parent[a]=parent[parent[a]];a=parent[a]
        return a
    tree=STRtree([n['g'] for n in nodes])
    for i,n in enumerate(nodes):
        for j0 in tree.query(n['g'].buffer(.002)):
            j=int(j0)
            if j<=i or not n['layers'].intersection(nodes[j]['layers']):continue
            if n['g'].distance(nodes[j]['g'])<.002:
                a,b=find(i),find(j)
                if a!=b:parent[b]=a
    grouped=collections.defaultdict(list)
    for i,n in enumerate(nodes):grouped[find(i)].append(n)
    result=[]
    for group in grouped.values():
        pins=sorted(n['pad'] for n in group if n['pad'])
        if not pins:continue
        layers={layer:unary_union([n['g'] for n in group if layer in n['layers']]) for layer in (1,2)}
        result.append({'pins':pins,'layers':layers,'geom':unary_union([n['g'] for n in group])})
    return result

class Router:
    def __init__(self,positions,data):
        self.positions=positions;self.data=data
        self.tracks=data['tracks'];self.vias=data['vias']
        nets={p['net'] for p in M.all_pads(positions) if p['net']}
        nets.update(t['net'] for t in self.tracks if t['net'])
        self.ids={net:i+1 for i,net in enumerate(sorted(nets))}
        self.no_net=max(self.ids.values(),default=0)+1
        self.images={layer:Image.new('I',(NX,NY),0) for layer in (1,2)}
        self.drawers={layer:ImageDraw.Draw(self.images[layer]) for layer in (1,2)}
        self.objects={1:[],2:[]}
        self.reservas=T.driver_escapes(positions) if RESERVAR else []
        self.reserva_cache={}
        for p in M.all_pads(positions):
            for layer in p['layers']:self.add_shape(layer,p['net'],p['shape'])
        for t in self.tracks:
            if t['status'] in ('mantida','ajustada','nova'):
                self.add_shape(t['layer'],t['net'],geom_tracks(t))
        for v in self.vias:
            if v['status'] in ('mantida','nova'):
                for layer in (1,2):self.add_shape(layer,v['net'],geom_via(v))
        self.board=board_mask()
        self.board_distance=distance_transform_edt(self.board)*STEP
        self.valid_board=M.BOARD.buffer(-CLEAR)
        self.failed=set()
        self.blocked=set()
        self.escaped=set()
        self.sequence=0
    def add_shape(self,layer,net,g):
        raster(g,self.drawers[layer],self.ids.get(net,self.no_net))
        self.objects[layer].append((net,g))
    def masks(self,net):
        allowed=[]; via=[]
        reservation_distance=None
        if self.reservas:
            if net not in self.reserva_cache:
                shape=unary_union([g for n,g in self.reservas if n!=net])
                im=Image.new('L',(NX,NY),0);raster(shape,ImageDraw.Draw(im),255)
                self.reserva_cache[net]=(shape,distance_transform_edt(np.asarray(im)==0)*STEP)
            reservation_distance=self.reserva_cache[net][1]
        for layer in (1,2):
            arr=np.asarray(self.images[layer]);obs=(arr!=0)&(arr!=self.ids[net])
            dist=distance_transform_edt(~obs)*STEP
            extra=.045 if FINO else .13
            allowed.append((dist>=SIGNAL/2+CLEAR+extra)&(self.board_distance>=SIGNAL/2+CLEAR+extra))
            via.append((dist>=VIA_D/2+CLEAR+extra)&(self.board_distance>=VIA_D/2+CLEAR+extra))
            if layer==1 and reservation_distance is not None:
                allowed[-1] &= reservation_distance>=SIGNAL/2+STEP*.3
                via[-1] &= reservation_distance>=VIA_D/2+STEP*.3
        return np.asarray(allowed),via[0]&via[1]
    def mask_group(self,group,allowed):
        masks=[]
        for idx,layer in enumerate((1,2)):
            im=Image.new('L',(NX,NY),0); raster(group['layers'][layer],ImageDraw.Draw(im),255)
            preliminary=(np.asarray(im)>0)&allowed[idx]
            yy,xx=np.nonzero(preliminary)
            exact=np.zeros((NY,NX),dtype=bool)
            if len(xx):
                hit=intersects_xy(group['layers'][layer],X0+xx*STEP,Y0+yy*STEP)
                exact[yy[hit],xx[hit]]=True
            masks.append(exact)
        return np.asarray(masks)
    def exact_clear(self,net,layer,g):
        if not self.valid_board.covers(g):return False
        if layer==1 and self.reservas:
            shape=unary_union([corridor for oldnet,corridor in self.reservas if oldnet!=net])
            if g.intersects(shape):return False
        for other,shape in self.objects[layer]:
            if other==net and net is not None:continue
            if g.distance(shape)<CLEAR-1e-5:return False
        return True
    def search(self,a,b,net):
        allowed,via=self.masks(net)
        source=self.mask_group(a,allowed); target=self.mask_group(b,allowed)
        src=np.argwhere(source); dst=np.argwhere(target)
        if not len(src):return None,'origem sem saida na grade'
        if not len(dst):return None,'destino sem saida na grade'
        # Pontos da ilha de origem mais proximos da ilha de destino.
        from shapely.ops import nearest_points
        p,q=nearest_points(a['geom'],b['geom']); qx,qy=pointxy(q.x,q.y); px,py=pointxy(p.x,p.y)
        scores=(src[:,1]-py)**2+(src[:,2]-px)**2
        src=src[np.argsort(scores)[:min(45,len(src))]]
        # Janela progressiva evita explorar a placa inteira para ligacoes curtas.
        for margin in (8,18,80):
            xmin=max(0,int(min(px,qx)-margin/STEP));xmax=min(NX-1,int(max(px,qx)+margin/STEP))
            ymin=max(0,int(min(py,qy)-margin/STEP));ymax=min(NY-1,int(max(py,qy)+margin/STEP))
            heap=[]; costs={}; prev={}
            def heur(x,y):return math.hypot(x-qx,y-qy)*.9
            for z,y,x in src:
                z,y,x=int(z),int(y),int(x)
                if xmin<=x<=xmax and ymin<=y<=ymax:
                    key=(z,y,x);costs[key]=0;heapq.heappush(heap,(heur(x,y),0,key))
            found=None;expanded=0
            max_expand=45000 if margin<80 else 110000
            while heap and expanded<max_expand:
                _,cost,key=heapq.heappop(heap)
                if cost!=costs.get(key):continue
                z,y,x=key;expanded+=1
                if target[z,y,x]:found=key;break
                for dx,dy,dc in ((1,0,1),(-1,0,1),(0,1,1),(0,-1,1),
                                 (1,1,1.414),(-1,1,1.414),(1,-1,1.414),(-1,-1,1.414)):
                    xx,yy=x+dx,y+dy
                    if xx<xmin or xx>xmax or yy<ymin or yy>ymax or not allowed[z,yy,xx]:continue
                    if dx and dy and (not allowed[z,y,xx] or not allowed[z,yy,x]):continue
                    k=(z,yy,xx);nc=cost+dc
                    if nc<costs.get(k,1e30):
                        costs[k]=nc;prev[k]=key;heapq.heappush(heap,(nc+heur(xx,yy),nc,k))
                if via[y,x] and allowed[1-z,y,x]:
                    k=(1-z,y,x);nc=cost+12
                    if nc<costs.get(k,1e30):
                        costs[k]=nc;prev[k]=key;heapq.heappush(heap,(nc+heur(x,y),nc,k))
            if found:
                path=[]
                while True:
                    path.append(found)
                    if found not in prev:break
                    found=prev[found]
                path.reverse()
                return path,''
        return None,'sem caminho com folga na busca'
    def escape_group(self,group):
        """Abre um pequeno trecho verificado na saida de pads finos dos CIs."""
        comps={c['ref']:c for c in self.positions}
        bypin={(p['ref'],p['pin']):p for p in M.all_pads(self.positions)}
        for name in group['pins']:
            if name in self.escaped:continue
            self.escaped.add(name)
            ref,pin=name.split('.')
            if ref not in ('U1','U2','U3') or pin=='17' and ref!='U1':continue
            c=comps[ref];pad=bypin[(ref,pin)]
            raw=next(p for p in M.F.FOOTPRINTS[c['footprint']]['pads'] if p['pino']==pin)
            lx,ly=raw['x'],raw['y']
            if abs(lx)>abs(ly):dx,dy=math.copysign(1,lx),0
            else:dx,dy=0,math.copysign(1,ly)
            angle=math.radians(c['rot'])
            dx,dy=dx*math.cos(angle)-dy*math.sin(angle),dx*math.sin(angle)+dy*math.cos(angle)
            for length in (1.8,1.3,.9):
                line=LineString([(pad['x'],pad['y']),(pad['x']+dx*length,pad['y']+dy*length)])
                copper=line.buffer(SIGNAL/2,quad_segs=8)
                if not self.exact_clear(pad['net'],1,copper):continue
                own=unary_union([g for net,g in self.objects[1] if net==pad['net']])
                if line.difference(own).length<.08:continue
                self.sequence+=1
                t={'id':f'escape_{self.sequence}','old_net':None,'net':pad['net'],'layer':1,
                   'width':SIGNAL,'xy':[list(xy) for xy in line.coords], 'type':'LINE',
                   'status':'nova','motivo':'escape de pad fino, verificado geometricamente'}
                self.tracks.append(t);self.add_shape(1,pad['net'],copper)
                return True
        return False
    def propose(self,path,net,a,b):
        """Confere vetorialmente todo o trajeto antes de aceita-lo."""
        runs=[];newvias=[];run=[];lastz=None
        for z,y,x in path:
            pt=world(x,y)
            if lastz is None:run=[pt];lastz=z;continue
            if z!=lastz:
                if len(run)>1:runs.append((lastz+1,run))
                newvias.append(pt);run=[pt];lastz=z
            elif pt!=run[-1]:run.append(pt)
        if len(run)>1:runs.append((lastz+1,run))
        lines=[]
        for layer,pts in runs:
            line=LineString(pts).simplify(0.01,preserve_topology=False)
            g=line.buffer(SIGNAL/2,quad_segs=8)
            if not self.exact_clear(net,layer,g):return False,'checagem vetorial de trilha'
            lines.append((layer,list(line.coords)))
        for pt in newvias:
            g=Point(pt).buffer(VIA_D/2,quad_segs=12)
            if not all(self.exact_clear(net,l,g) for l in (1,2)):
                return False,'checagem vetorial de via'
        # A rasterizacao pode incluir ponto fora da ilha: verificar encosto real.
        if not lines and not newvias:return False,'trajeto vazio'
        start=Point(world(path[0][2],path[0][1]))
        end=Point(world(path[-1][2],path[-1][1]))
        if start.distance(a['layers'][path[0][0]+1])>SIGNAL/2-.001:
            return False,'origem nao encosta no cobre'
        if end.distance(b['layers'][path[-1][0]+1])>SIGNAL/2-.001:
            return False,'destino nao encosta no cobre'
        self.sequence+=1
        for layer,pts in lines:
            # A largura minima respeita o estilo das trilhas finas de 0,30 mm do EVA-RT.
            t={'id':f'nova_{self.sequence}_{len(self.tracks)}','old_net':None,'net':net,
               'layer':layer,'width':SIGNAL,'xy':[list(pt) for pt in pts],
               'type':'LINE','status':'nova','motivo':'conexao nova; largura de escape 0,30 mm'}
            self.tracks.append(t);self.add_shape(layer,net,geom_tracks(t))
        for x,y in newvias:
            v={'id':f'via_nova_{self.sequence}_{len(self.vias)}','old_net':None,'net':net,
               'xy':[x,y],'drill':VIA_DRILL,'diameter':VIA_D,'status':'nova','motivo':'via de 0,8/0,4 mm'}
            self.vias.append(v)
            for layer in (1,2):self.add_shape(layer,net,geom_via(v))
        return True,''

def run():
    positions=M.load_positions()
    input_file='trilhas_roteadas.json' if '--continuar' in sys.argv else 'trilhas_classificadas.json'
    data=json.loads((M.HERE/input_file).read_text(encoding='utf8'))
    earlier=data.get('roteamento')
    router=Router(positions,data)
    attempted=0;success=0;reasons=collections.Counter();started=time.time()
    # Cada rodada reavalia a conectividade real; tenta primeiro ligacoes locais.
    numeric=[x for x in sys.argv[1:] if x.isdigit()]
    max_attempts=int(numeric[0]) if numeric else 220
    while attempted<max_attempts:
        edges,summary=T.connectivity(positions,router.tracks,router.vias)
        options=[]
        for e in edges:
            key=(e['net'],tuple(sorted(e['from'])),tuple(sorted(e['to'])))
            rev=(e['net'],key[2],key[1])
            if key in router.failed or rev in router.failed or key[1] in router.blocked or key[2] in router.blocked:continue
            options.append((e['distance'],key,e))
        if not options:break
        options.sort(key=lambda a:a[0])
        _,key,e=options[0]
        groups=groups_for(e['net'],positions,router.tracks,router.vias)
        af=set(e['from']);bf=set(e['to'])
        a=next((g for g in groups if set(g['pins'])==af),None)
        b=next((g for g in groups if set(g['pins'])==bf),None)
        if not a or not b:
            router.failed.add(key);continue
        attempted+=1
        path,why=router.search(a,b,e['net'])
        if not path and why in ('origem sem saida na grade','destino sem saida na grade'):
            blocked_group=a if why.startswith('origem') else b
            if router.escape_group(blocked_group):
                print('Escape de pad:',e['net'],','.join(blocked_group['pins']),flush=True)
                continue
            router.blocked.add(tuple(blocked_group['pins']))
        if path:
            before=len(edges)
            ok,why=router.propose(path,e['net'],a,b)
            if ok:
                after,_=T.connectivity(positions,router.tracks,router.vias)
                if len(after)>=before:
                    print('AVISO: caminho aceito nao uniu ilhas',e['net'],flush=True)
                else:success+=1
        else:ok=False
        if not ok:
            router.failed.add(key);reasons[why]+=1
            print('PENDENTE',e['net'],','.join(e['from']),'<->',','.join(e['to']),why,flush=True)
        if attempted%5==0:
            print(f'tentativas={attempted} unidas={success} pendentes={len(edges)} tempo={time.time()-started:.0f}s',flush=True)
        if attempted%10==0:
            data['ratsnest'],data['redes']=T.connectivity(positions,router.tracks,router.vias)
            (M.HERE/SAIDA).write_text(json.dumps(data,indent=1,ensure_ascii=False),encoding='utf8')
    data['ratsnest'],data['redes']=T.connectivity(positions,router.tracks,router.vias)
    data['roteamento']={'tentativas':attempted,'conexoes_unidas':success,'motivos_falhas':dict(reasons),
                         'grade_mm':STEP,'rodada_anterior':earlier}
    (M.HERE/SAIDA).write_text(json.dumps(data,indent=1,ensure_ascii=False),encoding='utf8')
    print('FINAL',data['roteamento'],'pendencias',len(data['ratsnest']),flush=True)

if __name__=='__main__':run()
