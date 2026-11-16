# Mecânica — peças para imprimir e montar

Peças do EVA-RT (© EXOTIC TEAM MX, AGPL-3.0) mais o patim refeito para a barra V1.
Análise e cotas do suporte da barra: [`docs/SUPORTE_BARRA_V1.md`](../docs/SUPORTE_BARRA_V1.md).
Os arquivos de `stl/` são gerados por `ferramentas/pecas_3d/gerar_pecas.py`; os do EVA-RT são cópias sem alteração de `referencias/eva-rt/3d_models/`.

## O que imprimir (`stl/`)
| Arquivo | Qtde | Origem | Função |
|---|---|---|---|
| `patim_v1_direito_pcb1.0.stl` | 1 | **novo** | patim da barra V1, lado direito (+x) |
| `patim_v1_esquerdo_pcb1.0.stl` | 1 | **novo** | patim da barra V1, lado esquerdo |
| `barilla_clamp.stl` | 4 | EVA-RT | presilha da vareta na base |
| `barilla_connection.stl` | 2 | EVA-RT | une a vareta longitudinal à transversal |
| `gearbox.stl` | 1 | EVA-RT | caixa de redução **direita** (pinhão para fora) |
| `gearbox_esquerdo_espelhado.stl` | 1 | EVA-RT espelhado | caixa de redução esquerda (o EVA-RT publica só um lado) |
| `wheel_rim.stl` | 2 | EVA-RT | aro da roda (rolamentos 692ZZ) |
| `impeller_base_1.stl` | 1 | EVA-RT | carcaça da ventoinha (4 pés) |
| `impeller_base_2.stl` | 1 | EVA-RT | parte de cima da carcaça, segura o motor |
| `impeller_fan.stl` | 1 | EVA-RT | hélice |
| `suction_base.stl` | 1 | EVA-RT | placa de sucção, 0,6 mm |
| `battery_holder.stl` | 1–2 | EVA-RT | apoio da bateria na vareta de trás (a foto mostra um) |
| `bead.stl` | ? | EVA-RT | bucha Ø6 / Ø3,15 com furo Ø2,15; ver "Não conferido" |

O `sensor_sledge.stl` do EVA-RT **não entra**: foi feito para a barra VISION.

`stl/se_a_placa_tiver_1.6mm/` só serve se a medida com paquímetro der 1,6 mm:
- V1 com 1,6 mm → imprimir os dois `patim_v1_*_pcb1.6.stl` no lugar dos de 1,0.
- Base com 1,6 mm → imprimir 4× `presilha_vareta_pcb1.6.stl` no lugar do `barilla_clamp`.

## Material e impressão
Recomendação minha; o EVA-RT não informa material.
- **PETG** nas peças com braço fino que trabalha sob aperto ou que encostam em motor: patins, presilhas, caixas de redução, `impeller_base_1/2`. O PLA amolece perto de 55–60 °C e racha em braço de 1 mm apertado por parafuso.
- **Hélice:** PETG ou ABS/ASA, 100% de preenchimento, camada de 0,12–0,16 mm. Conferir se gira sem bater antes de dar potência; se vibrar, imprimir de novo.
- **PLA serve** em aro, bloco da transversal, apoio da bateria, bucha e placa de sucção. O aro precisa do alojamento do rolamento preciso (Ø6,19 × 3,0), e o PLA acerta melhor a medida.
- Bico 0,4 mm, camada de 0,12–0,16 mm, 3 perímetros ou mais, 100% de preenchimento (as peças pesam de 0,05 a 2,7 g).
- Patim, presilha e bloco já estão na posição de impressão (furo da vareta na vertical), sem suporte.
- Placa de sucção: deitada, 3 camadas de 0,2 mm.
- Furos Ø2,0 e canal de 3,0 mm da vareta saem justos de propósito, como no original. Se não entrar, broca de 2 mm e de 3 mm, à mão.
- Imprimir primeiro **um** patim e **uma** presilha e testar na placa antes do resto.
- O fundo do esqui desgasta na pista: imprimir um par de reserva.

## Ferragens
| Item | Qtde | Onde |
|---|---|---|
| Vareta de carbono Ø3 mm × 94 mm | 3 | 2 longitudinais + 1 transversal (o EVA-RT usa tubo) |
| Vareta de carbono Ø3 mm × ~80 mm | 1 | traseira, entre as caixas de redução (comprimento estimado, medir na montagem) |
| Parafuso M2 × 6 + porca M2 | 4 | presilhas (cabeça por baixo, porca em cima) |
| Parafuso M2 × 8 + porca M2 | 2 | patins (cabeça por baixo, porca em cima) |
| Parafuso M2 × 6 + porca M2 | 4 | caixas de redução (pé de 2,5 mm + placa de 1,0 mm) |
| Parafuso M2 × 6, rosca direto no plástico | 4 | por baixo: placa de sucção → base → pés da carcaça (furo Ø1,85, 5 mm de fundo) |
| Rolamento 692ZZ (2 × 6 × 3) | 4 | dois por aro |

Total: 12× M2 × 6, 2× M2 × 8, 10 porcas M2. Um kit M2 de 4 a 10 mm cobre as variações.
Cabeça cilíndrica ou abaulada de até Ø3,8 mm. Nos patins a cabeça fica a ~1,3 mm da pista (0,7 mm com barra de 1,6 mm): cortar ou limar se o parafuso sobrar por baixo.

## Ordem de montagem do suporte da barra
1. Soldar tudo na base e na barra antes. A J2 tem de ficar reta: a vareta transversal passa a 0,23 mm dela.
2. Passar cada vareta longitudinal pelo bloco (`barilla_connection`) e pelas duas presilhas. Encaixar as presilhas na borda da base em x = ±50, sobre os furos (±43,75; −1,75) e (±43,75; 10,75), e prender com M2 × 6.
3. Encaixar a vareta transversal nos furos cegos dos dois blocos. Ela fica deitada sobre a base, com o eixo em y ≈ 19,75, logo atrás da J2.
4. Montar a carcaça da ventoinha com **os dois pés de orelha para a frente**: as orelhas prendem a transversal.
5. Encaixar os patins nas pontas da barra (esqui para fora, ponta curva para a frente), M2 × 8 sem apertar, e passar as varetas pelos canais.
6. Deslizar a barra até **63,14 mm** entre o furo da frente da base e o furo da barra, ou 57,89 mm entre a face da frente da presilha dianteira e a face de trás do patim. Conferir os dois lados iguais e apertar.
7. Com a distância aprovada na pista, uma gota de cola (cianoacrilato) em cada patim e cada presilha.

Resultado esperado: varetas paralelas em x = ±48,45, barra a 4,0 mm da pista, L = 107,1 mm.

## Cuidados
- **Pedir a base com 1,0 mm.** O `.epro` está com o empilhamento padrão de 1,6 mm e o `barilla_clamp` tem rasgo de 1,0 mm.
- Carbono conduz: não deixar ponta de vareta encostar em pad ou terminal. Sob as varetas não há via nem pad exposto.
- A vareta fica nivelada com pneu de Ø ≈ 22 mm. Com pneu diferente a barra inclina um pouco (1 mm de diferença no raio ≈ 0,9°).

## Não conferido
- `bead.stl`: pelas medidas parece uma bucha do eixo Ø2 junto ao rolamento 692ZZ, não um patim. Não achei nas fotos onde vai nem quantas são.
- Eixo das rodas (o furo na caixa de redução é Ø2,0; a foto mostra porca do lado de dentro), engrenagem de 64 dentes e pneu.
- Encaixe dos motores 1020 nas caixas de redução e na carcaça (furos Ø10,18).
- Comprimento da vareta traseira e posição do apoio da bateria com a GNB 350 mAh.
