# Seguidor fenolite — v5 (dupla face, contorno EVA-RT, nariz curto)

Mesmas peças da v4, só com top e bottom. Contorno simétrico no estilo do EVA-RT: chanfro de 45° no canto de dentro dos pés, nariz rente ao ESP e braços dos sensores de marca mais finos.

![Roteamento v5](imagens/placa_v5_roteamento.png)
![Corpo e nariz](imagens/placa_v5_zoom_frente.png)
![Braço esquerdo: QRE invertido no rasgo](imagens/placa_v5_zoom_braco.png)
![Sensores de marca na pista TRIF](imagens/v5_marcas_pista.png)

## Resultado (DRC vetorial próprio)
- **0 redes abertas, DRC 0.** Folga mínima de 0,6 mm entre cobres e até a borda. Plano de GND nas duas faces, sem ilhas.
- **8 furos com fio e 0 jumper.** A v4 tinha 7.
  - 6 vias de sinal: 3V3 ×2 (nariz e AMS1117), GATE_D, TURB_N, MK_L e MK_R (ao lado de cada QRE).
  - 2 vias de GND: (−24,70; −20,50) e (−29,02; −0,34).
- **Trilhas:**
  - sinais 1,0 mm; potência 1,5 mm;
  - paredes dos braços (LED e GND) 0,8 mm;
  - por baixo do ESP, no vão do IO9: 3V3 a 0,75 mm e GND a 0,8 mm. É a menor trilha da placa e fica acima de 0,7.
- **Placa 148,2 × 78,0 mm.** A v4 tinha 144 × 81,5. Cabe na fenolite de 10 × 15, mas sobram só ~0,9 mm de cada lado no comprimento.
- Peso estimado da placa: ~12–13 g. A v4 ficava em ~14 g.

## O que mudou em relação à v4
| | v4 | v5 |
|---|---|---|
| Contorno | cantos traseiros diferentes; frente "quadrada" | simétrico; nariz com chanfros e flancos a 45° como o EVA-RT; pés com o chanfro de 45° do EVA-RT (de (±30,6; −34,5) a (±24,6; −28,5)) |
| Nariz | ESP + barra deitada | ESP rente (fileira de trás em y = 22,5) e barra **vertical** a 2,54 mm da fileira da frente; frente em y = 43,5 |
| Botão | KFC-A06 no IO9 | removido: o **BOOT da própria SuperMini** já é o IO9. O pino IO9 não tem furo, e no vão dele passam o GND e o 3V3 do nariz |
| Barra (J2) | 1×8 90° | 1×8 **vertical**, sem o pino 3 (P6, sem ligação). No lugar dele fica a via do 3V3 |
| Braços | 8 mm, QRE soldado por baixo (janela a 0,7 mm do chão) | **7,4 mm**; QRE **invertido num rasgo** de 3,8 × 3,1 mm, com a janela a ~2,3 mm do chão |
| Posição do QRE | ±68 | **±69,5 = centro da fita lateral** (ver abaixo) |
| Pinagem do QRE | 3 = E, 4 = C (**errado**) | 3 = coletor, 4 = emissor (datasheet) |
| XT30 | x = −33,5 | x = −35,0 (1,5 mm para fora, para caber o chanfro) |

## ⚠ Pinagem do QRE1113: erro corrigido (afeta a v3 e a v4)
O datasheet da onsemi (QRE1113/D) dá **1 anodo, 2 catodo, 3 coletor, 4 emissor**. Os pinos 1 e 2 ficam na mesma fileira, o 4 embaixo do 1 e o 3 embaixo do 2.

A v3 e a v4 herdaram 3 = emissor e 4 = coletor. Com isso o fototransistor ficaria invertido (coletor no GND, emissor no GPIO) e o sensor de marca praticamente não responderia.

Na v5:
- O QRE foi girado para que a ponta K+C fique virada para o corpo. O coletor desce por uma via logo ao lado do pad e segue por baixo até o ESP. O catodo passa por cima dessa via e se junta à parede de GND.
- O LED (anodo) chega pela outra parede do braço até a ponta de fora.
- **No EasyEDA, confira a numeração do footprint do QRE1113GR contra o datasheet antes de tudo.**

## Sensores de marca × regra TRIF
- **Geometria da marca:** fita de 19 × 40 mm a 40 mm da borda da linha de 19 mm. Ela vai de 49,5 a 89,5 mm do centro da linha, com centro em **69,5 mm**. O QRE está em x = ±69,5.
- **Nas retas** (as marcas de partida/chegada ficam nas retas, do lado direito), o sensor passa **exatamente no centro da fita**, com ±20 mm de folga para o robô desviar da linha.
- **Virado para o chão:** o QRE entra de cabeça para baixo no rasgo e os terminais apoiam nos pads de cima. A janela olha para o chão pelo rasgo e fica a ~2,3 mm dele com roda Ø22, a mesma altura da barra do EVA-RT.
- **Nas curvas:** simulei o robô como um reboque, com o centro da barra sobre a linha e o eixo atrás (`codigo/marcas_v5.py`). Foram 108 passagens por marcas de curva, em curvas de R100 a R500, curvas encadeadas e em S. O resultado depende da distância **L** do centro da barra até o eixo:

| L (mm) | Marcas de curva lidas | Lateral ao cruzar a marca | Menor distância QRE–centro da linha |
|---|---|---|---|
| **82** | **102/108** | 43,6 … 88,4 | 34,0 |
| 88 | 92/108 | 39,8 … 92,3 | 28,0 |
| 95 | 78/108 | 34,4 … 97,2 | 20,5 |
| ≥ 105 | < 70 % | — | o QRE passa por cima da própria linha na R100 → **falsa marca de chegada** |

- **Recomendação: barra o mais perto possível, L ≈ 82 mm** (a borda de trás da barra a ~2 mm da frente do nariz), e **nunca acima de 95**.
  - Com L = 82, as únicas falhas são na saída de curvas R100 para a direita, e por 0,1–5,9 mm.
  - Com a presilha e o patim do EVA-RT, isso dá uma vareta de ~56 mm, medida desde a borda de trás da presilha traseira (y = −4). Cada 1 mm a mais de vareta soma 1 mm em L.
- **Firmware:**
  - marca direita = chegada; esquerda = curva; as duas juntas = cruzamento (ignorar);
  - amostrar a ≥ 2 kHz: a 3 m/s, uma fita de 19 mm passa em ~6 ms.

### Ajuste elétrico dos QRE de marca (bancada)
A leitura é digital, com INPUT_PULLUP (~45 kΩ) no IO8 e no IO21, que não têm ADC. Para o C3 ler certo:
- sobre o branco, a corrente do coletor precisa passar de ~55 µA (pino abaixo de 0,8 V);
- sobre o preto, precisa ficar abaixo de ~18 µA (pino acima de 2,5 V).

O ganho do QRE1113 varia até 9× de peça para peça (0,1–0,9 mA a 20 mA/1 mm). Por isso, **o R4/R5 (470 Ω, ~15 mA com 2S) é um valor de partida**:
1. Meça a tensão do IO8/IO21 com o robô na altura real: deve dar **> 2,5 V no preto e < 0,8 V no branco**.
2. Se o preto der baixo (sensível demais), suba o R4/R5 (1 k a 2,2 k).
3. Se o branco não baixar, desça o resistor (mínimo de ~330 Ω, que dá ~22 mA com 2S).

O footprint 1206 continua o mesmo.

## Peças do EVA-RT adaptadas (mecânica)
- **Roda Ø22:** com fenolite de 1,6 mm, a face de baixo fica a 2,4 mm do chão. Com a roda do EVA-RT (FR-4 de 1,0 mm) ficaria a 1,9 mm.
- **Presilha da vareta (barilla_clamp):**
  - os furos são os mesmos do EVA-RT, (±43,75; −1,75) e (±43,75; 10,75), e a vareta fica em x = ±48,45;
  - os braços (y 0,8…8,2) não encostam nas presilhas (y −4…0,5 e 8,5…13);
  - a fenda de 1,0 mm da asa ficou sem uso, porque o braço é inteiriço;
  - o parafuso M2 precisa ser ~0,6 mm mais longo.
- **Patim da barra (sensor_sledge):** foi refeito para os furos da barra V1 (89,25 mm), com o mesmo anel de vareta e o mesmo esqui.
- Os STL dessas duas peças estão em `3d/` (opcional).
- Caixas de redução, base de sucção, rotor e suportes da bateria ficam iguais: os furos são os do EVA-RT.

## Mapa de pinos (ESP32-C3 SuperMini)
| Pino | Função | Pino | Função |
|---|---|---|---|
| IO0–IO3 | S0–S3 da barra | IO8 | MK_L (QRE esq.) |
| IO4 | C0 da barra (ADC) | IO9 | BOOT da SuperMini (sem furo na placa) |
| IO5 | BI_A (RZ esq.) | IO10 | BI_B (RZ dir.) |
| IO6 | FI_A + R7 10 k p/ GND | IO20 | FI_B + R6 10 k p/ GND |
| IO7 | GATE_D (turbina) | IO21 | MK_R (QRE dir.) |

**IO8 é strapping:** para gravar pelo BOOT, ele precisa estar em nível alto. Grave com o robô levantado ou sobre superfície escura: o QRE esquerdo sobre branco puxa o IO8 para baixo. Por OTA isso não importa.

## Conferir ao passar para o EasyEDA
- **Footprint do QRE1113GR:** numeração (ver acima) e rasgo de 3,8 × 3,1 em (±69,5; 4,5). Os pads encostam no rasgo de propósito, porque é ali que os terminais apoiam.
- **SuperMini sem o furo do IO9.** **J2 vertical sem o pino 3:** corte o pino da barra e ponha a via do 3V3 no lugar.
- **XT30 em x = −35:** os pinos plásticos continuam fora da placa, como antes.
- **Plugue da barra:** com a barra vertical, o cabo sobe e passa por cima. Confira se a capa do DuPont não encosta no módulo (há 0,1 mm entre a base da barra e o ESP).
- **AMS1117 com 2S:** dissipa (8,4 − 3,3) × I. Confira a temperatura com Wi-Fi ligado e a barra acesa.

## Arquivos
- `TABELA_EASYEDA_v5.md`: componentes, pads (com rede e camada), netlist, contorno, furos, vias e trilhas ponto a ponto.
- `placa_v5_contorno.dxf`: contorno, furos e rasgos. `resumo_v5.json`.
- `roteamento/v5_freerouting.*`: saída crua do Freerouting 2.1.0. O `codigo/final_v5.py` aplica os ajustes finos (barra 0,2 mm à frente, braços com a pinagem certa, XT30) e gera tudo: `cd codigo && python3 final_v5.py`.
- Código: `build_v5.py` (contorno e posicionamento), `dsn_v5.py` (pré-rotas e Freerouting), `final_v5.py` (GND, costura, DRC, imagens e tabela), `marcas_v5.py` (simulação das marcas) e `pecas_3d_v5.py` (STL).
