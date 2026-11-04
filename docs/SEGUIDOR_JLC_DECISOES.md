# Seguidor (clone do EVA-RT, placa JLC) — decisões de 03/11/2026

_Complementa `CONTORNO_B_EVA-RT.md`. Origem = centro da ventoinha, +y = frente, mm._

## Compras conferidas (ok)
- Motor 1020 7,4 V 54 mil rpm (eixo 1,2 mm) + pinhão 11T M0,3 com furo de 1,15 mm: 0,05 mm de interferência. Prensar na morsa, sem martelo.
- DRV8874PWPR ×5 (4 + 1 reserva): PH/EN = DIR + PWM do IFX9201. Pad térmico com vias para soldar por baixo.
- 692ZZ (2 × 6 × 3): bate com os alojamentos Ø6,19 × 3,0 do aro.
- GNB 350 mAh 2S 60C XT30: 45 × 20,5 × 12 mm, 20 g.

## Microcontrolador
- **ATmega328P-AU**, tirado do Nano/Uno (já com bootloader), firmware EVA-RT 1.2.2.
- Chip novo (zerado): gravar o bootloader pelo ICSP com um **Arduino Uno inteiro rodando ArduinoISP** (D10 → RESET, D11 → MOSI, D12 → MISO, D13 → SCK, 5V, GND; 10 µF entre RESET e GND do Uno; placa "Arduino Uno", programador "Arduino as ISP", "Gravar bootloader"). Cristal de 16 MHz soldado antes.
- Descartados para o seguidor:
  - ESP32-S3-MINI-1U (US$ 4,93): cabe no lugar do ATmega, mas caro e exige solda LGA.
  - ESP32-C3 direto na placa (US$ 1,86): risco de cristal/RF sem analisador, QFN com pad central, só 13 GPIOs, portar firmware. Possível teste numa placa sem prazo (perseguidor, se separado).
  - C3/S3 SuperMini: não cabe sem crescer a placa (invade o furo; antena sob a bateria).
  - USB-C + CH340N na placa: viável, trocado pelo conversor externo.

## Gravação (serial)
- **Barra de pinos macho 2,54 mm, 90°, com furo, 5 vias, em cima, no centro da borda traseira** (entre os rasgos do velcro).
- Ordem: **+5V, GND, RX (D0), TX (D1), DTR**. Marcar o +5V na serigrafia.
- Na placa: **100 nF entre o pino DTR e o RESET** + 10 kΩ de pull-up no RESET.
- Mover o ATmega ~5 mm para a frente (hoje o canto de trás chega a y ≈ −28).
- Furos em y ≤ −28 (placa de sucção vai até y = −27,5); pontas cortadas rente.
- Bateria retirada (ou levantada) para gravar, como a Exotic faz. Com ela montada, apoia ~2,5 mm no conector (fica inclinada; frente continua fora do anel).
- Conversor: **módulo CH340G com pino DTR**, jumper em 5 V. Cabo: Dupont 2,54 mm de 5 vias (CTS não usado). TXD → RX, RXD → TX.

## Bluetooth (opcional): barra fêmea própria na placa
- Barra fêmea 2,54 mm **de 6 vias** ligada na **mesma UART** (D0/D1) do conector de gravação, em paralelo. O EVA-RT já usa `Serial.begin(115200)`.
- **Ordem do HC-05 (placa ZS-040): 1 STATE (NC), 2 RXD, 3 TXD, 4 GND, 5 VCC, 6 EN (NC).**
  - HC-05 de 6 pinos encaixa nas 6 vias.
  - HC-06 de 4 pinos (VCC, GND, TXD, RXD) encaixa nas 4 vias do meio, virado ao contrário. Conferir na serigrafia do módulo antes de ligar.
  - Furar as 6 vias e soldar a barra (6 ou 4 vias) depois de saber o módulo.
- Ligações: VCC → +5V; GND → GND; TXD do módulo → RX (D0) direto; TX (D1) → **divisor 1 kΩ / 2 kΩ na placa** → RXD do módulo (entrada de 3,3 V).
- **Tirar o módulo antes de gravar**: o TXD dele em nível alto impede o conversor de comandar o D0. Um resistor em série no TXD do módulo não resolve, porque o LED de RX do EVA-RT (LED7 + 1 kΩ para o +5V) já puxa o D0.
- **Posição: frente direita, no antigo lugar do Q1.** Coluna de furos ao longo de y em **x ≈ 32,5, de y ≈ 0,7 a 13,4** (STATE embaixo, EN em cima).
  - Fica entre os pads da ventoinha (29,7; 1,8/4,3) e o SW1/SW2 (x = 37,34), com ~1 mm de cobre livre dos dois lados.
  - Fora da placa de sucção (x > 23,1), da carcaça (r > 30), dos motores e da bateria.
  - O módulo fica em pé acima da barra fêmea (~8,5 mm de altura), então passa por cima dos botões e dos fios da ventoinha.
  - O AO3400A vai ao lado dos pads da ventoinha, em ~(25,8; 5,6).
  - Lado esquerdo não serve: lá está o 78M05 (TO-252) com os capacitores.
- HC-05/HC-06/JDY-31 = Bluetooth clássico (porta COM; Android ok). iPhone: precisa de BLE (HM-10).
- Configurar o módulo em 115200 (comando AT) ou mudar o baud no firmware.
- Custos: +3–4 g e centro de massa mais alto enquanto estiver no robô (tirar para a prova); firmware precisa de um interpretador de comandos e dos parâmetros como variáveis (hoje são `#define`); evitar muitos `Serial.print` durante a volta.
- Alternativa descartada: SoftwareSerial nos D8/D9 (atrapalha o tempo do laço).

## ICSP
- Manter os 6 pads SMD Ø1,8 da face de baixo nas posições do EVA-RT:
  - x = 33,97: +5V (y −8,36), MOSI (−10,90), GND (−13,44)
  - x = 36,51: MISO (−8,36), SCK (−10,90), RESET (−13,44)
- Uso: barra 2×3 encostada ou fios provisórios.

## Outras definições
- **Conector da barra de sensores na base: 2,54 mm.** A barra V1 tem furos de 2,0 mm, então o cabo é misto (2,0 mm na barra, 2,54 mm na base) ou os fios vão soldados direto na barra.
- **AO3400A (SOT-23) no lugar do Q1** (TO-252 / IRFZ44N): totalmente ligado com 5 V no gate, 30 V / 5,7 A. Manter 200 Ω no gate, 10 kΩ gate → GND e o 1N5819 em paralelo com o motor da ventoinha. Pinagem: 1 = gate, 2 = source, 3 = drain.

## Mecânica / geometria
- Anel da carcaça da ventoinha a partir de z ≈ 11,5 mm, r ≤ 22,1 (impeller_base_1.stl): a GNB 350 (12 mm) fica com a frente em y ≈ −22,1 e sobra ~12,6 mm atrás da borda (y = −30).
- Barra V1: conector 1×8 com passo de 2,0 mm (furos em x = ±1, ±3, ±5, ±7), pinagem +5V, GND, P6 (NC), C0, S3, S2, S1, S0. Canais 0, 1, 14 e 15 do mux ligados ao GND.

## Em aberto
- Base comum (100 × 57,6, asas soldadas como no EVA-RT) × placas separadas. A base sem braços cabe na faixa ≤ 100 × 100 mm da JLC.
- Confirmar o módulo Bluetooth do Embedded (4 ou 6 pinos).
- Layout no EasyEDA: ATmega movido, barra de gravação, barra fêmea do Bluetooth + divisor, 100 nF/10 kΩ, DRV8874 com vias no pad térmico, AO3400A.
