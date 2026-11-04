# Seguidor – placa base (clone do EVA-RT) – esquemático rev 1.0

Baseado no EVA-RT (c) EXOTIC TEAM MX, licença AGPL-3.0 (github.com/EXOTIC-TEAM-MX/EVA-RT).
Mantenha o crédito e a licença se publicar o projeto.

## Arquivos (`hardware/seguidor_base/`)
- `seguidor_base.pdf` – esquemático em A3
- `BOM_seguidor_base.csv` – lista de material (separador `;`, abre no Excel/LibreOffice)
- `REDES.md` – todas as redes com os pinos ligados, para conferir a importação no EasyEDA Pro
- `seguidor_base.kicad_sch` – esquemático (KiCad 7 ou mais novo; abre sozinho, os símbolos estão embutidos)
- `seguidor_base.kicad_pro`, `sym-lib-table`, `seguidor.kicad_sym` – projeto e biblioteca local (DRV8874PWP e VBAT)

Fonte: `ferramentas/esquematico/gen.py` (ver `ferramentas/README.md`). O EasyEDA Pro recebe o esquemático importado para o layout e o pedido na JLC.

Conectividade conferida contra a netlist exportada pelo KiCad: 54 redes, nenhuma fusão indevida,
7 pinos sem uso marcados com X (PB0/D8, PB1/D9, J2.3, J4.1, J4.6, nFAULT das duas pontes).
Footprints ainda não atribuídos: isso fica para a etapa da PCB (o campo `Encapsulamento` diz qual usar).

## Mapa de pinos (igual ao firmware EVA-RT 1.2.2)
| Função | Pino Arduino | Pino ATmega |
|---|---|---|
| Sentido A / B | D3 / D4 | 1 / 2 |
| PWM A / B | D5 / D6 | 9 / 10 |
| Ventoinha (Q1) | D10 | 14 |
| Botão 1 / 2 | D11 / D12 | 15 / 16 |
| LED A / B / C | D2 / D7 / D13 | 32 / 11 / 17 |
| Mux S0–S3 / comum | A0–A3 / A4 | 23–26 / 27 |
| Marca esq. / dir. | A5 / A6 | 28 / 19 |
| Bateria (opcional) | A7 | 22 |
| Serial RX / TX | D0 / D1 | 30 / 31 |

## O que mudou em relação ao EVA-RT
| EVA-RT | Este projeto | Por quê |
|---|---|---|
| IFX_A1 / IFX_B1 (IFX9201) | U2 / U3 DRV8874PWPR, modo PH/EN | disponível e mais barato; mesma lógica DIR/PWM |
| — | C13/C15 100 nF (VCP), C14/C16 22 nF 50 V (CPH–CPL) | bomba de carga do DRV8874 |
| — | R11/R12 1,5k 1 % (IPROPI) + R13/R14 15k/10k (VREF = 2,0 V) | limite de corrente ≈ 3,0 A por motor |
| — | R15 10k no nSLEEP | ponte sempre acordada |
| Q1 (MOSFET da ventoinha) | Q1 AO3400A (SOT-23) | liga totalmente com 5 V no gate |
| — | D1 1N5819 em paralelo com a ventoinha | roda livre (protege o Q1) |
| X1 ressonador 3 pinos | X1 cristal 16 MHz + C11/C12 22 pF | aproveita o cristal do Nano/Uno doador (o ressonador também serve, sem C11/C12) |
| R3 1k (reset) | R3 10k | necessário para o reset automático por DTR |
| Converter Conn Master (RST direto) | J3 1×5 macho 90° 2,54 mm (+5V, GND, RX, TX, DTR) + C17 100 nF DTR→RESET | gravar pela IDE com o CH340G com DTR e cabo Dupont |
| FPC1 (FPC 10 vias) | J2 barra 1×8 2,54 mm | conector da barra em 2,54 mm |
| LED3 + LED4 em paralelo no D13 (R4/R5) | só LED4 + R5 | um LED basta para o LED C |
| — | J4 fêmea 1×6 (ordem HC-05) + R16/R17 1k/2k + R18 0 Ω | Bluetooth opcional de encaixe |
| — | R23/R24 20k/10k + C18 no A7 | medição da bateria (opcional, o firmware original não usa) |
| — | J8/J9 4 pads (não montar) | só se os braços de marca forem placas separadas |
| VIN | J1 XT30 | conector da bateria 2S |
| USB to ASP Conn Master | J5 ICSP (mesmas posições) | gravar o bootloader no ATmega novo |

Sem mudança: 78M05 e capacitores (C1–C5), LED5/R10, QRE1113GR S0/S1 com R20/R21 220 Ω e R30/R31 47k,
LED1/LED2 com R6/R7, botões SW0–SW2, LED6/LED7 de TX/RX, C9/C10, R8/R9 do gate.

## Conferir antes de rotear
1. Pinos do QRE1113GR no footprint (1 ânodo, 2 cátodo, 3 coletor, 4 emissor) contra o datasheet.
2. DRV8874: pad térmico ligado ao GND com várias vias; C6/C7 e C13–C16 colados nos pinos.
3. C14/C16 (CPH–CPL) com tensão ≥ VM: use 50 V.
4. Os 100 nF podem ser todos do mesmo tipo (0603 50 V X7R) para simplificar a compra.
5. J3 na borda traseira em cima (furos em y ≤ −28), com o ATmega uns 5 mm à frente; J4 na frente direita (x ≈ 32,5).
6. LED7 e o Bluetooth disputam o RX: com o LED7 montado, deixe R18 = 0 Ω e tire o módulo para gravar.
7. Se um motor girar ao contrário, inverta os fios dele (ou troque OUT1/OUT2 na PCB).
