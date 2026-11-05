"""Grades de restricao (0,1 mm): cobre valido, areas de contato/sombra por face. Sem scipy."""
import numpy as np, time
from matplotlib.path import Path
import geo

X0, X1, DX = -75.0, 75.0, 0.1
Y0, Y1 = -45.0, 30.0
GX = np.arange(X0, X1 + 1e-9, DX)
GY = np.arange(Y0, Y1 + 1e-9, DX)
NX, NY = len(GX), len(GY)
MX, MY = np.meshgrid(GX, GY, indexing="ij")
PTS = np.column_stack([MX.ravel(), MY.ravel()])
MARGEM_COBRE = 0.3

def ij(x, y):
    i = int(round((x - X0) / DX)); j = int(round((y - Y0) / DX))
    return i, j

def dist_polyline(P, A):
    """Distancia de cada ponto de P ao contorno fechado A (poligono)."""
    B = np.roll(A, -1, axis=0); AB = B - A; L2 = (AB ** 2).sum(1)
    out = np.empty(len(P))
    for k in range(0, len(P), 20000):
        p = P[k:k + 20000]
        AP = p[:, None, :] - A[None]
        t = np.clip((AP * AB[None]).sum(2) / L2[None], 0, 1)
        proj = A[None] + t[..., None] * AB[None]
        out[k:k + 20000] = np.sqrt(((p[:, None, :] - proj) ** 2).sum(2)).min(1)
    return out

def parity_mask(polys, bbox_pad=0.5):
    """Mascara par-impar (regra do geometria.json) dos poligonos de uma area."""
    m = np.zeros(len(PTS), dtype=bool)
    for poly in polys:
        P = np.asarray(poly, float)
        x0, y0 = P.min(0) - bbox_pad; x1, y1 = P.max(0) + bbox_pad
        sel = (PTS[:, 0] >= x0) & (PTS[:, 0] <= x1) & (PTS[:, 1] >= y0) & (PTS[:, 1] <= y1)
        inside = np.zeros(len(PTS), dtype=bool)
        inside[sel] = Path(P).contains_points(PTS[sel])
        m ^= inside
    return m.reshape(NX, NY)

def build():
    t0 = time.time()
    board = parity_mask([geo.CONTORNO])
    dist_b = dist_polyline(PTS, geo.CONTORNO).reshape(NX, NY)
    ok = board & (dist_b >= MARGEM_COBRE)
    for h in geo.HOLES:
        if h["tipo"] == "furo":
            d = np.hypot(MX - h["x"], MY - h["y"]) - h["d"] / 2
        else:
            dx = np.maximum(np.abs(MX - h["x"]) - h["w"] / 2, 0)
            dy = np.maximum(np.abs(MY - h["y"]) - h["h"] / 2, 0)
            d = np.hypot(dx, dy)
        ok &= d >= MARGEM_COBRE
    top_con = np.zeros((NX, NY), bool); soft = np.zeros((NX, NY), bool)
    bot_con = np.zeros((NX, NY), bool)
    top_lim = np.full((NX, NY), 99.0)
    names_top = {}
    for a in geo.G["areas"]:
        m = parity_mask(a["poligonos"]).reshape(NX, NY) if False else None
        mm = parity_mask(a["poligonos"])
        mm = mm.reshape(NX, NY)
        if a["tipo"] == "contato":
            if a["face"] == "TOP":
                if "suporte_bateria" in a["nome"]:
                    soft |= mm
                else:
                    top_con |= mm
            else:
                bot_con |= mm
        elif a["tipo"] == "sombra" and a["face"] == "TOP":
            lim = a["altura_min_mm"] - 0.3
            top_lim = np.where(mm, np.minimum(top_lim, lim), top_lim)
    np.savez_compressed(geo.P + "/grades.npz", ok=ok, top_con=top_con, bot_con=bot_con,
                        soft=soft, top_lim=top_lim)
    print("grades prontas em %.1f s; cobre valido = %d celulas" % (time.time() - t0, ok.sum()))

if __name__ == "__main__":
    build()
