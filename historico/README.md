# Histórico: antes do layout (02 a 09/11/2026)

Material das fases anteriores ao layout da placa encomendada (Saturn v12, `hardware/placa_base/`). Fica aqui para consulta; **não vale para a placa encomendada** onde as duas divergem.

| Pasta | Conteúdo |
|---|---|
| `decisoes/` | decisões de 02 a 04/11: componentes, pedido na JLC, contorno B e esquemático rev 1.0 |
| `contorno_B/` | contorno B "degraus" (148,2 × 57,6 mm, até a v3) e figuras de conferência |
| `esquematico_kicad_rev1.0/` | esquemático rev 1.0 em KiCad (PDF, projeto, BOM, `REDES.md`), e o gerador em Python (`gerador/`) |
| `figuras/` | posição do conector do Bluetooth (fase do contorno B) |

Também é histórico:
- a v3 (contorno B, um QRE por lado), em `estudo_de_caso/01_projeto/`;
- as versões v4 a v10 do layout, em `hardware/placa_base/historico/`.

## Branches antigos no GitHub (17/11/2026)
O branch principal é o `main`. Os outros branches são de sessões anteriores. Apagar um branch no GitHub tem volta: a página "Branches" mostra "Restore" logo depois.

Já estão inteiros no `main`, então dá para apagar sem perder nada:
- `claude/vibrant-feynman-stdvz2`: era o padrão até 17/11. Trocar o padrão para `main` antes de apagar.
- `claude/wizardly-shannon-88f37e`: placa encomendada (v12).
- `claude/vibrant-hypatia-qzvmuv`: primeira versão de `mecânica/`.
- `ccr-4e7d43a4-bif1wb`: firmware.
- `claude/confident-gates-8pgim4`: pista TRIF 2024 e análise de L.

Têm coisas que **não** estão no `main`. Todas foram superadas, mas só se perdem se o branch for apagado:

| Branch | Data | O que tem | Onde está o que o substituiu |
|---|---|---|---|
| `claude/jolly-hypatia-g6elan` | 06/11 | prévia v2 da placa (contorno B) | `hardware/placa_base/` (v12) |
| `claude/funny-johnson-loahd4` | 07/11 | PCB do EasyEDA revisada (contorno B) | idem |
| `claude/loving-brahmagupta-x2x4pv` | 08/11 | Saturn corrigido v2 (contorno B) | idem |
| `simulacao-marcas-site` | 09/11 | site de simulação das marcas da v3 (PR #1) | `estudo_de_caso/06_estudo_consolidado/simulador.html` |
| `ccr-0f7dfdf7-6w0a8n` | 11/11 | primeiros arquivos do perseguidor | repositório `therickmatos/Perseguidor-de-linha` |
| `claude/bold-carson-hbu2ra` | 15/11 | Dreamcast gerado a partir do Saturn | idem |
| `claude/tender-feynman-jfmnaj` | 15/11 | teste de bancada da barra em `ferramentas/teste_barra/` | `firmware/teste_barra/` (mesmos arquivos) |
