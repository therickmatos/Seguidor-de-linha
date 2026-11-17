/*
 * hw.cpp - acesso ao hardware (ATmega328P, mapa de pinos do EVA-RT 1.2.2)
 *
 * Baseado no EVA-RT 1.2.2 (c) 2025 EXOTIC TEAM MX, licenca AGPL-3.0
 * https://github.com/EXOTIC-TEAM-MX/EVA-RT
 *
 * Como no EVA-RT: ADC em 8 bits (ADLAR) com relogio de 1 MHz e PWM dos
 * motores pelo analogWrite (Timer0, 976 Hz), que nao mexe no millis().
 */
#include "hw.h"

#define ADMUX_BASE  (_BV(REFS0) | _BV(ADLAR))   // referencia AVCC, resultado em ADCH

static const uint8_t MAPA[N_SENSORES] = MAPA_MUX;

static uint16_t batFiltro;   // 8 x a leitura (media movel exponencial)

static inline uint8_t converter() {
  ADCSRA |= _BV(ADSC);
  while (ADCSRA & _BV(ADSC)) {
  }
  return ADCH;
}

// Entrada direta do ATmega. A primeira conversao depois de trocar de canal
// e descartada: os sensores de marca tem 47k na saida e o capacitor de
// amostragem ainda guarda a tensao do canal anterior.
static uint8_t lerEntrada(uint8_t adc) {
  ADMUX = ADMUX_BASE | adc;
  converter();
  return converter();
}

void hwIniciar() {
  // saidas desligadas antes de virarem saida
  PORTD &= ~(_BV(PD2) | _BV(PD3) | _BV(PD4) | _BV(PD5) | _BV(PD6) | _BV(PD7));
  PORTB &= ~(_BV(PB2) | _BV(PB5));
  DDRD |= _BV(PD2) | _BV(PD3) | _BV(PD4) | _BV(PD5) | _BV(PD6) | _BV(PD7);
  DDRB |= _BV(PB2) | _BV(PB5);

  // botoes com pull-up interno
  DDRB &= ~(_BV(PB3) | _BV(PB4));
  PORTB |= _BV(PB3) | _BV(PB4);

  // S0..S3 do mux em PC0..PC3; PC4 e PC5 sao entradas analogicas
  PORTC &= 0xC0;
  DDRC = (DDRC & 0xC0) | 0x0F;
  DIDR0 = _BV(ADC4D) | _BV(ADC5D);

  ADMUX = ADMUX_BASE | ADC_MUX;
  ADCSRA = _BV(ADEN) | _BV(ADPS2);   // 16 MHz / 16 = 1 MHz
  converter();                       // a primeira conversao e mais longa

  batFiltro = (uint16_t)lerEntrada(ADC_BATERIA) * 8;
}

// ---------------------------------------------------------------- sensores

void hwLerSensores(uint8_t bruto[N_CANAIS]) {
  ADMUX = ADMUX_BASE | ADC_MUX;
  for (uint8_t i = 0; i < N_SENSORES; i++) {
    PORTC = (PORTC & 0xF0) | MAPA[i];
    delayMicroseconds(ACOMODACAO_US);
#if BARRA_ESPELHADA
    bruto[N_SENSORES - 1 - i] = converter();
#else
    bruto[i] = converter();
#endif
  }
  bruto[CANAL_MARCA_E] = lerEntrada(ADC_MARCA_E);
  bruto[CANAL_MARCA_D] = lerEntrada(ADC_MARCA_D);
}

void hwLerMedia(uint8_t bruto[N_CANAIS], uint8_t leituras) {
  uint16_t soma[N_CANAIS];
  uint8_t uma[N_CANAIS];
  for (uint8_t i = 0; i < N_CANAIS; i++) soma[i] = 0;
  for (uint8_t k = 0; k < leituras; k++) {
    hwLerSensores(uma);
    for (uint8_t i = 0; i < N_CANAIS; i++) soma[i] += uma[i];
  }
  for (uint8_t i = 0; i < N_CANAIS; i++) {
    bruto[i] = (uint8_t)((soma[i] + leituras / 2) / leituras);
  }
}

uint8_t hwLerCanalMux(uint8_t canal) {
  ADMUX = ADMUX_BASE | ADC_MUX;
  PORTC = (PORTC & 0xF0) | (canal & 0x0F);
  delayMicroseconds(100);
  converter();
  return converter();
}

uint8_t hwLerAdc(uint8_t adc) {
  return lerEntrada(adc);
}

// ---------------------------------------------------------------- bateria

void hwBateriaAtualizar() {
  batFiltro = batFiltro - (batFiltro >> 3) + lerEntrada(ADC_BATERIA);
}

uint16_t hwBateriaMv(const Parametros &p) {
  // (filtro / 8) contagens x (batcal / 10) mV por contagem
  return (uint16_t)(((uint32_t)batFiltro * p.batcal) / 80UL);
}

uint16_t hwEscalaBateria(const Parametros &p) {
  if (!p.comp) return 256;
  uint16_t mv = hwBateriaMv(p);
  if (mv < 5500 || mv > 9000) return 256;   // divisor sem montar ou batcal errado
  uint16_t e = (uint16_t)(((uint32_t)p.vref * 256UL) / mv);
  if (e < 205) e = 205;       // 0,8
  else if (e > 384) e = 384;  // 1,5
  return e;
}

// ---------------------------------------------------------------- saidas

// Como no EVA-RT: sentido em nivel baixo = para a frente (PH do DRV8874).
static void motor(uint8_t pinoPwm, uint8_t bitSentido, int16_t v) {
  if (v < 0) {
    PORTD |= _BV(bitSentido);
    v = -v;
  } else {
    PORTD &= ~_BV(bitSentido);
  }
  analogWrite(pinoPwm, v > 255 ? 255 : v);
}

void hwMotores(int16_t esq, int16_t dir) {
#if INVERTER_MOTOR_ESQ
  esq = -esq;
#endif
#if INVERTER_MOTOR_DIR
  dir = -dir;
#endif
#if TROCAR_MOTORES
  motor(5, PD3, dir);
  motor(6, PD4, esq);
#else
  motor(5, PD3, esq);
  motor(6, PD4, dir);
#endif
}

void hwVentoinha(uint8_t pwm) {
  analogWrite(10, pwm);
}

void hwLedA(bool ligado) {
  if (ligado) PORTD |= _BV(PD2);
  else PORTD &= ~_BV(PD2);
}

void hwLedB(bool ligado) {
  if (ligado) PORTD |= _BV(PD7);
  else PORTD &= ~_BV(PD7);
}

void hwLedC(bool ligado) {
  if (ligado) PORTB |= _BV(PB5);
  else PORTB &= ~_BV(PB5);
}

void hwLeds(bool ligado) {
  hwLedA(ligado);
  hwLedB(ligado);
  hwLedC(ligado);
}

bool hwBotao(uint8_t n) {
  return !(PINB & (n == 1 ? _BV(PB3) : _BV(PB4)));
}
