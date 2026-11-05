"""Verificacao final: checagem completa, regras de proximidade, ratsnest, exportacao (posicoes.csv, JSON)."""
import os as _os
_REPO = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))
import io, csv, json, re, contextlib, math
import numpy as np
import geo, footprints as F, place_lib as L
import build_pos as B, fixos

BOM = _REPO + "/hardware/seguidor_base/BOM_seguidor_base.csv"
EVA = geo.P + "/eva_rt_componentes.csv"

with contextlib.redirect_stdout(io.StringIO()):
    fixos.primeiro(B.PLACED, B.colocar)
    fixos.satelites(B.PLACED, B.colocar, B.satelite, B.ancora, B.buscar, B.custo, B.pad_xy)
P = B.PLACED
# 1) checagem completa: cada componente contra todos os outros (exceto DNP)
erros_all, avisos_all = {}, {}
for ref, c in P.items():
    others = {k: v for k, v in P.items() if k != ref}
    e, a = L.avaliar(c, others)
    if e: erros_all[ref] = e
    if a: avisos_all[ref] = a
# 2) pares de cortesia sobrepostos (mesma face ou THT)
pares = []
refs = [r for r in P if not P[r]["dnp"]]
for i in range(len(refs)):
    for j in range(i + 1, len(refs)):
        a, b = P[refs[i]], P[refs[j]]
        if a["face"] == b["face"] or a["tht"] or b["tht"]:
            if geo.sat_overlap(a["court"], b["court"]): pares.append((refs[i], refs[j]))
print("componentes posicionados:", len(P), "| DNP:", [r for r in P if P[r]["dnp"]])
print("PARES com cortesia sobreposta:", pares)
print("ERROS (checagem completa):", erros_all if erros_all else "nenhum")
print("AVISOS:")
for r, a in avisos_all.items():
    print("  ", r, sorted(set(a))[:3])
# 3) regras de proximidade (pino-alvo)
def dist(ref, pin, alvo_ref, alvo_pin):
    pa = [p["c"] for p in P[ref]["pads"]]; pb = B.pad_xy(alvo_ref, alvo_pin)
    return min(float(np.hypot(*(q - pb))) for q in pa)
regras = [("C6", "U2", 11), ("C7", "U3", 11), ("C13", "U2", 12), ("C15", "U3", 12), ("C14", "U2", 13), ("C16", "U3", 13),
          ("C9", "U1", 4), ("C10", "U1", 20), ("C11", "U1", 7), ("C12", "U1", 8)]
print("DISTANCIA dos desacoplamentos ao pino (mm):")
for ref, tr, tp in regras:
    print("   %-4s -> %s.%d : %.2f" % (ref, tr, tp, min(dist(ref, None, tr, tp) for _ in [0])))
# 4) ratsnest por rede (Prim) e categorias
def mst(pts):
    if len(pts) < 2: return [], 0.0
    n = len(pts); inT = [False]*n; best = [1e9]*n; par = [-1]*n; best[0] = 0; edges = []; tot = 0.0
    for _ in range(n):
        u = min((k for k in range(n) if not inT[k]), key=lambda k: best[k]); inT[u] = True
        if par[u] >= 0:
            edges.append((pts[par[u]], pts[u])); tot += best[u]
        for v in range(n):
            if not inT[v]:
                d = float(np.hypot(*(pts[u] - pts[v])))
                if d < best[v]: best[v] = d; par[v] = u
    return edges, tot
redes = {}
for net, lst in L.NET2PINS.items():
    pts = []
    for pin in lst:
        ref, num = pin.split(".")
        if ref not in P or P[ref]["dnp"]: continue
        for p in P[ref]["pads"]:
            if p["pin"] == num and p["net"] == net:
                pts.append(p["c"])
    if len(pts) >= 2:
        e, t = mst(pts); redes[net] = dict(edges=[(a.tolist(), b.tolist()) for a, b in e], total=t, n=len(pts))
cats = {"VBAT e +5V": ["VBAT", "+5V"], "GND": ["GND"], "saidas dos motores (OUT_*)": None}
tot = {"VBAT e +5V": 0.0, "GND": 0.0, "saidas dos motores (OUT_*)": 0.0, "sinais e demais": 0.0}
for net, d in redes.items():
    if net in ("VBAT", "+5V"): tot["VBAT e +5V"] += d["total"]
    elif net == "GND": tot["GND"] += d["total"]
    elif net.startswith("OUT_"): tot["saidas dos motores (OUT_*)"] += d["total"]
    else: tot["sinais e demais"] += d["total"]
print("RATSNEST total por categoria (mm):", {k: round(v, 1) for k, v in tot.items()})
# 5) CSV de posicoes
rows = list(csv.reader(open(BOM, encoding="utf-8-sig"), delimiter=";"))[1:]
valor = {}
for r in rows:
    for ref in r[1].split():
        valor[ref] = r[2]
eva = {}
for r in csv.reader(open(EVA, encoding="utf-8"), delimiter=";"):
    if r[0] == "ref": continue
    eva[r[0]] = dict(lado=r[2], x=float(r[3]), y=float(r[4]), rot=float(r[5]))
out = []
for ref in sorted(P, key=lambda k: (re.match(r"[A-Z]+", k).group(0), int(re.search(r"\d+", k).group(0)))):
    c = P[ref]
    fpname = F.REF_FOOTPRINT[ref]
    e0 = eva.get(ref)
    mudou = "sim"
    if e0 is not None:
        moved = math.hypot(c["x"] - e0["x"], c["y"] - e0["y"])
        rot_diff = (round(c["rot"] - e0["rot"]) % 360) != 0
        lado_diff = (c["lado"] != ("BOTTOM" if e0["lado"] == "BOT" else "TOP"))
        mudou = "sim" if (moved > 0.05 or rot_diff or lado_diff) else "nao"
    out.append(dict(ref=ref, valor=valor.get(ref, ""), footprint=fpname, face=c["lado"], x=round(c["x"], 3), y=round(c["y"], 3),
                    rot=c["rot"], mudou=mudou, dnp=c["dnp"], eva=e0, tht=c["tht"]))
json.dump(out, open(geo.P + "/posicoes.json", "w"), indent=1, ensure_ascii=False, default=float)
json.dump(redes, open(geo.P + "/ratsnest.json", "w"), indent=1)
with open(geo.P + "/posicoes.csv", "w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh, delimiter=";")
    w.writerow(["ref", "valor", "footprint", "face", "x_mm", "y_mm", "rot_graus", "mudou_do_EVA-RT", "motivo"])
    motivos = {}
    for it in B.LOG:
        motivos[it["ref"]] = it["motivo"]
    for it in out:
        mot = motivos.get(it["ref"], "")
        if it["dnp"]: mot = "DNP (nao montar; pode apagar no layout). " + mot
        w.writerow([it["ref"], it["valor"], it["footprint"], it["face"], f'{it["x"]:.3f}'.replace(".", ","),
                    f'{it["y"]:.3f}'.replace(".", ","), f'{it["rot"]:g}', it["mudou"], mot])
print("posicoes.csv gravado com", len(out), "linhas")
print("sem BOM:", sorted(set(valor) - set(P)), "| BOM sem posicao:", sorted(set(valor) - set(P)))
