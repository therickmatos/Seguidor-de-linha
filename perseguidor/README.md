# Perseguidor — RUSH - Dreamcast

Placa do perseguidor feita a partir da placa do seguidor **RUSH - Saturn** (versão final, validada eletricamente). Dele vêm o esquemático e o roteamento. Do **RUSH perseguidor - entalhe A** vêm o contorno (100 × 58,6 mm) e o receptor IR.

Unidades em mm. A origem fica no centro da ventoinha, com +y para a frente.

![PCB do Dreamcast](figuras/dreamcast_pcb.png)

## Arquivos
| Arquivo | O que é |
|---|---|
| `RUSH - Dreamcast.epro` | projeto EasyEDA Pro gerado (esquemático + PCB) |
| `origem/RUSH - Saturn - Final.epro` | seguidor validado (base) |
| `origem/RUSH perseguidor - entalhe A.epro` | perseguidor anterior (contorno e J6) |
| `ferramentas/gerar_dreamcast.py` | gera o `.epro` a partir dos dois de `origem/` |
| `ferramentas/conferir_netlist.py` | compara as ligações do esquemático com as redes do PCB |
| `ferramentas/figura_pcb.py` | figura de conferência do PCB |

Para regenerar (precisa de `shapely` e `matplotlib`):
```bash
python3 perseguidor/ferramentas/gerar_dreamcast.py
```
```bash
python3 perseguidor/ferramentas/conferir_netlist.py "perseguidor/RUSH - Dreamcast.epro"
```

## O que mudou em relação ao Saturn
**Esquemático** (bloco 3, agora "LEDS DAS PONTAS E RECEPTOR IR")
- Saíram os 4 sensores de marca e o que era só deles: S1–S4, R4, R5, R7, R8, R23–R26, C19 e C20.
- Ficaram LED2/R6 (LED A, D2) e LED3/R9 (LED B, D7).
- Entrou o J6 (barra fêmea 1×3 para o KY-022: 1 = S, 2 = +5V, 3 = GND), na rede IR_A5 (pino 28, A5).
- A6 (pino 19), D8 (12) e D9 (13) ficaram marcados como sem ligação.
- O resto não mudou, inclusive R14/R15 = 910 Ω (ver ITRIP abaixo).

**PCB**
- O contorno agora é o do Rush (entalhe A). Furos, pours e o restante do miolo são os do Saturn.
- Foram apagados os componentes, redes, trilhas e vias dos sensores de marca, e tudo que ficava fora do novo contorno. Também saíram as trilhas que ficaram penduradas depois do corte e as ilhas de cobre sem pad.
- **LEDs nas pontas da frente:** LED2/LED3 em cima em (±48,3; 11,0); R6/R9 embaixo em (±46,2; 11,0). A ligação é LED → via → resistor, e o D2/D7 desce pela face de baixo em x = ±45,74 até o resistor. O R9 foi girado igual ao R6, deixando os dois lados espelhados.
- **J6 em (−40,7; 4,04)**, pinos em y = 1,5 / 4,04 / 6,58. A posição do Rush (−37,6; 7,6) não serve aqui, porque no Saturn o U1 (78M05) está girado e a aba de GND ocupa esse lugar.
  - A5: reaproveita a trilha do antigo MARK_L_A5 até (−43,18; 1,5) e segue reta até o pino 1. O desvio pela face de baixo, que contornava o D2, saiu.
  - +5V: sai do trecho que ia para o braço esquerdo, desce em x = −39,4 (entre o J6 e a aba do U1) e chega no pino 2.
  - GND: pelo pour.
- Os preenchimentos de cobre (POURED) foram apagados e **precisam ser refeitos** no EasyEDA.

**Conferências feitas no script**
- Esquemático × PCB: as 50 redes com 2 ou mais pinos são iguais. No Saturn original, a mesma conferência dá 57 = 57.
- Conectividade: todas as redes ficam numa ilha só, menos o GND, que se fecha pelos pours, como no Saturn.
- Folga: nenhum par novo abaixo de 0,15 mm. A menor folga dos itens novos é 0,25 mm (J6.3 × +5V); a regra do projeto é 0,2 mm.

## Para conferir no EasyEDA Pro
1. Abrir o `.epro` e refazer todos os pours (Shift+B). Confirmar que LED2.1, LED3.1 e J6.3 (GND) pegaram o pour.
2. Rodar o DRC.
3. Rodar "Atualizar PCB a partir do esquemático": não deve aparecer nenhuma diferença.
4. Conferir no 3D, com os STL:
   - o J6 e o módulo KY-022 em relação à vareta e às presilhas (x = −43,75; y = −1,75 e 10,75). O corpo da barra fêmea fica entre x −41,97 e −39,43;
   - os LEDs das pontas em relação à presilha dianteira.
5. Arrumar as posições dos designadores na serigrafia, se for preciso.

## Em aberto
- **ITRIP (R14/R15):** com VREF = 2,0 V (15k/10k) e A_IPROPI = 450 µA/A (típico do DRV8874), ITRIP = 2,0 / (R × 450 µA/A):

  | R | ITRIP |
  |---|---|
  | 1,5 kΩ | 2,96 A |
  | 910 Ω (atual) | 4,88 A |
  | 820 Ω | 5,42 A |
  | 806 Ω (E96) | 5,51 A |

  Para o limite de 5,5 A, confira a tolerância do A_IPROPI no datasheet antes de escolher.
- **Firmware:** o IR fica no A5 (PC5/PCINT13), onde o EVA-RT 1.2.2 lê o sensor de curva pelo ADC. A leitura do receptor IR precisa ser escrita.
- Nome na serigrafia: a placa mantém o logo do IFSP e "Projetado por Erick Matos". Não há nome do robô na serigrafia.
- Já existe no Saturn um toco de trilha de 0,78 mm, inofensivo, na rede LEDC_D13 (face de baixo, x = 13,07; y = 3,3 a 4,1). Foi mantido; pode ser apagado nas duas placas.

Baseado no RUSH - Saturn, derivado do [EVA-RT](https://github.com/EXOTIC-TEAM-MX/EVA-RT) (© EXOTIC TEAM MX), AGPL-3.0.
