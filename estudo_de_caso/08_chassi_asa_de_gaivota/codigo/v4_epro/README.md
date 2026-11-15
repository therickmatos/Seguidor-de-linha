# v4 (asa de gaivota) a partir do projeto EasyEDA Pro da v3

`build.py` lê `ProPrj_RUSH - SATURN - v3_2026-11-09.epro` (em `estudo_de_caso/01_projeto/`) e grava
`ProPrj_RUSH - SATURN - v4_asa_gaivota_2026-11-11.epro`. Baseado no EVA-RT, © EXOTIC TEAM MX, AGPL-3.0.

O que o script faz:

1. Troca o contorno (camada 11) pelo da asa de gaivota (`../contorno.py`, 172,2 × 58,6 mm).
2. Leva os 5 componentes de cada aba antiga (QRE, 220, 47k, 1k, LED) e as trilhas internas da aba para o QRE externo (±81,5; 16), com deslocamento de (±12; +11,5) mm.
3. Apaga as 8 trilhas que iam do corpo à aba antiga e traça as novas na camada de cima: LED, +5V (0,5 mm) e sinal de marca, subindo a 45° pela aba.
4. Acrescenta os QRE internos E1 (S3) e D1 (S4) em (±50,5; 14), girados 45° para os pads caberem na aba. Cada um leva 220 Ω, 47 kΩ e 10 nF **DNP** (`PINOS.md`), com roteamento local na camada de baixo e vias para +5V e GND.
5. Cria as redes `MARK_L2_D8` (ATmega pino 12) e `MARK_R2_D9` (pino 13), `QRE_E1_A` e `QRE_D1_A`, no esquemático (bloco copiado dos sensores atuais) e na PCB.
6. Remove o cobre despejado (`POURED`): ele é refeito no EasyEDA.

`check.py` é uma checagem de folgas aproximada: 0,2 mm entre redes, 0,3 mm até a borda e até furos não metalizados. Nos objetos novos ou movidos, ela não acusa nenhum problema. Não substitui o DRC do EasyEDA.

Falta fazer no EasyEDA: ver a seção "Ao abrir" na resposta do 11/11 ou em `../../PINOS.md`.

## Correções sobre os arquivos do Erick

As saídas estão em `hardware/placa_base/historico/`, exceto o v10, que está em `hardware/placa_base/`. As entradas recebidas do Erick estão em `entradas/`. Uso: `python3 <script> <entrada> <saída>`, com exceção dos casos indicados.

| Script | Data | Entrada | Saída |
|---|---|---|---|
| `build.py` (sem argumentos) | 11/11 | v3 (`estudo_de_caso/01_projeto/`) | v4_asa_gaivota_2026-11-11 |
| `corrige_erick.py <entrada>` | 12/11 | `entrada_erick_2026-11-12` | v4_asa_gaivota_2026-11-12 |
| `corrige_v7.py` | 13/11 | `entrada_erick_v7_2026-11-13` | v7_2026-11-13_corrigido |
| `caps_smd.py` | 14/11 | `entrada_erick_v8f1_2026-11-14` | v8_2026-11-14 |
| `corrige_v81.py` | 14/11 | `entrada_erick_v81_2026-11-14` | v81_2026-11-14_corrigido |
| `corrige_v82.py` | 14/11 | `entrada_erick_v82_2026-11-14` | v82_2026-11-14_corrigido |
| `corrige_v83.py` | 14/11 | v82 corrigido | v83_2026-11-14 |
| `corrige_v84.py` | 14/11 | v83 | v84_2026-11-14 |
| `corrige_v85.py` | 14/11 | v84 | v85_2026-11-14 |
| `corrige_v87.py` | 14/11 | `entrada_erick_v86_2026-11-14` | v87_2026-11-14 |
| `serigrafia_v88.py` | 14/11 | `entrada_erick_v88_2026-11-14` | v88_2026-11-14_serigrafia |
| `corrige_v89.py` | 15/11 | `entrada_erick_v89_2026-11-15` | v89_2026-11-15 |
| `copia_serigrafia_dreamcast.py <dreamcast> <saturn> <saída>` | 15/11 | `ref_dreamcast_v3` + `entrada_erick_v10_2026-11-15` | **v10_2026-11-15_serigrafia (placa encomendada)** |

O que cada versão mudou está em `../../PINOS.md`. O `entrada_erick_v8_2026-11-13` e o `entrada_erick_v87_2026-11-14` são arquivos do Erick guardados só para referência: a lista de capacitores e resistores saiu do primeiro, e o segundo foi conferido sem gerar arquivo novo.

## Conferências (não alteram o arquivo)

- `interferencias_stl.py <placa.epro>`: componentes × peças do EVA-RT (hélice, carcaça, caixa de redução, motores, placa de sucção, rodas).
- `corrente.py` e `resumo_larguras.py`: largura das trilhas de potência e corrente pela IPC-2221.
- `verifica_placa.py` e `check.py`: folgas, aproximação do DRC. `conexoes.py`: conectividade por rede. `netlist_sch.py`: esquemático × PCB. `angulos.py`: cantos de trilha de 90° ou menos.
- `plano_gnd.py`, `pour_sim.py`, `poured.py`, `costura_gnd.py`: simulação do plano de GND e vias de costura.
- `zoom.py`, `zoom_gnd.py`, `plot.py`, `explora.py`: figuras e exploração.
- `engrossa_logo.py`: engrossa o traço fino do SVG da logo do IF (variáveis `LARG` e `SAIDA`).
- `route.py`, `route_v4.py`: roteador A* usado pelo `build.py`.
