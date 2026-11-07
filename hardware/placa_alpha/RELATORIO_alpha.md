# Placa base — versão alpha (06/11/2026)

Pacote para o EasyEDA em `hardware/placa_alpha/` (ver o README de lá): `placa_alpha.jpg` (as duas faces com trilhas), `posicao_alpha.jpg`, `posicoes_alpha.csv`, `contorno_alpha.dxf`, `guia_alpha.dxf` e `trilhas_fixas_alpha.csv`. Origem no centro da ventoinha, +y = frente, mm.

## Resultado

- **Todas as ligações do `REDES.md` estão feitas** (54 redes, 217 pads), conferidas por um verificador independente de conectividade sobre o cobre final (trilhas, vias, pads e plano de GND).
- Folgas: nenhuma violação abaixo de 0.2 mm entre redes diferentes e de 0.3 mm entre cobre e borda/furos (0 violações no verificador). Não substitui o DRC do EasyEDA.
- 398 segmentos de trilha (249 em cima, 149 embaixo) e 169 vias: 90 do roteamento, 0 dos troncos de VBAT, 12 térmicas (6 por DRV8874) e 67 de costura do GND.
- **Plano de GND nas duas faces.** 114 trilhas de GND do autorroteador ficaram redundantes e foram retiradas; a conectividade foi conferida com o plano. No EasyEDA: criar as áreas de cobre GND (cima e baixo) com folga de 0,25 mm e reconstruir antes do DRC.

## O que mudou em relação à prévia anterior

- **J3 (gravação) virou 5 pads SMD na face de baixo**, como o conector do EVA-RT: barra macho 1×5 2,54 mm deitada, soldada nos pads, com o plástico e os pinos longos para fora da borda traseira. Pads 1,25 × 2,25 mm (os do EVA-RT), passo 2,54 (barra comum), centro em (0; −28,575). Sem furos: o ATmega fica por cima dos pads, do outro lado.
  | pad | x (mm) | rede |
  |---|---|---|
  | J3.1 | -5.08 | `+5V` |
  | J3.2 | -2.54 | `GND` |
  | J3.3 | -0.00 | `RX_D0` |
  | J3.4 | +2.54 | `TX_D1` |
  | J3.5 | +5.08 | `DTR` |
  Visto de cima (e por trás do robô) a ordem é +5V, GND, RX, TX, DTR da esquerda para a direita, igual ao EVA-RT (que tem RESET onde aqui está o DTR; o auto-reset continua pelo C17). **Conferir a ordem dos pinos do conversor CH340G** antes de soldar a barra.
- **ATmega na posição e rotação do EVA-RT**, (0; −23), −45° (recuou 0,75 mm em relação à prévia).
- **Componentes espalhados por função, como no EVA-RT**, em vez de amontoados no ATmega:
  - divisor de VREF (R13/R14) junto ao U3 e pull-up do nSLEEP (R15) junto ao U2;
  - capacitores de cada DRV8874 em fileira, colados nos pinos de potência (C6/C13/C14 sob o U2, C7/C15/C16 sobre o U3), R11/R12 (IPROPI) ao lado do pino 6;
  - divisor do VBAT (R23/R24/C18) no lugar do LED3/R4 do EVA-RT; C17 (DTR→RESET) junto ao pad DTR;
  - cristal à esquerda dos pinos 7/8 com C11/C12; C9 junto ao AVCC; LEDs TX/RX e R1–R3 nas posições do EVA-RT. Frente esquerda (5 V) e frente direita (ventoinha, LED C, Bluetooth) mantidas do EVA-RT.
- **Cobre desenhado à mão (fixo), o resto pelo FreeRouting 1.9:**
  - troncos de VBAT na face de baixo, como no EVA-RT: J1 → driver esquerdo → sobe pela esquerda até C1 → contorna a frente da ventoinha até C2; na direita desce por cima até C15/C7 (VM do U3);
  - feixe dos sensores (S0–S3, C0) em volta do furo da ventoinha até J2, como o octógono do EVA-RT;
  - saídas de potência dos dois DRV8874 até os motores (OUT1/OUT2/VM), com pescoço de 0,4 mm só junto do pino, e a bomba de carga do U3 (VCP/CPH/CPL);
  - ventoinha (07/11): + do M3 colado no tronco de VBAT, C8 logo acima dele, D1 embaixo logo atrás dos pads (laço de roda-livre curto) e OUT_C subindo reto do M3.2 ao dreno do Q1, sem via.

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
| `VBAT` | 3,0 / 8,0 A | 0,40 mm: 6,4; 0,60 mm: 2,1; 1,20 mm: 18,4; 1,50 mm: 26,0; 2,00 mm: 17,9; 3,00 mm: 120,0 | **nenhuma** |
| `VBAT` até o 78M05 | 0,25 / 0,4 A | 1,20 mm: 15,2; 1,50 mm: 22,9; 2,00 mm: 14,2; 3,00 mm: 110,5 | **nenhuma** |
| `OUT_A1` | 1,0 / 3,0 A | 1,50 mm: 13,8 | **nenhuma** |
| `OUT_A2` | 1,0 / 3,0 A | 0,50 mm: 1,5; 1,50 mm: 19,0 | **nenhuma** |
| `OUT_B1` | 1,0 / 3,0 A | 1,50 mm: 25,2 | **nenhuma** |
| `OUT_B2` | 1,0 / 3,0 A | 0,50 mm: 1,9; 1,00 mm: 1,9; 1,50 mm: 6,0 | **nenhuma** |
| `OUT_C` | 1,5 / 3,0 A | 1,20 mm: 11,8; 1,50 mm: 7,2 | **nenhuma** |
| `+5V` | 0,25 / 0,4 A | 0,40 mm: 57,9; 0,50 mm: 17,7; 0,60 mm: 212,8 | **nenhuma** |

**Pescoços nos pinos do DRV8874.** O pino tem 0,45 mm de pad (o terminal do CI tem 0,19–0,30 mm) e passo 0,65 mm, então a trilha sai com 0,4–0,5 mm e alarga assim que deixa a fileira de pinos. 5 pescoços; o maior (VM, entre o pino 11 e o C15/C13, preso entre o OUT2 e o VCP) tem 2,3 mm: 2,8 mΩ, ou seja, a 3 A (limite do ITRIP) 8 mV e 25 mW, +2–3 °C, porque o calor escoa pelo pino e pela trilha larga das pontas. A IPC-2221 vale para trilhas longas; num pescoço curto quem limita é o terminal do CI.

## Conferir antes de fabricar

- **Barra do J3 deitada embaixo:** confirmar que a barra/conversor encaixa e que a altura do plástico não toca o chão (fica atrás da borda, como no EVA-RT).
- **Cristal X1: TXC 7A-16.000MAAJ-T** (5032 de 2 pads, CL 18 pF, C2450102), em diagonal junto dos pinos 7/8, com C11/C12 de 22 pF. Pads 1,7 × 2,4 mm com centro em ±1,85 mm.
- **C9** ficou junto ao AVCC (pinos 18/21); os pinos VCC 4/6 recebem o +5V pela trilha, como no EVA-RT (que também tem um único 100 nF afastado). Se quiser, cabe um 100 nF extra no esquemático.
- **XT30 (J1) em pé em (-27,0; -27,8)**, eixo longo em y, por dentro do suporte esquerdo, com o pino 1 (+) para a frente: corpo a 0,9 mm do suporte, 6,4 mm do motor, 1,9 mm da bateria e 10,4 mm do plano da engrenagem da roda; pads a 0,8 mm da borda. Traseira: pés do EVA-RT estendidos em linha reta até y = −33 (|x| 24…40), com chanfro de 45° até o centro em y = −30. A peça é a XT30U-M (C99101, macho de cabo): os copos vão nos furos. Medir o diâmetro dos copos (furo Ø2,5 / pad Ø3,9 estimados) e cortar rente o que sobrar embaixo (~2,5 mm até o chão). Prender o cabo da bateria baixo e para trás, longe da ventoinha.
- **Botões SW0–SW2: Jianfu TVBM17-025CF-R** (C19271064; 6,1 × 3,7 × 2,5 mm, 2 terminais com 8,0 mm de ponta a ponta) em **pads encurtados de 1,2 × 1,2 mm com centro em ±3,7** (8,6 mm no total). SW0 (reset) no pé direito; SW1/SW2 entre o J4 e a presilha da vareta da barra (J4 em x = 30,0; pads da ventoinha M3 atrás dele). A vareta passa por cima da faixa x ≈ 43–47: nada de componente ali.
- **J3 deitado embaixo:** o plástico da barra fica ~1,6 mm abaixo da face de baixo, atrás da borda (y < −30). Com pneus de Ø≈22 a face de baixo fica ~2,5 mm do chão; conferir a folga real. Alternativa: soldar a barra só para gravar, ou apoiar a barra nos pads na hora de gravar (como os pads do EVA-RT permitem).
- **Bluetooth:** R18 = 4,7 kΩ entre o TXD do HC-05 e o RX do ATmega, com **LED7 e R2 não montados** (footprints ficam na placa): o conversor ganha do módulo no RX e dá para gravar com o HC-05 encaixado. Se preferir o LED de RX, monte LED7/R2 e troque o R18 por 0 Ω (aí tire o módulo para gravar).
- Motores em balanço (~12 mm para dentro do suporte, como no EVA-RT): travar o motor na abraçadeira (cola ou fita kapton) e deixar folga nos fios até M1/M2.
- Altura do rotor sobre a placa: nenhum componente sob o disco de Ø34; só trilhas, como no EVA-RT.
- Footprints da prévia são aproximados (KiCad/EVA-RT); usar os da LCSC no EasyEDA e refazer o DRC.

## Arquivos

- `ferramentas/preview/placa_v2.py`: posicionamento e checagens mecânicas (rotor, pés da carcaça, suportes dos motores, bateria, placa de sucção).
- `ferramentas/preview/rotear_v2.py`: DSN, cobre fixo, FreeRouting, alargamento, plano de GND e verificação (`v2/verificacao_v2.json`).
- `ferramentas/preview/figura_v2.py`: imagem; `relatorio_v2.py`: este relatório e `posicoes_v2.csv`.

Baseado no EVA-RT © EXOTIC TEAM MX — AGPL-3.0.
