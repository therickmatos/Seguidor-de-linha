# Ferramentas

`designadores.py` — numeração por bloco de 07/11 (mapa antigo → novo e função de troca; `python designadores.py tabela`).
Os scripts antigos da prévia (v1) não foram atualizados e usam a numeração antiga.

## esquematico/ — fonte do esquemático
O esquemático da placa base é gerado por script, direto em S-expression do KiCad (sem GUI).
**Para mudar o esquemático, edite o `gen.py` e gere de novo**; não edite o `.kicad_sch` à mão, senão a próxima geração desfaz a mudança.

Dependências: Python 3 com `pillow`; KiCad 7 ou mais novo (`kicad-cli` e as bibliotecas de símbolos em `/usr/share/kicad/symbols/`, caminho definido em `kisch.py`); `poppler-utils` (`pdftoppm`).
No Ubuntu: `sudo apt install kicad poppler-utils` e `pip install pillow`.

- `kisch.py` — escritor mínimo de `.kicad_sch` (posiciona símbolos, fios, rótulos, símbolos de alimentação, textos e molduras).
- `drv8874.py` — símbolo próprio do DRV8874PWP (HTSSOP-16).
- `gen.py` — o projeto em si (8 blocos). Gera `seguidor_base.kicad_sch` e `intent.json` (ligações pretendidas + BOM).
- `render.sh` — `gen.py` → PDF (`kicad-cli`) → recortes PNG para conferência visual.
- `check.py` — compara a netlist exportada pelo KiCad com `intent.json` (redes fundidas, separadas, pinos sem uso).
- `make_pkg.py` — monta o pacote final (projeto, biblioteca local, PDF, BOM em CSV) em `pacote/seguidor_base/`.
- `redes.py` — gera `hardware/seguidor_base/REDES.md` (lista de redes legível, para conferir a importação no EasyEDA).

Gerar, conferir e publicar em `hardware/seguidor_base/` (rodar nesta pasta):

```
bash render.sh
kicad-cli sch export netlist --format kicadsexpr -o seguidor_base.net seguidor_base.kicad_sch
python3 check.py
python3 make_pkg.py
cp pacote/seguidor_base/* ../../hardware/seguidor_base/
python3 redes.py
```

As saídas intermediárias (`seguidor_base.kicad_sch`, `.pdf`, `.net`, PNGs, `pacote/`) ficam nesta pasta e são ignoradas pelo git. A geração é reprodutível (mesmo arquivo a cada rodada) e o UUID de cada símbolo depende só da referência, porque a placa `.kicad_pcb` se liga ao esquemático por esses UUIDs. O campo Footprint vem de `footprints_alpha.json` (gerado por `preview/kicad_exportar.py`). **Depois de regerar o esquemático, gere a placa KiCad de novo** (comandos no fim da seção da prévia v2).

## preview/ — preview de posicionamento da placa base (JPG)
Geometria mecânica (contorno B + STL do EVA-RT), biblioteca de footprints da BOM e posicionamento (em andamento).
Estado, convenções e próximos passos: `docs/HANDOFF_PREVIEW_2026-11-05.md`. Dependências em `preview/requirements.txt`.
`extrair_eprj.py` decodifica o `EVA_RT.eprj` (SQLite + base64/gzip) para texto, de onde saem posições, pads, trilhas e vias do EVA-RT.

No ambiente de nuvem "Seguidor-de-linha", o script de setup já cria o venv `/opt/seguidor-venv` (use `/opt/seguidor-venv/bin/python` no lugar de `python`) e baixa o FreeRouting 1.9.0 em `$FREEROUTING_JAR`; o KiCad (para `kicad_montar.py` e o esquemático) ainda é `sudo apt-get install -y kicad kicad-symbols poppler-utils`.

**Prévia v2 (06/11, atual)** — rodar em `preview/` (FreeRouting 1.9.0: `freerouting-1.9.0.jar` dos releases do GitHub, caminho em `FREEROUTING_JAR`; Java 17+):

```
python placa_v2.py               # posicionamento + checagens mecânicas
python rotear_v2.py dsn          # v2/seguidor_v2.dsn
python rotear_v2.py rotear 100   # FreeRouting -> v2/seguidor_v2.ses
python rotear_v2.py continuar 100  # (opcional) mais uma rodada a partir do SES
python rotear_v2.py importar     # finalizador, alargamento, plano de GND, verificação
python larguras.py               # larguras no caminho da corrente de cada rede de potência (IPC-2221)
python figura_v2.py              # hardware/preview/placa_v2.jpg
python relatorio_v2.py           # hardware/preview/RELATORIO_v2.md e posicoes_v2.csv
python pacote_alpha.py           # hardware/placa_alpha/: imagens, CSV, DXF do contorno e DXF-guia
```

Se a otimização final do FreeRouting travar, rodar sem ela: `FR_EXTRA="-mt 0" python rotear_v2.py rotear 100`.

**Simulação das marcas do TRIF** (rodar em `preview/`):

```
python marcas_sim.py               # QRE de marca x marcas do TRIF (v2/marcas_sim.json)
python marcas_sim.py --figura      # hardware/preview/marcas_trif_sim.jpg
```

**Placa em KiCad** (`hardware/seguidor_base/seguidor_base.kicad_pcb`) a partir da prévia v2 e do esquemático publicado:

```
python kicad_exportar.py           # (venv) v2/kicad_dados.json e esquematico/footprints_alpha.json
/usr/bin/python3 kicad_montar.py   # (python do KiCad, módulo pcbnew) monta a placa, preenche o GND, DRC e paridade
```

Por último, `python3 ../empacotar.py` monta `hardware/placa_base_alpha.zip` (projeto KiCad, pacote para o EasyEDA e prévia 3D).

O `kicad_montar.py` grava em `hardware/seguidor_base/` a placa, a biblioteca `seguidor_alpha.pretty`, o `fp-lib-table`, as regras no `.kicad_pro` (mantendo o que o esquemático já tinha) e o `drc_kicad.rpt`, e para com erro se algum pad sair do lugar do modelo. Se o `footprints_alpha.json` mudar (footprint novo ou trocado), regere o esquemático antes do `kicad_montar.py`.

## preview/ — roteamento no EasyEDA (08/11, placa RUSH)
Trabalham direto no `.epro` do EasyEDA Pro (zip com o `.epcb` em JSON por linha, unidades em mil).
Face de baixo = footprint espelhado em **y** e depois girado. Resumo do roteamento: `docs/ROTEAMENTO_2026-11-08.md`.

- `easyeda_cobre.py` — lê o `.epro` (peças, pads com rede, trilhas, vias, contorno, furos) e confere ligações (com `--gnd-planos`, o GND ligado pelos planos simulados a 0,3 mm), folgas, borda/furos, furo-furo, larguras de potência (pescoço e gargalo medidos como cadeia) e vias.
- `easyeda_cobre_figura.py` — figura das duas faces com os planos simulados e as ligações abertas.
- `easyeda_kicad_drc.py` — monta a mesma placa no KiCad 7 (python do sistema: `/usr/bin/python3.12`), preenche GND nas duas faces e roda o DRC do KiCad.
- `easyeda_rotear.py` — DSN/SES do FreeRouting a partir do `.epro` e gravação de trilhas, vias e planos (`POUR`) de volta.
- `grade.py` — roteador de grade (duas faces, folga garantida por construção) para fechar o que sobra.
- `rush_rotear.py`, `rush_gnd.py`, `rush_pipeline.py` — as etapas da placa RUSH: fanout de GND, FreeRouting, fechamento, costura, ligação de pads de GND (com arranque), limpeza e planos.

```
python rush_pipeline.py entrada.epro pasta saida.epro 2.5 30           # 1a versao (fanout + malha de costura)
python rush_pipeline.py plano roteada.epro pasta saida.epro            # plano puro + vias minimas
python rush_pipeline.py corrigir plano_vias.epro pasta saida.epro      # correcoes do DRC do EasyEDA (v2, atual)
python easyeda_cobre.py saida.epro --gnd-planos
/usr/bin/python3.12 easyeda_kicad_drc.py saida.epro conf.kicad_pcb 0.25
```

