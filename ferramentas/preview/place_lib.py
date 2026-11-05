"""Checagens de posicionamento (cobre, contorno, furos, areas, cortesias, modulo BT)."""
import os as _os
_REPO = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))
import re, numpy as np
import geo, grids
import footprints as F

G = np.load(geo.P + "/grades.npz")
OK, TOP_CON, BOT_CON, SOFT, TOP_LIM = G["ok"], G["top_con"], G["bot_con"], G["soft"], G["top_lim"]
X0, DX, Y0, NX, NY = grids.X0, grids.DX, grids.Y0, grids.NX, grids.NY
PASSO = 0.1
SUCAO = (-23.1, 23.1, -27.5, 21.0)     # x0,x1,y0,y1 (contato da placa de succao, BOTTOM)
MODULO_BT = (31.6, 34.6, 0.0, 14.0)     # zona reservada ao modulo Bluetooth (J4 em x=33,0)
LEGADO_THT = {"C1", "C2"}               # THT ja estava sob a succao no EVA-RT (aviso)

def _redes():
    pin2net, net2pins = {}, {}
    txt = open(_REPO + "/hardware/seguidor_base/REDES.md", encoding="utf-8").read()
    for linha in txt.splitlines():
        m = re.match(r"\|\s*`([^`]+)`\s*\|\s*([^|]+)\|", linha)
        if not m: continue
        net = m.group(1)
        for ref, pino in re.findall(r"\b([A-Z][A-Z0-9]*)\.(\d+)\b", m.group(2)):
            pin2net[f"{ref}.{pino}"] = net
            net2pins.setdefault(net, []).append(f"{ref}.{pino}")
    return pin2net, net2pins
PIN2NET, NET2PINS = _redes()

def net_of(ref, rede):
    if rede is None: return None
    return PIN2NET.get(f"{ref}.{rede}")

def quad_points(q, step=PASSO):
    q = np.asarray(q, float)
    x0, y0 = q.min(0); x1, y1 = q.max(0)
    xs = np.arange(x0, x1 + 1e-9, step); ys = np.arange(y0, y1 + 1e-9, step)
    if len(xs) == 0 or len(ys) == 0: return q.copy()
    XX, YY = np.meshgrid(xs, ys, indexing="ij")
    P = np.column_stack([XX.ravel(), YY.ravel()])
    pos = np.ones(len(P), bool); neg = np.ones(len(P), bool)
    n = len(q)
    for k in range(n):
        a, b = q[k], q[(k + 1) % n]
        cr = (b[0] - a[0]) * (P[:, 1] - a[1]) - (b[1] - a[1]) * (P[:, 0] - a[0])
        pos &= cr >= -1e-9; neg &= cr <= 1e-9
    return P[pos | neg]

def disk_points(cx, cy, r, step=PASSO):
    xs = np.arange(cx - r, cx + r + 1e-9, step); ys = np.arange(cy - r, cy + r + 1e-9, step)
    XX, YY = np.meshgrid(xs, ys, indexing="ij")
    P = np.column_stack([XX.ravel(), YY.ravel()])
    return P[np.hypot(P[:, 0] - cx, P[:, 1] - cy) <= r + 1e-9]

def _idx(P):
    i = np.rint((P[:, 0] - X0) / DX).astype(int); j = np.rint((P[:, 1] - Y0) / DX).astype(int)
    fora = (i < 0) | (i >= NX) | (j < 0) | (j >= NY)
    return np.clip(i, 0, NX - 1), np.clip(j, 0, NY - 1), fora

def comp(ref, x, y, rot, lado=None, dnp=False):
    lado = F._lado_efetivo(ref, lado)
    fp = F.FOOTPRINTS[F.REF_FOOTPRINT[ref]]
    pads = []
    for pino, rede, q, p in geo.pad_quads(ref, x, y, rot, lado):
        net = net_of(ref, rede)
        if isinstance(q, tuple):
            _, cx, cy, r = q
            pads.append(dict(pin=pino, net=net, circ=True, c=np.array([cx, cy]), r=r, q=None, furo=p["furo"]))
        else:
            q = np.asarray(q, float)
            pads.append(dict(pin=pino, net=net, circ=False, c=q.mean(0), r=None, q=q, furo=p["furo"]))
    body = None if ref in geo.SO_PADS else geo.corpo_quad(ref, x, y, rot, lado, "corpo")
    if ref in geo.SO_PADS:
        body = None
    return dict(ref=ref, x=x, y=y, rot=rot, lado=lado, tht=bool(fp["tht"]), face=lado, dnp=dnp,
                pads=pads, body=None if body is None else np.asarray(body, float),
                court=geo.courtyard(ref, x, y, rot, lado), h=float(fp["altura_mm"]))

def pad_pts(p):
    return disk_points(p["c"][0], p["c"][1], p["r"]) if p["circ"] else quad_points(p["q"])

def avaliar(c, placed, detalhe=False):
    """Retorna (erros, avisos) para o componente c frente aos ja posicionados (dict ref->comp)."""
    erros, avisos = [], []
    ref = c["ref"]
    # cobre: dentro do contorno com folga 0,3 e fora dos furos
    for p in c["pads"]:
        if p["net"] is None and p["furo"] is None and not c["tht"] and False:
            continue
        P = pad_pts(p)
        i, j, fora = _idx(P)
        if fora.any() or not OK[i, j].all():
            erros.append(f"cobre {p['pin']} fora da placa ou perto da borda/furo")
        if p["furo"] is not None or c["tht"]:
            # pad THT: a face oposta tambem conta (contato da succao em BOTTOM)
            if BOT_CON[i, j].any():
                msg = f"pino THT {p['pin']} na area da succao"
                (avisos if ref in LEGADO_THT else erros).append(msg)
        if c["face"] == "TOP":
            if TOP_CON[i, j].any(): erros.append(f"cobre {p['pin']} em area de CONTATO (TOP)")
            if SOFT[i, j].any(): avisos.append(f"cobre {p['pin']} sobre suporte da bateria (zona hipotetica, confianca baixa)")
        else:
            if BOT_CON[i, j].any(): erros.append(f"cobre {p['pin']} em area de CONTATO (BOTTOM)")
    # corpo: contato e altura (sombra)
    if c["body"] is not None:
        P = quad_points(c["body"])
        i, j, fora = _idx(P)
        if c["face"] == "TOP":
            if TOP_CON[i, j].any(): erros.append("corpo em area de CONTATO (TOP)")
            lim = TOP_LIM[i, j]
            if (lim < c["h"] - 1e-9).any(): erros.append(f"corpo com altura {c['h']} mm sob sombra (limite {lim[lim<c['h']].min():.2f})")
            if SOFT[i, j].any(): avisos.append("corpo sobre suporte da bateria (zona hipotetica)")
        else:
            if BOT_CON[i, j].any(): erros.append("corpo em area de CONTATO (BOTTOM)")
        if fora.any(): avisos.append("corpo fora da placa (em balanco sobre a borda)")
    # modulo BT: nada na zona reservada, exceto o proprio J4
    if c["face"] == "TOP" and ref != "J4":
        x0, x1, y0, y1 = MODULO_BT
        cq = c["court"]
        if cq[:, 0].max() > x0 and cq[:, 0].min() < x1 and cq[:, 1].max() > y0 and cq[:, 1].min() < y1:
            if geo.sat_overlap(cq, np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], float)):
                erros.append("invade a zona do modulo Bluetooth (x 31,6..34,6; y 0..14)")
    # cortesias de componentes na mesma face (THT conta nas duas)
    if not c["dnp"]:
        for r2, o in placed.items():
            if o["dnp"] or r2 == ref: continue
            if c["face"] == o["face"] or c["tht"] or o["tht"]:
                if geo.sat_overlap(c["court"], o["court"]):
                    erros.append(f"cortesia sobrepoe {r2}")
    return erros, avisos

def custo_rede(c, placed):
    """Soma, por pad, da distancia ate o pad mais proximo da mesma rede ja posicionada."""
    tot = 0.0; n = 0
    for p in c["pads"]:
        if p["net"] is None: continue
        best = None
        for r2, o in placed.items():
            for q in o["pads"]:
                if q["net"] == p["net"]:
                    d = float(np.hypot(*(p["c"] - q["c"])))
                    best = d if best is None or d < best else best
        if best is not None:
            tot += best; n += 1
    return tot, n
