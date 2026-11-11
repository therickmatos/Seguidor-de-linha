# Pinos dos 4 QRE de marca (11/11/2026)

Continua o [estudo da asa de gaivota](README.md). Baseado no EVA-RT, © EXOTIC TEAM MX, [AGPL-3.0](../LICENSE).

## Proposta

| Sensor | Posição (mm) | Pino | ATmega328P-AU (TQFP) | Leitura |
|---|---|---|---|---|
| **E2** (externo esquerdo) | (−81,5; 16) | **A5** | pino 28 (PC5/ADC5) | analógica, como hoje (`MARK_L_A5`) |
| **D2** (externo direito) | (+81,5; 16) | **A6** | pino 19 (ADC6) | analógica, como hoje (`MARK_R_A6`) |
| **E1** (interno esquerdo) | (−50,5; 14) | **D8** | pino 12 (PB0) | digital |
| **D1** (interno direito) | (+50,5; 14) | **D9** | pino 13 (PB1) | digital |

- **Mapa do EVA-RT 1.2.2 mantido:** A5 e A6 continuam sendo os sensores de marca do firmware original, agora ligados ao par externo. Sem mudar uma linha do firmware, o robô funciona como o EVA-RT: D2 para na chegada e E2 veta a parada nos cruzamentos. Os internos ficam prontos para o firmware novo.
- **D8 e D9 são os únicos pinos livres:** conferido no `.epro` da v3, pinos 12 e 13 sem rede. As entradas analógicas já estão todas ocupadas: A0–A3 seleção do mux, A4 saída do mux, A5/A6 marcas, A7 bateria.

## Por que os externos ficam nas entradas analógicas

O script [`codigo/firmware_pares.py`](codigo/firmware_pares.py) emula o `Marks.ino` do 1.2.2 com cada par ligado em A5/A6. A emulação é a mesma do [estudo 07](../07_firmware_e_geometria/README.md): parada na borda de subida do sensor direito, veto se o esquerdo subir dentro de 30 ms. Foram testadas as janelas de 10, 30 e 60 mm (velocidade × 30 ms, ~0,3 a 2 m/s), com a barra a 63,14 e 65 mm entre furos e nos cenários ideal, ±3 mm e "abre" 10–30 mm.

| Par em A5/A6 | TRIF 2025 | TRIF 2024 | Pista de teste do EVA-RT* |
|---|---|---|---|
| **Externos E2/D2** | para na chegada em todos os casos | para na chegada em todos os casos | paradas falsas (linha e cruzamentos oblíquos) |
| Internos E1/D1 | **paradas falsas**: D1 passa sobre a linha nas curvas fechadas à esquerda (ideal e +3 mm, janelas de 10–30 mm) | para na chegada | paradas falsas em todos os casos |

\* A pista de teste do EVA-RT não é regulamentar: tem laços, trechos a menos de 200 mm entre si e cruzamentos que não são a 90°. O estudo 07 já mostrava paradas falsas nela com o próprio EVA-RT no modelo ideal. Ela não entrou no critério.

Isso confirma o que a geometria indicava: D2 nunca encosta na linha (folga ≥ 11 mm, inclusive no grampo R100), e D1 encosta. No lado direito só há partida e chegada, sempre em reta, e D2 lê as duas com folga. **D1 não deve disparar a parada**; ele serve para confirmar cruzamentos ou pode ficar sem montar.

## Leitura digital em D8/D9: o que conferir antes

Na v3, cada QRE tem o LED com 220 Ω e o fototransistor com coletor no +5 V e emissor na saída, com 47 kΩ para o GND: branco dá tensão alta, preto dá tensão baixa. Em D8/D9 a leitura é digital, com Schmitt trigger no AVR. A 5 V, garante-se nível **baixo abaixo de 1,5 V** e **alto acima de 3,0 V**. Não há calibração como no ADC, então o sinal precisa cair claramente fora da faixa de 1,5 a 3,0 V.

O preto do tapete reflete pouco, mas não zero, e com 47 kΩ uns 30 µA já dão 1,4 V. Antes de fechar a placa, vale medir na v3 atual, na altura de corrida e com a ventoinha ligada, sobre o preto e o branco da pista:

```cpp
// Teste rápido: Serial Monitor a 115200. Mova o robô entre o preto e o branco.
void setup() { Serial.begin(115200); }
void loop() {
  int e = analogRead(A5), d = analogRead(A6);          // 0..1023 → 0..5 V
  Serial.print(e * 5.0 / 1023); Serial.print(" V  ");
  Serial.print(d * 5.0 / 1023); Serial.println(" V");
  delay(100);
}
```

- **Preto < ~1,0 V e branco > ~3,5 V:** os 47 kΩ servem também para D8/D9.
- **Preto entre 1 e 1,5 V:** usar resistor menor nos internos, por exemplo 22 kΩ. Isso baixa as duas tensões; conferir que o branco continua acima de 3,5 V.
- **Branco abaixo de 3,5 V:** usar resistor maior nos internos.

Para poder ajustar depois da placa pronta, deixar o resistor de emissor dos internos em 0603 com acesso fácil.

**Opcional, para testar na pista:** um jumper de solda de 3 pads por lado, para escolher qual sensor do lado (interno ou externo) vai no analógico e qual no digital. Custa 2 jumpers e um pouco de roteamento na raiz da aba. Dá para trocar o par do A5/A6 sem refazer a placa, caso os testes físicos contrariem o modelo.

## Para o pedido de hoje (recomendação)

Mesmo circuito da v3 nos 4 sensores, com **um capacitor a mais, não montado (DNP), em cada interno**:

| Por sensor interno (E1 → D8, D1 → D9) | Ligação |
|---|---|
| QRE1113GR | 1 anodo → 220 Ω → +5V; 2 catodo → GND; 3 coletor → +5V; 4 emissor → rede `MARK_L2_D8` / `MARK_R2_D9` |
| 47 kΩ (0603) | rede do sensor → GND (montar) |
| 10 nF (0603), **DNP** | rede do sensor → GND (só pads) |

- **Montado assim (47 kΩ, sem capacitor):** leitura digital simples, `digitalRead`.
- **Se a leitura no preto ou no branco ficar duvidosa:** retirar o 47 kΩ (ou trocar por ~1 MΩ) e soldar o 10 nF. O firmware descarrega o capacitor pondo o pino em LOW, passa o pino a entrada e mede quanto tempo o fototransistor leva para levá-lo a HIGH. No branco são dezenas a centenas de µs; no preto o tempo passa de ~1 ms (timeout = preto). Assim se tem um valor contínuo, que pode ser **calibrado como o analógico**, sem trocar a placa.
- Os pads extras ficam na mesma rede, sem mudar a topologia. Colocar o 47 kΩ e o capacitor perto do pino do ATmega ou na raiz da aba, com acesso para o ferro.
- Sem jumper de troca entre analógico e digital: a geometria e a emulação apontam com clareza para os externos no A5/A6, e o jumper só complica o roteamento.

## O que muda no esquemático (fonte: `ferramentas/esquematico/gen.py`)

- S0/S1, os QRE atuais de `MARK_L_A5`/`MARK_R_A6`, passam a ser os externos E2/D2. A mudança é só de posição no layout, sem mudança elétrica.
- **Novos:** dois QRE1113GR, cada um com o mesmo circuito dos atuais (220 Ω no LED, 47 kΩ no emissor). Saídas em novas redes `MARK_L2_D8` (U1.12, PB0) e `MARK_R2_D9` (U1.13, PB1). Essas redes saem da lista de pinos sem ligação.
- Os LEDs indicadores das abas (LED A em D2 e LED B em D7) continuam como estão. O firmware 1.2.2 os usa para mostrar o estado de A5/A6.

## Firmware (fase seguinte)

- **Pinos novos:** D8 e D9 ficam no mesmo registrador (`PINB & 0b11`). A leitura custa um ciclo, e as bordas podem ser pegas por interrupção de mudança de pino (PCINT0/PCINT1) para medir o tempo com precisão.
- **Timer1:** D9 é o OC1A do Timer1, que gera o PWM da ventoinha no D10 (OC1B). Como entrada não há conflito, desde que o firmware não ligue a saída OC1A.
- **Lógica a definir:** marca de curva = E1 **ou** E2, contada uma vez; parada = só D2, como no 1.2.2. Ignorar E1/D1 enquanto a barra indicar curva fechada, porque é aí que eles podem ver a linha principal.
