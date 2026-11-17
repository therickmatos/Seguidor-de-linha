/*
 * corrida.cpp - uma tentativa: largada, controle PD, reta x curva, marcas, parada
 *
 * Baseado no EVA-RT 1.2.2 (c) 2025 EXOTIC TEAM MX, licenca AGPL-3.0
 * https://github.com/EXOTIC-TEAM-MX/EVA-RT
 *
 * O que vem do EVA-RT: PD sobre a posicao da barra (P no erro, D no erro
 * filtrado), base + comando numa roda e base - comando na outra, re na roda
 * de dentro, parada pela marca da direita com re curta.
 *
 * O que muda:
 *  - ciclo de periodo fixo, entao a derivada nao depende do tempo do laco;
 *  - posicao pelo pico da linha (ver linha.cpp);
 *  - base mais alta nas retas e de volta ao valor de curva assim que o erro cresce;
 *  - quando uma roda satura, tira das duas para manter a diferenca;
 *  - PWM compensado pela tensao da bateria;
 *  - linha perdida: continua virando para o lado em que ela saiu por 'perdido' ms;
 *  - cruzamento: segura o erro e descarta a faixa nos sensores de marca;
 *  - conta as marcas da direita (partida, chegada) em vez de parar na
 *    primeira depois de 1 s.
 */
#include "corrida.h"

#define CICLOS(ms)  ((uint32_t)(((uint32_t)(ms) * 1000UL) / PERIODO_US))
#define MS(ciclos)  ((uint32_t)(((uint32_t)(ciclos) * (PERIODO_US / 100UL)) / 10UL))

// ---------------------------------------------------------------- niveis

uint8_t velCurvaDoNivel(const Parametros &p, uint8_t nivel) {
  uint16_t v = (uint16_t)p.vel + (uint16_t)p.passo * nivel;
  uint16_t teto = p.vel > VEL_MAXIMA ? p.vel : VEL_MAXIMA;
  return (uint8_t)(v > teto ? teto : v);
}

uint8_t velRetaDoNivel(const Parametros &p, uint8_t nivel) {
  uint16_t v = (uint16_t)velCurvaDoNivel(p, nivel) + p.reta;
  return (uint8_t)(v > 255 ? 255 : v);
}

uint8_t ventDoNivel(const Parametros &p, uint8_t nivel) {
  uint16_t v = (uint16_t)p.vent + (uint16_t)p.vpasso * nivel;
  uint16_t teto = p.vent > VENT_MAXIMO ? p.vent : VENT_MAXIMO;
  return (uint8_t)(v > teto ? teto : v);
}

uint8_t nivelMaximo(const Parametros &p) {
  if (p.passo == 0 || p.vel >= VEL_MAXIMA) return 0;
  return (uint8_t)((VEL_MAXIMA - p.vel + p.passo - 1) / p.passo);
}

// ---------------------------------------------------------------- apoio

// Deslocamento em vez de divisao: no avr-gcc ">>" de numero negativo e
// aritmetico (arredonda para baixo), o que serve para estas contas.
static int16_t escalar(int16_t v, uint16_t escala) {
  return (int16_t)(((int32_t)v * (int32_t)escala) >> 8);
}

static uint8_t escalarVent(uint8_t v, uint16_t escala) {
  uint16_t r = (uint16_t)(((uint32_t)v * escala) >> 8);
  return (uint8_t)(r > 255 ? 255 : r);
}

static int16_t modulo(int16_t v) {
  return v < 0 ? -v : v;
}

// ---------------------------------------------------------------- corrida

void Corrida::preparar(const Calibracao &c) {
  _linha.configurar(c);
  _marcas.configurar(c);
  _fase = FASE_PARADO;
}

void Corrida::observar(const uint8_t bruto[N_CANAIS]) {
  _linha.atualizar(bruto);
  _marcas.atualizar(bruto[CANAL_MARCA_E], bruto[CANAL_MARCA_D], false, 0);
}

static float limitar(float v, float mn, float mx) {
  return v < mn ? mn : (v > mx ? mx : v);
}

void Corrida::iniciar(const Parametros &p, const Calibracao &c, uint8_t nivel) {
  _p = &p;
  _linha.configurar(c);
  _marcas.configurar(c);

  _r = Resumo();
  _r.motivo = FIM_NENHUM;
  _r.velCurva = velCurvaDoNivel(p, nivel);
  _r.velReta = velRetaDoNivel(p, nivel);
  _r.vent = ventDoNivel(p, nivel);

  _fase = FASE_LARGADA;
  _tFase = 0;
  _t = 0;
  _tPartida = 0;
  _tUltimaDir = 0;

  _kp = (int32_t)(limitar(p.kp, 0, 2) * 65536.0f);
  _kd = (int32_t)(limitar(p.kd, 0, 20) * 4096.0f * (1000.0f / PERIODO_US));
  _fcurva = (uint16_t)(((uint32_t)p.fcurva * 1024UL) / 100UL);
  _cTreta = (uint16_t)CICLOS(p.treta);
  _cPerdido = (uint16_t)CICLOS(p.perdido);
  _cCruz = (uint16_t)CICLOS(p.cruz);
  _cTfcurva = (uint16_t)CICLOS(p.tfcurva);
  if (_cTfcurva < 1) _cTfcurva = 1;
  _cTminVolta = CICLOS(p.tminvolta);
  _cTmax = CICLOS((uint32_t)p.tmax * 1000UL);

  _ef = 0;
  uint16_t fd = p.fd < 1 ? 1 : (p.fd > 100 ? 100 : p.fd);
  _alfa = (uint16_t)(((uint32_t)fd * 256UL) / 100UL);
  _livreAnt = false;
  _uf = 0;
  _base = 0;
  _acelPasso = (int16_t)(((uint32_t)p.acel * 64UL * (PERIODO_US / 100UL)) / 10000UL);
  if (_acelPasso < 1) _acelPasso = 1;
  _excesso = 0;
  _limCruz = (int16_t)(((uint16_t)CRUZ_COMANDO_MAX * _r.velCurva) / 100);
  if (_limCruz < 2) _limCruz = 2;
  _reta = false;
  _calmo = 0;
  _semLinha = 0;
  _cruzAnt = false;

  _logPos = 0;
  _logQtd = 0;
  _logDiv = 0;
  _logEventos = 0;
}

void Corrida::abortar() {
  if (_fase == FASE_PARADO || _fase == FASE_FIM) return;
  if (_r.motivo == FIM_NENHUM) {
    _r.motivo = FIM_BOTAO;
    _r.totalMs = MS(_t);
  }
  _fase = FASE_FIM;
}

void Corrida::encerrar(uint8_t motivo) {
  _r.motivo = motivo;
  _r.totalMs = MS(_t);
  // Re proporcional ao PWM em que vinha: o tempo ate parar fica parecido
  // em qualquer nivel.
  uint16_t re = (uint16_t)(((uint32_t)(_base >> 6) * _p->freio) / 100UL);
  _freio = (int16_t)(re > 255 ? 255 : re);
  _fase = FASE_FREIO;
  _tFase = 0;
}

void Corrida::passo(const uint8_t bruto[N_CANAIS], uint16_t escalaBat, Saida &s) {
  s.esq = 0;
  s.dir = 0;
  s.vent = 0;
  if (_fase == FASE_PARADO || _fase == FASE_FIM) return;

  const Parametros &p = *_p;
  const uint8_t vent = escalarVent(_r.vent, escalaBat);
  // comando medio do ciclo anterior: virando forte = curva, nao cruzamento
  _linha.atualizar(bruto, modulo((int16_t)(_uf >> 8)) < _limCruz);

  switch (_fase) {
    case FASE_LARGADA: {
      // A ventoinha sobe em rampa (sem tranco na bateria) e o robo so sai
      // com ela ja puxando.
      uint16_t subida = (uint16_t)CICLOS(VENT_SUBIDA_MS);
      s.vent = _tFase >= subida ? vent
                                : (uint8_t)(((uint32_t)vent * _tFase) / subida);
      if (++_tFase >= CICLOS(LARGADA_MS)) {
        if (!_linha.vista()) {
          // fora da linha: nem sai
          _r.motivo = FIM_PERDEU;
          _fase = FASE_FIM;
          s.vent = 0;
        } else {
          _fase = FASE_CORRENDO;
          _tFase = 0;
        }
      }
      break;
    }

    case FASE_CORRENDO:
      s.vent = vent;
      controlar(bruto, escalaBat, s);
      break;

    case FASE_FREIO: {
      int16_t re = escalar(-_freio, escalaBat);
      if (re < -255) re = -255;
      s.esq = re;
      s.dir = re;
      s.vent = vent;
      if (++_tFase >= CICLOS(p.tfreio)) {
        _fase = FASE_POS_PARADA;
        _tFase = 0;
      }
      break;
    }

    case FASE_POS_PARADA:
      // PWM 0 no DRV8874 (PH/EN) curto-circuita o motor: a roda fica freada.
      // A ventoinha segura o robo no chao ate ele parar.
      s.vent = vent;
      if (++_tFase >= CICLOS(VENT_POS_PARADA_MS)) {
        _fase = FASE_FIM;
        s.vent = 0;
      }
      break;

    default:
      break;
  }
}

void Corrida::controlar(const uint8_t bruto[N_CANAIS], uint16_t escalaBat, Saida &s) {
  const Parametros &p = *_p;
  _t++;

  uint8_t eventos = _marcas.atualizar(bruto[CANAL_MARCA_E], bruto[CANAL_MARCA_D],
                                      _linha.cruzamento(), _cCruz);

  const int16_t e = _linha.erro();
  const bool vista = _linha.vista();
  const bool cruz = _linha.cruzamento();
  const bool livre = _linha.medida();   // erro medido de verdade neste ciclo

  // ---- PD: P no erro, D no erro filtrado
  const int32_t e256 = (int32_t)e * 256;
  int16_t d16 = 0;   // variacao do erro filtrado neste ciclo, x16
  if (livre && _livreAnt) {
    const int32_t anterior = _ef;
    _ef += ((e256 - _ef) * (int32_t)_alfa) >> 8;
    int32_t d = (_ef - anterior) >> 4;
    if (d > 16000) d = 16000;        // 1000 por ciclo: ja satura o comando
    else if (d < -16000) d = -16000;
    d16 = (int16_t)d;
  } else {
    _ef = e256;   // erro mantido ou no extremo: sem derivada
  }
  _livreAnt = livre;

  int32_t u = (((int32_t)e * _kp) >> 16) + (((int32_t)d16 * _kd) >> 16);
  if (u > 510) u = 510;       // limite do EVA-RT
  else if (u < -510) u = -510;
  const int16_t comando = (int16_t)u;

  // ---- velocidade conforme a curvatura
  // Curvatura = comando medio de direcao / PWM base (diferenca entre as
  // rodas sobre a velocidade), em %. Ate 'rreta' anda em velReta, de
  // 'rcurva' em diante em velCurva, e no meio proporcional: curva aberta
  // nao precisa da velocidade da curva mais fechada.
  // A entrada de curva aparece antes no erro: passou de 'ecurva', volta
  // para velCurva na hora e so sai de la com o erro quieto por 'treta' ms.
  _uf += ((int32_t)comando * 256 - _uf) >> 5;
  const int16_t comandoMedio = modulo((int16_t)(_uf >> 8));
  const int16_t erroAbs = modulo(e);
  if (!vista || erroAbs >= (int16_t)p.ecurva) {
    _calmo = 0;
  } else if (erroAbs < (int16_t)(p.ecurva / 2) && _calmo < 0xFFFF) {
    _calmo++;
  }

  uint8_t alvoPwm = _r.velCurva;
  if (_calmo >= _cTreta) {
    int16_t baseAgora = _base >> 6;
    if (baseAgora < _r.velCurva) baseAgora = _r.velCurva;
    if (baseAgora < 1) baseAgora = 1;
    const uint16_t curvatura = ((uint16_t)comandoMedio * 100U) / (uint16_t)baseAgora;
    if (curvatura <= p.rreta) {
      alvoPwm = _r.velReta;
    } else if (curvatura < p.rcurva) {
      alvoPwm = (uint8_t)(_r.velReta - ((uint16_t)(_r.velReta - _r.velCurva) * (curvatura - p.rreta)) /
                                           (uint16_t)(p.rcurva - p.rreta));
    }
  }
  _reta = (alvoPwm > _r.velCurva);

  // ---- base: sobe em rampa (a largada usa a mesma), cai na hora. Na queda
  // manda por um instante menos que o alvo ('fcurva' % da queda): o motor
  // demora a perder velocidade e a curva ja esta embaixo da barra.
  const int16_t alvo = (int16_t)alvoPwm * 64;
  if (_base < alvo) {
    _base += _acelPasso;
    if (_base > alvo) _base = alvo;
  } else if (_base > alvo) {
    _excesso += _base - alvo;
    if (_excesso > 16000) _excesso = 16000;
    _base = alvo;
  }
  int16_t base = _base >> 6;
  if (_excesso > 0) {
    const int16_t some = (int16_t)((uint16_t)_excesso / _cTfcurva);
    _excesso -= some > 0 ? some : 1;
    base -= (int16_t)(((int32_t)_excesso * _fcurva) >> 16);   // / 64 x fcurva / 100
    if (base < 0) base = 0;
  }

  // ---- rodas: erro positivo = linha a direita = roda esquerda mais rapida
  int16_t esq = escalar(base + comando, escalaBat);
  int16_t dir = escalar(base - comando, escalaBat);
  if (esq > 255) {
    dir -= esq - 255;   // sem folga em cima: mantem a diferenca
    esq = 255;
  }
  if (dir > 255) {
    esq -= dir - 255;
    dir = 255;
  }
  const int16_t piso = -(int16_t)p.re;
  if (esq < piso) esq = piso;
  if (dir < piso) dir = piso;
  s.esq = esq;
  s.dir = dir;

  // ---- numeros da tentativa
  if (_reta) _r.retaMs++;
  if (livre && (uint16_t)erroAbs > _r.erroMax) _r.erroMax = (uint16_t)erroAbs;
  if (cruz && !_cruzAnt) _r.cruzamentos++;
  _cruzAnt = cruz;
  if (eventos & MARCA_ESQ) _r.marcasEsq++;
  registrar(e, s, eventos);

  // ---- fim da tentativa
  if (eventos & MARCA_DIR) {
    // A primeira marca da direita e a partida. Depois dela, outra so vale
    // passado 'tminvolta' (a chegada fica 1 m antes da partida).
    bool partida = (_r.marcasDir == 0 && p.nmarcas > 1);
    if (partida || (_t - _tUltimaDir) >= _cTminVolta) {
      _r.marcasDir++;
      _tUltimaDir = _t;
      if (partida) _tPartida = _t;
      if (_r.marcasDir >= p.nmarcas) {
        _r.voltaMs = MS(_t - _tPartida);
        encerrar(FIM_CHEGADA);
        return;
      }
    }
  }

  if (!vista) {
    if (_r.perdidoMs < 0xFFFF) _r.perdidoMs++;
    if (++_semLinha >= _cPerdido) {
      encerrar(FIM_PERDEU);
      return;
    }
  } else {
    _semLinha = 0;
  }

  if (_cTmax && _t >= _cTmax) encerrar(FIM_TEMPO);
}

// ---------------------------------------------------------------- registro

void Corrida::registrar(int16_t erro, const Saida &s, uint8_t eventos) {
  _logEventos |= eventos;   // nao perde a marca entre duas amostras
  if (++_logDiv < CICLOS(LOG_PERIODO_MS)) return;
  _logDiv = 0;

  AmostraLog &a = _log[_logPos];
  a.erro = (int8_t)(erro / 50);
  a.esq = (int8_t)(s.esq / 2);
  a.dir = (int8_t)(s.dir / 2);
  a.bits = (_linha.vista() ? LOG_VISTA : 0) | (_linha.cruzamento() ? LOG_CRUZ : 0) |
           ((_logEventos & MARCA_ESQ) ? LOG_MARCA_E : 0) |
           ((_logEventos & MARCA_DIR) ? LOG_MARCA_D : 0) | (_reta ? LOG_RETA : 0);
  _logEventos = 0;

  if (++_logPos >= LOG_TAMANHO) _logPos = 0;
  if (_logQtd < LOG_TAMANHO) _logQtd++;
}

const AmostraLog &Corrida::logAmostra(uint8_t i) const {
  uint8_t inicio = _logQtd < LOG_TAMANHO ? 0 : _logPos;
  uint8_t k = (uint8_t)((inicio + i) % LOG_TAMANHO);
  return _log[k];
}
