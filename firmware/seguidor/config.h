/*
 * config.h - configuracao de compilacao do seguidor (pinos, barra, limiares)
 *
 * Baseado no EVA-RT 1.2.2 (c) 2025 EXOTIC TEAM MX, licenca AGPL-3.0
 * https://github.com/EXOTIC-TEAM-MX/EVA-RT
 *
 * O que muda de robo para robo ou de pista para pista fica aqui.
 * O que se ajusta entre tentativas (ganhos, velocidades) fica em params.h
 * e pode ser alterado pelo console serial, sem regravar.
 */
#pragma once

#define FW_NOME    "seguidor"
#define FW_VERSAO  "0.1.0"

// ------------------------------------------------------------------ pista
#define LINHA_BRANCA  1          // TRIF/RoboCore: linha branca em manta preta

// ------------------------------------------------------------------ pinos
// Mapa do EVA-RT 1.2.2 (nao mudou na placa). So documentacao: o hw.cpp
// acessa os registradores direto.
//   D2  PD2  LED A (braco esquerdo)      D3  PD3  sentido motor A (esq.)
//   D7  PD7  LED B (braco direito)       D4  PD4  sentido motor B (dir.)
//   D13 PB5  LED C                       D5  PD5  PWM motor A (OC0B)
//   D11 PB3  botao 1                     D6  PD6  PWM motor B (OC0A)
//   D12 PB4  botao 2                     D10 PB2  PWM ventoinha (OC1B)
//   A0..A3 PC0..PC3  S0..S3 do mux       A4  ADC4 saida comum do mux
//   A5  ADC5 marca esquerda (curvas)     A6  ADC6 marca direita (partida/chegada)
//   A7  ADC7 bateria (divisor 20k/10k)
#define ADC_MUX       4
#define ADC_MARCA_E   5
#define ADC_MARCA_D   6
#define ADC_BATERIA   7

// ------------------------------------------------------------------ barra
#define N_SENSORES    12

// Canal do 74HC4067 de cada sensor, do S0 (esquerda do robo, olhando para a
// frente) ao S11 (direita). E o mapa do teste de bancada da barra
// (firmware/teste_barra/barra.h).
//
// ATENCAO: no Gerber de hardware/barra_v1 os sensores estao nos canais 2 a
// 13 (0, 1, 14 e 15 no GND), como na barra do EVA-RT. Se a calibracao
// rejeitar sempre os mesmos sensores da ponta, veja com o comando 'r' quais
// canais respondem e troque para a linha de baixo.
#define MAPA_MUX  {4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15}
// #define MAPA_MUX  {2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13}

// 1 = a barra esta montada ao contrario (S0 do mapa ficou na direita)
#define BARRA_ESPELHADA      0

// Na barra V1 o preto da leitura alta (saida no coletor). Nos sensores de
// marca da base e o contrario (saida no emissor, 47k para o GND).
#define BARRA_ALTO_NO_PRETO  1
#define MARCA_ALTO_NO_PRETO  0

// Espera depois de trocar o canal do mux, antes da conversao (us)
#define ACOMODACAO_US        12

// Limiares na escala normalizada 0..255 (255 = em cima da linha)
#define LIMIAR_RUIDO         13   // abaixo disso o sensor nao entra na media
#define LIMIAR_LINHA         77   // algum sensor acima disso = linha vista
#define LIMIAR_MARCA_LIGA   153   // sensor de marca: liga em 60 %
#define LIMIAR_MARCA_DESL   102   //                  desliga em 40 %

// Contraste minimo (bruto, 8 bits) aceito na calibracao
#define DELTA_MINIMO         40

// A linha de 19 mm cobre 2 a 3 sensores (passo de 7,8 mm), 4 se o robo
// estiver um pouco torto. LARGURA_FAIXA ou mais sensores vizinhos ativos
// e uma faixa larga; LARGURA_CRUZAMENTO ou mais e um cruzamento (a faixa
// atravessada cobre a barra quase toda, mesmo torta 10 graus).
//
// Mas numa curva fechada a barra, que vai uns 100 mm a frente do eixo, fica
// quase paralela a linha e tambem ve uma faixa larga. Por isso a faixa so
// e tratada como cruzamento (erro mantido) se o robo nao estiver virando:
// comando medio de direcao abaixo de CRUZ_COMANDO_MAX % da velocidade de
// curva. O regulamento garante 250 mm de reta antes do cruzamento.
// Com LARGURA_TOTAL sensores e cruzamento em qualquer situacao (nas pistas
// simuladas a linha em curva nao passou de 6).
#define LARGURA_FAIXA         5
#define LARGURA_CRUZAMENTO    8
#define LARGURA_TOTAL        10
#define CRUZ_COMANDO_MAX     30
#define FAIXA_MAX_MS         80   // erro mantido no maximo por este tempo

// Num trecho reto a linha nao anda mais que isto de um ciclo para o outro
// (400 = 3 mm em 1 ms). Um salto maior so e aceito se durar SALTO_CICLOS:
// da tempo de a faixa de um cruzamento, que entra por um lado da barra,
// ser reconhecida.
#define SALTO_MAX           400
#define SALTO_CICLOS          3

// Perdeu a linha com o erro alem disso (1000 = um sensor): ela saiu pela
// lateral e o erro vai para o extremo. Senao (falha no meio) o erro e mantido.
#define LIMIAR_LATERAL     2000

// ------------------------------------------------------------------ motores
// Motor A = esquerdo, motor B = direito. Se uma roda girar para tras no
// teste de motores, mude aqui (ou inverta os fios).
#define INVERTER_MOTOR_ESQ   0
#define INVERTER_MOTOR_DIR   0
#define TROCAR_MOTORES       0    // 1 = o motor A esta na direita

// ------------------------------------------------------------------ ciclo
// Periodo fixo do controle. Os tempos em ms dos modulos sao contados em
// ciclos, entao mudar isto muda a escala do kd (ver params.h).
#define PERIODO_US         1000

// Marca: ciclos seguidos para aceitar a subida e a descida
#define MARCA_CICLOS_LIGA     2
#define MARCA_CICLOS_DESL     2
// Depois que a marca passa, espera isto para ver se o outro lado tambem
// viu (cruzamento atravessado torto)
#define MARCA_MARGEM_MS      12

// ------------------------------------------------------------------ largada e parada
#define LARGADA_MS         1000   // do botao ate sair (a ventoinha sobe nesse tempo)
#define VENT_SUBIDA_MS      400   // rampa da ventoinha
#define VENT_POS_PARADA_MS  500   // ventoinha ligada depois de frear
#define VENT_MAXIMO         245   // como no EVA-RT (MAX_IMP_SPEED)
#define VEL_MAXIMA          140   // teto do PWM base ao subir de nivel (EVA-RT)

// ------------------------------------------------------------------ registro
#define LOG_TAMANHO         120   // amostras guardadas (as ultimas)
#define LOG_PERIODO_MS       20   // 120 x 20 ms = ultimos 2,4 s
