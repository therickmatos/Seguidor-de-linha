# Barra de sensores V1

Gerber da barra V1 (12× QRE1113 + 74HC4067). O perseguidor RUSH - Dreamcast usa a mesma barra.

- Furos de fixação de Ø2,05 em x = ±44,626 mm e borda lateral em x = ±48,25 mm. As duas medidas são lidas do Gerber por `ferramentas/pecas_3d/conferir_montagem.py`.
- Sensores a cada 7,8 mm.
- Espessura de **1,6 mm**, medida pelo Erick (o Gerber não informa). É ela que define o patim (`mecânica/stl/patim_v1_*_barra1.6.stl`).
- Ligação à base pela J2 (1×8, 2,54 mm). A barra tem passo de 2,0 mm, então o cabo é misto.
