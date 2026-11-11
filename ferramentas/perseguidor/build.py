import sys, os, json, shutil, math; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from epro import *
import j6
from router import Grid
SRC, DST = sys.argv[1], sys.argv[2]
J6X, J6Y, J6ROT = -1480.0, 300.0, 90
NET_IR = 'IR_A5'
W_SIG, W_PWR = 9.843, 19.685
if os.path.exists(DST): shutil.rmtree(DST)
shutil.copytree(SRC, DST)
p = Proj(DST)
dump = lambda r: json.dumps(r, ensure_ascii=False, separators=(',', ':'))

# ---------- footprint ----------
fp6 = load_lines(os.path.join(DST, 'FOOTPRINT', '7d85cc9e83660af2.efoo'))
hdr = j6.footprint_lines()
mid = [r for r in fp6 if r[0] in ('LAYER', 'ACTIVE_LAYER', 'LAYER_PHYS', 'PREFERENCE')]
body, fp_pads, _ = j6.footprint_body(None, J6ROT)
fp_all = hdr + mid + body
with open(os.path.join(DST, 'FOOTPRINT', j6.FP_UUID + '.efoo'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(dump(r) for r in fp_all) + '\n')
sym, sym_pins = j6.symbol_lines()
with open(os.path.join(DST, 'SYMBOL', j6.SYM_UUID + '.esym'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(dump(r) for r in sym) + '\n')
pj = p.pj
pj['footprints'][j6.FP_UUID] = j6.footprint_entry()
pj['symbols'][j6.SYM_UUID] = j6.symbol_entry()
pj['devices'][j6.DEV_UUID] = j6.device_entry()
pj['config']['title'] = 'RUSH - SATURN - perseguidor - entalhe A - IR'
json.dump(pj, open(os.path.join(DST, 'project.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
p = Proj(DST)   # recarrega com o footprint novo

# ---------- PCB: componente J6 ----------
SCH_ID = 'e3400'
PCB_ID = 'e300001'
nid = [300001]
def new_id():
    nid[0] += 1; return f"e{nid[0]}"
pins_net = {'1': NET_IR, '2': '+5V', '3': 'GND'}
comp = ["COMPONENT", PCB_ID, 0, 1, J6X, J6Y, J6ROT, {"Name": "RECEPTOR IR (KY-022)", "Description": "barra femea 1x3; 1 = S (A5), 2 = +5V, 3 = GND",
        "Unique ID": "gge68", "Reuse Block": "", "Group ID": "", "Channel ID": "$1" + SCH_ID, "Value": "KY-022 (femea 1x3, S + -)",
        "Encapsulamento": "barra femea 1x3 2,54 mm", "DNP": "no"}, 1]
attrs = [["ATTR", new_id(), 0, PCB_ID, 3, None, None, "Footprint", j6.FP_UUID, 0, 0, "default", 45, 6, 0, 0, 3, 450, 0, 0, 0, False],
         ["ATTR", new_id(), 0, PCB_ID, 3, None, None, "Device", j6.DEV_UUID, 0, 0, "default", 45, 6, 0, 0, 3, 450, 0, 0, 0, False],
         ["ATTR", new_id(), 0, PCB_ID, 3, J6X - 30, J6Y + 205, "Designator", "J6", 0, 1, "default", 45, 6, 0, 0, 3, 720, 0, 0, 0, False]]
padnets = []
for r in body:
    if r[0] == 'PAD': padnets.append(["PAD_NET", PCB_ID, r[5], pins_net[r[5]], r[1], 0])
    else: padnets.append(["PAD_NET", PCB_ID, "", "", r[1], 0])
# rede: MARK_L_A5 -> IR_A5 (pino 28 do ATmega)
for r in p.pcb:
    if r[0] == 'NET' and r[1] == 'MARK_L_A5': r[1] = NET_IR
    if r[0] == 'PAD_NET' and r[3] == 'MARK_L_A5': r[3] = NET_IR
# insere depois do último bloco de componente (antes do primeiro LINE)
first_line = next(i for i, r in enumerate(p.pcb) if r[0] in ('LINE', 'VIA', 'POLY', 'FILL'))
p.pcb[first_line:first_line] = [comp] + attrs + padnets
p.parse()
assert p.byref['J6']['attrs']['Footprint'] == j6.FP_UUID
J6pads = {q['num']: q for q in p.comp_pads(p.byref['J6'])}
for k, q in sorted(J6pads.items()): print('J6', k, q['net'], round(q['x'] * MIL, 3), round(q['y'] * MIL, 3))

# ---------- roteamento ----------
new_recs = []
def add_route(net, start, goal, width, **kw):
    g = Grid(p, net=net, width_mil=width, clr_mil=10.0, hole_clr_mil=55.0)
    path = g.route([start], [goal], via_cost=80)
    assert path, 'sem caminho para ' + net
    segs = g.to_segments(path)
    # cola as pontas nos centros exatos dos pads
    if segs and segs[0][0] == 'L':
        s = list(segs[0]); s[2], s[3] = start[0], start[1]; segs[0] = tuple(s)
    if segs and segs[-1][0] == 'L':
        s = list(segs[-1]); s[4], s[5] = goal[0], goal[1]; segs[-1] = tuple(s)
    for s in segs:
        if s[0] == 'L':
            r = ["LINE", new_id(), 0, net, s[1], round(s[2], 4), round(s[3], 4), round(s[4], 4), round(s[5], 4), width, 0]
        else:
            r = ["VIA", new_id(), 0, net, "", round(s[1], 4), round(s[2], 4), 11.811, 23.622, 0, None, None, 0, []]
        p.pcb.append(r); new_recs.append(r)
    print(net, len(segs), 'segmentos', sum(1 for s in segs if s[0] == 'V'), 'vias')
u1_5v = [q for q in p.comp_pads(p.byref['U1']) if q['num'] == '3'][0]
u2_28 = [q for q in p.comp_pads(p.byref['U2']) if q['num'] == '28'][0]
add_route('+5V', (u1_5v['x'], u1_5v['y'], 1), (J6pads['2']['x'], J6pads['2']['y'], 12), W_PWR)
add_route(NET_IR, (u2_28['x'], u2_28['y'], 1), (J6pads['1']['x'], J6pads['1']['y'], 12), W_SIG)

# ---------- polígonos: apaga o preenchimento antigo (refazer no EasyEDA) ----------
if '--keep-poured' not in sys.argv:
    p.pcb = [r for r in p.pcb if r[0] != 'POURED']
with open(p.pcbpath, 'w', encoding='utf-8') as f:
    f.write('\n'.join(dump(r) for r in p.pcb) + '\n')

# ---------- esquemático ----------
sd = os.path.join(DST, 'SHEET'); sub = os.listdir(sd)[0]; sp = os.path.join(sd, sub, '1.esch')
S = load_lines(sp)
for r in S:   # rótulo do pino 28 do ATmega
    if r[0] == 'ATTR' and r[3] == 'NET' and r[4] == 'MARK_L_A5' and r[2] == 'e2306': r[4] = NET_IR
CX, CY = 800, 425
sid = [3400]
def sch_id():
    sid[0] += 1; return f"e{sid[0]}"
add = [["COMPONENT", SCH_ID, "Header-Female-2.54_1x3.1", CX, CY, 0, 0, {}, 0]]
for key, val, vis, x, y in (("Device", j6.DEV_UUID, 0, None, None), ("Symbol", j6.SYM_UUID, 0, None, None), ("Footprint", None, 0, None, None),
                            ("Unique ID", "gge68", 0, None, None), ("Designator", "J6", 1, CX - 10, CY + 25), ("Name", "RECEPTOR IR (KY-022)", 1, CX - 30, CY - 25),
                            ("Reuse Block", "", 0, None, None), ("Group ID", "", 0, None, None), ("Channel ID", "", 0, None, None),
                            ("Value", "KY-022 (femea 1x3, S + -)", 0, None, None), ("Description", "barra femea 1x3; 1 = S (A5), 2 = +5V, 3 = GND", 0, None, None),
                            ("Encapsulamento", "barra femea 1x3 2,54 mm", 0, None, None), ("Add into BOM", "yes", 0, None, None),
                            ("Convert to PCB", "yes", 0, None, None), ("DNP", "no", 0, None, None)):
    add.append(["ATTR", sch_id(), SCH_ID, key, val, 0, vis, x, y, 0, "st5" if key in ("Designator", "Name", "Symbol", "Footprint") else "st1", 0])
for pid, num, px, py in sym_pins:
    x, y = CX + px, CY + py
    wid = sch_id()
    add.append(["WIRE", wid, [[x, y, x - 30, y]], "st13", 0])
    add.append(["ATTR", sch_id(), wid, "NET", pins_net[num], 0, 1, x - 30, y, 0, "st14", 0])
add.append(["TEXT", sch_id(), CX - 80, CY + 45, 0, "Receptor IR KY-022 (S no A5; A5 so e lido pelo ADC no firmware EVA-RT)", "st14"])
S += add
with open(sp, 'w', encoding='utf-8') as f:
    f.write('\n'.join(dump(r) for r in S) + '\n')
print('ok')
