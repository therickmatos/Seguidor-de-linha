/*
  seguidor - firmware do seguidor de linha (ATmega328P-AU, 16 MHz)

  Baseado no EVA-RT v1.2.2 (c) 2025 EXOTIC TEAM MX
  https://github.com/EXOTIC-TEAM-MX/EVA-RT

      DRIVERS:            2x DRV8874 (PH/EN)
      SENSORES:           barra V1 de 12 QRE1113 + 74HC4067, 2 de marca
      MICROCONTROLADOR:   ATmega328P-AU (mapa de pinos do EVA-RT 1.2.2)
      BATERIA:            2S
      CONTROLE:           PD, ciclo fixo de 1 ms

  Placa na IDE: "Arduino Nano" (ATmega328P) ou "Arduino Uno", conforme o
  bootloader do chip doador. Serial em 115200.

  Uso (2 botoes, 3 LEDs), parecido com o EVA-RT:
    ligar com um botao apertado   modo teste (botao 1 rodas, botao 2 ventoinha)
    LED C piscando devagar        botao 1 = calibrar | botao 2 = usar a calibracao gravada
    calibrando (LED C rapido)     passar a barra e os dois bracos pela linha; botao 1 termina
    pronto (LEDs = sensores)      botao 2 = sobe um nivel (segurar = nivel 0)
                                  botao 1 = larga em 1 s (segurar = calibrar de novo)
    correndo                      qualquer botao desliga
    fim                           A+B acesos = chegada | C piscando = perdeu a linha
                                  qualquer botao volta para "pronto"

  Arquivos:
    config.h      pinos, barra e limiares (compilacao)
    params.h      ganhos e velocidades (console serial, EEPROM)
    linha.*       calibracao, posicao da linha, sensores de marca
    corrida.*     largada, PD, reta x curva, marcas, parada
    hw.*          ADC, mux, motores, ventoinha, LEDs, botoes, bateria
    memoria.*     EEPROM
    console.cpp   comandos pela serial

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU Affero General Public License as published
  by the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Affero General Public License for more details.

  You should have received a copy of the GNU Affero General Public License
  along with this program.  If not, see <https://www.gnu.org/licenses/>.
*/

#include "config.h"
#include "params.h"
#include "linha.h"
#include "corrida.h"
#include "hw.h"
#include "memoria.h"
#include "estado.h"

Parametros P;
Calibracao cal;
bool       temCal = false;
uint8_t    nivelAtual = 0;
Corrida    corrida;
uint16_t   cicloMaxUs = 0;
uint16_t   ciclosAtrasados = 0;

#define TOQUE_LONGO     0x80
#define TOQUE_LONGO_MS  800

// ---------------------------------------------------------------- LEDs e botoes

static void piscar(void (*led)(bool), uint8_t vezes, uint16_t ms) {
  for (uint8_t i = 0; i < vezes; i++) {
    led(true);
    delay(ms);
    led(false);
    delay(ms);
  }
}

// 0 = nada; 1 ou 2 = toque no botao; com TOQUE_LONGO se foi segurado.
// Devolve quando o botao e solto.
static uint8_t lerToque() {
  uint8_t b = hwBotao(1) ? 1 : (hwBotao(2) ? 2 : 0);
  if (!b) return 0;
  delay(20);
  if (!hwBotao(b)) return 0;

  uint32_t t0 = millis();
  bool longo = false;
  while (hwBotao(b)) {
    if (!longo && millis() - t0 >= TOQUE_LONGO_MS) {
      longo = true;
      hwLeds(true);   // avisa que ja pode soltar
    }
  }
  hwLeds(false);
  delay(30);
  return longo ? (b | TOQUE_LONGO) : b;
}

static void avisarBateria() {
  for (uint8_t i = 0; i < 16; i++) hwBateriaAtualizar();
  uint16_t mv = hwBateriaMv(P);
  if (mv > 5500 && mv < P.batmin) {
    Serial.print(F("BATERIA BAIXA: "));
    Serial.print(mv);
    Serial.println(F(" mV"));
    piscar(hwLeds, 4, 60);
  }
}

// ---------------------------------------------------------------- calibracao

// Minimo e maximo de cada sensor. Tem que passar pela linha a barra inteira
// e os dois sensores de marca (os bracos), como no EVA-RT.
static bool calibrar() {
  Calibrador c;
  uint8_t media[N_CANAIS];
  uint8_t k = 0;

  Serial.println(F("calibrando: passe a barra e os dois bracos pela linha; botao 1 termina"));
  hwLeds(false);
  c.iniciar();
  while (!hwBotao(1)) {
    hwLerMedia(media, 4);
    c.amostrar(media);
    hwLedC((++k >> 4) & 1);
  }
  hwLedC(false);
  while (hwBotao(1)) {
  }
  delay(30);

  Calibracao nova;
  uint16_t falha = c.finalizar(nova);
  consoleCalibracao(nova, falha);

  if (falha & (CAL_FALHA_BARRA | CAL_FALHA_MARCA_D)) {
    // LED C = barra, LED B = marca da direita (sem ela o robo nao para sozinho)
    Serial.println(F("REJEITADA: refaca (a calibracao anterior continua valendo)"));
    Serial.println(F("se forem sempre os mesmos sensores, confira o MAPA_MUX com o comando r"));
    for (uint8_t i = 0; i < 6; i++) {
      hwLedC(falha & CAL_FALHA_BARRA);
      hwLedB(falha & CAL_FALHA_MARCA_D);
      delay(150);
      hwLeds(false);
      delay(150);
    }
    return false;
  }
  if (falha & CAL_FALHA_MARCA_E) {
    // a marca da esquerda so e contada: segue sem ela
    Serial.println(F("aviso: marca esquerda sem contraste, sensor desligado"));
    nova.mn[CANAL_MARCA_E] = 0;
    nova.mx[CANAL_MARCA_E] = 0;
    piscar(hwLedA, 6, 150);
  }

  cal = nova;
  temCal = true;
  memSalvarCalibracao(cal);
  Serial.println(F("calibracao aceita e gravada"));
  piscar(hwLeds, 2, 200);
  return true;
}

// ---------------------------------------------------------------- telas

static void telaEspera() {
  Serial.println(F("botao 1 = calibrar | botao 2 = usar a calibracao gravada"));
  while (!temCal) {
    consoleProcessar();
    hwLedC((millis() >> 9) & 1);
    uint8_t t = lerToque() & ~TOQUE_LONGO;
    if (t == 1) {
      calibrar();
    } else if (t == 2) {
      if (memCarregarCalibracao(cal)) {
        temCal = true;
        Serial.println(F("calibracao gravada carregada"));
        piscar(hwLeds, 2, 200);
      } else {
        Serial.println(F("nao ha calibracao gravada para esta barra"));
        piscar(hwLedC, 8, 40);
      }
    }
  }
}

// Fica mostrando os sensores nos LEDs (A e B = marcas, C = barra na linha)
// ate o botao 1 mandar largar.
static void telaPronto() {
  uint8_t bruto[N_CANAIS];

  corrida.preparar(cal);
  consoleNivel();
  avisarBateria();
  Serial.println(F("pronto: botao 1 = largar | botao 2 = sobe o nivel"));

  for (;;) {
    consoleProcessar();
    hwLerSensores(bruto);
    corrida.observar(bruto);
    hwLedA(corrida.marcas().ativa(0));
    hwLedB(corrida.marcas().ativa(1));
    hwLedC(corrida.linha().vista());

    uint8_t t = lerToque();
    if (t == 1) return;
    if (t == (1 | TOQUE_LONGO)) {
      calibrar();
      corrida.preparar(cal);
    } else if (t == 2) {
      if (nivelAtual < nivelMaximo(P)) {
        nivelAtual++;
        piscar(hwLedC, 1, 250);
      } else {
        piscar(hwLedC, 3, 60);   // ja esta no ultimo
      }
      consoleNivel();
    } else if (t == (2 | TOQUE_LONGO)) {
      nivelAtual = 0;
      consoleNivel();
    }
    delay(1);
  }
}

static void correr() {
  uint8_t bruto[N_CANAIS];
  Saida s;
  uint8_t botao = 0, divisor = 0;

  cicloMaxUs = 0;
  ciclosAtrasados = 0;
  for (uint8_t i = 0; i < 16; i++) hwBateriaAtualizar();
  uint16_t escala = hwEscalaBateria(P);

  corrida.iniciar(P, cal, nivelAtual);
  hwLedA(true);
  hwLedB(true);
  hwLedC(false);

  uint32_t proximo = micros();
  while (corrida.fase() != FASE_FIM) {
    // ---- periodo fixo
    while ((int32_t)(micros() - proximo) < 0) {
    }
    uint32_t inicio = micros();
    if (inicio - proximo > PERIODO_US) {   // perdeu o passo: recomeca daqui
      if (ciclosAtrasados < 0xFFFF) ciclosAtrasados++;
      proximo = inicio;
    }
    proximo += PERIODO_US;

    // ---- le, decide, aplica
    hwLerSensores(bruto);
    if (++divisor >= 16) {
      divisor = 0;
      hwBateriaAtualizar();
      escala = hwEscalaBateria(P);
    }
    if (hwBotao(1) || hwBotao(2)) {
      if (++botao >= 5) corrida.abortar();
    } else {
      botao = 0;
    }

    corrida.passo(bruto, escala, s);
    hwMotores(s.esq, s.dir);
    hwVentoinha(s.vent);

    if (corrida.fase() == FASE_CORRENDO) {
      hwLedA(corrida.marcas().ativa(0));
      hwLedB(corrida.marcas().ativa(1));
      hwLedC(corrida.naReta());
    }

    uint16_t gasto = (uint16_t)(micros() - inicio);
    if (gasto > cicloMaxUs) cicloMaxUs = gasto;
  }
  hwMotores(0, 0);
  hwVentoinha(0);
  hwLeds(false);
}

static void telaFim() {
  uint8_t motivo = corrida.resumo().motivo;
  consoleResumo();
  while (hwBotao(1) || hwBotao(2)) {   // o botao que desligou ainda apertado
  }
  delay(30);

  for (;;) {
    consoleProcessar();
    bool pisca = (millis() >> 7) & 1;
    if (motivo == FIM_CHEGADA) {
      hwLedA(true);
      hwLedB(true);
    } else if (motivo == FIM_PERDEU) {
      hwLedC(pisca);
    } else {
      hwLeds((millis() >> 9) & 1);
    }
    if (lerToque()) break;
  }
  hwLeds(false);
}

// Ligado com um botao apertado (como o debug do EVA-RT)
static void modoTeste() {
  bool vent = false;
  Serial.println(F("MODO TESTE: botao 1 = rodas | botao 2 = ventoinha | console: r, s, motores"));
  piscar(hwLeds, 2, 300);
  while (hwBotao(1) || hwBotao(2)) {
  }
  delay(30);

  for (;;) {
    consoleProcessar();
    uint8_t t = lerToque() & ~TOQUE_LONGO;
    if (t == 1) {
      testeMotores();
    } else if (t == 2) {
      vent = !vent;
      hwVentoinha(vent ? 200 : 0);
      hwLedC(vent);
    }
  }
}

// ---------------------------------------------------------------- setup / loop

void setup() {
  hwIniciar();

  Serial.begin(115200);
  PORTD |= _BV(PD0);   // pull-up no RX: sem conversor nem Bluetooth, nao entra lixo

  if (!memCarregarParametros(P)) parametrosPadrao(P);
  nivelAtual = P.nivel;
  if (nivelAtual > nivelMaximo(P)) nivelAtual = nivelMaximo(P);

  if (hwBotao(1) || hwBotao(2)) modoTeste();   // nao volta

  piscar(hwLedC, 10, 25);
  consoleEstado();
}

void loop() {
  if (!temCal) telaEspera();
  telaPronto();
  correr();
  telaFim();
}
