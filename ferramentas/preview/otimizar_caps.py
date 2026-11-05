"""Busca posicoes para capacitores dos DRV sem bloquear saidas de pinos vizinhos.

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
import math
import numpy as np
from shapely.geometry import LineString, box
from shapely.ops import unary_union

import layout_placa as M

P=M.load_positions()
COMPS={c['ref']:c for c in P}
CAPS={'C6','C13','C14','C7','C15','C16'}
base=[c for c in P if c['ref'] not in CAPS and not c['dnp']]
pads=M.all_pads(base)
bodies=[M.body(c) for c in base if c['face']=='TOP' and M.body(c) is not None]
board=M.BOARD.buffer(-.2)
refpads={(p['ref'],p['pin']):p for p in pads}

def corridors(driver):
    c=COMPS[driver];res=[]
    for p in M.get_pads(c):
        if p['pin']=='17' or not p['net']:continue
        raw=next(k for k in M.F.FOOTPRINTS[c['footprint']]['pads'] if k['pino']==p['pin'])
        dx,dy=math.copysign(1,raw['x']),0
        a=math.radians(c['rot']);dx,dy=dx*math.cos(a)-dy*math.sin(a),dx*math.sin(a)+dy*math.cos(a)
        line=LineString([(p['x'],p['y']),(p['x']+1.4*dx,p['y']+1.4*dy)])
        res.append((p['net'],line.buffer(.35)))
    return res

def search(ref,driver,targets):
    global pads,bodies
    c=COMPS[ref];cx=COMPS[driver]['x'];cy=COMPS[driver]['y']
    blockers={net:unary_union([p['shape'] for p in pads if 1 in p['layers'] and p['net']!=net])
              for net in set(M.PIN_NET.get((ref,str(i))) for i in (1,2))}
    bodyblock=unary_union(bodies).buffer(.05)
    corrs=corridors(driver)
    best=[]
    # Janela cobre as duas extremidades e a lateral da fileira de pinos.
    for rot in (0,90,180,270):
        for x in np.arange(cx-6,cx+6.01,.35):
            for y in np.arange(cy-8,cy+8.01,.35):
                k={**c,'x':float(x),'y':float(y),'rot':rot,'face':'TOP'}
                body=M.body(k)
                if body.intersects(bodyblock):continue
                ps=M.get_pads(k)
                if any(not board.covers(p['shape']) or p['shape'].distance(blockers[p['net']])<.2-1e-6 for p in ps):continue
                if any(p['net']!=net and p['shape'].intersects(corr) for p in ps for net,corr in corrs):continue
                dist=0
                for pin,otherpin,weight in targets:
                    q=next(p for p in ps if p['pin']==str(pin))
                    dist+=q['shape'].distance(refpads[(driver,str(otherpin))]['shape'])*weight
                # Preferir uma solucao compacta, especialmente para CPH/CPL e VM/VCP.
                dist+=.02*math.hypot(x-cx,y-cy)
                best.append((dist,round(float(x),3),round(float(y),3),rot,k))
    if not best:
        print(ref,'SEM CANDIDATO');return
    best.sort(key=lambda x:x[0]);score,x,y,rot,k=best[0]
    print(ref,driver,'->',x,y,rot,'custo',round(score,2),'alternativas',len(best))
    bodies.append(M.body(k));pads.extend(M.get_pads(k))

for args in [
    ('C14','U2',[(1,13,1),(2,14,1)]),
    ('C13','U2',[(1,11,1),(2,12,1)]),
    ('C6','U2',[(1,11,1),(2,9,.3)]),
    ('C16','U3',[(1,13,1),(2,14,1)]),
    ('C15','U3',[(1,11,1),(2,12,1)]),
    ('C7','U3',[(1,11,1),(2,9,.3)]),
]:search(*args)
