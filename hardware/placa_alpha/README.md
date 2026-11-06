# Placa base — versão alpha (06/11/2026)

**Revisão da noite de 06/11:** traseira do EVA-RT (sem os lóbulos até y = −35) e XT30 em pé por
dentro do suporte esquerdo, com o roteamento refeito. Tudo (KiCad + este pacote + 3D) também em
`hardware/placa_base_alpha.zip`.

Prévia completa da placa base para fazer o layout no EasyEDA Pro. Origem no centro da
ventoinha, +y = frente, mm. Detalhes, folgas e verificação em `RELATORIO_alpha.md`.

| Arquivo | Para que serve |
|---|---|
| `placa_alpha.jpg` | as duas faces com trilhas, vias e plano de GND (guia visual do roteamento) |
| `posicao_alpha.jpg` | só posições, com a mecânica do EVA-RT por cima e o detalhe do canto do XT30 |
| `posicoes_alpha.csv` | ref, valor, face, x, y, rotação de cada componente |
| `contorno_alpha.dxf` | contorno da placa (camada CONTORNO) + furos e rasgos (camada FUROS) |
| `guia_alpha.dxf` | cobre, planos, pads, vias, corpos e referências, uma camada DXF para cada coisa |
| `trilhas_fixas_alpha.csv` | o cobre desenhado à mão (pontos exatos), para reproduzir primeiro |
| `RELATORIO_alpha.md` | resultado da verificação, larguras, mudanças e o que conferir |
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
- Regras: folga 0,2 mm, cobre–borda 0,3 mm, trilha mínima 0,2 mm, via mínima 0,5/0,3 mm.
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
  interna do suporte. Versão de placa, se preferir: XT30UPB-M (C428721).
- Engrenagem da roda: a prévia supõe a engrenagem encostada no suporte, em |x| = 40…42; o contorno
  não passa de |x| = 40 e o XT30 fica a 10,4 mm desse plano.
- J3 deitado: folga da barra até o chão (ver relatório).
- Cristal X1: a prévia usa 3225; HC-49/S não cabe sob a bateria.
- Esquemático: já regerado (J1 = XT30U-M C99101, J3, Bluetooth e R18 = 4,7k na BOM; campo
  Footprint apontando para `seguidor_alpha`). Falta decidir os botões (B3U ou 6 × 6 THT, ver
  `hardware/preview/botoes_6x6.jpg`).

Baseado no EVA-RT © EXOTIC TEAM MX — AGPL-3.0.
