import sys, io, contextlib
import build_pos as B, fixos, place_lib as L
with contextlib.redirect_stdout(io.StringIO()):
    fixos.primeiro(B.PLACED, B.colocar)
    fixos.satelites(B.PLACED, B.colocar, B.satelite, B.ancora, B.buscar, B.custo, B.pad_xy)
P = B.PLACED
def ver(ref, x, y, rot, lado=None, n=8):
    c = L.comp(ref, x, y, rot, lado)
    e, a = L.avaliar(c, {k: v for k, v in P.items() if k != ref})
    print("%-4s (%6.2f,%6.2f) rot %4d -> erros=%d %s" % (ref, x, y, rot, len(e), e[:n]))
    return c
print("Q1 candidatos (C8 e SW1 ja colocados):")
for x, y in [(25.8, 5.6), (25.5, 4.6), (26.0, 4.2)]:
    for r in (0, 90, 180, 270):
        ver("Q1", x, y, r)
print("U2/U3 nas posicoes do IFX:")
ver("U2", -22.10, -12.45, -90); ver("U3", 22.10, -12.45, 90)
print("posicoes atuais:")
for r in ["U2", "U3", "Q1", "C8", "SW1", "D1", "R16", "R17", "R18", "X1", "C12"]:
    if r in P:
        c = P[r]; print(r, round(c["x"], 2), round(c["y"], 2), c["rot"], c["lado"])
print("pads U2:", [(p["pin"], p["net"], round(p["c"][0], 2), round(p["c"][1], 2)) for p in P["U2"]["pads"]])
