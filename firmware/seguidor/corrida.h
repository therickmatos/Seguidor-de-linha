/*
 * corrida.h - uma tentativa: largada, controle PD, reta x curva, marcas, parada
 *
 * Baseado no EVA-RT 1.2.2 (c) 2025 EXOTIC TEAM MX, licenca AGPL-3.0
 * https://github.com/EXOTIC-TEAM-MX/EVA-RT
 *
 * Recebe as leituras brutas de um ciclo e devolve os PWM. Nao toca no
 * hardware, entao o mesmo codigo roda no simulador de firmware/testes.
 */
#pragma once

#include <stdint.h>
#include "config.h"
#include "params.h"
#include "linha.h"

enum Fase : uint8_t {
  FASE_PARADO,
  FASE_LARGADA,      // ventoinha subindo, rodas paradas
  FASE_CORRENDO,
  FASE_FREIO,        // re curta
  FASE_POS_PARADA,   // rodas travadas, ventoinha ainda ligada
  FASE_FIM
};

enum Motivo : uint8_t {
  FIM_NENHUM,
  FIM_CHEGADA,       // viu a marca de chegada
  FIM_PERDEU,        // ficou sem ver a linha
  FIM_BOTAO,
  FIM_TEMPO          // passou de 'tmax'
};

struct Saida {
  int16_t esq;       // -255..255, + = para a frente
  int16_t dir;
  uint8_t vent;      // 0..255
};

struct Resumo {
  uint8_t  motivo;
  uint8_t  velCurva, velReta, vent;   // do nivel usado
  uint32_t voltaMs;      // da marca de partida a de chegada (0 = nao fechou)
  uint32_t totalMs;      // da saida ate o fim
  uint32_t retaMs;       // tempo andando como reta
  uint16_t perdidoMs;    // soma do tempo sem ver a linha
  uint16_t erroMax;      // maior |erro| com a linha vista
  uint16_t marcasEsq;
  uint16_t marcasDir;
  uint16_t cruzamentos;
};

// Uma amostra do registro (as ultimas LOG_TAMANHO ficam guardadas)
#define LOG_VISTA   0x01
#define LOG_CRUZ    0x02
#define LOG_MARCA_E 0x04
#define LOG_MARCA_D 0x08
#define LOG_RETA    0x10
struct AmostraLog {
  int8_t  erro;      // erro / 50
  int8_t  esq;       // PWM / 2
  int8_t  dir;
  uint8_t bits;
};

class Corrida {
public:
  // Parado: so acompanha os sensores (LEDs e console), sem andar
  void preparar(const Calibracao &c);
  void observar(const uint8_t bruto[N_CANAIS]);

  void iniciar(const Parametros &p, const Calibracao &c, uint8_t nivel);

  // Um ciclo (PERIODO_US). escalaBat: 256 = PWM como esta (ver hw.h).
  void passo(const uint8_t bruto[N_CANAIS], uint16_t escalaBat, Saida &s);

  void abortar();    // botao: desliga tudo na hora

  uint8_t fase() const            { return _fase; }
  bool    naReta() const          { return _reta; }   // acima da velocidade de curva
  const Resumo &resumo() const    { return _r; }
  const Linha  &linha() const     { return _linha; }
  const Marcas &marcas() const    { return _marcas; }

  uint8_t logQtd() const          { return _logQtd; }
  const AmostraLog &logAmostra(uint8_t i) const;   // 0 = a mais antiga

private:
  void controlar(const uint8_t bruto[N_CANAIS], uint16_t escalaBat, Saida &s);
  void encerrar(uint8_t motivo);
  void registrar(int16_t erro, const Saida &s, uint8_t eventos);

  const Parametros *_p;
  Linha   _linha;
  Marcas  _marcas;
  Resumo  _r;

  uint8_t  _fase;
  uint16_t _tFase;        // ciclos na fase atual
  uint32_t _t;            // ciclos desde a saida
  uint32_t _tPartida;
  uint32_t _tUltimaDir;

  // Ganhos e tempos convertidos uma vez em iniciar(): o ciclo so faz
  // contas inteiras (float e divisao de 32 bits custam caro no ATmega).
  int32_t  _kp;           // kp x 65536
  int32_t  _kd;           // kd x 4096, ja por ciclo
  uint16_t _fcurva;       // fcurva / 100 x 1024
  uint16_t _cTreta, _cPerdido, _cCruz, _cTfcurva;   // em ciclos
  uint32_t _cTminVolta, _cTmax;

  int32_t  _ef;           // erro filtrado (x256)
  uint16_t _alfa;         // filtro da derivada (x256)
  bool     _livreAnt;
  int32_t  _uf;           // comando de direcao filtrado (x256)
  int16_t  _base;         // PWM base atual (x64)
  int16_t  _acelPasso;    // aumento da base por ciclo (x64)
  int16_t  _freio;        // PWM da re na parada
  int16_t  _excesso;      // queda recente da base, para a freada (x64)
  int16_t  _limCruz;      // |comando medio| acima disso = nao e cruzamento
  bool     _reta;         // andando acima da velocidade de curva
  uint16_t _calmo;        // ciclos com o erro quieto desde a ultima entrada de curva
  uint16_t _semLinha;     // ciclos seguidos sem ver a linha
  bool     _cruzAnt;

  AmostraLog _log[LOG_TAMANHO];
  uint8_t  _logPos;
  uint8_t  _logQtd;
  uint8_t  _logDiv;
  uint8_t  _logEventos;
};
