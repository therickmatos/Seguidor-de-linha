# Pistas e resultados

## O que as pistas representam

Os dois desenhos são modelos para ensaio, não plantas oficiais:

- **TRIF 2025:** construído a partir das fotos recebidas, com retas, curvas, cruzamento e 20 marcas hipotéticas. Partes ocultas e dimensões foram estimadas. A conferência geométrica não é uma certificação integral do percurso.
- **TRIF 2024:** inspirado em uma foto de 23/11/2024. O desenho foi adaptado ao regulamento de 2026: retas analíticas, arcos circulares, um cruzamento e 35 marcas. O fechamento fora da imagem foi escolhido como hipótese; a posição exata e as dimensões da pista fotografada são desconhecidas.

### Medidas do modelo 2024

| Verificação geométrica | Resultado |
|---|---:|
| Largura da linha | 19 mm |
| Largura × comprimento transversal da marca | 19 × 40 mm |
| Afastamento nominal da borda da linha | 40 mm |
| Mudanças de curvatura e marcas esquerdas | 33 |
| Partida/chegada à direita | 2, separadas 1.000 mm |
| Menor raio dos arcos | 150 mm |
| Cruzamento | 90°, com pelo menos 450 mm de reta em cada aproximação |
| Menor distância entre bordas de trechos independentes examinados | 231 mm |
| Menor distância da linha à borda da manta simulada | 240,5 mm |

Os pares de trechos imediatamente ligados e o cruzamento permitido são tratados separadamente no cálculo. Os portões opcionais e as propriedades físicas da manta não foram modelados. A conferência cobre condições geométricas, não é certificação oficial. O arquivo [validação geométrica](dados/validacao_pista_c_regulamentar.json) contém os valores e limites.

## Interseções nominais

Um ponto representa o centro de cada QRE; a barra virtual segue o centro da linha. A coluna “comum” conta marcas nas quais o ponto cruzou também uma região interna conservadora, não uma porcentagem de leituras reais. Todos os números abaixo incluem partida e chegada.

| Configuração | TRIF 2025 | Comum | TRIF 2024 | Comum |
|---|---:|---:|---:|---:|
| 63,14 mm entre furos; QRE originais | 20/20 | 14/20 | 22/35 | 20/35 |
| 63,14 mm; esquerdo −68 mm; direito original | 20/20 | 14/20 | 21/35 | 20/35 |
| 63,14 mm; esquerdo −70,5 mm; direito original | 17/20 | 14/20 | 22/35 | 20/35 |
| 60 mm entre furos; QRE originais | 20/20 | 14/20 | 22/35 | 20/35 |

Os cálculos foram refeitos com passo de 0,25 mm e interseção independente dos segmentos com os retângulos. [Dados por configuração](dados/resultados_duas_pistas.json) incluem as marcas não cruzadas. A animação usa passo de 0,5 mm e deve ser interpretada como visualização do mesmo cenário idealizado.

No caso original de 63,14 mm, as duas marcas direitas foram intersectadas nos dois modelos. Isso não confirma sua leitura elétrica nem a lógica de largada ou parada. No modelo 2024, as outras 13 marcas não intersectadas são de curva; isso não prova que o robô sairia da linha ou perderia a volta.

## Margem e tolerâncias

Um total completo pode esconder uma passagem quase tangente. No modelo 2025, com sensores originais e desvio fixo de −2 mm, uma marca teve somente cerca de **0,065 mm** de avanço geométrico, apesar do total nominal de 20/20. Outro caso de uma pista sintética anterior teve passagem de 0,081 mm. Não são sinais ou durações medidos; não devem ser classificados como leitura segura.

Em uma [varredura separada do modelo 2025](dados/tolerancias_trif_2025.json), com a barra centrada, somente **14/20 marcas** foram intersectadas em todas as 81 combinações discretas de dimensões escolhidas. As 81 combinações não são probabilidades nem substituem tolerâncias de montagem, campo óptico e controle. Desvio fixo de ±2 mm também não representa a oscilação dinâmica de um PID.

## Histórico e comparabilidade

Um estudo anterior usou uma pista sintética de 19 marcas, outra de sete marcas e montagens diferentes. O resultado 19/19 da imagem anterior correspondia a uma configuração de barra e sensor diferente; um segundo circuito registrou 6/7. Esses ensaios explicam por que um acerto em uma pista não garante outro percurso. Eles não são as pistas atuais do simulador e não representam uma competição fotografada. O [registro histórico](../README.md) preserva suas hipóteses e resultados.
