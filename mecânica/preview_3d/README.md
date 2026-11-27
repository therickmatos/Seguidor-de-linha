# Preview 3D do RUSH - SATURN v12

Modelo 3D do robô montado, para mostrar o projeto (professor, divulgação). **Não substitui a conferência de `mecânica/conferencia/`**: as medidas e folgas continuam valendo de lá.

| Arquivo | O que é |
|---|---|
| `rush_saturn_v12.glb` | modelo completo (glTF binário, em metros, +y para cima). Abre no Visualizador 3D do Windows, no Blender ou em qualquer visualizador de glTF |
| `index.html` + `pecas.json` | visualizador interativo: girar, vistas, lista de peças, vista explodida e cores por material. Precisa de um servidor local (`python3 -m http.server` dentro desta pasta e abrir `http://localhost:8000`); aberto direto do disco, o navegador bloqueia a leitura do `.glb` |
| `vista_*.jpg` | figuras tiradas do visualizador |
| `rush_saturn_4_vistas.jpg` | as 4 vistas numa imagem só, sem textos (perspectiva, explodida por material, cima e baixo) |

## O que entra
- Base v12 e barra V1 com a textura tirada do Gerber (cobre, máscara verde, serigrafia, furos). A cor da máscara é a padrão da JLC (o pedido não especifica outra).
- Peças impressas e ferragens nas posições do `conferir_montagem.py` (barra a 63,14 mm entre furos, L = 107,1 mm), pista 4,0 mm abaixo da face de cima da base.
- Caixas de redução, motores 1020, pinhões 11T, rodas (aro + engrenagem 64T versão 2 + pneu Ø22 × 15), carcaça, suporte e hélice da ventoinha, vareta traseira com os apoios da bateria e o XT30 macho da placa (J1).
- Componentes das duas placas com os modelos 3D da biblioteca oficial do KiCad (STEP). QRE1113GR, botões e XT30 não existem lá e foram desenhados no script. Cada componente é encaixado nos pads pelo próprio script (giro e deslocamento que põem os terminais nas aberturas da máscara).
- Fios dos motores, desenhados à mão. O fundo é preto liso (sem a linha da pista), na altura da pista.

## Ilustrativo (não decidido no projeto)
- **Bateria:** fica fora do preview, porque a posição dela ainda está em aberto (`mecânica/README.md`). Para mostrar, `MOSTRAR_BATERIA = True` em `modelo_3d.py` (apoiada nos dois `battery_holder` sobre a vareta traseira, atrás da carcaça, com o XT30 fêmea encaixado na J1 e os fios até ela).
- Cores das peças impressas, cabo misto da J2 à barra (não modelado) e módulo Bluetooth (não modelado).

## Refazer
Na raiz do repositório, com `pip install -r ferramentas/pecas_3d/requisitos.txt`:
```bash
python3 ferramentas/pecas_3d/modelo_3d.py
```
Na primeira vez ele baixa os STEP do KiCad (gitlab.com/kicad/libraries/kicad-packages3D) para `ferramentas/pecas_3d/modelos_kicad/` (fora do git).

Créditos: STL do EVA-RT © EXOTIC TEAM MX (AGPL-3.0); modelos 3D do KiCad sob CC-BY-SA 4.0 com a exceção de uso em projetos.
