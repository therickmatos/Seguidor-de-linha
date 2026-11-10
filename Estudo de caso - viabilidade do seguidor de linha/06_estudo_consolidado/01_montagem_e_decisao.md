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

Os QRE permanecem na mesma posição longitudinal da v3. Posições alternativas e contornos nas imagens são hipóteses geométricas: não representam uma PCB fabricável ou alterada.

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
- **V3 e 60 mm:** mantém as mesmas contagens nominais das duas pistas atuais. É uma posição possível para testar, não uma prova de ganho de velocidade ou de estabilidade.
- **QRE esquerdo em X = −68 mm:** não exige alongar a ponta pela geometria, mas requer ajuste local de montagem. Manteve o total nominal no modelo 2025 e reduziu uma interseção no 2024; não há evidência para recomendá-lo como melhoria geral.
- **QRE esquerdo 1 mm para fora:** preservando os 4,6 mm originais até a ponta, corresponde a aproximadamente +1 mm na aba esquerda. Piorou a contagem no modelo 2025 e não aumentou a contagem no 2024. Alongar a aba sem mover o sensor não altera sua trajetória geométrica.

Uma haste ou montagem ajustável entre aproximadamente 60 e 63,14 mm pode facilitar a comparação em bancada, se for viável na construção. O ajuste é uma proposta, não uma modificação já feita. Não se comprovou que uma distância reproduza o desempenho do EVA-RT, pois a simulação não inclui controle dinâmico, motores ou tempo de volta.

As hipóteses históricas com mais sensores foram registradas antes da definição atual de **um por lado**. Algumas atingiram 19/19 e 20/20 em pistas sintéticas anteriores, mas perderam margem sob perturbações ou falharam em outro ensaio; não comprovam resultado para o modelo atual. Não foram adicionadas opções de múltiplos sensores ao simulador consolidado.
