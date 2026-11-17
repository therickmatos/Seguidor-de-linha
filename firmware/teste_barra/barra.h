/*
 * barra.h - Barra QRE1113 (12 sensores) + MUX 74HC4067
 *
 * Modulo de leitura reutilizavel (teste de bancada e firmware final).
 * Nao usa Serial e nao tem delay() no caminho da leitura: a unica espera
 * e a acomodacao do mux (delayMicroseconds), configuravel.
 * Feito para ESP32-C3 com Arduino-ESP32 core 3.x.
 *
 * Uso:
 *   Barra barra;
 *   barra.begin(pinos, LINHA_PRETA);
 *   barra.carregarNVS();
 *   // a cada ciclo:
 *   barra.atualizar();
 *   barra.posicao(); barra.erro(); barra.linhaPerdida();   // mesma leitura
 *
 * Atencao: begin() ajusta o ADC global (12 bits, ADC_11db). No core 3.x,
 * analogSetPinAttenuation() antes do primeiro analogRead() nao tem efeito,
 * e analogReadMilliVolts() calibra pela atenuacao global.
 */
#pragma once

#include <Arduino.h>

#define NUM_SENSORS   12
#define NUM_CANAIS    16

// Canal do mux de cada sensor (S0..S11). A barra usa C4..C15 (C0..C3 vazios).
// O mapa e fixo no codigo: o comando 'm' do sketch de teste so confere quais
// canais respondem e imprime a linha para colar aqui.
// Se a barra estiver montada espelhada, inverta a ordem.
#define MAPA_PADRAO  {4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15}

// Leitura de um sensor: troca o canal, espera a acomodacao, descarta a
// primeira conversao (limpa o S&H) e tira a media de AMOSTRAS conversoes.
// Valores provisorios: a varredura 't' do sketch de teste mede os ideais.
#define AMOSTRAS_PADRAO        4
#define ACOMODACAO_US_PADRAO  20
#define DESCARTE_PADRAO       true

#define DELTA_MINIMO      150   // contraste minimo (cru) aceito na calibracao
#define LIMIAR_ATIV        80   // variacao minima (cru) para considerar canal conectado
#define LIMIAR_RUIDO       50   // normalizado 0..1000: abaixo disso fica fora da media
#define LIMIAR_LINHA      200   // normalizado 0..1000: algum sensor acima disso = linha vista
#define LIMIAR_SATURACAO 4090   // cru: a partir daqui o ADC esta saturado

// Calibracao: o min/max sai da media movel das ultimas JANELA_CALIBRACAO
// leituras, e nao de leituras soltas. Um pico isolado entra dividido pela
// janela, em vez de virar o minimo ou o maximo do sensor.
#define JANELA_CALIBRACAO   4

struct PinosBarra {
  uint8_t s[4];   // S0..S3 do mux
  uint8_t sig;    // saida comum do mux (pino do ADC1)
};

enum CorLinha : uint8_t {
  LINHA_PRETA  = 0,   // linha preta em fundo branco
  LINHA_BRANCA = 1    // linha branca em fundo preto
};

struct ResultadoCalibracao {
  bool     aceita;
  bool     manteveAnterior;      // rejeitada, mas a calibracao anterior continua valendo
  uint8_t  semContraste;         // sensores com delta < DELTA_MINIMO
  uint8_t  saturados;            // sensores com max >= LIMIAR_SATURACAO
  uint16_t vMin[NUM_SENSORS];    // valores desta tentativa
  uint16_t vMax[NUM_SENSORS];
};

struct ResultadoMapa {
  uint16_t cMin[NUM_CANAIS];
  uint16_t cMax[NUM_CANAIS];
  uint8_t  ativos[NUM_CANAIS];   // canais com variacao > LIMIAR_ATIV, em ordem crescente
  uint8_t  nAtivos;
  bool     confere;              // os canais ativos sao exatamente os do mapa
};

struct EstadoNVS {
  bool calibracao;               // carregados da NVS
  bool cor;
  bool calibracaoInvalida;       // estava na NVS, mas foi ignorada (outro mapa ou dados ruins)
};

class Barra {
public:
  static constexpr uint16_t LEITURA_MAX = 4095;                     // ADC de 12 bits
  static constexpr uint16_t POS_MAX     = (NUM_SENSORS - 1) * 1000;  // 11000
  static constexpr uint16_t POS_CENTRO  = POS_MAX / 2;               // 5500

  void begin(const PinosBarra& pinos, CorLinha cor);
  void restaurarPadroes();       // sem calibracao, cor do begin()

  // ---- Leitura: uma chamada de atualizar() por ciclo ----
  void     atualizar();          // le os 12 sensores e calcula posicao, erro e perda
  uint16_t posicao() const              { return _posicao; }      // 0..POS_MAX
  int16_t  erro() const                 { return _erro; }         // posicao - POS_CENTRO
  bool     linhaPerdida() const         { return _perdida; }      // posicao vai ao extremo
  uint16_t bruto(uint8_t i) const       { return _raw[i]; }
  uint16_t normalizado(uint8_t i) const { return _norm[i]; }      // 0..1000, 1000 = linha
  uint32_t tempoLeituraUs() const       { return _tLeituraUs; }   // so a leitura dos 12

  void     configurarLeitura(uint8_t amostras, uint16_t acomodacaoUs, bool descarte);
  uint8_t  amostras() const             { return _amostras; }
  uint16_t acomodacaoUs() const         { return _acomodacaoUs; }
  bool     descarte() const             { return _descarte; }

  // ---- Acesso direto ao mux (conferencia de canais e diagnostico) ----
  void     selecionarCanal(uint8_t ch);       // so escreve S0..S3
  uint16_t lerCanal(uint8_t ch)           { return (uint16_t)amostrar(ch, false); }   // cru
  uint32_t lerCanalMilliVolts(uint8_t ch) { return amostrar(ch, true); }
  const PinosBarra& pinos() const       { return _pinos; }

  // ---- Calibracao por minimo e maximo (quem chama controla o tempo) ----
  void iniciarCalibracao();
  void amostrarCalibracao();                  // le os 12 e atualiza min/max da media movel
  ResultadoCalibracao finalizarCalibracao();  // rejeita se algum sensor nao tiver contraste
  void descartarCalibracao();
  bool     calibrado() const            { return _calibrado; }
  uint16_t vMin(uint8_t i) const        { return _vMin[i]; }
  uint16_t vMax(uint8_t i) const        { return _vMax[i]; }

  // ---- Conferencia dos canais (quem chama controla o tempo) ----
  void iniciarMapeamento();
  void amostrarMapeamento();                  // le os 16 canais e atualiza min/max
  const ResultadoMapa& finalizarMapeamento(); // so confere; nao altera o mapa
  uint8_t canalDoSensor(uint8_t i) const { return _canal[i]; }

  // ---- Cor da linha ----
  void     setCorLinha(CorLinha cor);
  CorLinha corLinha() const             { return _cor; }

  // ---- NVS (Preferences, namespace "barra") ----
  EstadoNVS carregarNVS();
  bool salvarCalibracao();       // grava junto o mapa em que ela foi feita
  bool salvarCor();
  bool apagarCalibracaoNVS();
  bool apagarNVS();              // calibracao e cor

private:
  // troca o canal, espera a acomodacao, descarta e tira a media
  uint32_t amostrar(uint8_t ch, bool emMilliVolts);
  void     lerBrutos();
  void     calcularPosicao();
  uint16_t normalizar(uint8_t i) const;

  PinosBarra _pinos = {};
  uint8_t  _canal[NUM_SENSORS] = MAPA_PADRAO;
  uint16_t _raw[NUM_SENSORS] = {};
  uint16_t _norm[NUM_SENSORS] = {};
  uint16_t _vMin[NUM_SENSORS] = {};
  uint16_t _vMax[NUM_SENSORS] = {};
  uint16_t _calMin[NUM_SENSORS] = {};
  uint16_t _calMax[NUM_SENSORS] = {};
  uint16_t _calHist[NUM_SENSORS][JANELA_CALIBRACAO] = {};   // janela circular
  uint32_t _calSoma[NUM_SENSORS] = {};
  uint8_t  _calPos = 0;
  uint8_t  _calCheia = 0;        // leituras na janela, ate JANELA_CALIBRACAO
  ResultadoMapa _mapa = {};

  bool     _calibrado = false;
  CorLinha _cor = LINHA_PRETA;
  CorLinha _corPadrao = LINHA_PRETA;
  uint8_t  _amostras = AMOSTRAS_PADRAO;
  uint16_t _acomodacaoUs = ACOMODACAO_US_PADRAO;
  bool     _descarte = DESCARTE_PADRAO;

  uint16_t _posicao = POS_CENTRO;
  uint16_t _ultimaPosicao = POS_CENTRO;
  int16_t  _erro = 0;
  bool     _perdida = true;
  uint32_t _tLeituraUs = 0;
};
