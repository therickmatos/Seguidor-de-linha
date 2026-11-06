"""Modelo Specctra historico, anterior a decisao de retirar o J3 PTH.

O conector J3 deste teste precisa ser alterado antes do proximo roteamento;
consulte docs/HANDOFF_2026-11-06.md. Todos os pads de cada componente foram
agrupados no mesmo footprint.

Avalia a proposta sem substituir a placa anterior. Os arquivos sao um modelo de
preview, nao um projeto EasyEDA nativo. Baseado no EVA-RT, AGPL-3.0.
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

import layout_placa as M
import proposta_organizacao as P
import trilhas_eva as T
from freerouting_io import fmt, sexp, child

DIR=M.HERE/'analise_organizacao'
DIR.mkdir(exist_ok=True)
VIA='VIA_080_040'


def prepare(which):
    old,new=P.candidate()
    pos=new if which=='proposta' else old
    pads=M.all_pads(pos)
    nets=sorted({p['net'] for p in pads if p['net']})
    ids={name:f'N{i:03d}' for i,name in enumerate(nets,1)}
    by_ref=collections.defaultdict(list);pins=collections.defaultdict(list)
    for p in pads:
        by_ref[p['ref']].append(p)
        nid=ids[p['net']] if p['net'] else f'NC_{p["ref"]}_{p["pin"]}'
        pins[nid].append(p['ref']+'-'+p['pin'])
    placements=[];images=[];stacks=[]
    for c in pos:
        ref=c['ref']
        if ref not in by_ref:continue
        placements.append(f'    (component IMG_{ref} (place {ref} {fmt(c["x"])} {fmt(c["y"])} front 0))')
        image_pins=[]
        for p in by_ref[ref]:
            stack=f'PAD_{ref}_{p["pin"]}'
            coords=list(p['shape'].exterior.coords)[:-1]
            xy=' '.join(f'{fmt(x-p["x"])} {fmt(y-p["y"])}' for x,y in coords)
            shapes=' '.join(f'(shape (polygon {"F" if layer==1 else "B"} 0 {xy}))' for layer in p['layers'])
            stacks.append(f'    (padstack {stack} {shapes} (attach off))')
            image_pins.append(f'(pin {stack} {p["pin"]} {fmt(p["x"]-c["x"])} {fmt(p["y"]-c["y"])})')
        images.append(f'    (image IMG_{ref} {" ".join(image_pins)})')
    outline=' '.join(f'{fmt(x)} {fmt(y)}' for x,y in M.OUTLINE.exterior.coords)
    keep=[]
    for h in M.BOARD_DATA['furos']:
        for layer in ('F','B'):
            if h['tipo']=='furo':
                shape=f'(circle {layer} {fmt(h["d"])} {fmt(h["x"])} {fmt(h["y"])})'
            else:
                x0,y0,x1,y1=M.hole_shape(h).bounds
                shape=f'(rect {layer} {fmt(x0)} {fmt(y0)} {fmt(x1)} {fmt(y1)})'
            keep.append(f'    (keepout {shape})')
    lines=['(pcb seguidor_grupos',
           '  (parser (string_quote ") (space_in_quoted_tokens on) (host_cad "preview") (host_version "2"))',
           '  (resolution mm 1000000)','  (structure','    (layer F (type signal))',
           '    (layer B (type signal))',f'    (boundary (path pcb 0 {outline}))',*keep,
           f'    (via {VIA})','    (rule (width 0.30) (clearance 0.20))','  )',
           '  (placement',*placements,'  )','  (library',*images,*stacks,
           f'    (padstack {VIA} (shape (circle F 0.8)) (shape (circle B 0.8)) (attach off))',
           '  )','  (network']
    for nid,terms in pins.items():lines.append(f'    (net {nid} (pins {" ".join(terms)}))')
    for net in nets:
        power=net=='VBAT' or net.startswith('OUT_')
        width=.8 if power else .5 if net=='GND' else .4 if net=='+5V' else .3
        nid=ids[net]
        lines.append(f'    (class C_{nid} {nid} (circuit (use_via {VIA})) '
                     f'(rule (width {fmt(width)}) (clearance 0.20)))')
    for nid in sorted(x for x in pins if x.startswith('NC_')):
        lines.append(f'    (class C_{nid} {nid} (circuit (use_via {VIA})) (rule (width 0.30)))')
    lines += ['  )','  (wiring)',')','']
    (DIR/f'{which}.dsn').write_text('\n'.join(lines),encoding='utf8')
    (DIR/f'{which}_mapa.json').write_text(json.dumps({'net_ids':{v:k for k,v in ids.items()},
        'componentes':len(by_ref),'pads':len(pads)},ensure_ascii=False,indent=1),encoding='utf8')
    air,summary=T.connectivity(pos,[],[])
    print(which,len(by_ref),'componentes reais,',len(pads),'pads,',len(air),'conexoes iniciais',flush=True)


def read_result(which,continuacao=False):
    old,new=P.candidate();pos=new if which=='proposta' else old
    mapping=json.loads((DIR/f'{which}_mapa.json').read_text(encoding='utf8'))['net_ids']
    stem=f'{which}_continuacao' if continuacao else which
    ses=sexp((DIR/f'{stem}.ses').read_text(encoding='utf8'))
    routes=child(ses,'routes');resolution=child(routes,'resolution')
    if not resolution:raise ValueError('resolucao ausente')
    factor={'mm':1.0,'um':.001,'mil':.0254,'inch':25.4}[resolution[1]]/float(resolution[2])
    network=child(routes,'network_out')
    if network is None:raise ValueError('rede ausente')
    tracks=[];vias=[]
    for net in network[1:]:
        if not isinstance(net,list) or not net or net[0]!='net':continue
        name=mapping.get(net[1])
        if name is None:
            if net[1].startswith('NC_'):continue
            raise ValueError('rede desconhecida '+str(net[1]))
        for item in net[2:]:
            if not isinstance(item,list) or not item:continue
            if item[0]=='wire':
                path=child(item,'path')
                if not path:raise ValueError('fio sem path')
                values=[float(x)*factor for x in path[3:]]
                if len(values)<4 or len(values)%2:raise ValueError('fio invalido')
                tracks.append({'id':f'FRG-{len(tracks)+1}','net':name,'layer':{'F':1,'B':2}[path[1]],
                               'width':float(path[2])*factor,
                               'xy':[[values[i],values[i+1]] for i in range(0,len(values),2)],'status':'nova'})
            elif item[0]=='via':
                if item[1]!=VIA:raise ValueError('via desconhecida')
                vias.append({'id':f'FRGV-{len(vias)+1}','net':name,
                             'xy':[float(item[2])*factor,float(item[3])*factor],
                             'diameter':.8,'drill':.4,'status':'nova'})
    if not tracks:raise ValueError('nenhuma trilha')
    air,summary=T.connectivity(pos,tracks,vias)
    data={'tracks':tracks,'vias':vias,'ratsnest':air,'redes':summary,'proposta':which,
          'componentes_agrupados':True,'autorouter':'FreeRouting 2.5.0'}
    (DIR/f'{stem}_trilhas.json').write_text(json.dumps(data,ensure_ascii=False,indent=1),encoding='utf8')
    print(stem,len(tracks),'trilhas,',len(vias),'vias,',len(air),'ligacoes abertas:',
          dict(collections.Counter(e['net'] for e in air)),flush=True)


def continue_dsn(which):
    data=json.loads((DIR/f'{which}_trilhas.json').read_text(encoding='utf8'))
    mapping=json.loads((DIR/f'{which}_mapa.json').read_text(encoding='utf8'))['net_ids']
    inverse={name:nid for nid,name in mapping.items()}
    wires=[]
    for t in data['tracks']:
        xy=' '.join(f'{fmt(x)} {fmt(y)}' for x,y in t['xy'])
        layer='F' if t['layer']==1 else 'B'
        wires.append(f'    (wire (path {layer} {fmt(t["width"])} {xy}) (net {inverse[t["net"]]}))')
    for v in data['vias']:
        x,y=v['xy']
        wires.append(f'    (via {VIA} {fmt(x)} {fmt(y)} (net {inverse[v["net"]]}))')
    source=(DIR/f'{which}.dsn').read_text(encoding='utf8')
    if source.count('  (wiring)')!=1:raise ValueError('wiring inesperado')
    (DIR/f'{which}_continuacao.dsn').write_text(
        source.replace('  (wiring)','  (wiring\n'+'\n'.join(wires)+'\n  )'),encoding='utf8')
    print(which,'continuacao:',len(wires),'elementos',flush=True)


if __name__=='__main__':
    if len(sys.argv) not in (3,4) or sys.argv[1] not in ('prepare','import','continue') or sys.argv[2] not in ('atual','proposta'):
        raise SystemExit('Uso: python rotear_agrupado.py prepare|import|continue atual|proposta [continuacao]')
    if sys.argv[1]=='prepare':prepare(sys.argv[2])
    elif sys.argv[1]=='continue':continue_dsn(sys.argv[2])
    else:read_result(sys.argv[2],len(sys.argv)==4 and sys.argv[3]=='continuacao')
