# Seguidor de linha — contexto do projeto

_Atualizado em 11/10/2026 (pendência de geometria em 21/10/2026). Arquivo de referência para as sessões com o Claude: manter curto e atual. Ligações completas em `HARDWARE.md`._

## Objetivo
- Competição baseada no regulamento do **TRIF 7ª edição**, que permite sucção.
- Meta: igualar ou superar a velocidade do robô **El Barto** (Club Robótica Potosí).
- Sem encoders nesta competição (prazo curto). Evolução futura: motores coreless 1020.
- Foco atual: hardware primeiro, firmware depois.

## Hardware disponível
| Item | Detalhe |
|---|---|
| Controlador | ESP32-C3 Super Mini; "ESP32" da lista inicial (modelo a confirmar); Arduino Nano de reserva |
| Sensores | Barra com 12× QRE1113 inspirada na barra da Exotic, testada e funcionando (uso do 74HC4067 e tensão da barra a confirmar) |
| Motores | N20 6 V 3000 rpm genéricos, sem encoder |
| Rodas | RoboCore de silicone, 22 mm (diâmetro a confirmar) |
| Driver | 1× TB6612FNG (módulo) |
| Turbina | EDF 30 mm QX-Motor QF1611 7000 KV + ESC 30 A |
| Partida | Módulo arrancador (recebe o sinal do controle remoto) |
| Bateria | ZIPPY Compact 3S 1000 mAh 25C: 91 g, 74 × 34 × 20 mm, conector XT60 |
| Regulador | 2× Mini-360 (buck) |

## Decidido
- Bateria Zippy 3S 1000 mAh direto no VM do TB6612 (N20 em sobretensão, como a TamanduTech fez). Usar para bancada e primeiros testes; uma 3S de ~450 mAh (metade do peso) é o primeiro upgrade se faltar desempenho.
- **Uma TB6612 só**: canal A no motor esquerdo, B no direito. Segunda só se a bancada mostrar corte térmico.
- **STBY fixo em alto** (3,3 V), como no El Barto. VCC da TB6612 em 3,3 V, nunca 5 V (nível alto mínimo = 0,7 × VCC).
- Turbina permitida pelo TRIF: EDF 30 mm + ESC 30 A.
- Sem encoder nesta competição, portanto sem mapeamento.
- PCB em fenolite, corrosão caseira.
- ESP32 com comunicação sem fio para não depender do cabo.
- **Lógica**: Mini-360 em 5,0 V no pino de 5 V/VIN da placa; o 3,3 V vem do regulador da placa. Trimpot travado com esmalte/cola.
- **Bateria no chassi**: deitada, atravessada (74 mm no sentido do eixo), centrada, logo à frente da turbina (que fica entre os motores). Centro de massa à frente do eixo, ~15–20% do peso no apoio da frente; a barra não pode levantar na aceleração. Fixar com velcro + tira. Reservar ~76 × 36 mm livres na PCB.
- **Botão**: um botão físico (calibração e partida de reserva, caso o rádio falhe); sem resistor externo (BOOT no C3, ou `INPUT_PULLUP` no DevKit).
- Rodas de 22 mm (32 mm só se a telemetria mostrar 100% de PWM por trechos longos).

## Alimentação
- XT60 como chave geral (mesmo conector da bateria); desconectar ao terminar a sessão (o ESC drena a bateria). Durante sessões de ~2 h, pode ficar conectada.
- ESC ligado por fio direto no conector da bateria; corrente da turbina não passa por trilha nem por chave. Fio vermelho do BEC desligado.
- VM direto da bateria, eletrolítico low-ESR 470 µF/25 V junto aos pinos VM; trilhas de potência ≥ 2 mm estanhadas.
- **Duas chaves deslizantes, nenhuma na potência**:
  - Chave do robô na entrada do Mini-360 (~0,2 A). Desligada, a TB6612 fica sem VCC e os motores param.
  - Chave da turbina em série no fio de sinal do ESC, com o pull-down de 10 kΩ do lado do ESC. Aberta, o ESC não recebe pulsos e a turbina não gira, mesmo com bug no firmware.
- Procedimento: ligar a chave da turbina antes da partida, porque o ESC só arma vendo o comando mínimo (1000 µs).
- Sem turbina (chave aberta) o robô roda normalmente; usar parâmetros separados com e sem turbina.
- Sem proteção contra polaridade reversa (XT60 polarizado); conferir polaridade com multímetro na primeira ligação.
- Opcional: polyfuse 0,5 A na entrada do Mini-360 + TVS SMAJ5.0A na saída.
- Medição da bateria: divisor 100 kΩ / 22 kΩ + 100 nF.

## Pinagem — opção A: ESP32-WROOM (DevKit), preferida se existir
- Mux: SIG 36 (ADC1), S0–S3 25/26/27/14; enable LEDs IR 15 (se a barra tiver).
- Bateria: 39 (ADC1).
- TB6612: PWMA 23, AIN1 22, AIN2 21 (esquerdo); PWMB 19, BIN1 18, BIN2 5 (direito); STBY 17 com pull-down 10 kΩ.
- ESC 16 (pull-down 10 kΩ); botão 4 (pull-up interno); partida/arrancador 13; LED de status 2.
- Reservados para encoders futuros: 34, 35, 32, 33.
- Não usar: 0, 1, 3, 6–11, 12.
- Nesse caso, o C3 Super Mini vira a ponte ESP-NOW no notebook.

## Pinagem — opção B: ESP32-C3 Super Mini (13 GPIOs para 13 funções; tabela completa em HARDWARE.md)
- SIG 0, bateria 1 (ADC1); S0 2 (pull-up 10 kΩ), S1 3, S2 21, S3 8.
- TB6612 com 4 pinos: PWMA, PWMB e STBY no 3,3 V; AIN1 5, AIN2 6 (pull-down 10 kΩ: o GPIO6 tem pull-up interno no reset e faria o motor esquerdo girar no boot), BIN1 7, BIN2 10 (mesmo lado da placa).
- ESC 4 (pull-down 10 kΩ); botão = BOOT (9); arrancador 20 (divisor 10 k/15 k se o módulo for 5 V; o C3 não tolera 5 V).
- Concessões: sem encoders, sem enable dos LEDs IR, sem LED de status livre. Para liberar um pino, medir a bateria por um canal livre do mux.
- Cuidados: núcleo único (rádio quieto durante a volta); em muitas versões o 5 V vai direto ao USB sem diodo (não ligar USB com a bateria conectada); LEDs IR da barra no 5 V, se ela permitir.
- Firmware por OTA Wi-Fi em "modo oficina" (Wi-Fi ligado, motores desligados ao ligar); a primeira gravação é por cabo e todo firmware novo mantém o OTA. Se o rádio da Super Mini falhar, reduzir a potência de transmissão para 8,5 dBm.

## Recomendado (a confirmar)
- Firmware protege a TB6612: rampa no PWM e reversão limitada (no El Barto o PID nunca inverte roda; o freio inverte só a 100/255).
- Normalizar o PWM pela tensão da bateria; corte por volta de 3,5 V/célula; recusar partida abaixo de ~10,5 V em repouso.
- Parâmetros e telemetria por ESP-NOW (ESP32 ponte no notebook), salvos em Preferences; durante a volta, só telemetria e parada.
- Velocidade base reduzida pelo erro + freio nas bordas (estilo El Barto).
- Projeto no EasyEDA Pro, módulos em barra de pinos.

## Estimativa contra o El Barto (11/10)
- Massas estimadas: El Barto ~105 g (bateria 18,2 g); este robô ~120 g sem bateria, ~210 g com a Zippy, ~165 g com uma bateria de 45 g.
- Turbina: ~110 g de empuxo estimado em 3S contra 66 g da EDF27 em 2S. Motores: 2,5–4× a potência dos dele (N20 a ~11 V contra Pololu a ~5,5 V efetivos), se o XL6009 dele não elevar a tensão dos motores.
- Resultado: com a Zippy, empate técnico (3–5% mais lento nas curvas, mais rápido nas retas); com bateria de ~45 g, tende a ser mais rápido. A sintonia decide.
- Para refinar: pesar as peças e medir o empuxo da turbina em 3S numa balança.

## Referências
- **El Barto**: Arduino Nano, TB6612 (STBY ligado ao VCC), Pololu 10:1 HPCB 6 V, LiPo 2S 300 mAh (18,2 g), EDF27 10000 KV (5,2 A e 66 g a 7,4 V), barra de 16 sensores com MUX, XL6009 (função a confirmar), módulo de arranque, duas chaves deslizantes (lógica+motores e turbina) na linha de potência, botão com pull-up de 10 kΩ. Barra curva bem à frente do eixo; turbina entre os motores. Código: posição binária ponderada 0–1500 (setpoint 750); KP 0,18, KD 4, KI 0,002 (integral = soma dos últimos 6 erros); vel. base 180/255; freio quando a linha chega aos sensores das pontas; turbina a 1800 µs; para pelo pino GO do módulo de arranque.
- **Line-Follower-Turbo** (MichalisPapa19): Nano, 16× QRE1113 + CD74HC4067, EDF 30 mm 7000 KV, 2× TB6612 (provavelmente canais paralelados; não confirmado no Gerber).
- **Semreh (TamanduTech/UFABC)**: N20 Pololu 6 V 3000 rpm em 3S sem regulador, com TB6612; a TB6612 só desarmava com os coreless 1020, trocada por ponte H própria (RZ7886).

## Armadilhas ao portar o código do El Barto para o ESP32
- Divisão por zero quando nenhum sensor vê a linha: no AVR dá -1 e o código depende disso; no ESP32 clássico trava; no C3 (RISC-V) dá -1 por coincidência, mas é comportamento indefinido em C. Tratar `suma == 0` sempre.
- `frenos()` é sobrescrito por `PID()` no mesmo ciclo e só funciona por causa do tempo de leitura (~2 ms no Nano). Fazer o freio como `if/else` explícito.
- A calibração guarda só a última amostra: usar mínimo e máximo por sensor.
- Posição binária: usar média ponderada analógica (12 sensores dão só 12 posições binárias).
- PWM do Timer2 e biblioteca ESC são do AVR: usar LEDC no ESP32.

## Pendências
- Regulamento TRIF: dimensões, peso, partida/parada, marcadores, comunicação sem fio, chaves obrigatórias.
- Qual placa vai no robô (DevKit WROOM ou C3 Super Mini).
- Pinagem e tensão do conector da barra; se os LEDs IR têm alimentação separada.
- Tensão do arrancador (3,3 V ou 5 V).
- Distância barra–eixo: escolher na pista com os braços impressos (furos a cada 5 mm, de 50 a 185 mm da linha dos furos da frente; começar no de 100, que deixa os sensores do centro onde ficam os do El Barto: ≈ 110 mm, ≈ 165 mm do eixo). Detalhes em `HARDWARE.md`.
- Função do XL6009 no El Barto.

## Próximos passos
1. Primeira energização com rodas fora do chão: conferir que nenhum motor dá tranco no boot.
2. Bancada em 3S: corrente de partida do N20 travado (< 1 s; acima de 3,2 A a rampa é obrigatória), zigue-zague e reversões fortes com a mula no chão, temperatura da TB6612; corrente e empuxo da turbina.
3. "Mula" com módulos ligados por fio: calibração, posição, PID com ajuste sem fio.
4. PCB definitiva (que também é o chassi).
