# Hardware — ligações e lista de componentes (ESP32-C3 Super Mini)

_Atualizado em 16/10/2026: mapa de pinos e alimentação refeitos para a placa de face simples sem jumpers (`posicionamento_sugerido.png` / `roteamento_sugerido.dxf`). 20/10/2026: braços da barra. 21/10/2026: braços medidos na barra V1 (Gerber), versão longa (furos de 50 a 185 mm) e de 12 cm (50 a 110 mm), e patins. 24/10/2026: resultados da primeira energização (ver seção no fim)._

## ESP32-C3 Super Mini
| Pino (nº no footprint) | Liga em | Observação |
|---|---|---|
| 5V (16) | **nada** | a lógica agora vem do Mini-360 em 3,3 V direto no 3V3 |
| GND (15) | GND comum | |
| 3V3 (14) | OUT+ do Mini-360, C2, VCC/STBY/PWMA/PWMB da TB6612, pino 1 da barra, R3, VCC do KY-022 | |
| GPIO0 (9) | S0 da barra | ADC |
| GPIO1 (10) | S1 da barra | ADC |
| GPIO2 (11) | S2 da barra | pull-up R3 10 kΩ (pino de boot) |
| GPIO3 (12) | S3 da barra | ADC |
| GPIO4 (13) | SIG (C0) da barra | ADC |
| GPIO5 (1) | BIN1 | PWM |
| GPIO6 (2) | START (S do KY-022) | entrada; o pull-up interno do reset não atrapalha |
| GPIO7 (3) | BIN2 | PWM |
| GPIO8 (4) | meio da SW2 → sinal do ESC | pull-down R4 10 kΩ do lado do ESC; LED da placa pisca junto |
| GPIO9 (5) | botão U8 (outro lado no GND) | BOOT; não apertar ao ligar |
| GPIO10 (6) | AIN1 | PWM |
| GPIO20 (7) | AIN2 | PWM (RX; sem log de boot). **Pull-up interno no boot: precisa de pull-down externo 4,7–10 kΩ ao GND** (ver Primeira energização) |
| GPIO21 (8) | **nada** | TX solta log no boot, por isso ficou sem motor |

## Ligações por rede
| Rede | Pontos ligados |
|---|---|
| VBAT | XT60 +, ESC+ (pad), VM da TB6612, + do C3 470 µF, pino do meio da SW1 |
| VSW | pino lateral da SW1 → IN+ do Mini-360 |
| 3V3 | OUT+ do Mini-360 (ajustado em 3,3 V), C2 100 nF, 3V3 do C3, VCC + STBY + PWMA + PWMB da TB6612, pino 1 da barra, R3, VCC do KY-022 |
| ESC_SW / ESC_SIG | GPIO8 → meio da SW2; lado da SW2 → sinal do ESC (U7) + R4 10 kΩ ao GND |
| BTN | GPIO9, U8 pino 1; U8 pino 4 no GND |
| START | GPIO6, S do KY-022 |
| M_ESQ_A/B, M_DIR_A/B | AO → motor esquerdo, BO → motor direito (pads dos N20) |
| GND | plano de cobre único: XT60 −, ESC−, GND do servo do ESC, GNDs da TB6612, − do C3, IN−/OUT− do Mini-360, GND do ESP, GND da barra, GND do KY-022, U8, R4, C2 |
- Removidos: 5V, VBAT_ADC (R1, R2, C1) e R5. Medir bateria → alarme de LiPo no balanceamento (recolocar o divisor custaria ~2 jumpers).

## Barra de sensores (conector 1×8, pino 1 à esquerda olhando de cima, robô de frente para cima)
| Pino | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| Barra | +5V | GND | P6 | C0 | S3 | S2 | S1 | S0 |
| Placa | 3V3 | GND | sem ligação | GPIO4 | GPIO3 | GPIO2 | GPIO1 | GPIO0 |
- Barra alimentada em 3,3 V (o C0 a 5 V queimaria o C3). Mini-360 dá mais corrente que o regulador do ESP para os LEDs.
- Testar em 3,3 V antes de corroer: diferença clara linha × fundo nos 12 sensores, na altura real, com luz forte. ADC com atenuação de 11 dB.

## Layout da placa (face simples, 0 jumpers)
Origem = centro da turbina, +y = frente, mm. Posição do centro do footprint e rotação no EasyEDA:
| Ref | x | y | rot | Nota |
|---|---|---|---|---|
| U1 ESP32-C3 | −47,0 | 12,0 | 90 | USB para a borda esquerda; pinos ADC voltados para a frente |
| U5 barra | 0,0 | 39,6 | 0 | 3V3 à esquerda |
| U2 TB6612 | 48,0 | −5,0 | 180 | entradas voltadas para o anel |
| U4 XT60 | 50,0 | 30,3 | 0 | |
| C3 470 µF | 63,0 | 19,0 | 90 | |
| ESC+ / ESC− | (63,5; 28,5) / (60,5; 33,5) | | | pads |
| U3 Mini-360 | 47,5 | 18,5 | 0 | |
| SW1 | 57,5 | 8,2 | 90 | |
| C2 | 40,3 | 28,0 | 90 | |
| U6 KY-022 | −61,0 | 24,0 | 90 | |
| U8 botão | −41,0 | −2,2 | −90 | |
| SW2 | −50,5 | −1,0 | 180 | |
| U7 sinal ESC | −57,5 | −4,6 | 0 | |
| R4 | −50,0 | −7,4 | 0 | |
| R3 | −43,19 | 16,6 | 90 | |
- Trilhas: VBAT 1,2 mm; 3V3 e motores 0,8 mm; sinais 0,6 mm; isolação ≥ 0,5 mm; resto em plano de GND. Trilhas passam por baixo do ESP, da TB6612, da bateria e dos N20.
- Bateria de lado na faixa x −37,5…38,5, y 23…37,3 (só trilhas por baixo).

## Motores e turbina
- AO1/AO2 → motor esquerdo; BO1/BO2 → motor direito. Motor girando ao contrário: inverter no firmware.
- N20 em sobretensão (VM direto na 3S): começar com PWM máximo ~70%, rampa e reversão limitada; conferir temperatura na bancada; ter par reserva.
- ESC 30 A EVO (2–6S, BEC 5 V/3 A): +/− nos pads ESC+/ESC−; A/B/C no motor da turbina em qualquer ordem (se soprar para baixo, trocar dois); cabo de servo: branco = sinal, preto/marrom = GND, vermelho (BEC) desligado. Calibrar 1000–2000 µs se necessário, com a turbina presa.

## Turbina QX-Motor 30 mm (QF1611 7000 KV)
- Folha de dados (= medido): corpo Ø34,0 mm, boca Ø37,5 mm com 5 mm de altura, corpo ~22 mm, comprimento total 50 mm. Em 3S: ~220 g de empuxo, ~11 A, 124 W no máximo. Rotor externo: manter fios e bateria a ≥3 mm do cilindro acima do duto.
- Montagem: motores por cima da placa, rodas Ø22 → face de cima da placa a ~6,0 mm do chão (fenolite 1,5 mm). A boca atravessa o furo de 38 mm; entrada a ~2 mm do chão.
- Anel de fixação em **PLA** (`gerar_anel.py`): **arquivo único `anel_edf_qx30_furo34.4.stl`**. Braçadeira com fenda de 2 mm, rebaixo Ø38,6 × 3 mm + chanfro 45°, aba de 2,5 mm, altura 14 mm, ~6,5 g.
- Furo 34,4 porque a impressora fecha ~0,1–0,2 mm. Se falhar: medir; duto não entra → ~34,6; folgado com fenda fechada → ~34,2.
- Abas a 210°, 270° e 330° (R = 24,5 mm): 3× M3×8 cabeça abaulada (ou panela) **por baixo da placa** + porca parlock em cima. Aperto: 1× M3×12 com porca no rebaixo sextavado, braçadeira a 300° (deixar ~20 mm livres na linha de 210° para a chave Allen).
- Impressão (Bambu Lab, PLA): como exportado, camada 0,2 mm, 4 paredes, 100%, sem suporte, sem brim.
- Placa: furo de 38 mm e 3 furos de **4,0 mm**; sem cobre num raio de ~4 mm em volta dos 3 furos e ~1 mm em volta do furo de 38.
- Ordem: porca no rebaixo → anel na turbina (frouxo) → turbina pelo furo de 38 → robô nas rodas com calço de 2 mm sob a entrada → apertar braçadeira → parafusos das abas → riscar o duto para ver se escorrega.
- PLA: reapertar antes de competir; não deixar no sol/carro.
- Vedação: fresta entre a boca e a placa → fita.

## Braços da barra e patins (PLA, `gerar_bracos.py` e `gerar_patins.py`)
- Arquivos: `bracos_barra_M2.5_M2.stl` (longo, os dois braços, ~17 g), `bracos_barra_12cm_M2.5_M2.stl` (12 cm, ~11 g) e `patins_barra_M2.stl` (6 patins, ~0,7 g). `python3 gerar_bracos.py` gera as duas versões de braço.
- Placa base: furos da frente a 45,98 mm, parafuso **M2,5×8** (cabeça por baixo da placa, porca em cima do pé). Pé com furo oblongo Ø2,9 × 4,1 mm (±0,6) e batente por baixo que encosta na borda da frente da placa: impede o braço de girar, já que só há um furo por lado.
- Barra V1 (Gerber `V1_Barra_de_sensores`, 2026-03): furos Ø2,05 a **89,25 mm**, parafuso **M2×8**. 12 QRE1113GR em arco: os do centro 10,6 mm à frente da linha dos furos, os das pontas 5,6 mm. Em cima da barra há um componente em |x| ≈ 40,5 mm, por isso o trecho reto do braço fica todo em |x| ≥ 42,1 mm.
- Braço de 4 mm no formato da vista de cima: abre de 45,98 para 89,25 mm e segue reto. **28 furos Ø2,4, de 50 a 185 mm a cada 5 mm** (furo da placa → furo da barra), números em cm a cada 10 mm na lateral de fora. Ponta do braço a 189 mm; com a barra no furo de 185, a frente dela fica a 198,6 mm (limite de 200 mm).
- Versão de 12 cm: mesmo pé, batente e formato, **120 mm do fundo do pé até a ponta**, **7 furos a cada 10 mm, de 50 a 110 mm**, cada um com o número em cm. Com a barra no furo de 110, a frente dela fica a 123,6 mm do furo da placa.
- Furo de **100** = sensores do centro onde ficam os do El Barto (foto: ≈110 ± 4 mm da linha dos furos da frente, ≈165 mm do eixo).
- Patim: redondo, Ø6,4 mm, embaixo da barra em cada furo e preso pelo mesmo M2. Porca M2 embutida, face de baixo lisa para uma camada da fita de deslizar, chanfro de 45°. Folga de 0,6 mm até o QRE da ponta e de 0,5 mm até os pads de baixo. Altura do sensor = patim + fita − 1,7 mm (QRE1113GR). Pares para sensor a 2,0 / 2,5 / 3,0 mm (1 / 2 / 3 riscos). Referência: o EVA-RT deixa o QRE a ~2,3 mm.
- Montagem na barra: cabeça do M2 em cima do braço → braço → barra → patim (porca dentro). Usar M2×8: o M2×10 atravessa o fundo dos patins mais baixos.
- Montagem na placa: empurrar o braço para trás até o batente encostar na borda e só então apertar; usar o mesmo furo nos dois braços.
- Lado do cobre: só 0,6 mm sem cobre em volta dos furos da frente e a cabeça do M2,5 (Ø4,5–5) passa disso. Se ela encostar em trilha (e não só no plano de GND), arruela de nylon sob a cabeça.
- O pé ocupa até 3,8 mm atrás da linha dos furos: a bateria fica atrás disso.
- Impressão (Bambu Lab, PLA), como exportado e sem suporte: braços com a face de cima na mesa (batente para cima), patins com a face lisa na mesa. Camada 0,2 mm, 4 paredes, 100%. Porca justa no patim: empurrar com o ferro de solda quente.
- Comprimento total do robô (placa de 78 mm): ~14 cm (furo 50), ~19 cm (100), ~20 cm (110), ~24 cm (150), ~27 cm (185). Se o limite for 25 cm, o último furo útil do braço longo é o de 160; o de 12 cm fica todo abaixo disso.

## Montagem
- **Mini-360: ajustar para 3,3 V antes de ligar na placa** (com multímetro, sem carga) e travar o trimpot com cola. Acima de 3,6 V queima o ESP.
- Não deixar USB conectado com a SW1 ligada (duas fontes no 3V3); para programar, SW1 desligada.
- Para gravar pelo USB, SW2 (turbina) desligada: com ela ligada o R4 puxa o GPIO8 para baixo e o modo de gravação não entra.
- Chaves SS12D00 TH: terceiro pino numa ilha isolada, só para fixação.
- Suportes dos N20 (Pololu): parafusos M2 × 8 + porca M2.

## Lista de componentes

### Eletrônica principal
| Item | Qtd | Situação | Uso |
|---|---|---|---|
| ESP32-C3 Super Mini | 1 | tem | controlador |
| Barra 12× QRE1113 (com 74HC4067) | 1 | tem | sensores |
| Módulo TB6612FNG | 1 | tem | driver dos motores |
| Motor N20 6 V 3000 rpm | 2 | tem | tração |
| EDF 30 mm QX-Motor QF1611 7000 KV | 1 | tem | sucção |
| ESC 30 A EVO | 1 | tem | turbina |
| Mini-360 | 1 | tem (2) | 3,3 V da lógica |
| ZIPPY Compact 3S 1000 mAh 25C (XT60) | 1 | tem | bateria |
| KY-022 (receptor IR) | 1 | tem | arrancador |

### Componentes da placa
| Item | Qtd | Situação | Uso |
|---|---|---|---|
| Conector XT60 macho | 1 | comprar | entrada da bateria |
| Chave deslizante SS12D00G3 (SPDT, 3 terminais) | 2 | comprar | robô e turbina |
| Botão táctil TH 6×6 | 1 | tem | U8 |
| Eletrolítico 470 µF/25 V | 1 | comprar | C3 |
| Capacitor cerâmico 100 nF (104) | 1 | comprar | C2 |
| Resistor 10 kΩ **PTH 1/4 W ou 1/8 W** (footprint 9 mm) | 2 | comprar | R3 (pull-up GPIO2) e R4 (pull-down ESC) |
| Resistor 4,7 kΩ (ou 10 kΩ) | 1 | adicionar | pull-down do GPIO20/AIN2, soldado nos pinos do header da TB |
| Barra de pinos fêmea 1×8 | 4 | comprar | ESP (2) e TB6612 (2) |
| Barra de pinos macho | 1 | comprar | barra, ESC e arrancador |
| Cabo de 8 vias | 1 | comprar | ligação até a barra |

### Mecânica
| Item | Qtd | Situação | Uso |
|---|---|---|---|
| Placa de fenolite face simples 1,5 mm | 1 | tem | chassi |
| Rodas RoboCore de silicone 22 mm | 2 | tem | tração |
| Suporte Pololu para micro motor | 2 | tem | motores |
| Anel da EDF (PLA, furo 34,4) | 1 | imprimir | turbina |
| Braços da barra (PLA, `bracos_barra_M2.5_M2.stl` ou `bracos_barra_12cm_M2.5_M2.stl`) | 2 | imprimir | barra de sensores |
| Patins da barra (PLA, `patins_barra_M2.stl`) | 2 (+4 de outras alturas) | imprimir | apoio dianteiro |
| Parafuso M3×8 cabeça abaulada (ou panela) + porca parlock | 3 | comprar | abas do anel |
| Parafuso M3×12 + porca M3 | 1 | comprar | aperto do anel |
| Parafuso M2,5×8 + porca M2,5 | 2 | comprar | braços na placa base |
| Parafuso M2×8 + porca M2 | 6 | comprar | barra e patins (2), suportes dos motores (4) |
| Fita de deslizar (fita verde 3M) | 1 | tem | uma camada na face de cada patim |
| Velcro + tira | 1 | comprar | bateria |

### Opcionais
| Item | Uso |
|---|---|
| Alarme de LiPo no conector de balanceamento | substitui a medição de bateria |
| Bateria 3S ~450 mAh | upgrade de peso |

## Por que esses pinos
- ADC do C3 só nos GPIO0–4: os cinco ficam na fileira voltada para a frente e saem em ordem direto para a barra.
- Entradas da TB6612 (GPIO5/7/10/20) na outra fileira, atravessando o ESP por dentro até a TB6612 — sem cruzamentos.
- GPIO21 (TX) solta log no boot → sem motor. GPIO6 (pull-up no reset) → START, não motor.
- GPIO2 com pull-up (boot); GPIO8 só importa no modo de gravação (ver Montagem); GPIO9 = botão/BOOT.
- STBY e PWM fixos em 3V3: estado no boot depende só de AIN/BIN (pull-down interno da TB6612) — **exceto o GPIO20, que tem pull-up interno no boot** (ver abaixo).

## Primeira energização
- Mini-360 a 3,3 V conferido antes de soldar na placa.
- Polaridade do XT60 com multímetro.
- Rodas fora do chão, turbina desligada: reiniciar algumas vezes e conferir que nenhum motor dá tranco no boot.
- Turbina presa: conferir que puxa o ar de baixo.

### Resultados (23–24/10/2026)
- Etapas 1–3 concluídas: VBAT e 3V3 ok em todos os pontos; ESP com firmware seguro e OTA (`galileia`, 192.168.1.10); TB6612 e os dois N20 giram nos dois sentidos.
- Solda fria no pino + do XT60 deixava o C3/SW1/VM sem VBAT; refeita. Várias soldas opacas: conferir continuidade por rede.
- Faísca ao medir a SW1 com bateria ligada (ponta escorregou para o GND). Medir sempre em tensão DC com a bateria ligada.
- ESC ligado direto na bateria bipa sem sinal e aquece o motor da turbina: não deixar a 3S conectada por muito tempo antes da etapa 4.
- **GPIO20 (AIN2):** é o RX da UART0 e tem pull-up interno no boot/modo de gravação → motor esquerdo dispara a 100% (PWMA fixo em 3V3). Correção: resistor 4,7–10 kΩ do AIN2 ao GND.
- **Firmware deve ser compilado com `USB CDC On Boot: Enabled`**: com Disabled, o `Serial` vai para a UART0, o GPIO20 vira RX com pull-up e o motor esquerdo fica a 100% com o firmware rodando. Os sketches têm `#error` se o CDC estiver desligado.
- Fumaça do Mini-360 na primeira energização com a TB (continuou dando 3,3 V). Tratar como suspeito: trocar pelo reserva ou testar aquecimento sem o ESP.
- Zona morta dos N20 na 3S: partem a ~30–40% de PWM (modo acionar/soltar, 20 kHz). No firmware final: PWM acionar/frear, PWM mínimo de partida e ganho por motor.
- Gravação: OTA funciona; Telnet (porta 23) no firmware de teste. Compilação no Windows lenta (excluir `AppData\Local\arduino` e `Arduino15` do Defender).

## Pendências
- Altura dos patins e furo dos braços: escolher na pista (sensor a 2,0 / 2,5 / 3,0 mm; começar no furo de 100).
- Resistor de pull-down no GPIO20/AIN2.
- Mini-360 suspeito (fumaça).
- `START 0` com o KY-022 na placa (deveria ser 1 em repouso).
- Confirmar sentido das rodas (`a 50`) e fixar INV_ESQ/INV_DIR.
- Etapa 4: ESC e turbina.
