# v4 (asa de gaivota) a partir do projeto EasyEDA Pro da v3

`build.py` lê `ProPrj_RUSH - SATURN - v3_2026-11-09.epro` (raiz do repositório) e grava
`ProPrj_RUSH - SATURN - v4_asa_gaivota_2026-11-11.epro`. Baseado no EVA-RT, © EXOTIC TEAM MX, AGPL-3.0.

O que o script faz:

1. Troca o contorno (camada 11) pelo da asa de gaivota (`../contorno.py`, 172,2 × 58,6 mm).
2. Leva os 5 componentes de cada aba antiga (QRE, 220, 47k, 1k, LED) e as trilhas internas da aba para o QRE externo (±81,5; 16), com deslocamento de (±12; +11,5) mm.
3. Apaga as 8 trilhas que iam do corpo à aba antiga e traça as novas na camada de cima: LED, +5V (0,5 mm) e sinal de marca, subindo a 45° pela aba.
4. Acrescenta os QRE internos E1 (S3) e D1 (S4) em (±50,5; 14), girados 45° para os pads caberem na aba. Cada um leva 220 Ω, 47 kΩ e 10 nF **DNP** (`PINOS.md`), com roteamento local na camada de baixo e vias para +5V e GND.
5. Cria as redes `MARK_L2_D8` (ATmega pino 12) e `MARK_R2_D9` (pino 13), `QRE_E1_A` e `QRE_D1_A`, no esquemático (bloco copiado dos sensores atuais) e na PCB.
6. Remove o cobre despejado (`POURED`): ele é refeito no EasyEDA.

`check.py` é uma checagem de folgas aproximada: 0,2 mm entre redes, 0,3 mm até a borda e até furos não metalizados. Nos objetos novos ou movidos, ela não acusa nenhum problema. Não substitui o DRC do EasyEDA.

Falta fazer no EasyEDA: ver a seção "Ao abrir" na resposta do 11/11 ou em `../../PINOS.md`.
