"""Monta POS: posicoes fixas (EVA-RT mantido + novos fixos) e busca de satelites/botoes com as checagens."""
import json, sys, numpy as np
import geo, footprints as F, place_lib as L

PLACED = {}
LOG = []          # (ref, x, y, rot, lado, motivo, erros, avisos)
MOTIVO = {}

def custo(c):
    """Atracao por rede (sem GND, que e plano): distancia de cada pad ao pad mais proximo da mesma rede."""
    tot = 0.0; n = 0
    for p in c["pads"]:
        if p["net"] in (None, "GND"): continue
        best = None
        for r2, o in PLACED.items():
            if o["dnp"]: continue
            for q in o["pads"]:
                if q["net"] == p["net"]:
                    d = float(np.hypot(*(p["c"] - q["c"])))
                    best = d if best is None or d < best else best
        if best is not None:
            tot += best; n += 1
    return tot, n

def pad_xy(ref, pin):
    for p in PLACED[ref]["pads"]:
        if p["pin"] == str(pin):
            return p["c"]
    raise KeyError((ref, pin))

def colocar(ref, x, y, rot, lado=None, motivo="", dnp=False, fixo=True):
    c = L.comp(ref, x, y, rot, lado, dnp=dnp)
    erros, avisos = L.avaliar(c, PLACED)
    PLACED[ref] = c
    LOG.append(dict(ref=ref, x=round(x, 3), y=round(y, 3), rot=rot, lado=c["lado"], motivo=motivo,
                    erros=erros, avisos=avisos, fixo=fixo, dnp=dnp))
    return erros, avisos

def custo_alvo(c, alvo, modo="soma"):
    """Distancia do pad mais proximo do componente a cada pino-alvo (soma ou minimo dos alvos)."""
    ds = [min(float(np.hypot(*(p["c"] - pt))) for p in c["pads"]) for pt in alvo]
    return sum(ds) if modo == "soma" else min(ds)

def buscar(ref, cx, cy, raio, rots, lado=None, passo=0.5, topn=5, peso_centro=0.02, alvo=None, modo="soma"):
    res = []
    xs = np.arange(cx - raio, cx + raio + 1e-9, passo)
    ys = np.arange(cy - raio, cy + raio + 1e-9, passo)
    for rot in rots:
        for x in xs:
            for y in ys:
                c = L.comp(ref, round(float(x), 3), round(float(y), 3), rot, lado)
                e, a = L.avaliar(c, PLACED)
                if e: continue
                if alvo is not None:
                    t = custo_alvo(c, alvo, modo); n = len(alvo)
                else:
                    t, n = custo(c)
                res.append((t + peso_centro * np.hypot(x - cx, y - cy), round(float(x), 3), round(float(y), 3), rot, t, n, a))
    res.sort(key=lambda r: r[0])
    return res[:topn]

def satelite(ref, cx, cy, raio, rots, lado=None, motivo="", passo=0.5, alvo=None, modo="soma"):
    top = buscar(ref, cx, cy, raio, rots, lado, passo, alvo=alvo, modo=modo)
    if not top:
        print("!! sem posicao valida para", ref); return None
    best = top[0]
    fino = buscar(ref, best[1], best[2], 0.5, [best[3]], lado, 0.1, topn=1, alvo=alvo, modo=modo)
    _, x, y, rot, t, n, a = fino[0] if fino else best
    erros, avisos = colocar(ref, x, y, rot, lado, motivo, fixo=False)
    print("%-6s (%7.2f, %7.2f) rot %4d custo %.2f mm (%d) avisos=%d erros=%d" %
          (ref, x, y, rot, t, n, len(avisos), len(erros)))
    return (x, y, rot)

def ancora(refpin_list):
    pts = [pad_xy(r, p) for r, p in refpin_list]
    return float(np.mean([p[0] for p in pts])), float(np.mean([p[1] for p in pts]))

if __name__ == "__main__":
    import fixos
    fixos.primeiro(PLACED, colocar)
    print("FIXOS montados:", len(PLACED))
    fixos.satelites(PLACED, colocar, satelite, ancora, buscar, custo, pad_xy)
    out = []
    for item in LOG:
        out.append(item)
    json.dump(out, open(geo.P + "/log_build.json", "w"), indent=1, ensure_ascii=False, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    print("total de componentes:", len(PLACED))
    for it in LOG:
        if it["erros"]:
            print("ERRO", it["ref"], it["erros"][:4])
        if it["fixo"] and it["avisos"]:
            print("AVISO-FIXO", it["ref"], it["avisos"][:2])
