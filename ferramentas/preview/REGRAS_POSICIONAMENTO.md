# Regras de posicionamento (proposta para o preview)

Filosofia do projeto: "jogar seguro a partir do projeto original". O EVA-RT ganhou competicoes com esse layout.
Portanto: **o que nao mudou fica onde estava no EVA-RT** (mesmo x, y, rot, face — tabela $P/eva_rt_componentes.csv);
so se move o que foi trocado, o que e novo, ou o que colide com algo novo. Cada movimento precisa de um motivo curto.

## Correspondencia EVA-RT → este projeto (mesmas referencias quando "igual" na BOM)
- Ficam no lugar (se nao colidirem): C1, C2 (eletroliticos entre os pes da carcaca), C3, C4, C5, U5 (78M05), LED5 + R10,
  LED4 + R5 (LED C), C8, R8, R9, LED6 + R1, LED7 + R2, R3, C9, C10, X1 (ajustar ao footprint novo).
- Saem: LED3, R4 (LED C duplicado), FPC1 (vira J2), conector do conversor (5 pads em y = −28,57; vira J3),
  IFX_A1/IFX_B1 (viram U2/U3), VIN (vira J1).
- U1 ATmega328P-AU: mover ~5 mm para a FRENTE (EVA-RT: (0; −23) rot −45 → proposta (0; −18) rot −45),
  e levar junto o que esta em volta dele (X1, C9, C10, R3, LED6/R1, LED7/R2), deslocando +5 mm em y quando fizer sentido.
- U2 (DRV8874, motor ESQ.) no lugar do IFX_A1 (−22,1; −12,45); U3 (motor DIR.) no lugar do IFX_B1 (22,1; −12,45).
  Escolher a rotacao para que a ponta de potencia (pinos 8 OUT1, 9 PGND, 10 OUT2, 11 VM) fique para o lado dos pads
  do motor (M1 em x = −36,58 / M2 em x = +36,58; y 0…2,54) e a ponta logica (pinos 1 EN, 2 PH, 3 nSLEEP, 5 VREF, 6 IPROPI)
  para o lado do U1. Em volta de cada DRV, colados nos pinos: C6/C7 (VM, pino 11), C13/C15 (VCP pino 12 → VM),
  C14/C16 (CPH 13 – CPL 14), R11/R12 (IPROPI, pino 6). R13/R14 (divisor VREF, comum aos dois) e R15 (nSLEEP, comum)
  entre os dois DRV, perto do U1. Nada na face BOTTOM debaixo do pad termico (so vias).
- Q1 AO3400A (SOT-23) perto dos pads da ventoinha, em ~(25,8; 5,6) (doc), com R8 (10k gate→GND) e R9 (200 Ω) ao lado.
  D1 (SOD-123) colado nos pads da ventoinha M3 (29,72; 1,78 = + / 4,32 = −), catodo no + (VBAT).
- M1, M2, M3 (pads de motor/ventoinha): mesmas posicoes do EVA-RT ($P/eva_rt_pads_livres.csv). M1 = motor esq. (x −36,58), M2 = dir. (x +36,58).
  Conferir no REDES.md qual pad e "+" e qual e "−".
- J5 ICSP: 6 pads SMD na face BOTTOM nas posicoes do EVA-RT (x 33,97/36,51; y −8,36/−10,90/−13,44).
- J3 gravacao 1x5 macho 90°, em CIMA, centro da borda traseira, furos numa linha em x = −5,08…+5,08 com y ≤ −28
  (fora da placa de succao, que vai ate y = −27,5); pinos apontando para tras (−y). Ordem da esquerda para a direita
  vista de cima: +5V, GND, RX, TX, DTR (pino 1 = +5V). C17 (100 nF DTR→RESET) entre J3 e o U1.
- J2 barra de sensores 1x8 2,54 mm: linha de furos em y = 22,74, centrada em x = 0 (x = −8,89…+8,89).
  Ordem dos pinos igual a barra V1: +5V, GND, NC, C0, S3, S2, S1, S0 (conferir com REDES.md: J2.1 = +5V, J2.8 = S0_A0).
- J4 Bluetooth femea 1x6: coluna em x ≈ 32,5, y ≈ 0,7…13,4 (pino 1 STATE embaixo, pino 6 EN em cima).
  R16/R17 (divisor 1k/2k) e R18 (0 Ω) perto do J4.
- J1 bateria (XT30): no lugar do antigo VIN (−36,35; −30,25) se couber. Se o XT30PW-M nao couber sem colidir com o
  suporte do motor/rodas, usar a versao "rabicho" (2 pads para fios) no mesmo lugar e dizer isso.
- Sensores de marca: S0 (esq., A5) e S1 (dir., A6) na face BOTTOM nos bracos, em (−69,5; 4,5) e (+69,5; 4,5).
  No EVA-RT os conjuntos das asas soltas eram: esq. = S0 + LED1 (em cima, mesmo x,y do S0) + R20 + R30 + R6;
  dir. = S1 + LED2 (em cima) + R21 + R31 + R7. Levar esses conjuntos para os bracos integrados: LED1/LED2 em CIMA
  sobre o respectivo QRE (mesmo x,y), R20/R30 (e R21/R31) na face BOTTOM ao lado do QRE, R6/R7 em cima ao lado do LED.
  Ficar dentro da largura do braco com ≥ 0,5 mm de folga da borda.
- J8/J9 (pads das asas, NAO montar): os bracos sao integrados, entao sao opcionais. Mostrar tracejados nas posicoes
  dos pads das asas do EVA-RT (x = ±45,04/±46,57; y 2,79…6,22) com a nota "DNP — pode apagar no layout".
- R23/R24/C18 (medicao da bateria, opcional): perto do U1 (pino 22, ADC7) ou no caminho do VBAT; dizer onde.
- C11/C12 (22 pF) colados no X1, X1 colado nos pinos 7/8 do U1.

## BOTOES 6 x 6 x 4,5 mm (SW0 RESET, SW1 BOTAO 1, SW2 BOTAO 2) — principal mudanca de layout
O dono do projeto ja comprou botoes taticos 6 x 6 x 4,5 (assumir THT de 4 terminais; footprint da biblioteca).
No EVA-RT eram B3U-1000P minusculos (3 x 2,5 mm): SW1 (37,34; 5,84), SW2 (37,34; 11,30), SW0 (36,35; −30,25).
Os 6 x 6 (com pads ~7,5 x 6,5 mm) provavelmente NAO cabem nesses lugares (SW1/SW2 ficam a 5,46 mm um do outro;
SW0 encosta no suporte do motor direito). Encontrar lugar para os tres respeitando:
- face TOP, acessiveis ao dedo (nao debaixo da bateria, da carcaca da ventoinha, dos motores/gearbox, das presilhas e da vareta);
- terminais THT fora da area de contato da placa de succao embaixo;
- fora do caminho do modulo Bluetooth (que fica em pe sobre o J4, plano vertical em x ≈ 32,5, ~4 mm de espessura,
  componentes do modulo virados para a ventoinha);
- SW1/SW2 de preferencia juntos (frente direita, como no EVA-RT) e SW0 (reset) separado deles para nao apertar por engano;
- se precisar mexer em J4/Q1/D1/R8/R9/LED4/R5 para caber, mexer o minimo e dizer.
Proponha a melhor opcao e, se houver uma segunda opcao razoavel, descreva-a no relatorio (sem desenhar).

## Conferencias automaticas obrigatorias (script)
1. Nenhuma sobreposicao de cortesias (courtyards) entre componentes da MESMA face (THT conta nas duas faces).
2. Todo cobre dentro do contorno com ≥ 0,3 mm da borda e dos furos/rasgos.
3. Nada nas areas proibidas da face correspondente (geometria.json), exceto o que ja estava ali no EVA-RT (avisar).
4. Todo REF da BOM posicionado (ou explicitamente marcado DNP/omitido com motivo).
5. Lista de avisos impressa no relatorio.

## Notas do coordenador depois da geometria (valem mais que o texto acima se houver conflito)
- Use $P/geometria.json (contorno, furos, areas) e veja $P/conf_geometria.png. Areas "sombra" tem altura_min_mm:
  um componente pode ficar debaixo se a altura dele (footprints.py → altura_mm) for menor que altura_min_mm − 0,3.
  Areas "contato" proibem qualquer componente na face indicada.
- Bateria (corrigida): x ±22,5, y −42,6…−22,1, apoio a 3,0 mm → embaixo dela so componentes ≤ 2,5 mm.
  X1: se ficar debaixo da bateria, so o 3225 (0,8 mm) cabe; o HC-49/S SMD (~3,5–4 mm) tem que ficar fora (y > −22,1).
  Prefira um lugar onde o HC-49/S SMD caiba (o cristal do Nano doador costuma ser esse), colado nos pinos 7/8 do U1,
  e desenhe o 3225 como alternativa tracejada no mesmo lugar.
- Disco do rotor da ventoinha (ventoinha_base_contato, r ≤ 17) e pes da carcaca: proibidos em cima.
- Presilhas da vareta (confianca baixa) ocupam x 40,5…50, y −5,3…1,7 e 7,2…14,2 dos dois lados; a vareta sai dessas
  presilhas para a frente (+y) por cima da placa em x ≈ ±43,75 — nao colocar componente alto (> 3 mm) em x 40…48, y > 7.
- Suportes dos motores (gearbox) ocupam x ±30,5…±40, y −28,5…−1,8 em cima. Atras deles (y −32…−28,5) so sobra uma faixa
  de ~3,5 mm: o botao 6 x 6 do RESET nao cabe mais no canto traseiro direito.
- Os eletroliticos C1/C2 (11,2 mm) ficam no lugar do EVA-RT mesmo encostando na sombra da carcaca (ja era assim).
