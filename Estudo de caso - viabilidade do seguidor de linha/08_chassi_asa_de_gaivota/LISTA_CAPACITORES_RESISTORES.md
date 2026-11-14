# Capacitores e resistores do seguidor (placa v4, asa de gaivota)

Lista tirada do arquivo do Erick que passou no DRC em 13/11/2026 (`codigo/v4_epro/entrada_erick_v8_2026-11-13.epro`). Nela, o C1 e o C2 já aparecem como eletrolíticos SMD, no lugar dos radiais com furo, porque estes ficam sob a placa de sucção. A troca de footprint ainda não foi feita no arquivo.

Baseado no EVA-RT (EXOTIC TEAM MX, AGPL-3.0).

## Capacitores: 19 montados e 1 não montado

- **2× 220 µF, 16 V, eletrolítico SMD, lata 6,3 × 7,7 mm: C1, C2**
  - Substituem os radiais de 6,3 × 11 mm e 25 V.
  - Usar série low ESR e pôr uma gota de cola na base.
  - 16 V basta para a bateria 2S (8,4 V no máximo). Para 25 V, o tamanho comum é 8 × 10 mm, e é preciso conferir se cabe.
- 1× 47 µF, 10 V, cerâmico 1210: C5 (GRM32ER61A476KE20L)
- 1× 220 nF, 50 V, 0603: C3 (está no VBAT, com 8,4 V no máximo; **25 V X7R serve**)
- 10× 100 nF, 0603: C4, C6, C7, C8, C11, C13, C14, C16, C17, C18
  - C13, C16 e C17 precisam de 25 V. Os outros podem ser de 16 V.
  - Comprando todos de 25 V X7R, um só item serve para os 10.
- 2× 22 nF, 50 V, X7R, 0603: C12, C15 (bomba de carga dos DRV8874)
- 2× 22 pF, 0603: C9, C10 (cristal; de preferência C0G/NP0)
- 1× 10 nF, 50 V, 0603: C19 (filtro do E1)
- Não montar: 10 nF, 50 V, 0603, C20

## Resistores 0603: 26

- 1× 200 Ω: R16 (gate do AO3400A; **pode ser 220 Ω**, o mesmo dos QRE, e a tolerância não importa)
- 4× 220 Ω: R4, R7, R23, R25 (LED dos 4 QRE de marca)
- 6× 1 kΩ: R1, R6, R9, R18, R19, R20
- 2× 1,5 kΩ 1%: R14, R15 (IPROPI, limite de corrente; **5% serve**: ITRIP fica entre 2,8 e 3,1 A em vez de 3,0 A)
- 1× 2 kΩ: R21 (divisor do Bluetooth)
- 1× 4,7 kΩ: R22
- 3× 10 kΩ: R10, R13, R17
- 2× 10 kΩ 1%: R3, R12
- 1× 15 kΩ 1%: R11 (VREF = 2,0 V; **5% serve**: o VREF fica entre 1,94 e 2,06 V, menos que a variação de ±4% do próprio 78M05)
- 1× 20 kΩ 1%: R2 (medição da bateria; **5% serve**, porque o firmware 1.2.2 não lê o A7)
- 4× 47 kΩ: R5, R8, R24, R26 (pull-up dos 4 QRE de marca)

Comprando 10 kΩ de 1%, eles servem para os 5 resistores de 10 kΩ.

## Outros componentes da placa

### Semicondutores e CIs
- 1× ATmega328P-AU, TQFP-32: U2 (do Nano doador, com bootloader, ou novo + bootloader pelo ICSP)
- 2× DRV8874PWPR, HTSSOP-16 com pad térmico: U3, U4
- 1× 78M05, TO-252 (DPAK): U1
- 1× AO3400A, SOT-23: Q1 (ventoinha)
- 1× 1N5819HW (ou B5819W), SOD-123: D1 (face de baixo)
- 4× QRE1113GR: S1, S2, S3, S4 (face de baixo, nas abas)

### Cristal
- 1× 16 MHz SMD 5032 (5,0 × 3,2 mm, 2 pads): X1, carga de ~18–20 pF (combina com os 22 pF do C9/C10)
  - O cristal do Nano clone costuma ser HC-49 SMD (bem maior) e não cabe nesse footprint.

### LEDs 0603
- 5× LED 0603: LED1 (5 V presente, verde), LED2 (LED A), LED3 (LED B), LED4 (LED C, vermelho), LED5 (TX)

### Botões
- 3× chave táctil SMD 6,1 × 3,7 mm (TVBM17-025CF-R ou equivalente com o mesmo footprint): SW1, SW2, SW3

### Conectores
- 1× XT30 macho de placa (XT30U-M ou XT30PW-M) ou rabicho XT30: J1 (bateria)
- 1× barra de pinos macho 1×8, 2,54 mm, reta: J2 (barra de sensores)
- 1× barra de pinos macho 1×5, 2,54 mm, 90°: J3 (gravação; deitada sobre os pads da face de baixo)
- Opcional: 1× barra fêmea 1×6, 2,54 mm: J4 (Bluetooth)
- J5 (ICSP): só pads, nada a comprar

### Já comprados / fora da lista
- M1, M2 (motores 1020) e M3 (ventoinha): só os pads na placa
