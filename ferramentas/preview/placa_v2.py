"""Placa base v2: J3 SMD na face inferior, ATmega recuado e componentes espalhados.

Posicionamento completo e unico desta versao (06/11/2026), no referencial do
seguidor: origem no centro da ventoinha, +y para a frente, mm. Rotacao em graus,
anti-horaria, vista de cima; componentes BOTTOM sao vistos atraves da placa.

Filosofia (EVA-RT): ATmega no centro da traseira a -45 graus, drivers nos lados
com seus capacitores, regulador na frente esquerda, ventoinha/Bluetooth/botoes na
frente direita, sinais em feixes em volta do furo da ventoinha. Passivos em
linhas e colunas, a alguns milimetros dos CIs, e nao amontoados no ATmega.

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

import footprints as F
import layout_placa as M

SAIDA = M.HERE / 'v2'
SAIDA.mkdir(exist_ok=True)

# ---------------------------------------------------------------- J3 na face inferior
# Barra macho 1x5 2,54 mm deitada na face de baixo, soldada em 5 pads SMD, como o
# conector do EVA-RT (que usa 5 pads 1,25 x 2,25 em y = -28,575, passo 2,0).
# Aqui o passo e 2,54 (barra comum). Footprint desenhado visto de cima do
# componente: com lado BOTTOM o x e espelhado, entao o pino 1 (+5V) fica em
# x = -5,08 na placa, como o +5V do EVA-RT (x = -4). Ordem na placa, da esquerda
# para a direita vista de cima: +5V, GND, RX, TX, DTR (EVA-RT: +5V, GND, RX, TX, RESET).
F.FOOTPRINTS['HDR_1x05_P2.54_SMD_DEITADA'] = F._fp(
    [F._pad(i + 1, 5.08 - 2.54 * i, 0.0, 1.25, 2.25) for i in range(5)],
    (12.7, 2.5), 2.5, False,
    'Barra macho 1x5 passo 2,54 deitada na face inferior, soldada em 5 pads SMD '
    '1,25 x 2,25 (largura e comprimento iguais aos do EVA-RT, passo 2,54). Corpo '
    'plastico e pinos longos para tras, alem da borda.', corpo_xy=(0.0, -2.4))
F.REF_FOOTPRINT['J3'] = 'HDR_1x05_P2.54_SMD_DEITADA'
F.LADO_PADRAO_REF['J3'] = 'BOTTOM'

T, B = 'TOP', 'BOTTOM'
# ref: (x, y, rot, face, motivo)
POS = {
    # ---- mecanica e conectores (fixos)
    'J1': (-32.9, -31.7, 0, T, 'XT30 no canto traseiro esquerdo, corpo em x >= -38 (2 mm da engrenagem em x <= -40); pad 1 (lado reto) = +'),
    'J2': (0.0, 22.74, 0, T, 'barra de sensores, centro da frente'),
    'J3': (0.0, -28.575, 0, B, 'gravacao: barra deitada embaixo, 5 pads SMD como no EVA-RT (passo 2,54)'),
    'J4': (32.5, 7.05, 0, T, 'Bluetooth (femea 1x6), frente direita'),
    'J5': (35.244, -10.901, 0, B, 'ICSP: pads do EVA-RT'),
    'M1': (-36.58, 1.27, 0, T, 'motor esq.: pads do EVA-RT'),
    'M2': (36.58, 1.27, 0, T, 'motor dir.: pads do EVA-RT'),
    'M3': (29.72, 3.05, 0, T, 'ventoinha: pads do EVA-RT'),
    'SW0': (36.35, -30.25, 180, T, 'reset, B3U na posicao do EVA-RT'),
    'SW1': (37.34, 5.84, 0, T, 'B3U na posicao do EVA-RT'),
    'SW2': (37.34, 11.30, 0, T, 'B3U na posicao do EVA-RT'),
    # ---- bracos (sensores de marca)
    'S0': (-69.5, 4.5, 180, B, 'QRE esq. (curva, A5)'),
    'S1': (69.5, 4.5, 0, B, 'QRE dir. (partida/chegada, A6)'),
    'LED1': (-69.5, 4.5, -90, T, 'LED sobre o QRE esq.'),
    'LED2': (69.5, 4.5, 90, T, 'LED sobre o QRE dir.'),
    'R6': (-61.73, 4.43, 90, B, 'braco esq. (asa do EVA-RT)'),
    'R20': (-64.67, 3.61, 180, B, 'braco esq. (asa do EVA-RT)'),
    'R30': (-64.67, 5.39, 180, B, 'braco esq. (asa do EVA-RT)'),
    'R7': (61.73, 4.57, 270, B, 'braco dir. (asa do EVA-RT)'),
    'R21': (64.67, 5.39, 0, B, 'braco dir. (asa do EVA-RT)'),
    'R31': (64.67, 3.61, 0, B, 'braco dir. (asa do EVA-RT)'),
    # ---- frente esquerda: 5 V (EVA-RT)
    'U5': (-30.61, 9.02, 180, T, '78M05, EVA-RT'),
    'C1': (-22.0, 2.06, -90, T, '220 uF VBAT, EVA-RT'),
    'C3': (-19.18, 7.0, 90, T, 'EVA-RT'),
    'C4': (-24.26, 10.12, 90, T, 'EVA-RT'),
    'C5': (-21.72, 8.0, -90, T, 'tantalo 47 uF, EVA-RT'),
    'LED5': (-21.34, 13.46, 0, T, 'LED 5 V, EVA-RT'),
    'R10': (-17.91, 11.81, 0, T, 'EVA-RT'),
    # ---- frente direita: ventoinha, LED C, Bluetooth (EVA-RT)
    'Q1': (26.92, 9.14, 180, T, 'AO3400A, EVA-RT'),
    'R8': (20.57, 7.62, -90, T, 'EVA-RT'),
    'R9': (20.57, 10.79, -90, T, 'EVA-RT'),
    'R5': (18.67, 10.79, 90, T, 'EVA-RT'),
    'LED4': (21.34, 13.46, 180, T, 'LED C, EVA-RT'),
    'C2': (22.0, 2.06, 90, T, '220 uF VBAT, EVA-RT'),
    'C8': (26.67, 2.79, -90, T, 'EVA-RT'),
    'D1': (26.5, 3.05, -90, B, 'diodo da ventoinha, embaixo dos pads do motor'),
    'R16': (29.2, 8.2, 0, B, 'divisor do Bluetooth, embaixo do J4'),
    'R17': (29.2, 10.2, 0, B, 'divisor do Bluetooth, embaixo do J4'),
    # ---- driver esquerdo: sinais (pinos 1-8) em cima, potencia (9-16) embaixo
    'U2': (-22.1, -12.45, -90, T, 'DRV8874 esq. no lugar do IFX do EVA-RT'),
    'C6': (-25.9, -17.6, 180, T, 'VM-GND junto a VM/PGND'),
    'C13': (-23.075, -17.6, 0, T, 'VCP-VM sob os pinos 11/12'),
    'C14': (-20.425, -17.6, 0, T, 'CPH-CPL sob os pinos 13/14'),
    'R11': (-23.4, -6.6, 90, T, 'IPROPI A, acima do pino 6'),
    'R15': (-21.125, -6.6, 270, T, 'pull-up nSLEEP, acima do pino 3'),
    # ---- driver direito (rotacao 90: sinais embaixo, potencia em cima)
    'U3': (22.1, -12.45, 90, T, 'DRV8874 dir. no lugar do IFX do EVA-RT'),
    'C7': (25.9, -7.3, 0, T, 'VM-GND junto a VM/PGND'),
    'C15': (23.075, -7.3, 180, T, 'VCP-VM sobre os pinos 11/12'),
    'C16': (20.425, -7.3, 180, T, 'CPH-CPL sobre os pinos 13/14'),
    'R12': (23.4, -18.3, 270, T, 'IPROPI B, abaixo do pino 6'),
    'R14': (22.0, -20.6, 180, T, 'divisor VREF (lado GND), abaixo do pino 5'),
    'R13': (24.5, -20.6, 180, T, 'divisor VREF (lado +5V)'),
    # ---- ATmega e vizinhos
    'U1': (0.0, -23.0, -45, T, 'posicao e rotacao do EVA-RT (recuado 0,75 mm em relacao a previa anterior)'),
    'X1': (-7.8, -27.4, 180, T, 'PROPOSTA 3225, a esquerda dos pinos 7/8'),
    'C11': (-6.7, -24.3, 90, T, '22 pF de XTAL1'),
    'C12': (-11.3, -28.25, 180, T, '22 pF de XTAL2'),
    'C9': (7.4, -21.6, 45, T, '100 nF +5V junto a AVCC/GND (pinos 18/21)'),
    'C10': (5.71, -18.29, 135, T, 'AREF, EVA-RT'),
    'R3': (-15.49, -19.56, 0, T, 'pull-up do RESET, EVA-RT'),
    'R1': (-15.49, -21.46, 0, T, 'LED TX, EVA-RT'),
    'R2': (-15.49, -23.37, 0, T, 'LED RX, EVA-RT'),
    'LED6': (-11.94, -21.46, 180, T, 'TX, EVA-RT'),
    'LED7': (-11.94, -23.37, 180, T, 'RX, EVA-RT'),
    'C17': (8.6, -27.6, 0, T, 'DTR-RESET, junto ao pad DTR do J3'),
    'R23': (11.74, -19.55, 0, T, 'divisor VBAT (no lugar do LED3/R4 do EVA-RT)'),
    'R24': (11.74, -21.45, 180, T, 'divisor VBAT'),
    'C18': (11.74, -23.35, 180, T, 'filtro do A7'),
}


# componentes que sairam do esquematico depois da lista base (posicoes.json)
REMOVIDOS = {'R18'}   # 06/11: TXD do Bluetooth direto no RX_D0 (trilha)


def load():
    base = json.loads((M.HERE / 'posicoes.json').read_text(encoding='utf8'))
    out = []
    for c in base:
        c = dict(c)
        ref = c['ref']
        if c.get('dnp') or ref in REMOVIDOS:
            continue
        if ref not in POS:
            raise KeyError('sem posicao: ' + ref)
        c['x'], c['y'], c['rot'], c['face'], c['motivo'] = POS[ref]
        c['footprint'] = F.REF_FOOTPRINT[ref]
        c['tht'] = F.FOOTPRINTS[c['footprint']]['tht']
        if ref == 'J3':
            c['valor'] = 'GRAVACAO (barra 1x5 2,54 deitada, embaixo)'
        out.append(c)
    missing = set(POS) - {c['ref'] for c in out}
    if missing:
        raise KeyError('posicoes sem componente: ' + ', '.join(sorted(missing)))
    return out


# ---------------------------------------------------------------- areas mecanicas
def _area(nome):
    for a in M.BOARD_DATA['areas']:
        if a['nome'] == nome:
            return unary_union([Polygon(p).buffer(0) for p in a['poligonos']])
    raise KeyError(nome)

ROTOR = Point(0, 0).buffer(17.0, quad_segs=32)          # rotor: so trilhas em cima
CARCACA = _area('carcaca_contato')                       # pes da carcaca (em cima)
SUCCAO = _area('succao_contato')                         # placa de succao (embaixo)
GEARBOX = [box(-40, -28.5, -30.5, -1.8), box(30.5, -28.5, 40, -1.8)]
BATERIA = box(-22.5, -42.6, 22.5, -22.1)                 # so componentes <= 2,5 mm
# engrenagem 64T M0,3 (Ø19,8 x 2) no eixo da roda (y -22,59, 7,0 mm acima da placa), fora
# do suporte em |x| 40..42: componentes em cima nao entram nessa faixa e a placa nao pode
# passar de |x| = 40 onde a engrenagem desce abaixo da face de cima (|y + 22,59| < 7,0)
ENGRENAGEM = [box(40, -32.49, 42, -12.69), box(-42, -32.49, -40, -12.69)]
ENGRENAGEM_SOB_PLACA = [box(40, -29.59, 45, -15.59), box(-45, -29.59, -40, -15.59)]
PRESILHAS = [_area(n) for n in ('presilha_D_tras_contato', 'presilha_D_frente_contato',
                                'presilha_E_tras_contato', 'presilha_E_frente_contato')]


def footprint_shape(c):
    """Corpo + pads do componente (para colisao mecanica)."""
    parts = [p['shape'] for p in M.get_pads(c)]
    b = M.body(c)
    if b is not None:
        parts.append(b)
    return unary_union(parts)


def check(positions):
    problems = list(M.check_positions(positions))
    for c in positions:
        ref = c['ref']
        if ref in ('M1', 'M2', 'M3'):
            continue
        g = footprint_shape(c)
        h = F.FOOTPRINTS[c['footprint']]['altura_mm']
        if c['face'] == 'TOP' or c['tht']:
            if g.intersects(ROTOR) and ref not in ('J2',):
                problems.append(('sob o rotor', ref))
            if g.intersects(CARCACA):
                problems.append(('pe da carcaca', ref))
            for gb in GEARBOX:
                if g.intersects(gb) and ref not in ('J1', 'SW0'):
                    problems.append(('suporte do motor', ref))
            for pr in PRESILHAS:
                if g.intersects(pr):
                    problems.append(('presilha', ref))
            for eg in ENGRENAGEM:
                if g.intersects(eg):
                    problems.append(('engrenagem da roda', ref))
            if g.intersects(BATERIA) and h > 2.5 and c['face'] == 'TOP':
                problems.append(('alto sob a bateria', ref, h))
        if c['face'] == 'BOTTOM' or c['tht']:
            # pads rentes (< 0,1 mm) como os do conector do EVA-RT nao contam
            if c['face'] == 'BOTTOM' and g.buffer(-0.1).intersects(SUCCAO):
                problems.append(('placa de succao', ref))
    return problems


def check_board():
    out = []
    for z in ENGRENAGEM_SOB_PLACA:
        a = M.OUTLINE.intersection(z).area
        if a > 1e-6:
            out.append(('contorno invade a engrenagem', round(a, 3)))
    return out


def export_dxf(path):
    import ezdxf
    d = ezdxf.new('R2010'); d.units = 4
    d.layers.new('CONTORNO'); d.layers.new('FURO_VENTOINHA')
    msp = d.modelspace()
    msp.add_lwpolyline(list(M.OUTLINE.exterior.coords)[:-1], close=True, dxfattribs={'layer': 'CONTORNO'})
    msp.add_circle((0, 0), 8.5, dxfattribs={'layer': 'FURO_VENTOINHA'})
    d.saveas(path)


def export_csv(positions, path):
    with open(path, 'w', encoding='utf8', newline='') as fh:
        wr = csv.writer(fh, delimiter=';', lineterminator='\n')
        wr.writerow(['ref', 'valor', 'footprint', 'face', 'x_mm', 'y_mm', 'rot_graus', 'motivo'])
        for c in sorted(positions, key=lambda c: (c['ref'][0], int(''.join(ch for ch in c['ref'] if ch.isdigit()) or 0))):
            wr.writerow([c['ref'], c.get('valor', ''), c['footprint'], c['face'],
                         f"{c['x']:.3f}".replace('.', ','), f"{c['y']:.3f}".replace('.', ','),
                         c['rot'], c['motivo']])


if __name__ == '__main__':
    pos = load()
    print(len(pos), 'componentes')
    for p in check(pos) + check_board():
        print(p)
    export_dxf(M.OUTPUT / 'contorno_b_xt30.dxf')
