# Placa base — versão alpha (06/11/2026)

Pacote para o EasyEDA em `hardware/placa_alpha/` (ver o README de lá): `placa_alpha.jpg` (as duas faces com trilhas), `posicao_alpha.jpg`, `posicoes_alpha.csv`, `contorno_alpha.dxf`, `guia_alpha.dxf` e `trilhas_fixas_alpha.csv`. Origem no centro da ventoinha, +y = frente, mm.

## Resultado

- **Todas as ligações do `REDES.md` estão feitas** (53 redes, 213 pads), conferidas por um verificador independente de conectividade sobre o cobre final (trilhas, vias, pads e plano de GND).
- Folgas: nenhuma violação abaixo de 0.2 mm entre redes diferentes e de 0.3 mm entre cobre e borda/furos (0 violações no verificador). Não substitui o DRC do EasyEDA.
- 382 segmentos de trilha (247 em cima, 135 embaixo) e 157 vias: 75 do roteamento, 2 dos troncos de VBAT, 12 térmicas (6 por DRV8874) e 68 de costura do GND.
- **Plano de GND nas duas faces.** 111 trilhas de GND do autorroteador ficaram redundantes e foram retiradas; a conectividade foi conferida com o plano. No EasyEDA: criar as áreas de cobre GND (cima e baixo) com folga de 0,25 mm e reconstruir antes do DRC.

## O que mudou em relação à prévia anterior

- **J3 (gravação) virou 5 pads SMD na face de baixo**, como o conector do EVA-RT: barra macho 1×5 2,54 mm deitada, soldada nos pads, com o plástico e os pinos longos para fora da borda traseira. Pads 1,25 × 2,25 mm (os do EVA-RT), passo 2,54 (barra comum), centro em (0; −28,575). Sem furos: o ATmega fica por cima dos pads, do outro lado.
  | pad | x (mm) | rede |
  |---|---|---|
  | J3.1 | -5.08 | `+5V` |
  | J3.2 | -2.54 | `GND` |
  | J3.3 | -0.00 | `RX_D0` |
  | J3.4 | +2.54 | `TX_D1` |
  | J3.5 | +5.08 | `DTR` |
  Visto de cima (e por trás do robô) a ordem é +5V, GND, RX, TX, DTR da esquerda para a direita, igual ao EVA-RT (que tem RESET onde aqui está o DTR; o auto-reset continua pelo C18). **Conferir a ordem dos pinos do conversor CH340G** antes de soldar a barra.
- **ATmega na posição e rotação do EVA-RT**, (0; −23), −45° (recuou 0,75 mm em relação à prévia).
- **Componentes espalhados por função, como no EVA-RT**, em vez de amontoados no ATmega:
  - divisor de VREF (R11/R12) junto ao U4 e pull-up do nSLEEP (R13) junto ao U3;
  - capacitores de cada DRV8874 em fileira, colados nos pinos de potência (C13/C11/C12 sob o U3, C16/C14/C15 sobre o U4), R14/R15 (IPROPI) ao lado do pino 6;
  - divisor do VBAT (R2/R3/C6) no lugar do LED3/R4 do EVA-RT (designadores de lá); C18 (DTR→RESET) junto ao pad DTR;
  - cristal à esquerda dos pinos 7/8 com C9/C10; C7 junto ao AVCC; LED de TX (LED5/R19) e pull-up do reset (R10) nas posições do EVA-RT. Frente esquerda (5 V) e frente direita (ventoinha, LED C, Bluetooth) mantidas do EVA-RT.
- **Cobre desenhado à mão (fixo), o resto pelo FreeRouting 1.9:**
  - troncos de VBAT na face de baixo, como no EVA-RT: J1 → driver esquerdo → sobe pela esquerda até C1 → contorna a frente da ventoinha até C2; na direita desce por cima até C14/C16 (VM do U4);
  - feixe dos sensores (S0_A0–S3_A3, C0_A4) em volta do furo da ventoinha até J2, como o octógono do EVA-RT;
  - saídas de potência dos dois DRV8874 até os motores (OUT1/OUT2/VM), com pescoço de 0,4 mm só junto do pino, e a bomba de carga do U4 (VCP/CPH/CPL);
  - ventoinha (07/11): + do M3 colado no tronco de VBAT, C17 logo acima dele, D1 embaixo logo atrás dos pads (laço de roda-livre curto) e OUT_C subindo reto do M3.2 ao dreno do Q1, sem via.

## Larguras e correntes (conferência automática, `larguras.py`)

Para cada rede de potência o verificador acha o **caminho por onde a corrente passa** (poda os ramos que só levam a capacitor de 100 nF ou divisor) e mede cada trilha desse caminho. Capacidade pela IPC-2221, camada externa, cobre de 1 oz (o padrão da JLC).

| largura | +10 °C | +20 °C | resistência |
|---|---|---|---|
| 0,40 mm | 1,2 A | 1,7 A | 1,23 mΩ/mm |
| 0,60 mm | 1,7 A | 2,2 A | 0,82 mΩ/mm |
| 0,80 mm | 2,0 A | 2,8 A | 0,61 mΩ/mm |
| 1,00 mm | 2,4 A | 3,2 A | 0,49 mΩ/mm |
| 1,20 mm | 2,7 A | 3,7 A | 0,41 mΩ/mm |
| 1,50 mm | 3,2 A | 4,4 A | 0,33 mΩ/mm |
| 2,00 mm | 4,0 A | 5,4 A | 0,25 mΩ/mm |
| 2,50 mm | 4,6 A | 6,3 A | 0,20 mΩ/mm |
| 3,00 mm | 5,3 A | 7,2 A | 0,16 mΩ/mm |

| caminho | corrente típica / pico | trilhas no caminho (mm por largura) | finas fora dos pinos |
|---|---|---|---|
| `VBAT` | 3,0 / 8,0 A | 0,40 mm: 8,5; 1,20 mm: 21,0; 1,50 mm: 31,3; 2,00 mm: 3,7; 3,00 mm: 74,7 | **nenhuma** |
| `VBAT` até o 78M05 | 0,25 / 0,4 A | 1,20 mm: 7,6; 1,50 mm: 29,6; 3,00 mm: 30,2 | **nenhuma** |
| `OUT_A1` | 1,0 / 3,0 A | 1,50 mm: 15,6 | **nenhuma** |
| `OUT_A2` | 1,0 / 3,0 A | 0,50 mm: 1,5; 1,50 mm: 19,0 | **nenhuma** |
| `OUT_B1` | 1,0 / 3,0 A | 1,00 mm: 3,6; 1,20 mm: 13,4; 1,50 mm: 10,1 | **nenhuma** |
| `OUT_B2` | 1,0 / 3,0 A | 0,50 mm: 1,9; 1,00 mm: 1,9; 1,50 mm: 6,0 | **nenhuma** |
| `OUT_C` | 1,5 / 3,0 A | 1,20 mm: 11,8; 1,50 mm: 7,2 | **nenhuma** |
| `+5V` | 0,25 / 0,4 A | 0,40 mm: 39,8; 0,50 mm: 36,1; 0,60 mm: 265,4 | **nenhuma** |

**Pescoços nos pinos do DRV8874.** O pino tem 0,45 mm de pad (o terminal do CI tem 0,19–0,30 mm) e passo 0,65 mm, então a trilha sai com 0,4–0,5 mm e alarga assim que deixa a fileira de pinos. 5 pescoços; o maior (VM, entre o pino 11 e o C14/C11, preso entre o OUT2 e o VCP) tem 2,3 mm: 2,8 mΩ, ou seja, a 3 A (limite do ITRIP) 8 mV e 25 mW, +2–3 °C, porque o calor escoa pelo pino e pela trilha larga das pontas. A IPC-2221 vale para trilhas longas; num pescoço curto quem limita é o terminal do CI.

## Conferir antes de fabricar

- **Barra do J3 deitada embaixo:** confirmar que a barra/conversor encaixa e que a altura do plástico não toca o chão (fica atrás da borda, como no EVA-RT).
- **Cristal X1: TXC 7A-16.000MAAJ-T** (5032 de 2 pads, CL 18 pF, C2450102), em diagonal junto dos pinos 7/8, com C9/C10 de 22 pF. Pads 1,7 × 2,4 mm com centro em ±1,85 mm.
- **C7** ficou junto ao AVCC (pinos 18/21); os pinos VCC 4/6 recebem o +5V pela trilha, como no EVA-RT (que também tem um único 100 nF afastado). Se quiser, cabe um 100 nF extra no esquemático.
- **XT30 (J1) em pé em (-27,0; -27,8)**, eixo longo em y, por dentro do suporte esquerdo, com o pino 1 (+) para a frente: corpo a 0,9 mm do suporte, 6,4 mm do motor, 1,9 mm da bateria e 10,4 mm do plano da engrenagem da roda; pads a 0,8 mm da borda. Traseira: pés do EVA-RT estendidos em linha reta até y = −33 (|x| 24…40), com chanfro de 45° até o centro em y = −30. A peça é a XT30U-M (C99101, macho de cabo): os copos vão nos furos. Medir o diâmetro dos copos (furo Ø2,5 / pad Ø3,9 estimados) e cortar rente o que sobrar embaixo (~2,5 mm até o chão). Prender o cabo da bateria baixo e para trás, longe da ventoinha.
- **Botões SW1–SW3: Jianfu TVBM17-025CF-R** (C19271064; 6,1 × 3,7 × 2,5 mm, 2 terminais com 8,0 mm de ponta a ponta) em **pads encurtados de 1,2 × 1,2 mm com centro em ±3,7** (8,6 mm no total). SW1 (reset) no pé direito; SW2/SW3 entre o J4 e a presilha da vareta da barra (J4 em x = 30,0; pads da ventoinha M3 atrás dele). A vareta passa por cima da faixa x ≈ 43–47: nada de componente ali.
- **J3 deitado embaixo:** o plástico da barra fica ~1,6 mm abaixo da face de baixo, atrás da borda (y < −30). Com pneus de Ø≈22 a face de baixo fica ~2,5 mm do chão; conferir a folga real. Alternativa: soldar a barra só para gravar, ou apoiar a barra nos pads na hora de gravar (como os pads do EVA-RT permitem).
- **Bluetooth:** R22 = 4,7 kΩ entre o TXD do HC-05 e o RX do ATmega, **sem LED de RX** (saiu do esquemático em 07/11): o conversor ganha do módulo no RX e dá para gravar com o HC-05 encaixado. O LED5 (TX) pisca durante a gravação.
- Motores em balanço (~12 mm para dentro do suporte, como no EVA-RT): travar o motor na abraçadeira (cola ou fita kapton) e deixar folga nos fios até M1/M2.
- Altura do rotor sobre a placa: nenhum componente sob o disco de Ø34; só trilhas, como no EVA-RT.
- Footprints da prévia são aproximados (KiCad/EVA-RT); usar os da LCSC no EasyEDA e refazer o DRC.

## Arquivos

- `ferramentas/preview/placa_v2.py`: posicionamento e checagens mecânicas (rotor, pés da carcaça, suportes dos motores, bateria, placa de sucção).
- `ferramentas/preview/rotear_v2.py`: DSN, cobre fixo, FreeRouting, alargamento, plano de GND e verificação (`v2/verificacao_v2.json`).
- `ferramentas/preview/figura_v2.py`: imagem; `relatorio_v2.py`: este relatório e `posicoes_v2.csv`.

Baseado no EVA-RT © EXOTIC TEAM MX — AGPL-3.0.
