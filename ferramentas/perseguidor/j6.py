"""Footprint/symbol/device do J6 (fêmea 1x3 2,54 mm, KY-022)."""
import json, math
FP_UUID = 'a7c3e1f05b2d4c69'
SYM_UUID = 'b9d4f2a16c3e5d70'
DEV_UUID = 'c1e5a3b27d4f6e81'
H, W = 47.0, 31.0     # altura/largura das letras (mil)
SW = 6.0              # traço da serigrafia (mil) = 0,15 mm
PITCH = 100.0
def glyph(ch):
    h, w = H / 2, W / 2
    if ch == 'S': return [[(w, h), (-w, h), (-w, 0), (w, 0), (w, -h), (-w, -h)]]
    if ch == '+': return [[(-w, 0), (w, 0)], [(0, -w), (0, w)]]
    if ch == '-': return [[(-w, 0), (w, 0)]]
    raise ValueError(ch)
def label_polys(rot_deg):
    """letras S + - à esquerda (global -x) de cada pino, de pé para a rotação rot_deg do componente"""
    out = []
    th = math.radians(-rot_deg)
    c, s = math.cos(th), math.sin(th)
    d = 49.212 + 14 + W / 2
    for k, ch in enumerate('S+-'):
        px = (k - 1) * PITCH              # pino 1 em -100
        # centro da letra: deslocamento global (-d, 0) -> local
        gx, gy = -d, 0.0
        lx, ly = gx * c - gy * s, gx * s + gy * c
        for stroke in glyph(ch):
            pts = []
            for (ax, ay) in stroke:
                bx, by = ax * c - ay * s, ax * s + ay * c
                pts += [round(px + lx + bx, 3), round(ly + by, 3)]
            out.append(pts)
    return out
def footprint_lines(rot_for_labels=90):
    L = []
    L.append(["DOCTYPE", "FOOTPRINT", "1.8"])
    L.append(["HEAD", {"editorVersion": "2.2.C", "importFlag": 0, "uuid": FP_UUID, "title": "HDR-TH_3P-P2.54-V-F_KY022"}])
    L.append(["CANVAS", 0, 0, "mm", 10, 10, 0.03937, 0.03937, 1, 1, 0, 0, 5])
    return L
def footprint_body(layers_block, rot_for_labels=90):
    """layers_block: linhas LAYER/LAYER_PHYS/PREFERENCE copiadas do footprint de 6 vias"""
    L = []
    n = [0]
    def eid():
        n[0] += 1; return f"e{n[0]}"
    L.append(["ATTR", eid(), 0, "", 3, None, None, "Designator", "J?", 0, 0, "default", 67.5, 6, 0, 0, 3, 0, 0, 0, 0, False])
    L.append(["FILL", eid(), 0, "", 49, 0.2, 0, [["CIRCLE", -159.843, -49.212, 2.362]], 0])
    for k in range(3):
        cx = (k - 1) * PITCH
        L.append(["FILL", eid(), 0, "", 50, 0.2, 0, [[cx - 12.598, 5.906, "L", cx + 12.598, 5.906, cx + 12.598, -5.906, cx - 12.598, -5.906, cx - 12.598, 5.906]], 0])
    L.append(["POLY", eid(), 0, "", 48, 2, [-159.843, -49.212, "L", -159.843, 49.213, 159.842, 49.213, 159.842, -49.212, -159.843, -49.212], 0])
    L.append(["POLY", eid(), 0, "", 3, 10, [-50, 49.212, "L", -50, -49.212], 0])
    L.append(["POLY", eid(), 0, "", 3, 10, [-159.842, -49.212, "L", 159.842, -49.212], 0])
    L.append(["POLY", eid(), 0, "", 3, 10, [-159.842, 49.212, "L", -159.842, -49.212], 0])
    L.append(["POLY", eid(), 0, "", 3, 10, [159.842, 49.212, "L", -159.842, 49.212], 0])
    L.append(["POLY", eid(), 0, "", 3, 10, [159.842, -49.212, "L", 159.842, 49.212], 0])
    for pts in label_polys(rot_for_labels):
        path = [pts[0], pts[1], "L"] + pts[2:]
        L.append(["POLY", eid(), 0, "", 3, SW, path, 0])
    pads = []
    for num, cx in (("3", 100), ("2", 0), ("1", -100)):
        shape = ["RECT", 70.866, 70.866, 0] if num == "1" else ["ELLIPSE", 62.992, 62.992]
        pid = eid()
        L.append(["PAD", pid, 0, "", 12, num, cx, 0, 0, ["ROUND", 40.158, 40.158], shape, [], 0, 0, 0, 1, 0, None, None, None, None, 0])
        pads.append((pid, num))
    return L, pads, n[0]

def symbol_lines():
    L = []
    L.append(["DOCTYPE", "SYMBOL", "1.1"])
    L.append(["HEAD", {"originX": 0, "originY": 0, "version": "2", "symbolType": 2}])
    L.append(["PART", "Header-Female-2.54_1x3.1", {"BBOX": [-10, -15, 10, 15]}])
    L.append(["LINESTYLE", "st1", None, 0, None, 1, 1])
    L.append(["RECT", "e0", -10, 15, 10, -15, 0, 0, 0, "st1", 0])
    L.append(["CIRCLE", "e1", -5, 10, 1.5, "st1", 0])
    L.append(["FONTSTYLE", "st2", None, None, None, 8, 0, 0, 0, 0, 2, 0])
    L.append(["FONTSTYLE", "st3", None, None, None, 8, 0, 0, 0, 0, 2, 2])
    pins = []
    k = 2
    for num, name, y in (("1", "S", 10), ("2", "+", 0), ("3", "-", -10)):
        pid = f"e{100 + int(num)}"
        L.append(["PIN", pid, 1, None, -20, y, 10, 0, None, 0, 0])
        L.append(["ATTR", f"e{k}", pid, "NAME", name, 0, 1, -6.3, y - 5.91498, 0, "st2", 0]); k += 1
        L.append(["ATTR", f"e{k}", pid, "NUMBER", num, 0, 1, -10.5, y - 0.91498, 0, "st3", 0]); k += 1
        L.append(["ATTR", f"e{k}", pid, "Pin Type", "IN", 0, 0, None, None, 0, "st2", 0]); k += 1
        pins.append((pid, num, -20, y))
    L.append(["FONTSTYLE", "st4", None, None, None, 6.75, 0, 0, 0, 0, 2, 0])
    L.append(["ATTR", f"e{k}", "", "Designator", "J?", 0, 0, None, None, 0, "st4", 0])
    return L, pins

def device_entry():
    return {"uuid": DEV_UUID, "title": "Header-Female-2.54_1x3 (KY-022)", "description": "Barra de pinos femea 1x3, 2,54 mm, vertical (receptor IR KY-022)",
            "attributes": {"Symbol": SYM_UUID, "Footprint": FP_UUID, "Add into BOM": "yes", "Convert to PCB": "yes", "Designator": "J?",
                           "Name": "Header-Female-2.54_1x3", "Description": "Barra femea 1x3 2,54 mm vertical (altura 8,5 mm)",
                           "Holes Structure": "1x3P", "Pitch": "2.54mm", "Mounting Type": "Through Hole", "Number of Positions": "3P"},
            "images": None, "tag": {}, "source": "", "version": "1793767680693", "symbol_type": 2, "footprint_type": 4}
def symbol_entry():
    return {"uuid": SYM_UUID, "title": "Header-Female-2.54_1x3", "display_title": "Header-Female-2.54_1x3", "docType": 2, "type": 2,
            "description": "1*3p", "desc": "1*3p", "source": "", "version": "1793767680693"}
def footprint_entry():
    return {"uuid": FP_UUID, "title": "HDR-TH_3P-P2.54-V-F_KY022", "display_title": "HDR-TH_3P-P2.54-V-F_KY022", "docType": 4, "type": 4,
            "description": "TH-3P,P=2.54mm; femea; serigrafia S + - (KY-022)", "desc": "TH-3P,P=2.54mm; femea; serigrafia S + - (KY-022)", "source": "", "version": "1793767680693"}
