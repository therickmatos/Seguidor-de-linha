# Pistas e resultados

## O que as pistas representam

Os dois desenhos são modelos para ensaio, não plantas oficiais nem medições da pista:

- **TRIF 2025:** redesenhado a partir das fotografias, inclusive a [imagem recebida na correção](imagens/referencia_trif_2025.png). Contém a reta longa, o retorno inferior, a alça superior, o S e um cruzamento. O trecho à esquerda que sai do enquadramento foi fechado por hipótese e aparece em amarelo. As proporções e o raio de cada curva são estimados; as 26 marcas são nominais, não uma contagem confirmada na fotografia.
- **TRIF 2024:** desenho anterior espelhado horizontalmente para inverter o sentido visual da passagem. O traçado, as retas e os arcos foram preservados. As marcas são construídas novamente para ficar **à esquerda nas curvas e à direita na partida e na chegada em relação ao robô**; portanto, a posição de cada fita não é uma reflexão literal do desenho anterior. A parte que não aparece na foto continua hipotética.

As [prévias de 2025](imagens/trif_2025.png) e [2024](imagens/trif_2024.png) identificam o sentido de início; o simulador permite percorrer as duas. Em ambos os casos, as posições das marcas e as medidas foram escolhidas para testar o robô segundo o modelo nominal do TRIF 2026. A trajetória no cruzamento é imposta pelo programa.

## Geometria dos modelos

| Verificação | TRIF 2025 | TRIF 2024 |
|---|---:|---:|
| Largura da linha | 19 mm | 19 mm |
| Marca: largura × comprimento transversal | 19 × 40 mm | 19 × 40 mm |
| Afastamento nominal da borda da linha | 40 mm | 40 mm |
| Marcas esquerdas de curva | 24 | 33 |
| Partida e chegada à direita | 2, separadas 1.000 mm | 2, separadas 1.000 mm |
| Menor raio dos arcos | 150 mm | 150 mm |
| Cruzamento | 90°, com pelo menos 650 mm de reta nas aproximações | 90°, com pelo menos 450 mm de reta nas aproximações |

No modelo 2024, a menor distância entre bordas de trechos independentes examinados é de 231 mm, e a menor distância da linha à borda da manta simulada é de 240,5 mm. Pares imediatamente ligados e o cruzamento permitido recebem tratamento separado. Os portões e as propriedades físicas da manta não foram modelados. As checagens ([2025](dados/validacao_pista_trif2025.json), [2024](dados/validacao_pista_c_regulamentar.json)) são geométricas e não constituem certificação oficial.

## Interseções nominais

Um ponto representa o centro de cada QRE; a barra virtual segue o centro da linha. A coluna “comum” conta marcas nas quais o ponto cruzou também uma região interna conservadora, não uma porcentagem de leituras reais. Todos os números incluem partida e chegada.

| Configuração | TRIF 2025 | Comum | TRIF 2024 | Comum |
|---|---:|---:|---:|---:|
| 63,14 mm entre furos; QRE originais | 17/26 | 15/26 | 21/35 | 18/35 |
| 63,14 mm; esquerdo −68 mm; direito original | 18/26 | 15/26 | 20/35 | 19/35 |
| 63,14 mm; esquerdo −70,5 mm; direito original | 17/26 | 15/26 | 22/35 | 18/35 |
| 60 mm entre furos; QRE originais | 17/26 | 15/26 | 22/35 | 19/35 |

Os cálculos foram refeitos com passo de 0,25 mm e interseção independente dos segmentos com os retângulos. Os [dados por configuração](dados/resultados_duas_pistas.json) incluem as marcas não cruzadas. A animação usa passo de 0,5 mm e representa o mesmo cenário idealizado.

No caso original de 63,14 mm, as duas marcas direitas foram intersectadas em ambos os modelos. Isso não confirma sua leitura elétrica nem a lógica de largada ou parada. As marcas restantes sem interseção são de curva; isso não prova que o robô sairia da linha ou perderia a volta.

## Margem, tolerâncias e histórico

Um total completo pode esconder uma passagem quase tangente. O simulador destaca interseções muito curtas, mas mesmo as demais exigem verificação física. A região comum é uma faixa geométrica conservadora, não uma probabilidade de detecção. Desvio fixo também não representa a oscilação dinâmica de um PID.

Os resultados de **20/20** para a pista 2025 anterior e **22/35** para a 2024 anterior correspondem aos desenhos antes desta correção. O [arquivo histórico de tolerâncias](dados/tolerancias_trif_2025.json), inclusive a varredura de 81 combinações, pertence à versão antiga do modelo 2025 e **não se aplica à pista atual**. Outro estudo usou uma pista sintética de 19 marcas e uma de sete; seus resultados e hipóteses permanecem no [registro histórico](../README.md). Não compare diretamente as contagens, pois os percursos, os sentidos e a quantidade de marcas mudaram.
