# CLAUDE.md — contexto para o Claude Code

> **Atualização mais recente — 08/11/2026:** a placa base do RUSH está roteada no EasyEDA:
> `hardware/easyeda/RUSH_PCB_plano_vias_v2.epro` (versão "plano + vias mínimas" corrigida depois do DRC do
> EasyEDA; ainda há 6 vias encostadas em pad SMD, seção 7 do doc). Versões anteriores: `RUSH_PCB_plano_vias.epro`
> e `RUSH_PCB_roteada.epro` (com malha de costura). Resumo, conferência e passo a passo no EasyEDA em
> `docs/ROTEAMENTO_2026-11-08.md`. **Face de baixo no EasyEDA Pro = espelho em y do footprint e depois a
> rotação** (não espelho em x, como as sessões anteriores usavam).
>
> Histórico — 06/11/2026: o Erick decidiu substituir o J3 PTH da prévia por contatos na face inferior,
> com a barra deitada como no EVA-RT; a versão alpha está em `hardware/placa_alpha/`.

## Como trabalhar
- Responder em **português**, de forma direta e concisa. O Erick (estudante de eletrônica, IFSP) revisa e corrige o que recebe.
- Antes de afirmar algo sobre o projeto, ler o doc correspondente em `docs/`. As decisões mais novas estão em `docs/DECISOES_2026-11-05.md`, `docs/DECISOES_2026-11-04.md` e `docs/SEGUIDOR_JLC_DECISOES.md`.
- Unidades em mm. **Referencial do seguidor: origem no centro da ventoinha, +y para a frente** (o mesmo do `.eprj` e do Gerber do EVA-RT).
- **Designadores numerados por bloco desde 07/11** (R1–R3 na alimentação, R4–R9 nos sensores de marca…): tabela antigo → novo em `hardware/DESIGNADORES.md` (fonte `ferramentas/designadores.py`). Docs e figuras anteriores a 07/11 usam a numeração antiga.

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
- Bluetooth (**obrigatório** desde 05/11): fêmea 1×6 (ordem HC-05) na frente direita (x = 30,0 desde 07/11, 2,5 mm à esquerda do EVA-RT para caber as chaves; y 0,7…13,4), divisor 1k/2k no RXD do módulo; R22 = 4,7k entre o TXD do módulo e o RX_D0, sem LED de RX (o LED7/R2 antigo saiu em 07/11) — grava com o módulo encaixado.
- Botões SW1–SW3 (07/11; SW1 = reset, SW2/SW3 = botões 1/2): **Jianfu TVBM17-025CF-R** (C19271064; 6,1 × 3,7 × 2,5 mm, terminais com 8,0 mm de ponta a ponta), com **pads encurtados** (1,2 × 1,2 em ±3,7; 8,6 mm no total) para caber ao lado do J4. SW1 no pé direito; SW2/SW3 entre o J4 e a presilha da vareta (a vareta passa por cima de x ≈ 43–47). Substitui a B3U-1000P.
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
- **07/11 — larguras de potência:** conferência automática no caminho da corrente (`ferramentas/preview/larguras.py`). Corrigidos trechos de 0,4–0,6 mm na ventoinha e nas saídas do motor esquerdo: M3 invertido, D1 embaixo atrás do M3, C8 e Q1 girados, R11 0,65 mm à direita, OUT_A1/A2 e OUT_C pré-roteadas; VBAT até 3,0 mm. Só sobram os pescoços nos pinos do DRV8874 (o maior, VM, 0,4 × 2,3 mm). Regras de largura para o EasyEDA no README da `placa_alpha`.
- **07/11 — projeto RUSH conferido e renumerado:** o `.epro` final do Erick bate com a referência nas 53 redes (C5 cerâmico com os pinos invertidos, sem efeito). Faltam 2 footprints: chaves (ainda o P8.20 de 10,6 mm → `seguidor_alpha:SW_TACT_3x6_SMD_2P`) e X1 (o da LCSC deixa o pad a 0,13 mm do rasgo → `seguidor_alpha:XTAL_TXC_7A_5032_2P`). Designadores renumerados por bloco no `.epro` (`hardware/easyeda/ProPrj_RUSH_-_renumerado.epro`, títulos dos blocos numerados 1–8) e em todo o repositório; saíram LED7/R2 e J8/J9 (65 peças, 213 pads).
- **07/11 — PCB do EasyEDA posicionada:** `hardware/easyeda/ProPrj_RUSH_-_posicionado.epro` (do `pcbv1` do Erick): 65 peças nos lugares da referência, calculadas para os footprints dele (`ferramentas/preview/easyeda_posicionar.py`), contorno (camada Board Outline), 13 furos e os 2 rasgos, origem no centro da ventoinha. Ajustes por causa dos footprints da LCSC: X1 deslocado (−0,6; +0,2) mm e C10 0,05 mm; chaves com o footprint da LCSC (pads de 9,5 mm) cabem (≥ 0,4 mm do J4). Sem folga < 0,2 mm entre pads nem pad a < 0,3 mm da borda. Conferir no EasyEDA a convenção da face de baixo (J3.1 = +5V em x = −5,08 visto de cima).
- **07/11 (noite) — PCB do Erick revisada e ajustada:** `hardware/easyeda/ProPrj_RUSH_-_pcb_ajustado.epro` (do `pcb_2026-11-07` dele, com as centralizações dele mantidas). Correções aprovadas: U2 só desceu para y −23,0 (saiu do disco do rotor); X1/C9/C10/C7 de volta junto dos pinos do ATmega; M3/D1/Q1 na disposição da referência; R10 em y −18,75 (fora do pé da carcaça); SW2/SW3 em x 36,10 (SW3 fora da presilha); velcro = o pad dele duplicado em (±16,685; −28,213), no lugar dos contornos de rasgo. Revisão: `ferramentas/preview/easyeda_revisar.py` (folgas ok, mecânica ok).
- **08/11 — placa roteada:** a partir do `.epro` do Erick com o cobre de outro agente (`hardware/easyeda/RUSH_PCB_nova_com_cobre.epro`: potência ok, mas faltavam PWMA_D5, PWMB_D6 e RESET, e o GND não fechava pelos planos). Potência e cristal do agente mantidos; fanout de GND; sinais e +5V refeitos no FreeRouting (face de baixo mais cara) + roteador de grade; planos de GND (`POUR`) nas duas faces com vias de costura. Resultado em `hardware/easyeda/RUSH_PCB_roteada.epro` (nenhuma peça movida): 0 abertas, 0 folgas, larguras na regra, DRC do KiCad 0 erros de cobre e 0 não roteadas. Ferramentas: `ferramentas/preview/easyeda_cobre.py` (leitor/verificador do `.epro`), `rush_pipeline.py`, `rush_rotear.py`, `rush_gnd.py`, `grade.py`, `easyeda_kicad_drc.py`. Achado: com a convenção certa da face de baixo, J3 está com a ordem dos pinos invertida (J3.1 = +5V em x = +5,08 visto de cima) e J5 (ICSP) e S2 estão girados 180° em relação ao plano; o Erick decide se gira (aí é preciso refazer o roteamento dessa região).
- **08/11 — versão "plano + vias mínimas" (preferida pelo Erick):** `hardware/easyeda/RUSH_PCB_plano_vias.epro` (`rush_pipeline.py plano`): sem nenhuma trilha de GND e com só 24 vias de GND (encostadas no pad quando cabe), MARK_L_A5 refeito para não cortar o plano de baixo entre o U3 e o J1. Mesma conferência (0 abertas, 0 folgas, KiCad 0 erros de cobre e 0 não roteadas, retorno largo nos terminais de corrente). Detalhes na seção 6 do `docs/ROTEAMENTO_2026-11-08.md`.
- **08/11 — teste do Erick no EasyEDA e v2:** o DRC deu 108 "free copper region" (ilhas soltas do plano: ligar remoção de ilhas), 8 "SMD Pad to Via" da mesma rede (o EasyEDA não aceita via encostada em pad SMD) e 2 ligações faltando (U3.7, U4.15/U4.16). `hardware/easyeda/RUSH_PCB_plano_vias_v2.epro` (`rush_pipeline.py corrigir`): pinos de GND dos DRV8874 ligados ao pad térmico por dentro (o CPH_B do U4 passa por dentro, então U4.15/16 têm ponte e via), 10 vias afastadas para ≥ 0,2 mm do pad com toco. Restam 6 vias encostadas (R5.1, R5.2, C7.2, R3.2, U2.21, U2.3), que pedem ajuste local do roteamento (seção 7 do `docs/ROTEAMENTO_2026-11-08.md`).
- **Próximo:** abrir no EasyEDA Pro, reconstruir os planos (folga ≤ 0,3 mm, SMD sólido), DRC, acabamento das trilhas → conferência 3D com os STL → Gerber → pedido JLC (cupom de US$ 50, junto com a placa do perseguidor).

## Arquivos
| Pasta | Conteúdo |
|---|---|
| `docs/` | decisões, contorno e esquemático |
| `hardware/contorno/` | contorno B definitivo (DXF) + figuras de conferência (Gerber do EVA-RT, marcas do TRIF) |
| `hardware/seguidor_base/` | esquemático rev 1.0 e placa alpha (projeto KiCad, PDF, `.kicad_pcb`, `seguidor_alpha.pretty`, DRC), BOM, `REDES.md` (lista de redes para conferir a importação no EasyEDA) |
| `hardware/barra_v1/` | Gerber da barra de sensores V1 |
| `hardware/easyeda/` | projeto do EasyEDA Pro do Erick (RUSH), com a numeração por bloco; `RUSH_PCB_plano_vias_v2.epro` = placa roteada atual (08/11) |
| `hardware/DESIGNADORES.md` | tabela antigo → novo da numeração por bloco (07/11) |
| `hardware/figuras/` | posição do conector do Bluetooth |
| `referencias/eva-rt/` | cópia do repositório EVA-RT (sem as fotos grandes): `pcb_files/EVA_RT.eprj` abre no EasyEDA Pro (footprints e layout originais) |
| `ferramentas/esquematico/` | gerador do esquemático KiCad (fonte), conferência da netlist, BOM e `REDES.md` |
| `ferramentas/preview/` | preview de posicionamento: geometria (DXF + STL), footprints, posicionamento (em andamento), extrator do `.eprj` |
| `hardware/preview/` | figuras do preview (geometria, footprints, marcas do TRIF), prévias 3D e foto do XT30 |

## Cuidados
- Manter o crédito e a licença AGPL-3.0 do EVA-RT em qualquer arquivo derivado.
- Não decidir pelo Erick: base comum × placas separadas já foi decidido (placas separadas); nome do robô: **RUSH** (por enquanto, 07/11); terceira placa do pedido em aberto.
- O KiCad 7 do Ubuntu não tem ERC pela linha de comando; a conectividade é conferida por `ferramentas/esquematico/check.py`.
- Peça na face de baixo do EasyEDA Pro: footprint espelhado em **y** e depois girado (conferido no `EVA_RT.eprj`; `easyeda_cobre.transformar`). Scripts e figuras de antes de 08/11 usavam espelho em x.
- EasyEDA: via não pode encostar em pad SMD, nem da mesma rede (regra "SMD Pad to Via"); o plano não entra entre pinos a 0,65 mm (ligar pinos de GND por trilha).
- Mudança de peça ou de roteamento no `.epro`: conferir com `ferramentas/preview/easyeda_cobre.py arquivo.epro --gnd-planos` (e, se possível, `easyeda_kicad_drc.py`).
- Mudança no esquemático depois da importação no EasyEDA: fazer no `gen.py` (fonte) e repetir no EasyEDA, para os dois não divergirem.
- Ficaram fora do repositório (estão no zip original): a conversa com o Claude e seus anexos, os scripts de figuras e de STL, a netlist `.net` (regenerável), figuras de alternativas descartadas (ESP, USB-C), os renders PNG dos PDFs do EVA-RT e os docs do perseguidor e da fenolite (outros projetos).
