# Firmware

Baseado no firmware [EVA-RT 1.2.2](../referencias/eva-rt/source_code/EVA-RT_1.2.2/) (© 2025 EXOTIC TEAM MX, AGPL-3.0). Mesmo mapa de pinos, mesmo jeito de usar (2 botões, 3 LEDs) e os mesmos valores de partida (velocidade 40, ventoinha 180, KP 0,06).

| Pasta | Conteúdo |
|---|---|
| `seguidor/` | firmware do robô (ATmega328P-AU, 16 MHz). Abrir `seguidor.ino` na IDE do Arduino |
| `testes/` | simulador no PC que roda o mesmo código de controle em pistas (ensaio curto + modelos TRIF 2025 e 2024) |
| `teste_barra/` | teste de bancada da barra V1 no ESP32-C3 (referência da leitura; não vai no robô) |

**Estado: compila e passa no simulador; ainda não rodou no robô.** Os ganhos e o freio só se acertam na pista.

## Gravar
IDE do Arduino → abrir `seguidor/seguidor.ino` → placa "Arduino Nano" (ATmega328P; "Old Bootloader" se o chip veio de um Nano antigo) ou "Arduino Uno", conforme o chip doador → gravar pelo conector de 5 vias. Serial e Bluetooth em 115200. Ocupa 18,9 kB de flash e 1 kB de RAM.

## Uso
| Situação | LEDs | Botão 1 | Botão 2 |
|---|---|---|---|
| Ligar com um botão apertado | piscam 2× | teste das rodas | liga/desliga a ventoinha |
| Esperando | C pisca devagar | calibrar | usar a calibração gravada |
| Calibrando | C pisca rápido | terminar | — |
| Pronto | A, B = sensores de marca; C = barra vê a linha | largar em 1 s (segurar: calibrar de novo) | sobe um nível (segurar: nível 0) |
| Correndo | A, B = marcas; C = acima da velocidade de curva | desliga | desliga |
| Fim | A+B acesos = chegada; C piscando = perdeu a linha; os três piscando = botão ou tempo | volta para "pronto" | volta para "pronto" |

- **Calibração:** passar pela linha a barra inteira **e os dois braços** (sensores de marca). Rejeitada se faltar contraste na barra (LED C pisca) ou na marca direita (LED B); sem a marca esquerda segue, só com aviso (LED A). Fica gravada na EEPROM: nas tentativas seguintes basta o botão 2.
- **Nível:** cada toque soma 5 no PWM das rodas e 14 no da ventoinha, como no EVA-RT.
- **Largada:** colocar o robô sobre a linha com o sensor direito **antes** da marca de partida. A primeira marca da direita é a partida; a segunda, a chegada (`nmarcas`).
- Depois do fim, qualquer botão volta para "pronto" com a mesma calibração e o mesmo nível: dá para fazer as 3 tentativas sem reset.

## Conferir na bancada, nesta ordem
1. **Canais da barra:** console `r`. Passando a mão, devem variar 12 dos 16 canais; conferir com o `MAPA_MUX` do `config.h` (ver o aviso lá: o teste de bancada usou 4–15, o Gerber da V1 indica 2–13).
2. **Rodas:** ligar com um botão apertado, botão 1. A sequência é esquerda para a frente, esquerda para trás, direita para a frente, direita para trás (LED A = esquerda, LED B = direita, LED C = para trás). Se não bater, mudar `INVERTER_MOTOR_*` / `TROCAR_MOTORES` no `config.h` ou inverter os fios.
3. **Lado da barra:** calibrar e usar o console `s`. Com a linha sob a ponta **esquerda** do robô, quem acende é a primeira coluna e o erro é **negativo**. Se estiver ao contrário, `BARRA_ESPELHADA 1`.
4. **Marcas:** em "pronto", o LED A acende com branco sob o sensor esquerdo e o B sob o direito.
5. **Bateria:** console `?` mostra a tensão. Ajustar `batcal` até bater com o multímetro (`batcal` novo = `batcal` × tensão real / tensão mostrada).
6. Primeira volta no nível 0, com a mão perto do robô.

## Console (serial ou Bluetooth, só com o robô parado)
`?` estado · `p` lista · `nome=valor` muda · `salvar` grava na EEPROM · `padrao` valores de fábrica · `s` sensores ao vivo · `r` canais brutos · `res` resumo da última tentativa · `log` últimos 2,4 s em CSV · `motores` teste das rodas

| Parâmetro | Padrão | O que é |
|---|---|---|
| `kp`, `kd` | 0,06 / 0,40 | PD. Erro em milésimos de sensor (1000 = 7,8 mm); `kd` por ms |
| `fd` | 50 | filtro da derivada (% da leitura nova; 100 = sem filtro, como no EVA-RT) |
| `vel` | 40 | PWM nas curvas fechadas, nível 0 |
| `reta` | 10 | PWM a mais nas retas (0 = velocidade única, como no EVA-RT) |
| `passo`, `vent`, `vpasso`, `nivel` | 5 / 180 / 14 / 0 | aumento por nível, ventoinha, nível ao ligar |
| `ecurva` | 600 | erro que indica entrada de curva: volta para `vel` na hora |
| `treta` | 60 | ms com o erro quieto para poder passar de `vel` |
| `rreta`, `rcurva` | 15 / 40 | curvatura (diferença entre as rodas em % do PWM): até `rreta` anda em `vel + reta`, de `rcurva` em diante em `vel`, no meio proporcional |
| `acel` | 300 | PWM por segundo ao acelerar (também é a rampa da largada) |
| `fcurva`, `tfcurva` | 100 / 40 | freada ao baixar a velocidade: % da queda aplicada a mais, por uns `tfcurva` ms |
| `re` | 255 | ré máxima da roda de dentro |
| `perdido` | 100 | ms sem ver a linha até desligar (EVA-RT: 10) |
| `cruz` | 300 | ms em que, depois de um cruzamento na barra, o próximo pulso de cada sensor de marca é descartado |
| `nmarcas`, `tminvolta`, `tmax` | 2 / 2000 ms / 120 s | marcas da direita até parar; tempo mínimo de volta; tempo máximo |
| `freio`, `tfreio` | 100 / 75 | ré na chegada: % do PWM em que vinha, por `tfreio` ms (EVA-RT: −SPEED por 75 ms) |
| `comp`, `vref`, `batcal`, `batmin` | 1 / 7600 / 588 / 7000 | compensação do PWM pela bateria; tensão de referência (mV); ajuste do divisor; aviso de bateria baixa |

## Ajuste na pista
1. `reta=0`, nível 0: acertar `kp`/`kd` até seguir sem balançar (balança rápido → menos `kp` ou mais `kd`; demora a entrar na curva → mais `kp`).
2. **Parada:** se o robô voltar para trás depois da chegada, diminuir `tfreio`; se passar da área (1 m), aumentar. Conferir de novo ao subir de nível.
3. Subir o nível (botão 2) até o limite das curvas fechadas.
4. Subir `reta` aos poucos. O resumo (`res`) mostra a % do tempo acima da velocidade de curva; se ficar perto de 0, aumentar `ecurva`.
5. `salvar`.

## O que muda em relação ao EVA-RT 1.2.2
| EVA-RT | Aqui | Para quê |
|---|---|---|
| laço livre (derivada depende do tempo do laço) | ciclo fixo de 1 ms; contas em ponto fixo | derivada e tempos previsíveis |
| média ponderada dos 12 sensores, limiar de 75 % | média só do grupo de sensores em cima da linha, com calibração por sensor | a marca lateral ou um reflexo na ponta da barra não puxam a posição |
| velocidade única | mais rápido nas retas e nas curvas abertas; freada na entrada de curva | tempo de volta (no simulador, 10–16 % com `reta=10`) |
| roda satura em 255 e perde a diferença | tira das duas rodas para manter a diferença | curva fechada em nível alto |
| PWM direto | PWM compensado pela tensão da bateria (A7) | mesmo comportamento com a bateria cheia ou no fim |
| cruzamento: erro = 0 se os sensores 2 e 9 veem branco | erro de antes de a faixa entrar; faixa descartada nos sensores de marca | cruzamento torto não desvia nem conta como marca |
| para na 1ª marca direita depois de 1 s | conta partida e chegada; marca só vale se o outro lado não viu branco junto | não parar na marca errada |
| saiu da linha: ±255 por 10 ms e desliga | continua virando para o lado em que a linha saiu por `perdido` ms | recuperar uma escapada curta |
| parâmetros em `#define` | console serial/Bluetooth e EEPROM; calibração gravada | ajustar entre tentativas sem regravar |
| laço infinito no fim | volta para "pronto" | 3 tentativas seguidas |
| — | resumo e registro da tentativa (`res`, `log`) | saber o que aconteceu |

Não mudou: ADC em 8 bits a 1 MHz, PWM dos motores pelo `analogWrite` (976 Hz), limites do comando (±510), ré na roda de dentro, incrementos de nível.

## Simulador (`testes/`)
```
cd firmware/testes
g++ -O2 -std=c++11 -I../seguidor sim.cpp ../seguidor/linha.cpp ../seguidor/corrida.cpp -o sim && ./sim
```
Roda `linha.cpp` e `corrida.cpp` (os mesmos arquivos do robô) com um robô simulado: barra em arco a 104 mm do eixo, sensores de marca em x = ±69,5 mm. Confere largada, curvas R100–R300, cruzamento (reto e a 85°), marcas, parada, perda da linha e uma volta completa nos modelos **TRIF 2025 e 2024** do estudo de caso (`pistas/*.txt`, exportados por `exportar_pistas.py`), com três motores diferentes e com sensores desiguais. Termina com "tudo certo" ou lista o que falhou.

O modelo dos motores é inventado (velocidade proporcional ao PWM, atraso de primeira ordem, sem escorregar): serve para conferir a lógica e comparar estratégias, **não** para escolher ganhos nem prever tempo de volta. O número de marcas esquerdas lidas (20–22 de 31–33) bate com o estudo geométrico: é limite da posição dos sensores, não do firmware, e o firmware não depende delas.

Tempo de um ciclo medido no `simavr` (ATmega328P, 16 MHz): leitura dos 14 sensores 372 µs + controle 210–235 µs + saídas 17 µs. O console `res` mostra o maior ciclo e quantos passaram de 1 ms no robô.

## Pendências
- Tudo acima precisa ser confirmado no robô: mapa do mux, sentido das rodas, lado da barra, ganhos, freio.
- A barra fica ~104 mm à frente do eixo (60 mm entre furos). Em curva de R100 ela fica quase paralela à linha e vê uma faixa larga; o firmware trata isso, mas a leitura da posição perde resolução ali. Com a barra mais perto do eixo o efeito diminui.
- PWM dos motores em 976 Hz, como no EVA-RT. Frequência mais alta exigiria tirar o `millis()` do Timer0; não foi mexido.
