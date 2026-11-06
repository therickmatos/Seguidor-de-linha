# Placa base — versão alpha (06/11/2026)

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

## Conferir antes de pedir na JLC

- XT30 (J1): medir o corpo do macho e o plugue fêmea encaixado; pads Ø3,9 e furos Ø2,5 são estimados.
- Engrenagem da roda: medir a distância da face da engrenagem até a face externa do suporte
  (a prévia supõe encostada em |x| = 40; o XT30 fica a 2 mm desse plano).
- J3 deitado: folga da barra até o chão (ver relatório).
- Cristal X1: a prévia usa 3225; HC-49/S não cabe sob a bateria.
- Esquemático (`ferramentas/esquematico/gen.py`): texto e BOM do J3 (agora SMD embaixo),
  código LCSC do XT30, B3U e Bluetooth obrigatório (ver `docs/DECISOES_2026-11-05.md`).

Baseado no EVA-RT © EXOTIC TEAM MX — AGPL-3.0.
