# Ferramentas

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

As saídas intermediárias (`seguidor_base.kicad_sch`, `.pdf`, `.net`, PNGs, `pacote/`) ficam nesta pasta e são ignoradas pelo git. Os UUIDs mudam a cada geração, então o `.kicad_sch` publicado muda inteiro mesmo sem mudança de ligação: confira pelo `check.py` e pelo diff do `REDES.md`.

## preview/ — preview de posicionamento da placa base (JPG)
Geometria mecânica (contorno B + STL do EVA-RT), biblioteca de footprints da BOM e posicionamento (em andamento).
Estado, convenções e próximos passos: `docs/HANDOFF_PREVIEW_2026-11-05.md`. Dependências em `preview/requirements.txt`.
`extrair_eprj.py` decodifica o `EVA_RT.eprj` (SQLite + base64/gzip) para texto, de onde saem posições, pads, trilhas e vias do EVA-RT.
