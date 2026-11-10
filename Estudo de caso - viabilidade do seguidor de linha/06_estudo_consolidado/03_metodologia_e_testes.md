# Método e próximos testes

## Modelo usado

O robô é um corpo rígido com eixo sem escorregamento lateral. O ponto virtual central da barra segue a linha ou uma trajetória de desvio fixo; a orientação é integrada ao longo do percurso. O centro do QRE é tratado como um ponto e cada marca como um retângulo. No cruzamento, a trajetória é definida previamente.

Uma interseção significa apenas que esse ponto geométrico cruzou o retângulo. Não foram simulados área óptica, altura, refletância, limiar, ADC, interferência luminosa, atrasos, ruído, PID, motor, bateria, força normal, derrapagem, frenagem, nem tempo de volta. Um erro fixo da barra não é uma simulação de controle.

A leitura de uma marca esquerda pode ser útil para mapear transições e decidir velocidade, mas o regulamento não torna sua identificação, por si só, uma condição explícita de volta válida. O robô deve seguir o percurso e parar automaticamente, sobre a linha e na área de partida-chegada, por pelo menos dois segundos. Perder uma marca de curva pode prejudicar a estratégia escolhida sem, isoladamente, invalidar a volta.

## Antes e depois da montagem

1. Medir a distância entre furos, o vão e L na montagem real. Se houver suporte ajustável, comparar 60 e 63,14 mm entre furos sem presumir que o mesmo ajuste do PID servirá às duas configurações.
2. Calibrar cada QRE sobre fita e fundo representativos, na altura de trabalho. Registrar o sinal de cada lado, escolher limiares com histerese e verificar se a amostragem captura os pulsos na velocidade de teste.
3. Testar marcas no início, no fim e na transição de curvas dos dois sentidos. Registrar separadamente as marcas detectadas, a passagem pelo cruzamento e sinais produzidos pela linha principal.
4. Validar partida, chegada, desaceleração e parada na área correta; impedir contagens repetidas da mesma marca e conferir a lógica em cruzamentos. Ajustar regras de rearme com dados de pista, sem ignorar marcas próximas.
5. Só então aumentar a velocidade e comparar estabilidade e tempo, repetindo sob variação razoável de alinhamento, altura e superfície. A distância entre furos, sozinha, não determina o desempenho.

O estudo não implementou firmware, não alterou CAD nem Gerbers e não inspecionou trilhas. Não foram realizados testes físicos. O campo óptico real pode gerar uma leitura quando o centro não cruza a marca, mas também pode falhar apesar de uma interseção muito curta.

## Reprodução

O [HTML](simulador.html) é autocontido e abre sem instalar pacotes. Para reconstruí-lo ou refazer os ensaios, com Python instalado:

```sh
python -m pip install -r codigo/requisitos.txt
python codigo/gerar_trif_2024_2025.py
python codigo/pista_c_regulamentar.py
python codigo/validar_duas_pistas.py
```

Execute os comandos a partir deste diretório dentro da pasta de estudo: eles reutilizam os módulos arquivados em `../05_codigo/originais/` e as cotas visuais em `../03_simulacoes/`. Os resultados vão para `dados/`. O gerador grava novamente `simulador.html`. A verificação geométrica não valida hardware, e a animação usa velocidade arbitrária.
