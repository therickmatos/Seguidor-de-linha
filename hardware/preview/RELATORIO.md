> **Histórico.** A prévia atual é `RELATORIO_v2.md` / `placa_v2.jpg` (06/11, 100% das ligações, J3 SMD embaixo).

# Prévia da placa base — atualização de 06/11/2026

**Resultado:** 21 ligações em 17 redes ainda abertas, desenhadas em amarelo. Elas não foram demonstradas impossíveis; os grupos e coordenadas estão em `pendencias_roteamento.csv`.

Nesta entrega, `placa_completa.jpg` é a imagem atual das duas faces. As imagens
isoladas `placa_top.jpg`, `placa_bottom.jpg` e `mudancas_vs_eva-rt.jpg` são da
sessão de 05/11 e não representam este novo roteamento.

## Alterações

- Foi removido o cobre antigo do EVA-RT e refeito o roteamento nas duas faces com FreeRouting 2.5.0, a partir das redes de `hardware/seguidor_base/REDES.md`. Os componentes existentes permaneceram o mais próximo possível do EVA-RT. Bluetooth, botões e conectores continuam montados nas faces indicadas nas imagens.
- **J1 XT30** está em (−35,5; −31,7) mm, no canto inferior esquerdo, com o lado reto e o pad 1 no **positivo**. O corpo 10,214 × 5,2 mm e o passo 5 mm vêm do desenho enviado; os diâmetros dos pads (aprox. 3,9 mm) e dos furos (aprox. 2,5 mm) foram estimados pela proporção da imagem e precisam ser medidos na peça. A projeção do corpo tem folga aproximada de 0,6 mm até a área de apoio do gearbox, sem considerar tolerâncias de montagem.
- O contorno foi prolongado até y = −35 mm nos dois cantos traseiros, simetricamente, com largura máxima local de x = ±41 mm. O restante do contorno B, os furos e os rasgos originais foram preservados. `contorno_b_xt30.dxf` contém o contorno proposto e o furo central da ventoinha; os demais furos permanecem os originais.
- **J2 e J3** estão centralizados em x = 0. J3 é uma barra de 5 pinos a 90° em y = −28,8 mm, com corpo voltado para trás; não colide com os rasgos originais. O ATmega U1 foi deslocado de (0; −23) para (0; −22,25), mantendo −45°; C9 foi rearranjado para liberar a barra. O corpo de J3 avança além da borda traseira.
- **Sensores laterais:** S0 e S1 permanecem na face inferior, nos braços, e seus pads estão horizontais. Posições e medidas dos pads (1,66 × 0,80 mm) e pinagem foram confrontadas com o Gerber e as redes do EVA-RT; a pinagem também confere com o datasheet da onsemi. Os sensores devem ser conferidos contra as peças compradas.

## Propostas e conferências

- **Cristal X1:** continua a proposta do encapsulamento baixo 3225; caso a peça seja HC-49/S, escolher outra posição e revisar o roteamento curto.
- **J1:** conferir furos, tamanho real do corpo e acesso do cabo na montagem. O desenho da posição é uma proposta; a polaridade segue a orientação informada pelo usuário.
- **J3:** o conector a 90° fica centralizado sob a bateria. Conferir altura e acesso físico; alternativas são um conector de menor altura ou mudar seu tipo e refazer o encaixe. A montagem 3D da bateria, dos motores e do rotor não foi comprovada.
- As classes iniciais do roteador usam 0,8 mm para bateria/saídas dos motores, 0,5 mm para GND, 0,4 mm para +5 V e 0,3 mm para sinais, com redução automática onde necessária. Larguras **efetivamente desenhadas**: `VBAT`: mínimo 0.600 mm; `OUT_A1`: mínimo 0.400 mm; 3.0 mm abaixo de 0,5 mm; `OUT_B1`: mínimo 0.400 mm; 4.1 mm abaixo de 0,5 mm; `OUT_C`: mínimo 0.800 mm; `GND`: mínimo 0.250 mm; 45.4 mm abaixo de 0,5 mm; `+5V`: mínimo 0.200 mm; 315.3 mm abaixo de 0,5 mm. Elas não substituem o dimensionamento por corrente e espessura de cobre.

## Ligações ainda abertas

`VREF` (3); `VBAT` (2); `DRV_SLEEP` (2); `GND` (1); `+5V` (1); `XTAL2` (1); `DTR` (1); `RESET` (1); `VBAT_A7` (1); `B2_D12` (1); `OUT_A2` (1); `OUT_B2` (1); `PWMC_D10` (1); `IPROPI_A` (1); `IPROPI_B` (1); `DIRA_D3` (1); `PWMA_D5` (1)

## Verificação e arquivos

- A checagem geométrica independente inspecionou 701 objetos, alvo de folga aproximada de 0,2 mm com tolerância de 0,01 mm: nenhuma violação no modelo. Conferir também os contatos, o fabricante dos footprints e o DRC no EasyEDA.
- Nas imagens, vermelho é cobre superior, azul é cobre inferior, amarelo é ligação aberta e o ponto branco marca o pino 1. Círculos amarelos indicam pendências curtas ou entre ilhas sobrepostas em faces diferentes. A face inferior é vista através da placa, sem espelhar. Grade de 5 mm; +y aponta para a frente.
- `seguidor_potencia.dsn` e `seguidor_potencia.ses` registram o intercâmbio usado na geração. São um modelo de prévia com pads individuais, não um projeto nativo EasyEDA para fabricação nem uma sessão diretamente importável no projeto original.

Baseado no EVA-RT © EXOTIC TEAM MX — AGPL-3.0.
