# Pistas e resultados

## O que as pistas representam

Os dois desenhos são modelos para ensaio, não plantas oficiais nem medições da pista:

- **TRIF 2025:** redesenhado conforme o [rascunho aéreo fornecido](imagens/rascunho_aereo_trif_2025.png) e as fotos em [ângulo 1](imagens/referencia_trif_2025.png), [ângulo 2](imagens/referencia_2025_angulo_2.png), [ângulo 3](imagens/referencia_2025_angulo_3.png) e [ângulo 4](imagens/referencia_2025_angulo_4.png). O modelo inclui o retorno arredondado à esquerda, as curvas em S, a alça superior ligada à reta interna, o cruzamento e a volta inferior. A escala e os raios foram escolhidos para o teste, não medidos nas imagens; as 31 marcas são nominais, não uma contagem confirmada na fotografia.
- **TRIF 2024:** desenho anterior espelhado horizontalmente para inverter o sentido visual da passagem. O traçado, as retas e os arcos foram preservados. As marcas são construídas novamente para ficar **à esquerda nas curvas e à direita na partida e na chegada em relação ao robô**; portanto, a posição de cada fita não é uma reflexão literal do desenho anterior. A parte que não aparece na foto continua hipotética.

As [prévias de 2025](imagens/trif_2025.png) e [2024](imagens/trif_2024.png) identificam o sentido de início; o simulador permite percorrer as duas. Em ambos os casos, as posições das marcas e as medidas foram escolhidas para testar o robô segundo o modelo nominal do TRIF 2026. A trajetória no cruzamento é imposta pelo programa.

As marcas de curva são geradas à esquerda em cada mudança de curvatura dos arcos e retas do modelo; partida e chegada ficam à direita e a 1 m de distância. A decomposição escolhida para os trechos em S produz algumas marcas próximas entre si. Como os arcos reais não foram medidos, a quantidade e a posição dessas marcas podem diferir das usadas em 2025.

## Geometria dos modelos

| Verificação | TRIF 2025 | TRIF 2024 |
|---|---:|---:|
| Largura da linha | 19 mm | 19 mm |
| Marca: largura × comprimento transversal | 19 × 40 mm | 19 × 40 mm |
| Afastamento nominal da borda da linha | 40 mm | 40 mm |
| Marcas esquerdas de curva | 29 | 33 |
| Partida e chegada à direita | 2, separadas 1.000 mm | 2, separadas 1.000 mm |
| Menor raio dos arcos | 142 mm | 150 mm |
| Cruzamento | 85,99°, com pelo menos 652 mm de reta nas aproximações | 90°, com pelo menos 450 mm de reta nas aproximações |

No modelo 2025, a menor distância entre bordas de trechos independentes examinados é de 204,65 mm; no 2024, é de 231 mm. No modelo 2025, a comparação exclui o cruzamento permitido e trechos separados por menos de 500 mm ao longo da linha, por pertencerem à mesma região contínua do percurso. A extensão estimada do modelo 2025 é de **19,62 m**, abaixo dos limites de 60 m da categoria Pro e 20 m da Junior. A escala foi arbitrada para a simulação, portanto esse número não é uma medida do circuito fotografado. Os portões e as propriedades físicas da manta não foram modelados. As checagens ([2025](dados/validacao_pista_trif2025.json), [2024](dados/validacao_pista_c_regulamentar.json)) são geométricas e não constituem certificação oficial.

## Interseções nominais

Um ponto representa o centro de cada QRE; a barra virtual segue o centro da linha. A coluna “comum” conta marcas nas quais o ponto cruzou também uma região interna conservadora, não uma porcentagem de leituras reais. Todos os números incluem partida e chegada.

| Configuração | TRIF 2025 | Comum | TRIF 2024 | Comum |
|---|---:|---:|---:|---:|
| 63,14 mm entre furos; QRE originais | 24/31 | 18/31 | 21/35 | 18/35 |
| 63,14 mm; esquerdo −68 mm; direito original | 23/31 | 22/31 | 20/35 | 19/35 |
| 63,14 mm; esquerdo −70,5 mm; direito original | 24/31 | 17/31 | 22/35 | 18/35 |
| 60 mm entre furos; QRE originais | 25/31 | 19/31 | 22/35 | 19/35 |

Os cálculos foram refeitos com passo de 0,25 mm e interseção independente dos segmentos com os retângulos. Os [dados por configuração](dados/resultados_duas_pistas.json) incluem as marcas não cruzadas. A animação usa passo de 0,5 mm e representa o mesmo cenário idealizado.

No caso original de 63,14 mm, as duas marcas direitas foram intersectadas em ambos os modelos. Isso não confirma sua leitura elétrica nem a lógica de largada ou parada. As marcas restantes sem interseção são de curva; isso não prova que o robô sairia da linha ou perderia a volta.

## Margem, tolerâncias e histórico

Um total completo pode esconder uma passagem quase tangente. O simulador destaca interseções muito curtas, mas mesmo as demais exigem verificação física. A região comum é uma faixa geométrica conservadora, não uma probabilidade de detecção. Desvio fixo também não representa a oscilação dinâmica de um PID.

Os resultados de **17/26** e **20/20** para versões anteriores do modelo 2025, e **22/35** para a 2024 antes do espelhamento, correspondem a desenhos anteriores. O [arquivo histórico de tolerâncias](dados/tolerancias_trif_2025.json), inclusive a varredura de 81 combinações, pertence à versão antiga do modelo 2025 e **não se aplica à pista atual**. Outro estudo usou uma pista sintética de 19 marcas e uma de sete; seus resultados e hipóteses permanecem no [registro histórico](../README.md). Não compare diretamente as contagens, pois os percursos, os sentidos e a quantidade de marcas mudaram.
