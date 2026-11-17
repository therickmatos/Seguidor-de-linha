# Ferramentas

## bom_epro.py: BOM a partir do .epro
`python3 ferramentas/bom_epro.py <projeto.epro> <saida.csv>` lê os componentes colocados na PCB (designador, valor, encapsulamento, footprint, face, DNP, LCSC) e agrupa as linhas iguais. Gerou `hardware/placa_base/BOM_v12.csv`.

O gerador do esquemático KiCad rev 1.0 (de antes do layout) foi para `historico/esquematico_kicad_rev1.0/gerador/`.

## pecas_3d/ — peças impressas
Monta `mecânica/stl/` (subpastas `PETG/` e `PLA/`, conforme o filamento de cada peça) para a placa encomendada (Saturn v12, base de 1,6 mm) e a barra V1 de 1,6 mm. As peças são derivadas das do EVA-RT (© EXOTIC TEAM MX, AGPL-3.0):
- paramétricas: o patim da barra V1 e as presilhas da vareta de trás e da frente;
- adaptadas dos STL do EVA-RT: o bloco da transversal (com rebaixo para a asa) e a placa de sucção (com rebaixo para as cabeças);
- os STL do EVA-RT usados como estão, mais a caixa de redução espelhada.

A presilha sem braço de baixo e a conferência de parafusos e alturas vieram do repositório do perseguidor (`therickmatos/Perseguidor-de-linha`, `ferramentas/pecas_3d/`). Análise em `mecânica/SUPORTE_BARRA_V1.md`; guia de impressão e montagem em `mecânica/README.md`.

Dependências: `pip install -r ferramentas/pecas_3d/requisitos.txt`.

- `gerar_pecas.py` — peças (espessura da base e da barra, distância vareta–parafuso, folgas). Lê o contorno do `.epro` para o rebaixo do bloco. Antes de gravar, reconstrói o `sensor_sledge` e o `barilla_clamp` originais com os mesmos parâmetros e compara com os STL do EVA-RT.
- `conferir_montagem.py` — monta em 3D as peças e as placas e desenha as figuras de `mecânica/conferencia/`.
  - Entram a base (lida do `.epro`), a V1 (lida do Gerber), varetas, presilhas, blocos, carcaça, patins, parafusos, porcas, placa de sucção, a J3 deitada e os componentes da face de baixo.
  - Lista as interferências, as folgas e a altura de cada peça até a pista.

Rodar na raiz do repositório:
```bash
python3 ferramentas/pecas_3d/gerar_pecas.py
```
```bash
python3 ferramentas/pecas_3d/conferir_montagem.py --furos 63.14 --esp-barra 1.6
```

Se mudar a distância entre furos ou a espessura da barra, rodar de novo o `conferir_montagem.py`. Se sair outra versão da placa, trocar o `.epro` em `gerar_pecas.py` (`EPRO`, que o `conferir_montagem.py` também usa) e a espessura (`ESP_BASE`) e rodar os dois.
