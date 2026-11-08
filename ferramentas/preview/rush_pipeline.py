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


def plano_e_vias(entrada, pasta, saida):
    """Versao "so o plano" (08/11, pedido do Erick): parte da placa roteada sem nenhuma via ou trilha
    de GND, refaz o MARK_L_A5 por cima (ele cortava o plano de baixo entre o U3 e o J1) e poe so as
    vias que faltam: uma por grupo de pads de GND solto, encostada no pad quando cabe, e o reforco do
    retorno dos terminais de corrente; no fim tira as vias e trilhas de GND que o plano ja dispensa.
    Pinos de GND dos DRV8874 ligados ao pad termico por dentro (ligar_drv) e vias sempre a >= 0,2 mm
    de pad SMD, com toco de trilha (regras do EasyEDA, 08/11)."""
    os.makedirs(pasta, exist_ok=True)
    p = lambda n: os.path.join(pasta, n)
    placa = C.Placa(entrada)
    import easyeda_rotear as R
    R.gravar_epro(placa, p('a_so_plano.epro'), lambda r: not (r[0] in ('LINE', 'VIA') and r[3] == 'GND'), [], [])
    RR.refazer_rede(p('a_so_plano.epro'), p('b_mark.epro'), 'MARK_L_A5', custo_b=3.0, custo_via=250)
    G.ligar_drv(p('b_mark.epro'), p('b_drv.epro'))
    G.vias_minimas(p('b_drv.epro'), p('c_vias.epro'))
    G.reforco_retorno(p('c_vias.epro'), p('d_reforco.epro'))
    G.podar_gnd(p('d_reforco.epro'), saida, base=p('b_drv.epro'))
    print(G.retorno_largo(saida))
    return C.relatorio(saida, gnd_planos=True)


def corrigir_easyeda(entrada, pasta, saida):
    """Correcoes depois do teste do Erick no EasyEDA (08/11) sobre a versao "plano + vias minimas":
    - pinos de GND dos DRV8874 ligados ao pad termico por dentro (U3.7 ficava solto) e pontes entre
      pinos de GND vizinhos (U4.15/U4.16 ficavam soltos);
    - vias encostadas em pad SMD (regra "SMD Pad to Via" do EasyEDA, mesmo da mesma rede) afastadas
      para >= 0,2 mm, no mesmo pedaco de plano, com toco de trilha ate o pad; onde 0,2 nao cabe,
      tenta >= 0,05 (sem encostar). As que nao cabem nem assim ficam e sao listadas."""
    os.makedirs(pasta, exist_ok=True)
    p = lambda n: os.path.join(pasta, n)
    G.ligar_drv(entrada, p('a_drv.epro'))
    G.afastar_vias(p('a_drv.epro'), p('b_afastado.epro'))
    folga = G.FOLGA_VIA_PAD
    G.FOLGA_VIA_PAD = 0.05
    try:
        G.afastar_vias(p('b_afastado.epro'), saida, raio=1.2)
    finally:
        G.FOLGA_VIA_PAD = folga
    print(G.retorno_largo(saida))
    return C.relatorio(saida, gnd_planos=True)


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'corrigir':
    corrigir_easyeda(sys.argv[2], sys.argv[3], sys.argv[4])
    sys.exit()

if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'plano':
    plano_e_vias(sys.argv[2], sys.argv[3], sys.argv[4])
    sys.exit()

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
