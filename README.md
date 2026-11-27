# RUSH - SATURN: seguidor de linha baseado no EVA-RT

Robotracer com ventoinha centrífuga (sucção) para uma competição baseada no regulamento do TRIF 7ª edição.
Baseado no [EVA-RT](https://github.com/EXOTIC-TEAM-MX/EVA-RT) (© EXOTIC TEAM MX, AGPL-3.0).

- ATmega328P-AU, firmware próprio baseado no EVA-RT 1.2.2 (mesmo mapa de pinos): `firmware/`
- 2× DRV8874PWPR (motores coreless 1020), ITRIP ≈ 4,9 A; AO3400A na ventoinha
- Barra V1 de 12× QRE1113 + 74HC4067; 4 sensores de marca QRE1113GR nas abas (dois por lado)
- LiPo 2S 350 mAh (XT30), 78M05
- Contorno asa de gaivota, 172,2 × 58,6 mm

## Onde encontrar
| Para… | Abra |
|---|---|
| ver a placa encomendada (Gerber, `.epro`, o que foi pedido à JLC) | [`hardware/placa_base/`](hardware/placa_base/README.md) |
| comprar e soldar os componentes | [`hardware/placa_base/BOM_v12.csv`](hardware/placa_base/BOM_v12.csv) |
| imprimir as peças: um arquivo por impressão, com as peças já posicionadas | [`mecânica/mesas/`](mecânica/mesas/) e [`mecânica/README.md`, "Primeira impressão"](mecânica/README.md#primeira-impressão-ventoinha-e-motores) |
| ver o robô montado em 3D (apresentação) | [`mecânica/preview_3d/`](mecânica/preview_3d/README.md) |
| ver ou reimprimir uma peça avulsa (STL separados por material: PETG, PLA e resina) | [`mecânica/stl/`](mecânica/stl/) e [`mecânica/README.md`](mecânica/README.md#o-que-imprimir) |
| imprimir e testar a ventoinha e as caixas de redução antes da placa | [`mecânica/README.md`, "Primeira impressão"](mecânica/README.md#primeira-impressão-ventoinha-e-motores) |
| comprar parafusos, varetas e rolamentos | [`mecânica/README.md`, "Ferragens"](mecânica/README.md#ferragens) |
| montar o robô | [`mecânica/README.md`, "Ordem de montagem"](mecânica/README.md#ordem-de-montagem) |
| gravar e ajustar o firmware | [`firmware/README.md`](firmware/README.md) |
| testar a barra de sensores na bancada | [`firmware/teste_barra/`](firmware/teste_barra/) e [`hardware/barra_v1/`](hardware/barra_v1/README.md) |
| ler o regulamento | [`referencias/TRIF 2026 - Seguidor de Linha.pdf`](referencias/TRIF%202026%20-%20Seguidor%20de%20Linha.pdf) |
| consultar o projeto original | [`referencias/eva-rt/`](referencias/README.md) |

## Estado
- [x] Esquemático (rev 1.0 em KiCad; depois, no EasyEDA Pro)
- [x] Layout no EasyEDA Pro, conferido com os STL do EVA-RT
- [x] Gerber conferido e **placa encomendada na JLC (15/11/2026)**
- [x] Peças para imprimir e guia de montagem (`mecânica/`, para base e barra de 1,6 mm; conferido só em 3D)
- [x] Firmware (`firmware/seguidor/`; compila e passa no simulador, falta testar no robô)
- [ ] Montagem
- [ ] Teste do sentido dos motores e da ventoinha
- [ ] Firmware: leitura dos QRE internos (D8/D9) e ajuste na pista

## Estrutura
Em uso na montagem e na pista:

| Pasta | Conteúdo |
|---|---|
| [`hardware/`](hardware/placa_base/README.md) | `placa_base/`: **placa encomendada** (`.epro` do v12, Gerber, BOM, versões anteriores em `historico/`). `barra_v1/`: Gerber da barra de sensores (12 QRE1113, 1,6 mm) |
| [`mecânica/`](mecânica/README.md) | mesas prontas para imprimir (`mesas/`), STL avulsos por material (`stl/`), parafusos, ordem de montagem e conferência 3D (base e barra de 1,6 mm) |
| [`firmware/`](firmware/README.md) | `seguidor/` (firmware do robô), `testes/` (simulador do controle no PC), `teste_barra/` (teste de bancada da barra no ESP32-C3) |
| [`referencias/`](referencias/README.md) | regulamento do TRIF 2026 e cópia do EVA-RT (projeto EasyEDA, Gerbers, PDFs, STL, firmware 1.2.2) |

Para gerar arquivos e para consulta:

| Pasta | Conteúdo |
|---|---|
| [`ferramentas/`](ferramentas/README.md) | `pecas_3d/` (gera os STL de `mecânica/` e faz a conferência 3D) e `bom_epro.py` (BOM a partir do `.epro`) |
| [`estudo_de_caso/`](estudo_de_caso/README.md) | estudos que levaram às decisões: marcas do TRIF (06, 07) e chassi asa de gaivota (08, com o histórico do layout versão a versão) |
| [`historico/`](historico/README.md) | antes do layout (02 a 09/11): decisões, contorno B, esquemático KiCad rev 1.0 e seu gerador |

O perseguidor (placa "RUSH - Dreamcast") está em [therickmatos/Perseguidor-de-linha](https://github.com/therickmatos/Perseguidor-de-linha). O seguidor em fenolite está em [therickmatos/seguidor-fenolite](https://github.com/therickmatos/seguidor-fenolite).

## Licença
GNU Affero General Public License v3.0 (`LICENSE`), a mesma do EVA-RT.
