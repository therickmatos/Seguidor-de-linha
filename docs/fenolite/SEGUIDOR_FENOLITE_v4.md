# Seguidor fenolite — v4 (estilo do anexo 4, dupla face)

Placa base em fenolite **dupla face**, com o corpo do clone EVA-RT 100 × 80 (anexo 4) e **as mesmas peças da v3** (mesma lista, mesmo mapa de pinos: [`MAPA_PINOS.txt`](MAPA_PINOS.txt)).

![Roteamento v4](imagens/placa_v4_roteamento.png)
![Zoom](imagens/placa_v4_zoom_frente.png)
![Contornos: EVA-RT, anexo 4, v3 e v4](imagens/comparacao_contornos.png)

## Resultado (conferido com o DRC vetorial)
- 0 redes abertas, DRC 0 (folga ≥ 0,6 mm, inclusive até a borda), plano de GND nas duas faces **sem ilhas**.
- **Trilhas:** sinais 1,0 mm; potência (VBAT, motores, turbina) 1,5 mm; 3V3 1,0 mm. O menor trecho é de 0,9 mm (3V3 e GND no nariz, igual à v3).
- **7 furos com fio** (v3: 9 vias + 1 jumper):
  - 5 vias de sinal: 3V3 ×2 (nariz), BTN, GATE_D e VBAT (no pad do R4.1, para o LED do sensor de marca esquerdo);
  - 2 vias de GND: (−29,32; −20,86) e (−12,52; 22,58).
- **0 jumpers.**
- Placa 144 × 81,5 mm: corpo 100 × 81,5 + braços dos sensores de marca até ±72. Cabe na fenolite de 10 × 15 cm.

## O que mudou em relação à v3
| | v3 | v4 |
|---|---|---|
| Corpo | ±48 mm | ±50 mm (largura do EVA-RT; a presilha da vareta agarra a borda certa) |
| Braços dos sensores de marca | 9 mm | 8 mm (y 0,5…8,5), trilhas retas por baixo e GND dos dois lados |
| AMS1117 + C1/C2 | embaixo da bateria | embaixo do motor direito, com área de cobre de 3V3 na aba. Dissipa ~0,5–1 W e não esquenta mais a LiPo |
| AO3400A + R1/R2 | embaixo da bateria | embaixo do motor esquerdo, perto do TP |
| R7 (pull-down do FI_A) | entre as fileiras do U3 | acima da fileira de cima do U3 (libera o vão para o MK_L) |
| R4/R5 | raiz dos braços | raiz dos braços, alinhados com o anodo de cada QRE |
| VBAT | — | atravessa a traseira por cima (embaixo da bateria não há mais peças) |
| Trilhas | 0,8 / 1,1 / 0,9 | 1,0 / 1,5 / 1,0 |
| Furos com fio | 9 vias + 1 jumper | 7 vias, 0 jumper |

Tudo que fica embaixo dos motores tem no máximo 1,8 mm de altura (SOT-223). Cabe embaixo do 8520 (barriga a ~3,4 mm da placa) e do 1020 (~2,6 mm).

## Do anexo 4 que não dá para copiar em fenolite
- **RZ7886 DIP-8 embaixo dos motores:** o DIP tem no mínimo ~3,7 mm de altura, e a barriga do motor fica a 3,4 mm (8520) ou 2,6 mm (1020) da placa. Além disso, os terminais em x ≈ ±20…28 cairiam dentro da placa de sucção. Por isso os RZ continuam nas faixas da frente, onde o anexo 4 tinha o 78M05 e o MOSFET. Esses dois agora são SMD pequenos e foram para baixo dos motores.
- **Vias metalizadas:** na fenolite, cada via é um fio soldado nas duas faces.
- **Asas separadas:** dá para fazer, mas em fenolite o braço inteiriço é mais firme e não muda o peso. Para fazer asa separada, corte em x = ±50 e emende as 3 trilhas (LEDA, MK, GND) com fio.

## Conferir antes de fabricar
- Tudo da lista da v3: XT30 (polaridade, pinos plásticos fora da placa), pads do KFC-A06, fenda de 1,6 mm na presilha, roda Ø22, gravação pelo BOOT com o IO8 em nível alto.
- **Presilhas das varetas:** a presilha tem 9,5 × 7 mm e agarra a borda em x = ±50. Confirme que ela não pega na raiz do braço (y 0,5…8,5). Se pegar, lixe a presilha.
- **Trilhas por baixo da caixa de redução direita:** VBAT (x ≈ 30,5) e BTN (x ≈ 38,8) passam por baixo da base dela. Isso é normal, mas não deixe solda alta ali.
- **AMS1117:** confira a temperatura com Wi-Fi ligado e a barra acesa. Se esquentar demais, desligue o Wi-Fi durante a volta ou baixe a corrente dos LEDs da barra.

## Arquivos
- [`TABELA_EASYEDA_v4.md`](TABELA_EASYEDA_v4.md): componentes, pads, netlist, contorno, furos, vias e trilhas ponto a ponto.
- [`placa_v4_contorno.dxf`](placa_v4_contorno.dxf), [`resumo_v4.json`](resumo_v4.json).
- [`roteamento/v4.dsn`](roteamento/v4.dsn) / [`v4.ses`](roteamento/v4.ses): Freerouting 2.1.0. A saída crua não tem o ramo de VBAT do R4.1, que foi acrescentado à mão.
- Código: `codigo/build_v4.py` (posicionamento e contorno), `codigo/dsn_v4.py` (pré-rotas e Freerouting), `codigo/final_v4.py` (plano de GND, costura, DRC, imagens e tabela). O `design.py` usa a v4 por padrão; `SEGUIDOR=v3` volta para a v3.
