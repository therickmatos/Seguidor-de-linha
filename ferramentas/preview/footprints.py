"""Biblioteca de footprints do preview de posicionamento da placa base do seguidor.

Clone do EVA-RT (EXOTIC TEAM MX, AGPL-3.0). Este modulo so descreve geometria
(pads, corpo, cortesia) e a ligacao de cada pad ao pino do simbolo do esquematico.

Convencoes (valem para tudo):
- Unidades em mm. Origem (0,0) = centro do footprint. +x = direita, +y = para cima.
- Os footprints estao no referencial do componente visto DE CIMA, montado na face TOP
  (rotacao 0). Para componente na face BOTTOM use lado="BOTTOM" em pads_absolutos:
  o x e espelhado antes de girar (x -> -x), o que da a "vista atraves da placa"
  (mesmas coordenadas x,y da placa, sem espelhar na figura).
- Rotacao em graus, anti-horaria.
- "pino" = identificador do pad no footprint. "rede_pino" = pino do SIMBOLO do esquematico
  (formato REF.pino do REDES.md). rede_pino None = pad sem pino no simbolo
  (GND de carcaca, NC, furo de fixacao).
- "corpo" e "cortesia" sao [w, h] (mm). Ficam centrados em "corpo_xy" e "cortesia_xy"
  (campos extras; default (0,0)). Quando o corpo nao e simetrico em relacao aos pads
  (barra 90 graus, XT30PW, DPAK) o centro e diferente da origem.
- "cortesia" = caixa do corpo + pads + 0,25 mm de folga em cada lado.
- Para os componentes da placa do EVA-RT que estao na face BOTTOM (S0, S1, J5 e, no EVA-RT,
  tambem R6, R7, R20, R21, R30, R31) use o lado de LADO_PADRAO_REF ou o lado do CSV original.

Fontes das medidas (resumo; detalhes em "obs" de cada footprint):
- EVA-RT (.eprj decodificado, valores em mil x 0,0254): TQFP-32, radial D6,3, tantalo 3216,
  botao B3U, pads dos motores, ICSP, asas (pads 0,75 x 3,0), posicoes e redes reais.
- KiCad footprint library (github KiCad/kicad-footprints): 0603, SOT-23, SOD-123, DPAK
  (TO-252-3), HTSSOP-16 com EP, HC-49/S SMD, 3225 de 4 pads, barra 1x5 90 graus, botao 6x6.
- AMASS XT30 (catalogo oficial, pagina 15/16, figura "Mounting hole diagram"): XT30PW-M.
- QRE1113GR: pads medidos no Gerber inferior EVA-RT; pinos conferidos no datasheet onsemi.
"""

import math

SAME = "__igual__"  # rede_pino igual ao pino (default)

LADO_PADRAO_REF = {"J5": "BOTTOM", "S0": "BOTTOM", "S1": "BOTTOM"}


def _pad(pino, x, y, w, h, forma="rect", furo=None, rede=SAME):
    r = pino if rede == SAME else rede
    return {
        "pino": str(pino),
        "x": float(x),
        "y": float(y),
        "w": float(w),
        "h": float(h),
        "forma": forma,
        "furo": None if furo is None else float(furo),
        "rede_pino": None if r is None else str(r),
    }


def _caixa_pads_corpo(pads, corpo, corpo_xy):
    xs, ys = [], []
    for p in pads:
        xs += [p["x"] - p["w"] / 2, p["x"] + p["w"] / 2]
        ys += [p["y"] - p["h"] / 2, p["y"] + p["h"] / 2]
    if corpo[0] > 0 and corpo[1] > 0:
        cx, cy = corpo_xy
        xs += [cx - corpo[0] / 2, cx + corpo[0] / 2]
        ys += [cy - corpo[1] / 2, cy + corpo[1] / 2]
    return min(xs), max(xs), min(ys), max(ys)


def _fp(pads, corpo, altura_mm, tht, obs, corpo_xy=(0.0, 0.0)):
    x0, x1, y0, y1 = _caixa_pads_corpo(pads, corpo, corpo_xy)
    x0, x1, y0, y1 = x0 - 0.25, x1 + 0.25, y0 - 0.25, y1 + 0.25
    cortesia = [round(x1 - x0, 3), round(y1 - y0, 3)]
    cortesia_xy = [round((x0 + x1) / 2, 4), round((y0 + y1) / 2, 4)]
    return {
        "pads": pads,
        "corpo": [float(corpo[0]), float(corpo[1])],
        "corpo_xy": [float(corpo_xy[0]), float(corpo_xy[1])],
        "cortesia": cortesia,
        "cortesia_xy": cortesia_xy,
        "altura_mm": float(altura_mm),
        "tht": bool(tht),
        "obs": obs,
    }


FOOTPRINTS = {}

# ---------------------------------------------------------------- passivos e LEDs
_PADS_0603 = [_pad("1", -0.825, 0, 0.8, 0.95), _pad("2", 0.825, 0, 0.8, 0.95)]
_OBS_0603 = (
    "Chip 0603 (1608 metrico). Pads 0,80 x 0,95 em x = +-0,825 (KiCad R_0603_1608Metric, "
    "IPC-7351). Corpo 1,6 x 0,8 (padrao). Pino 1 = pad da esquerda (-x)."
)
FOOTPRINTS["R0603"] = _fp(
    [dict(p) for p in _PADS_0603], (1.6, 0.8), 0.55, False,
    _OBS_0603 + " Resistor; altura estimada 0,55.")
FOOTPRINTS["C0603"] = _fp(
    [dict(p) for p in _PADS_0603], (1.6, 0.8), 0.8, False,
    _OBS_0603 + " Capacitor ceramico; altura estimada 0,8 (varia com o modelo).")
FOOTPRINTS["LED0603"] = _fp(
    [dict(p) for p in _PADS_0603], (1.6, 0.8), 0.8, False,
    _OBS_0603 + " LED: pino 1 = K (catodo), pino 2 = A (anodo), como no REDES.md. "
    "Altura estimada 0,8 (lente).")

FOOTPRINTS["C_RAD_D6.3_P2.5"] = _fp(
    [_pad("1", -1.25, 0, 2.0, 2.0, "round", 1.0),
     _pad("2", 1.25, 0, 2.0, 2.0, "round", 1.0)],
    (6.3, 6.3), 11.2, True,
    "Eletrolitico radial D6,3 passo 2,5 (BOM). Pads Ø2,0 com furo Ø1,0 "
    "(EVA-RT: cap-th_bd6.3-p2.50-d1.0, EasyEDA, pads medidos em +-1,27; aqui +-1,25 "
    "pelo passo 2,5 da BOM). Pino 1 = + (-x). Corpo redondo Ø6,3 desenhado como quadrado. "
    "Altura 11,2 (pedido do projeto).")

FOOTPRINTS["C_TANT_3216_A"] = _fp(
    [_pad("1", -1.449, 0, 1.0, 1.296), _pad("2", 1.449, 0, 1.0, 1.296)],
    (3.2, 1.6), 1.6, False,
    "Tantalo 3216 caso A (BOM, C5 47uF). Pads 1,0 x 1,30 em +-1,449: medidos no EVA-RT "
    "(EasyEDA cap-smd_l3.2-w1.6-rd, e328, mesma peca do C5). Pino 1 = + (-x). "
    "Corpo 3,2 x 1,6 e altura 1,6 (padrao caso A).")

# 07/11: C5 = 47 uF ceramico 1210 (o Erick achou em 1210). KiCad C_1210_3225Metric: pads 1,15 x 2,7 em +-1,475.
FOOTPRINTS["C1210"] = _fp(
    [_pad("1", -1.475, 0, 1.15, 2.7), _pad("2", 1.475, 0, 1.15, 2.7)],
    (3.2, 2.5), 2.5, False,
    "Capacitor ceramico 1210 (C5, 47 uF). Pads 1,15 x 2,7 em +-1,475 (KiCad C_1210_3225Metric). Corpo 3,2 x 2,5.")

# ---------------------------------------------------------------- semicondutores
FOOTPRINTS["SOD123"] = _fp(
    [_pad("1", -1.65, 0, 0.9, 1.2), _pad("2", 1.65, 0, 0.9, 1.2)],
    (2.65, 1.35), 1.1, False,
    "SOD-123 (D1 1N5819/B5819W). Pads 0,9 x 1,2 em +-1,65: KiCad D_SOD-123 (IPC). "
    "Pino 1 = K (catodo, -x), pino 2 = A (+x). Corpo 2,65 x 1,35 e altura 1,1 padrao. "
    "Datasheet do B5819W nao conferido.")

FOOTPRINTS["SOT23_AO3400A"] = _fp(
    [_pad("1", -1.0, 0.95, 0.9, 0.8),
     _pad("2", -1.0, -0.95, 0.9, 0.8),
     _pad("3", 1.0, 0.0, 0.9, 0.8)],
    (2.9, 1.3), 1.1, False,
    "SOT-23 (Q1 AO3400A: 1 = G, 2 = S, 3 = D). KiCad Package_TO_SOT_SMD:SOT-23 "
    "(pads 0,9 x 0,8): a biblioteca KiCad usa y para baixo; aqui convertido para y para cima. "
    "Pino 1 (G) em (-1,0; +0,95) = canto superior-esquerdo; pino 2 (S) em (-1,0; -0,95); "
    "pino 3 (D) em (+1,0; 0). Corpo 2,9 x 1,3. CONFERIR a orientacao no datasheet do AO3400A "
    "(nao acessivel).")

# ---------------------------------------------------------------- circuitos integrados
_pads_tqfp = []
for _i in range(8):  # borda inferior, pinos 1..8 da esquerda para a direita
    _pads_tqfp.append(_pad(_i + 1, -2.8 + 0.8 * _i, -4.269, 0.45, 1.25))
for _i in range(8):  # borda direita, pinos 9..16 de baixo para cima
    _pads_tqfp.append(_pad(9 + _i, 4.282, -2.8 + 0.8 * _i, 1.25, 0.45))
for _i in range(8):  # borda superior, pinos 17..24 da direita para a esquerda
    _pads_tqfp.append(_pad(17 + _i, 2.8 - 0.8 * _i, 4.269, 0.45, 1.25))
for _i in range(8):  # borda esquerda, pinos 25..32 de cima para baixo
    _pads_tqfp.append(_pad(25 + _i, -4.281, 2.8 - 0.8 * _i, 1.2, 0.45))
FOOTPRINTS["TQFP32_7x7_P0.8"] = _fp(
    _pads_tqfp, (7.0, 7.0), 1.2, False,
    "TQFP-32 7x7 passo 0,8 (U1 ATmega328P-AU). Medidas do footprint EasyEDA do EVA-RT "
    "(tqfp-32_l7.0-w7.0-p0.80-ls9.0-bl), lidas do .eprj: pads 0,45 de largura; comprimento "
    "1,25 nas bordas superior/inferior e 1,25 (direita) / 1,20 (esquerda) como no EasyEDA. "
    "Pino 1 = primeiro pad da borda inferior, perto do canto inferior-esquerdo; numeracao "
    "anti-horaria vista de cima. CONFERIR a marca de pino 1 do chip (ponto/chanfro) antes de "
    "fechar a rotacao. Altura 1,2 (pacote).")

_pads_htssop = []
for _i in range(8):  # pinos 1..8: coluna esquerda, de cima para baixo
    _pads_htssop.append(_pad(_i + 1, -2.775, 2.275 - 0.65 * _i, 1.05, 0.45))
for _i in range(8):  # pinos 9..16: coluna direita, de baixo para cima
    _pads_htssop.append(_pad(9 + _i, 2.775, -2.275 + 0.65 * _i, 1.05, 0.45))
_pads_htssop.append(_pad(17, 0.0, 0.0, 3.4, 5.0, "rect", None, rede="17"))  # pad termico
FOOTPRINTS["HTSSOP16_PWP_DRV8874"] = _fp(
    _pads_htssop, (4.4, 5.0), 1.2, False,
    "HTSSOP-16 com pad termico (U2/U3 DRV8874PWPR). KiCad HTSSOP-16-1EP_4.4x5mm_P0.65mm_"
    "EP3.4x5mm: pads 1,05 x 0,45, passo 0,65, colunas em x = +-2,775; pad 17 (= U2.17 PAD, "
    "GND) 3,4 x 5,0 em (0;0). Pino 1 no canto superior-esquerdo, 1..8 descendo a esquerda, "
    "9..16 subindo a direita (anti-horario). PENDENTE: o datasheet TI nao foi acessivel; o "
    "tamanho do pad termico (3,4 x 5,0 da biblioteca KiCad) precisa de conferencia com a "
    "tabela D2 x E2 do datasheet (o briefing esperava ~3,4 x 3,4). Sem vias termicas.")

# ---------------------------------------------------------------- regulador (DPAK)
FOOTPRINTS["DPAK_TO252_3"] = _fp(
    [_pad("1", -2.28, -4.2, 1.2, 2.2),
     _pad("2", 0.0, 2.1, 5.8, 6.4, "rect", None),  # aba = pino 2 (GND)
     _pad("3", 2.28, -4.2, 1.2, 2.2)],
    (6.1, 6.6), 2.3, False,
    "TO-252 (DPAK) 3 terminais (U5 78M05: 1 = VI, 2 = GND na aba, 3 = VO). KiCad "
    "Package_TO_SOT_SMD:TO-252-3_TabPin2 girado 90 graus (terminais embaixo, aba em cima). "
    "Terminais 1,2 x 2,2 em (-2,28; -4,2) e (+2,28; -4,2); aba 5,8 x 6,4 em (0; +2,1) = pino 2. "
    "O terminal central (pino 2) e cortado na maioria dos 78M05: nao modelado. Se o componente "
    "tiver o pino central, acrescentar pad 1,2 x 2,2 em (0; -4,2). Corpo 6,1 x 6,6 estimado. "
    "Conferir 1 = VI, 2 = GND, 3 = VO no datasheet do 78M05.")

# ---------------------------------------------------------------- cristal
FOOTPRINTS["CRISTAL_HC49S_SMD"] = _fp(
    [_pad("1", -4.25, 0, 4.5, 2.0), _pad("2", 4.25, 0, 4.5, 2.0)],
    (11.4, 4.7), 3.5, False,
    "Cristal HC-49/S SMD 2 terminais (X1 16 MHz, alternativa do BOM). KiCad "
    "Crystal_SMD_HC49-SD: pads 4,5 x 2,0 em +-4,25; corpo 11,4 x 4,7 (F.Fab). Pino 1 = XTAL1, "
    "pino 2 = XTAL2 (sem pinos de GND). Altura 3,5 estimada. Default de X1: por ser o maior, "
    "serve de caso conservador para colisao.")

# 07/11: cristal TXC 7A-16.000MAAJ-T (16 MHz, CL 18 pF, ESR 50, +-30 ppm; LCSC C2450102), 5,0 x 3,2 x 1,2,
# 2 pads. Padrao sugerido no datasheet TXC 7A: pads 1,7 x 2,4 com 2,0 entre eles (centros em +-1,85).
FOOTPRINTS["XTAL_TXC_7A_5032_2P"] = _fp(
    [_pad("1", -1.85, 0, 1.7, 2.4), _pad("2", 1.85, 0, 1.7, 2.4)],
    (5.0, 3.2), 1.2, False,
    "Cristal TXC 7A 5032 de 2 pads (X1). Pads 1,7 x 2,4 em +-1,85 (datasheet TXC 7A). Pad 1 = XTAL1, pad 2 = XTAL2.")

FOOTPRINTS["CRISTAL_3225_4P"] = _fp(
    [_pad("1", -1.1, -0.85, 1.4, 1.2, rede="1"),
     _pad("2", 1.1, -0.85, 1.4, 1.2, rede=None),
     _pad("3", 1.1, 0.85, 1.4, 1.2, rede="2"),
     _pad("4", -1.1, 0.85, 1.4, 1.2, rede=None)],
    (3.2, 2.5), 0.8, False,
    "Cristal 3225 de 4 pads (alternativa do BOM). KiCad Crystal_SMD_3225-4Pin_3.2x2.5mm: "
    "pads 1,4 x 1,2 em (+-1,1; +-0,85) (y convertido de y para baixo). Pads 1 e 3 (diagonais) = "
    "cristal: pad 1 -> X1.1 (XTAL1), pad 3 -> X1.2 (XTAL2). Pads 2 e 4 = carcaca/GND ou NC, "
    "rede_pino None. Corpo 3,2 x 2,5 (padrao). Altura 0,8 estimada.")

# ---------------------------------------------------------------- conectores
FOOTPRINTS["XT30PW_M_PCB"] = _fp(
    [_pad("1", -2.5, 0, 2.8, 2.8, "round", 1.7),
     _pad("2", 2.5, 0, 2.8, 2.8, "round", 1.7),
     _pad("P1", -5.5, 5.0, 1.6, 1.6, "round", 1.0, rede=None),
     _pad("P2", 5.5, 5.0, 1.6, 1.6, "round", 1.0, rede=None)],
    (14.9, 9.9), 13.3, True,
    "XT30PW-M (AMASS, macho de placa 90 graus; J1 bateria). Medidas da figura 'Mounting hole "
    "diagram' do catalogo AMASS (pag. 15/16, baixado): 2 furos Ø1,7 em (-2,5; 0) e (+2,5; 0) "
    "(distancia 5,00 entre os contatos) = pino 1 (+) e pino 2 (-); 2 furos Ø1,0 (postes sem "
    "sinal, anel 1,6 suposto) em (-5,5; +5,0) e (+5,5; +5,0) (distancia 11,00), medidas pela "
    "figura em escala (linha 5,00 acima). Corpo 14,90 x 9,90 (cotas da vista lateral/frontal), "
    "centro em (0; +2,5) = centro dos 4 furos (ESTIMATIVA). Altura 13,30 = maior cota vertical "
    "(incerta). CONFERIR com o desenho 3D/datasheet: lado do corpo (postes em +y), polaridade "
    "(qual contato e +) e medidas do corpo.", corpo_xy=(0.0, 2.5))

FOOTPRINTS["XT30_RABICHO"] = _fp(
    [_pad("1", -2.5, 0, 3.0, 3.0, "round", 2.0),
     _pad("2", 2.5, 0, 3.0, 3.0, "round", 2.0)],
    (0.0, 0.0), 0.0, True,
    "Rabicho XT30 (alternativa a J1): 2 furos Ø2,0 com pad Ø3,0 para soldar fios grossos. "
    "Passo 5,0 (igual aos contatos do XT30, escolha sem norma). Pino 1 = + (-x). Sem corpo.")

FOOTPRINTS["XT30_VERTICAL_M_PROPOSTA"] = _fp(
    [_pad("1", -2.5, 0, 3.9, 3.9, "round", 2.5),
     _pad("2", 2.5, 0, 3.9, 3.9, "round", 2.5)],
    (10.214, 5.2), 10.2, True,
    "XT30 macho: imagem fornecida pelo usuario indica corpo 10,214 x 5,200 mm e passo "
    "5,000 mm. Pino 1 = + no lado reto (-x); pino 2 = - na extremidade arredondada. "
    "A imagem nao cota diametros: pads Ø3,9 e furos Ø2,5 sao estimados pela proporcao "
    "com o passo de 5 mm; a altura tambem e estimada. Conferir a peca antes de fabricar.")

_pads_bar8 = []
for _i in range(8):
    _pads_bar8.append(_pad(_i + 1, -8.89 + 2.54 * _i, 0, 1.7, 1.7,
                           "rect" if _i == 0 else "round", 1.0))
FOOTPRINTS["HDR_1x08_P2.54"] = _fp(
    _pads_bar8, (20.32, 2.54), 8.5, True,
    "Barra macho reta 1x8 passo 2,54 (J2 sensores). Pads Ø1,7 (pino 1 quadrado) com furo Ø1,0 "
    "(padrao KiCad PinHeader; pads em +-8,89 e borda em +-9,74, como no briefing). Corpo 20,32 "
    "x 2,54 e altura 8,5 (2,5 de corpo + 6,0 de pino). Pino 1 = -x. Origem no centro da fileira "
    "(y = 0). Pinos 1..8 = +5V, GND, NC (J2.3), A4, A3, A2, A1, A0.")

FOOTPRINTS["HDR_RA_1x05_P2.54"] = _fp(
    [_pad(_i + 1, 5.08 - 2.54 * _i, 0, 1.7, 1.7, "rect" if _i == 0 else "round", 1.0)
     for _i in range(5)],
    (12.7, 2.54), 2.54, True,
    "Barra macho 1x5 passo 2,54 a 90 graus (J3 gravacao). Base: KiCad "
    "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Horizontal, girado para o corpo ficar em "
    "-y e as pontas irem para -y. Furos Ø1,0 com pad 1,7 em y = 0; corpo 12,7 x 2,54 entre y = "
    "-1,50 e -4,04 (centro em y = -2,77, dado por corpo_xy); distancia furo -> face do corpo = "
    "1,50 mm; pontas dos pinos dobrados ate y = -10,04 (6,0 mm alem do corpo, altura ~2,5 mm). "
    "Pino 1 (+5V) em x = +5,08 (ordem invertida em relacao ao J2, por causa da rotacao "
    "fisica). Pinos 1..5 = +5V, GND, RX, TX, DTR. Cortesia calculada sem as pontas.",
    corpo_xy=(0.0, -2.77))

_pads_f6 = []
for _i in range(6):
    _pads_f6.append(_pad(_i + 1, 0, -6.35 + 2.54 * _i, 1.7, 1.7,
                         "rect" if _i == 0 else "round", 1.0))
FOOTPRINTS["HDR_F_1x06_P2.54"] = _fp(
    _pads_f6, (2.54, 15.24), 8.5, True,
    "Barra femea 1x6 passo 2,54 (J4 Bluetooth, ordem HC-05). Pads Ø1,7 com furo Ø1,0 (padrao). "
    "Disposta na vertical (y): pino 1 em y = -6,35 e pino 6 em y = +6,35; origem no centro. "
    "Corpo 2,54 x 15,24 e altura 8,5 (padrao de socket). Pinos 1 e 6 sem ligacao (NC); "
    "2 = BT_RXD, 3 = BT_TXD, 4 = GND, 5 = +5V.")

_icsp_board = {  # offsets medidos no EVA-RT (x,y) na placa, origem = centro dos 6 pads
    "1": (1.27, 2.54),   # MISO (D12) em x 36,51 / y -8,36
    "2": (-1.27, 2.54),  # +5V em x 33,97 / y -8,36
    "3": (1.27, 0.0),    # SCK (D13) em x 36,51 / y -10,90
    "4": (-1.27, 0.0),   # MOSI (D11) em x 33,97 / y -10,90
    "5": (1.27, -2.54),  # RESET em x 36,51 / y -13,44
    "6": (-1.27, -2.54), # GND em x 33,97 / y -13,44
}
_pads_icsp = []
for _pino, (_xb, _yb) in _icsp_board.items():
    # biblioteca = vista de cima do componente: x espelhado em relacao a placa (lado BOTTOM)
    _pads_icsp.append(_pad(_pino, -_xb, _yb, 1.8, 1.8, "round"))
FOOTPRINTS["ICSP_6P_SMD_BOT"] = _fp(
    _pads_icsp, (0.0, 0.0), 0.0, False,
    "ICSP: 6 pads SMD Ø1,8 na face BOTTOM (J5, grade 2,54), so pads (sem corpo). Medidas do "
    "EVA-RT no .eprj (ELLIPSE 1,8 na camada BOTTOM): x 33,974 / 36,514 e y -8,361 / -10,901 / "
    "-13,441; nets confirmadas no PCB: pino 1 MISO (D12), 2 +5V, 3 SCK (D13), 4 MOSI (D11), "
    "5 RESET, 6 GND. A biblioteca esta espelhada em x (vista de cima do componente): "
    "pads_absolutos(..., lado='BOTTOM') devolve as posicoes da placa do EVA-RT quando o centro "
    "fica em (35,244; -10,901) com rot 0.")

# asas (braco solto): 4 pads 3,0 (x) x 0,75 (y), passo 1,143 (45 mil); centro do conjunto = 0
_YS_ASA = {"a": 0.5715, "b": 1.7145}  # meio-passo e passo+meio do centro
_pads_asa_e = [  # J8 esquerda: 1 = +5V (y 5,08), 2 = GND (6,223), 3 = A5 (3,937), 4 = LED (2,794)
    _pad(1, 0, +_YS_ASA["a"], 3.0, 0.75),
    _pad(2, 0, +_YS_ASA["b"], 3.0, 0.75),
    _pad(3, 0, -_YS_ASA["a"], 3.0, 0.75),
    _pad(4, 0, -_YS_ASA["b"], 3.0, 0.75),
]
_pads_asa_d = [  # J9 direita: 1 = +5V (y 3,937), 2 = GND (2,794), 3 = A6 (5,08), 4 = LED2/D7 (6,223)
    _pad(1, 0, -_YS_ASA["a"], 3.0, 0.75),
    _pad(2, 0, -_YS_ASA["b"], 3.0, 0.75),
    _pad(3, 0, +_YS_ASA["a"], 3.0, 0.75),
    _pad(4, 0, +_YS_ASA["b"], 3.0, 0.75),
]
FOOTPRINTS["WING_L_1x4_SMD"] = _fp(
    _pads_asa_e, (0.0, 0.0), 0.0, False,
    "Asa esquerda J8 (DNP): 4 pads SMD 3,0 x 0,75 (3,0 no eixo x), passo 1,143 (45 mil), "
    "medidos no EVA-RT (camada TOP em x = -45,044; y 2,794 / 3,937 / 5,080 / 6,223; "
    "nets no PCB: LED1/D2 em 2,794, Y0/A5 em 3,937, +5V em 5,080, GND em 6,223). Pinos "
    "numerados como no REDES: J8.1 = +5V (y 5,08), J8.2 = GND (6,22), J8.3 = A5 (3,94), "
    "J8.4 = LEDA_D2 (2,79). Origem no centro do conjunto (x -45,04; y 4,51). Os 4 pads "
    "inferiores do EVA-RT (camada BOTTOM, 0,75 x 6,0 em x = -46,57) nao foram modelados.")
FOOTPRINTS["WING_R_1x4_SMD"] = _fp(
    _pads_asa_d, (0.0, 0.0), 0.0, False,
    "Asa direita J9 (DNP): mesmo pad do J8, espelhado. Medidos no EVA-RT (x = +45,044): "
    "GND em y 2,794, +5V em 3,937, Y1/A6 em 5,080, LED2/D7 em 6,223. Pinos numerados como no "
    "REDES: J9.1 = +5V (y 3,94), J9.2 = GND (2,79), J9.3 = A6 (5,08), J9.4 = LEDB_D7 (6,22). "
    "Origem no centro do conjunto (x 45,04; y 4,51). Pads inferiores do EVA-RT nao modelados.")

# ---------------------------------------------------------------- motores e ventoinha
FOOTPRINTS["MOTOR_1020_2P"] = _fp(
    [_pad("1", 0.0, -1.27, 3.0, 2.0, "oval", 0.9),
     _pad("2", 0.0, 1.27, 3.0, 2.0, "oval", 0.9)],
    (10.0, 20.0), 10.0, True,
    "Motor coreless 1020 (M1, M2) e ventoinha (M3), 2 pads (BOM). Medidos no EVA-RT (.eprj): "
    "furo ROUND Ø0,9; pad OVAL 3,0 (x) x 2,0 (y), passo 2,54. Pino 1 (+) em y = -1,27 e pino 2 "
    "(-) em y = +1,27: M1.1 = OUT_A2 (y 0,00) e M1.2 = OUT_A1 (y 2,54) no EVA-RT; "
    "M2.1 = OUT_B2, M2.2 = OUT_B1; M3.1 = VBAT (+), M3.2 = OUT_C. Corpo 10 x 20 (diametro 10, "
    "comprimento 20, eixo ao longo de y pelos suportes do gearbox) e altura 10: ESTIMATIVA; "
    "caixa de engrenagens nao incluida.")

# ---------------------------------------------------------------- botoes
_SW_POS = [(-3.25, 2.25), (3.25, 2.25), (-3.25, -2.25), (3.25, -2.25)]
_pads_sw_tht = []
for _i, (_x, _y) in enumerate(_SW_POS):
    _pads_sw_tht.append(_pad(_i + 1, _x, _y, 2.0, 2.0, "round", 1.1,
                             rede="1" if _y > 0 else "2"))
FOOTPRINTS["SW_6x6_THT_4P"] = _fp(
    _pads_sw_tht, (6.0, 6.0), 4.5, True,
    "Botao tatil 6x6 THT de 4 terminais (padrao do comprado, SW0..SW2). Furos em retangulo "
    "6,5 x 4,5 (pads em x = +-3,25 e y = +-2,25), furo Ø1,1 e pad Ø2,0, corpo 6 x 6, altura "
    "4,5. Base: KiCad Button_Switch_THT:SW_PUSH_6mm. Pares internos (mesma linha, 6,5 mm "
    "de distancia): pads 1 e 2 (linha de cima, y +2,25) = rede 1 (pino 1 do simbolo); pads 3 "
    "e 4 (linha de baixo) = rede 2 (pino 2). CONFERIR COM MULTIMETRO antes de encomendar: "
    "o datasheet do modelo exato nao foi acessivel.")

_pads_sw_smd = []
for _i, (_x, _y) in enumerate(_SW_POS):
    _pads_sw_smd.append(_pad(_i + 1, _x, _y, 1.8, 1.4, "rect", None,
                             rede="1" if _y > 0 else "2"))
FOOTPRINTS["SW_6x6_SMD_4P"] = _fp(
    _pads_sw_smd, (6.0, 6.0), 4.5, False,
    "Variante SMD 6x6x4,5 de 4 pads (so por garantia). PADRAO ASSUMIDO: pads 1,8 x 1,4 nas "
    "mesmas posicoes 6,5 x 4,5 e mesma ligacao da THT (linha de cima = rede 1, linha de "
    "baixo = rede 2). Sem datasheet acessivel: conferir o modelo SMD antes de usar.")

FOOTPRINTS["SW_B3U_SMD_2P"] = _fp(
    [_pad("1", -1.7, 0, 1.0, 1.7), _pad("2", 1.7, 0, 1.0, 1.7)],
    (3.0, 2.5), 2.5, False,
    "Botao B3U-1000P SMD de 2 pads. Pads 1,0 x 1,7 em x = +-1,7 medidos "
    "no EVA-RT (EasyEDA key-smd_b3u-1000pm, e330/e331/e332). Corpo 3,0 x 2,5 mm.")

# No SW0, o simbolo KiCad foi numerado ao contrario do footprint EVA-RT.
# Botao sem polaridade: inverter a correspondencia preserva as trilhas originais.
FOOTPRINTS["SW_B3U_SMD_2P_RESET"] = _fp(
    [_pad("1", -1.7, 0, 1.0, 1.7, rede="2"),
     _pad("2", 1.7, 0, 1.0, 1.7, rede="1")],
    (3.0, 2.5), 2.5, False,
    "Mesmo B3U-1000P, com pad fisico 1 = RESET (SW0.2 no esquematico) "
    "e pad 2 = GND (SW0.1); reproduz as redes do EVA-RT.")

# Chave tactil SMD 3 x 6 de 2 terminais. 07/11 (noite): o Erick escolheu a Jianfu TVBM17-025CF-R (LCSC C19271064):
# corpo 6,1 x 3,7 x 2,5, terminais de 0,6 com 8,0 de ponta a ponta; padrao do fabricante = pads 1,0 x 1,75 a 9,5 no
# total, que nao cabe ao lado do J4. Pads encurtados abaixo (8,6 no total), com o terminal inteiro sobre o pad.
# Escolha anterior: TC-3610 (comprada; sem datasheet),
# equivalente JLC HCTL TC-3601L-2.5-260G (C2845294): corpo 6,0 x 3,6 x 2,5, terminais gull-wing com 8,0 de
# ponta a ponta, pads recomendados de 6,2 a 8,4 (1,0 de largura). Aqui pads de 1,2 x 1,2 de |x| = 3,1 a 4,3
# (um pouco maiores, para soldar a mao). A HYP 1TS002B (C255788, 4,3 mm de altura) tambem solda neles.
FOOTPRINTS["SW_TACT_3x6_SMD_2P"] = _fp(
    [_pad("1", -3.7, 0, 1.2, 1.2), _pad("2", 3.7, 0, 1.2, 1.2)],
    (6.1, 3.7), 2.5, False,
    "Chave tactil SMD 3 x 6 de 2 terminais (Jianfu TVBM17-025CF-R, C19271064). Corpo 6,1 x 3,7 x 2,5; "
    "pads 1,2 x 1,2 em x = +-3,7 (de 3,1 a 4,3; recomendado pelo fabricante: 6,2 a 8,4).")

FOOTPRINTS["SW_TACT_3x6_SMD_2P_RESET"] = _fp(
    [_pad("1", -3.7, 0, 1.2, 1.2, rede="2"), _pad("2", 3.7, 0, 1.2, 1.2, rede="1")],
    (6.1, 3.7), 2.5, False,
    "Mesma chave 3 x 6, com pad fisico 1 = RESET (SW0.2 no esquematico) e pad 2 = GND (SW0.1).")

# ---------------------------------------------------------------- sensores de marca
FOOTPRINTS["QRE1113GR_SMD"] = _fp(
    [_pad("1", 2.0, 0.9, 1.66, 0.8),
     _pad("2", -2.0, 0.9, 1.66, 0.8),
     _pad("3", -2.0, -0.9, 1.66, 0.8),
     _pad("4", 2.0, -0.9, 1.66, 0.8)],
    (3.6, 2.9), 1.7, False,
    "QRE1113GR SMD horizontal (S0, S1 na face BOTTOM). Pads 1,66 x 0,80 mm, centros "
    "(+/-2,0; +/-0,9), conferidos no Gerber inferior do EVA-RT e associados as redes "
    "originais. Pinos 1/2/3/4 = anodo/catodo/coletor/emissor, conforme onsemi. "
    "Corpo 3,6 x 2,9 x 1,7 mm aproximado; conferir contra a peca e o footprint adotado.")

# ---------------------------------------------------------------- mapeamento REF -> footprint
REF_FOOTPRINT = {}
for _r in ["R1", "R2", "R3", "R5", "R6", "R7", "R8", "R9", "R10", "R11", "R12", "R13",
           "R14", "R15", "R16", "R17", "R18", "R20", "R21", "R23", "R24", "R30", "R31"]:
    REF_FOOTPRINT[_r] = "R0603"
for _r in ["C3", "C4", "C6", "C7", "C8", "C9", "C10", "C11", "C12", "C13", "C14", "C15",
           "C16", "C17", "C18"]:
    REF_FOOTPRINT[_r] = "C0603"
REF_FOOTPRINT.update({
    "C1": "C_RAD_D6.3_P2.5",
    "C2": "C_RAD_D6.3_P2.5",
    "C5": "C1210",
    "D1": "SOD123",
    "Q1": "SOT23_AO3400A",
    "LED1": "LED0603", "LED2": "LED0603", "LED4": "LED0603",
    "LED5": "LED0603", "LED6": "LED0603", "LED7": "LED0603",
    "U1": "TQFP32_7x7_P0.8",
    "U2": "HTSSOP16_PWP_DRV8874",
    "U3": "HTSSOP16_PWP_DRV8874",
    "U5": "DPAK_TO252_3",
    "X1": "XTAL_TXC_7A_5032_2P",
    "J1": "XT30_VERTICAL_M_PROPOSTA",
    "J2": "HDR_1x08_P2.54",
    "J3": "HDR_RA_1x05_P2.54",
    "J4": "HDR_F_1x06_P2.54",
    "J5": "ICSP_6P_SMD_BOT",
    "J8": "WING_L_1x4_SMD",
    "J9": "WING_R_1x4_SMD",
    "M1": "MOTOR_1020_2P",
    "M2": "MOTOR_1020_2P",
    "M3": "MOTOR_1020_2P",
    "S0": "QRE1113GR_SMD",
    "S1": "QRE1113GR_SMD",
    "SW0": "SW_TACT_3x6_SMD_2P_RESET",
    "SW1": "SW_TACT_3x6_SMD_2P",
    "SW2": "SW_TACT_3x6_SMD_2P",
})

# alternativas da BOM (nao usadas por padrao)
ALTERNATIVAS = {
    "J1": ["XT30_RABICHO", "XT30PW_M_PCB"],
    "X1": ["CRISTAL_HC49S_SMD"],
    "SW0": ["SW_6x6_SMD_4P", "SW_6x6_THT_4P"],
    "SW1": ["SW_6x6_SMD_4P", "SW_6x6_THT_4P"],
    "SW2": ["SW_6x6_SMD_4P", "SW_6x6_THT_4P"],
}


# ---------------------------------------------------------------- funcoes de uso
def _rot(x, y, rot_graus):
    t = math.radians(rot_graus)
    c, s = math.cos(t), math.sin(t)
    # arredonda para evitar 6e-17 em multiplos de 90 graus
    c = round(c, 12)
    s = round(s, 12)
    return x * c - y * s, x * s + y * c


def _lado_efetivo(ref, lado):
    if lado is None:
        return LADO_PADRAO_REF.get(ref, "TOP")
    if lado not in ("TOP", "BOTTOM"):
        raise ValueError("lado deve ser 'TOP' ou 'BOTTOM'")
    return lado


def pads_absolutos(ref, x, y, rot_graus, lado=None):
    """Pads do componente `ref` colocado em (x, y) com rotacao anti-horaria.

    lado: 'TOP' ou 'BOTTOM'. Para BOTTOM o x do footprint e espelhado antes de girar.
    Se lado for None usa LADO_PADRAO_REF (J5, S0 e S1 em BOTTOM; o resto em TOP).
    Retorna lista de dicts: pino, rede_pino, x, y (absolutos, mm), w, h, forma, furo.
    w e h trocam de lugar em rotacoes de 90 ou 270 graus.
    """
    fp = FOOTPRINTS[REF_FOOTPRINT[ref]]
    lado = _lado_efetivo(ref, lado)
    troca = (round(rot_graus / 90.0) % 2 == 1) and abs(rot_graus / 90.0 - round(rot_graus / 90.0)) < 1e-9
    saida = []
    for p in fp["pads"]:
        px = -p["x"] if lado == "BOTTOM" else p["x"]
        rx, ry = _rot(px, p["y"], rot_graus)
        w, h = (p["h"], p["w"]) if troca else (p["w"], p["h"])
        saida.append({
            "pino": p["pino"],
            "rede_pino": p["rede_pino"],
            "x": x + rx,
            "y": y + ry,
            "w": w,
            "h": h,
            "forma": p["forma"],
            "furo": p["furo"],
        })
    return saida


def corpo_absoluto(ref, x, y, rot_graus, lado=None, chave="corpo"):
    """Retangulo (centro e tamanho) do corpo ou da cortesia do componente colocado.

    chave: 'corpo' ou 'cortesia'. Retorna dict com cx, cy, w, h (mm, absolutos).
    Quando o componente nao tem corpo ([0,0]) devolve w = h = 0.
    """
    fp = FOOTPRINTS[REF_FOOTPRINT[ref]]
    lado = _lado_efetivo(ref, lado)
    w, h = fp[chave]
    cxy = fp["corpo_xy"] if chave == "corpo" else fp["cortesia_xy"]
    px = -cxy[0] if lado == "BOTTOM" else cxy[0]
    rx, ry = _rot(px, cxy[1], rot_graus)
    troca = (round(rot_graus / 90.0) % 2 == 1) and abs(rot_graus / 90.0 - round(rot_graus / 90.0)) < 1e-9
    if troca:
        w, h = h, w
    return {"cx": x + rx, "cy": y + ry, "w": w, "h": h}
