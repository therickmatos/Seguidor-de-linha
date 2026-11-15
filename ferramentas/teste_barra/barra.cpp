#include "barra.h"
#include <Preferences.h>

// ---- NVS ----
static const char* const NVS_NAMESPACE = "barra";
static const char* const CHAVE_CAL  = "cal";
static const char* const CHAVE_COR  = "cor";
static const uint8_t VERSAO_CAL = 1;

struct CalibracaoNVS {
  uint8_t  versao;
  uint8_t  canal[NUM_SENSORS];   // mapa em que a calibracao foi feita
  uint16_t vMin[NUM_SENSORS];
  uint16_t vMax[NUM_SENSORS];
};

static bool contrasteOk(const uint16_t* vMin, const uint16_t* vMax) {
  for (uint8_t i = 0; i < NUM_SENSORS; i++) {
    if ((int32_t)vMax[i] - (int32_t)vMin[i] < DELTA_MINIMO) return false;
  }
  return true;
}

void Barra::begin(const PinosBarra& pinos, CorLinha cor) {
  _pinos = pinos;
  _corPadrao = cor;

  for (uint8_t b = 0; b < 4; b++) {
    pinMode(_pinos.s[b], OUTPUT);
    digitalWrite(_pinos.s[b], LOW);
  }

  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);   // global e antes da 1a leitura (ver barra.h)
  analogRead(_pinos.sig);           // inicializa o canal do ADC (a 1a leitura e lenta)

  configurarLeitura(AMOSTRAS_PADRAO, ACOMODACAO_US_PADRAO, DESCARTE_PADRAO);
  restaurarPadroes();
}

void Barra::restaurarPadroes() {
  _calibrado = false;
  _cor = _corPadrao;
  _ultimaPosicao = POS_CENTRO;
}

void Barra::configurarLeitura(uint8_t amostras, uint16_t acomodacaoUs, bool descarte) {
  _amostras = amostras ? amostras : 1;
  _acomodacaoUs = acomodacaoUs;
  _descarte = descarte;
}

// ---------------- Leitura ----------------

void Barra::selecionarCanal(uint8_t ch) {
  for (uint8_t b = 0; b < 4; b++) {
    digitalWrite(_pinos.s[b], (ch >> b) & 0x01);
  }
}

uint32_t Barra::amostrar(uint8_t ch, bool emMilliVolts) {
  selecionarCanal(ch);
  if (_acomodacaoUs) delayMicroseconds(_acomodacaoUs);
  if (_descarte) analogRead(_pinos.sig);   // descarta a primeira (limpa o S&H)
  uint32_t acc = 0;
  for (uint8_t k = 0; k < _amostras; k++) {
    acc += emMilliVolts ? analogReadMilliVolts(_pinos.sig) : analogRead(_pinos.sig);
  }
  return acc / _amostras;
}

void Barra::lerBrutos() {
  uint32_t t0 = micros();
  for (uint8_t i = 0; i < NUM_SENSORS; i++) _raw[i] = lerCanal(_canal[i]);
  _tLeituraUs = micros() - t0;
}

void Barra::atualizar() {
  lerBrutos();
  calcularPosicao();
}

// 0..1000, com 1000 = sobre a linha (ja considera a cor da linha)
uint16_t Barra::normalizar(uint8_t i) const {
  int32_t v;
  if (_calibrado && _vMax[i] > _vMin[i]) {
    v = ((int32_t)_raw[i] - _vMin[i]) * 1000 / ((int32_t)_vMax[i] - _vMin[i]);
    if (v < 0) v = 0;
    else if (v > 1000) v = 1000;
  } else {
    v = (int32_t)_raw[i] * 1000 / LEITURA_MAX;   // sem calibracao: escala cheia do ADC
  }
  // No QRE1113 o preto gera leitura alta; para linha branca, inverte.
  if (_cor == LINHA_BRANCA) v = 1000 - v;
  return (uint16_t)v;
}

// Media ponderada: 0 .. (NUM_SENSORS-1)*1000. Calculada uma vez por leitura.
void Barra::calcularPosicao() {
  uint32_t soma = 0, somaPonderada = 0;
  bool naLinha = false;

  for (uint8_t i = 0; i < NUM_SENSORS; i++) {
    uint16_t v = normalizar(i);
    _norm[i] = v;
    if (v > LIMIAR_LINHA) naLinha = true;
    if (v > LIMIAR_RUIDO) {
      somaPonderada += (uint32_t)v * ((uint32_t)i * 1000);
      soma += v;
    }
  }

  if (!naLinha || soma == 0) {
    // linha perdida: vai para o extremo do lado em que foi vista por ultimo
    _perdida = true;
    _posicao = (_ultimaPosicao < POS_CENTRO) ? 0 : POS_MAX;
  } else {
    _perdida = false;
    _ultimaPosicao = (uint16_t)(somaPonderada / soma);
    _posicao = _ultimaPosicao;
  }
  _erro = (int16_t)((int16_t)_posicao - (int16_t)POS_CENTRO);
}

// ---------------- Calibracao ----------------

void Barra::iniciarCalibracao() {
  for (uint8_t i = 0; i < NUM_SENSORS; i++) {
    _calMin[i] = LEITURA_MAX;
    _calMax[i] = 0;
    _calSoma[i] = 0;
  }
  memset(_calHist, 0, sizeof(_calHist));
  _calPos = 0;
  _calCheia = 0;
}

void Barra::amostrarCalibracao() {
  lerBrutos();
  for (uint8_t i = 0; i < NUM_SENSORS; i++) {
    _calSoma[i] += _raw[i];
    _calSoma[i] -= _calHist[i][_calPos];   // sai a leitura mais antiga
    _calHist[i][_calPos] = _raw[i];
  }
  _calPos = (uint8_t)((_calPos + 1) % JANELA_CALIBRACAO);
  if (_calCheia < JANELA_CALIBRACAO) _calCheia++;
  if (_calCheia < JANELA_CALIBRACAO) return;   // janela ainda enchendo

  for (uint8_t i = 0; i < NUM_SENSORS; i++) {
    uint16_t media = (uint16_t)(_calSoma[i] / JANELA_CALIBRACAO);
    if (media < _calMin[i]) _calMin[i] = media;
    if (media > _calMax[i]) _calMax[i] = media;
  }
}

ResultadoCalibracao Barra::finalizarCalibracao() {
  ResultadoCalibracao r = {};
  for (uint8_t i = 0; i < NUM_SENSORS; i++) {
    r.vMin[i] = _calMin[i];
    r.vMax[i] = _calMax[i];
    if ((int32_t)_calMax[i] - (int32_t)_calMin[i] < DELTA_MINIMO) r.semContraste++;
    if (_calMax[i] >= LIMIAR_SATURACAO) r.saturados++;
  }

  if (r.semContraste == 0) {
    memcpy(_vMin, _calMin, sizeof(_vMin));
    memcpy(_vMax, _calMax, sizeof(_vMax));
    _calibrado = true;
    _ultimaPosicao = POS_CENTRO;
    r.aceita = true;
  } else {
    // rejeitada: a calibracao anterior (se havia) continua valendo
    r.manteveAnterior = _calibrado;
  }
  return r;
}

void Barra::descartarCalibracao() {
  _calibrado = false;
}

// ---------------- Conferencia dos canais ----------------

void Barra::iniciarMapeamento() {
  memset(&_mapa, 0, sizeof(_mapa));
  for (uint8_t c = 0; c < NUM_CANAIS; c++) _mapa.cMin[c] = LEITURA_MAX;
}

void Barra::amostrarMapeamento() {
  for (uint8_t c = 0; c < NUM_CANAIS; c++) {
    uint16_t v = lerCanal(c);
    if (v < _mapa.cMin[c]) _mapa.cMin[c] = v;
    if (v > _mapa.cMax[c]) _mapa.cMax[c] = v;
  }
}

const ResultadoMapa& Barra::finalizarMapeamento() {
  uint32_t ativos = 0, mapa = 0;   // um bit por canal
  _mapa.nAtivos = 0;
  for (uint8_t c = 0; c < NUM_CANAIS; c++) {
    if ((int32_t)_mapa.cMax[c] - (int32_t)_mapa.cMin[c] > LIMIAR_ATIV) {
      _mapa.ativos[_mapa.nAtivos++] = c;
      ativos |= 1UL << c;
    }
  }
  for (uint8_t i = 0; i < NUM_SENSORS; i++) mapa |= 1UL << _canal[i];
  _mapa.confere = (ativos == mapa);
  return _mapa;
}

// ---------------- Cor da linha ----------------

void Barra::setCorLinha(CorLinha cor) {
  _cor = cor;
  _ultimaPosicao = POS_CENTRO;   // a memoria da linha anterior nao vale para a outra cor
}

// ---------------- NVS ----------------

EstadoNVS Barra::carregarNVS() {
  EstadoNVS e = {};
  Preferences p;
  // leitura/escrita: no primeiro boot cria o namespace em vez de gerar erro
  if (!p.begin(NVS_NAMESPACE, false)) return e;

  if (p.isKey(CHAVE_CAL)) {
    CalibracaoNVS c;
    if (p.getBytesLength(CHAVE_CAL) == sizeof(c) &&
        p.getBytes(CHAVE_CAL, &c, sizeof(c)) == sizeof(c) &&
        c.versao == VERSAO_CAL &&
        memcmp(c.canal, _canal, sizeof(_canal)) == 0 &&   // MAPA_PADRAO mudou? recalibrar
        contrasteOk(c.vMin, c.vMax)) {
      memcpy(_vMin, c.vMin, sizeof(_vMin));
      memcpy(_vMax, c.vMax, sizeof(_vMax));
      _calibrado = true;
      _ultimaPosicao = POS_CENTRO;
      e.calibracao = true;
    } else {
      e.calibracaoInvalida = true;
    }
  }

  if (p.isKey(CHAVE_COR)) {
    uint8_t cor = p.getUChar(CHAVE_COR, 0xFF);
    if (cor == LINHA_PRETA || cor == LINHA_BRANCA) {
      _cor = (CorLinha)cor;
      e.cor = true;
    }
  }

  p.end();
  return e;
}

bool Barra::salvarCalibracao() {
  if (!_calibrado) return false;
  CalibracaoNVS c;
  memset(&c, 0, sizeof(c));
  c.versao = VERSAO_CAL;
  memcpy(c.canal, _canal, sizeof(c.canal));
  memcpy(c.vMin, _vMin, sizeof(c.vMin));
  memcpy(c.vMax, _vMax, sizeof(c.vMax));

  Preferences p;
  if (!p.begin(NVS_NAMESPACE, false)) return false;
  bool ok = p.putBytes(CHAVE_CAL, &c, sizeof(c)) == sizeof(c);
  p.end();
  return ok;
}

bool Barra::salvarCor() {
  Preferences p;
  if (!p.begin(NVS_NAMESPACE, false)) return false;
  bool ok = p.putUChar(CHAVE_COR, (uint8_t)_cor) == 1;
  p.end();
  return ok;
}

bool Barra::apagarCalibracaoNVS() {
  Preferences p;
  if (!p.begin(NVS_NAMESPACE, false)) return false;
  bool ok = !p.isKey(CHAVE_CAL) || p.remove(CHAVE_CAL);
  p.end();
  return ok;
}

bool Barra::apagarNVS() {
  Preferences p;
  if (!p.begin(NVS_NAMESPACE, false)) return false;
  bool ok = p.clear();
  p.end();
  return ok;
}
