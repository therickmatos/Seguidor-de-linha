# Pistas e resultados

## O que as pistas representam

Os três desenhos são modelos para ensaio, não plantas oficiais nem medições da pista:

- **TRIF 2025:** redesenhado conforme o [rascunho aéreo](imagens/rascunho_aereo_trif_2025.png), a [retificação posterior](imagens/rascunho_retificacao_trif_2025.png) e as fotos em [ângulo 1](imagens/referencia_trif_2025.png), [ângulo 2](imagens/referencia_2025_angulo_2.png), [ângulo 3](imagens/referencia_2025_angulo_3.png) e [ângulo 4](imagens/referencia_2025_angulo_4.png). O modelo inclui o retorno à esquerda, as curvas em S, a alça superior ligada à reta interna, o cruzamento e a volta inferior. Os três trechos indicados na retificação são verticais, com ligações em arco. A escala e os raios foram escolhidos para o teste, não medidos nas imagens; as 33 marcas são nominais, não uma contagem confirmada na fotografia.
- **TRIF 2024 · sentido corrigido:** o desenho (retas, arcos e coordenadas) é exatamente o mesmo de antes (distância máxima entre as duas polilinhas < 1e-9 mm), mas o robô agora o percorre no sentido contrário ao do modelo espelhado anterior. As marcas foram regeradas pela regra: **à esquerda nas curvas e à direita na partida e na chegada em relação ao robô**, na mesma reta de baixo e nos mesmos dois pontos (x = 1.400 e 2.400 mm), com os papéis trocados: o robô corre para a direita, a chegada fica em x = 1.400 e a partida em x = 2.400, com 1 m entre elas, 1.250 mm de reta antes da chegada e 750 mm depois da partida. A parte que não aparece na foto continua hipotética.
- **Pista de teste do EVA-RT:** modelo aproximado reconstruído de um quadro do vídeo de teste do EVA-RT (EXOTIC TEAM MX), em perspectiva; veja a seção própria no fim.

As [prévias de 2025](imagens/trif_2025.png) e [2024](imagens/trif_2024.png) identificam o sentido de início; o simulador permite percorrer as duas. Em ambos os casos, as posições das marcas e as medidas foram escolhidas para testar o robô segundo o modelo nominal do TRIF 2026. A trajetória no cruzamento é imposta pelo programa.

As marcas de curva são geradas à esquerda em cada mudança de curvatura dos arcos e retas do modelo; partida e chegada ficam à direita e a 1 m de distância. A decomposição escolhida para os trechos em S produz algumas marcas próximas entre si. Como os arcos reais não foram medidos, a quantidade e a posição dessas marcas podem diferir das usadas em 2025.

## Geometria dos modelos

| Verificação | TRIF 2025 | TRIF 2024 |
|---|---:|---:|
| Largura da linha | 19 mm | 19 mm |
| Marca: largura × comprimento transversal | 19 × 40 mm | 19 × 40 mm |
| Afastamento nominal da borda da linha | 40 mm | 40 mm |
| Marcas esquerdas de curva | 31 | 33 |
| Partida e chegada à direita | 2, separadas 1.000 mm | 2, separadas 1.000 mm |
| Menor raio dos arcos | 106,5 mm | 150 mm |
| Cruzamento | 90°, com pelo menos 585 mm de reta nas aproximações | 90°, com pelo menos 450 mm de reta nas aproximações |

No modelo 2025, a menor distância entre bordas de trechos independentes examinados é de 204,65 mm; no 2024, é de 231 mm. No modelo 2025, a comparação exclui o cruzamento permitido e trechos separados por menos de 500 mm ao longo da linha, por pertencerem à mesma região contínua do percurso. A extensão estimada do modelo 2025 é de **19,43 m**, abaixo dos limites de 60 m da categoria Pro e 20 m da Junior. A escala foi arbitrada para a simulação, portanto esse número não é uma medida do circuito fotografado. Os portões e as propriedades físicas da manta não foram modelados. As checagens ([2025](dados/validacao_pista_trif2025.json), [2024](dados/validacao_pista_c_regulamentar.json)) são geométricas e não constituem certificação oficial.

## Interseções nominais

Um ponto representa o centro de cada QRE; a barra virtual segue o centro da linha. A coluna “comum” conta marcas nas quais o ponto cruzou também uma região interna conservadora, não uma porcentagem de leituras reais. Todos os números incluem partida e chegada.

| Configuração | TRIF 2025 | Comum | TRIF 2024 | Comum |
|---|---:|---:|---:|---:|
| 63,14 mm entre furos; QRE originais | 24/33 | 16/33 | 20/35 | 19/35 |
| 63,14 mm; esquerdo −68 mm; direito original | 22/33 | 19/33 | 20/35 | 19/35 |
| 63,14 mm; esquerdo −70,5 mm; direito original | 24/33 | 15/33 | 21/35 | 18/35 |
| 60 mm entre furos; QRE originais | 24/33 | 16/33 | 21/35 | 19/35 |
| EVA-RT original, L = 100 mm, um QRE por lado | 26/33 | 21/33 | 23/35 | 19/35 |
| 60 mm; chassi baixo, dois QRE por lado | 33/33 | 33/33 | 35/35 | 35/35 |
| 65 mm; chassi baixo, dois QRE por lado | 33/33 | 33/33 | 35/35 | 34/35 |
| 70 mm; chassi baixo, dois QRE por lado | 33/33 | 30/33 | 34/35 | 33/35 |

No chassi baixo, os dois QRE de cada lado ficam em |X| = 52,25 e 77,75 mm, Y = 20 mm. Cada marca conta uma vez se algum sensor do lado correspondente a intersecta. A 60 mm, os totais se dividem em **31/31 à esquerda e 2/2 à direita em 2025**, e **33/33 à esquerda e 2/2 à direita em 2024**, também na região comum. A 70 mm, no modelo 2025 todas as marcas nominais ainda são intersectadas (algumas deixam de cruzar a região comum); no 2024 com o sentido corrigido, uma marca de curva deixa de ser intersectada (34/35).

Os cálculos foram refeitos com passo de 0,25 mm e interseção independente dos segmentos com os retângulos. Os [dados por configuração](dados/resultados_duas_pistas.json) incluem os resultados por marca, sensores que a intersectam e totais por lado. A animação usa passo de 0,5 mm e representa o mesmo cenário idealizado. A verificação automatizada no navegador compara cada marca do chassi baixo a 60, 65 e 70 mm com o cálculo independente.

No caso original de 63,14 mm, as duas marcas direitas foram intersectadas em ambos os modelos. Isso não confirma sua leitura elétrica nem a lógica de largada ou parada. As marcas restantes sem interseção são de curva; isso não prova que o robô sairia da linha ou perderia a volta.

## Margem, tolerâncias e histórico

Um total completo pode esconder uma passagem quase tangente. O simulador destaca interseções muito curtas, mas mesmo as demais exigem verificação física. A região comum é uma faixa geométrica conservadora, não uma probabilidade de detecção. Desvio fixo também não representa a oscilação dinâmica de um PID.

Os resultados de **24/31**, **17/26** e **20/20** para versões anteriores do modelo 2025, e **22/35** para a 2024 antes da correção do sentido (21/35 no modelo espelhado anterior), correspondem a desenhos anteriores. O [arquivo histórico de tolerâncias](dados/tolerancias_trif_2025.json), inclusive a varredura de 81 combinações, pertence à versão antiga do modelo 2025 e **não se aplica à pista atual**. Outro estudo usou uma pista sintética de 19 marcas e uma de sete; seus resultados e hipóteses permanecem no [registro histórico](../README.md). Não compare diretamente as contagens, pois os percursos, os sentidos e a quantidade de marcas mudaram.

## Pista de teste do EVA-RT (modelo aproximado)

Reconstruída de um único quadro de vídeo (1920 × 1080, em perspectiva) do teste do EVA-RT, em [`imagens/referencia_pista_teste_eva_rt.png`](imagens/referencia_pista_teste_eva_rt.png). **É uma aproximação**: só o canto superior esquerdo da placa aparece no quadro, a escala foi ajustada e dois trechos foram completados por hipótese (a reta de baixo sob o robô e o trecho do grampo de baixo cortado pela borda da imagem).

- **Método:** modelo de câmera ajustado para que as 27 marcas fiquem retangulares e congruentes; retificação; extração da linha central; ajuste por retas e arcos exatos, com junções tangentes e pista fechada. Erro RMS do ajuste de cerca de 1,3 mm no plano. Código em [`pista_eva_rt_teste.py`](codigo/pista_eva_rt_teste.py) e [`retificar_pista_eva_rt.py`](codigo/retificar_pista_eva_rt.py); conferência visual em [`imagens/pista_eva_rt_sobreposicao.png`](imagens/pista_eva_rt_sobreposicao.png) e prévia em [`imagens/pista_teste_eva_rt.png`](imagens/pista_teste_eva_rt.png).
- **Escala:** a linha foi ajustada para 19 mm (fator 0,96 sobre a escala que daria marcas de 19 × 40 mm; a linha media ~19,8 mm antes do ajuste). A placa resultante tem cerca de 2440 × 1221 mm, o que concorda com a chapa padrão de 2440 × 1220 mm sem que isso tenha sido usado no ajuste. A distância das marcas isoladas à linha (~69 mm) também bate com a regra (49,5 a 89,5 mm).
- **Geometria:** volta de cerca de 10,9 m; raios de 101 a 111 mm nos laços, nas curvas em S e no grampo da direita, de 152 a 170 mm na sequência ondulada e de 208 mm no grampo grande de baixo; menor raio 101,1 mm. **Três** cruzamentos da reta central com as pernas dos laços, a ~89,5° (a leitura inicial era de dois). Menor trecho reto de 125,6 mm e bordas de trechos independentes a 77 mm: fora do regulamento do TRIF, o que é apenas registrado.
- **Sentido:** o robô corre para a direita na reta de baixo. Nesse sentido as marcas de curva ficam à esquerda (dentro dos grampos e acima da reta de baixo e da sequência ondulada) e as duas marcas isoladas da reta de baixo ficam à direita, como pede a regra. A partida é a marca mais à direita; a chegada fica ~515 mm atrás (menos de 1 m, medida na foto).
- **Marcas:** a foto mostra 27 (25 de curva e 2 de partida/chegada); a regra gera 26 (24 de curva e 2). 26 das 27 coincidem a menos de 80 mm (mediana 2,5 mm); só falta uma marca do primeiro laço, no canto superior esquerdo. As marcas do modelo são geradas pela regra, não copiadas da foto.
- **Contagens** (um QRE por lado, L = 100 mm, X = ±69,5 mm, Y = 4,5 mm): 22/26 nominal e 16/26 na região comum; com o chassi baixo de dois sensores por lado a 60 mm, 25/26 nominal. Dados em [`dados/validacao_pista_eva_rt_teste.json`](dados/validacao_pista_eva_rt_teste.json) e [`dados/resultados_duas_pistas.json`](dados/resultados_duas_pistas.json).
