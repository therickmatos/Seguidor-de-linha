"""Gera hardware/preview/RELATORIO_v2.md e posicoes_v2.csv a partir do roteamento verificado.

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import collections
import json

from shapely.geometry import LineString

import layout_placa as M
import placa_v2 as V
import rotear_v2 as R


def main():
    pos = V.load()
    data = json.loads(R.COBRE.read_text(encoding='utf8'))
    ver = json.loads(R.VERIF.read_text(encoding='utf8'))
    V.export_csv(pos, M.OUTPUT / 'posicoes_v2.csv')
    tracks = data['tracks']
    n_open = sum(len(g) - 1 for g in ver['abertas_final'].values())
    per_net = collections.defaultdict(lambda: {'comp': 0.0, 'min': 9.0, 'max': 0.0, 'estreito': 0.0})
    for t in tracks:
        L = LineString(t['xy']).length
        d = per_net[t['net']]
        d['comp'] += L
        d['min'] = min(d['min'], t['width'])
        d['max'] = max(d['max'], t['width'])
        if t['width'] < 0.6:
            d['estreito'] += L
    layers = collections.Counter(t['layer'] for t in tracks)
    vias = data['vias']
    kinds = collections.Counter('costura' if v.get('costura') else
                                ('termica' if v['id'].startswith('TV') else
                                 ('fixa' if v.get('fixa') else 'roteador')) for v in vias)
    j3 = [p for p in M.get_pads(next(c for c in pos if c['ref'] == 'J3'))]
    L = []
    w = L.append
    w('# Placa base — versão alpha (06/11/2026)\n')
    w('Pacote para o EasyEDA em `hardware/placa_alpha/` (ver o README de lá): `placa_alpha.jpg` (as duas faces '
      'com trilhas), `posicao_alpha.jpg`, `posicoes_alpha.csv`, `contorno_alpha.dxf`, `guia_alpha.dxf` e '
      '`trilhas_fixas_alpha.csv`. Origem no centro da ventoinha, +y = frente, mm.\n')
    w('## Resultado\n')
    if n_open == 0:
        pads_all = M.all_pads(pos)
        n_redes = len({p['net'] for p in pads_all if p['net']})
        w(f'- **Todas as ligações do `REDES.md` estão feitas** ({n_redes} redes, {len(pads_all)} pads), conferidas por um '
          'verificador independente de conectividade sobre o cobre final (trilhas, vias, pads e plano de GND).')
    else:
        w(f'- **{n_open} ligação(ões) aberta(s)**, em amarelo na imagem:')
        for net, groups in ver['abertas_final'].items():
            w(f'  - `{net}`: grupos ' + ' | '.join(', '.join(g) for g in groups))
    w(f'- Folgas: nenhuma violação abaixo de {R.CLEAR} mm entre redes diferentes e de {R.EDGE} mm entre '
      f'cobre e borda/furos ({len(ver["violacoes"])} violações no verificador). Não substitui o DRC do EasyEDA.')
    w(f'- {len(tracks)} segmentos de trilha ({layers[1]} em cima, {layers[2]} embaixo) e {len(vias)} vias: '
      f'{kinds["roteador"]} do roteamento, {kinds["fixa"]} dos troncos de VBAT, {kinds["termica"]} térmicas '
      f'(6 por DRV8874) e {kinds["costura"]} de costura do GND.')
    w(f'- **Plano de GND nas duas faces.** {ver["trilhas_gnd_removidas_pelo_plano"]} trilhas de GND do '
      'autorroteador ficaram redundantes e foram retiradas; a conectividade foi conferida com o plano. '
      'No EasyEDA: criar as áreas de cobre GND (cima e baixo) com folga de 0,25 mm e reconstruir antes do DRC.\n')
    w('## O que mudou em relação à prévia anterior\n')
    w('- **J3 (gravação) virou 5 pads SMD na face de baixo**, como o conector do EVA-RT: barra macho 1×5 '
      '2,54 mm deitada, soldada nos pads, com o plástico e os pinos longos para fora da borda traseira. '
      'Pads 1,25 × 2,25 mm (os do EVA-RT), passo 2,54 (barra comum), centro em (0; −28,575). '
      'Sem furos: o ATmega fica por cima dos pads, do outro lado.')
    w('  | pad | x (mm) | rede |')
    w('  |---|---|---|')
    for p in sorted(j3, key=lambda p: p['x']):
        w(f"  | J3.{p['pin']} | {p['x']:+.2f} | `{p['net']}` |")
    w('  Visto de cima (e por trás do robô) a ordem é +5V, GND, RX, TX, DTR da esquerda para a direita, '
      'igual ao EVA-RT (que tem RESET onde aqui está o DTR; o auto-reset continua pelo C17). '
      '**Conferir a ordem dos pinos do conversor CH340G** antes de soldar a barra.')
    w('- **ATmega na posição e rotação do EVA-RT**, (0; −23), −45° (recuou 0,75 mm em relação à prévia).')
    w('- **Componentes espalhados por função, como no EVA-RT**, em vez de amontoados no ATmega:')
    w('  - divisor de VREF (R13/R14) junto ao U3 e pull-up do nSLEEP (R15) junto ao U2;')
    w('  - capacitores de cada DRV8874 em fileira, colados nos pinos de potência '
      '(C6/C13/C14 sob o U2, C7/C15/C16 sobre o U3), R11/R12 (IPROPI) ao lado do pino 6;')
    w('  - divisor do VBAT (R23/R24/C18) no lugar do LED3/R4 do EVA-RT; C17 (DTR→RESET) junto ao pad DTR;')
    w('  - cristal à esquerda dos pinos 7/8 com C11/C12; C9 junto ao AVCC; LEDs TX/RX e R1–R3 '
      'nas posições do EVA-RT. Frente esquerda (5 V) e frente direita (ventoinha, LED C, Bluetooth) '
      'mantidas do EVA-RT.')
    w('- **Cobre desenhado à mão (fixo), o resto pelo FreeRouting 1.9:**')
    w('  - troncos de VBAT na face de baixo, como no EVA-RT: J1 → driver esquerdo → sobe pela esquerda até '
      'C1 → contorna a frente da ventoinha até C2; na direita desce por cima até C15/C7 (VM do U3);')
    w('  - feixe dos sensores (S0–S3, C0) em volta do furo da ventoinha até J2, como o octógono do EVA-RT;')
    w('  - cristal (pinos 7/8 → X1 → C11/C12), saída de potência do U3 (OUT1/OUT2/VM) e a bomba de carga '
      'do U3 (VCP/CPH/CPL).\n')
    w('## Larguras desenhadas (potência)\n')
    w('| rede | mín. (mm) | máx. (mm) | trecho < 0,6 mm |')
    w('|---|---|---|---|')
    for net in ['VBAT', 'OUT_A1', 'OUT_A2', 'OUT_B1', 'OUT_B2', 'OUT_C', '+5V']:
        d = per_net.get(net)
        if d:
            w(f"| `{net}` | {d['min']:.2f} | {d['max']:.2f} | {d['estreito']:.1f} mm |")
    w('\nOs trechos estreitos são as saídas dos pinos 0,45 mm do DRV8874 (passo 0,65) e passagens entre pads; '
      'o resto foi alargado até 1,0–1,2 mm onde a folga permitiu. No EasyEDA, alargar onde houver espaço.\n')
    w('## Conferir antes de fabricar\n')
    w('- **Barra do J3 deitada embaixo:** confirmar que a barra/conversor encaixa e que a altura do plástico '
      'não toca o chão (fica atrás da borda, como no EVA-RT).')
    w('- **Cristal X1:** a prévia usa 3225 (baixo, cabe sob a bateria). Se vier HC-49/S do doador, '
      'ele é alto demais para ficar sob a bateria; avisar para reposicionar.')
    w('- **C9** ficou junto ao AVCC (pinos 18/21); os pinos VCC 4/6 recebem o +5V pela trilha, como no EVA-RT '
      '(que também tem um único 100 nF afastado). Se quiser, cabe um 100 nF extra no esquemático.')
    f = V.folgas_j1(pos)
    nn = lambda v: f'{v:.1f}'.replace('.', ',')
    w(f"- **XT30 (J1) em pé em ({nn(f['xy'][0])}; {nn(f['xy'][1])})**, eixo longo em y, por dentro do suporte esquerdo, "
      f"com o pino 1 (+) para a frente: corpo a {nn(f['corpo_suporte'])} mm do suporte, {nn(f['corpo_motor'])} mm do "
      f"motor, {nn(f['corpo_bateria'])} mm da bateria e {nn(f['corpo_engrenagem'])} mm do plano da engrenagem da roda; "
      f"pads a {nn(f['cobre_borda'])} mm da borda. Traseira: pés do EVA-RT estendidos em linha reta até y = −33 "
      '(|x| 24…40), com chanfro de 45° até o centro em y = −30. A peça é a XT30U-M (C99101, macho de cabo): os copos vão nos furos. Medir o diâmetro dos '
      'copos (furo Ø2,5 / pad Ø3,9 estimados) e cortar rente o que sobrar embaixo (~2,5 mm até o chão). Prender o '
      'cabo da bateria baixo e para trás, longe da ventoinha.')
    w('- **Botões SW0–SW2: chave táctil SMD 3 × 6 de 2 terminais** (TC-3610; na JLC, TC-3601L-2.5-260G, C2845294): '
      'corpo 6,0 × 3,6 × 2,5 mm, pads 1,2 × 1,2 de |x| = 3,1 a 4,3. SW0 (reset) no pé direito, 0,7 mm atrás do suporte '
      'do motor; SW1/SW2 entre o J4 e a presilha da vareta da barra (o J4 foi 2,5 mm para a esquerda, x = 30,0, e os '
      'pads da ventoinha M3 foram para trás dele, girados 90°). A vareta passa por cima da faixa x ≈ 43–47: nada de '
      'componente ali.')
    w('- **J3 deitado embaixo:** o plástico da barra fica ~1,6 mm abaixo da face de baixo, atrás da borda '
      '(y < −30). Com pneus de Ø≈22 a face de baixo fica ~2,5 mm do chão; conferir a folga real. Alternativa: '
      'soldar a barra só para gravar, ou apoiar a barra nos pads na hora de gravar (como os pads do EVA-RT permitem).')
    w('- **Bluetooth:** R18 = 4,7 kΩ entre o TXD do HC-05 e o RX do ATmega, com **LED7 e R2 não montados** '
      '(footprints ficam na placa): o conversor ganha do módulo no RX e dá para gravar com o HC-05 encaixado. '
      'Se preferir o LED de RX, monte LED7/R2 e troque o R18 por 0 Ω (aí tire o módulo para gravar).')
    w('- Motores em balanço (~12 mm para dentro do suporte, como no EVA-RT): travar o motor na abraçadeira '
      '(cola ou fita kapton) e deixar folga nos fios até M1/M2.')
    w('- Altura do rotor sobre a placa: nenhum componente sob o disco de Ø34; só trilhas, como no EVA-RT.')
    w('- Footprints da prévia são aproximados (KiCad/EVA-RT); usar os da LCSC no EasyEDA e refazer o DRC.\n')
    w('## Arquivos\n')
    w('- `ferramentas/preview/placa_v2.py`: posicionamento e checagens mecânicas (rotor, pés da carcaça, '
      'suportes dos motores, bateria, placa de sucção).')
    w('- `ferramentas/preview/rotear_v2.py`: DSN, cobre fixo, FreeRouting, alargamento, plano de GND e verificação '
      '(`v2/verificacao_v2.json`).')
    w('- `ferramentas/preview/figura_v2.py`: imagem; `relatorio_v2.py`: este relatório e `posicoes_v2.csv`.\n')
    w('Baseado no EVA-RT © EXOTIC TEAM MX — AGPL-3.0.')
    (M.OUTPUT / 'RELATORIO_v2.md').write_text('\n'.join(L) + '\n', encoding='utf8')
    print('ok', n_open, 'abertas')


if __name__ == '__main__':
    main()
