# Placa base — versão alpha (06/11/2026)

**Revisão de 07/11 (noite) — ver a seção "Fluxo no EasyEDA" abaixo.** Traseira reta em y = −33, XT30 em pé
por dentro do suporte esquerdo (6,4 mm do motor), braços dos sensores de marca com **6,1 mm** de altura
(y 1,45–7,55), chaves **Jianfu TVBM17-025CF-R** (C19271064) com pads encurtados, cristal **TXC 7A 5032**
(C2450102) em diagonal junto do ATmega, C5 em **1210**. Tudo (KiCad + este pacote + 3D) também em
`hardware/placa_base_alpha.zip`.

Prévia completa da placa base para fazer o layout no EasyEDA Pro. Origem no centro da
ventoinha, +y = frente, mm. Detalhes, folgas e verificação em `RELATORIO_alpha.md`.

| Arquivo | Para que serve |
|---|---|
| `placa_alpha.jpg` | as duas faces com trilhas, vias e plano de GND (guia visual do roteamento) |
| `posicao_alpha.jpg` | só posições, com a mecânica do EVA-RT por cima e o detalhe do XT30 em pé |
| `posicoes_alpha.csv` | ref, valor, face, x, y, rotação de cada componente |
| `contorno_alpha.dxf` | contorno da placa (camada CONTORNO) + furos e rasgos (camada FUROS) |
| `guia_alpha.dxf` | cobre, planos, pads, vias, corpos e referências, uma camada DXF para cada coisa |
| `trilhas_fixas_alpha.csv` | o cobre desenhado à mão (pontos exatos), para reproduzir primeiro |
| `RELATORIO_alpha.md` | resultado da verificação, larguras, mudanças e o que conferir |
| `contorno_furos_easyeda.dxf` | **contorno + furos + rasgos numa camada só**, para importar direto na Board Outline |
| `furos.csv` | furos e rasgos com coordenadas (para pôr como furo sem metalização, se preferir) |
| `posicoes_easyeda.csv` | **posição de cada peça por dois pinos** (numeração do esquemático), face e centro |

## Fluxo no EasyEDA a partir do seu esquemático (07/11)

1. **Origem e contorno.** Importe `contorno_furos_easyeda.dxf` na camada **Board Outline**. As formas fechadas
   de dentro (furos e rasgos) viram recorte; no 3D do EasyEDA elas aparecem como buraco. Confira três pontos: o
   furo da ventoinha centrado em (0; 0), os furos da carcaça em (±15,556; ±15,556) e o furo traseiro do suporte
   do motor direito em (35,25; −26,55). Se este aparecer em y = **+**26,55, o EasyEDA está com o y invertido:
   use −y nos CSVs.
2. **Posições** (`posicoes_easyeda.csv`). Para cada peça: coloque na face indicada (`cima` ou `baixo`), mova
   até o **pino A** ficar em (A_x; A_y) e gire até o **pino B** cair em (B_x; B_y). Os pinos usam a numeração
   do esquemático, então isso vale para qualquer footprint (LCSC ou nosso), e as coordenadas são sempre
   vistas de cima, também para as peças da face de baixo. Face de baixo: D1, J3, J5, R6, R7, R16, R17, R18,
   R20, R21, R30, R31, S0, S1. A coluna `rot_previa` é a rotação dos footprints desta prévia (só referência).
3. **Footprints a ajustar no seu projeto:**
   - **SW0–SW2 (TVBM17):** pads de **1,2 × 1,2 mm com centro em ±3,7 mm** (de 3,1 a 4,3; 8,6 mm no total). O
     padrão do fabricante (9,5 mm) não cabe ao lado do J4; o terminal (8,0 mm de ponta a ponta) assenta
     inteiro no pad encurtado.
   - **X1 (TXC 7A, 5032 de 2 pads):** pads de 1,7 × 2,4 mm com centro em ±1,85 mm (datasheet TXC 7A).
   - **C5:** footprint C1210.
4. **Regras de projeto:** folga 0,2 mm; cobre–borda 0,3 mm; sinais 0,25 mm; vias 0,6/0,3 (sinais) e 0,8/0,4
   (potência; 2–3 em paralelo ao trocar de face).

   | Rede | Largura | Observação |
   |---|---|---|
   | VBAT | **2,0 mm** ou polígono | afina para 0,4 mm só no último milímetro do pino 11 do DRV8874 |
   | OUT_A1/A2/B1/B2 (motores) | 1,5 mm | até 3 A cada (limite do DRV8874); 0,4 mm só na saída dos pinos |
   | VBAT até o M3 e OUT_C (ventoinha) | ≥ 1,2 mm | ~1–2 A contínuos |
   | +5V | 0,6–0,8 mm | ≤ 0,3 A |
   | GND | plano nas duas faces | vias de costura a cada ~5 mm |
   | sinais | 0,25 mm | |

   Com cobre de 1 oz, 2,0 mm aguentam ~5 A contínuos com +20 °C, e 1,5 mm aguentam ~4 A.
5. **Roteamento:** primeiro **à mão a potência** (VBAT, motores, ventoinha), seguindo `placa_alpha.jpg`
   (importe o `guia_alpha.dxf` numa camada Document como gabarito). Depois o **autorouter só nos sinais**,
   revisando a região do ATmega e do cristal (trilhas do cristal curtas, sem via). Por fim, plano de GND nas
   duas faces e DRC.
6. **DRV8874:** pad térmico com as vias pequenas do footprint, soldado com soprador (sem furo grande).

| `../seguidor_base/seguidor_base.kicad_pcb` | **a mesma placa em KiCad 7**, ligada ao esquemático (ver abaixo) |

## Placa em KiCad (`hardware/seguidor_base/`)

`seguidor_base.kicad_pcb` é esta versão alpha completa: contorno, furos e rasgos, os 67
componentes nas posições e faces acima, trilhas, vias e as áreas de GND nas duas faces
(preenchidas pelo KiCad, folga 0,25 mm). Abre junto com o esquemático no projeto
`seguidor_base.kicad_pro`: cada footprint está ligado ao símbolo pelo UUID e cada pad está na rede
do esquemático. Origem auxiliar e da grade no centro da ventoinha.

- **Conferido pelo próprio KiCad 7.0.11** (`drc_kicad.rpt`): 0 violações, 0 pads sem ligação,
  0 erros de footprint. Paridade com o esquemático: 217 pads, 0 diferenças. Só J8/J9 (pads das
  asas, não montados) ficam fora da placa, como na prévia.
- Regras: folga 0,2 mm, cobre–borda 0,3 mm, trilha mínima 0,2 mm, via mínima 0,5/0,3 mm. O pino 2 (GND)
  do J2 liga ao plano sem alívio térmico: embaixo só cabia 1 raio de alívio, e o KiCad exige 2.
- As referências S0, S1, R6 e R7 (nos braços estreitos) ficaram na camada F.Fab/B.Fab, sem espaço na
  serigrafia; refazer a serigrafia no EasyEDA.
- Footprints na biblioteca do projeto `seguidor_alpha.pretty` (já no `fp-lib-table`). **São os
  modelos aproximados da prévia** (pads certos, corpo aproximado na camada F.Fab, sem 3D): trocar
  pelos da LCSC antes do pedido e repetir o DRC.
- **EasyEDA Pro:** importar o projeto KiCad (Arquivo → Importar → KiCad), escolhendo os arquivos
  desta pasta (`.kicad_pro`, `.kicad_sch`, `.kicad_pcb`, `seguidor_alpha.pretty` e
  `seguidor.kicad_sym`). Não testei a importação aqui (não há EasyEDA neste ambiente). Se ela
  falhar ou não trouxer as áreas de cobre, use o caminho manual abaixo: os DXF e o CSV são os
  mesmos dados.
- Para gerar Gerber direto do KiCad (opcional): `Arquivo → Plotar`, marcando "usar origem auxiliar".
  Pelo terminal, o `kicad-cli pcb export gerbers` / `export drill` já foi testado.

## Passo a passo no EasyEDA Pro

1. **Unidade mm e origem no centro da ventoinha** (furo Ø17 em 0; 0).
2. **Contorno:** importar `contorno_alpha.dxf`. A camada CONTORNO vai para Board Outline; os
   círculos e retângulos da camada FUROS são os furos sem cobre (carcaça, suportes dos motores,
   presilhas, ventoinha) e os rasgos do velcro.
3. **Guia:** importar `guia_alpha.dxf` numa camada de documento (Document) e ligar só o que
   ajudar (por exemplo COBRE_CIMA e PADS_CIMA). Serve de gabarito para posicionar e rotear.
4. **Posicionar** pelo `posicoes_alpha.csv`. Componentes com face BOTTOM vão na camada de baixo.
   A rotação é a dos footprints desta prévia; nos footprints da LCSC, **oriente pelo pino 1**
   (ponto branco nas imagens), não pelo número da rotação.
5. **Regras:** folga 0,2 mm; cobre–borda 0,3 mm; sinais 0,25 mm; +5V 0,4–0,6 mm; VBAT e
   saídas dos motores 1,0–1,2 mm, afinando para 0,4 mm só na saída dos pinos do DRV8874;
   vias 0,6/0,3 (sinais) e 0,8/0,4 (potência).
6. **Cobre fixo primeiro** (`trilhas_fixas_alpha.csv`): troncos de VBAT na face de baixo,
   feixe dos sensores em volta da ventoinha, cristal e saídas de potência do U3. Depois
   rotear o resto seguindo `placa_alpha.jpg`.
7. **Plano de GND nas duas faces** (folga 0,25 mm), 6 vias térmicas 0,6/0,3 no pad de cada
   DRV8874 e vias de costura a cada ~5 mm onde couber.
8. **DRC** no EasyEDA e conferência rede por rede com `hardware/seguidor_base/REDES.md`.

## J3 (gravação) — 5 pads SMD na face de baixo

| pad | x (mm) | rede |
|---|---|---|
| J3.1 | −5,08 | +5V |
| J3.2 | −2,54 | GND |
| J3.3 | 0,00 | RX_D0 |
| J3.4 | +2,54 | TX_D1 |
| J3.5 | +5,08 | DTR |

Pads 1,25 × 2,25 mm em y = −28,575, passo 2,54. Visto de cima (e por trás do robô) a ordem
é +5V, GND, RX, TX, DTR da esquerda para a direita. Conferir a ordem do conversor CH340G.

## Montagem do Bluetooth

R18 = 4,7 kΩ e **LED7 e R2 não montados**: assim dá para gravar pelo J3 com o HC-05 encaixado
(o conversor ganha do módulo no RX). Os footprints do LED7/R2 ficam na placa; para ter o LED de
RX, monte LED7/R2, troque o R18 por 0 Ω e tire o módulo antes de gravar.

## Conferir antes de pedir na JLC

- XT30 (J1) = **XT30U-M (C99101, macho de cabo)**, em pé por dentro do suporte esquerdo, com os
  copos soldados nos furos: medir o diâmetro dos copos (furos Ø2,5 e pads Ø3,9 são estimados) e
  cortar rente o que sobrar embaixo (~2,5 mm até o chão). Conferir a folga de 0,9 mm até a face
  interna do suporte (até o motor ficam 6,4 mm). Versão de placa, se preferir: XT30UPB-M (C428721).
- Engrenagem da roda: a prévia supõe a engrenagem encostada no suporte, em |x| = 40…42; o contorno
  não passa de |x| = 40 e o XT30 fica a 10,4 mm desse plano.
- J3 deitado: folga da barra até o chão (ver relatório).
- Cristal X1: a prévia usa 3225; HC-49/S não cabe sob a bateria.
- Esquemático: já regerado (J1 = XT30U-M C99101, J3, Bluetooth e R18 = 4,7k na BOM; campo
  Footprint apontando para `seguidor_alpha`; botões = TC-3610 / C2845294).
- Botões 3 × 6 (TVBM17): a vareta da barra passa por cima de x ≈ 43–47 na frente direita; conferir no
  conjunto real que a presilha da vareta não encosta na SW2 (0,25 mm da área estimada).

Baseado no EVA-RT © EXOTIC TEAM MX — AGPL-3.0.
