"""Checagem geometrica independente da proposta; nao substitui DRC de fabricacao."""
import collections
import json
import sys

from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

import layout_placa as M
import proposta_organizacao as P
import trilhas_eva as T
from rotear_agrupado import DIR


def main(which):
    old,new=P.candidate()
    positions=new if which.startswith('proposta') else old
    data=json.loads((DIR/f'{which}_trilhas.json').read_text(encoding='utf8'))
    objects=[]
    for p in M.all_pads(positions):
        objects.append({'name':p['ref']+'.'+p['pin'],'net':p['net'],
                        'layers':set(p['layers']),'geom':p['shape']})
    for t in data['tracks']:
        objects.append({'name':t['id'],'net':t['net'],'layers':{t['layer']},
                        'geom':LineString(t['xy']).buffer(t['width']/2,quad_segs=8)})
    for v in data['vias']:
        objects.append({'name':v['id'],'net':v['net'],'layers':{1,2},
                        'geom':Point(v['xy']).buffer(v['diameter']/2,quad_segs=8)})
    issues=[];border=M.BOARD.buffer(-.19)
    for o in objects:
        if not border.covers(o['geom']):issues.append({'tipo':'borda/furo','obj':o['name']})
    for layer in (1,2):
        subset=[o for o in objects if layer in o['layers']]
        tree=STRtree([o['geom'] for o in subset])
        for i,a in enumerate(subset):
            for jj in tree.query(a['geom'].buffer(.19)):
                j=int(jj)
                if j<=i:continue
                b=subset[j]
                if a['net'] is not None and a['net']==b['net']:continue
                gap=a['geom'].distance(b['geom'])
                if gap<.19-1e-6:
                    issues.append({'tipo':'folga/curto','camada':layer,'a':a['name'],'b':b['name'],
                                   'rede_a':a['net'],'rede_b':b['net'],'folga_mm':round(gap,4)})
    air,summary=T.connectivity(positions,data['tracks'],data['vias'])
    result={'componentes_agrupados':True,'objetos_de_cobre':len(objects),'folga_alvo_mm':.2,
            'limite_de_verificacao_mm':.19,'violacoes':issues,
            'resumo_violacoes':dict(collections.Counter(i['tipo'] for i in issues)),
            'ligacoes_abertas':len(air),'redes_abertas':{k:v for k,v in summary.items() if v['pendencias']}}
    (DIR/f'{which}_verificacao.json').write_text(json.dumps(result,ensure_ascii=False,indent=1),encoding='utf8')
    print(which,'objetos',len(objects),'violacoes',result['resumo_violacoes'],
          'ligacoes abertas',len(air),flush=True)
    for issue in issues[:20]:print(issue,flush=True)


if __name__=='__main__':
    if len(sys.argv)!=2 or sys.argv[1] not in ('atual','proposta','proposta_continuacao'):
        raise SystemExit('Uso: python verificar_agrupado.py atual|proposta|proposta_continuacao')
    main(sys.argv[1])
