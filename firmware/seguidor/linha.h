/*
 * linha.h - calibracao, posicao da linha e sensores de marca
 *
 * Baseado no EVA-RT 1.2.2 (c) 2025 EXOTIC TEAM MX, licenca AGPL-3.0, e no
 * modulo de bancada firmware/teste_barra (mesma escala de posicao e erro).
 *
 * So contas: quem le o ADC e o hw.cpp. Sem dependencia do Arduino, para
 * compilar tambem no PC (firmware/testes).
 */
#pragma once

#include <stdint.h>
#include "config.h"

#define N_CANAIS       (N_SENSORES + 2)        // barra + 2 sensores de marca
#define CANAL_MARCA_E  (N_SENSORES)
#define CANAL_MARCA_D  (N_SENSORES + 1)

#define POS_MAX        ((N_SENSORES - 1) * 1000)   // 11000
#define ERRO_MAX       (POS_MAX / 2)               // 5500

// Minimo e maximo brutos (8 bits) de cada canal
struct Calibracao {
  uint8_t mn[N_CANAIS];
  uint8_t mx[N_CANAIS];
};

// Bits do resultado de Calibrador::finalizar()
#define CAL_FALHA_BARRA    0x0FFF
#define CAL_FALHA_MARCA_E  (1u << CANAL_MARCA_E)
#define CAL_FALHA_MARCA_D  (1u << CANAL_MARCA_D)

class Calibrador {
public:
  void iniciar();
  void amostrar(const uint8_t v[N_CANAIS]);   // passe a media de algumas leituras
  // Copia o resultado e devolve um bit por canal sem contraste (0 = tudo ok)
  uint16_t finalizar(Calibracao &c) const;

private:
  uint8_t _mn[N_CANAIS];
  uint8_t _mx[N_CANAIS];
};

// 0..255 a partir do bruto; 255 = branco se 'inverter' corrigir a polaridade
uint16_t ganhoDoCanal(uint8_t mn, uint8_t mx);
uint8_t  normalizar(uint8_t bruto, uint8_t mn, uint16_t ganho, bool inverter);

class Linha {
public:
  void configurar(const Calibracao &c);
  void reiniciar();                              // posicao volta para o centro

  // Uma vez por ciclo. podeCruzar = false quando o robo esta em curva: ai
  // uma faixa larga embaixo da barra e a propria linha, nao um cruzamento.
  void atualizar(const uint8_t bruto[N_SENSORES], bool podeCruzar = true);

  int16_t erro() const         { return _erro; }     // -5500..+5500, + = linha a direita
  bool    vista() const        { return _vista; }
  bool    cruzamento() const   { return _cruz; }     // faixa atravessada embaixo da barra
  bool    medida() const       { return _medida; }   // o erro e uma medida deste ciclo
  uint8_t norm(uint8_t i) const { return _norm[i]; } // 0..255, 255 = linha
  uint8_t largura() const      { return _largura; }  // sensores vizinhos ativos (o maior grupo)

private:
  uint8_t  _mn[N_SENSORES];
  uint16_t _ganho[N_SENSORES];
  uint8_t  _norm[N_SENSORES];
  int16_t  _erro;
  int16_t  _hist[4];     // erro dos ultimos ciclos (para antes de a faixa entrar)
  uint8_t  _histPos;
  uint8_t  _faixa;       // ciclos seguidos com o erro mantido por faixa larga
  uint8_t  _salto;       // ciclos seguidos recusando um salto
  uint8_t  _largura;
  bool     _vista;
  bool     _cruz;
  bool     _medida;
};

// Bits devolvidos por Marcas::atualizar()
#define MARCA_ESQ  0x01
#define MARCA_DIR  0x02

// Sensores de marca dos bracos. Uma marca so vale se o outro lado nao viu
// branco junto e se nao e a faixa de um cruzamento que a barra acabou de ver.
class Marcas {
public:
  void configurar(const Calibracao &c);
  void reiniciar();

  // Uma vez por ciclo. Devolve MARCA_ESQ / MARCA_DIR no ciclo em que a
  // marca e confirmada (pouco depois de ela passar).
  // descarteCiclos: por quanto tempo, depois de um cruzamento na barra, o
  // proximo pulso de cada lado e tratado como a faixa do cruzamento.
  uint8_t atualizar(uint8_t brutoE, uint8_t brutoD, bool cruzamentoNaBarra,
                    uint16_t descarteCiclos);

  bool ativa(uint8_t lado) const { return _l[lado].ativo; }   // 0 = esq., 1 = dir.
  // false = o sensor nao teve contraste na calibracao e esta desligado
  bool valida(uint8_t lado) const { return _l[lado].ganho != 0; }

private:
  struct Lado {
    uint8_t  mn;
    uint16_t ganho;
    bool     ativo;        // branco embaixo do sensor (com histerese e filtro)
    uint8_t  cont;         // ciclos seguidos pedindo a troca de estado
    bool     pulsoRuim;    // o pulso atual nao e uma marca
    uint8_t  pendente;     // ciclos ate confirmar o pulso que acabou
    uint8_t  recente;      // ciclos desde que o pulso acabou (para o outro lado)
    uint16_t descartar;    // ciclos em que o proximo pulso e do cruzamento
  };
  Lado _l[2];
};
