/*
 * memoria.cpp - parametros e calibracao na EEPROM
 *
 * Baseado no EVA-RT 1.2.2 (c) 2025 EXOTIC TEAM MX, licenca AGPL-3.0
 */
#include <avr/eeprom.h>
#include <string.h>
#include "memoria.h"

#define END_PARAMETROS   0
#define END_CALIBRACAO   128

#define MAGIA_PARAMETROS 0x5347   // mudar a struct Parametros -> somar 1 aqui
#define MAGIA_CALIBRACAO 0x4341

struct BlocoParametros {
  uint16_t   magia;
  uint8_t    tamanho;
  Parametros p;
  uint8_t    soma;
};

struct BlocoCalibracao {
  uint16_t   magia;
  uint8_t    mapa[N_SENSORES];
  uint8_t    opcoes;
  Calibracao c;
  uint8_t    soma;
};

static const uint8_t MAPA[N_SENSORES] = MAPA_MUX;
#define OPCOES_CAL  ((LINHA_BRANCA ? 1 : 0) | (BARRA_ESPELHADA ? 2 : 0))

static uint8_t somar(const void *dados, uint8_t n) {
  const uint8_t *b = (const uint8_t *)dados;
  uint8_t s = 0x5A;
  while (n--) s = (uint8_t)((s << 1) | (s >> 7)) ^ *b++;
  return s;
}

bool memCarregarParametros(Parametros &p) {
  BlocoParametros b;
  eeprom_read_block(&b, (const void *)END_PARAMETROS, sizeof(b));
  if (b.magia != MAGIA_PARAMETROS || b.tamanho != sizeof(Parametros)) return false;
  if (b.soma != somar(&b, sizeof(b) - 1)) return false;
  p = b.p;
  return true;
}

void memSalvarParametros(const Parametros &p) {
  BlocoParametros b;
  memset(&b, 0, sizeof(b));
  b.magia = MAGIA_PARAMETROS;
  b.tamanho = sizeof(Parametros);
  b.p = p;
  b.soma = somar(&b, sizeof(b) - 1);
  eeprom_update_block(&b, (void *)END_PARAMETROS, sizeof(b));
}

bool memCarregarCalibracao(Calibracao &c) {
  BlocoCalibracao b;
  eeprom_read_block(&b, (const void *)END_CALIBRACAO, sizeof(b));
  if (b.magia != MAGIA_CALIBRACAO || b.opcoes != OPCOES_CAL) return false;
  if (memcmp(b.mapa, MAPA, sizeof(MAPA)) != 0) return false;
  if (b.soma != somar(&b, sizeof(b) - 1)) return false;
  // a barra inteira precisa de contraste (as marcas podem estar desligadas)
  for (uint8_t i = 0; i < N_SENSORES; i++) {
    if (b.c.mx[i] < b.c.mn[i] || (uint8_t)(b.c.mx[i] - b.c.mn[i]) < DELTA_MINIMO) return false;
  }
  c = b.c;
  return true;
}

void memSalvarCalibracao(const Calibracao &c) {
  BlocoCalibracao b;
  memset(&b, 0, sizeof(b));
  b.magia = MAGIA_CALIBRACAO;
  memcpy(b.mapa, MAPA, sizeof(MAPA));
  b.opcoes = OPCOES_CAL;
  b.c = c;
  b.soma = somar(&b, sizeof(b) - 1);
  eeprom_update_block(&b, (void *)END_CALIBRACAO, sizeof(b));
}
