"""Roteamento completo da placa base do RUSH a partir do .epro do Erick (08/11/2026).

  python rush_pipeline.py entrada.epro pasta saida.epro [CUSTO_B VIA]

Etapas (cada uma grava um .epro intermediario na pasta):
  1. fanout   - toco + via em cada pad SMD de GND (so a potencia e o cristal do agente ficam);
  2. sinais   - FreeRouting 1.9.0 em todos os sinais e no +5V (face de baixo mais cara);
  3. fechar   - roteador de grade nas ligacoes que o FreeRouting deixou abertas;
  4. costura  - vias de costura entre as ilhas dos planos de GND (simulados a 0,3 mm);
  5. pads     - pads de GND ainda soltos ligados ao GND principal (grade);
  6. arrancar - se ainda sobrar pad de GND solto: caminho que cruza sinais, arranca e refaz (fechar);
  7. limpar   - vias da mesma rede com furos colados viram uma so; vias/trilhas de GND que nao chegam
                ao GND principal saem;
  8. final    - planos de GND (POUR) nas duas faces e ajustes de ponta de trilha.
No fim roda o verificador (easyeda_cobre.py --gnd-planos).

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import os
import sys

import easyeda_cobre as C
import rush_gnd as G
import rush_rotear as RR


def depois_do_freerouting(pasta_fr, base_fanout, pasta, saida):
    os.makedirs(pasta, exist_ok=True)
    p = lambda n: os.path.join(pasta, n)
    RR.aplicar(base_fanout, pasta_fr, p('1_sinais.epro'))
    RR.fechar(p('1_sinais.epro'), p('2_fechado.epro'))
    G.costura(p('2_fechado.epro'), p('3_costura.epro'))
    soltos = G.ligar_pads(p('3_costura.epro'), p('4_pads.epro'))
    atual = p('4_pads.epro')
    for i in range(3):
        if soltos == []:
            break
        G.ligar_com_arranque(atual, p(f'5_arranque{i}.epro'))
        RR.fechar(p(f'5_arranque{i}.epro'), p(f'5_refeito{i}.epro'))
        soltos = G.ligar_pads(p(f'5_refeito{i}.epro'), p(f'5_pads{i}.epro'))
        atual = p(f'5_pads{i}.epro')
    G.fundir_vias(atual, p('6_fundido.epro'))
    G.limpar_gnd(p('6_fundido.epro'), p('6_limpo.epro'))
    RR.finalizar(p('6_limpo.epro'), saida)
    return C.relatorio(saida, gnd_planos=True)


if __name__ == '__main__':
    entrada, pasta, saida = sys.argv[1:4]
    os.makedirs(pasta, exist_ok=True)
    base = os.path.join(pasta, '0_fanout.epro')
    if not os.path.exists(base):
        RR.fanout(entrada, base)
    fr = os.path.join(pasta, 'freerouting')
    if not os.path.exists(os.path.join(fr, 'sinais.ses')):
        custo_b = float(sys.argv[4]) if len(sys.argv) > 4 else 2.5
        via = int(sys.argv[5]) if len(sys.argv) > 5 else 30
        RR.etapa_sinais(base, fr, 100, custo_b, via)
    depois_do_freerouting(fr, base, pasta, saida)
