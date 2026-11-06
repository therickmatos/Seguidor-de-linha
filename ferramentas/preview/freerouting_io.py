"""Intercambio Specctra para a previa; unidades em mm, origem na ventoinha.

Os pads sao instancias individuais para manter formas e faces ja transformadas.
O arquivo e uma representacao de roteamento, nao um projeto nativo de fabricacao.
Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import collections
import csv
import json
import re
import sys
from pathlib import Path

import layout_placa as M
import trilhas_eva as T

DSN = M.HERE / 'seguidor_freerouting.dsn'
SES = M.HERE / 'seguidor_freerouting.ses'
MAPA = M.HERE / 'freerouting_mapa.json'


def fmt(v):
    return f'{v:.5f}'.rstrip('0').rstrip('.') if abs(v) > 0.000005 else '0'


def prepare():
    positions = M.load_positions()
    M.export_positions(positions)
    pads = M.all_pads(positions)
    real_nets = sorted({p['net'] for p in pads if p['net']})
    net_ids = {net: f'N{i:03d}' for i, net in enumerate(real_nets, 1)}
    pins = collections.defaultdict(list)
    placements, images, padstacks = [], [], []
    mapping = {}
    for i, p in enumerate(pads):
        name, img, stack = f'P{i:03d}', f'I{i:03d}', f'PS{i:03d}'
        net_id = net_ids[p['net']] if p['net'] else f'NC{i:03d}'
        pins[net_id].append(f'{name}-1')
        mapping[name] = {'ref': p['ref'], 'pad': p['pin'], 'net': p['net']}
        placements.append(f'    (component {img} (place {name} {fmt(p["x"])} {fmt(p["y"])} front 0))')
        images.append(f'    (image {img} (pin {stack} 1 0 0))')
        # O contorno do pad esta em coordenadas absolutas e ja inclui rotacao e
        # espelhamento da face inferior; manter a forma exata, nao so a caixa.
        coords = list(p['shape'].exterior.coords)[:-1]
        xy = ' '.join(f'{fmt(x-p["x"])} {fmt(y-p["y"])}' for x, y in coords)
        shapes = ' '.join(f'(shape (polygon {"F" if layer == 1 else "B"} 0 {xy}))'
                          for layer in p['layers'])
        padstacks.append(f'    (padstack {stack} {shapes} (attach off))')

    outline = ' '.join(f'{fmt(x)} {fmt(y)}' for x, y in M.OUTLINE.exterior.coords)
    keepouts = []
    for h in M.BOARD_DATA['furos']:
        for layer in ('F', 'B'):
            if h['tipo'] == 'furo':
                shape = f'(circle {layer} {fmt(h["d"])} {fmt(h["x"])} {fmt(h["y"])})'
            else:
                x0,y0,x1,y1 = M.hole_shape(h).bounds
                shape = f'(rect {layer} {fmt(x0)} {fmt(y0)} {fmt(x1)} {fmt(y1)})'
            keepouts.append(f'    (keepout {shape})')

    power = {'VBAT', 'OUT_A1', 'OUT_A2', 'OUT_B1', 'OUT_B2', 'OUT_C'}
    lines = ['(pcb seguidor',
             '  (parser (string_quote ") (space_in_quoted_tokens on) (host_cad "preview") (host_version "1"))',
             '  (resolution mm 1000000)',
             '  (structure',
             '    (layer F (type signal))', '    (layer B (type signal))',
             f'    (boundary (path pcb 0 {outline}))',
             *keepouts,
             '    (via VIA_080_040)',
             '    (rule (width 0.30) (clearance 0.20))', '  )',
             '  (placement', *placements, '  )',
             '  (library', *images, *padstacks,
             '    (padstack VIA_080_040 (shape (circle F 0.8)) (shape (circle B 0.8)) (attach off))',
             '  )', '  (network']
    for net, terms in pins.items():
        lines.append(f'    (net {net} (pins {" ".join(terms)}))')
    for net in real_nets:
        width = .8 if net in power else .5 if net == 'GND' else .4 if net == '+5V' else .30
        nid = net_ids[net]
        lines.append(f'    (class C_{nid} {nid} (circuit (use_via VIA_080_040)) '
                     f'(rule (width {fmt(width)}) (clearance 0.20)))')
    for net in sorted(n for n in pins if n.startswith('NC')):
        lines.append(f'    (class C_{net} {net} (circuit (use_via VIA_080_040)) (rule (width 0.30)))')
    lines += ['  )', '  (wiring)', ')', '']
    DSN.write_text('\n'.join(lines), encoding='utf8')
    MAPA.write_text(json.dumps({'net_ids': {v:k for k,v in net_ids.items()}, 'pads':mapping},
                               ensure_ascii=False, indent=2),encoding='utf8')

    old=json.loads((M.HERE/'trilhas_classificadas.json').read_text(encoding='utf8'))
    for track in old['tracks']:
        track['status']='removida'
    for via in old['vias']:
        via['status']='removida'
    old['ratsnest'],old['redes']=T.connectivity(positions, [], [])
    (M.HERE/'etapa1_colocacao.json').write_text(json.dumps(old,indent=1,ensure_ascii=False),encoding='utf8')

    # Variante CAD do contorno: a geometria original e os demais furos nao mudam.
    import ezdxf
    d=ezdxf.new('R2010'); d.units=4
    d.layers.new('CONTORNO'); d.layers.new('FURO_VENTOINHA')
    model=d.modelspace()
    model.add_lwpolyline(list(M.OUTLINE.exterior.coords)[:-1], close=True, dxfattribs={'layer':'CONTORNO'})
    model.add_circle((0,0),8.5,dxfattribs={'layer':'FURO_VENTOINHA'})
    d.saveas(M.OUTPUT/'contorno_b_xt30.dxf')
    print('DSN:',len(pads),'pads,',len(real_nets),'redes;',len(old['ratsnest']),'conexoes iniciais',flush=True)


def sexp(text):
    # A declaracao de delimitador e uma aspa isolada na sintaxe Specctra.
    text=text.replace('(string_quote ")','(string_quote QUOTE)')
    tokens=re.findall(r'"(?:\\.|[^"\\])*"|\(|\)|[^\s()]+',text)
    root=[]; stack=[root]
    for token in tokens:
        if token=='(':
            item=[];stack[-1].append(item);stack.append(item)
        elif token==')':
            if len(stack)==1:raise ValueError('parentese excedente no SES')
            stack.pop()
        else:
            stack[-1].append(token[1:-1] if token.startswith('"') else token)
    if len(stack)!=1 or len(root)!=1:raise ValueError('SES incompleto')
    return root[0]


def child(node,name):
    return next((n for n in node if isinstance(n,list) and n and n[0]==name),None)


def import_ses():
    positions=M.load_positions()
    mapping=json.loads(MAPA.read_text(encoding='utf8'))['net_ids']
    session=sexp(SES.read_text(encoding='utf8'))
    routes=child(session,'routes')
    resolution=child(routes,'resolution')
    if not resolution:raise ValueError('resolucao ausente no SES')
    mm={'mm':1.0,'um':0.001,'mil':0.0254,'inch':25.4}
    scale=mm[resolution[1]]/float(resolution[2])
    network=child(routes,'network_out')
    if network is None:raise ValueError('network_out ausente no SES')
    old=json.loads((M.HERE/'etapa1_colocacao.json').read_text(encoding='utf8'))
    newtracks=[];newvias=[]
    for item in network[1:]:
        if not isinstance(item,list) or item[0]!='net':continue
        net=mapping.get(item[1])
        if net is None:
            if item[1].startswith('NC'):continue
            raise ValueError('rede SES desconhecida: '+str(item[1]))
        for obj in item[2:]:
            if not isinstance(obj,list) or not obj:continue
            if obj[0]=='wire':
                path=child(obj,'path')
                if not path:raise ValueError('fio sem path: '+repr(obj[:3]))
                layer={'F':1,'B':2}[path[1]]
                numbers=[float(x)*scale for x in path[3:]]
                if len(numbers)%2 or len(numbers)<4:raise ValueError('coordenadas de fio invalidas')
                xy=[[numbers[i],numbers[i+1]] for i in range(0,len(numbers),2)]
                newtracks.append({'id':f'FR-T{len(newtracks)+1}', 'net':net, 'layer':layer,
                                  'width':float(path[2])*scale,'xy':xy,'status':'nova'})
            elif obj[0]=='via':
                if obj[1]!='VIA_080_040':raise ValueError('via nao prevista: '+str(obj[1]))
                newvias.append({'id':f'FR-V{len(newvias)+1}','net':net,
                                'xy':[float(obj[2])*scale,float(obj[3])*scale],
                                'diameter':.8,'drill':.4,'status':'nova'})
    if not newtracks:raise ValueError('nenhuma trilha importada do SES')
    old['tracks'].extend(newtracks);old['vias'].extend(newvias)
    old['ratsnest'],old['redes']=T.connectivity(positions,old['tracks'],old['vias'])
    old['routing_tool']='FreeRouting 2.5.0';old['ses_resolution']=resolution[1:]
    old['ses_origem']=SES.name
    (M.HERE/'trilhas_roteadas.json').write_text(json.dumps(old,indent=1,ensure_ascii=False),encoding='utf8')
    print('SES:',len(newtracks),'trilhas,',len(newvias),'vias,',len(old['ratsnest']),'ligacoes abertas',flush=True)


def continue_dsn(proteger_potencia=False, nome=None):
    """Coloca os caminhos verificados num DSN, evitando o leitor SES do Freerouting 2.5."""
    data=json.loads((M.HERE/'trilhas_roteadas.json').read_text(encoding='utf8'))
    mapping=json.loads(MAPA.read_text(encoding='utf8'))['net_ids']
    reverse={net:nid for nid,net in mapping.items()}
    wires=[]
    for t in data['tracks']:
        if t['status']!='nova':continue
        xy=' '.join(f'{fmt(x)} {fmt(y)}' for x,y in t['xy'])
        layer='F' if t['layer']==1 else 'B'
        fixo=' (type protect)' if proteger_potencia and (t['net']=='VBAT' or t['net'].startswith('OUT_')) else ''
        wires.append(f'    (wire (path {layer} {fmt(t["width"])} {xy}) (net {reverse[t["net"]]}){fixo})')
    for v in data['vias']:
        if v['status']!='nova':continue
        x,y=v['xy']
        fixo=' (type protect)' if proteger_potencia and (v['net']=='VBAT' or v['net'].startswith('OUT_')) else ''
        wires.append(f'    (via VIA_080_040 {fmt(x)} {fmt(y)} (net {reverse[v["net"]]}){fixo})')
    source=DSN.read_text(encoding='utf8')
    marker='  (wiring)'
    if source.count(marker)!=1:raise ValueError('secao wiring inesperada')
    out=M.HERE/(nome or ('seguidor_potencia.dsn' if proteger_potencia else 'seguidor_continuacao.dsn'))
    out.write_text(source.replace(marker,'  (wiring\n'+'\n'.join(wires)+'\n  )'),encoding='utf8')
    print('DSN de continuacao:',len(wires),'elementos de cobre',flush=True)


def ligar_vm():
    """Prioriza dois enlaces curtos VBAT/VM; VCP e devolvido ao roteador."""
    p=M.load_positions()
    data=json.loads((M.HERE/'trilhas_roteadas.json').read_text(encoding='utf8'))
    data['tracks']=[t for t in data['tracks'] if not (t['status']=='nova' and t['net'] in ('VCP_A','VCP_B'))]
    data['vias']=[v for v in data['vias'] if not (v['status']=='nova' and v['net'] in ('VCP_A','VCP_B'))]
    paths=[('VM_A_saida',.45,[(-23.075,-15.225),(-23.075,-16.5)]),
           ('VM_A_largo',.80,[(-23.075,-16.5),(-25.3,-16.5),(-25.3,-16.025)]),
           ('VM_B_saida',.45,[(23.075,-9.675),(23.075,-8.4)]),
           ('VM_B_largo',.80,[(23.075,-8.4),(25.2,-8.4),(25.2,-8.425)])]
    for name,width,xy in paths:
        data['tracks'].append({'id':name,'net':'VBAT','layer':1,'width':width,
                               'xy':xy,'status':'nova','motivo':'VM/decoupling; VCP a rerotear'})
    data['ratsnest'],data['redes']=T.connectivity(p,data['tracks'],data['vias'])
    if any(e['net']=='VBAT' for e in data['ratsnest']):
        raise ValueError('VM nao se conectou a toda a rede VBAT; nao gravado')
    (M.HERE/'trilhas_roteadas.json').write_text(json.dumps(data,indent=1,ensure_ascii=False),encoding='utf8')
    print('VBAT integralmente ligado;',len(data['ratsnest']),'ligacoes de outras redes pendentes',flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['prepare']:
        prepare()
    elif len(sys.argv) in (2,3) and sys.argv[1] == 'import':
        if len(sys.argv)==3:
            SES=M.HERE / sys.argv[2]
        import_ses()
    elif sys.argv[1:] in (['continue'], ['continue','potencia']):
        continue_dsn('potencia' in sys.argv[1:])
    elif sys.argv[1:] == ['vm']:
        ligar_vm()
    elif sys.argv[1:] == ['continue','vm']:
        continue_dsn(True,'seguidor_vm.dsn')
    else:
        raise SystemExit('Uso: python freerouting_io.py prepare | import [sessao.ses] | vm | continue [potencia|vm]')
