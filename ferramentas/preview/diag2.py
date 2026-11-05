import io, contextlib, collections, numpy as np
import build_pos as B, fixos, place_lib as L
with contextlib.redirect_stdout(io.StringIO()):
    fixos.primeiro(B.PLACED, B.colocar)
    a = B.ancora([("M3", 1)]); B.satelite("C8", a[0], a[1], 4.0, [0, 90, 180, 270])
    a = B.ancora([("M3", 1), ("M3", 2)]); B.satelite("D1", a[0], a[1], 4.0, [0, 90, 180, 270])
P = B.PLACED
for r in ["C8", "D1", "SW1", "C2", "R8", "R9", "M3"]:
    c = P[r]; print(r, round(c["x"], 2), round(c["y"], 2), c["rot"])
cnt = collections.Counter(); melhores = []
for rot in (0, 90, 180, 270):
    for x in np.arange(22.0, 31.01, 0.25):
        for y in np.arange(-7.0, 8.01, 0.25):
            c = L.comp("Q1", round(float(x), 2), round(float(y), 2), rot)
            e, a2 = L.avaliar(c, P)
            if not e:
                melhores.append((round(float(x), 2), round(float(y), 2), rot))
            for m in e: cnt[m.split(" ")[0] + " " + m.split(" ")[1] if m.startswith("cortesia") else m[:40]] += 1
print("posicoes validas Q1:", len(melhores), melhores[:10])
print("motivos mais comuns:", cnt.most_common(8))
win = [m for m in melhores if (29.72 - 6.0) <= m[0] <= (29.72 + 6.0) and (4.32 - 6.0) <= m[1] <= (4.32 + 6.0)]
print("validas dentro da janela do dreno:", len(win), win[:12])
