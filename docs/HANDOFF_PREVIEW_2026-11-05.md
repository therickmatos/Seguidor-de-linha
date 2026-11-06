# Handoff — preview de posicionamento da placa base (05/11/2026)

## Atualização de 06/11 — ler primeiro

O Erick autorizou apagar as trilhas antigas e pediu XT30 no canto inferior esquerdo, J2/J3 centralizados, sensores laterais horizontais e preferência pelo FreeRouting. Depois pediu **uma única imagem** com a versão de menos pendências, seguida de uma explicação e pausa antes de resolver as causas e rotear novamente. Não iniciar novo roteamento sem primeiro discutir o diagnóstico com ele.

O novo posicionamento usa J1 (−35,5; −31,7), lado reto = +; J2 (0; 22,74); J3 (0; −28,8), 90° para trás; U1 (0; −22,25), −45°. A traseira foi ampliada simetricamente até y = −35 mm, preservando os furos e os rasgos; ver `hardware/preview/contorno_b_xt30.dxf`. O padrão dos pads QRE veio do Gerber EVA-RT, na horizontal. Os diâmetros dos pads e furos do XT30 foram estimados da imagem e devem ser conferidos fisicamente.

O resultado tem **21 ligações abertas**, inclusive VBAT e OUT nos dois drivers; a checagem independente encontrou zero violações de folga no modelo. As redes, limitações e conferências estão em `hardware/preview/RELATORIO.md`, `pendencias_roteamento.csv` e `ferramentas/preview/verificacao_cobre.json`. A imagem **atual** é `hardware/preview/placa_completa.jpg`; `placa_top.jpg`, `placa_bottom.jpg` e `mudancas_vs_eva-rt.jpg` são históricos da sessão anterior. `freerouting_io.py` gera o modelo Specctra e lê a sessão; este é um modelo de prévia com pads individuais, não um projeto EasyEDA de fabricação.

As informações a seguir são históricas e subordinadas a esta atualização e ao último pedido do usuário.

Para o agente que continua o trabalho. Leia antes: `CLAUDE.md`, `docs/DECISOES_2026-11-05.md` (decisões de hoje) e `ferramentas/preview/BRIEFING.md` (referencial e restrições mecânicas).
Branch: `claude/jolly-hypatia-g6elan` (repositório `therickmatos/Seguidor-de-linha`).

## Atualização posterior — estado atual

O pedido mais recente prevalece sobre o restante deste handoff: os três botões são **B3U SMD 3,0 × 2,5 mm** nas posições originais, não os THT 6 × 6. U1 permanece em (0; −23), −45°; a bateria atravessa a traseira e os motores ficam sobre os drivers. J4 e R16/R17/R18 são obrigatórios.

As figuras `hardware/preview/placa_completa.jpg`, `placa_top.jpg`, `placa_bottom.jpg` e `mudancas_vs_eva-rt.jpg` foram geradas; `placa_etapa1.jpg` registra a primeira entrega e usa a posição anterior dos desacoplamentos. A posição atual está em `ferramentas/preview/posicoes.csv`. Há **34 ligações ainda abertas**, não comprovadas impossíveis: estão em amarelo e discriminadas em `hardware/preview/pendencias_roteamento.csv` e `RELATORIO.md`. O resultado ainda não é roteamento completo.

As propostas J1 (−54; 4,5), X1 3225 (−7,9; −25,3) e J3 (9; −28,75) aguardam decisão. O pad J3.1 colide com o rasgo original; o deslocamento proposto de 2,2 mm exige também alterar o contorno, e não foi aplicado à geometria aprovada. A verificação de cobre registrou apenas esse conflito de borda/furo e nenhuma folga entre redes diferentes abaixo de 0,19 mm no modelo; conferir o DRC real, alturas, corrente e os footprints.

Scripts novos em `ferramentas/preview/`: `layout_placa.py`, `trilhas_eva.py` (extração/classificação), `rotear.py`, `ajustar_trechos.py`, `alargar_potencia.py`, `verificar_cobre.py`, `gerar_figuras.py` e `gerar_relatorio.py`. `trilhas_classificadas.json` registra o cobre de origem; `trilhas_roteadas.json` contém os caminhos finais parciais e o ratsnest; `verificacao_cobre.json` registra a checagem. Para regenerar as figuras do estado salvo, executar `python gerar_figuras.py final` nessa pasta, após instalar `requirements.txt`.

O registro seguinte é histórico; onde divergir, valem esta atualização, `DECISOES_2026-11-05.md` e o pedido mais recente do Erick.

## O que o Erick pediu
Um **preview da placa base em JPG** (não arquivo KiCad) para guiar o posicionamento e o roteamento que ele vai fazer no EasyEDA Pro. O preview considera:
- os componentes reais da BOM;
- a base do robô (STL do EVA-RT);
- os botões que ele já tem.

Nesta sessão ele pediu que o trabalho fosse feito por agentes Haiku em esforço máximo. Para a próxima, siga o que ele pedir.
Depois, acrescentou:
1. **Botão: THT de 2 terminais** (6 × 6 × 4,5), não de 4.
2. **J1 = XT30 macho de placa** (foto em `hardware/preview/xt30_m_foto_erick.png`); **lado reto = +**.
3. **Bluetooth obrigatório:** J4, R16, R17 e R18 vão na placa.
4. **Usar as trilhas do EVA-RT como base:** reaproveitar o máximo e redesenhar só o necessário.

## Estado
| Etapa | Estado | Onde |
|---|---|---|
| Geometria: contorno B, furos reais, áreas proibidas dos STL | **pronta e conferida** | `ferramentas/preview/geometria.{py,json}`, figura `hardware/preview/conf_geometria.jpg` |
| Footprints de toda a BOM, pino a pino com `REDES.md` | **pronta** (teste OK: 69 refs, 225 pinos) | `ferramentas/preview/footprints.py`, `teste_footprints.py`, figura `hardware/preview/conf_footprints.jpg` |
| Posicionamento | **interrompido no meio** (ainda com colisões) | `posicoes.csv/json`, `log_build.json`, scripts `fixos.py`, `build_pos.py`, … |
| JPGs finais (cima, baixo, ligações) | **não feitos** | — |
| Trilhas do EVA-RT no preview | **não começado** (pedido novo) | — |

### Geometria (confiável)
- Contorno do DXF (mm, sem correção); furos conferidos no Gerber: carcaça 4 × Ø2,0 (±15,556; ±15,556), suportes de motor 4 × Ø2,0 (±35,25; −3,733/−26,55), presilhas 4 × Ø2,0 (±43,75; −1,75/10,75), velcro 7 × 1 mm em (±16,685; −28,213), ventoinha Ø17.
- STL casados pelos furos (erro ≤ 0,001 mm): `impeller_base_1` (girado 45°), `suction_base` (translação (0; −27,5)), `gearbox` (direito (+30,5; −19,027), esquerdo espelhado).
- Confiança **baixa**: `battery_holder` (sem furo para casar; posição suposta em (0; −24,6)) e `barilla_clamp` (posição pelo desenho do EasyEDA do EVA-RT). Confiança **média**: rotor (`impeller_fan`, disco r ≤ 17 tocando a placa em z = 0 **no referencial do STL**, que não foi provado ser o da montagem) e orientação da carcaça.
- Bateria: 45 mm em x (x ±22,5), y −42,6…−22,1, apoio a 3,0 mm. (Um briefing anterior dizia x ±10,25: errado, já corrigido no script.)
- Alturas medidas: carcaça (pés 0–5 mm; anel a partir de 11,2–12,0 mm); gearbox (flange 2,5 mm, corpo até 14,3 mm).

### Footprints (convenções que pegam)
- `pads_absolutos(ref, x, y, rot, lado=None)`: com `lado="BOTTOM"` espelha x antes de girar (vista através da placa, sem espelhar a figura). J5, S0 e S1 saem em BOTTOM por padrão; qualquer outro componente embaixo precisa de `lado="BOTTOM"`. O `ICSP_6P_SMD_BOT` já é desenhado espelhado.
- `MOTOR_1020_2P` (M1–M3): o "corpo" 10 × 20 é fictício. Os pads são só pontos de solda dos fios: **ignorar o corpo** em colisão e desenho.
- `HDR_RA_1x05_P2.54` (J3): com rot 0 o corpo fica para −y e o pino 1 (+5V) em +x. Visto por trás do robô, a ordem fica +5V, GND, RX, TX, DTR da esquerda para a direita. Isso foi aceito.
- TQFP-32 vem do footprint do EVA-RT (pino 1 na borda de baixo, à esquerda): com rot −45 bate com o EVA-RT.
- **Desatualizados pelas decisões de hoje** (corrigir em `footprints.py` e rodar `teste_footprints.py`):
  - botão: o padrão é `SW_6x6_THT_4P`. Criar `SW_6x6_THT_2P` com 2 pads (pino 1 e pino 2 do símbolo); a distância entre terminais será medida pelo Erick;
  - J1: o padrão é `XT30PW_M_PCB` (horizontal). Trocar pelo XT30 macho da foto (código e footprint da LCSC); o pad + fica no lado reto do corpo;
  - J4 e R16–R18: deixar de ser opcionais (afeta só legenda/relatório).
- Medidas não conferidas em datasheet porque o proxy bloqueou `ti.com` e `onsemi.com`: pad térmico do DRV8874 (usado 3,4 × 5,0 do KiCad) e land pattern do QRE1113GR. No EasyEDA o Erick usa os footprints da LCSC (DRV8874PWPR = C1855818). Para o preview basta.

### Posicionamento interrompido (`posicoes.csv`, gerado por `verifica.py`)
O agente estava resolvendo os desacoplamentos dos DRV quando foi parado. Erros que sobraram (`log_build.json`):
- C6, C13, C14 sobrepõem U2 (e C6/C13 o SW0); C7, C15, C16 sobrepõem U3.
- Os capacitores 0603 não cabem todos a ≤ 2 mm dos pinos de passo 0,65. Distribuir pelos dois lados do CI e aceitar ~3–4 mm.

Escolhas provisórias que precisam ser revistas com a nova orientação de reaproveitar trilhas:
- **U1 ficou em (0; −23) rot −45, igual ao EVA-RT.** A posição (0; −18) invadia o disco do rotor (r ≤ 17).
- **J3 foi para x = +9** (proposta de afastar o rasgo do velcro 2,2 mm). Com o U1 em (0; −23), o J3 não cabe centrado: os pads do U1 descem até y ≈ −28,4 e a borda central é y = −30. Decisão do Erick (ver abaixo).
- **Botões provisórios** (com o footprint de 4 terminais, que agora mudou): SW0 em (−26,4; −20,5), SW1 em (27,0; 10,7), SW2 em (27,2; −20,5), todos rot 90. Não foram conferidos visualmente, e acessibilidade (gearbox de 14 mm ao lado) e trilhas do EVA-RT não foram consideradas.
- **Q1 foi para a face BOTTOM** em (29,72; −1,18), porque o SW1 tomou o lugar previsto (25,8; 5,6). Rever.
- **X1 = cristal 3225** em (−7,9; −25,3), porque fica sob a bateria e o HC-49/S não cabe ali. Confirmar com o Erick qual cristal ele tem.
- **J1 (rabicho) em (−27,2; −0,8).** O antigo VIN (−36,35; −30,25) não comportava o XT30PW-M. Refazer com o XT30 da foto.
- **J4 em x = 33,0** (pino 1 em y = 0,7).
- **Braços:** S0/S1 embaixo em (∓69,5; 4,5), LED1/LED2 em cima sobre eles. R20/R30 e R21/R31 embaixo, R6/R7 em cima, nos braços.

## Próximos passos (ordem sugerida)
1. **Atualizar footprints** (botão 2 terminais, XT30 da foto, J4 obrigatório) → `teste_footprints.py` OK.
2. **Trilhas do EVA-RT** (pedido novo, central). Rodar `python3 extrair_eprj.py` (gera `eprj/`).
   - Formatos no bloco `["DOCTYPE","PCB"]` de `eprj/eva_rt_pcb_b73a4a.txt`, em mil (× 0,0254 = mm), já no referencial do seguidor:
     - `["LINE", id, 0, rede, camada(1 TOP, 2 BOTTOM), x1, y1, x2, y2, largura, travado]`;
     - `["VIA", id, 0, rede, "", x, y, furo, diâmetro, …]`;
     - também `POLY`/`FILL` (cobre e furos), `PAD`/`PAD_NET` (pads e redes).
   - São 613 LINE, 89 VIA, 43 redes.
   - Classificar cada trilha:
     - **reaproveitável:** liga só componentes/pads que ficam no lugar;
     - **a ajustar:** termina num componente trocado ou movido (IFX → DRV8874, FPC → J2, conector do conversor → J3, VIN → J1, botões, Q1, asas → braços), e o trecho final se refaz;
     - **remover:** redes que saíram, ex. `$LED3_2`, ou que cruzam a cortesia de um componente novo.
   - Use o mapa de redes abaixo.
3. **Rever o posicionamento com a regra "trilha do EVA-RT primeiro"**: preferir posições em que as trilhas existentes continuem servindo; o critério de desempate passa a ser "metros de trilha do EVA-RT reaproveitada". Resolver os erros dos desacoplamentos.
4. **JPGs** em `hardware/preview/` (especificação da sessão anterior, ainda válida):
   - **geral:** ~4200 px de largura, escala 1:1, fundo escuro, textos em português, grade de 5 mm cotada, contorno e furos, áreas proibidas, pads reais, pino 1 marcado, referência de cada componente;
   - **`preview_top.jpg`:** face de cima;
   - **`preview_bottom.jpg`:** face de baixo vista através da placa, sem espelhar, como no EasyEDA;
   - **`preview_ligacoes.jpg`:** ratsnest por árvore geradora mínima, cores VBAT laranja, +5V vermelho, GND verde fraco, OUT_* roxo, sinais ciano;
   - **`preview_trilhas_eva-rt.jpg`** (novo): trilhas do EVA-RT coloridas pela classificação do passo 2, sob o posicionamento novo;
   - **tabela:** `posicoes.csv` com ref, face, x, y, rot, para digitar no EasyEDA (rotação anti-horária relativa ao footprint da biblioteca; no EasyEDA, orientar pelo pino 1).
   - Abrir cada JPG (recortes ampliados nas regiões densas) e corrigir antes de entregar.
5. **Esquemático:** aplicar no `gen.py` as mudanças de BOM de `DECISOES_2026-11-05.md` (precisa de KiCad para regerar; nesta sessão não havia `kicad-cli`).

## Decisões em aberto (perguntar ao Erick; não decidir por ele)
1. **J3 × U1:** com o U1 no lugar do EVA-RT (bom para reaproveitar trilhas), a barra 1×5 de 2,54 mm não cabe centrada na borda traseira. Opções:
   - (a) J3 fora do centro (ex.: x ≈ +9), afastando o rasgo do velcro ~2 mm (muda o contorno);
   - (b) U1 para a frente, refazendo as trilhas do U1; depende de confirmar a altura real do rotor;
   - (c) U1 com outra rotação ou posição;
   - (d) J3 noutro ponto da borda.
2. **Altura do rotor:** confirmar com os STL montados (impeller_base_1/2 + impeller_fan + motor) a folga entre o rotor e a placa. Se houver folga ≥ 1,5 mm, componentes baixos (TQFP 1,2 mm) podem entrar sob o rotor.
3. **Fluxo no EasyEDA para reaproveitar trilhas.** Hoje a fonte do esquemático é o KiCad (`gen.py`) importado no EasyEDA. Trilhas copiadas do PCB do EVA-RT trazem as redes antigas (nomes diferentes; ver mapa abaixo). Duas opções:
   - (A) colar as trilhas no projeto importado e reatribuir as redes;
   - (B) partir do `EVA_RT.eprj` e editar o esquemático do EVA-RT no EasyEDA. Isso quebra a regra "KiCad é a fonte".

   Apresentar as opções ao Erick; ele decide.
4. Posição dos botões (2 terminais) e do XT30; qual cristal (HC-49/S ou 3225) vem do Nano/Uno doador.

## Mapa de redes EVA-RT → seguidor (rascunho; conferir com `REDES.md`)
| EVA-RT | Seguidor | | EVA-RT | Seguidor |
|---|---|---|---|---|
| `VCC` | `VBAT` | | `S0/A0`…`S3/A3` | `S0_A0`…`S3_A3` |
| `+5V`, `GND` | iguais | | `C0/A4` | `C0_A4` |
| `RESET` | `RESET` | | `Y0/A5` / `Y1/A6` | `MARK_L_A5` / `MARK_R_A6` |
| `RX/D0` / `TX/D1` | `RX_D0` / `TX_D1` | | `LED1/D2` / `LED2/D7` | `LEDA_D2` / `LEDB_D7` |
| `DIRA/D3` / `DIRB/D4` | `DIRA_D3` / `DIRB_D4` | | `LED3/D13` | `LEDC_D13` |
| `PWMA/D5` / `PWMB/D6` | `PWMA_D5` / `PWMB_D6` | | `B1/D11` / `B2/D12` | `B1_D11` / `B2_D12` |
| `PWMC/D10` | `PWMC_D10` | | `$U1_7` / `$U1_8` | `XTAL1` / `XTAL2` |
| `OUT_A1/A2/B1/B2`, `OUT_C` | iguais | | `$C10_1` | `AREF` |
| `$Q1_1` | `Net-(Q1-G)` | | `$R20_2` / `$R21_2` | `Net-(S0-A)` / `Net-(S1-A)` |
| `$LED1_2`, `$LED2_2`, `$LED4_2`, `$LED5_2`, `$LED6_2`, `$LED7_2` | `Net-(LEDx-A)` | | `P3` | J2.3 (sem ligação) |
| `$LED3_2` | — (LED3 saiu) | | — | novas: `DTR`, `BT_RXD`, `BT_TXD`, `VCP_*`, `CPH_*`, `CPL_*`, `IPROPI_*`, `VREF`, `DRV_SLEEP`, `VBAT_A7` |

## Como rodar (`ferramentas/preview/`)
```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python extrair_eprj.py          # eprj/ + eva_rt_componentes.csv
.venv/bin/python geometria.py             # geometria.json + conf_geometria.png (~20 s)
.venv/bin/python teste_footprints.py      # confere footprints × BOM × REDES.md
.venv/bin/python conf_footprints.py       # conf_footprints.png
.venv/bin/python grids.py                 # grades.npz (cache usado por place_lib.py)
.venv/bin/python verifica.py              # roda build_pos/fixos e grava posicoes.csv/json, ratsnest.json
```
- `diag*.py` e `analise/` são scripts de exploração das sessões anteriores (STL, colisões).
- `BRIEFING.md` e `REGRAS_POSICIONAMENTO.md` foram as instruções dadas aos agentes. As "Notas do coordenador", no fim das regras, valem mais que o texto acima delas. As decisões de 05/11 valem mais que as duas.
- Ambiente desta sessão: os sites da TI e da onsemi estavam bloqueados pelo proxy, e não havia KiCad instalado.

Crédito: baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
