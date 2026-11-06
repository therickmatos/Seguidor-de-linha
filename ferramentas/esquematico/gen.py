import os, sys, json
sys.path.insert(0, '.')
from kisch import Sch
from drv8874 import drv_block

def g(n): return round(n * 2.54, 3)

S = Sch(paper='A3', project='seguidor_base')
S.tb = dict(title='Seguidor - placa base (clone do EVA-RT)',
            date='2026-11-03', rev='1.0', company='Erick',
            comments=['conectores 2,54 mm (barra, gravacao, Bluetooth), ICSP mantido',
                      'Trocas: DRV8874 no lugar do IFX9201, AO3400A no Q1, cristal 16 MHz,',
                      'Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0'])
BOM = {}   # ref -> dict(value, pkg, note, lcsc)

def part(lib, name, ref, value, x, y, r=0, pkg='', note='', lcsc='', dnp=False, block=None, **kw):
    f = {'Encapsulamento': pkg}
    if lcsc: f['LCSC'] = lcsc
    S.place(lib, name, ref, value, x, y, r, fields=f, block=block, dnp=dnp, **kw)
    BOM[ref] = dict(value=value, pkg=pkg, note=note, lcsc=lcsc, dnp=dnp)

def R(ref, val, x, y, r=0, pkg='0603', note='', dnp=False):
    off = dict(ref_off=(2.54, -1.27), val_off=(2.54, 1.27)) if r == 0 else dict(ref_off=(-2.54, -2.54), val_off=(-2.54, 3.81))
    part('Device', 'R', ref, val, x, y, r, pkg, note, dnp=dnp, **off)

def C(ref, val, x, y, r=0, pkg='0603', note='', pol=False, dnp=False):
    off = dict(ref_off=(2.54, -1.27), val_off=(2.54, 1.27)) if r == 0 else dict(ref_off=(-2.54, -2.54), val_off=(-2.54, 3.81))
    part('Device', 'C_Polarized' if pol else 'C', ref, val, x, y, r, pkg, note, dnp=dnp, **off)

def LED(ref, val, x, y, r=180, note='', dnp=False):
    part('Device', 'LED', ref, val, x, y, r, '0603', note, dnp=dnp, ref_off=(-2.54, -2.54), val_off=(-2.54, 3.81))

def frame(x1, y1, x2, y2, title):
    S.rect(x1, y1, x2, y2)
    S.text(title, x1 + 2.54, y1 + 5.08, 2.0, True)

def note(lines, x, y, size=1.27):
    for i, t in enumerate(lines):
        S.text(t, x, y + i * 2.54 * size / 1.27)

# ---------------------------------------------------------------- 1 ALIMENTACAO
frame(10, 12, 144, 72, '1 - ALIMENTACAO (bateria 2S -> 5 V)')
part('Connector_Generic', 'Conn_01x02', 'J1', 'XT30 (bateria 2S)', g(8), g(12), 180,
     'XT30 macho de placa (vertical)', 'pino 1 = + (lado reto), pino 2 = -; canto traseiro esquerdo', ref_off=(-2.54, -6.35), val_off=(-7.62, 6.35))
S.conn('J1', '1', 'VBAT'); S.conn('J1', '2', 'GND')
x, y, ox, oy = S.pinpos('J1', '1'); S.flag(x + 2.54, y)
x, y, ox, oy = S.pinpos('J1', '2'); S.flag(x + 2.54, y)
for i, (ref, val) in enumerate([('C1', '220uF'), ('C2', '220uF')]):
    C(ref, val, g(15 + 5 * i), g(14), pkg='eletrolitico 25 V, radial D6,3 mm P2,5', pol=True, note='entre os pes da carcaca, como no EVA-RT')
    S.conn(ref, '1', 'VBAT'); S.conn(ref, '2', 'GND')
C('C3', '220nF', g(25), g(14), pkg='0603 50 V'); S.conn('C3', '1', 'VBAT'); S.conn('C3', '2', 'GND')
part('Regulator_Linear', 'LM78M05_TO252', 'U5', '78M05', g(32), g(13), 0, 'TO-252 (DPAK)', '', 'C111265',
     ref_off=(-2.54, -6.35), val_off=(5.08, 6.35))
S.conn('U5', '1', 'VBAT', bend='up'); S.conn('U5', '2', 'GND'); S.conn('U5', '3', '+5V', bend='up')
C('C4', '100nF', g(39), g(14)); S.conn('C4', '1', '+5V'); S.conn('C4', '2', 'GND')
C('C5', '47uF', g(44), g(14), pkg='tantalo 10 V, 3216 (caso A)', pol=True); S.conn('C5', '1', '+5V'); S.conn('C5', '2', 'GND')
R('R10', '1k', g(49), g(12)); S.conn('R10', '1', '+5V')
part('Device', 'LED', 'LED5', 'verde', g(49), g(15) + 1.27, 90, '0603', 'indica 5 V presente', ref_off=(2.54, -1.27), val_off=(2.54, 1.27))
S.link('R10', '2', 'LED5', '2'); S.conn('LED5', '1', 'GND')
R('R23', '20k 1%', g(42), g(22), r=90, note='medicao da bateria (opcional)'); S.conn('R23', '1', 'VBAT')
R('R24', '10k 1%', g(45), g(22) + 3.81, note='medicao da bateria (opcional)'); S.conn('R24', '2', 'GND')
C('C18', '100nF', g(50.5), g(22) + 3.81, note='filtro da medicao (opcional)'); S.conn('C18', '2', 'GND')
_xa, _ya, _, _ = S.pinpos('R23', '2'); _xc, _yc, _, _ = S.pinpos('C18', '1')
S.wire(_xa, _ya, g(45), _ya); S.wire(g(45), _ya, _xc, _yc); S.junction(g(45), _ya); S.junction(_xc, _yc); S.links.append(('R23', '2', 'R24', '1'))
S.wire(_xc, _yc, _xc + 5.08, _yc); S.label('VBAT_A7', _xc + 5.08, _yc, 1, 0)
S.intent += [('R23', '2', 'VBAT_A7'), ('R24', '1', 'VBAT_A7'), ('C18', '1', 'VBAT_A7')]
note(['Bateria LiPo 2S (6,0-8,4 V) pelo XT30, que tambem e a chave liga/desliga.',
      'XT30 polarizado; sem protecao contra inversao.',
      'VBAT_A7 (abaixo, a direita): divisor 20k/10k no ADC7, 8,4 V -> 2,8 V.',
      'Opcional: o firmware original nao mede a bateria.',
      'C1/C2: reserva do VM das pontes H e da ventoinha (igual ao EVA-RT).'], 12.7, 53.34)

# ---------------------------------------------------------------- 2 BARRA
frame(10, 76, 144, 118, '2 - BARRA DE SENSORES (V1: 12x QRE1113 + 74HC4067)')
part('Connector_Generic', 'Conn_01x08', 'J2', 'BARRA (1x8, 2,54 mm)', g(24), g(37), 0, 'barra de pinos 1x8 2,54 mm', '',
     ref_off=(-2.54, -10.16), val_off=(2.54, -10.16))
for p, n in zip('12345678', ['+5V', 'GND', None, 'C0_A4', 'S3_A3', 'S2_A2', 'S1_A1', 'S0_A0']):
    S.conn('J2', p, n, stub=7.62 if n in ('+5V', 'GND') else 2.54)
note(['Mesma ordem da barra V1 (pino 1 a esquerda, vista de cima).',
      'Barra com furos de 2,0 mm: cabo misto (2,0 / 2,54 mm)',
      'ou fios soldados direto na barra.',
      'Canais 0, 1, 14 e 15 do mux estao no GND na barra.'], g(30), g(35))

# ---------------------------------------------------------------- 3 MARCAS
frame(10, 122, 144, 222, '3 - SENSORES DE MARCA (bracos laterais)')
def wing(i, y0, side, mark, led_net, ledref, rled, rqa, rqe, qref, jref):
    S.text(side, 12.7, y0 - 6.35, 1.5, True)
    part('Sensor_Proximity', 'QRE1113GR', qref, 'QRE1113GR', g(24), y0, 0, 'SMD 4 pinos',
         'datasheet: 1 = anodo, 2 = catodo, 3 = coletor, 4 = emissor', ref_off=(-2.54, -5.08), val_off=(-2.54, 6.35))
    R(rqa, '220', g(18), y0 - 2.54, r=90); S.conn(rqa, '1', '+5V'); S.link(rqa, '2', qref, '1')
    S.conn(qref, '2', 'GND', bend='down'); S.conn(qref, '3', '+5V'); S.conn(qref, '4', mark)
    x, y, _, _ = S.pinpos(qref, '4')
    R(rqe, '47k', g(36), y0 + 2.54 + 3.81); S.wire(x + 2.54, y, g(36), y); S.links.append((qref, '4', rqe, '1'))
    S.conn(rqe, '2', 'GND')
    R(rled, '1k', g(44), y0 - 2.54, r=90); S.conn(rled, '1', led_net)
    LED(ledref, ('LED A' if i == 0 else 'LED B'), g(44) + 7.62, y0 - 2.54, r=180)
    S.links.append((rled, '2', ledref, '2'))
    S.conn(ledref, '1', 'GND', bend='down')
    part('Connector_Generic', 'Conn_01x04', jref, 'ASA ' + ('ESQ.' if i == 0 else 'DIR.'),
         g(50), y0 + g(5), 0, '4 pads', 'opcional: nao montar se o braco for parte da placa base', dnp=True,
         ref_off=(3.81, 0), val_off=(3.81, 2.54))
    for p, n in zip('1234', ['+5V', 'GND', mark, led_net]):
        S.conn(jref, p, n, stub=12.7 if n in ('+5V', 'GND') else 2.54)
wing(0, g(56), 'Esquerdo: marca de curva (EVA-RT: S0 -> A5, LED A -> D2)', 'MARK_L_A5', 'LEDA_D2', 'LED1', 'R6', 'R20', 'R30', 'S0', 'J8')
wing(1, g(73), 'Direito: partida/chegada (EVA-RT: S1 -> A6, LED B -> D7)', 'MARK_R_A6', 'LEDB_D7', 'LED2', 'R7', 'R21', 'R31', 'S1', 'J9')
note(['QRE em seguidor de emissor: coletor no +5V, saida no emissor com 47k ao GND (alto no branco).',
      'Confira a numeracao do footprint do QRE1113GR contra o datasheet antes de rotear.',
      'QRE nos bracos em x = +/-69,5, y = 4,5 (centro da fita lateral do TRIF).'], 12.7, g(81) + 2.54)

# ---------------------------------------------------------------- 4 MICROCONTROLADOR
frame(146, 12, 276, 160, '4 - MICROCONTROLADOR (ATmega328P-AU, 16 MHz, 5 V)')
part('MCU_Microchip_ATmega', 'ATmega328P-A', 'U1', 'ATmega328P-AU', g(84), g(33), 0, 'TQFP-32',
     'do Nano/Uno doador (com bootloader) ou novo + bootloader pelo ICSP', 'C14877',
     ref_off=(7.62, -38.1), val_off=(2.54, 40.64))
right = {'12': None, '13': None, '14': 'PWMC_D10', '15': 'B1_D11', '16': 'B2_D12', '17': 'LEDC_D13',
         '7': 'XTAL1', '8': 'XTAL2', '23': 'S0_A0', '24': 'S1_A1', '25': 'S2_A2', '26': 'S3_A3', '27': 'C0_A4',
         '28': 'MARK_L_A5', '29': 'RESET', '30': 'RX_D0', '31': 'TX_D1', '32': 'LEDA_D2', '1': 'DIRA_D3',
         '2': 'DIRB_D4', '9': 'PWMA_D5', '10': 'PWMB_D6', '11': 'LEDB_D7'}
for p, n in right.items(): S.conn('U1', p, n)
S.conn('U1', '20', 'AREF'); S.conn('U1', '19', 'MARK_R_A6'); S.conn('U1', '22', 'VBAT_A7')
S.conn('U1', '3', 'GND')
# VCC + AVCC to +5V with one power symbol
x4, y4, _, _ = S.pinpos('U1', '4'); x18, y18, _, _ = S.pinpos('U1', '18')
S.wire(x4, y4, x4, y4 - 2.54); S.wire(x18, y18, x18, y18 - 2.54); S.wire(x4, y4 - 2.54, x18, y18 - 2.54)
S.power('+5V', x4, y4 - 2.54); S.intent += [('U1', '4', '+5V'), ('U1', '18', '+5V')]
# cristal
part('Device', 'Crystal', 'X1', '16MHz', g(102), g(14), 0, 'HC-49/S SMD ou 3225 (o que vier do doador)',
     'ou o ressonador CSTCE16M0V13 do EVA-RT (3 pinos), sem C11/C12', ref_off=(-2.54, -3.81), val_off=(2.54, -3.81))
S.conn('X1', '1', 'XTAL1'); S.conn('X1', '2', 'XTAL2')
_X, _Y = g(102), g(14)
C('C11', '22pF', _X - 6.35, _Y + 6.35); S.conn('C11', '2', 'GND')
C('C12', '22pF', _X + 6.35, _Y + 6.35); S.conn('C12', '2', 'GND')
for _c in ('C11', 'C12'):
    _x, _y, _, _ = S.pinpos(_c, '1'); S.wire(_x, _y, _x, _Y)
S.intent += [('C11', '1', 'XTAL1'), ('C12', '1', 'XTAL2')]
# desacoplamento e reset
C('C9', '100nF', g(60), g(20), note='junto aos pinos VCC'); S.conn('C9', '1', '+5V'); S.conn('C9', '2', 'GND')
C('C10', '100nF', g(65), g(20), note='AREF (referencia = AVCC no firmware)'); S.conn('C10', '1', 'AREF', bend='right'); S.conn('C10', '2', 'GND')
R('R3', '10k', g(60), g(36), note='EVA-RT usava 1k; 10k com reset automatico por DTR'); S.conn('R3', '1', '+5V'); S.conn('R3', '2', 'RESET', bend='right')
part('Switch', 'SW_Push', 'SW0', 'RESET', g(66), g(40), 90, 'botao tatil 2 pinos (furo) ou B3U-1000P', '',
     ref_off=(5.08, -1.27), val_off=(5.08, 1.27))
S.conn('SW0', '2', 'RESET', bend='right'); S.conn('SW0', '1', 'GND')
note(['Pinos iguais ao EVA-RT 1.2.2: motores D3-D6, ventoinha D10,',
      'botoes D11/D12, LEDs D2/D7/D13, mux A0-A4, marcas A5/A6.',
      'D11/D12/D13 tambem sao MOSI/MISO/SCK do ICSP.',
      'D8 e D9 livres (Ready/Go no codigo do EVA-RT, sem uso). ADC7 = bateria.'], 148.59, g(53))

# ---------------------------------------------------------------- 5 PONTES H
frame(280, 12, 410, 170, '5 - PONTES H (2x DRV8874, modo PH/EN)')
drv = drv_block()
def hbridge(ref, y0, sfx, en, ph, mref, cvcp, ccp, cvm, ripr, side):
    part('seguidor', 'DRV8874PWP', ref, 'DRV8874PWPR', g(132), y0, 0, 'HTSSOP-16 (PWP), pad termico com vias',
         side, 'C1855818', block=drv, ref_off=(-10.16, -15.24), val_off=(-10.16, 15.24))
    S.conn(ref, '1', en); S.conn(ref, '2', ph); S.conn(ref, '3', 'DRV_SLEEP'); S.conn(ref, '5', 'VREF')
    # PMODE, IMODE, GND, PGND, PAD -> GND bus
    pts = [S.pinpos(ref, p) for p in ('16', '7', '15', '9', '17')]
    xb = pts[0][0] - 2.54
    for (x, y, _, _), p in zip(pts, ('16', '7', '15', '9', '17')):
        S.wire(x, y, xb, y); S.intent.append((ref, p, 'GND'))
    for a, b in zip(pts, pts[1:]): S.wire(xb, a[1], xb, b[1])
    for (x, y, _, _) in pts[1:-1]: S.junction(xb, y)
    S.wire(xb, pts[-1][1], xb, pts[-1][1] + 2.54); S.power('GND', xb, pts[-1][1] + 2.54)
    S.conn(ref, '11', 'VBAT', bend='up'); S.conn(ref, '12', 'VCP' + sfx); S.conn(ref, '13', 'CPH' + sfx); S.conn(ref, '14', 'CPL' + sfx)
    S.conn(ref, '8', 'OUT' + sfx + '1'); S.conn(ref, '10', 'OUT' + sfx + '2'); S.conn(ref, '6', 'IPROPI' + sfx); S.conn(ref, '4', None)
    C(cvcp, '100nF', g(143), y0 - g(3), pkg='0603 16 V X7R', note='VCP -> VM'); S.conn(cvcp, '1', 'VBAT'); S.conn(cvcp, '2', 'VCP' + sfx, bend='right')
    C(ccp, '22nF', g(148), y0 - g(3), pkg='0603 50 V X7R', note='CPH -> CPL (tensao >= VM)'); S.conn(ccp, '1', 'CPH' + sfx, bend='right'); S.conn(ccp, '2', 'CPL' + sfx, bend='right')
    C(cvm, '100nF', g(155), y0 - g(3), pkg='0603 25 V X7R', note='VM, junto ao pino 11'); S.conn(cvm, '1', 'VBAT'); S.conn(cvm, '2', 'GND')
    R(ripr, '1.5k 1%', g(143), y0 + g(5), note='IPROPI -> limite de corrente'); S.conn(ripr, '1', 'IPROPI' + sfx, bend='right'); S.conn(ripr, '2', 'GND')
    part('Motor', 'Motor_DC', mref, '1020 ' + side, g(156), y0 + g(6), 0, '2 pads',
         'coreless 1020 7,4 V; se girar ao contrario, inverta os fios', ref_off=(3.81, -1.27), val_off=(3.81, 1.27))
    S.conn(mref, '1', 'OUT' + sfx + '2', bend='left'); S.conn(mref, '2', 'OUT' + sfx + '1', bend='left')
hbridge('U2', g(18), '_A', 'PWMA_D5', 'DIRA_D3', 'M1', 'C13', 'C14', 'C6', 'R11', 'esq.')
hbridge('U3', g(50), '_B', 'PWMB_D6', 'DIRB_D4', 'M2', 'C15', 'C16', 'C7', 'R12', 'dir.')
R('R13', '15k 1%', g(116), g(29), note='VREF = 2,0 V'); S.conn('R13', '1', '+5V')
R('R14', '10k 1%', g(116), g(35), note='VREF = 2,0 V'); S.wire(g(116), g(29) + 3.81, g(116), g(32)); S.wire(g(116), g(32), g(116), g(35) - 3.81); S.links.append(('R13', '2', 'R14', '1')); S.wire(g(116), g(32), g(117), g(32)); S.junction(g(116), g(32)); S.label('VREF', g(117), g(32), 1, 0); S.intent += [('R13', '2', 'VREF'), ('R14', '1', 'VREF')]; S.conn('R14', '2', 'GND')
R('R15', '10k', g(124), g(29), note='nSLEEP sempre alto (pull-down interno de 100k)'); S.conn('R15', '1', '+5V'); S.conn('R15', '2', 'DRV_SLEEP', bend='right')
note(['PMODE = GND: modo PH/EN (EN = PWM, PH = sentido), como o DIR/PWM do IFX9201.',
      'IMODE = GND: corte por tempo fixo e religamento automatico (nunca trava a saida na corrida).',
      'ITRIP = VREF / (450 uA/A x R_IPROPI) = 2,0 V / (450 uA/A x 1,5 k) = ~3,0 A.',
      'Ajuste: troque R13/R14 (VREF ate 3,6 V) ou R11/R12. nFAULT sem uso.',
      'PH = 0 -> OUT2 positivo (o firmware usa D3/D4 = 0 para frente).'], 282.0, g(61) + 1.27)

# ---------------------------------------------------------------- 6 VENTOINHA
frame(280, 174, 410, 248, '6 - VENTOINHA (coreless 1020 + rotor centrifugo)')
part('Motor', 'Motor_DC', 'M3', 'ventoinha', g(138), g(77), 0, '2 pads', 'coreless 1020 7,4 V',
     ref_off=(3.81, -1.27), val_off=(3.81, 1.27))
S.conn('M3', '1', 'VBAT'); S.conn('M3', '2', 'OUT_C', bend='right')
part('Device', 'D_Schottky', 'D1', '1N5819', g(150), g(77), 270, 'SOD-123 (B5819W) ou 1N5819 nos terminais do motor',
     'diodo de roda livre (novo; o EVA-RT nao tem)', ref_off=(2.54, -1.27), val_off=(2.54, 1.27))
S.conn('D1', '1', 'VBAT'); S.conn('D1', '2', 'OUT_C', bend='right')
part('Device', 'Q_NMOS_GSD', 'Q1', 'AO3400A', g(140), g(88), 0, 'SOT-23 (1 = G, 2 = S, 3 = D)',
     'no lugar do IRFR3411/RM10N100LD; liga totalmente com 5 V no gate', 'C20917', ref_off=(5.08, -1.27), val_off=(5.08, 1.27))
S.conn('Q1', '3', 'OUT_C', bend='right'); S.conn('Q1', '2', 'GND')
R('R9', '200', g(130), g(88), r=90, note='gate'); S.conn('R9', '1', 'PWMC_D10')
R('R8', '10k', g(135), g(88) + 3.81, note='gate -> GND (desligado no boot)')
xg, yg, _, _ = S.pinpos('Q1', '1'); x9, y9, _, _ = S.pinpos('R9', '2'); x8, y8, _, _ = S.pinpos('R8', '1')
S.wire(x9, y9, x8, y8); S.wire(x8, y8, xg, yg); S.junction(x8, y8)
S.links += [('R9', '2', 'R8', '1'), ('R8', '1', 'Q1', '1')]
S.conn('R8', '2', 'GND')
C('C8', '100nF', g(156), g(77), pkg='0603 25 V'); S.conn('C8', '1', 'VBAT'); S.conn('C8', '2', 'GND')
note(['Q1 do lado do GND, PWM no D10 (Timer1), como no EVA-RT.',
      'AO3400A: 30 V, 5,7 A, ~30 mOhm com 4,5 V no gate.'], 282.0, g(95))

# ---------------------------------------------------------------- 7 INTERFACE
frame(146, 164, 276, 224, '7 - INTERFACE (botoes e LEDs da placa)')
for i, (sw, net, lbl) in enumerate([('SW1', 'B1_D11', 'BOTAO 1'), ('SW2', 'B2_D12', 'BOTAO 2')]):
    part('Switch', 'SW_Push', sw, lbl, g(66), g(71 + 6 * i), 0, 'botao tatil 2 pinos (furo) ou B3U-1000P', '',
         ref_off=(-2.54, -2.54), val_off=(-2.54, 3.81))
    S.conn(sw, '1', net); S.conn(sw, '2', 'GND', bend='down')
R('R5', '1k', g(84), g(71), r=90); S.conn('R5', '1', 'LEDC_D13')
LED('LED4', 'LED C', g(84) + 7.62, g(71), r=180, note='vermelho; o LED3 em paralelo do EVA-RT foi retirado')
S.links.append(('R5', '2', 'LED4', '2')); S.conn('LED4', '1', 'GND', bend='down')
R('R1', '1k', g(84), g(77), r=90); S.conn('R1', '1', '+5V')
LED('LED6', 'TX', g(84) + 7.62, g(77), r=180); S.links.append(('R1', '2', 'LED6', '2')); S.conn('LED6', '1', 'TX_D1')
R('R2', '1k', g(84), g(83), r=90, note='nao montar com R18 = 4,7k'); S.conn('R2', '1', '+5V')
LED('LED7', 'RX (opcional)', g(84) + 7.62, g(83), r=180, note='nao montar com R18 = 4,7k')
S.links.append(('R2', '2', 'LED7', '2')); S.conn('LED7', '1', 'RX_D0')
note(['Botoes: menu do EVA-RT (1 = calibrar/partir, 2 = menu/+velocidade). LED C: calibracao e menu.',
      'LED6/LED7 piscam com trafego na serial. Com R18 = 4,7k, LED7 e R2 nao sao montados.'], 148.59, g(86))

# ---------------------------------------------------------------- 8 GRAVACAO / BT / ICSP
frame(10, 228, 276, 287, '8 - GRAVACAO, BLUETOOTH E ICSP')
part('Connector_Generic', 'Conn_01x05', 'J3', 'GRAVACAO (barra 1x5 2,54 deitada)', g(22), g(97), 0,
     '5 pads SMD 1,25 x 2,25 + barra macho 1x5 2,54 deitada', 'borda traseira, face de baixo (como o EVA-RT)', ref_off=(-2.54, -7.62), val_off=(2.54, -7.62))
for p, n in zip('12345', ['+5V', 'GND', 'RX_D0', 'TX_D1', 'DTR']): S.conn('J3', p, n, stub=7.62 if n in ('+5V', 'GND') else 2.54)
C('C17', '100nF', g(32), g(104), r=90, note='reset automatico pelo DTR'); S.conn('C17', '1', 'DTR'); S.conn('C17', '2', 'RESET')
part('Connector_Generic', 'Conn_01x06', 'J4', 'BLUETOOTH (femea 1x6, ordem HC-05)', g(70), g(97), 0,
     'barra femea 1x6 2,54 mm', 'frente direita, x = 32,5; HC-06 nas vias 2-5 (virado)', ref_off=(-2.54, -10.16), val_off=(2.54, -10.16))
for p, n in zip('123456', [None, 'BT_RXD', 'BT_TXD', 'GND', '+5V', None]): S.conn('J4', p, n, stub=7.62 if n in ('+5V', 'GND') else 2.54)
R('R16', '1k', g(48), g(95), r=90, note='divisor 5 V -> 3,3 V'); S.conn('R16', '1', 'TX_D1'); S.conn('R16', '2', 'BT_RXD')
R('R17', '2k', g(56), g(98), note='divisor 5 V -> 3,3 V'); S.conn('R17', '1', 'BT_RXD', bend='right'); S.conn('R17', '2', 'GND')
R('R18', '4.7k', g(48), g(103), r=90, note='4,7k: grava com o HC-05 encaixado (LED7/R2 nao montados); 0 ohm se montar o LED7')
S.conn('R18', '1', 'RX_D0'); S.conn('R18', '2', 'BT_TXD')
part('Connector', 'AVR-ISP-6', 'J5', 'ICSP (pads SMD embaixo)', g(90), g(99), 0, '6 pads SMD D1,8 em grade 2,54',
     'posicoes do EVA-RT: x 33,97/36,51; y -8,36/-10,90/-13,44', ref_off=(5.08, -12.7), val_off=(5.08, 12.7))
S.conn('J5', '1', 'B2_D12'); S.conn('J5', '4', 'B1_D11'); S.conn('J5', '3', 'LEDC_D13'); S.conn('J5', '5', 'RESET')
S.conn('J5', '2', '+5V'); S.conn('J5', '6', 'GND')
note(['J3: 1 +5V, 2 GND, 3 RX (<- TXD do conversor), 4 TX (-> RXD do conversor), 5 DTR. Conversor CH340G com DTR, em 5 V.',
      'J4: com R18 = 4,7k o conversor ganha do modulo no RX: grava com o HC-05 encaixado. Com R18 = 0 e LED7, tire o modulo. 115200 (AT). HC-06 nas vias 2-5.',
      'J5: bootloader com Arduino Uno + ArduinoISP (D10 -> RST, D11 -> MOSI, D12 -> MISO, D13 -> SCK, 10 uF no RESET do Uno).'],
     12.7, g(108) + 1.27)

# footprints da placa (biblioteca seguidor_alpha, gerada por ferramentas/preview/kicad_exportar.py)
if os.path.exists('footprints_alpha.json'):
    for ref, fp in json.load(open('footprints_alpha.json')).items():
        if ref in S.syms:
            S.syms[ref]['footprint'] = fp
open('seguidor_base.kicad_sch', 'w').write(S.render())
json.dump(dict(intent=S.intent, links=S.links, ncs=S.ncs, bom=BOM), open('intent.json', 'w'), indent=1)
print('ok', len(S.syms), 'simbolos')
