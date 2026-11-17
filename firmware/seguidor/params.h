/*
 * params.h - parametros ajustaveis entre tentativas (console serial + EEPROM)
 *
 * Baseado no EVA-RT 1.2.2 (c) 2025 EXOTIC TEAM MX, licenca AGPL-3.0
 *
 * Os valores padrao partem dos do EVA-RT (SPEED 40, IMP 180, KP 0.06).
 * Sem dependencia do Arduino: tambem compila no PC (firmware/testes).
 */
#pragma once

#include <stdint.h>

struct Parametros {
  // ---- PD (erro em milesimos de sensor: +-5500, 1000 = 7,8 mm)
  float    kp;        // PWM por unidade de erro
  float    kd;        // PWM por (unidade de erro por ms)
  uint8_t  fd;        // filtro da derivada, % da leitura nova (100 = sem filtro)

  // ---- velocidade (PWM 0..255, ja compensado pela bateria)
  uint8_t  vel;       // base nas curvas, no nivel 0 (SPEED do EVA-RT)
  uint8_t  reta;      // quanto a mais nas retas (0 = velocidade unica)
  uint8_t  passo;     // aumento de 'vel' por nivel (botao 2)
  uint8_t  vent;      // ventoinha no nivel 0
  uint8_t  vpasso;    // aumento da ventoinha por nivel
  uint8_t  nivel;     // nivel ao ligar

  // ---- reta x curva
  // A curvatura e estimada pelo comando medio de direcao em % do PWM base
  // (diferenca entre as rodas / velocidade): 0 = reta, ~55 = curva de R100.
  uint16_t ecurva;    // |erro| acima disso e entrada de curva: volta para 'vel' na hora
  uint16_t treta;     // ms com o erro abaixo de ecurva/2 para poder passar de 'vel'
  uint8_t  rreta;     // curvatura (%) ate a qual anda em vel + reta
  uint8_t  rcurva;    // curvatura (%) a partir da qual anda em 'vel'; entre as
                      //   duas a velocidade e proporcional (rcurva <= rreta: degrau)
  uint16_t acel;      // PWM por segundo ao acelerar (tambem e a rampa da largada)
  uint8_t  fcurva;    // freada ao baixar a velocidade: % da queda aplicada a mais
  uint16_t tfcurva;   //   por um instante (constante de tempo, ms); 0 % = sem freada

  uint8_t  re;        // re maxima da roda de dentro (PWM)

  // ---- seguranca e marcas
  uint16_t perdido;   // ms sem ver a linha ate desligar
  uint16_t cruz;      // ms: depois de um cruzamento na barra, descarta a
                      // proxima marca de cada lado (e a faixa do cruzamento)
  uint8_t  nmarcas;   // marcas da direita ate parar (2 = partida + chegada)
  uint16_t tminvolta; // ms minimos entre a partida e a chegada
  uint16_t tmax;      // s: desliga se a volta passar disso (0 = sem limite)

  // ---- parada
  uint16_t freio;     // re para frear, em % do PWM base do momento
  uint16_t tfreio;    // ms de re (voltou para tras: diminua; passou: aumente)

  // ---- bateria
  uint8_t  comp;      // 1 = compensa o PWM pela tensao da bateria
  uint16_t vref;      // mV em que os PWM acima valem como estao
  uint16_t batcal;    // decimos de mV por contagem do ADC (ajuste do divisor)
  uint16_t batmin;    // mV: abaixo disso avisa antes de largar
};

inline void parametrosPadrao(Parametros &p) {
  p.kp = 0.06f;       // KP do EVA-RT
  p.kd = 0.40f;       // KD 0.6 do EVA-RT era por volta do laco (~0,65 ms)
  p.fd = 50;

  p.vel = 40;         // SPEED do EVA-RT
  p.reta = 10;
  p.passo = 5;
  p.vent = 180;       // SPEED_IMP do EVA-RT
  p.vpasso = 14;
  p.nivel = 0;

  p.ecurva = 600;     // 4,7 mm
  p.treta = 60;
  p.rreta = 15;
  p.rcurva = 40;
  p.acel = 300;
  p.fcurva = 100;
  p.tfcurva = 40;

  p.re = 255;         // como no EVA-RT (-255)

  p.perdido = 100;    // EVA-RT: 10 ms
  p.cruz = 300;
  p.nmarcas = 2;
  p.tminvolta = 2000;
  p.tmax = 120;

  p.freio = 100;      // EVA-RT: -SPEED por 75 ms
  p.tfreio = 75;

  p.comp = 1;
  p.vref = 7600;
  p.batcal = 588;     // 5 V / 255 x 3 (divisor 20k/10k) = 58,8 mV
  p.batmin = 7000;
}

// Velocidades de um nivel (o botao 2 sobe o nivel, como o +5 do EVA-RT)
uint8_t velCurvaDoNivel(const Parametros &p, uint8_t nivel);
uint8_t velRetaDoNivel(const Parametros &p, uint8_t nivel);
uint8_t ventDoNivel(const Parametros &p, uint8_t nivel);
uint8_t nivelMaximo(const Parametros &p);
