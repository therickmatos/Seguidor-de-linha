# marcas/ — sensores de marca × marcas do TRIF

`index.html` é um site de um arquivo só (sem dependências) com a simulação dos QRE de marca do RUSH SATURN v3. Abra no navegador, direto do disco ou por um visualizador de HTML do GitHub.

## O que tem
- **Pista:** pista de teste fechada (volta de 9,45 m, 21 marcas de curvatura + partida/chegada) ou uma pista digitada (`S800 D100/90 E200/45 P C`). Mostra quais marcas o robô lê, inspeciona cada marca com o robô desenhado no instante em que o QRE cruza o meio dela, anima o robô ao longo da pista e emula a parada do firmware EVA-RT 1.2.2 (`Marks.ino`).
- **Bateria de curvas:** 272 trechos (R100–R500, 45–180°, curvas encadeadas e em S, para os dois lados), 768 marcas de curvatura por L. Agrupa as perdas pelo trecho que vem antes da marca e desenha cada caso perdido.
- **Comparar L:** marcas lidas × L de 60 a 104 mm para três modelos de seguimento, e varredura da posição y do QRE com L fixo.
- **Método e regra:** geometria, regra usada, modelos e limites.

Parâmetros no painel: L (distância do eixo à linha dos sensores da barra), modelo de seguimento (barra ideal, controle P firme/solto, barra deslocada), L de comparação, posição do QRE e velocidade/timer do firmware.

## Geometria (v3, `.epro` de 09/11/2026)
- QRE de marca em (±69,5; 4,5); eixo das rodas em y = −22,59 (suportes de motor em (±35,25; −26,55/−3,73) + `gearbox.stl`).
- L do EVA-RT ≈ 98 mm, medido na foto de baixo do EVA-RT com homografia em 8 furos de posição conhecida (±2–3 mm).
- Marca de 40 × 19 mm a 40 mm da borda da linha de 19 mm (regulamento RoboCore Line Follower, revisão de 16/01/2024, itens 4.7 e 4.15) → de 49,5 a 89,5 mm do centro da linha.

## Conferência
O núcleo da simulação (`<script id="sim">`) é o mesmo modelo do script em Python usado na análise de 09/11/2026 e dá os mesmos números:

| L (mm) | Bateria, barra ideal | P firme | P solto | Pista de teste |
|---|---|---|---|---|
| 67 | 768/768 | 768/768 | 768/768 | 21/21 |
| 70 | 768/768 | 768/768 | 768/768 | 21/21 |
| 82 | 759/768 | 764/768 | 768/768 | 19/21 |
| 95 | 689/768 | 701/768 | 724/768 | 17/21 |
| 98 (EVA-RT) | 672/768 | 684/768 | 704/768 | 17/21 |

Partida e chegada são lidas em todos os casos, e a parada emulada do firmware 1.2.2 acontece logo depois da chegada.

Modelo cinemático (sem escorregamento). Seguidor baseado no EVA-RT (© EXOTIC TEAM MX, AGPL-3.0).
