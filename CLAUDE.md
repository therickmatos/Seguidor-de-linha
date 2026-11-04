# CLAUDE.md — contexto para o Claude Code

## Como trabalhar
- Responder em **português**, de forma direta e concisa. O Erick (estudante de eletrônica, IFSP) revisa e corrige o que recebe.
- Antes de afirmar algo sobre o projeto, ler o doc correspondente em `docs/`. As decisões mais novas estão em `docs/DECISOES_2026-11-04.md` e `docs/SEGUIDOR_JLC_DECISOES.md`.
- Unidades em mm. **Referencial do seguidor: origem no centro da ventoinha, +y para a frente** (o mesmo do `.eprj` e do Gerber do EVA-RT).

## O projeto
Dois robôs para uma competição baseada no regulamento do **TRIF 7ª edição** (sucção permitida):
- **Seguidor (prioridade):** clone do **EVA-RT** (EXOTIC TEAM MX, AGPL-3.0), placa feita na JLC pelo EasyEDA Pro. Meta: igualar ou superar o EVA-RT, jogando seguro a partir do projeto original. Divulgar como "baseado no EVA-RT"; não deve parecer um clone direto (contorno B "degraus", estilo HLR).
- **Perseguidor:** o robô atual (ESP32-C3 SuperMini, TB6612, N20, turbina QX 30 mm), que também vai ganhar placa na JLC. Contexto em `docs/perseguidor/` (`CONTEXTO.md`, `HARDWARE.md`, `LAYOUT_PLACA.md`).
- Plano B do seguidor em fenolite (ESP32-C3 + RZ7886 + 8520): `docs/fenolite/SEGUIDOR_FENOLITE_v4.md` / `v5.md` (imagens, tabelas e arquivos no repositório `therickmatos/seguidor-fenolite`).
- Peças do seguidor chegando entre ~10 e 25/11/2026; meta de ter tudo até 20–23/11.

## Seguidor: decisões fixas
- ATmega328P-AU (tirado do Nano/Uno doador, com bootloader) + firmware **EVA-RT 1.2.2 sem mudar o mapa de pinos**.
- 2× DRV8874PWPR (modo PH/EN) no lugar do IFX9201; ITRIP ≈ 3 A (VREF 2,0 V, IPROPI 1,5k).
- Ventoinha: AO3400A (SOT-23) + 1N5819 em paralelo com o motor; PWM no D10.
- Cristal 16 MHz + 2× 22 pF; reset 10k + 100 nF do DTR.
- Gravação: barra macho 1×5 90° 2,54 mm (+5V, GND, RX, TX, DTR) no centro da borda traseira, em cima; conversor CH340G com DTR. ICSP: 6 pads SMD embaixo, posições do EVA-RT.
- Bluetooth opcional: fêmea 1×6 (ordem HC-05) na frente direita (x ≈ 32,5; y 0,7…13,4), divisor 1k/2k.
- Barra de sensores: **V1 de 12 QRE1113 + 74HC4067** (Gerber em `hardware/barra_v1/`), ligada por barra de pinos **2,54 mm** na base (a barra tem passo de 2,0 mm → cabo misto). Distância barra–eixo L = 67–70 mm.
- Sensores de marca QRE1113GR nos braços em (±69,5; 4,5); esquerdo = curva (A5), direito = partida/chegada (A6). **Pinagem do QRE1113GR: 1 anodo, 2 catodo, 3 coletor, 4 emissor** — conferir no footprint.
- Bateria GNB 350 mAh 2S (45 × 20,5 × 12 mm), XT30. 78M05 para 5 V.
- Contorno definitivo: `hardware/contorno/EVA-RT_contorno_B_degraus.dxf` (148,2 × 57,6 mm, braços integrados, furo Ø17).
- STL do EVA-RT usados como estão; a placa respeita as áreas deles (ver `docs/DECISOES_2026-11-04.md`).

## Estado (04/11/2026)
- Esquemático rev 1.0 pronto em KiCad: `hardware/seguidor_base/` (PDF, BOM, `REDES.md`; projeto em `kicad/`). Foi gerado por script (fora do repositório) e fica congelado como referência.
- **Em andamento:** o Erick está passando o esquemático do KiCad para o EasyEDA Pro (para facilitar a confecção na JLC). A partir daí, o EasyEDA vira a fonte; mudanças no esquemático são feitas lá, não no KiCad. Conferir o port rede por rede com `hardware/seguidor_base/REDES.md` (54 redes, 7 pinos sem ligação).
- **Próximo:** layout da placa base no EasyEDA Pro → placa do perseguidor → conferência 3D com os STL → Gerber → pedido JLC (2 placas, cupom de US$ 50).

## Arquivos
| Pasta | Conteúdo |
|---|---|
| `docs/` | decisões, contorno e esquemático do seguidor |
| `hardware/contorno/` | contorno B definitivo (DXF) + figuras de conferência (Gerber do EVA-RT, marcas do TRIF) |
| `hardware/seguidor_base/` | esquemático rev 1.0 (PDF), BOM, `REDES.md` (lista de redes para conferir o EasyEDA); `kicad/` com o projeto KiCad de referência. O projeto EasyEDA Pro (`.eprj`) entra aqui quando estiver pronto |
| `hardware/barra_v1/` | Gerber da barra de sensores V1 |
| `hardware/figuras/` | posição do conector do Bluetooth |
| `referencias/eva-rt/` | cópia do repositório EVA-RT (sem as fotos grandes): `pcb_files/EVA_RT.eprj` abre no EasyEDA Pro (footprints e layout originais) |
| `docs/perseguidor/`, `docs/fenolite/` | perseguidor e plano B em fenolite |

## Cuidados
- Manter o crédito e a licença AGPL-3.0 do EVA-RT em qualquer arquivo derivado.
- Não decidir pelo Erick: base comum × placas separadas já foi decidido (placas separadas), mas nome do robô e terceira placa do pedido estão em aberto.
- A conectividade do KiCad rev 1.0 foi conferida contra a netlist exportada (54 redes). Para o EasyEDA, comparar com `hardware/seguidor_base/REDES.md`.
- Ficaram fora do repositório (estão no zip original): a conversa com o Claude e seus anexos, os scripts que geraram o esquemático e as figuras, a netlist `.net`, figuras de alternativas descartadas (ESP, USB-C) e os renders PNG dos PDFs do EVA-RT.
