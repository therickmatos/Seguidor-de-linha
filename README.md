# RUSH - SATURN: seguidor de linha baseado no EVA-RT

Robotracer com ventoinha centrífuga (sucção) para uma competição baseada no regulamento do TRIF 7ª edição.
Baseado no [EVA-RT](https://github.com/EXOTIC-TEAM-MX/EVA-RT) (© EXOTIC TEAM MX, AGPL-3.0).

- ATmega328P-AU, firmware EVA-RT 1.2.2 (mesmo mapa de pinos)
- 2× DRV8874PWPR (motores coreless 1020), ITRIP ≈ 4,9 A; AO3400A na ventoinha
- Barra V1 de 12× QRE1113 + 74HC4067; 4 sensores de marca QRE1113GR nas abas (dois por lado)
- LiPo 2S 350 mAh (XT30), 78M05
- Contorno asa de gaivota, 172,2 × 58,6 mm

## Estado
- [x] Esquemático (rev 1.0 em KiCad; depois, no EasyEDA Pro)
- [x] Layout no EasyEDA Pro, conferido com os STL do EVA-RT
- [x] Gerber conferido e **placa encomendada na JLC (15/11/2026)**
- [ ] Montagem
- [ ] Teste do sentido dos motores e da ventoinha
- [ ] Firmware: leitura dos QRE internos (D8/D9)

## Estrutura
| Pasta | Conteúdo |
|---|---|
| [`hardware/placa_base/`](hardware/placa_base/README.md) | **placa encomendada**: `.epro` do v12, Gerber, BOM, histórico das versões |
| `hardware/barra_v1/` | Gerber da barra de sensores V1 (12 sensores) |
| `hardware/contorno/` | contorno B "degraus" (histórico, até a v3) |
| `hardware/seguidor_base/` | esquemático rev 1.0 em KiCad (histórico) |
| `hardware/figuras/` | posição do conector do Bluetooth |
| [`estudo_de_caso/`](estudo_de_caso/README.md) | simulações das marcas do TRIF (06, 07) e projeto do chassi asa de gaivota (08, com o histórico do layout e os scripts) |
| `docs/` | decisões de 02 a 04/11/2026 (antes do layout) |
| `ferramentas/` | gerador do esquemático KiCad; `bom_epro.py` (BOM a partir do `.epro`) |
| `referencias/eva-rt/` | cópia do EVA-RT: projeto EasyEDA Pro, Gerbers, PDFs, STL e firmware |

O perseguidor (placa "RUSH - Dreamcast") está em [therickmatos/Perseguidor-de-linha](https://github.com/therickmatos/Perseguidor-de-linha). O seguidor em fenolite está em [therickmatos/seguidor-fenolite](https://github.com/therickmatos/seguidor-fenolite).

## Licença
GNU Affero General Public License v3.0 (`LICENSE`), a mesma do EVA-RT.
