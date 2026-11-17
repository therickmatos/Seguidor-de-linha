/*
 * Teste de bancada: barra QRE1113 (12 sensores) + MUX 74HC4067
 * Placa: ESP32-C3 Super Mini (Arduino-ESP32 core 3.x)
 *
 * A leitura da barra fica em barra.h/.cpp (vai para o firmware final);
 * este sketch e so a interface serial em cima do modulo.
 *
 * O Serial sai pela USB nativa do C3: Ferramentas > USB CDC On Boot: Enabled
 * (arduino-cli: --fqbn esp32:esp32:esp32c3:CDCOnBoot=cdc).
 *
 * Comandos no monitor serial:
 *   m -> conferir canais do mux (8 s, passe a mao sobre a barra)
 *   c -> calibrar (10 s); uma pressao no botao BOOT faz o mesmo
 *   d -> diagnostico estatico (cru, mV, margem, calibracao, linhas S0..S3)
 *   r -> descartar calibracao (RAM e NVS)
 *   l -> alternar linha preta / branca (salva na NVS)
 *   p -> ligar/desligar a saida CSV (Serial Plotter)
 *   t -> varredura de tempo (AMOSTRAS x acomodacao x descarte)
 *   x -> apagar a NVS (envie 'x' de novo em ate 5 s para confirmar)
 *   ? -> ajuda e estado atual
 */

#include <inttypes.h>
#include "barra.h"

#if !ARDUINO_USB_CDC_ON_BOOT
#error "Ative Ferramentas > USB CDC On Boot: Enabled (arduino-cli: --fqbn esp32:esp32:esp32c3:CDCOnBoot=cdc)"
#endif

// ================== Configuracao (todos os pinos aqui) ==================
// Nao usar GPIO8 (LED da placa), GPIO20 e GPIO21 (UART0) neste sketch.
#define PINO_S0      5
#define PINO_S1      6
#define PINO_S2      7
#define PINO_S3     10
#define PINO_SIG     3     // saida comum do mux (ADC1_CH3)
#define PINO_BOTAO   9     // BOOT, ativo em baixo (pull-up interno)

#define COR_LINHA_PADRAO  LINHA_PRETA   // ou LINHA_BRANCA; o comando 'l' troca e salva

#define TEMPO_MAPEAMENTO_MS    8000
#define TEMPO_CALIBRACAO_MS   10000
#define INTERVALO_LEGIVEL_MS    100
#define INTERVALO_CSV_MS         20
#define DEBOUNCE_MS              30
#define CONFIRMA_APAGAR_MS     5000
#define MV_FAIXA_UTIL          2500    // faixa calibrada do ADC do C3 em 11 dB

// Varredura de tempo ('t')
#define VARR_CICLOS            200     // leituras dos 12 sensores por combinacao
#define VARR_TOL_RUIDO         5.0f    // sigma maximo no pior sensor (escala 0..1000)
#define VARR_TOL_DESVIO       10.0f    // desvio maximo da media vs referencia (escala 0..1000)
#define VARR_REF_AMOSTRAS       16
#define VARR_REF_ACOMOD_US     100
const uint8_t  VARR_AMOSTRAS[]  = {1, 2, 4, 8};
const uint16_t VARR_ACOMOD_US[] = {0, 5, 10, 20, 40, 80};
// ========================================================================

constexpr uint8_t N_AMOSTRAS = sizeof(VARR_AMOSTRAS) / sizeof(VARR_AMOSTRAS[0]);
constexpr uint8_t N_ACOMOD   = sizeof(VARR_ACOMOD_US) / sizeof(VARR_ACOMOD_US[0]);
constexpr uint8_t N_COMBOS   = N_AMOSTRAS * N_ACOMOD * 2;   // descarte sim e nao

struct Medida {
  uint8_t  amostras;
  uint16_t acomodUs;
  bool     descarte;
  float    media[NUM_SENSORS];   // cru
  float    sigma[NUM_SENSORS];   // cru
  uint32_t tMedUs;
  uint32_t tMaxUs;
};

Barra barra;
bool modoCsv = false;

// tempo de leitura acumulado entre duas linhas impressas
uint32_t somaTempoUs = 0, maxTempoUs = 0, nLeituras = 0;
uint32_t tUltimaLinha = 0;

// botao (LOW = pressionado)
int botaoLido = HIGH, botaoEstavel = HIGH;
uint32_t tMudancaBotao = 0;

bool pedidoApagar = false;
uint32_t tPedidoApagar = 0;

Medida combos[N_COMBOS];   // varredura: global para nao ocupar a pilha
Medida ref1, ref2;

// ------------------------------------------------------------ utilidades

const char* nomeCor(CorLinha cor) {
  return cor == LINHA_PRETA ? "PRETA em fundo branco" : "BRANCA em fundo preto";
}

uint32_t segundosRestantes(uint32_t t0, uint32_t totalMs) {
  uint32_t decorrido = millis() - t0;
  return decorrido < totalMs ? (totalMs - decorrido) / 1000 : 0;
}

// Espera (no maximo 100 ms) ate caber n bytes no buffer de TX do USB.
// So nas rotinas de bancada que imprimem muitas linhas seguidas.
void esperarTx(int n) {
  uint32_t t0 = millis();
  while (Serial.availableForWrite() < n && millis() - t0 < 100) delay(1);
}

void zerarTempos() {
  somaTempoUs = 0;
  maxTempoUs = 0;
  nLeituras = 0;
}

void mostrarMapa() {
  Serial.print(F("#define MAPA_PADRAO  {"));
  for (uint8_t i = 0; i < NUM_SENSORS; i++) {
    Serial.print(barra.canalDoSensor(i));
    if (i < NUM_SENSORS - 1) Serial.print(F(", "));
  }
  Serial.println(F("}"));
}

void mostrarEstado() {
  Serial.print(F("Mapa (barra.h): "));
  mostrarMapa();
  Serial.printf("Linha %s | calibrada: %s\n", nomeCor(barra.corLinha()),
                barra.calibrado() ? "sim" : "nao");
  Serial.printf("Leitura: amostras=%u acomodacao=%uus descarte=%s\n",
                (unsigned)barra.amostras(), (unsigned)barra.acomodacaoUs(),
                barra.descarte() ? "sim" : "nao");
}

void ajuda() {
  Serial.println(F("Comandos: m=conferir canais  c=calibrar (ou botao BOOT)  d=diagnostico  r=descartar calib."));
  Serial.println(F("          l=linha preta/branca  p=CSV liga/desliga  t=varredura de tempo"));
  Serial.println(F("          x=apagar NVS  ?=ajuda"));
}

// ------------------------------------------------------------ saidas

void imprimirLegivel(uint32_t tMedio) {
  for (uint8_t i = 0; i < NUM_SENSORS; i++) {
    Serial.printf("%4u ", (unsigned)(barra.calibrado() ? barra.normalizado(i) : barra.bruto(i)));
  }
  if (barra.calibrado()) {
    Serial.printf("| pos=%5u  erro=%+6d %s", (unsigned)barra.posicao(), (int)barra.erro(),
                  barra.linhaPerdida() ? "PERDIDA" : "       ");
  }
  Serial.printf(" | t=%4" PRIu32 "us max=%4" PRIu32 "us\n", tMedio, maxTempoUs);
}

// s0..s11 (normalizados se calibrado, senao crus), pos, erro, perdida, t_us
// Sem calibracao a posicao nao significa nada: sai pos=0, erro=0, perdida=1.
void imprimirCsv(uint32_t tMedio) {
  bool cal = barra.calibrado();
  for (uint8_t i = 0; i < NUM_SENSORS; i++) {
    Serial.printf("%u,", (unsigned)(cal ? barra.normalizado(i) : barra.bruto(i)));
  }
  Serial.printf("%u,%d,%u,%" PRIu32 "\n",
                cal ? (unsigned)barra.posicao() : 0u,
                cal ? (int)barra.erro() : 0,
                (!cal || barra.linhaPerdida()) ? 1u : 0u, tMedio);
}

// ------------------------------------------------------------ conferencia dos canais

bool canalAtivo(const ResultadoMapa& r, uint8_t c) {
  for (uint8_t i = 0; i < r.nAtivos; i++) {
    if (r.ativos[i] == c) return true;
  }
  return false;
}

bool canalNoMapa(uint8_t c) {
  for (uint8_t i = 0; i < NUM_SENSORS; i++) {
    if (barra.canalDoSensor(i) == c) return true;
  }
  return false;
}

// So confere: o mapa vale o MAPA_PADRAO de barra.h e nao e alterado aqui.
void mapear() {
  Serial.printf("\n>> CONFERENCIA DOS CANAIS: passe a mao sobre TODA a barra por %u s...\n",
                (unsigned)(TEMPO_MAPEAMENTO_MS / 1000));

  barra.iniciarMapeamento();
  uint32_t t0 = millis(), tPrint = 0;
  while (millis() - t0 < TEMPO_MAPEAMENTO_MS) {
    barra.amostrarMapeamento();
    if (millis() - tPrint >= 1000) {
      tPrint = millis();
      Serial.printf("   [lendo... %" PRIu32 "s]\n", segundosRestantes(t0, TEMPO_MAPEAMENTO_MS));
    }
  }

  const ResultadoMapa& r = barra.finalizarMapeamento();
  Serial.println(F("\n>> Resultado por canal do mux:"));
  for (uint8_t c = 0; c < NUM_CANAIS; c++) {
    int32_t var = (int32_t)r.cMax[c] - (int32_t)r.cMin[c];
    esperarTx(80);
    Serial.printf("   C%-2u %-9s min=%4u max=%4u var=%4" PRId32 "  %s\n",
                  (unsigned)c, canalNoMapa(c) ? "(mapeado)" : "",
                  (unsigned)r.cMin[c], (unsigned)r.cMax[c], var,
                  var > LIMIAR_ATIV ? "ATIVO" : "-- parado");
  }

  Serial.printf("\n>> %u canais ativos de %u sensores esperados.\n",
                (unsigned)r.nAtivos, (unsigned)NUM_SENSORS);

  if (r.confere) {
    Serial.println(F(">> OK: os canais ativos sao exatamente os do MAPA_PADRAO."));
    Serial.println(F("   Ordem: tampe so uma ponta da barra e veja se quem muda e o S0 ou o S11;"));
    Serial.println(F("   se estiver ao contrario do que voce quer, inverta o MAPA_PADRAO em barra.h."));
  } else {
    for (uint8_t i = 0; i < NUM_SENSORS; i++) {
      uint8_t c = barra.canalDoSensor(i);
      if (!canalAtivo(r, c)) {
        Serial.printf("   S%u (C%u) esta no mapa e NAO respondeu\n", (unsigned)i, (unsigned)c);
      }
    }
    for (uint8_t i = 0; i < r.nAtivos; i++) {
      if (!canalNoMapa(r.ativos[i])) {
        Serial.printf("   C%u respondeu e NAO esta no mapa\n", (unsigned)r.ativos[i]);
      }
    }
    if (r.nAtivos == NUM_SENSORS) {
      Serial.println(F(">> A barra usa outros canais. Troque em barra.h, regrave e recalibre:"));
      Serial.print(F("#define MAPA_PADRAO  {"));
      for (uint8_t i = 0; i < r.nAtivos; i++) {
        Serial.print(r.ativos[i]);
        if (i < r.nAtivos - 1) Serial.print(F(", "));
      }
      Serial.println(F("}"));
      Serial.println(F("   (ordem crescente; se a barra estiver espelhada, inverta)"));
    } else if (r.nAtivos < NUM_SENSORS) {
      Serial.println(F(">> Faltam canais. Possiveis causas:"));
      Serial.printf("   - a mao nao cobriu toda a barra durante os %u s\n",
                    (unsigned)(TEMPO_MAPEAMENTO_MS / 1000));
      Serial.println(F("   - sensor ou trilha aberta (ver continuidade)"));
    } else {
      Serial.println(F(">> Ativos demais. Entrada vazia do mux flutua e pode variar com a mao perto;"));
      Serial.println(F("   se for so isso, ignore. Senao, reduza o ruido ou aumente LIMIAR_ATIV."));
    }
  }
  Serial.println();
}

// ------------------------------------------------------------ calibracao

void calibrar() {
  Serial.printf(">> Calibrando por %u s. Varra a linha lateralmente (vaivem)...\n",
                (unsigned)(TEMPO_CALIBRACAO_MS / 1000));

  barra.iniciarCalibracao();
  uint32_t t0 = millis(), tPrint = 0;
  while (millis() - t0 < TEMPO_CALIBRACAO_MS) {
    barra.amostrarCalibracao();
    if (millis() - tPrint >= 100) {
      tPrint = millis();
      for (uint8_t i = 0; i < NUM_SENSORS; i++) Serial.printf("%4u ", (unsigned)barra.bruto(i));
      Serial.printf("[calibrando... %" PRIu32 "s]\n", segundosRestantes(t0, TEMPO_CALIBRACAO_MS));
    }
  }

  ResultadoCalibracao r = barra.finalizarCalibracao();
  Serial.printf(">> Resultado (min/max da media movel de %u leituras):\n", (unsigned)JANELA_CALIBRACAO);
  for (uint8_t i = 0; i < NUM_SENSORS; i++) {
    int32_t d = (int32_t)r.vMax[i] - (int32_t)r.vMin[i];
    esperarTx(80);
    Serial.printf("S%-2u (C%-2u) min=%4u max=%4u delta=%4" PRId32 "  %s%s\n",
                  (unsigned)i, (unsigned)barra.canalDoSensor(i),
                  (unsigned)r.vMin[i], (unsigned)r.vMax[i], d,
                  d < DELTA_MINIMO ? "<-- CONTRASTE INSUFICIENTE" : "ok",
                  r.vMax[i] >= LIMIAR_SATURACAO ? "  [SATURADO]" : "");
  }

  if (r.saturados > 0) {
    Serial.printf(">> %u sensor(es) saturando (>= %u): tensao acima da faixa do ADC "
                  "(~%u mV em 11 dB). Veja os mV no 'd'.\n",
                  (unsigned)r.saturados, (unsigned)LIMIAR_SATURACAO, (unsigned)MV_FAIXA_UTIL);
  }

  if (r.aceita) {
    Serial.println(barra.salvarCalibracao() ? F(">> Calibracao aceita e salva na NVS.")
                                            : F(">> Calibracao aceita, mas ERRO ao salvar na NVS."));
  } else {
    Serial.printf(">> REJEITADA: %u sensor(es) sem contraste. %s\n", (unsigned)r.semContraste,
                  r.manteveAnterior ? "Mantendo a calibracao anterior." : "Mantendo leitura crua.");
  }
}

// ------------------------------------------------------------ diagnostico

void diagnostico() {
  Serial.println(F("\n===== DIAGNOSTICO ====="));
  mostrarEstado();

  // cru e mV sao conversoes separadas (a API do Arduino nao da os dois de uma vez)
  Serial.printf("\n[1] Varredura estatica dos 16 canais (faixa calibrada do ADC: ate %u mV):\n",
                (unsigned)MV_FAIXA_UTIL);
  for (uint8_t ch = 0; ch < NUM_CANAIS; ch++) {
    uint16_t v = barra.lerCanal(ch);
    uint32_t mv = barra.lerCanalMilliVolts(ch);
    esperarTx(100);
    Serial.printf("  C%-2u %-9s = %4u  %4" PRIu32 " mV  ", (unsigned)ch,
                  canalNoMapa(ch) ? "(mapeado)" : "", (unsigned)v, mv);
    if (v >= LIMIAR_SATURACAO) {
      Serial.println(F("SATURADO: a tensao real e maior ou igual a mostrada"));
    } else if (mv > MV_FAIXA_UTIL) {
      Serial.println(F("acima da faixa calibrada"));
    } else {
      Serial.printf("margem %4" PRIu32 " mV\n", (uint32_t)(MV_FAIXA_UTIL - mv));
    }
  }

  Serial.println(F("\n[2] Calibracao atual:"));
  if (!barra.calibrado()) {
    Serial.println(F("  (sem calibracao)"));
  } else {
    for (uint8_t i = 0; i < NUM_SENSORS; i++) {
      esperarTx(80);
      Serial.printf("  S%-2u (C%-2u) min=%4u max=%4u delta=%4d%s\n",
                    (unsigned)i, (unsigned)barra.canalDoSensor(i),
                    (unsigned)barra.vMin(i), (unsigned)barra.vMax(i),
                    (int)barra.vMax(i) - (int)barra.vMin(i),
                    barra.vMax(i) >= LIMIAR_SATURACAO ? "  [SATURADO]" : "");
    }
  }

  Serial.println(F("\n[3] Teste das linhas de selecao (meca com multimetro):"));
  for (uint8_t b = 0; b < 4; b++) {
    Serial.printf("  S%u/GPIO%u em 3.3V por 2 s...\n", (unsigned)b, (unsigned)barra.pinos().s[b]);
    barra.selecionarCanal(1 << b);   // so a linha b em nivel alto
    delay(2000);
  }
  barra.selecionarCanal(0);
  Serial.println(F("  Fim.\n"));
}

// ------------------------------------------------------------ varredura de tempo

float faixaCal(uint8_t i) {
  return (float)((int)barra.vMax(i) - (int)barra.vMin(i));   // >= DELTA_MINIMO se calibrado
}

void medir(Medida& m) {
  barra.configurarLeitura(m.amostras, m.acomodUs, m.descarte);
  uint32_t soma[NUM_SENSORS] = {};
  uint64_t soma2[NUM_SENSORS] = {};
  uint32_t somaT = 0, maxT = 0;

  for (uint16_t k = 0; k < VARR_CICLOS; k++) {
    barra.atualizar();
    uint32_t t = barra.tempoLeituraUs();
    somaT += t;
    if (t > maxT) maxT = t;
    for (uint8_t i = 0; i < NUM_SENSORS; i++) {
      uint32_t v = barra.bruto(i);
      soma[i] += v;
      soma2[i] += (uint64_t)v * v;
    }
  }

  for (uint8_t i = 0; i < NUM_SENSORS; i++) {
    // variancia exata em inteiros: (N*soma2 - soma^2) / N^2
    uint64_t num = (uint64_t)VARR_CICLOS * soma2[i] - (uint64_t)soma[i] * soma[i];
    m.media[i] = (float)soma[i] / VARR_CICLOS;
    m.sigma[i] = (float)(sqrt((double)num) / VARR_CICLOS);
  }
  m.tMedUs = somaT / VARR_CICLOS;
  m.tMaxUs = maxT;
}

void prepararMedida(Medida& m, uint8_t amostras, uint16_t acomodUs, bool descarte) {
  m.amostras = amostras;
  m.acomodUs = acomodUs;
  m.descarte = descarte;
}

void varreduraTempo() {
  if (!barra.calibrado()) {
    Serial.println(F(">> Calibre antes ('c'): o criterio usa a escala 0..1000 da calibracao."));
    return;
  }
  const uint8_t  amostrasAntes = barra.amostras();
  const uint16_t acomodAntes   = barra.acomodacaoUs();
  const bool     descarteAntes = barra.descarte();

  Serial.printf("\n>> VARREDURA DE TEMPO: %u combinacoes x %u leituras. Deixe a barra PARADA.\n",
                (unsigned)N_COMBOS, (unsigned)VARR_CICLOS);
  Serial.printf("   Criterio: sigma <= %.1f e desvio <= %.1f (escala 0..1000) no pior sensor.\n",
                VARR_TOL_RUIDO, VARR_TOL_DESVIO);

  prepararMedida(ref1, VARR_REF_AMOSTRAS, VARR_REF_ACOMOD_US, true);
  medir(ref1);

  // Sem saltos entre canais claros e escuros, o erro de acomodacao nao aparece.
  bool temAlto = false, temBaixo = false;
  for (uint8_t i = 0; i < NUM_SENSORS; i++) {
    float n = (ref1.media[i] - barra.vMin(i)) * 1000.0f / faixaCal(i);
    if (n > 500) temAlto = true;
    if (n < LIMIAR_RUIDO) temBaixo = true;
  }
  if (!temAlto || !temBaixo) {
    Serial.println(F("   AVISO: nao ha sensores no claro e no escuro ao mesmo tempo. Ponha a linha"));
    Serial.println(F("   sob 1-2 sensores, senao o erro de acomodacao nao aparece no teste."));
  }

  uint8_t k = 0;
  for (uint8_t d = 0; d < 2; d++) {
    for (uint8_t u = 0; u < N_ACOMOD; u++) {
      for (uint8_t a = 0; a < N_AMOSTRAS; a++) {
        Medida& m = combos[k++];
        prepararMedida(m, VARR_AMOSTRAS[a], VARR_ACOMOD_US[u], d == 0);
        medir(m);
        Serial.print('.');
      }
    }
  }
  prepararMedida(ref2, VARR_REF_AMOSTRAS, VARR_REF_ACOMOD_US, true);
  medir(ref2);
  Serial.println();

  // referencia = media do inicio e do fim; a diferenca entre elas mede a deriva da cena
  float refMedia[NUM_SENSORS];
  float deriva = 0, sigmaRef = 0;
  uint8_t sDeriva = 0, sSigmaRef = 0;
  for (uint8_t i = 0; i < NUM_SENSORS; i++) {
    refMedia[i] = (ref1.media[i] + ref2.media[i]) / 2;
    float dv = fabsf(ref1.media[i] - ref2.media[i]) * 1000.0f / faixaCal(i);
    if (dv > deriva) { deriva = dv; sDeriva = i; }
    float s = ref1.sigma[i] * 1000.0f / faixaCal(i);
    if (s > sigmaRef) { sigmaRef = s; sSigmaRef = i; }
  }
  Serial.printf("   Referencia (%u amostras, %uus, descarte): t_med=%" PRIu32 "us  t_max=%" PRIu32
                "us  sigma=%.1f (S%u)\n",
                (unsigned)VARR_REF_AMOSTRAS, (unsigned)VARR_REF_ACOMOD_US,
                ref1.tMedUs, ref1.tMaxUs, sigmaRef, (unsigned)sSigmaRef);

  Serial.println(F("\n amost acomod desc |  t_med  t_max |  sigma (S)  | desvio (S)  | ok"));
  int melhor = -1;
  for (uint8_t j = 0; j < N_COMBOS; j++) {
    const Medida& m = combos[j];
    float sMax = 0, dMax = 0;
    uint8_t sIdx = 0, dIdx = 0;
    for (uint8_t i = 0; i < NUM_SENSORS; i++) {
      float s = m.sigma[i] * 1000.0f / faixaCal(i);
      float dv = fabsf(m.media[i] - refMedia[i]) * 1000.0f / faixaCal(i);
      if (s > sMax) { sMax = s; sIdx = i; }
      if (dv > dMax) { dMax = dv; dIdx = i; }
    }
    bool ok = sMax <= VARR_TOL_RUIDO && dMax <= VARR_TOL_DESVIO;
    if (ok && (melhor < 0 || m.tMedUs < combos[melhor].tMedUs)) melhor = j;

    esperarTx(100);
    Serial.printf("  %3u  %4uus  %s | %6" PRIu32 " %6" PRIu32 " | %5.1f (S%-2u) | %5.1f (S%-2u) | %s\n",
                  (unsigned)m.amostras, (unsigned)m.acomodUs, m.descarte ? "sim" : "nao",
                  m.tMedUs, m.tMaxUs, sMax, (unsigned)sIdx, dMax, (unsigned)dIdx,
                  ok ? "OK" : "--");
  }

  bool cenaOk = deriva <= VARR_TOL_DESVIO / 2;
  Serial.printf("\n>> Deriva da referencia (inicio x fim): %.1f (S%u)  %s\n", deriva, (unsigned)sDeriva,
                cenaOk ? "ok" : "ALTA: a cena mudou durante o teste, repita");

  if (!cenaOk || melhor < 0) {
    barra.configurarLeitura(amostrasAntes, acomodAntes, descarteAntes);
    Serial.println(cenaOk ? F(">> Nenhuma combinacao passou no criterio. Configuracao anterior mantida.")
                          : F(">> Sem recomendacao. Configuracao anterior mantida."));
    Serial.println();
    return;
  }

  const Medida& r = combos[melhor];
  barra.configurarLeitura(r.amostras, r.acomodUs, r.descarte);
  Serial.printf(">> Recomendado: amostras=%u acomodacao=%uus descarte=%s -> t_med=%" PRIu32
                "us (t_max=%" PRIu32 "us)\n",
                (unsigned)r.amostras, (unsigned)r.acomodUs, r.descarte ? "sim" : "nao",
                r.tMedUs, r.tMaxUs);
  Serial.println(F(">> Aplicado ate o reset. Para fixar, mude AMOSTRAS_PADRAO, ACOMODACAO_US_PADRAO"));
  Serial.println(F("   e DESCARTE_PADRAO em barra.h e recalibre com a configuracao nova."));
  Serial.println();
}

// ------------------------------------------------------------ comandos

void descartar() {
  barra.descartarCalibracao();
  Serial.println(barra.apagarCalibracaoNVS() ? F(">> Calibracao descartada (RAM e NVS).")
                                             : F(">> Calibracao descartada, mas ERRO ao apagar da NVS."));
}

void alternarCor() {
  barra.setCorLinha(barra.corLinha() == LINHA_PRETA ? LINHA_BRANCA : LINHA_PRETA);
  bool ok = barra.salvarCor();
  Serial.printf(">> Linha %s (%s).\n", nomeCor(barra.corLinha()),
                ok ? "cor salva na NVS" : "ERRO ao salvar a cor na NVS");
}

void alternarCsv() {
  modoCsv = !modoCsv;
  if (modoCsv) {
    // cabecalho; o Serial Plotter nao usa e mostra as series como value 1..16 nesta ordem
    for (uint8_t i = 0; i < NUM_SENSORS; i++) Serial.printf("s%u,", (unsigned)i);
    Serial.println(F("pos,erro,perdida,t_us"));
  } else {
    Serial.println(F(">> Saida legivel."));
  }
}

void pedirApagarNVS() {
  uint32_t agora = millis();
  if (pedidoApagar && agora - tPedidoApagar <= CONFIRMA_APAGAR_MS) {
    pedidoApagar = false;
    if (barra.apagarNVS()) {
      barra.restaurarPadroes();
      Serial.println(F(">> NVS apagada. Sem calibracao e com a cor padrao."));
      mostrarEstado();
    } else {
      Serial.println(F(">> ERRO ao apagar a NVS."));
    }
  } else {
    pedidoApagar = true;
    tPedidoApagar = agora;
    Serial.printf(">> Apagar calibracao e cor da NVS? Envie 'x' de novo em ate %u s.\n",
                  (unsigned)(CONFIRMA_APAGAR_MS / 1000));
  }
}

// ------------------------------------------------------------ entradas

void processarBotao() {
  int lido = digitalRead(PINO_BOTAO);
  uint32_t agora = millis();
  if (lido != botaoLido) {
    botaoLido = lido;
    tMudancaBotao = agora;
  } else if (lido != botaoEstavel && agora - tMudancaBotao >= DEBOUNCE_MS) {
    botaoEstavel = lido;
    if (botaoEstavel == LOW) {   // so rearma depois de soltar
      Serial.println(F("\n>> Botao: iniciando calibracao."));
      calibrar();
      zerarTempos();
    }
  }
}

void processarSerial() {
  if (Serial.available() <= 0) return;
  char cmd = (char)Serial.read();
  switch (cmd) {
    case 'm': mapear(); break;
    case 'c': calibrar(); break;
    case 'd': diagnostico(); break;
    case 'r': descartar(); break;
    case 'l': alternarCor(); break;
    case 'p': alternarCsv(); break;
    case 't': varreduraTempo(); break;
    case 'x': pedirApagarNVS(); return;   // nao cancela o proprio pedido
    case '?': ajuda(); mostrarEstado(); break;
    default: return;                      // '\n', '\r' e desconhecidos
  }
  pedidoApagar = false;   // outro comando cancela o pedido de apagar
  zerarTempos();
}

// ------------------------------------------------------------ setup / loop

void setup() {
  // USB CDC: buffer maior e sem espera, para o loop nunca travar quando
  // ninguem le a porta (monitor fechado com o cabo no PC).
  // Nao chamar Serial.flush(): com timeout 0 ele descarta o buffer.
  Serial.setTxBufferSize(4096);
  Serial.setTxTimeoutMs(0);
  Serial.begin(115200);

  pinMode(PINO_BOTAO, INPUT_PULLUP);

  const PinosBarra pinos = {{PINO_S0, PINO_S1, PINO_S2, PINO_S3}, PINO_SIG};
  barra.begin(pinos, COR_LINHA_PADRAO);
  EstadoNVS nvs = barra.carregarNVS();

  Serial.printf("\nQRE1113 x%u + 74HC4067 pronto (ESP32-C3).\n", (unsigned)NUM_SENSORS);
  Serial.printf("Pinos: S0..S3=GPIO%u,%u,%u,%u  SIG=GPIO%u  botao=GPIO%u\n",
                (unsigned)PINO_S0, (unsigned)PINO_S1, (unsigned)PINO_S2, (unsigned)PINO_S3,
                (unsigned)PINO_SIG, (unsigned)PINO_BOTAO);
  Serial.printf("NVS: calibracao %s | cor %s\n",
                nvs.calibracao ? "carregada"
                               : (nvs.calibracaoInvalida ? "ignorada (outro mapa ou dados invalidos)" : "nenhuma"),
                nvs.cor ? "carregada" : "padrao");
  mostrarEstado();
  ajuda();
  Serial.println();
}

void loop() {
  processarSerial();
  processarBotao();

  barra.atualizar();   // posicao e erro saem desta mesma leitura
  uint32_t t = barra.tempoLeituraUs();
  somaTempoUs += t;
  nLeituras++;
  if (t > maxTempoUs) maxTempoUs = t;

  uint32_t agora = millis();
  uint32_t intervalo = modoCsv ? INTERVALO_CSV_MS : INTERVALO_LEGIVEL_MS;
  if (agora - tUltimaLinha >= intervalo) {
    tUltimaLinha = agora;
    uint32_t tMedio = nLeituras ? somaTempoUs / nLeituras : 0;
    if (modoCsv) imprimirCsv(tMedio);
    else imprimirLegivel(tMedio);
    zerarTempos();
  }
}
