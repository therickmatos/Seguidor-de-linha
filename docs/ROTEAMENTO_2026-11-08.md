# Roteamento da placa base (RUSH) no EasyEDA — 08/11/2026

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.

**Arquivo para abrir no EasyEDA Pro (versão atual, "plano + vias mínimas", ver a seção 6):**
`hardware/easyeda/RUSH_PCB_plano_vias.epro` (figura `RUSH_plano_vias.png`). A primeira versão, com
fanout e malha de costura (201 vias de GND), é `hardware/easyeda/RUSH_PCB_roteada.epro` (figura
`RUSH_roteada.png`); as seções 2–5 descrevem essa primeira versão. Ponto de partida: `hardware/easyeda/RUSH_PCB_nova_com_cobre.epro`,
o arquivo do Erick com o cobre do agente anterior.

Fora do cobre, o `.epro` entregue é **idêntico** ao de partida: as mesmas 65 peças nas mesmas posições,
rotações e faces, o mesmo contorno, os mesmos furos e rasgos, as mesmas redes, e nenhuma peça girada.
Só mudaram trilhas, vias e os dois planos de GND.

## 1. Avaliação do trabalho do agente anterior

| Item | Resultado |
|---|---|
| Folgas | 0 conflitos (0,2 mm entre redes; 0,3 mm até a borda e os furos) |
| Ligações abertas | **PWMA_D5, PWMB_D6, RESET** + GND (sem plano, o GND não estava ligado) |
| GND com os planos simulados nas duas faces | não fechava: 66 ilhas em cima e 64 embaixo; **o lado direito (U4, Q1, C2, C17, J4) não chegava ao J1.2**, ou seja, a volta da corrente do motor direito e da ventoinha não tinha caminho |
| Potência (VBAT, OUT_A/B, OUT_C) | **dentro das regras**: pescoços de 0,4 mm com até 1,44 mm medidos da borda do pad; gargalos de 1,0 mm com até 2,7 mm; VBAT principal com 2,0–2,5 mm; ramo da ventoinha (M3.1, D1.1, C17.1) com 1,0 mm |
| Cristal | sem via, trilhas de 0,25 mm; XTAL1 com 17 mm (somando o ramo do C9, contorna o X1.2) e XTAL2 com 9 mm; dá para encurtar no acabamento |
| Outros | 2991 pedaços de trilha (o +5V sozinho tinha 440); 25 vias ligadas a uma face só; 3 tocos de GND soltos; 2 pontas de VBAT que só encostavam na borda do pad (C17.1 e D1.1) |

**Achado importante (convenção da face de baixo):** no EasyEDA Pro, uma peça na face de baixo é o
footprint **espelhado em y** e depois girado. As sessões anteriores usavam espelho em x. A convenção foi
conferida no `EVA_RT.eprj`, roteado à mão no EasyEDA: com espelho em y, 79 de 79 pontas de trilha das peças
de baixo caem em pads da mesma rede; com espelho em x, nenhuma. O `easyeda_posicionar.py` foi corrigido.
Efeito no seu arquivo (as ligações estão certas; o que muda é só a orientação das peças em relação ao plano):

| Peça | Como está no arquivo (vista de cima) | Plano anterior |
|---|---|---|
| J3 (gravação) | J3.1 (+5V) em x = **+5,08**, J3.5 (DTR) em −5,08 | J3.1 em x = −5,08 |
| J5 (ICSP) | pino 1 (MISO) em (33,98; −13,44), pino 6 (GND) em (36,52; −8,36) | girado 180°: pino 1 em (36,51; −8,36) |
| S2 (marca direita) | girado 180° em relação ao S1/EVA-RT | igual ao EVA-RT |
| S1 | igual ao EVA-RT | — |

Para o J3 e o J5, isso decide a ordem dos fios do cabo de gravação e do adaptador ICSP. Se quiser as
duas peças como no plano, é preciso girá-las e refazer o roteamento dessa região.

## 2. O que foi feito

1. **Potência e cristal do agente mantidos** (já cumpriam as regras). Só as duas pontas de VBAT foram
   levadas ao centro do pad (C17.1 e D1.1).
2. **Fanout do GND antes dos sinais:** cada um dos 43 pads SMD de GND ganhou um toco curto (0,3 mm) e uma
   via de 0,6/0,3 (U4.15 e U4.16, vizinhos, dividem a mesma via), para nenhum pad de GND ficar cercado
   por sinais.
3. **Sinais e +5V refeitos do zero** no FreeRouting 1.9.0, com a face de baixo 2,5× mais cara: hoje são
   1290 mm de sinal em cima e 460 mm embaixo (no do agente, 926 e 892), e o plano de baixo ficou com 3305 mm²
   em 37 ilhas (eram 2887 mm² em 64 ilhas). As ligações que o FreeRouting deixou abertas (o +5V da saída do 78M05 até o
   C4/C5, que passa por baixo do U1 com duas vias, e os sinais S1_A1 e S2_A2) foram fechadas com um
   roteador de grade.
4. **Planos de GND nas duas faces** (`POUR` GND_CIMA e GND_BAIXO, um retângulo que cobre a placa; o
   EasyEDA recorta pelo contorno), **vias de costura** de 0,8/0,4 entre as ilhas e numa malha de ~5 mm,
   com reforço junto do J1.2, do PGND e do pad térmico dos drivers, do Q1.2 e dos capacitores de VBAT.
   O C6.2 e o C7.2, que ficavam fora do plano, ganharam trilha + via até o GND principal; U2.3, U2.5
   (GND do ATmega) e J3.2 só tinham saída arrancando 3 trechos de sinal em volta (DTR e PWMC_D10), que
   foram refeitos em seguida.
5. Limpeza: vias de GND sem saída retiradas, vias com furos colados fundidas.

Larguras usadas: VBAT e motores do agente (2,0–2,5 / 1,5 mm, pescoços de 0,4 mm ≤ 1,5 mm, gargalos de
1,0 mm ≤ 3 mm); ventoinha 1,0 mm; +5V 0,5 mm; sinais 0,25 mm; fanout e ligações de GND 0,3 mm.
Vias: VBAT 0,8/0,4 (as 2 do agente); sinais e +5V 0,6/0,3; GND 0,8/0,4 na costura e 0,6/0,3 no fanout.
Nenhuma via em XTAL1/XTAL2. Total de vias: 298 na placa (201 de GND, 85 de sinal, 10 de +5V, 2 de VBAT).

## 3. Conferência

Dois verificadores independentes, rodados no arquivo final:

- **`easyeda_cobre.py --gnd-planos`** (lê o `.epcb` direto): 0 ligações abertas, com o GND ligado só pelos
  planos simulados de forma **conservadora** (0,3 mm do cobre de outras redes e da borda, sem sobras
  com menos de 0,25 mm); 0 folgas abaixo de 0,2 mm; 0 cobre a menos de 0,3 mm da borda e dos furos;
  0 furos a menos de 0,3 mm um do outro; 0 trilhas de potência fora da regra; nenhuma via no cristal.
- **KiCad 7 (`easyeda_kicad_drc.py`):** a mesma placa montada no KiCad, com pads na forma exata, planos de
  GND preenchidos pelo próprio KiCad (folga de 0,25 e de 0,2 mm) e o DRC dele: **0 erros de cobre e 0
  ligações não roteadas**. Os únicos avisos são de serigrafia e de biblioteca do modelo montado para a
  conferência, que não fazem parte da placa.
- **Volta da corrente:** J1.2, U3.9, U3.17, U4.9, U4.17, Q1.2, C1.2, C2.2, C13.2, C16.2 e C17.2 chegam
  ao J1.2 por corredores de plano com pelo menos 1 mm de largura, mais as vias (`rush_gnd.py retorno`).

## 4. No EasyEDA Pro

1. Abrir `RUSH_PCB_roteada.epro` (Arquivo → Abrir).
2. Regras do plano (Copper Area / Pour): **folga até 0,3 mm** (a simulação usou 0,3; 0,25 está ok),
   **ligação sólida nos pads SMD** e alívio térmico só nos pads com furo (no J1.2, raios de 1 mm).
   Manter a remoção de ilhas soltas.
3. **Reconstruir os planos** (Rebuild All Copper Areas, em geral Shift+B). Antes disso o EasyEDA mostra o
   GND como não ligado, porque o arquivo leva só o contorno do plano e não o preenchimento.
4. Rodar o DRC. Se aparecer algo, é provável que seja diferença de regra entre o EasyEDA e esta conferência
   (por exemplo, uma folga de plano maior que 0,3 mm); me mande o relatório.

Acabamento sugerido: as trilhas do FreeRouting estão em muitos pedaços e algumas fazem voltas (ex.: o
cristal do agente); dá para limpar sem mexer nas larguras. Se for mover uma via de costura, conferir que
a ilha de plano continua ligada.

## 5. Como refazer

Em `ferramentas/preview/` (venv `/opt/seguidor-venv`; KiCad 7 só para a conferência):

```
python rush_pipeline.py entrada.epro pasta saida.epro 2.5 30   # fanout, FreeRouting, fechamento, GND, final
python easyeda_cobre.py saida.epro --gnd-planos                 # verificador
python easyeda_cobre_figura.py saida.epro figura.png            # figura das duas faces
/usr/bin/python3.12 easyeda_kicad_drc.py saida.epro conf.kicad_pcb 0.25   # DRC do KiCad
python rush_gnd.py retorno saida.epro                           # volta da corrente por corredores >= 1 mm
```

O FreeRouting não dá sempre o mesmo resultado: o arquivo entregue saiu da variante com custo 2,5 na face
de baixo e custo 30 por via, seguida das mesmas etapas do `rush_pipeline.py`.

## 6. Versão "plano + vias mínimas" (pedido do Erick, 08/11)

O Erick preferiu não encher a placa de vias: plano de GND nas duas faces primeiro e, depois de ver
onde a ligação falha, só as vias necessárias, de preferência encostadas no próprio pad. A ideia veio de
um teste dele no EasyEDA, em que uma via em cima de uma ligação de componente levou a ligação para a outra
face e resolveu o conflito.

Arquivo: `hardware/easyeda/RUSH_PCB_plano_vias.epro` (`rush_pipeline.py plano`). Partindo da versão
anterior:

1. **Tirei todo o cobre de GND da placa** (201 vias e 101 trechos). Com o plano puro, 20 grupos de pads
   de GND ficavam fora do GND principal (os pads perto do ATmega, os capacitores de desacoplamento, LEDs,
   botões, U4.15/U4.16, J3.2…).
2. **Refiz o MARK_L_A5** (sensor de marca esquerdo → ATmega pino 28): a trilha dele corria embaixo em
   y ≈ −17,3 e separava o plano de baixo sob o U3 do plano do J1, deixando a volta da corrente do motor
   esquerdo só por gargalos com menos de 1 mm. Refeita com a face de baixo mais cara, com as mesmas 5 vias.
3. **Uma via por grupo solto**: primeiro uma via encostada no pad (sobrepondo 0,1 mm da borda, com o furo
   fora do pad) que cai no plano principal da outra face; sem lugar, uma via no pedaço de plano do grupo;
   em último caso, trilha + vias pelo roteador de grade.
4. **Poda:** cada via e cada trecho de GND novo saiu, um de cada vez, quando a ligação de todos os pads
   e o retorno largo dos terminais de corrente continuavam valendo. Todas as trilhas de GND saíram (dentro
   de cada bolsão, o próprio plano liga o pad à via) e 4 vias também.

Resultado: **24 vias de GND** (10 de 0,8/0,4 encostadas em pads; 14 de 0,6/0,3), nenhuma trilha de GND.
Sinais, potência, peças e planos (`POUR`) iguais à versão anterior, exceto o MARK_L_A5.

Conferência: `easyeda_cobre.py --gnd-planos` com 0 abertas, 0 folgas, 0 furo-furo e larguras na regra;
DRC do KiCad com plano a 0,25 e a 0,3 mm com 0 erros de cobre e 0 não roteadas; retorno largo
(≥ 1 mm) do J1.2 até U3.9, U3.17, U4.9, U4.17, Q1.2, C1.2, C2.2, C13.2, C16.2 e C17.2.

As vias que ficaram (posição em mm) e o que se solta do GND principal sem cada uma (conferido tirando
uma via de cada vez):

| Via | Sem ela, solta |
|---|---|
| (−65,62; 5,77) 0,8, no pad | R5.2 |
| (−27,55; −19,50) 0,8, encostada | C13.2 (e o retorno largo dele) |
| (−23,37; 6,32) 0,8, encostada | C3.2, C4.2, C5.1 |
| (−22,25; 13,26) 0,8, encostada | LED1.1 |
| (−4,81; −25,94) 0,8, encostada | U2.3, U2.5 |
| (2,19; −20,43) 0,6, encostada | U2.21 |
| (14,70; −22,20) 0,6 | R3.2 |
| (9,80; −19,20) 0,6 | C8.2 |
| (8,00; −21,75), (12,00; −20,60), (12,50; −22,10), (13,80; −23,30), (18,20; −22,20), (21,80; −22,20), (24,50; −18,80) — 0,6 | **corrente** que leva C6.2, C7.2, C8.2, R3.2, R12.2, J3.2 e U2.21 até o GND principal |
| (20,33; 6,91) 0,8, encostada | R17.2 |
| (20,39; −8,55) 0,8, encostada | U4.15, U4.16 |
| (20,50; −13,30) e (21,60; −17,80) 0,6 | R15.2 |
| (28,75; −5,75) 0,6 | C16.2 (e o retorno largo dele) |
| (38,00; −13,00) 0,6 | SW1.1 (pelo pedaço de plano dele) |
| (39,09; 10,38) 0,8, encostada | SW3.2 |
| (21,95; 13,82) 0,8, encostada | LED4.1 |
| (69,16; 3,00) 0,8, encostada | LED3.1 |

**Ponto fraco:** a região à direita do ATmega (C6, C7, C8, R3, R12, R15, J3.2 e o pino 21 do ATmega)
fica em bolsões fechados por sinais nas duas faces e chega ao GND principal por uma corrente de 7 vias,
alternando de face. Funciona (só passa corrente de sinal e de desacoplamento), mas cada via dessa corrente
é um ponto único. Para melhorar sem pôr mais vias, dá para mudar de face ou de caminho 1–2 trilhas de sinal
nessa região, como foi feito com o MARK_L_A5, e abrir o plano. Depois de mexer, conferir de novo com
`easyeda_cobre.py --gnd-planos`.

