# Teste do chassi baixo com dois sensores por lado

No [simulador](simulador.html), selecione a configuração **Chassi baixo · 2 sensores por lado · furos 60 mm** (desde 11/11/2026 ele abre com a v3 atual em L 70 mm; veja a [análise do firmware e da geometria](../07_firmware_e_geometria/README.md)). São quatro sensores de marcas ao todo, além da barra frontal que acompanha a linha.

## Como testar

1. Baixe o HTML e abra-o no Chrome ou Edge. A página de código do GitHub não executa o simulador.
2. Escolha **TRIF 2025**, **TRIF 2024 · sentido corrigido** ou **Pista de teste do EVA-RT** em **Pista de teste**.
3. Clique em **Simular percurso** para animar a passagem. Use **Próxima marca**, **Inspecionar marca** e **Ver detalhe** para examinar cada fita.
4. Observe os totais separados de esquerda e direita. E1/D1 identificam os sensores internos; E2/D2, os externos. As trajetórias externas são tracejadas.
5. Para comparar, selecione uma configuração original de um sensor por lado. Selecionar novamente o chassi baixo restaura suas medidas iniciais.

Cada fita é contada apenas uma vez, mesmo que os dois sensores daquele lado a intersectem. Isso é uma regra do cálculo geométrico; a lógica equivalente ainda precisa ser implementada e testada no firmware.

## Geometria usada

Coordenadas locais em milímetros, com a mesma origem do projeto v3 e Y positivo para a frente:

| Elemento | Valor |
|---|---:|
| Sensores internos E1 / D1 | X = −52,25 / +52,25; Y = 20 |
| Sensores externos E2 / D2 | X = −77,75 / +77,75; Y = 20 |
| Separação entre sensores do mesmo lado | 25,5 |
| Distância entre os furos da base e da barra | 60 |
| L: eixo das rodas até o ponto central da barra | 103,974 |
| Largura × comprimento longitudinal da base | 164,7 × 58,6 |
| Aumento em cada ponta lateral sobre o v3 | 8,25 |
| Frente das abas / frente original da base | Y = 24,6 / 25,6 |

O contorno deriva do [projeto v3 original](../01_projeto/ProPrj_RUSH%20-%20SATURN%20-%20v3_2026-11-09.epro). Mantém os 12 furos de fixação, a abertura central e os dois rasgos, além das regiões |X| ≤ 45 mm e Y ≤ 0. A barra frontal e as posições das rodas mantêm a geometria usada pelo simulador original. O arquivo de PCB permanece intacto.

Ao personalizar X/Y, o contorno permanece fixo. O campo X move os sensores internos; os externos continuam a 77,75 mm do centro. O simulador informa se algum centro fica fora da placa. Isso não verifica o espaço para encapsulamentos, fixações, trilhas ou componentes.

## Resultados nas pistas TRIF 2025 e TRIF 2024

Barra centrada, sem desvio fixo:

| Furos | L | 2025 nominal | 2025 região comum | 2024 nominal | 2024 região comum |
|---:|---:|---:|---:|---:|---:|
| 60 mm | 103,974 mm | 33/33 | 33/33 | 35/35 | 35/35 |
| 65 mm | 108,975 mm | 33/33 | 33/33 | 35/35 | 34/35 |
| 70 mm | 113,975 mm | 33/33 | 30/33 | 34/35 | 33/35 |

Na pista de teste do EVA-RT (modelo aproximado de um quadro de vídeo, ver [Pistas e resultados](02_pistas_e_resultados.md)), o chassi baixo intersectou 25/26 marcas a 60, 65 e 70 mm (região comum 25, 24 e 23/26).

A 60 mm, são **31/31 marcas esquerdas e 2/2 direitas em 2025** e **33/33 esquerdas e 2/2 direitas em 2024**. Todas também cruzam a região comum. O teste inicia em 60 mm; para comparar 65 ou 70 mm, altere L conforme a tabela.

Os resultados foram calculados em Python com passo de 0,25 mm e interseção de segmentos com os retângulos das marcas. A interface usa passo de 0,5 mm; o teste automatizado compara o resultado de cada marca, nominal e comum, nas combinações acima (três pistas × três distâncias). Veja os [dados completos](dados/resultados_duas_pistas.json) e as [instruções para reproduzir](03_metodologia_e_testes.md#reprodução).

## Alcance do ensaio

As pistas são reconstruções estimadas a partir das referências, incluindo a revisão de 2025 disponível no repositório. As marcas seguem o modelo nominal do estudo e podem diferir das fitas reais.

O resultado demonstra interseções dos centros dos sensores com as marcas dos modelos. A região comum é um retângulo interno conservador, não uma probabilidade de leitura. Não foram simulados sinal óptico, área sensível, altura, eletrônica, PID, derrapagem, velocidade ou falsos disparos. Os sensores internos podem cruzar a linha principal em curvas; a contagem de acertos não valida a distinção entre essa linha e uma marca lateral.

O caminho correto no cruzamento é imposto. A fabricação do novo contorno, a instalação dos quatro QRE e a integração elétrica ainda exigem projeto e ensaio físico.

Baseado no RUSH/SATURN v3 e no EVA-RT, EXOTIC TEAM MX; código derivado sob [AGPL-3.0](../LICENSE).
