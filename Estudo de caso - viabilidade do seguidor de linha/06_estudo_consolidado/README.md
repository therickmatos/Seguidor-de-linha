# Estudo consolidado: RUSH v3 e marcações do TRIF

Este diretório reúne a análise realizada até **10/11/2026** sobre o RUSH/SATURN v3, baseado no EVA-RT, para preparar o robô para o TRIF. O foco atual é a leitura das marcações laterais com **um QRE por lado**, sem mudar o arquivo da PCB ou inspecionar o roteamento.

## Comece pelo simulador

[Baixar o simulador autocontido](simulador.html) e abri-lo no Chrome ou Edge. Ao navegar pelo GitHub, use a opção de download: a página de código do GitHub não executa o HTML. O arquivo funciona sem internet e contém somente duas pistas:

- **TRIF 2025:** modelo inspirado nas fotografias, com 20 marcações.
- **TRIF 2024:** modelo inspirado na fotografia e redesenhado com retas, arcos e marcações nominais do TRIF 2026, com 35 marcações.

**Nenhuma é uma planta oficial medida.** Nas duas há trechos ou dimensões estimados, e a trajetória correta no cruzamento é imposta. O programa anima a geometria; não prova que o robô real seguirá a linha ou lerá uma fita.

## Conclusão para a decisão atual

Com os QRE originais em X = ±69,5 mm e Y = 4,5 mm, barra centrada e **63,14 mm entre os furos**, o centro dos sensores intersectou **20/20** marcas do modelo 2025 e **22/35** do modelo 2024. As contagens incluem as marcas de partida e chegada. Elas não demonstram sinal óptico, resposta do controlador ou volta válida.

Nos dois modelos atuais, aproximar a barra para **60 mm entre os furos**, mantendo os sensores originais, conservou essas mesmas contagens nominais. Levar o QRE esquerdo 1 mm para fora reduziu o modelo 2025 para **17/20** e manteve 22/35 no modelo 2024. Esses cenários não justificam afirmar que aumentar as abas, aproximar a barra ou manter a v3 garantirá todas as leituras.

Para a preparação da competição, a alternativa mais simples é começar com a geometria original dos QRE e, se a montagem permitir, comparar fisicamente distâncias próximas de 60–63,14 mm entre os furos. Ajustar o controle e calibrar os sinais requer testes; não há evidência aqui de que uma das distâncias seja mais rápida. A leitura de todas as marcas esquerdas pode ajudar estratégias de velocidade, mas não é um requisito isolado de volta válida; a passagem pela linha e a parada precisam ser verificadas conforme o regulamento.

## Conteúdo

| Arquivo | Assunto |
|---|---|
| [Montagem e opções](01_montagem_e_decisao.md) | Cotas da v3 e da barra, diferenças em relação ao EVA-RT e alternativas examinadas. |
| [Pistas e resultados](02_pistas_e_resultados.md) | Geometria, regras verificadas, contagens e histórico dos modelos. |
| [Método e próximos testes](03_metodologia_e_testes.md) | Hipóteses, margens, limitações e plano de validação. |
| [Simulador](simulador.html) | Arquivo HTML para download e uso local. |
| [Código](codigo/) | Construção das pistas, gerador e verificação das interseções. |
| [Dados](dados/) | Resultados e checagens geométricas. |

O [estudo arquivado de 09/11](../README.md) e seus arquivos permanecem preservados. Ele usa outros circuitos e outras montagens; seus resultados, como 19/19, não são automaticamente comparáveis aos modelos atuais.

Referências: [regulamento do TRIF 2026](../02_referencias/TRIF%202026%20-%20Seguidor%20de%20Linha.pdf), [IFSP](https://ifsp.edu.br/index.php/trif/83-pesquisa/6044-trif2026) e [EVA-RT, EXOTIC TEAM MX](https://github.com/EXOTIC-TEAM-MX/EVA-RT). O código derivado mantém a [licença AGPL-3.0](../LICENSE).
