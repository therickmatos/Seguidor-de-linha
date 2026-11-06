"""Etapa 1 da placa KiCad: exporta o modelo da versao alpha para v2/kicad_dados.json.

A etapa 2 (kicad_montar.py) roda no python do sistema com o modulo pcbnew do KiCad.
Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import json
import re

import footprints as F
import layout_placa as M
import placa_v2 as V
import rotear_v2 as R

SCH = M.ROOT / 'hardware' / 'seguidor_base' / 'seguidor_base.kicad_sch'
OUT = V.SAIDA / 'kicad_dados.json'
FP_SCH = M.ROOT / 'ferramentas' / 'esquematico' / 'footprints_alpha.json'   # lido pelo gen.py


def uuids_simbolos():
    """Referencia -> uuid do simbolo no esquematico (para ligar placa e esquematico no KiCad)."""
    txt = SCH.read_text(encoding='utf8')
    out = {}
    for m in re.finditer(r'\n  \(symbol \(lib_id "[^"]+"\)', txt):
        bloco = txt[m.start():txt.find('\n  )', m.start())]
        u = re.search(r'\n    \(uuid ([0-9a-f-]+)\)', bloco)
        r = re.search(r'\(property "Reference" "([^"]+)"', bloco)
        if u and r and not r.group(1).startswith('#'):
            out[r.group(1)] = u.group(1)
    return out


def main():
    pos = V.load()
    cu = json.loads(R.COBRE.read_text(encoding='utf8'))
    uu = uuids_simbolos()
    comps = []
    for c in pos:
        fpn = c['footprint']
        fp = F.FOOTPRINTS[fpn]
        lado = c['face']
        abs_pads = {p['pin']: p for p in M.get_pads(c)}
        pads = []
        for p in fp['pads']:
            a = abs_pads[p['pino']]
            pads.append({'fisico': p['pino'], 'numero': p['rede_pino'] or '', 'x': p['x'], 'y': p['y'],
                         'w': p['w'], 'h': p['h'], 'forma': p['forma'], 'furo': p['furo'],
                         'rede': a['net'], 'abs': [a['x'], a['y']]})
        comps.append({'ref': c['ref'], 'valor': str(c.get('valor', '')), 'footprint': fpn, 'x': c['x'], 'y': c['y'],
                      'rot': float(c['rot']), 'face': lado, 'pads': pads, 'corpo': fp['corpo'],
                      'corpo_xy': fp['corpo_xy'], 'altura': fp['altura_mm'], 'uuid': uu.get(c['ref']),
                      'obs': c.get('motivo', '')})
    furos = []
    for h in M.BOARD_DATA['furos']:
        furos.append({'nome': h['nome'], 'tipo': h['tipo'], 'x': h['x'], 'y': h['y'], 'd': h.get('d'),
                      'w': h.get('w'), 'h': h.get('h')})
    data = {
        'contorno': [list(p) for p in M.OUTLINE.exterior.coords][:-1],
        'furos': furos,
        'componentes': comps,
        'trilhas': [{'rede': t['net'], 'camada': t['layer'], 'largura': t['width'], 'xy': t['xy']} for t in cu['tracks']],
        'vias': [{'rede': v['net'], 'xy': v['xy'], 'd': v['diameter'], 'furo': v['drill']} for v in cu['vias']],
        'redes': sorted({p['rede'] for c in comps for p in c['pads'] if p['rede']}),
        'regras': {'folga': R.CLEAR, 'borda': R.EDGE},
        'sem_uuid': sorted(c['ref'] for c in comps if not c['uuid']),
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False), encoding='utf8')
    fps = {c['ref']: 'seguidor_alpha:' + c['footprint'] for c in comps}
    FP_SCH.write_text(json.dumps(fps, ensure_ascii=False, indent=0, sort_keys=True) + '\n', encoding='utf8')
    print(OUT, len(comps), 'componentes,', len(data['trilhas']), 'trilhas,', len(data['vias']), 'vias,',
          len(data['redes']), 'redes; sem uuid:', data['sem_uuid'])


if __name__ == '__main__':
    main()
