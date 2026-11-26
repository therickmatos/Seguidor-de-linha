# CLAUDE.md — contexto para o Claude Code

## Como trabalhar
- Responder em **português**, de forma direta e concisa. O Erick (estudante de eletrônica, IFSP) revisa e corrige o que recebe.
- Antes de afirmar algo sobre o projeto, ler o doc correspondente. O estado da placa está em `hardware/placa_base/README.md`; o histórico do layout, versão a versão, em `estudo_de_caso/08_chassi_asa_de_gaivota/PINOS.md`.
- Unidades em mm. **Referencial do seguidor: origem no centro da ventoinha, +y para a frente** (o mesmo do `.epro` e do Gerber do EVA-RT).
- Antes de mudar algo de que o Erick gostou (trilhas, posições), explicar o que seria alterado. Manter o resto da placa como está e não deixar nada travado no EasyEDA.

## O projeto
Seguidor de linha **RUSH - SATURN** para uma competição baseada no regulamento do **TRIF 7ª edição** (sucção permitida). É baseado no **EVA-RT** (EXOTIC TEAM MX, AGPL-3.0), com placa feita na JLC. Meta: igualar ou superar o EVA-RT, jogando seguro a partir do projeto original. Divulgar como "baseado no EVA-RT"; não deve parecer um clone direto.
- **Fluxo:** esquemático e layout no EasyEDA Pro → Gerber → JLC. O KiCad (`historico/esquematico_kicad_rev1.0/gerador/gen.py`) gerou só a rev 1.0 do esquemático e ficou para trás.
- **Fora deste repositório:** o perseguidor (placa "RUSH - Dreamcast", irmã do Saturn, encomendada junto), em `therickmatos/Perseguidor-de-linha`, e o seguidor em fenolite, em `therickmatos/seguidor-fenolite`.

## Placa encomendada (v12, 15/11/2026)
- Arquivos: `hardware/placa_base/ProPrj_RUSH - SATURN - v12_2026-11-15.epro`, Gerber em `hardware/placa_base/gerber/`, BOM em `hardware/placa_base/BOM_v12.csv`.
- ATmega328P-AU (tirado do Nano/Uno doador, com bootloader) + firmware próprio em `firmware/seguidor/`, **baseado no EVA-RT 1.2.2 e sem mudar o mapa de pinos**. Cristal 16 MHz + 2× 22 pF; reset 10k + 100 nF do DTR.
- 2× DRV8874PWPR (modo PH/EN) no lugar do IFX9201. IPROPI 910 Ω com VREF 2,0 V → ITRIP ≈ 4,9 A. Trilhas de potência para 5,5 A contínuos.
- Ventoinha: AO3400A + 1N5819 em paralelo com o motor; PWM no D10.
- **Sensores de marca QRE1113GR**, dois por lado:
  - S1 = esq. externo (−81,5; 16), A5;
  - S2 = esq. interno (−50,5; 14), D8;
  - S3 = dir. interno (50,5; 14), D9;
  - S4 = dir. externo (81,5; 16), A6.
  - Pinagem do QRE1113GR: 1 anodo, 2 catodo, 3 coletor, 4 emissor.
- **Conectores:**
  - J3, gravação: 5 pads SMD embaixo (+5V, GND, RX, TX, DTR), com conversor CH340G com DTR;
  - J5, ICSP: 6 pads SMD embaixo;
  - J4, Bluetooth: fêmea 1×6 na ordem do HC-05, com divisor 1k/2k (STATE e EN sem ligação);
  - J2, barra V1: 1×8 de 2,54 mm, com cabo misto porque a barra tem passo de 2,0 mm.
- Bateria GNB 350 mAh 2S (45 × 20,5 × 12 mm), XT30. 78M05 para 5 V. C1/C2 eletrolíticos SMD de 220 µF/16 V.
- Contorno asa de gaivota 172,2 × 58,6 mm, furo Ø17 da ventoinha.
- **STL do EVA-RT usados como estão.** Componente alto na face de cima precisa ficar fora de r ≈ 18 mm (hélice com r 17). A conferência é feita por `estudo_de_caso/08_chassi_asa_de_gaivota/codigo/v4_epro/interferencias_stl.py`.
- Distância barra–eixo: L vai do eixo das rodas (y = −22,59) à linha dos sensores centrais da barra. Entre o furo da frente da base (y = 10,75) e o furo da barra V1, L = distância + 43,97 mm. A escolha atual é a barra a 63–65 mm entre furos (L ≈ 107–109); a distância se ajusta na vareta, não na PCB.

## Firmware (17/11/2026)
- `firmware/seguidor/`: escrito e conferido só por simulação (`firmware/testes/sim.cpp`) e compilação com `avr-gcc`; **ainda não rodou no robô**. Ganhos, freio, mapa do mux, sentido das rodas e lado da barra precisam ser conferidos na bancada (lista em `firmware/README.md`).
- Lê as marcas só em A5 (S1) e A6 (S4), como o 1.2.2. S2/S3 (D8/D9) ficam como entrada sem uso: falta escrever a leitura.
- `linha.cpp` e `corrida.cpp` não dependem do Arduino e são os mesmos no robô e no simulador: depois de mexer neles, rodar o simulador (tem que terminar com "tudo certo").
- O simulador usa a geometria do v12 (barra a 107,1 mm, S1/S4 em ±81,5). Com ela, **falha o caso "3 nível 12"** da pista de ensaio (cruzamento a mais e parada fora da área); o resto passa. Ver `firmware/README.md`.
- O ciclo de controle é de 1 ms e o ATmega gasta ~0,6 ms nele: nada de `float` nem divisão de 32 bits dentro de `Corrida::passo()`.
- Divergência em aberto: `firmware/teste_barra/barra.h` usa os canais 4–15 do mux; o Gerber de `hardware/barra_v1` indica 2–13. O firmware segue o teste de bancada (`MAPA_MUX` em `config.h`).

## Mecânica (17/11/2026)
- Base de **1,6 mm** (pedido na JLC) e barra V1 de **1,6 mm** (medida pelo Erick). Guia em `mecânica/README.md`; análise em `mecânica/SUPORTE_BARRA_V1.md`.
- STL gerados por `ferramentas/pecas_3d/gerar_pecas.py`; conferência 3D com o `.epro` do v12 em `ferramentas/pecas_3d/conferir_montagem.py`. A presilha sem braço de baixo e a conferência de parafusos e alturas vieram do repositório do perseguidor.
- Peças adaptadas:
  - presilha de trás sem braço de baixo, com a parede na borda x = ±50 (a do perseguidor);
  - presilha da frente apoiada sobre a raiz da asa;
  - as duas presilhas com assento (furo da vareta fechado embaixo), por serem impressas em PLA/PETG;
  - patim da V1 para barra de 1,6 mm (igual ao do perseguidor);
  - bloco da transversal com rebaixo para a asa;
  - placa de sucção com rebaixo para as cabeças dos pés. O fundo de 0,2 mm isola as vias PWMA_D5/PWMB_D6/GND.
- Barra a 63,14 mm entre furos (L = 107,1), ajustável na vareta. Barra a 3,4 mm da pista; QRE de marca a 0,7 mm; cabeças de parafuso a 0,6–0,8 mm (pneu de ~22 mm, não medido).
- O Erick tem só PLA e PETG (sem filamento com fibra de carbono). PETG nas peças sob aperto ou perto de motor; PLA nos aros. Tabela em `mecânica/README.md`.
- Os STL ficam separados por material em `mecânica/stl/PETG/`, `mecânica/stl/PLA/` e `mecânica/stl/RESINA/`; quem decide a pasta são os conjuntos `PLA` e `RESINA` em `gerar_pecas.py`.
- Todos os STL saem na posição de impressão, sem suporte. `stl/PLA/gabarito_base_teste.stl` é uma base de teste (contorno e furos do v12, asas cortadas) para montar a ventoinha e as caixas antes da placa.
- **Em aberto:** o cubo da hélice tem furo de Ø3,4, e o eixo do 1020 tem 1,2 mm. Hipótese: pinhão 11T prensado no eixo e cravado no cubo. Ver "Primeira impressão" em `mecânica/README.md`.
- Rodas (18/11/2026):
  - pneu StickyMAX 22 mm da RoboCore (Ø22 × 15, furo de Ø12) no `wheel_rim.stl` do EVA-RT;
  - engrenagem de 64 dentes (módulo 0,3) impressa em resina, presa nos 6 pinos do aro (Ø3,09 × 2,0, raio 5,45). São 3 versões em `stl/RESINA/`, de justa a folgada, marcadas com 1, 2 ou 3 furos: imprimir 3 de cada na mesma leva e escolher no teste das caixas. Elas cobrem o deslocamento de perfil desconhecido do pinhão (0 ou +0,33; a caixa tem a distância sem folga para +0,33), o encolhimento do PETG e o engorde da resina. Antes da resina, o Erick confere o pinhão (11 dentes, ~3,8 ou ~4,0 mm no paquímetro);
  - eixo fixo = parafuso M2 × 30, com 2 buchas (`bead.stl`) por roda apertando o anel interno dos rolamentos;
  - distância entre o motor e o eixo na caixa: 11,35 mm (nominal 11,25).
- Varetas: o Erick não tem as de carbono. **Não imprimir:** o esqui é o apoio da frente do robô (~0,5 N por vareta, em balanço de 54–63 mm), e a base fica a 0,6–0,8 mm da pista. Impressa em PETG, a vareta fletiria 3,5–5,5 mm e a base arrastaria; filamento com fibra de carbono não resolve (1,3–2,1 mm). Servem carbono (1 m basta), fibra de vidro maciça (0,17–0,26 mm) ou alumínio (agulha de tricô de alumínio de 3,0 mm, achada em armarinho, para não depender de encomenda); inox e barra roscada M3 servem, mas pesam 14–20 g. Tabela em `mecânica/README.md` ("Ferragens").
- Impressão: duas mesas de PETG (uma de teste curta e o resto; as peças de `stl/PLA/` também saem em PETG) e uma leva de resina com as 9 engrenagens. Os arquivos prontos ficam em `mecânica/mesas/`: 3MF com um objeto por peça, posicionados para uma mesa de 180 × 180 mm, e um STL com as 9 engrenagens. O `gerar_pecas.py` refaz esses arquivos (`MESA_TESTE`, `MESA_RESTO`, `MESA_FUNC_PEQUENAS`, `MESA_FUNC_GRANDES`).
- **Decisão de 26/11/2026:** o conjunto que vai no robô sai todo em **PLA**, numa ida só à impressora (sem reimprimir), com a montagem em casa. A geometria das peças não mudou. Ordem:
  1. `cupom_furos_PLA.stl`: cupom de furos que acerta a compensação de furos do fatiador pelo motor 1020 e pelo rolamento;
  2. `mesa_funcional_1_pequenas_PLA` (19 peças);
  3. `mesa_funcional_2_grandes_PLA` (10 peças).
  
  As 21 peças do robô levam 8 reservas baratas: 2 buchas, 1 presilha de cada tipo, 1 patim de cada lado, 1 placa de sucção e 1 hélice. Resina: `resina_6_engrenagens.stl` (2 de cada versão), porque a versão só se escolhe na montagem; os `resina_2_engrenagens_v*` ficam como impressão mínima. Cuidados de impressão e montagem em PLA (calor nas caixas e na ventoinha, aperto leve com cianoacrilato nas porcas das presilhas, fundo da placa de sucção sobre D5/D6/VREF/GND nos pés de trás) em `mecânica/README.md`, "Tudo em PLA". Os 12 furos de fixação do v12 são NPTH de Ø2,00.
- Nada foi impresso nem testado fisicamente.

## Próximos passos
- Montagem (peças chegando entre ~10 e 25/11/2026). O furo do XT30 tem 2,54 mm e serve para pino de até ~2,3 mm.
- **Teste do sentido dos motores:**
  - se o robô andar para trás, inverter os dois motores;
  - se girar no lugar, inverter um deles;
  - se a ventoinha soprar, inverter a ventoinha.
- Leitura dos QRE internos (D8/D9) no `firmware/seguidor/`. O 1.2.2 lê só A5/A6 e não usa marcas de curva: o sensor esquerdo só veta a parada nos cruzamentos. Os QRE internos podem ver a linha em curva fechada, e o S3 não deve disparar a parada. Ver `estudo_de_caso/07_firmware_e_geometria/README.md`.

## Arquivos
O `README.md` da raiz tem a tabela "Onde encontrar" por tarefa. Manter atualizada quando algo mudar de lugar.
Branch principal: `main`. Os branches antigos e o que cada um tem estão listados em `historico/README.md`.

| Pasta | Conteúdo |
|---|---|
| `hardware/placa_base/` | placa encomendada (v12), Gerber final, BOM, `historico/` com v4 a v10 |
| `hardware/barra_v1/` | Gerber da barra de sensores V1 (1,6 mm) |
| `mecânica/` | mesas prontas para imprimir (`mesas/`), STL avulsos por material (`stl/PETG/`, `stl/PLA/`, `stl/RESINA/`), guia de montagem, análise do suporte da barra e figuras da conferência 3D |
| `estudo_de_caso/` | simulações das marcas do TRIF (`06_estudo_consolidado/`, `07_firmware_e_geometria/`) e chassi asa de gaivota (`08_chassi_asa_de_gaivota/`: `PINOS.md`, lista de capacitores e resistores, scripts de cada versão em `codigo/v4_epro/`, entradas do Erick em `codigo/v4_epro/entradas/`) |
| `firmware/` | `seguidor/` (firmware do robô), `testes/` (simulador do controle com as pistas TRIF 2025/2024), `teste_barra/` (teste de bancada da barra no ESP32-C3) |
| `ferramentas/` | `pecas_3d/` (STL e conferência 3D) e `bom_epro.py` |
| `historico/` | antes do layout: decisões de 02–04/11, contorno B, esquemático KiCad rev 1.0 com o gerador (`esquematico_kicad_rev1.0/gerador/`), figura do BT |
| `referencias/` | regulamento do TRIF 2026 (seguidor) e cópia do repositório EVA-RT (sem as fotos grandes): `eva-rt/pcb_files/EVA_RT.eprj` abre no EasyEDA Pro |

## Formato .epro (para os scripts)
- É um zip de linhas JSON, com coordenadas em mil (× 0,0254 = mm).
- Campos de trava: COMPONENT r[8], LINE r[10], VIA r[12], ATTR r[20].
- Serigrafia STRING: camada 3 = cima, 4 = baixo. Limites da JLC: texto ≥ 1 mm de altura, traço ≥ ~0,15 mm.

## Cuidados
- Manter o crédito e a licença AGPL-3.0 do EVA-RT em qualquer arquivo derivado.
- Não decidir pelo Erick.
- O KiCad 7 do Ubuntu não tem ERC pela linha de comando.
- Ficaram fora do repositório (estão no zip original): a conversa com o Claude e seus anexos, os scripts de figuras e de STL, a netlist `.net`, figuras de alternativas descartadas (ESP, USB-C), os renders PNG dos PDFs do EVA-RT e os docs do perseguidor e da fenolite.
