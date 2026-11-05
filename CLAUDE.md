# CLAUDE.md — contexto para o Claude Code

## Como trabalhar
- Responder em **português**, de forma direta e concisa. O Erick (estudante de eletrônica, IFSP) revisa e corrige o que recebe.
- Antes de afirmar algo sobre o projeto, ler o doc correspondente em `docs/`. As decisões mais novas estão em `docs/DECISOES_2026-11-05.md`, `docs/DECISOES_2026-11-04.md` e `docs/SEGUIDOR_JLC_DECISOES.md`.
- Unidades em mm. **Referencial do seguidor: origem no centro da ventoinha, +y para a frente** (o mesmo do `.eprj` e do Gerber do EVA-RT).

## O projeto
Seguidor de linha para uma competição baseada no regulamento do **TRIF 7ª edição** (sucção permitida): clone do **EVA-RT** (EXOTIC TEAM MX, AGPL-3.0), placa feita na JLC. Meta: igualar ou superar o EVA-RT, jogando seguro a partir do projeto original. Divulgar como "baseado no EVA-RT"; não deve parecer um clone direto (contorno B "degraus", estilo HLR).
- **Fluxo:** esquemático em KiCad (fonte) → importado no EasyEDA Pro → layout → Gerber → pedido na JLC.
- **Fora deste repositório:** o perseguidor e o seguidor em fenolite são outros projetos (as bases dos robôs são parecidas). Os docs de decisão citam os dois porque o pedido na JLC é compartilhado.
- Peças do seguidor chegando entre ~10 e 25/11/2026; meta de ter tudo até 20–23/11.

## Seguidor: decisões fixas
- ATmega328P-AU (tirado do Nano/Uno doador, com bootloader) + firmware **EVA-RT 1.2.2 sem mudar o mapa de pinos**.
- 2× DRV8874PWPR (modo PH/EN) no lugar do IFX9201; ITRIP ≈ 3 A (VREF 2,0 V, IPROPI 1,5k).
- Ventoinha: AO3400A (SOT-23) + 1N5819 em paralelo com o motor; PWM no D10.
- Cristal 16 MHz + 2× 22 pF; reset 10k + 100 nF do DTR.
- Gravação: barra macho 1×5 90° 2,54 mm (+5V, GND, RX, TX, DTR) no centro da borda traseira, em cima; conversor CH340G com DTR. ICSP: 6 pads SMD embaixo, posições do EVA-RT.
- Bluetooth (**obrigatório** desde 05/11): fêmea 1×6 (ordem HC-05) na frente direita (x ≈ 32,5; y 0,7…13,4), divisor 1k/2k.
- Botões SW0–SW2: táteis **6 × 6 × 4,5 THT de 2 terminais** (já comprados).
- Barra de sensores: **V1 de 12 QRE1113 + 74HC4067** (Gerber em `hardware/barra_v1/`), ligada por barra de pinos **2,54 mm** na base (a barra tem passo de 2,0 mm → cabo misto). Distância barra–eixo L = 67–70 mm.
- Sensores de marca QRE1113GR nos braços em (±69,5; 4,5); esquerdo = curva (A5), direito = partida/chegada (A6). **Pinagem do QRE1113GR: 1 anodo, 2 catodo, 3 coletor, 4 emissor** — conferir no footprint.
- Bateria GNB 350 mAh 2S (45 × 20,5 × 12 mm, deitada atrás com 45 mm em x). Conector: **XT30 macho de placa** (foto em `hardware/preview/`; lado reto do corpo = +). 78M05 para 5 V.
- Contorno definitivo: `hardware/contorno/EVA-RT_contorno_B_degraus.dxf` (148,2 × 57,6 mm, braços integrados, furo Ø17).
- STL do EVA-RT usados como estão; a placa respeita as áreas deles (ver `docs/DECISOES_2026-11-04.md`).

## Estado (04/11/2026)
- Esquemático rev 1.0 pronto: `hardware/seguidor_base/` (projeto KiCad, PDF, BOM, `REDES.md`).
- **A fonte do esquemático é o KiCad**, gerado por `ferramentas/esquematico/gen.py` (feito com o Claude em outra sessão). Mudança no esquemático → editar o `gen.py` e regerar (passo a passo em `ferramentas/README.md`).
- **Em andamento:** o Erick está importando o esquemático do KiCad no EasyEDA Pro para fazer o layout e encomendar na JLC. Conferir a importação rede por rede com `hardware/seguidor_base/REDES.md` (54 redes, 7 pinos sem ligação).
- **05/11:** preview de posicionamento (JPG) em andamento: geometria e footprints prontos, posicionamento interrompido, JPGs pendentes. Continuar por `docs/HANDOFF_PREVIEW_2026-11-05.md`. Orientação nova: **reaproveitar as trilhas do EVA-RT** o máximo possível.
- **Próximo:** layout da placa base no EasyEDA Pro → conferência 3D com os STL → Gerber → pedido JLC (cupom de US$ 50, junto com a placa do perseguidor).

## Arquivos
| Pasta | Conteúdo |
|---|---|
| `docs/` | decisões, contorno e esquemático |
| `hardware/contorno/` | contorno B definitivo (DXF) + figuras de conferência (Gerber do EVA-RT, marcas do TRIF) |
| `hardware/seguidor_base/` | esquemático rev 1.0 (projeto KiCad, PDF), BOM, `REDES.md` (lista de redes para conferir a importação no EasyEDA) |
| `hardware/barra_v1/` | Gerber da barra de sensores V1 |
| `hardware/figuras/` | posição do conector do Bluetooth |
| `referencias/eva-rt/` | cópia do repositório EVA-RT (sem as fotos grandes): `pcb_files/EVA_RT.eprj` abre no EasyEDA Pro (footprints e layout originais) |
| `ferramentas/esquematico/` | gerador do esquemático KiCad (fonte), conferência da netlist, BOM e `REDES.md` |
| `ferramentas/preview/` | preview de posicionamento: geometria (DXF + STL), footprints, posicionamento (em andamento), extrator do `.eprj` |
| `hardware/preview/` | figuras do preview (geometria, footprints) e foto do XT30 |

## Cuidados
- Manter o crédito e a licença AGPL-3.0 do EVA-RT em qualquer arquivo derivado.
- Não decidir pelo Erick: base comum × placas separadas já foi decidido (placas separadas), mas nome do robô e terceira placa do pedido estão em aberto.
- O KiCad 7 do Ubuntu não tem ERC pela linha de comando; a conectividade é conferida por `ferramentas/esquematico/check.py`.
- Mudança no esquemático depois da importação no EasyEDA: fazer no `gen.py` (fonte) e repetir no EasyEDA, para os dois não divergirem.
- Ficaram fora do repositório (estão no zip original): a conversa com o Claude e seus anexos, os scripts de figuras e de STL, a netlist `.net` (regenerável), figuras de alternativas descartadas (ESP, USB-C), os renders PNG dos PDFs do EVA-RT e os docs do perseguidor e da fenolite (outros projetos).
