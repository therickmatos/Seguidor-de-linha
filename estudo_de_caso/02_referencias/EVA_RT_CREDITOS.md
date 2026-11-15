# Referências e créditos

O robô analisado é baseado no **EVA-RT**, de **EXOTIC TEAM MX**: https://github.com/EXOTIC-TEAM-MX/EVA-RT . O repositório de referência é distribuído sob AGPL-3.0. O arquivo LICENSE deste estudo preserva a licença usada pelo projeto local; os créditos de origem permanecem nos arquivos derivados.

As malhas de `stl/` são cópias das referências locais de gearbox, aro da roda, patim e peças de fixação das varetas. Não são novas peças validadas pelo estudo, nem incluem o pneu montado. As demais peças do EVA-RT continuam disponíveis na pasta `referencias/eva-rt/` do repositório principal e no projeto de origem.

O Gerber da barra V1 é o arquivo de referência utilizado para extrair sensores e furação. A montagem do patim original com a V1 tem diferenças de furação/alinhamento que ainda exigem conferência; não se presume que a impressão dos STL originais, sem adaptação, resolva a montagem completa.

O PDF TRIF foi fornecido/consultado para as regras da 7ª edição de 2026, classe Pro. Ele mantém a autoria do IFSP e do anexo RoboCore; não é um documento produzido pelo estudo.

`parametros_mecanicos_EVA.json` registra a extração mecânica da investigação. Seus valores de L próximos de 100 mm se referem à referência original do desenho. O cálculo consolidado de L ≈ 92,8 mm para preservar o vão na base SATURN/V1 está no README e nos dados de simulação. Não substituir uma referência pela outra.
