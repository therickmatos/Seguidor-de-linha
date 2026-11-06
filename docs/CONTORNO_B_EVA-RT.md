# Contorno B "Degraus" para o clone do EVA-RT (versão ATmega)

_02/11/2026. Substitui o contorno do documento `EVA_RT_PCB` (não usar o `EVA_RT_JLCPCB`, que é um painel)._

## Arquivos (`hardware/contorno/`)
- `EVA-RT_contorno_B_degraus.dxf`: contorno fechado com arcos reais + furo Ø17 da ventoinha. Importar na camada Board Outline, em mm.
- `EVA-RT_B_degraus_referencia.dxf`: contorno antigo, furos do EVA-RT, rasgos do velcro, origem e rasgo opcional do QRE. Fora do repositório (feito em outra conversa). Só para conferência, numa camada de documentação.
- `contorno_B_sobre_gerber_EVA-RT.jpg`: contorno B sobre o cobre e os furos do Gerber oficial.
- `marcas_x_regra_TRIF.jpg`: posição dos QRE de marca × regra do TRIF e simulação por L.

## Referencial
- Origem no centro da ventoinha, +y para a frente. É a mesma do projeto `.eprj` (em mil) e do Gerber oficial: o ponto (206,69; 1131,89) mil do contorno = (5,25; 28,75) mm.

## Forma
- Largura 148,2 mm (braços de marca até ±74,1), comprimento 57,6 mm (de y = −32 a y = 25,6).
- Nariz curto, sem FFC: frente em y = 25,6, logo depois da barra de pinos 1×8 de 2,54 mm em y = 22,74 (pads até x ±9,74).
- Frente em degraus (estilo HLR); asas, pés, traseira e rasgos do velcro iguais aos do EVA-RT.
- Placa nua ≈ 8,5 g em FR-4 de 1,0 mm: +3,5% de área e +4,9% de inércia de giro contra o EVA-RT com braços.

## Conferência contra o Gerber oficial
- Todo o cobre e todos os furos da placa principal ficam dentro, com a mesma folga até a borda do original (0,30 mm embaixo, 0,34 mm em cima).
- Saem só o conector FFC da ponta do nariz (cobre acima de y = 25,3 e 5 vias) e as duas asas soltas de 14 × 5 mm, que viram os braços integrados (ligação pelos 4 pads em x = ±45).
- Rasgos do velcro: 1 × 7 mm em x = ±13,7…±19,7, y = −28,2; borda reta em y = −30 atrás deles.

## Sensores de marca × TRIF 2026 (regulamento RoboCore, Figuras 2 e 4)
- Marca de 40 × 19 mm a 40 mm da borda da linha de 19 mm → de 49,5 a 89,5 mm do centro da linha, meio em 69,5.
- QRE nos braços em (±69,5; 4,5), 27 mm à frente do eixo (y = −22,56).
- Partida/chegada (retas): o QRE cruza a 69,0–70,0 mm, mesmo 250 mm depois de uma R100 de 180°.
- Marcas de curva (106 casos, R100–R500, curvas encadeadas e em S), por distância L do centro da barra ao eixo:

| L (mm) | Na marca | Com 4 mm de folga | Lateral ao cruzar |
|---|---|---|---|
| 64 | 106/106 | 106/106 | 55,7…78,6 |
| 67 | 106/106 | 106/106 | 54,1…80,1 |
| 70 | 106/106 | 104/106 | 52,4…81,7 |
| 73 | 106/106 | 102/106 | 50,7…83,3 |
| 76 | 105/106 | 100/106 | 48,8…84,9 |
| 82 | 101/106 | 88/106 | 44,7…88,6 |

- **Recomendação: L entre 67 e 70 mm.** O nariz curto permite: com a barra V1 (centro ~14 mm à frente da borda de trás), L = 70 deixa ~8 mm entre a barra e o nariz.
- Com a presilha e o patim do EVA-RT, cada 1 mm de vareta soma 1 mm em L (L = 82 ↔ vareta de ~56 mm desde y = −4), então L = 70 ↔ ~44 mm.
- QRE nunca passa a menos de 44,7 mm do centro da linha com L = 70 (não lê a própria linha).
- Código da simulação: `marcas_sim.py` (robô como reboque, barra ideal sobre a linha).
- **06/11:** simulação refeita em `ferramentas/preview/marcas_sim.py` (eixo em y −22,59, controle P e barra deslocada, marca antes/centrada/depois da troca): `hardware/preview/marcas_trif_sim.jpg` e resumo em `docs/DECISOES_2026-11-05.md`.
