# Estudo consolidado: RUSH v3 e marcações do TRIF

Este diretório reúne a análise realizada até **10/11/2026** sobre o RUSH/SATURN v3, baseado no EVA-RT, para preparar o robô para o TRIF. O simulador compara a geometria original, com **um QRE por lado**, com um **chassi baixo experimental de dois QRE por lado**. O arquivo da PCB foi preservado; o contorno experimental não inclui roteamento.

## Comece pelo simulador

[Baixar o simulador autocontido](simulador.html) e abri-lo no Chrome ou Edge. Ao navegar pelo GitHub, use a opção de download: a página de código do GitHub não executa o HTML. O arquivo funciona sem internet e contém somente duas pistas:

- **TRIF 2025:** modelo redesenhado a partir do [rascunho aéreo](imagens/rascunho_aereo_trif_2025.png), da [retificação posterior](imagens/rascunho_retificacao_trif_2025.png) e das fotografias, com 33 marcações nominais.
- **TRIF 2024:** modelo espelhado para inverter o sentido visual de percurso, com 35 marcações nominais.

**Nenhuma é uma planta oficial medida.** Nas duas há trechos ou dimensões estimados, e a trajetória correta no cruzamento é imposta. O programa anima a geometria; não prova que o robô real seguirá a linha ou lerá uma fita.

O arquivo abre com **Chassi baixo · 2 sensores por lado · furos 60 mm**. Escolha a pista, clique em **Simular percurso** ou use **Próxima marca** e **Ver detalhe** para acompanhar os quatro sensores. E1/D1 são os internos; E2/D2, os externos. Os totais separam esquerda e direita, e cada marca é contada uma única vez.

## Conclusão para a decisão atual

Com dois QRE por lado em **X = ±52,25 e ±77,75 mm**, **Y = 20 mm** e **60 mm entre furos**, o modelo intersectou **31/31 marcas esquerdas e 2/2 direitas em 2025**, e **33/33 esquerdas e 2/2 direitas em 2024**. Todas também cruzaram a região comum conservadora. O contorno de **164,7 × 58,6 mm** mantém os 15 recortes mecânicos do v3 e suas regiões central e traseira. Veja o [teste do chassi com dois sensores](04_teste_chassi_dois_sensores.md) para as cotas, comparação de 60–70 mm e limitações.

Com os QRE originais em X = ±69,5 mm e Y = 4,5 mm, barra centrada e **63,14 mm entre os furos**, o centro dos sensores intersectou **24/33** marcas do modelo 2025 e **21/35** do modelo 2024 espelhado. As contagens incluem as marcas de partida e chegada. Elas não demonstram sinal óptico, resposta do controlador ou volta válida.

Com **60 mm entre os furos** e os sensores originais, os resultados foram 24/33 e 22/35, respectivamente. Levar somente o QRE esquerdo 1 mm para fora resultou em 24/33 e 22/35. Nenhum desses cenários demonstra leitura segura de todas as marcas.

O chassi baixo a 60 mm é a configuração inicial do novo ensaio geométrico. As opções originais continuam disponíveis para comparação. Ajustar o controle e calibrar os sinais requer testes físicos; não há evidência aqui de que uma das configurações seja mais rápida. A leitura de todas as marcas esquerdas pode ajudar estratégias de velocidade, mas não é um requisito isolado de volta válida; a passagem pela linha e a parada precisam ser verificadas conforme o regulamento.

## Conteúdo

| Arquivo | Assunto |
|---|---|
| [Montagem e opções](01_montagem_e_decisao.md) | Cotas da v3 e da barra, diferenças em relação ao EVA-RT e alternativas examinadas. |
| [Pistas e resultados](02_pistas_e_resultados.md) | Geometria, regras verificadas, contagens e histórico dos modelos. |
| [Método e próximos testes](03_metodologia_e_testes.md) | Hipóteses, margens, limitações e plano de validação. |
| [Teste com dois sensores por lado](04_teste_chassi_dois_sensores.md) | Novo chassi baixo, instruções do simulador e resultados a 60, 65 e 70 mm entre furos. |
| [Simulador](simulador.html) | Arquivo HTML para download e uso local. |
| [Código](codigo/) | Construção das pistas, gerador e verificação das interseções. |
| [Dados](dados/) | Resultados e checagens geométricas. |

O [estudo arquivado de 09/11](../README.md) e seus arquivos permanecem preservados. Ele usa outros circuitos e outras montagens; seus resultados, como 19/19, não são automaticamente comparáveis aos modelos atuais.

Referências: [regulamento do TRIF 2026](../02_referencias/TRIF%202026%20-%20Seguidor%20de%20Linha.pdf), [IFSP](https://ifsp.edu.br/index.php/trif/83-pesquisa/6044-trif2026) e [EVA-RT, EXOTIC TEAM MX](https://github.com/EXOTIC-TEAM-MX/EVA-RT). O código derivado mantém a [licença AGPL-3.0](../LICENSE).
