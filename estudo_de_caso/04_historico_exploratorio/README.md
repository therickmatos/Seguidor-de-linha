# Histórico exploratório — não é uma matriz de aprovação do TRIF

Os arquivos desta pasta registram buscas e resultados intermediários. Não devem ser interpretados como recomendação atual para fabricar a PCB.

## As 220 transições

`comparacao_preliminar.json`, `busca_combinada.json` e `solucoes_confirmadas.json` preservam números calculados durante a busca de posições e distâncias. O conjunto de 220 sequências não foi integralmente validado contra o edital. Posteriormente foram identificadas 20 sequências com cruzamentos sem as retas exigidas. As outras 200 não receberam aprovação integral. Os índices globais desse conjunto foram retirados como critério de aprovação/reprovação para o TRIF.

Algumas alternativas consideradas nesses arquivos reduzem muito a distância da barra, mudam o contorno ou a quantidade de sensores, ou movem apenas o esquerdo. Elas não representam o conjunto final de restrições: uma PCB, um QRE por lado, abas iguais, posições espelhadas e vão próximo do EVA-RT.

## Imagem antiga de 432 passagens

`resultado_432_passagens_nao_reproduzido.png` é a imagem fornecida pelo usuário. Ela cita L = 67 e 70 mm e um script `ferramentas/preview/marcas_sim.py`. A fonte exata desse script não foi localizada nesta investigação. Não foi possível reproduzir nem validar aqueles 432 resultados. A imagem não corresponde ao L ≈ 92,8 mm estimado para o mesmo vão base–barra do EVA-RT na base SATURN com V1.

## Correções de interpretação

- A referência aproximada de L = 100 mm do desenho original não é o mesmo que preservar o vão de aproximadamente 35 mm na geometria SATURN/V1.
- A primeira versão do circuito de 19 marcas tinha uma sobreposição entre marcações. Ela foi substituída pela revisão 2; os arquivos de `03_simulacoes/` usam a revisão corrigida.
- Intersectar uma fita não equivale a passar pelo seu centro nem a comprovar leitura elétrica.
- Uma falha em uma trajetória idealizada não demonstra falha inevitável para qualquer controlador.
- Uma contagem favorável em uma pista não aprova a montagem para todos os percursos permitidos.

O documento principal na raiz desta pasta de estudo contém o estado consolidado.
