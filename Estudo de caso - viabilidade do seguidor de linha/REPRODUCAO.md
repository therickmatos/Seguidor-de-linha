# Reprodução dos ensaios

## Animações

Baixe e abra em um navegador os dois HTML de `03_simulacoes/02_ajuste_8mm_1mm/`. Os dados, estilos e lógica de animação estão incluídos. A apresentação foi conferida em Chrome, inclusive em largura de 320 px; a animação 6/7 foi reproduzida até o fim. A velocidade visual é arbitrária, sem previsão de tempo físico.

As fontes dos dois visuais estão em `05_codigo/fontes_visuais/`. São fragmentos para a superfície de visualização original; os arquivos de `03_simulacoes/` já são as versões completas para abrir localmente.

## Cálculo portátil

Requer Python e os pacotes listados em `05_codigo/requisitos.txt`. As versões ali registradas são as versões instaladas no ambiente da análise, não uma exigência de usar versões futuras ou um resultado de benchmark.

```sh
python -m pip install -r "05_codigo/requisitos.txt"
python "05_codigo/reproduzir_estudo.py" --step 0.25
```

Execute os comandos a partir desta pasta. Os resultados vão para `reproducao/`, sem sobrescrever os dados arquivados. O programa usa os parâmetros registrados no estudo, sem caminhos pessoais ou dependência de acesso à rede.

Resultados esperados com passo de 0,25 mm:

| Ensaio | Cobertura nominal esperada |
|---|---:|
| Volta revisada, configuração base | 17/19 |
| Volta revisada, barra −8 mm e QRE +1 mm | 19/19 |
| Circuito fechado R100 → R200, configuração ajustada | 6/7, falha C2 |
| Auditoria específica de cruzamentos nas 220 sequências | 20 reprovadas nessa checagem; outras 200 sem aprovação integral |

A auditoria verifica uma condição necessária de cruzamento com trechos retos; não transforma as sequências restantes em pistas aprovadas contra todos os itens do edital. A verificação do circuito de sete marcas inclui uma interseção independente por Shapely.

Para comparar um passo menor:

```sh
python "05_codigo/reproduzir_estudo.py" --step 0.1 --output "reproducao_passo_0p1"
```

O passo é espacial, em milímetros de avanço do ponto virtual frontal. Não corresponde ao período de amostragem do ADC ou do controlador.

## Proveniência e limites

`05_codigo/originais/` contém cópias dos módulos usados no estudo. Suas funções de linha de comando históricas mantêm caminhos e configurações do ambiente original; **use o reprodutor portátil**, que chama somente as funções geométricas e passa os parâmetros deste registro. Eles não são firmware para o ATmega.

O reprodutor confirma a cinemática e as interseções. Não reexecuta automaticamente a extração das cotas dos Gerbers/STL, não substitui uma montagem 3D e não gera Gerbers aprovados. Os parâmetros mecânicos extraídos foram preservados em `02_referencias/parametros_mecanicos_EVA.json`.

`comparacao_animacao.json` arquiva os dados reduzidos de desenho, incluindo poses especiais das passagens. A classificação de leitura vem do cálculo mais fino, não de inspeção de pixels ou da interpolação visual.

Os resultados brutos antigos em `04_historico_exploratorio/` têm eixos/hipóteses históricos e não devem substituir os parâmetros consolidados do README.
