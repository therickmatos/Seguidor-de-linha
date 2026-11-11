# Perseguidor de linha (RUSH – SATURN, entalhe A)

Placa do perseguidor = placa do seguidor **sem os braços dos sensores de marca**, com o receptor IR **KY-022** para a partida.
Baseado no EVA-RT (© EXOTIC TEAM MX, AGPL-3.0). Origem no centro da ventoinha, +y para a frente, mm.

| Arquivo | Conteúdo |
|---|---|
| `RUSH_perseguidor_entalhe_A.epro` | projeto EasyEDA Pro (esquemático + PCB) com o J6 (KY-022) já roteado. A versão anterior, sem o J6, está no histórico do git |
| `figuras/perseguidor_J6_zoom.png` | J6 e as rotas novas (vermelho = cima, azul = baixo) |
| `figuras/perseguidor_placa.png` | placa inteira, as duas camadas |
| `../ferramentas/perseguidor/` | scripts usados na revisão (leitura do `.epro`, DRC, roteador, simulação do polígono de GND) |

Observação: a placa do perseguidor saiu de uma versão do seguidor anterior à v4 (posições e rotas iguais às do SATURN v3, menos os braços). Correções feitas na v4 do seguidor não estão aqui.

## Receptor IR (J6, KY-022)
- **Barra fêmea 1×3, 2,54 mm, vertical**, na frente esquerda: coluna em **x = −37,6; y = 5,08 / 7,62 / 10,16** (pino 1 atrás).
- **Pinagem: 1 = S (sinal) → A5 (PC5, pino 28 do ATmega); 2 = +5V; 3 = GND.** A serigrafia mostra `S`, `+` e `−` ao lado dos furos.
- Rotas: +5V em 0,5 mm direto do pino 3 do 78M05 (U1); sinal em 0,25 mm desde o pino 28 do ATmega, com 2 vias; GND pelos polígonos (cima e embaixo).
- **Por que o A5 e não o D2:** o firmware EVA-RT 1.2.2 configura D2 e D7 como **saída** (LEDs A/B, `DDRD |= 1 << DDD2` no `setup`). Com o receptor no D2, a saída do microcontrolador brigaria com a saída do VS1838B. O A5 o firmware só lê pelo ADC (nunca põe como saída) e ficou livre sem os braços. Qualquer pino serve para a biblioteca IRremote (usa o Timer2, que o firmware não usa); o A5 é o pino digital 19 no Arduino.
- **Posição:** fora da placa de sucção (|x| > 23,1), à frente da caixa de redução (que vai até y ≈ −1,7), longe das presilhas da vareta (x = ±43,75) e da carcaça da ventoinha. O módulo fica em pé (~8,5 mm da barra + a placa do KY-022), com o receptor virado para o lado (±x).
- **Conferir antes de soldar:** a ordem dos pinos do KY-022 varia entre fabricantes (o comum é `S`, meio = `+`, `−`). Encaixe com o `S` do módulo no `S` da placa. Invertido (S↔−) não queima nada se o A5 estiver como entrada, mas não funciona.
- O footprint novo não tem modelo 3D: na conferência 3D, o módulo não aparece.

## Revisão: o que foi conferido
Feita lendo o `.epro` direto (pads, trilhas, vias, polígonos, furos e contorno), com o mesmo espelhamento que o EasyEDA usa nos componentes da face de baixo (conferido pelos próprios polígonos calculados pelo EasyEDA).

| Verificação | Antes | Depois do J6 |
|---|---|---|
| Redes abertas | 0 | 0 |
| Curtos | 0 | 0 |
| Folga cobre–cobre < 0,2 mm | 0 | 0 (rotas novas com ≥ 0,25 mm) |
| GND ligado pelos polígonos (simulados) | sim | sim, incluindo o J6.3 |

Mudanças no projeto:
- J6 no esquemático (bloco 7 – INTERFACE) e na PCB, com símbolo e footprint próprios.
- Rede do pino 28 renomeada de `MARK_L_A5` para `IR_A5` (o bloco 3 – sensores de marca continua no esquemático como estava, sem ir para a PCB).
- **O preenchimento dos polígonos de GND foi apagado** (estava desatualizado e encostaria nas trilhas novas).

## Para terminar no EasyEDA Pro
1. Abrir o `.epro` e **reconstruir todos os polígonos** (Shift+B ou botão direito no polígono → reconstruir).
2. Rodar o DRC.
3. Conferir na vista 3D e na camada de montagem inferior os pontos abaixo, principalmente o J3.

## Erros e pontos de atenção encontrados
1. **J3 (gravação, barra deitada na face de baixo) provavelmente está com o corpo virado para dentro da placa.** No footprint, o corpo plástico fica do lado −y dos pads (para sair pela borda traseira). Ao ir para a face de baixo, o EasyEDA espelha o footprint em y, então o corpo cai em y ≈ −27,4…−24,9, **embaixo da placa de sucção**, e os pinos apontam para o centro da placa. **Isso também vale para o seguidor (SATURN v3)**, que usa o mesmo J3 na mesma posição. Conferir na vista 3D ou na camada Bottom Assembly; se confirmar, girar o J3 em 180° (os pads ficam no mesmo lugar, mas a ordem dos pinos inverte: refazer as 5 rotas).
2. **ICSP (J5) girado 180° em relação ao EVA-RT** (mesma causa). Na placa: x = 33,98 → RESET (y −8,36), SCK (−10,90), MISO (−13,44); x = 36,52 → GND (−8,36), MOSI (−10,90), +5V (−13,44). As posições batem com o EVA-RT, mas a função de cada pad não. Usando fios, basta seguir esta tabela; um gabarito feito pela pinagem do EVA-RT ligaria +5V no RESET.
3. **C1 e C2 (220 µF, com furo) ficam dentro da área da placa de sucção** (x ±23,1; y −27,5…21). Os terminais e a solda saem embaixo, onde a placa de sucção encosta. Cortar rente e conferir se a placa de sucção assenta; ou trocar por eletrolítico SMD de 6,3 mm.
4. **Sem LED A e LED B** (D2/D7): no perseguidor só sobrou o LED C (D13), além do TX e do LED de 5 V. As indicações do firmware nos LEDs A/B não aparecem (só um aviso; não é erro de placa).
5. Firmware do perseguidor: **não usar o D2/D7 como saída se algo for ligado neles no futuro**, e ler o receptor no A5 (`pinMode(A5, INPUT)`; o VS1838B já tem pull-up interno).
6. Sugestão (não feita): se a partida falhar com a ventoinha ligada (ruído no 5 V), um 100 nF entre +5V e GND junto do J6 ajuda.

As trilhas dos motores afinam para 0,4 mm só no trecho de saída dos pinos do DRV8874 (passo de 0,65 mm, menos de 2 mm de comprimento); isso é normal e não foi mudado.
