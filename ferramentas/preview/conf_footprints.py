"""Gera conf_footprints.png: todos os footprints na mesma escala (grade de 1 mm).

Pads dourados, furos escuros, pino 1 em vermelho, corpo em azul (linha cheia),
cortesia tracejada, origem em cruz. Desenho na convencao da biblioteca
(vista de cima do componente; J5 ja vem espelhado para a face BOTTOM).
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle  # noqa: E402
import matplotlib.patheffects as pe  # noqa: E402

import footprints as F  # noqa: E402

SAIDA = os.path.join(HERE, "conf_footprints.png")

BG = "#0d1117"
GRADE_MENOR = "#1f2933"
GRADE_MAIOR = "#34414f"
COBRE = "#d9a441"
COBRE_PIN1 = "#e5484d"
FURO = "#0d1117"
BORDA_FURO = "#8b949e"
CORPO = "#58a6ff"
CORTESIA = "#d277f2"
TEXTO = "#e6edf3"
TEXTO_FRACO = "#8b949e"

# fonte Inter, se disponivel; senao DejaVu Sans
_fontes = {f.name: f.fname for f in font_manager.fontManager.ttflist}
_otf = [f for f in font_manager.findSystemFonts() if "Inter-Regular" in f or "Inter-Medium" in f]
if _otf:
    try:
        font_manager.fontManager.addfont("/usr/share/fonts/opentype/inter/Inter-Regular.otf")
        font_manager.fontManager.addfont("/usr/share/fonts/opentype/inter/Inter-SemiBold.otf")
    except Exception:
        pass
plt.rcParams["font.family"] = ["Inter", "DejaVu Sans"]

CW, CH = 24.0, 16.0          # mm por celula (todas iguais)
GAP_X, GAP_Y = 4.0, 14.0     # mm entre celulas (GAP_Y deixa espaco para o titulo)
MARG_L, MARG_R, MARG_T, MARG_B = 6.0, 6.0, 14.0, 14.0
COLS = 5

nomes = list(F.FOOTPRINTS.keys())
linhas = (len(nomes) + COLS - 1) // COLS
W_MM = MARG_L + COLS * CW + (COLS - 1) * GAP_X + MARG_R
H_MM = MARG_T + linhas * CH + (linhas - 1) * GAP_Y + MARG_B
DPI = 450
fig = plt.figure(figsize=(W_MM / 25.4, H_MM / 25.4), dpi=DPI, facecolor=BG)


def _desenha_pad(ax, p, pin1):
    cor = COBRE_PIN1 if pin1 else COBRE
    if p["forma"] == "round":
        ax.add_patch(Circle((p["x"], p["y"]), p["w"] / 2.0, facecolor=cor, edgecolor="none", zorder=3))
    elif p["forma"] == "oval":
        raio = min(p["w"], p["h"]) / 2.0
        ax.add_patch(FancyBboxPatch((p["x"] - p["w"] / 2.0 + raio, p["y"] - p["h"] / 2.0 + raio),
                                    max(p["w"] - 2 * raio, 1e-6), max(p["h"] - 2 * raio, 1e-6),
                                    boxstyle=f"round,pad={raio},rounding_size={raio}",
                                    facecolor=cor, edgecolor="none", zorder=3))
    else:
        ax.add_patch(Rectangle((p["x"] - p["w"] / 2.0, p["y"] - p["h"] / 2.0), p["w"], p["h"],
                               facecolor=cor, edgecolor="none", zorder=3))
    if p["furo"]:
        ax.add_patch(Circle((p["x"], p["y"]), p["furo"] / 2.0, facecolor=FURO,
                            edgecolor=BORDA_FURO, linewidth=0.35, zorder=4))


for k, nome in enumerate(nomes):
    fp = F.FOOTPRINTS[nome]
    lin, col = divmod(k, COLS)
    left_mm = MARG_L + col * (CW + GAP_X)
    top_mm = MARG_T + lin * (CH + GAP_Y)
    bottom_mm = H_MM - (top_mm + CH)
    ax = fig.add_axes([left_mm / W_MM, bottom_mm / H_MM, CW / W_MM, CH / H_MM])
    ax.set_facecolor(BG)
    ax.set_xlim(-CW / 2, CW / 2)
    ax.set_ylim(-CH / 2, CH / 2)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)

    # grade de 1 mm (menor) e 5 mm (maior)
    for gx in range(-int(CW / 2), int(CW / 2) + 1):
        ax.axvline(gx, color=GRADE_MAIOR if gx % 5 == 0 else GRADE_MENOR, lw=0.35 if gx % 5 else 0.6, zorder=0)
    for gy in range(-int(CH / 2), int(CH / 2) + 1):
        ax.axhline(gy, color=GRADE_MAIOR if gy % 5 == 0 else GRADE_MENOR, lw=0.35 if gy % 5 else 0.6, zorder=0)

    # cortesia (tracejada) e corpo
    cx, cy = fp["cortesia_xy"]
    w, h = fp["cortesia"]
    ax.add_patch(Rectangle((cx - w / 2, cy - h / 2), w, h, facecolor="none",
                           edgecolor=CORTESIA, linewidth=0.6, linestyle=(0, (3, 2)), zorder=1))
    if fp["corpo"][0] > 0 and fp["corpo"][1] > 0:
        bx, by = fp["corpo_xy"]
        bw, bh = fp["corpo"]
        ax.add_patch(Rectangle((bx - bw / 2, by - bh / 2), bw, bh, facecolor="#16324f",
                               alpha=0.55, edgecolor=CORPO, linewidth=0.7, zorder=1.5))

    # pads e furos
    npads = len(fp["pads"])
    fs = 3.0 if npads >= 16 else 4.3
    for p in fp["pads"]:
        pin1 = p["pino"] == "1"
        _desenha_pad(ax, p, pin1)
        ax.text(p["x"], p["y"], p["pino"], color=TEXTO, fontsize=fs, ha="center", va="center",
                zorder=6, fontweight="bold" if pin1 else "normal",
                path_effects=[pe.withStroke(linewidth=0.8, foreground=BG)])

    # origem
    ax.plot([-0.5, 0.5], [0, 0], color=TEXTO_FRACO, lw=0.4, zorder=7)
    ax.plot([0, 0], [-0.5, 0.5], color=TEXTO_FRACO, lw=0.4, zorder=7)

    tit = nome if nome != "ICSP_6P_SMD_BOT" else "ICSP_6P_SMD_BOT *"
    ax.set_title(tit, color=TEXTO, fontsize=6.0, pad=2.2, loc="center")

fig.text(MARG_L / W_MM, 1 - 5.5 / H_MM,
         "Footprints do seguidor, mesma escala (grade de 1 mm), vista de cima. Pino 1 em vermelho.",
         color=TEXTO, fontsize=6.4, ha="left", va="center")
fig.text(MARG_L / W_MM, 7.2 / H_MM,
         "Dourado = pad; circulo escuro = furo; azul = corpo; tracejado = cortesia (corpo + pads + 0,25 mm); + = origem.",
         color=TEXTO_FRACO, fontsize=5.0, ha="left", va="center")
fig.text(MARG_L / W_MM, 3.6 / H_MM,
         "Unidades em mm. * ICSP_6P_SMD_BOT ja vem espelhado em x (face BOTTOM); os demais estao na face TOP.",
         color=TEXTO_FRACO, fontsize=5.0, ha="left", va="center")

fig.savefig(SAIDA, dpi=DPI, facecolor=BG)
print("gravado:", SAIDA, "tamanho mm:", round(W_MM, 1), "x", round(H_MM, 1))
