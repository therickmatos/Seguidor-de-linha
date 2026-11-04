# Layout final da placa (transferência térmica)

_19/10/2026. Baseado na disposição do Erick (18/10, 23h44), com ajustes para fechar 0 jumpers e plano de GND inteiro. Arquivos: `Galileia_cobre_1x1.pdf` (arte), `Galileia_posicionamento.png`, `Galileia_referencia.dxf`. Substitui a tabela "Layout da placa" do HARDWARE.md._

- Face simples, 0 jumpers. Trilhas ≥ 1,0 mm; folga mínima real 0,6 mm; resto em plano de GND.
- XT60+ → ESC+ por faixa de cobre de 4 mm; ESC− ao lado do XT60−.
- Cobre a 0,6 mm do furo de 38 mm (raio 19,6).
- Mapa de pinos do ESP igual ao esquemático Galiléia3.
- GND dos pinos 8 e 9 da TB6612 e o OUT− do Mini-360 chegam pela ligação interna dos módulos (pino 3 da TB e IN− do Mini estão no plano).
- Pads do motor esquerdo trocados (M_ESQ_A embaixo, M_ESQ_B em cima): só inverte o sentido; corrigir no firmware.
- Caminho de retorno dos motores pelo plano: gargalo ~1,8 mm de largura (ok para N20).
- Arte: imprimir a 100%, sem espelhar; "GALILEIA" deve ficar legível no cobre depois da transferência.

| Ref | x | y | rot (convenção do layout) | Nota |
|---|---|---|---|---|
| U1 ESP32-C3 | −44,4 | 12,34 | 90 | |
| U5 barra | 0,0 | 39,6 | 0 | 3V3 à esquerda |
| U2 TB6612 | 43,9 | 0,76 | 180 | pino 1 (VM) embaixo à direita |
| U4 XT60 | 41,35 | 29,0 | −90 | pino 1 (VBAT) embaixo |
| ESC+ | 34,8 | 27,0 | – | |
| ESC− | 34,8 | 33,15 | – | |
| U3 Mini-360 | 57,56 | 25,5 | 0 | OUT+ em cima à esquerda, IN+ em cima à direita |
| C3 | 57,35 | 13,64 | −90 | + em cima |
| SW1 | 57,65 | −0,3 | −90 | pino 1 (VSW) em cima |
| U6 KY-022 | −59,13 | 33,07 | 0 | |
| C2 | −51,7 | 24,0 | 180 | pino 1 (3V3) à direita |
| R3 | −49,3 | 28,06 | 0 | |
| SW2 | −47,9 | −1,0 | 180 | |
| U7 sinal ESC | −54,9 | −4,6 | 0 | |
| R4 | −47,4 | −7,4 | 0 | |
| U8 botão | −45,0 | −27,5 | −90 | pino 1 (BTN) em cima à direita, pino 4 (GND) embaixo à esquerda |

Ajustes em relação à disposição do Erick e motivo:
- Botão no canto inferior esquerdo (em vez de perto do anel): na posição original, a trilha do botão fechava o GND em volta da turbina numa ilha.
- Mini-360 girado 180° e 3,7 mm mais baixo, XT60 com VBAT embaixo, ESC+ embaixo e ESC− em cima: evita o cruzamento entre VBAT, VSW e 3V3.
- SW1 1,5 mm mais baixo: alarga o caminho de GND entre a chave e a borda.
- C2 ao lado do 3V3 do ESP: ao lado do KY ele fechava o GND do canto superior esquerdo.
- SW2, U7 e R4 na disposição horizontal debaixo do ESP.
