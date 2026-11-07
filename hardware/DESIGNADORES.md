# Designadores — numeração por bloco (07/11/2026)

A pedido do Erick, os designadores foram renumerados **na ordem dos blocos do esquemático** e, dentro de
cada bloco, na ordem de leitura. Assim R1–R3 ficam na alimentação, R4–R9 nos sensores de marca, e assim por
diante. A mesma numeração está no projeto do EasyEDA (`hardware/easyeda/ProPrj_RUSH_-_renumerado.epro`),
no esquemático KiCad (`hardware/seguidor_base/`), na placa KiCad e no kit do EasyEDA
(`hardware/placa_alpha/posicoes_easyeda.csv`). Fonte: `ferramentas/designadores.py`.

**Saíram:** LED7/R2 (LED de RX, não montado desde 06/11) e J8/J9 (conectores das asas soltas do EVA-RT;
os braços são da placa). No EasyEDA do Erick o cristal estava como U4; agora é **X1**.

Documentos e figuras **anteriores a 07/11** usam a numeração antiga: use a tabela abaixo.

## Antigo → novo, por bloco

| Bloco | Antigo → novo |
|---|---|
| 1 - Alimentação | J1, C1, C2, C3, U5 → **U1**, C4, C5, R10 → **R1**, LED5 → **LED1**, R23 → **R2**, R24 → **R3**, C18 → **C6** |
| 2 - Barra de sensores | J2 |
| 3 - Sensores de marca | R20 → **R4**, S0 → **S1**, R30 → **R5**, R6, LED1 → **LED2**, R21 → **R7**, S1 → **S2**, R31 → **R8**, R7 → **R9**, LED2 → **LED3** |
| 4 - Microcontrolador | U1 → **U2**, R3 → **R10**, C9 → **C7**, C10 → **C8**, SW0 → **SW1**, X1, C11 → **C9**, C12 → **C10** |
| 5 - Pontes H | U2 → **U3**, C13 → **C11**, C14 → **C12**, C6 → **C13**, R13 → **R11**, R14 → **R12**, R15 → **R13**, R11 → **R14**, M1, U3 → **U4**, C15 → **C14**, C16 → **C15**, C7 → **C16**, R12 → **R15**, M2 |
| 6 - Ventoinha | M3, R9 → **R16**, R8 → **R17**, Q1, C8 → **C17**, D1 |
| 7 - Interface | SW1 → **SW2**, SW2 → **SW3**, R5 → **R18**, LED4, R1 → **R19**, LED6 → **LED5** |
| 8 - Gravação, Bluetooth e ICSP | J3, C17 → **C18**, R16 → **R20**, R17 → **R21**, R18 → **R22**, J4, J5 |

## Novo → antigo (só os que mudaram)

C6 = C18 · C7 = C9 · C8 = C10 · C9 = C11 · C10 = C12 · C11 = C13 · C12 = C14 · C13 = C6 · C14 = C15 · C15 = C16 · C16 = C7 · C17 = C8 · C18 = C17 · LED1 = LED5 · LED2 = LED1 · LED3 = LED2 · LED5 = LED6 · R1 = R10 · R2 = R23 · R3 = R24 · R4 = R20 · R5 = R30 · R7 = R21 · R8 = R31 · R9 = R7 · R10 = R3 · R11 = R13 · R12 = R14 · R13 = R15 · R14 = R11 · R15 = R12 · R16 = R9 · R17 = R8 · R18 = R5 · R19 = R1 · R20 = R16 · R21 = R17 · R22 = R18 · S1 = S0 · S2 = S1 · SW1 = SW0 · SW2 = SW1 · SW3 = SW2 · U1 = U5 · U2 = U1 · U3 = U2 · U4 = U3

## Observações

- SW1 = reset; **SW2 = BOTÃO 1** (B1_D11) e **SW3 = BOTÃO 2** (B2_D12). Os nomes dos botões no firmware
  continuam "botão 1" e "botão 2".
- S1 = QRE de marca esquerdo (curva, A5); S2 = direito (partida/chegada, A6). Não confundir com as redes
  `S0_A0`…`S3_A3` (seleção do 74HC4067 na barra), que não mudaram.
- Os nomes das redes não mudaram; só as automáticas do KiCad (`Net-(LED1-A)` etc.) seguem os designadores.

Baseado no EVA-RT © EXOTIC TEAM MX — AGPL-3.0.
