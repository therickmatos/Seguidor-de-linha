# Seguidor de linha — baseado no EVA-RT

Robotracer com ventoinha centrífuga para uma competição baseada no regulamento do TRIF 7ª edição.
Baseado no [EVA-RT](https://github.com/EXOTIC-TEAM-MX/EVA-RT) (© EXOTIC TEAM MX, AGPL-3.0).

- ATmega328P-AU, firmware EVA-RT 1.2.2 (mesmo mapa de pinos)
- 2× DRV8874 (motores coreless 1020), AO3400A na ventoinha
- Barra de 12× QRE1113 + 74HC4067, sensores de marca nos braços laterais
- LiPo 2S 350 mAh, contorno "B degraus" de 148,2 × 57,6 mm

## Estado
- [x] Componentes definidos
- [x] Contorno definitivo (`hardware/contorno/`)
- [x] Esquemático rev 1.0 em KiCad (`hardware/seguidor_base/seguidor_base.pdf`; fonte em `ferramentas/esquematico/`)
- [ ] Importação no EasyEDA Pro (em andamento; conferir com `hardware/seguidor_base/REDES.md`)
- [ ] Layout da placa (EasyEDA Pro)
- [ ] Pedido na JLC
- [ ] Montagem e firmware

## Estrutura
| Pasta | Conteúdo |
|---|---|
| `docs/` | decisões (as mais novas: `DECISOES_2026-11-04.md`), contorno e esquemático |
| `hardware/contorno/` | contorno B definitivo (DXF) e figuras de conferência |
| `hardware/seguidor_base/` | esquemático rev 1.0 (projeto KiCad, PDF), BOM, lista de redes (`REDES.md`) |
| `hardware/barra_v1/` | Gerber da barra de sensores V1 (12 sensores) |
| `hardware/figuras/` | posição do conector do Bluetooth |
| `Perseguidor de linha/` | perseguidor (placa sem os braços + receptor IR KY-022): projeto EasyEDA Pro e revisão |
| `ferramentas/esquematico/` | scripts que geram o esquemático KiCad, a BOM e a lista de redes |
| `referencias/eva-rt/` | cópia do EVA-RT: projeto EasyEDA Pro, Gerbers, PDFs, STL e firmware |

O seguidor em fenolite é outro projeto e não está neste repositório.

## Licença
GNU Affero General Public License v3.0 (`LICENSE`), a mesma do EVA-RT.
