# Prévia da placa base — resultado da sessão de 05/11/2026

**Resultado parcial:** 37 ligações de 25 redes continuam abertas, desenhadas em amarelo. Não são consideradas impossíveis: não encontrei um caminho que satisfizesse as regras da busca. A placa ainda não está integralmente roteada. A lista exata de ilhas e coordenadas está em `pendencias_roteamento.csv`.

## Mudanças em relação ao EVA-RT

- U1 permaneceu em (0; −23), −45°. SW0/SW1/SW2 são B3U de 3,0 × 2,5 mm nas posições e rotações originais. SW0 usa o mesmo desenho de pads, com a correspondência símbolo/footprint invertida para manter RESET e GND nos lados originais.
- U2/U3 substituem os IFX, nos mesmos centros; os desacoplamentos foram rearranjados ao redor dos drivers para não obstruir as saídas. As distâncias pad a pad mais próximas são aproximadamente 2,4–2,7 mm centro a centro (1,4–1,6 mm entre bordas) para C6/C7/C13–C16.
- Q1 está no centro e rotação originais; D1 está embaixo, próximo à ventoinha. J4 fica em x = 32,5 mm, com R16/R17/R18 montados embaixo. Os dois conjuntos das asas foram transladados para os braços sem trocar suas faces e rotações. J5 permanece embaixo nos pads ICSP originais. J8/J9 são DNP.
- O cobre deriva de 613 LINE, 89 VIA e 2 POLY de cobre do `.eprj`. Cada fragmento e via, rede e classificação estão em `ferramentas/preview/trilhas_classificadas.json`; a proposta com cobre novo está em `trilhas_roteadas.json`. A imagem de mudanças distingue mantida, ajustada, removida e nova. O GND usa trilhas e vias como no original, sem plano presumido.

## Propostas que dependem de você

1. **J3:** em (9; −28,75), rot 0°, mantém U1 no lugar, mas o pad 1 colide com o rasgo original direito. A proposta tracejada move esse rasgo 2,2 mm para fora e exige alterar também um pequeno trecho do contorno. **Não foi aplicada** à geometria aprovada. Alternativas: levar J3 para outra região, mantendo furos/contorno e verificando motor, bateria e acesso; ou mudar posição/rotação do U1, o que contraria a regra atual de mantê-lo no EVA-RT e exige refazer trilhas. A ideia de aproximar U1 da frente depende ainda da altura real do rotor.
2. **J1 XT30:** proposta em (−54; 4,5), rot 0°, no braço esquerdo, fora do apoio do gearbox; o lado reto e o pad 1 são o **+**. A região do VIN original não comportou o corpo estimado sem interferir no apoio. Conferir alcance do cabo e interferência com sensor/vareta e confirmar o código da peça: a foto não identifica com certeza o modelo. O desenho estimado usa o vertical AMASS XT30UPB-M como referência ([catálogo AMASS](https://www.china-amass.com/public/upload/20260207/7fa24f5a6f35ec66c7a115c07a34ab06.pdf)). Outra opção é buscar posição próxima ao VIN mediante montagem/recorte diferente.
3. **X1:** proposta de cristal baixo 3225 em (−7,9; −25,3), rot 180°, sob a bateria. Se a peça disponível for HC-49/S, escolher outro local fora da área da bateria e refazer as ligações curtas do cristal. Confirmar o modelo efetivo e o footprint.

## Ligações abertas

`GND` (5); `VBAT` (4); `VBAT_A7` (2); `RX_D0` (2); `TX_D1` (2); `VREF` (2); `DRV_SLEEP` (2); `+5V` (1); `XTAL1` (1); `VCP_A` (1); `CPH_A` (1); `CPL_A` (1); `VCP_B` (1); `BT_RXD` (1); `BT_TXD` (1); `LEDC_D13` (1); `OUT_B1` (1); `LEDA_D2` (1); `LEDB_D7` (1); `PWMC_D10` (1); `IPROPI_A` (1); `IPROPI_B` (1); `MARK_R_A6` (1); `DIRB_D4` (1); `PWMB_D6` (1).

No CSV, cada linha liga duas ilhas de cobre da mesma rede. Os pontos são os extremos do ratsnest em mm; os grupos listam os **pads físicos do footprint**, não necessariamente a numeração do símbolo (por exemplo, X1.3 físico corresponde ao segundo terminal do cristal no esquemático). Linhas que ainda passam pela região de J3 pressupõem resolver o conflito do rasgo.

## Conferência e limites

- A verificação geométrica independente examinou 1286 objetos e não apontou folgas abaixo de 0,19 mm entre redes diferentes no modelo. Encontrou **1 conflito de borda/furo: J3.1 × rasgo original**. Limite de 0,19 mm usado como tolerância para o alvo aproximado de 0,20 mm.
- Os pads e corpos da face superior não invadem as áreas retangulares de apoio dos gearboxes informadas. C1/C2 mantêm os furos THT originais sobre a área da placa de sucção, como no EVA-RT. O encaixe 3D completo, o módulo Bluetooth e a altura real do rotor não foram comprovados.
- Algumas saídas de potência foram alargadas para 0,4–1,0 mm onde havia espaço, mas alguns escapes de alimentação permanecem finos. Dimensionar corrente/temperatura e conferir todas as ligações, pads e DRC no EasyEDA. O código e as figuras são um guia, não Gerber nem arquivo de fabricação; DRV e QRE continuam sujeitos à conferência dos footprints reais.

Baseado no EVA-RT © EXOTIC TEAM MX — AGPL-3.0.
