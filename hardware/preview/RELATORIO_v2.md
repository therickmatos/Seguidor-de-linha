# Placa base — versão alpha (06/11/2026)

Pacote para o EasyEDA em `hardware/placa_alpha/` (ver o README de lá): `placa_alpha.jpg` (as duas faces com trilhas), `posicao_alpha.jpg`, `posicoes_alpha.csv`, `contorno_alpha.dxf`, `guia_alpha.dxf` e `trilhas_fixas_alpha.csv`. Origem no centro da ventoinha, +y = frente, mm.

## Resultado

- **Todas as ligações do `REDES.md` estão feitas** (54 redes, 217 pads), conferidas por um verificador independente de conectividade sobre o cobre final (trilhas, vias, pads e plano de GND).
- Folgas: nenhuma violação abaixo de 0.2 mm entre redes diferentes e de 0.3 mm entre cobre e borda/furos (0 violações no verificador). Não substitui o DRC do EasyEDA.
- 393 segmentos de trilha (246 em cima, 147 embaixo) e 173 vias: 94 do roteamento, 0 dos troncos de VBAT, 12 térmicas (6 por DRV8874) e 67 de costura do GND.
- **Plano de GND nas duas faces.** 115 trilhas de GND do autorroteador ficaram redundantes e foram retiradas; a conectividade foi conferida com o plano. No EasyEDA: criar as áreas de cobre GND (cima e baixo) com folga de 0,25 mm e reconstruir antes do DRC.

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
  - cristal (pinos 7/8 → X1 → C11/C12), saída de potência do U3 (OUT1/OUT2/VM) e a bomba de carga do U3 (VCP/CPH/CPL).

## Larguras desenhadas (potência)

| rede | mín. (mm) | máx. (mm) | trecho < 0,6 mm |
|---|---|---|---|
| `VBAT` | 0.40 | 2.00 | 23.2 mm |
| `OUT_A1` | 0.40 | 1.50 | 4.9 mm |
| `OUT_A2` | 0.40 | 1.50 | 6.1 mm |
| `OUT_B1` | 0.40 | 1.50 | 0.9 mm |
| `OUT_B2` | 0.40 | 1.50 | 3.1 mm |
| `OUT_C` | 0.40 | 1.50 | 2.5 mm |
| `+5V` | 0.40 | 0.60 | 73.0 mm |

Os trechos estreitos são as saídas dos pinos 0,45 mm do DRV8874 (passo 0,65) e passagens entre pads; o resto foi alargado até 1,0–1,2 mm onde a folga permitiu. No EasyEDA, alargar onde houver espaço.

## Conferir antes de fabricar

- **Barra do J3 deitada embaixo:** confirmar que a barra/conversor encaixa e que a altura do plástico não toca o chão (fica atrás da borda, como no EVA-RT).
- **Cristal X1:** a prévia usa 3225 (baixo, cabe sob a bateria). Se vier HC-49/S do doador, ele é alto demais para ficar sob a bateria; avisar para reposicionar.
- **C9** ficou junto ao AVCC (pinos 18/21); os pinos VCC 4/6 recebem o +5V pela trilha, como no EVA-RT (que também tem um único 100 nF afastado). Se quiser, cabe um 100 nF extra no esquemático.
- **XT30 (J1) em pé em (-27,0; -27,8)**, eixo longo em y, por dentro do suporte esquerdo, com o pino 1 (+) para a frente: corpo a 0,9 mm do suporte, 6,4 mm do motor, 1,9 mm da bateria e 10,4 mm do plano da engrenagem da roda; pads a 0,8 mm da borda. Traseira: pés do EVA-RT estendidos em linha reta até y = −33 (|x| 24…40), com chanfro de 45° até o centro em y = −30. A peça é a XT30U-M (C99101, macho de cabo): os copos vão nos furos. Medir o diâmetro dos copos (furo Ø2,5 / pad Ø3,9 estimados) e cortar rente o que sobrar embaixo (~2,5 mm até o chão). Prender o cabo da bateria baixo e para trás, longe da ventoinha.
- **Botões SW0–SW2: chave táctil SMD 3 × 6 de 2 terminais** (TC-3610; na JLC, TC-3601L-2.5-260G, C2845294): corpo 6,0 × 3,6 × 2,5 mm, pads 1,2 × 1,2 de |x| = 3,1 a 4,3. SW0 (reset) no pé direito, 0,7 mm atrás do suporte do motor; SW1/SW2 entre o J4 e a presilha da vareta da barra (o J4 foi 2,5 mm para a esquerda, x = 30,0, e os pads da ventoinha M3 foram para trás dele, girados 90°). A vareta passa por cima da faixa x ≈ 43–47: nada de componente ali.
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
