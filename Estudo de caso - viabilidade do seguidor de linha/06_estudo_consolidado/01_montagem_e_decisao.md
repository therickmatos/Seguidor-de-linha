# Montagem e opções

## Geometria recebida

O projeto [RUSH/SATURN v3](../01_projeto/ProPrj_RUSH%20-%20SATURN%20-%20v3_2026-11-09.epro) foi preservado. O arquivo tem SHA-256 `ecc0495a237022ebb8a2ca117a50deeefd051657176f5c42b0f6bf40fd09cb57`. As coordenadas abaixo usam origem no centro da PCB, X para a direita e Y para a frente; são referências geométricas, não medidas de uma montagem pronta.

| Elemento | Valor aproximado |
|---|---:|
| QRE esquerdo | X = −69,5 mm; Y = 4,5 mm |
| QRE direito | X = +69,5 mm; Y = 4,5 mm |
| Pontas das abas | X = ±74,1 mm |
| Centro do QRE até a ponta | 4,6 mm |
| Largura da PCB entre pontas | 148,2 mm |
| Eixo estimado das rodas | Y = −22,59 mm |

Nas configurações originais, os QRE permanecem na mesma posição longitudinal da v3. O novo ensaio de chassi baixo usa Y = 20 mm e dois QRE por lado. Posições alternativas e contornos nas imagens são hipóteses geométricas: não representam uma PCB roteada para fabricação.

## Não confundir as três distâncias

**Entre furos** é a distância do furo frontal da base ao furo correspondente da barra. **Vão** é a separação longitudinal entre as bordas centrais das placas. **L** vai do eixo das rodas ao ponto virtual central da barra de sensores. Elas não são intercambiáveis.

| Distância entre furos | L estimado | Vão estimado |
|---:|---:|---:|
| 63,141 mm | 107,115 mm | 49,208 mm |
| 60,000 mm | 103,974 mm | 46,067 mm |

Os **63,141 mm** vieram da medição no print do usuário, de furo a furo. O comprimento global de aproximadamente **117 mm** no EVA-RT descreve outra medida e, isoladamente, não determina L nem comprova a posição do eixo. Houve também uma estimativa anterior de vão de aproximadamente 34,9 mm, que produz outra montagem; não usar resultados dessa hipótese como se fossem automaticamente os de 63,14 mm. A montagem física, os suportes e o deslocamento transversal aproximado de 0,876 mm entre os furos correspondentes ainda precisam ser conferidos.

## Alterações discretas investigadas

Os resultados detalhados estão em [Pistas e resultados](02_pistas_e_resultados.md). Com um QRE por lado, na posição longitudinal original:

- **V3 e 63,14 mm:** referência para a comparação; não se demonstrou leitura de todas as marcas.
- **V3 e 60 mm:** manteve 24/33 interseções no modelo 2025 e passou de 21/35 para 22/35 no 2024 espelhado. É uma posição possível para testar, não uma prova de ganho de velocidade ou de estabilidade.
- **QRE esquerdo em X = −68 mm:** não exige alongar a ponta pela geometria, mas requer ajuste local de montagem. Passou de 24/33 para 22/33 no modelo 2025 e de 21/35 para 20/35 no 2024; não há evidência para recomendá-lo como melhoria geral.
- **QRE esquerdo 1 mm para fora:** preservando os 4,6 mm originais até a ponta, corresponde a aproximadamente +1 mm na aba esquerda. Conservou 24/33 no modelo 2025 e passou a 22/35 no 2024. Alongar a aba sem mover o sensor não altera sua trajetória geométrica.

Uma haste ou montagem ajustável entre aproximadamente 60 e 63,14 mm pode facilitar a comparação em bancada, se for viável na construção. O ajuste é uma proposta, não uma modificação já feita. Não se comprovou que uma distância reproduza o desempenho do EVA-RT, pois a simulação não inclui controle dinâmico, motores ou tempo de volta.

## Chassi baixo com dois sensores por lado

O novo teste do simulador usa X = ±52,25 e ±77,75 mm, Y = 20 mm e 60 mm entre furos. O contorno mede 164,7 × 58,6 mm: aumenta 8,25 mm em cada ponta em relação à largura original e mantém a altura longitudinal da base. As abas chegam a Y = 24,6 mm, dentro da frente original em Y = 25,6 mm.

O desenho conserva a região central de |X| ≤ 45 mm, toda a região de Y ≤ 0 e os 15 recortes originais: 12 furos de fixação, abertura central e dois rasgos. Os centros dos quatro sensores ficam dentro do contorno. Isso não verifica a área dos componentes, trilhas ou interferência com os demais elementos da montagem.

As duas pistas atuais foram verificadas com esse contorno e essas posições. Veja [cotas e resultados do teste](04_teste_chassi_dois_sensores.md). As hipóteses históricas com mais sensores, que atingiram 19/19 ou 20/20 em pistas sintéticas anteriores, continuam sendo ensaios distintos e não fundamentam os totais atuais.
