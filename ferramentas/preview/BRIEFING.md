# Briefing comum — preview de posicionamento da placa base do seguidor (clone do EVA-RT)

Projeto: seguidor de linha (robotracer) com ventoinha de succao, clone do EVA-RT (EXOTIC TEAM MX, AGPL-3.0).
Repositorio: raiz do clone (caminhos abaixo relativos a ela). Fora de ferramentas/preview/, tratar como so leitura.
Pasta de trabalho: ferramentas/preview/  (chamada abaixo de $P)
Python 3 com matplotlib, ezdxf, numpy, pillow (ver ferramentas/preview/requirements.txt; usar um venv)
Fonte para figuras: Inter (/usr/share/fonts/opentype/inter/) ou DejaVu Sans. Textos das figuras em PORTUGUES.

## Referencial (OBRIGATORIO em tudo)
- Unidades em mm. Origem (0,0) = centro da ventoinha (centro do furo de Ø17). +x = direita do robo, +y = FRENTE do robo.
- E o mesmo referencial do projeto EasyEDA do EVA-RT (.eprj, em mil: 1 mil = 0,0254 mm) e do Gerber oficial.
- Vista de cima = olhando a face TOP. A face BOTTOM deve ser desenhada "vista atraves da placa" (mesmas coordenadas x,y, SEM espelhar), que e como o EasyEDA mostra a camada de baixo.

## Arquivos de entrada
- Contorno definitivo: hardware/contorno/EVA-RT_contorno_B_degraus.dxf (1 LWPOLYLINE fechada com bulges = arcos, + 1 CIRCLE = furo Ø17). Ja esta no referencial acima. 148,2 x 57,6 mm: x de -74,1 a +74,1; y de -32 a 25,6. Bracos laterais finos ate x = ±74,1.
- Figura de conferencia: hardware/contorno/contorno_B_sobre_gerber_EVA-RT.jpg (contorno B sobre o cobre do EVA-RT).
- Posicoes ORIGINAIS dos componentes do EVA-RT (extraidas do .eprj, ja em mm no referencial): $P/eva_rt_componentes.csv (ref;footprint;lado;x_mm;y_mm;rot;valor). rot em graus (EasyEDA, anti-horario).
- Pads livres do EVA-RT (motores, ventoinha, ICSP, asas, rasgos do velcro): $P/eva_rt_pads_livres.csv
- Projeto EasyEDA original decodificado (texto, uma linha JSON por primitiva; coordenadas em mil): $P/eprj/eva_rt_pcb_b73a4a.txt (gerado por `python3 extrair_eprj.py`, fora do git)  (blocos ["DOCTYPE","FOOTPRINT"] com os footprints embutidos + bloco ["DOCTYPE","PCB"] com a placa). Formato PAD de footprint: ["PAD", id, ?, net, layer, num, x, y, rot, [furo] , [forma, w, h, ...], ...] (em mil, relativo ao centro do footprint).
- Gerber do EVA-RT: referencias/eva-rt/pcb_files/Gerber_EVA_RT_PCB_2025-02-02.zip
- STL do EVA-RT: referencias/eva-rt/3d_models/*.stl
- Lista de material (BOM, separador ;): hardware/seguidor_base/BOM_seguidor_base.csv
- Redes (todas as ligacoes REF.pino): hardware/seguidor_base/REDES.md
- Decisoes: docs/SEGUIDOR_JLC_DECISOES.md, docs/DECISOES_2026-11-04.md, docs/ESQUEMATICO_SEGUIDOR.md, docs/CONTORNO_B_EVA-RT.md, CLAUDE.md

## Restricoes mecanicas ja decididas (referencial acima)
- Furo Ø17 da ventoinha em (0,0).
- 4 furos da carcaca da ventoinha (impeller_base_1) em (±15,56; ±15,56). Os pes da carcaca apoiam em cima (TOP) em volta desses furos: area proibida em cima.
- Anel da carcaca a partir de z ≈ 11,5 mm acima da placa, r ≤ 22,1: componentes baixos podem ficar embaixo dele.
- 4 furos dos suportes dos motores (gearbox) em (±35,25; −3,73) e (±35,25; −26,55). Os motores 1020 (Ø10 x 20 mm) + caixa de engrenagens ficam em CIMA nessa regiao (x ≈ ±30..±41, y ≈ −30..0): area proibida em cima.
- Presilhas da vareta da barra de sensores (barilla_clamp) em (±43,75; −1,75) e (±43,75; 10,75): furos + area da presilha proibidos.
- Placa de succao (suction_base) EMBAIXO: retangulo x ±23,1, y −27,5 … 21 → nenhum componente na face BOTTOM ali.
- Rasgos do velcro (1 x 7 mm) em x = ±13,7…±19,7, y = −28,2. Bateria GNB 350 mAh 2S (45 x 20,5 x 12 mm) deitada em cima, atras: 45 mm em x (x ±22,5), 20,5 mm em y (frente em y ≈ −22,1, passa ~12,6 mm da borda traseira), apoiada a ~3 mm. Embaixo dela so componentes com altura ≤ 2,5 mm (TQFP ok; cristal HC-49/S SMD NAO, ~3,5–4 mm). [CORRIGIDO: antes dizia x ±10,25]
- Eixo das rodas traseiras em y = −22,56. Rodas fora da placa.
- Sensores de marca QRE1113GR (S0 esq., S1 dir.) EMBAIXO nos bracos, em (−69,5; 4,5) e (+69,5; 4,5).
- Barra de sensores: conector J2 1x8 2,54 mm na frente, linha de furos em y = 22,74, centrada em x = 0 (pads ate x ±9,74).
- Folga cobre–borda: ≥ 0,3 mm (ideal ≥ 0,5).
