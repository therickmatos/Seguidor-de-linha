# CLAUDE.md — contexto para o Claude Code

> **Atualização mais recente — 06/11/2026:** leia primeiro
> `docs/HANDOFF_2026-11-06.md`. O Erick decidiu substituir o J3 PTH da
> prévia por contatos na face inferior, com a barra deitada como no EVA-RT,
> para poder recuar o ATmega e reorganizar a placa. Isso prevalece sobre
> instruções anteriores de J3 PTH em cima e de avançar o ATmega. Já implementado:
> a versão alpha (100% ligada, 0 violações) está em `hardware/placa_alpha/`.

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
- Cristal 16 MHz + 2× 22 pF; reset 10k + 100 nF do DTR. Cristal (07/11): **TXC 7A-16.000MAAJ-T** (5032 de 2 pads, CL 18 pF, C2450102), em diagonal junto dos pinos 7/8 do ATmega.
- Gravação: barra macho 1×5 90° 2,54 mm (+5V, GND, RX, TX, DTR) no centro da borda traseira, em cima; conversor CH340G com DTR. ICSP: 6 pads SMD embaixo, posições do EVA-RT.
- Bluetooth (**obrigatório** desde 05/11): fêmea 1×6 (ordem HC-05) na frente direita (x = 30,0 desde 07/11, 2,5 mm à esquerda do EVA-RT para caber as chaves; y 0,7…13,4), divisor 1k/2k no RXD do módulo; R18 = 4,7k entre o TXD do módulo e o RX_D0, com LED7/R2 não montados — grava com o módulo encaixado (06/11).
- Botões SW0–SW2 (07/11): **Jianfu TVBM17-025CF-R** (C19271064; 6,1 × 3,7 × 2,5 mm, terminais com 8,0 mm de ponta a ponta), com **pads encurtados** (1,2 × 1,2 em ±3,7; 8,6 mm no total) para caber ao lado do J4. SW0 no pé direito; SW1/SW2 entre o J4 e a presilha da vareta (a vareta passa por cima de x ≈ 43–47). Substitui a B3U-1000P.
- Barra de sensores: **V1 de 12 QRE1113 + 74HC4067** (Gerber em `hardware/barra_v1/`), ligada por barra de pinos **2,54 mm** na base (a barra tem passo de 2,0 mm → cabo misto). Distância barra–eixo L = 67–70 mm.
- Sensores de marca QRE1113GR nos braços em (±69,5; 4,5); esquerdo = curva (A5), direito = partida/chegada (A6). **Pinagem do QRE1113GR: 1 anodo, 2 catodo, 3 coletor, 4 emissor** — conferir no footprint.
- Bateria GNB 350 mAh 2S (45 × 20,5 × 12 mm, deitada atrás com 45 mm em x). Conector: **XT30U-M (C99101, macho de cabo, copos soldados nos furos), em pé por dentro do suporte esquerdo** (foto em `hardware/preview/`; lado reto do corpo = +). 78M05 para 5 V.
- Contorno: base `hardware/contorno/EVA-RT_contorno_B_degraus.dxf` (148,2 mm de largura, braços integrados, furo Ø17), com as mudanças de 07/11 feitas em `ferramentas/preview/layout_placa.py`: traseira reta em y −33 e **braços com 6,1 mm de altura** (y 1,45–7,55; raiz com R1; as asas do EVA-RT têm 5 mm). Contorno atual: `hardware/placa_alpha/contorno_alpha.dxf`.
- STL do EVA-RT usados como estão; a placa respeita as áreas deles (ver `docs/DECISOES_2026-11-04.md`).

## Estado (04/11/2026)
- Esquemático rev 1.0 pronto: `hardware/seguidor_base/` (projeto KiCad, PDF, BOM, `REDES.md`).
- **A fonte do esquemático é o KiCad**, gerado por `ferramentas/esquematico/gen.py` (feito com o Claude em outra sessão). Mudança no esquemático → editar o `gen.py` e regerar (passo a passo em `ferramentas/README.md`).
- **Em andamento:** o Erick está importando o esquemático do KiCad no EasyEDA Pro para fazer o layout e encomendar na JLC. Conferir a importação rede por rede com `hardware/seguidor_base/REDES.md` (54 redes, 7 pinos sem ligação).
- **05/11:** prévia de posicionamento e trilhas em `hardware/preview/`, baseada no EVA-RT. Roteamento ainda parcial, com 34 ligações abertas e conflito de J3 com o rasgo original; as propostas e verificações estão no `RELATORIO.md` dessa pasta e no `docs/HANDOFF_PREVIEW_2026-11-05.md`.
- **06/11 — prévia v2 com 100% das ligações:** `hardware/preview/placa_v2.jpg`, `RELATORIO_v2.md` e `posicoes_v2.csv` (substituem `placa_completa.jpg`/`RELATORIO.md`). J3 = 5 pads SMD embaixo (barra 2,54 deitada, como o EVA-RT), U1 em (0; −23) −45°, passivos espalhados por função, plano de GND nas duas faces, 0 violações de folga no verificador. Scripts: `ferramentas/preview/placa_v2.py`, `rotear_v2.py` (FreeRouting 1.9.0 + cobre fixo + finalizador), `figura_v2.py`. Pendente no `gen.py`: texto do J3 (agora SMD embaixo).
- **06/11 — VERSÃO ALPHA (atual):** pacote em `hardware/placa_alpha/` (README com o passo a passo no EasyEDA, imagens, CSV de posições, DXF do contorno e DXF-guia). J1 (XT30U-M, C99101) **em pé por dentro do suporte esquerdo, em (−27,0; −27,8)**, a 6,4 mm do motor; **traseira reta em y −33** (pés do EVA-RT estendidos de |x| 24 a 40, chanfro até o centro em y −30), desde 07/11. 54 redes ligadas, 0 violações; R18 = 4,7k com LED7/R2 não montados (grava com o HC-05 encaixado). Esquemático regerado com KiCad 7.0.11 (J1, J3 e Bluetooth atualizados na BOM). Motores: eixo em y −11,26 (camada Document do EVA-RT), não o −19,03 do `geometria.py`. Prévia 3D da versão alpha (com trilhas) em `hardware/preview/placa_3d.html`. **Placa KiCad** da versão alpha (ligada ao esquemático, DRC do KiCad sem erros) em `hardware/seguidor_base/seguidor_base.kicad_pcb`; gerada por `ferramentas/preview/kicad_exportar.py` + `kicad_montar.py` (rodar de novo depois de regerar o esquemático).
- **06/11 (noite):** o Erick aprovou a traseira do EVA-RT com o XT30 em pé; aplicada na alpha, com o roteamento refeito (registro da proposta em `hardware/preview/traseira_eva_xt30.jpg`). Simulação das marcas do TRIF refeita (`hardware/preview/marcas_trif_sim.jpg`, `marcas_sim.py`): nada muda nos QRE. Zip de entrega (KiCad + pacote EasyEDA + 3D): `hardware/placa_base_alpha.zip` (`ferramentas/empacotar.py`).
- **07/11:** traseira reta em y −33 (XT30 recuado, 6,4 mm do motor), chaves 3 × 6 TC-3610 (C2845294) em SW0–SW2, J4 em x = 30,0 e pads da ventoinha (M3) girados atrás dele; braços com 5,0 mm de altura (eram 7,4); roteamento refeito (0 abertas, 0 violações) e DRC do KiCad sem erros. Ambiente de nuvem "Seguidor-de-linha" com acesso à LCSC/JLC e venv + FreeRouting no script de setup (`/opt/seguidor-venv`, `$FREEROUTING_JAR`).
- **07/11 (tarde):** o Erick refez o esquemático no EasyEDA Pro (projeto "RUSH") e vai **comprar e soldar tudo à mão** (sem PCBA da JLC). Revisão da netlist: 52 de 54 redes iguais à referência; faltam os rótulos MARK_L_A5 (S0.4/R30.1) e MARK_R_A6 (S1.4/R31.1). Trocar o footprint das chaves para o da TC-3601L (C2845294; o de 8,2 mm não cabe ao lado do J4) e o cristal HC-49US por um SMD baixo (o Erick sugeriu o Hosonic HCX-8FA, 8,0 × 4,5 × 1,6 mm, 2 terminais; falta o datasheet com o padrão de pads).
- **07/11 (noite):** peças definidas pelo Erick: cristal TXC 7A (5032), chave TVBM17-025CF-R, C5 47 µF 1210; braços com 6,1 mm. Kit para o EasyEDA em `hardware/placa_alpha/` (`contorno_furos_easyeda.dxf`, `furos.csv`, `posicoes_easyeda.csv` com dois pinos por peça, regras de largura no README), gerado por `ferramentas/preview/kit_easyeda.py`. O Erick vai posicionar pelo CSV e usar o autorouter do EasyEDA nos sinais (potência à mão).
- **Próximo:** layout da placa base no EasyEDA Pro → conferência 3D com os STL → Gerber → pedido JLC (cupom de US$ 50, junto com a placa do perseguidor).

## Arquivos
| Pasta | Conteúdo |
|---|---|
| `docs/` | decisões, contorno e esquemático |
| `hardware/contorno/` | contorno B definitivo (DXF) + figuras de conferência (Gerber do EVA-RT, marcas do TRIF) |
| `hardware/seguidor_base/` | esquemático rev 1.0 e placa alpha (projeto KiCad, PDF, `.kicad_pcb`, `seguidor_alpha.pretty`, DRC), BOM, `REDES.md` (lista de redes para conferir a importação no EasyEDA) |
| `hardware/barra_v1/` | Gerber da barra de sensores V1 |
| `hardware/figuras/` | posição do conector do Bluetooth |
| `referencias/eva-rt/` | cópia do repositório EVA-RT (sem as fotos grandes): `pcb_files/EVA_RT.eprj` abre no EasyEDA Pro (footprints e layout originais) |
| `ferramentas/esquematico/` | gerador do esquemático KiCad (fonte), conferência da netlist, BOM e `REDES.md` |
| `ferramentas/preview/` | preview de posicionamento: geometria (DXF + STL), footprints, posicionamento (em andamento), extrator do `.eprj` |
| `hardware/preview/` | figuras do preview (geometria, footprints, marcas do TRIF), prévias 3D e foto do XT30 |

## Cuidados
- Manter o crédito e a licença AGPL-3.0 do EVA-RT em qualquer arquivo derivado.
- Não decidir pelo Erick: base comum × placas separadas já foi decidido (placas separadas); nome do robô: **RUSH** (por enquanto, 07/11); terceira placa do pedido em aberto.
- O KiCad 7 do Ubuntu não tem ERC pela linha de comando; a conectividade é conferida por `ferramentas/esquematico/check.py`.
- Mudança no esquemático depois da importação no EasyEDA: fazer no `gen.py` (fonte) e repetir no EasyEDA, para os dois não divergirem.
- Ficaram fora do repositório (estão no zip original): a conversa com o Claude e seus anexos, os scripts de figuras e de STL, a netlist `.net` (regenerável), figuras de alternativas descartadas (ESP, USB-C), os renders PNG dos PDFs do EVA-RT e os docs do perseguidor e da fenolite (outros projetos).
