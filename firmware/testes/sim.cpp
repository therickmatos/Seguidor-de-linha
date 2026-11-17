/*
 * sim.cpp - roda o controle do firmware (linha.cpp + corrida.cpp) no PC
 *
 * Baseado no EVA-RT 1.2.2 (c) 2025 EXOTIC TEAM MX, licenca AGPL-3.0
 *
 * Confere a logica e os sinais (lado do erro, roda que acelera, marcas,
 * cruzamento, parada, perda da linha) sem o robo. NAO serve para ajustar
 * ganhos nem o freio: o modelo dos motores e inventado (velocidade
 * proporcional ao PWM com atraso de primeira ordem, sem escorregar).
 *
 * Rodar nesta pasta:
 *   g++ -O2 -std=c++11 -I../seguidor sim.cpp ../seguidor/linha.cpp \
 *       ../seguidor/corrida.cpp -o sim && ./sim
 *
 * Alem de uma pista de ensaio curta, roda os modelos das pistas TRIF 2025 e
 * 2024 do estudo de caso (pasta pistas, gerada por exportar_pistas.py).
 *
 * Geometria: barra em arco de R 180 mm, 12 sensores a cada 7,8 mm (Gerber
 * da V1), 107,1 mm a frente do eixo (63,14 mm entre os furos da base e da
 * barra); sensores de marca externos do Saturn v12 (S1/S4, os unicos que o
 * firmware le) em x = +-81,5 mm, 38,6 mm a frente do eixo. Pista: linha de 19 mm, marcas de 40 x 19 mm a
 * 49,5 mm do centro da linha (regulamento RoboCore/TRIF).
 */
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

#include "corrida.h"

static const double PI = 3.14159265358979;

// ------------------------------------------------------------------ pista

struct Trecho { double comprimento, curvatura; };   // mm, 1/mm (+ = esquerda)
struct Ponto  { double x, y, th; };
struct Faixa  { double s, tangente; };              // cruzamento em s, inclinado

struct Pista {
  std::vector<Ponto>  pt;          // a cada PASSO mm
  std::vector<double> marcasEsq;   // s das marcas de mudanca de curvatura
  std::vector<double> marcasDir;   // partida, chegada
  std::vector<Faixa>  faixas;
  double fim;                      // a linha acaba aqui (mm)
};
static const double PASSO = 0.5;

static Pista montar(const std::vector<Trecho> &trechos) {
  Pista p;
  double x = 0, y = 0, th = 0, s = 0, kAnt = 0;
  p.pt.push_back({x, y, th});
  for (const Trecho &t : trechos) {
    if (t.curvatura != kAnt && s > 0) p.marcasEsq.push_back(s);
    kAnt = t.curvatura;
    int n = (int)std::lround(t.comprimento / PASSO);
    for (int i = 0; i < n; i++) {
      th += t.curvatura * PASSO;
      x += std::cos(th) * PASSO;
      y += std::sin(th) * PASSO;
      p.pt.push_back({x, y, th});
    }
    s += t.comprimento;
  }
  p.fim = s;
  return p;
}

// Pista fechada de pistas/*.txt, desenrolada em duas voltas. O robo larga
// 500 mm antes da marca de partida e a chegada e a da volta seguinte.
struct Circuito {
  Pista pista;
  double volta, sLargada, sChegada;
  unsigned marcasEsq;    // esperadas entre a partida e a chegada
};

static bool carregar(const std::string &arquivo, Circuito &c) {
  FILE *f = std::fopen(arquivo.c_str(), "r");
  if (!f) return false;
  std::vector<Trecho> umaVolta;
  std::vector<Faixa> cruz;
  double partida = 0, chegada = 0;
  char linha[200];
  while (std::fgets(linha, sizeof(linha), f)) {
    double a = 0, b = 0;
    if (std::sscanf(linha, "T %lf %lf", &a, &b) == 2) umaVolta.push_back({a, b});
    else if (std::sscanf(linha, "P %lf", &a) == 1) partida = a;
    else if (std::sscanf(linha, "C %lf", &a) == 1) chegada = a;
    else if (std::sscanf(linha, "X %lf %lf", &a, &b) == 2) cruz.push_back({a, b});
  }
  std::fclose(f);

  c.volta = 0;
  for (const Trecho &t : umaVolta) c.volta += t.comprimento;
  std::vector<Trecho> tudo = umaVolta;
  tudo.insert(tudo.end(), umaVolta.begin(), umaVolta.end());
  c.pista = montar(tudo);
  c.sLargada = partida - 500;
  c.sChegada = chegada + c.volta;
  c.pista.marcasDir = {partida, c.sChegada};
  for (int v = 0; v < 2; v++)
    for (const Faixa &x : cruz) c.pista.faixas.push_back({x.s + v * c.volta, x.tangente});
  c.marcasEsq = 0;
  for (double m : c.pista.marcasEsq)
    if (m > partida && m < c.sChegada) c.marcasEsq++;
  return true;
}

static double BORDA = 3.0;   // largura da borda borrada vista pelo sensor (mm)

static double rampa(double dentro, double borda) {   // 1 dentro, 0 fora
  double v = dentro / borda + 0.5;
  return v < 0 ? 0 : (v > 1 ? 1 : v);
}

// Indice do ponto da linha mais proximo de (px, py), procurando de 'de' a 'ate'
static int maisProximo(const Pista &p, double px, double py, int de, int ate) {
  int n = (int)p.pt.size();
  if (de < 0) de = 0;
  if (ate >= n) ate = n - 1;
  double melhor = 1e18;
  int j = de;
  for (int i = de; i <= ate; i++) {
    double dx = px - p.pt[i].x, dy = py - p.pt[i].y;
    double d2 = dx * dx + dy * dy;
    if (d2 < melhor) { melhor = d2; j = i; }
  }
  return j;
}

// Quanto de branco ha embaixo do ponto (0..1). 'eixo' e o indice do ponto da
// linha mais proximo do eixo do robo; devolve em 'j' o mais proximo do ponto.
static double branco(const Pista &p, double px, double py, int eixo, int &j) {
  j = maisProximo(p, px, py, eixo - 300, eixo + 600);   // -150 a +300 mm
  const Ponto &q = p.pt[j];
  double dx = px - q.x, dy = py - q.y;
  double lado = -std::sin(q.th) * dx + std::cos(q.th) * dy;      // + = esquerda
  double s = j * PASSO + std::cos(q.th) * dx + std::sin(q.th) * dy;

  const double B = BORDA;
  double w = 0;
  if (s <= p.fim) w = rampa(9.5 - std::fabs(lado), B);
  for (double m : p.marcasEsq) {
    double v = std::fmin(rampa(9.5 - std::fabs(s - m), B), rampa(20.0 - std::fabs(lado - 69.5), B));
    if (v > w) w = v;
  }
  for (double m : p.marcasDir) {
    double v = std::fmin(rampa(9.5 - std::fabs(s - m), B), rampa(20.0 - std::fabs(lado + 69.5), B));
    if (v > w) w = v;
  }
  for (const Faixa &f : p.faixas) {
    double v = std::fmin(rampa(9.5 - std::fabs(s - f.s - lado * f.tangente), B),
                         rampa(400.0 - std::fabs(lado), B));
    if (v > w) w = v;
  }
  return w;
}

// ------------------------------------------------------------------ robo

static const double L_BARRA = 107.1, R_ARCO = 180.0, PASSO_ANG = 2.4826 * PI / 180.0;
static const double X_MARCA = 81.5, Y_MARCA = 38.6;   // S1/S4: (+-81,5; 16) e eixo em y = -22,59
static const double BITOLA = 110.0;          // entre as rodas (mm)
static double MM_S_POR_PWM = 45.0;           // PWM 40 -> 1,8 m/s
static double TAU_MOTOR = 0.120;             // s

struct Robo {
  double x, y, th, vE, vD;
  int eixo;              // indice do ponto da linha mais proximo do eixo
  int onde[N_CANAIS];    // idem, de cada sensor
};

// Leitura bruta de cada canal no preto e no branco. A barra da alto no
// preto, as marcas alto no branco (como no robo).
static double PRETO[N_CANAIS], BRANCO[N_CANAIS];
static double ESCALA_BAT = 256;

static void sensoresIguais() {
  for (int i = 0; i < N_CANAIS; i++) {
    PRETO[i] = i < N_SENSORES ? 210 : 25;
    BRANCO[i] = i < N_SENSORES ? 40 : 215;
  }
}

static unsigned semente = 12345;
static double ruido() {   // -1..1
  semente = semente * 1103515245u + 12345u;
  return ((semente >> 16) & 0x7FFF) / 16383.5 - 1.0;
}

static void ler(const Pista &p, Robo &r, uint8_t bruto[N_CANAIS]) {
  double c = std::cos(r.th), s = std::sin(r.th);
  r.eixo = maisProximo(p, r.x, r.y, r.eixo - 200, r.eixo + 200);
  for (int i = 0; i < N_CANAIS; i++) {
    double frente, direita;
    if (i < N_SENSORES) {
      double a = (i - (N_SENSORES - 1) / 2.0) * PASSO_ANG;   // sensor 0 = esquerda
      direita = R_ARCO * std::sin(a);
      frente = L_BARRA - R_ARCO * (1 - std::cos(a));
    } else {
      direita = (i == CANAL_MARCA_E) ? -X_MARCA : X_MARCA;
      frente = Y_MARCA;
    }
    double px = r.x + frente * c + direita * s;
    double py = r.y + frente * s - direita * c;
    double w = branco(p, px, py, r.eixo, r.onde[i]);
    double v = PRETO[i] + (BRANCO[i] - PRETO[i]) * w + 3 * ruido();
    bruto[i] = (uint8_t)(v < 0 ? 0 : (v > 255 ? 255 : v));
  }
}

static void andar(Robo &r, const Saida &s, double dt) {
  r.vE += (MM_S_POR_PWM * s.esq - r.vE) * dt / TAU_MOTOR;
  r.vD += (MM_S_POR_PWM * s.dir - r.vD) * dt / TAU_MOTOR;
  double v = (r.vE + r.vD) / 2, w = (r.vD - r.vE) / BITOLA;
  r.th += w * dt;
  r.x += v * std::cos(r.th) * dt;
  r.y += v * std::sin(r.th) * dt;
}

// ------------------------------------------------------------------ ensaio

struct Resultado {
  Resumo r;
  double desvioMax;     // maior distancia do centro da barra a linha (mm)
  double sParada;       // posicao do sensor de marca ao parar (mm ao longo da pista)
  double vMax;          // m/s
};

static Resultado ensaiar(const Pista &p, const Parametros &par, uint8_t nivel,
                         double sInicial, double desvioInicial, double anguloInicial) {
  // calibracao: tudo preto e tudo branco
  Calibrador cb;
  cb.iniciar();
  uint8_t v[N_CANAIS];
  for (int i = 0; i < N_CANAIS; i++) v[i] = (uint8_t)PRETO[i];
  cb.amostrar(v);
  for (int i = 0; i < N_CANAIS; i++) v[i] = (uint8_t)BRANCO[i];
  cb.amostrar(v);
  Calibracao cal;
  if (cb.finalizar(cal) != 0) { std::printf("calibracao falhou\n"); std::exit(2); }

  Robo r = {};
  int i0 = (int)(sInicial / PASSO);
  r.th = p.pt[i0].th + anguloInicial;
  r.x = p.pt[i0].x - std::sin(p.pt[i0].th) * desvioInicial;
  r.y = p.pt[i0].y + std::cos(p.pt[i0].th) * desvioInicial;
  r.eixo = i0;

  static Corrida c;
  c.iniciar(par, cal, nivel);
  Resultado res = {};
  uint8_t bruto[N_CANAIS];
  Saida s;
  int naBarra = i0;
  for (long ciclo = 0; ciclo < 200000 && c.fase() != FASE_FIM; ciclo++) {
    ler(p, r, bruto);
    c.passo(bruto, (uint16_t)ESCALA_BAT, s);
    for (int k = 0; k < 10; k++) andar(r, s, PERIODO_US * 1e-6 / 10);

    if (c.fase() == FASE_CORRENDO) {
      double bx = r.x + L_BARRA * std::cos(r.th), by = r.y + L_BARRA * std::sin(r.th);
      branco(p, bx, by, r.eixo, naBarra);
      double d = std::hypot(bx - p.pt[naBarra].x, by - p.pt[naBarra].y);
      if (d > res.desvioMax && naBarra * PASSO < p.fim - 1) res.desvioMax = d;
      double vel = (r.vE + r.vD) / 2000.0;
      if (vel > res.vMax) res.vMax = vel;
    }
  }
  res.r = c.resumo();
  res.sParada = r.onde[CANAL_MARCA_D] * PASSO;
  return res;
}

static int falhas = 0;
static void conferir(bool ok, const char *o_que) {
  if (!ok) { falhas++; std::printf("    FALHOU: %s\n", o_que); }
}

static const char *MOTIVO[] = {"nenhum", "CHEGADA", "PERDEU", "BOTAO", "TEMPO"};

static void mostrar(const char *nome, const Resultado &x) {
  std::printf("%-34s %-8s volta %6.3f s | vmax %.2f m/s | reta %2ld %% | desvio max %4.1f mm | "
              "marcas E %2u D %u | cruz %u | sem linha %u ms\n",
              nome, MOTIVO[x.r.motivo], x.r.voltaMs / 1000.0, x.vMax,
              x.r.totalMs ? (long)(x.r.retaMs * 100 / x.r.totalMs) : 0, x.desvioMax,
              x.r.marcasEsq, x.r.marcasDir, x.r.cruzamentos, x.r.perdidoMs);
}

int main(int argc, char **argv) {
  const std::string pasta = argc > 1 ? argv[1] : "pistas";
  const double R90 = PI / 2;
  Parametros par;
  parametrosPadrao(par);
  Resultado x;
  sensoresIguais();

  // ================================================================ pista de ensaio
  // Retas, R100 a R300, curvas em S e uma reta com cruzamento.
  std::vector<Trecho> t = {
    {1500, 0},
    {200 * R90, 1.0 / 200},                               // esquerda R200 90
    {500, 0},
    {100 * 2 * R90, -1.0 / 100},                          // direita R100 180
    {400, 0},
    {150 * R90, 1.0 / 150}, {150 * R90, -1.0 / 150},      // S R150
    {1200, 0},                                            // cruzamento no meio
    {300 * 2 * R90, 1.0 / 300},                           // esquerda R300 180
    {700, 0},
    {100 * R90, -1.0 / 100}, {100 * R90, 1.0 / 100},      // S R100
    {2500, 0},                                            // chegada + area de parada
  };
  Pista pista = montar(t);
  double sCruz = 1500 + 200 * R90 + 500 + 100 * 2 * R90 + 400 + 2 * 150 * R90 + 600;
  double sPartida = 300, sChegada = pista.fim - 2500 + 800;
  pista.marcasDir = {sPartida, sChegada};
  pista.faixas = {{sCruz, 0.0}};
  const unsigned nMarcasEsq = (unsigned)pista.marcasEsq.size();
  std::printf("PISTA DE ENSAIO: %.2f m, %u marcas na esquerda, 1 cruzamento\n", pista.fim / 1000, nMarcasEsq);

  // 1. valores padrao, nivel 0
  x = ensaiar(pista, par, 0, 150, 0, 0);
  mostrar("1 padrao, nivel 0", x);
  conferir(x.r.motivo == FIM_CHEGADA, "tinha que parar na chegada");
  conferir(x.r.marcasDir == 2, "duas marcas na direita (partida, chegada)");
  conferir(x.r.marcasEsq <= nMarcasEsq, "marca esquerda a mais");
  conferir(x.r.cruzamentos == 1, "um cruzamento");
  conferir(x.r.perdidoMs == 0, "nao podia perder a linha");
  conferir(x.desvioMax < 30, "barra longe da linha");
  double parou = x.sParada - sChegada;
  std::printf("    parou %.0f mm depois da marca de chegada (a de partida fica a 1000 mm)\n", parou);
  // o sensor de marca fica ~35 mm a frente da traseira e ~135 mm atras da frente
  conferir(parou > 35 && parou < 865, "parada fora da area de partida-chegada");
  double voltaPadrao = x.r.voltaMs;

  // 2. mesma coisa sem as melhorias de velocidade (como o EVA-RT)
  Parametros unica = par;
  unica.reta = 0;
  x = ensaiar(pista, unica, 0, 150, 0, 0);
  mostrar("2 velocidade unica (reta=0)", x);
  conferir(x.r.motivo == FIM_CHEGADA && x.r.marcasDir == 2, "chegada");
  conferir(voltaPadrao < x.r.voltaMs, "a velocidade de reta tinha que baixar o tempo");

  // 3. niveis mais altos (rapido demais para as curvas R100 desta pista:
  //    pode perder a linha por um instante, mas tem que achar de novo)
  for (uint8_t nivel = 4; nivel <= 12; nivel += 4) {
    char nome[40];
    std::snprintf(nome, sizeof(nome), "3 nivel %u (curva %u, reta %u)", nivel,
                  velCurvaDoNivel(par, nivel), velRetaDoNivel(par, nivel));
    x = ensaiar(pista, par, nivel, 150, 0, 0);
    mostrar(nome, x);
    conferir(x.r.motivo == FIM_CHEGADA && x.r.marcasDir == 2, "chegada");
    conferir(x.r.cruzamentos == 1 && x.r.marcasEsq <= nMarcasEsq, "cruzamento ou marca a mais");
    conferir(x.sParada - sChegada > 35 && x.sParada - sChegada < 865, "parada fora da area");
  }

  // 4. largada torta: 15 mm fora do centro e 8 graus
  x = ensaiar(pista, par, 0, 150, 15, -8 * PI / 180);
  mostrar("4 largada torta", x);
  conferir(x.r.motivo == FIM_CHEGADA && x.r.perdidoMs == 0, "chegada sem perder a linha");

  // 5. cruzamento inclinado (85 graus) e devagar: a faixa nao pode virar marca
  Pista torta = pista;
  torta.faixas = {{sCruz, std::tan(5 * PI / 180)}};
  Parametros lento = par;
  lento.vel = 14;
  lento.reta = 0;
  x = ensaiar(torta, lento, 0, 150, 0, 0);
  mostrar("5 cruzamento a 85 graus, devagar", x);
  conferir(x.r.motivo == FIM_CHEGADA && x.r.marcasDir == 2, "chegada (a faixa nao e marca)");
  conferir(x.r.marcasEsq <= nMarcasEsq, "a faixa contou como marca esquerda");
  conferir(x.desvioMax < 15, "a faixa torta desviou o robo");
  x = ensaiar(torta, par, 8, 150, 0, 0);
  mostrar("5 cruzamento a 85 graus, nivel 8", x);
  conferir(x.r.motivo == FIM_CHEGADA && x.r.marcasDir == 2, "chegada (a faixa nao e marca)");

  // 6. a linha acaba: tem que desligar por perda
  Pista cortada = pista;
  cortada.fim = 1200;
  x = ensaiar(cortada, par, 0, 150, 0, 0);
  mostrar("6 linha interrompida", x);
  conferir(x.r.motivo == FIM_PERDEU, "tinha que desligar por perder a linha");

  // 7. sai da curva pela lateral (ganho baixo demais): vira para o lado certo e desliga
  Parametros frouxo = par;
  frouxo.kp = 0.004f;
  frouxo.kd = 0;
  x = ensaiar(pista, frouxo, 8, 150, 0, 0);
  mostrar("7 ganho baixo demais", x);
  conferir(x.r.motivo == FIM_PERDEU, "tinha que desligar por perder a linha");

  // 8. largada fora da linha: nem sai
  x = ensaiar(pista, par, 0, 150, 80, 0);
  mostrar("8 largada fora da linha", x);
  conferir(x.r.motivo == FIM_PERDEU && x.r.totalMs == 0, "nao podia sair");

  // ================================================================ pistas TRIF
  // Volta completa nos modelos do estudo de caso, com tres "robos" (atraso
  // do motor de 60, 120 e 200 ms): o que vale e funcionar nos tres.
  const char *nomes[] = {"trif2025", "trif2024"};
  const double atrasos[] = {0.060, 0.120, 0.200};
  for (const char *nome : nomes) {
    Circuito c;
    if (!carregar(pasta + "/" + nome + ".txt", c)) {
      std::printf("\n%s: arquivo nao encontrado em %s/ (rode a partir de firmware/testes)\n", nome, pasta.c_str());
      falhas++;
      continue;
    }
    std::printf("\n%s: volta de %.2f m, %u marcas na esquerda, 2 passagens pelo cruzamento\n",
                nome, c.volta / 1000, c.marcasEsq);
    for (double atraso : atrasos) {
      TAU_MOTOR = atraso;
      for (int modo = 0; modo < 2; modo++) {
        Parametros q = par;
        if (modo == 0) q.reta = 0;   // velocidade unica, como o EVA-RT
        char rotulo[48];
        std::snprintf(rotulo, sizeof(rotulo), "motor %3.0f ms, %s", atraso * 1000,
                      modo == 0 ? "velocidade unica" : "padrao");
        x = ensaiar(c.pista, q, 0, c.sLargada, 0, 0);
        mostrar(rotulo, x);
        conferir(x.r.motivo == FIM_CHEGADA && x.r.marcasDir == 2, "volta completa com parada na chegada");
        conferir(x.r.cruzamentos == 2, "duas passagens pelo cruzamento");
        conferir(x.r.marcasEsq <= c.marcasEsq, "marca esquerda a mais");
        conferir(x.r.perdidoMs == 0, "perdeu a linha");
        conferir(x.sParada - c.sChegada < 865, "parou depois da area de partida-chegada");
      }
    }
    TAU_MOTOR = 0.120;

    // Sensores desiguais (contraste de 60 a 170 contagens), borda mais
    // borrada e PWM multiplicado por 1,2 (bateria abaixo de 'vref').
    for (int i = 0; i < N_CANAIS; i++) {
      double contraste = 115 + 55 * ruido(), fundo = 45 + 20 * ruido();
      if (i < N_SENSORES) { BRANCO[i] = fundo; PRETO[i] = fundo + contraste; }
      else { PRETO[i] = fundo; BRANCO[i] = fundo + contraste; }
    }
    BORDA = 6.0;
    ESCALA_BAT = 307;
    x = ensaiar(c.pista, par, 0, c.sLargada, 0, 0);
    mostrar("sensores desiguais, PWM x 1,2", x);
    conferir(x.r.motivo == FIM_CHEGADA && x.r.marcasDir == 2, "volta completa com parada na chegada");
    conferir(x.r.cruzamentos == 2 && x.r.marcasEsq <= c.marcasEsq, "cruzamento ou marca a mais");
    conferir(x.r.perdidoMs == 0, "perdeu a linha");
    sensoresIguais();
    BORDA = 3.0;
    ESCALA_BAT = 256;
  }

  std::printf("\n%s\n", falhas ? "HOUVE FALHAS" : "tudo certo");
  return falhas ? 1 : 0;
}
