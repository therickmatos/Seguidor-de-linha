# Conferência da combinação: barra -8 mm; sensores +1 mm

Configuração: um QRE por lado em x = ±69,5 mm e y = 5,5 mm na origem da PCB; eixo y = -22,587743819 mm; L = 84,795483579 mm; vão central base–barra = 26,88849766 mm. Rodas e motores não deslocados. A fonte EPRO não foi alterada.

A volta revisada anterior confirmou 19/19 interseções nominais com passo de 0,1 mm. Somente 17/19 interceptaram a região comum às tolerâncias consideradas. Em M7, a distância no plano médio foi 89,495309 mm, quase na borda nominal de 89,5 mm; em M11 foi 48,200942 mm, com interseção por uma parte da marca fora desse plano médio. Portanto, contar interseções não equivale a margem de leitura elétrica.

Um segundo circuito fechado foi construído para testar a ligação R100 direita de 90° → R200 direita de 90°. Ele tem 6,842478 m, nenhum cruzamento, retas paralelas separadas por 300 mm entre centros (281 mm entre bordas), raio mínimo de 100 mm, marcações afastadas 40 mm da borda da linha, sem sobreposição, e chegada 1 m antes da partida na mesma reta. Há 500 mm retos antes da chegada e 1500 mm após a partida. A manta de referência tem 290,5 mm de margem até a borda da linha; portões opcionais não foram modelados. Arcos consecutivos de diferentes curvaturas são previstos no item 4.16 do regulamento consultado. Os trechos da mesma curva composta são vizinhos conectados; o afastamento entre trechos independentes foi avaliado entre as retas paralelas e as extremidades opostas do oval.

Resultado do segundo circuito: 6/7 marcas cobertas. Falha C2 na ligação R100 → R200: distância do QRE de 42,127081 mm no plano médio, abaixo da borda interna nominal de 49,5 mm; nenhuma interseção com o retângulo inteiro da marca. A classificação das sete marcas foi conferida independentemente por interseção de polilinhas e polígonos no Shapely. A distância de C2 variou cerca de 0,000056 mm entre passos de 0,25 e 0,1 mm. A marca de fechamento C5 foi avaliada em uma passagem com trajetória disponível antes e depois do fechamento, evitando truncamento no fim do traçado simulado.

O modelo mantém o ponto virtual central da barra sobre o centro da linha, eixo sem escorregamento e corpo rígido. Não simula resposta óptica, dinâmica dos motores nem controle PD. A falha vale para essa trajetória idealizada, não demonstra que qualquer controlador físico necessariamente falhará.

Conclusão: a combinação é uma candidata de montagem, mas não passou em todos os circuitos testados com as condições geométricas verificadas. O resultado anterior de 19/19, sozinho, não valida sua fabricação como solução garantida de leitura.

Dados: verificacao_circuito_6_de_7.json. Figura: circuito_e_falha.png. As coordenadas e medidas estão em milímetros.
