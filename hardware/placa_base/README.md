# Placa base: RUSH - SATURN

Placa encomendada na JLC em 15/11/2026. Baseada no EVA-RT (© EXOTIC TEAM MX, AGPL-3.0).

## Arquivos
| Arquivo | O que é |
|---|---|
| `ProPrj_RUSH - SATURN - v12_2026-11-15.epro` | projeto EasyEDA Pro da placa encomendada, com esquemático e PCB |
| `gerber/Gerber_Final_Saturn_v12_2026-11-15.zip` | Gerber enviado à JLC |
| `BOM_v12.csv` | lista de componentes tirada da PCB do v12 (`python3 ferramentas/bom_epro.py <epro> <csv>`) |
| `historico/` | versões anteriores (v4 a v10), na ordem em que foram feitas |

A v3 (um QRE por lado, contorno B "degraus") está em `estudo_de_caso/01_projeto/`.

## Pedido na JLC
- FR-4, 2 camadas, 1,6 mm, 172,2 × 58,6 mm.
- HASL com chumbo, cobre de 1 oz.
- Vias tented, via mínima de 0,3/0,45 mm.
- Remove Mark, teste elétrico.

## Resumo da placa
- **Contorno asa de gaivota:**
  - 172,2 × 58,6 mm;
  - furo Ø17 da ventoinha;
  - abas com dois QRE1113GR por lado.
- **Sensores de marca:**
  - S1 = esquerdo externo (A5), em (−81,5; 16);
  - S2 = esquerdo interno (D8), em (−50,5; 14);
  - S3 = direito interno (D9), em (50,5; 14);
  - S4 = direito externo (A6), em (81,5; 16).
- **Microcontrolador:** ATmega328P-AU com cristal de 16 MHz, firmware EVA-RT 1.2.2 com o mesmo mapa de pinos.
- **Motores:**
  - 2× DRV8874PWPR em modo PH/EN;
  - IPROPI de 910 Ω com VREF de 2,0 V, o que dá ITRIP ≈ 4,9 A;
  - trilhas de potência dimensionadas para 5,5 A contínuos (IPC-2221, ΔT 20 °C).
- **Ventoinha:** AO3400A com 1N5819 em paralelo com o motor, PWM no D10.
- **Alimentação:**
  - LiPo 2S pelo XT30, com furo de 2,54 mm (serve para pino de até ~2,3 mm);
  - 78M05;
  - C1/C2 eletrolíticos SMD de 220 µF/16 V.
- **Conectores:**
  - J2, barra de sensores: barra 1×8 de 2,54 mm;
  - J3, gravação: 5 pads SMD embaixo, com +5V, GND, RX, TX e DTR;
  - J4, Bluetooth: barra fêmea 1×6 na ordem do HC-05 (STATE e EN sem ligação);
  - J5, ICSP: 6 pads SMD embaixo.
- **Serigrafia de baixo:** logo do IF e "Projetado por Erick Matos".

Os pinos, as folgas com os STL do EVA-RT e o que cada versão mudou estão em `estudo_de_caso/08_chassi_asa_de_gaivota/PINOS.md`. Os scripts que geraram cada versão estão em `estudo_de_caso/08_chassi_asa_de_gaivota/codigo/v4_epro/README.md`.

## Depois da montagem
- **Sentido dos motores, testar com o robô no chão:**
  - se andar para trás, inverter os dois motores;
  - se girar no lugar, inverter um deles;
  - se a ventoinha soprar em vez de sugar, inverter a ventoinha.
- Firmware das 4 entradas de marca: S2/S3 (D8/D9) ainda não são lidos pelo 1.2.2. Os QRE internos podem ver a linha em curva fechada, e o S3 não deve disparar a parada.

## Histórico das versões
| Versão | Data | O que mudou |
|---|---|---|
| v3 | 09/11 | um QRE por lado em (±69,5; 4,5), contorno B "degraus" |
| v4 | 11–12/11 | contorno asa de gaivota, 4 QRE roteados (D1 → pino 13), tudo em 45° |
| v7 | 13/11 | 17 erros do DRC corrigidos, 37 vias de costura de GND, furo de 1,0 mm nos pads dos motores |
| v8 | 14/11 | C1/C2 em eletrolítico SMD (os radiais ficavam sob a placa de sucção), vias de VBAT de 1,6/1,0 |
| v8.1 | 14/11 | alinhamentos; QRE renomeados para S1 a S4 |
| v8.2 | 14/11 | GND do J3 e do R3 religados, rótulos dos QRE |
| v8.3 | 14/11 | segunda via de VBAT no C2; R14/R15 = 910 Ω (ITRIP ≈ 4,9 A) |
| v8.4 | 14/11 | C2 fora do giro da hélice (r 17 mm); M3 desce 1 mm |
| v8.5 | 14/11 | R2, R10, M1 e J3 com folga de todos os STL |
| v8.7 | 14/11 | trilhas de potência para 5,5 A contínuos; VBAT esquerdo e LEDC_D13 religados |
| v8.8 | 14/11 | logo do IF e "Projetado por Erick Matos" embaixo |
| v8.9 | 15/11 | plano GND; pads do J3 com 1,9 mm e J3 em y = −28,75; DRC sem erros |
| v10 | 15/11 | sinais +/− e nomes do J5 na serigrafia, copiados do Dreamcast |
| v12 | 15/11 | ajustes do Erick sobre o v10: retângulo em volta dos nomes do J5 (serigrafia de baixo), designadores do C17 e do J3 movidos, o do J5 oculto, retângulos do plano GND redesenhados (o cobre final não muda); **encomendada** |
