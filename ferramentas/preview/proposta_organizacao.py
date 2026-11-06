"""Estudo historico de posicionamento, anterior a decisao de retirar o J3 PTH.

O pedido vigente e recuar U1 e colocar o conector deitado na outra face; este
estudo nao implementa essas mudancas. Consulte docs/HANDOFF_2026-11-06.md.

Coordenadas em mm; +y aponta para a frente. Inspirado em principios visuais do
HLR (nao copia seu layout). Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import copy
import csv
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Patch
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union

import layout_placa as M
import gerar_figuras as G


# Avanco de U1 depende da altura real do rotor. Os demais movimentos mantem
# conectores, botoes, motores, sensores e a face dos componentes ja decididos.
CHANGES = {
    'U1': (0, -20.5, -45, 'avanco 1,75 mm; depende da folga real do rotor'),
    'X1': (-5.5, -26.0, 180, 'cristal 3225 aproximado dos pinos XTAL; modelo a confirmar'),
    'C11': (-7.0, -23.8, 180, 'capacitor de XTAL1 junto ao cristal'),
    'C12': (-9.0, -26.5, 180, 'capacitor de XTAL2 junto ao cristal'),
    'C9': (-5.5, -23.0, 135, 'desacoplamento junto a VCC e GND do ATmega'),
    'C17': (-8.0, -28.2, 180, 'capacitor DTR/RESET junto ao pino 5 de J3'),
    'R3': (-8.0, -17.8, 0, 'pull-up RESET aproximado do ATmega'),
    'C18': (8.0, -23.4, 270, 'filtro da bateria agrupado ao divisor ADC7'),
    'R23': (8.0, -20.5, 270, 'divisor ADC7 com a saida voltada para C18'),
    'R24': (10.5, -22.0, 0, 'divisor ADC7 junto a R23 e C18'),
    'R13': (11.0, -14.8, 270, 'divisor VREF alinhado, saida entre R13 e R14'),
    'R14': (11.0, -17.7, 270, 'divisor VREF alinhado, GND no lado inferior'),
    'R15': (12.5, -19.5, 90, 'pull-up de nSLEEP agrupado ao controle dos drivers'),
    'C13': (-23.65, -17.65, 0, 'VCP/VM de U2 ajustado para liberar corredor'),
    'C14': (-20.85, -17.65, 0, 'CPH/CPL de U2 ajustado junto ao driver'),
    'C15': (23.55, -7.15, 180, 'VCP/VM de U3 ajustado para liberar corredor'),
    'C16': (20.75, -7.15, 180, 'CPH/CPL de U3 ajustado junto ao driver'),
}


def candidate():
    old=M.load_positions()
    new=copy.deepcopy(old)
    for c in new:
        if c['ref'] in CHANGES:
            c['x'],c['y'],c['rot'],c['motivo']=CHANGES[c['ref']]
            c['proposta']=True
    return old,new


def area(name):
    item=next(x for x in M.BOARD_DATA['areas'] if x['nome']==name)
    return unary_union([Polygon(p) for p in item['poligonos'] if len(p)>=3])


def verify(positions):
    errors=M.check_positions(positions)
    if errors:
        raise ValueError('colisoes entre componentes ou pads: '+repr(errors))
    changed={c['ref']:c for c in positions if c['ref'] in CHANGES}
    support=unary_union([area('carcaca_contato'),
                         box(-40,-28.5,-30.5,-1.8),box(30.5,-28.5,40,-1.8)])
    rotor=Point(0,0).buffer(17,quad_segs=128)
    overlapping=[]
    for ref,c in changed.items():
        body=M.body(c)
        pads=M.get_pads(c)
        geom=unary_union([body]+[p['shape'] for p in pads])
        if geom.intersection(support).area > .001:
            raise ValueError(f'{ref} invade area de apoio')
        overlap=geom.intersection(rotor).area
        if overlap > .001:
            overlapping.append((ref,round(overlap,3)))
        # Componentes movidos sao baixos e devem caber no contorno proposto.
        if not M.OUTLINE.buffer(-.2).covers(body):
            raise ValueError(f'corpo {ref} ultrapassa a placa')
        for other in positions:
            if other['dnp'] or other['ref']==ref:continue
            if c['face']!=other['face'] and not other['tht']:continue
            ob=M.body(other)
            if ob is None:continue
            for p in pads:
                if ob.intersection(p['shape']).area > .01:
                    raise ValueError(f'pad {ref}.{p["pin"]} em corpo {other["ref"]}')
            for p in M.get_pads(other):
                if body.intersection(p['shape']).area > .01:
                    raise ValueError(f'corpo {ref} sobre pad {other["ref"]}.{p["pin"]}')
    if {x[0] for x in overlapping}!={'U1'}:
        raise ValueError('componentes inesperados na projecao do rotor: '+repr(overlapping))
    u=changed['U1']
    return {'conflitos_placa':len(errors),
            'projecao_rotor_diametro_mm':34.0,
            'u1_intersecao_corpo_mm2':round(M.body(u).intersection(rotor).area,3),
            'u1_intersecao_corpo_e_pads_mm2':overlapping[0][1],
            'altura_u1_mm':M.F.FOOTPRINTS[u['footprint']]['altura_mm'],
            'altura_rotor_montado':'nao determinada nos STL avulsos',
            'componentes_movidos':len(CHANGES)}


def distances(p):
    pads={(x['ref'],x['pin']):x for c in p if not c['dnp'] for x in M.get_pads(c)}
    pairs=[('ATmega XTAL1 -> X1',('U1','7'),('X1','1')),
           ('ATmega XTAL2 -> X1',('U1','8'),('X1','3')),
           ('X1 -> C11',('X1','1'),('C11','1')),
           ('X1 -> C12',('X1','3'),('C12','1')),
           ('VCC U1 -> C9',('U1','4'),('C9','1')),
           ('GND U1 -> C9',('U1','3'),('C9','2')),
           ('J3 DTR -> C17',('J3','5'),('C17','1')),
           ('VREF R13 -> R14',('R13','2'),('R14','1'))]
    return {name:round(pads[a]['shape'].distance(pads[b]['shape']),3) for name,a,b in pairs}


def export(old,new,info):
    old_by_ref={c['ref']:c for c in old}
    (M.HERE/'posicoes_proposta_organizacao.json').write_text(
        json.dumps({'posicoes':new,'verificacao':info,'distancias_anteriores_mm':distances(old),
                    'distancias_propostas_mm':distances(new)},ensure_ascii=False,indent=1),encoding='utf8')
    with (M.HERE/'posicoes_proposta_organizacao.csv').open('w',encoding='utf8',newline='') as fh:
        wr=csv.writer(fh,delimiter=';',lineterminator='\n')
        wr.writerow(['ref','face','x_mm','y_mm','rot_graus','x_anterior_mm','y_anterior_mm',
                     'rot_anterior','alterado_nesta_proposta','motivo'])
        for c in new:
            before=old_by_ref[c['ref']]
            wr.writerow([c['ref'],c['face'],f"{c['x']:.3f}",f"{c['y']:.3f}",c['rot'],
                         f"{before['x']:.3f}",f"{before['y']:.3f}",before['rot'],
                         'sim' if c['ref'] in CHANGES else 'nao',c.get('motivo','')])


def highlight(ax,positions,proposed=False):
    # Area tracejada para o disco varrido; altura ainda nao determinada.
    ax.add_patch(Circle((0,0),17,facecolor='#f7af42',edgecolor='#ffbd62',
                        alpha=.10,linewidth=.8,zorder=2))
    ax.add_patch(Circle((0,0),17,facecolor='none',edgecolor='#ffbd62',
                        linewidth=.8,linestyle='--',alpha=.8,zorder=4))
    groups=[((-29,-19.8,13,14.5),'#63c7ef'),((16,-18.8,13,14.5),'#63c7ef'),
            ((-11.5,-29.8,25,16.2),'#f0cf6a')]
    for (x,y,w,h),color in groups:
        ax.add_patch(Rectangle((x,y),w,h,facecolor=color,edgecolor=color,
                               linewidth=.8,alpha=.07,zorder=2))
        ax.add_patch(Rectangle((x,y),w,h,fill=False,edgecolor=color,
                               linewidth=.7,linestyle='--',alpha=.8,zorder=4))
    if proposed:
        ax.annotate('U1: avanço 1,75 mm\nfolga do rotor a conferir',
                    xy=(0,-20.5),xytext=(17,-24.3),color='#ffd38c',fontsize=6.2,
                    arrowprops={'arrowstyle':'->','color':'#ffd38c','lw':.7},zorder=25)


def render(old,new,info):
    fig=plt.figure(figsize=(21,17.2),dpi=200)
    G.header(fig,'ORGANIZAÇÃO DA PLACA  |  ATUAL × PROPOSTA',
             'Duas vistas sem cobre · princípios observados no HLR: grupos funcionais, potência separada e sinais em feixes · grade 5 mm')
    a=fig.add_axes([.045,.51,.91,.40]);b=fig.add_axes([.045,.09,.91,.40])
    empty={'tracks':[],'vias':[],'ratsnest':[]}
    for ax,p,title in [(a,old,'ATUAL · SEM TRILHAS'),(b,new,'PROPOSTA · SEM TRILHAS')]:
        G.draw_board(ax,p,empty,0,air=False)
        highlight(ax,p,ax is b)
        ax.set_title(title,loc='left',color=G.WHITE,fontsize=10,fontweight='bold',pad=4)
    fig.text(.047,.065,'AZUL: driver, desacoplamentos e corrente do motor  ·  AMARELO: ATmega, cristal, reset e sinais',
             color='#d7e3dc',fontsize=8.3)
    fig.text(.047,.047,'FLUXO: J1 → alimentação → U2/U3 → motores  ·  J2/sensores → U1 → comandos aos drivers',
             color='#cbd8d1',fontsize=8.0)
    fig.text(.047,.028,'LARANJA: projeção do rotor Ø34 mm. A altura montada não consta nos STLs; avanço do ATmega depende dessa folga.',
             color='#ffcf86',fontsize=8.2)
    fig.text(.047,.009,'Áreas tracejadas agrupam componentes; não são trilhas. Face inferior vista através da placa. Base: EVA-RT © EXOTIC TEAM MX.',
             color='#9cb0a5',fontsize=7.6)
    out=M.OUTPUT/'filosofia_posicionamento.jpg'
    fig.savefig(out,dpi=200,facecolor=G.BG,pil_kwargs={'quality':93,'optimize':True})
    plt.close(fig)
    print('imagem:',out,flush=True)


if __name__=='__main__':
    old,new=candidate()
    info=verify(new)
    export(old,new,info)
    print(json.dumps(info,ensure_ascii=False),flush=True)
    print('distancias anteriores:',distances(old),flush=True)
    print('distancias propostas:',distances(new),flush=True)
    render(old,new,info)
