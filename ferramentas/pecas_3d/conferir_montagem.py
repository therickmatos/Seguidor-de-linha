#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Monta em 3D a base SATURN v3, as varetas, as presilhas, a barra V1 e o patim,
mede interferencias e folgas e desenha as figuras de conferencia.

Le direto do repositorio: o .epro da placa, o Gerber da V1 e da VISION e os STL
do EVA-RT ((c) EXOTIC TEAM MX, AGPL-3.0). Referencial do robo: origem no centro
da ventoinha, +x direita, +y frente, z = 0 na face de cima da base.

Uso: python3 conferir_montagem.py [--furos 63.14] [--esp-barra 1.0]
"""
from __future__ import annotations

import argparse
import json
import math
import re
import zipfile
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import trimesh
from manifold3d import Manifold, Mesh
from shapely.geometry import LineString, Polygon
from shapely.ops import polygonize, unary_union

import gerar_pecas as gp

RAIZ = gp.RAIZ
EPRO = RAIZ / "ProPrj_RUSH - SATURN - v3_2026-11-09.epro"
GERBER_V1 = RAIZ / "hardware/barra_v1/V1_Barra_de_sensores_PCB_2026-03.zip"
GERBER_VISION = RAIZ / "referencias/eva-rt/pcb_files/Gerber_VISION_2_X12_4S_PCB_2025-02-02.zip"
STL = RAIZ / "referencias/eva-rt/3d_models"
FIG = gp.MECANICA / "conferencia"
MIL = 0.0254

# Cotas da montagem
ESP_BASE = 1.0                  # as presilhas do EVA-RT tem rasgo de 1,0 mm
Y_FUROS_BASE = (-1.75, 10.75)   # furos das presilhas
Z_VARETA = 2.5                  # eixo da vareta acima da face de cima da base
Y_TRANSVERSAL = 19.745          # eixo da vareta transversal no desenho do EVA-RT
Z_TRANSVERSAL = Z_VARETA - 1.0  # deitada sobre a base (o furo do bloco fica 1 mm abaixo do eixo)
GIRO_CARCACA = 225              # pes com orelha na frente: as orelhas seguram a transversal
COMP_VARETA = 94.0              # o EVA-RT usa 3 varetas de 94 mm
Y_TRAS_VARETA = -4.0            # a vareta comeca na face de tras da presilha traseira


# ----------------------------------------------------------------------------
# Leitura dos arquivos de placa
# ----------------------------------------------------------------------------
def ler_epro(caminho: Path):
    """Contorno (poligono), furos [(x, y, d)] e componentes {ref: (x, y, face)}."""
    with zipfile.ZipFile(caminho) as z:
        nome = next(n for n in z.namelist() if n.endswith(".epcb"))
        linhas = [json.loads(l) for l in z.read(nome).decode().splitlines() if l.strip()]
    segs = [LineString([(r[6][0] * MIL, r[6][1] * MIL), (r[6][3] * MIL, r[6][4] * MIL)])
            for r in linhas if r[0] == "POLY" and r[4] == 11 and r[6][2] == "L"]
    contorno = max(polygonize(unary_union(segs)), key=lambda p: p.area)
    contorno = Polygon(contorno.exterior)
    furos = [(r[7][0][1] * MIL, r[7][0][2] * MIL, 2 * r[7][0][3] * MIL)
             for r in linhas if r[0] == "FILL" and r[7][0][0] == "CIRCLE"]
    ref = {r[3]: r[8] for r in linhas if r[0] == "ATTR" and r[7] == "Designator"}
    comps = {ref[r[1]]: (r[4] * MIL, r[5] * MIL, r[3]) for r in linhas
             if r[0] == "COMPONENT" and r[1] in ref}
    return contorno, furos, comps


def ler_gerber(texto: str):
    """Polilinhas de um Gerber RS-274X (so tracos retos e arcos)."""
    dec = int(re.search(r"%FSLAX\d(\d)Y\d\d\*%", texto).group(1))
    esc = (25.4 if "%MOIN" in texto else 1.0) / 10 ** dec
    pols, cur, x, y, modo = [], None, 0.0, 0.0, 1
    for cmd in texto.split("*"):
        cmd = cmd.strip().lstrip("%")
        g = re.match(r"^(G0?[123])?(?:X(-?\d+))?(?:Y(-?\d+))?(?:I(-?\d+))?(?:J(-?\d+))?(D0?[123])?$", cmd)
        if not cmd or not g or cmd in ("G75", "G74") or not (g.group(2) or g.group(3)):
            continue
        if g.group(1):
            modo = int(g.group(1)[1:])
        nx = int(g.group(2)) * esc if g.group(2) else x
        ny = int(g.group(3)) * esc if g.group(3) else y
        d = int(g.group(6)[1:]) if g.group(6) else 1
        if d == 2:
            cur = [(nx, ny)]
            pols.append(cur)
        elif d == 1 and cur is not None:
            if modo == 1:
                cur.append((nx, ny))
            else:
                i = int(g.group(4) or 0) * esc
                j = int(g.group(5) or 0) * esc
                cx, cy, r = x + i, y + j, math.hypot(i, j)
                a0, a1 = math.atan2(y - cy, x - cx), math.atan2(ny - cy, nx - cx)
                if modo == 2 and a1 >= a0 - 1e-12:
                    a1 -= 2 * math.pi
                if modo == 3 and a1 <= a0 + 1e-12:
                    a1 += 2 * math.pi
                n = max(4, int(abs(a1 - a0) / math.radians(3)))
                cur += [(cx + r * math.cos(t), cy + r * math.sin(t)) for t in np.linspace(a0, a1, n + 1)[1:]]
                cur[-1] = (nx, ny)
        x, y = nx, ny
    return [np.array(p) for p in pols if len(p) > 1]


def ler_barra(zip_gerber: Path):
    """Contorno externo e furos de uma barra de sensores (Gerber do EasyEDA)."""
    with zipfile.ZipFile(zip_gerber) as z:
        gko = z.read("Gerber_BoardOutlineLayer.GKO").decode()
        furos = []
        for nome in ("Drill_PTH_Through.DRL", "Drill_NPTH_Through.DRL"):
            ferr, t = {}, None
            for l in z.read(nome).decode().splitlines():
                if m := re.match(r"T(\d+)C([\d.]+)", l):
                    ferr[int(m.group(1))] = float(m.group(2))
                elif m := re.match(r"T(\d+)$", l):
                    t = int(m.group(1))
                elif m := re.match(r"X(-?[\d.]+)Y(-?[\d.]+)$", l):
                    furos.append((float(m.group(1)), float(m.group(2)), ferr[t]))
    faces = list(polygonize(unary_union([LineString(p) for p in ler_gerber(gko)])))
    contorno = Polygon(max(faces, key=lambda p: p.area).exterior)
    return contorno, furos


# ----------------------------------------------------------------------------
# Solidos
# ----------------------------------------------------------------------------
def placa(contorno: Polygon, furos, esp, z_topo, dx=0.0, dy=0.0, d_min=0.0) -> Manifold:
    m = gp.poligono(np.array(contorno.exterior.coords)[:-1]).extrude(esp)
    for x, y, d in furos:
        if d >= d_min:
            m -= Manifold.cylinder(esp + 2, d / 2).translate((x, y, -1))
    return m.translate((dx, dy, z_topo - esp))


def stl(nome) -> Manifold:
    t = trimesh.load(STL / nome)
    return Manifold(Mesh(vert_properties=np.asarray(t.vertices, dtype=np.float32),
                         tri_verts=np.asarray(t.faces, dtype=np.uint32)))


def cil_y(x, z, y0, y1, r) -> Manifold:
    return Manifold.cylinder(y1 - y0, r).transform([[1, 0, 0, x], [0, 0, 1, y0], [0, -1, 0, z]])


def cil_x(y, z, x0, x1, r) -> Manifold:
    return Manifold.cylinder(x1 - x0, r).transform([[0, 0, 1, x0], [1, 0, 0, y], [0, 1, 0, z]])


def cil_z(x, y, z0, z1, r) -> Manifold:
    return Manifold.cylinder(z1 - z0, r).translate((x, y, z0))


def no_robo(peca: Manifold, lado: int, y0: float, z_eixo=Z_VARETA, inverter_z=False, comp=0.0) -> Manifold:
    """Peca no referencial local (x p/ dentro, y p/ cima, z ao longo da vareta)
    levada para o robo. lado = +1 direita, -1 esquerda. Do lado esquerdo usa-se
    a peca espelhada (mesma rotacao) ou, se inverter_z, a mesma peca virada."""
    if inverter_z:      # gira 180 graus em torno da vertical
        return peca.transform([[1, 0, 0, lado * gp.X_VARETA], [0, 0, -1, y0 + comp], [0, 1, 0, z_eixo]])
    return peca.transform([[-1, 0, 0, lado * gp.X_VARETA], [0, 0, 1, y0], [0, 1, 0, z_eixo]])


def bloco_transversal(lado: int, y_eixo: float) -> Manifold:
    """barilla_connection: furo cego (y local) virado para dentro e 1 mm ABAIXO do
    eixo da vareta longitudinal (x local = -1 -> z = 1,5), como nas fotos do EVA-RT:
    a transversal deita sobre a base e fica sob as orelhas da carcaca da ventoinha."""
    b = stl("barilla_connection.stl")
    if lado > 0:
        return b.transform([[0, -1, 0, gp.X_VARETA], [0, 0, -1, y_eixo + 3.5], [1, 0, 0, Z_VARETA]])
    return b.transform([[0, 1, 0, -gp.X_VARETA], [0, 0, 1, y_eixo - 3.5], [1, 0, 0, Z_VARETA]])


def montar(dist_furos: float, esp_barra: float, patim_dir: Manifold, desl_patim: float, x_vareta_barra=None):
    """Devolve dict nome -> Manifold e dados da montagem."""
    contorno, furos, comps = ler_epro(EPRO)
    c_v1, f_v1 = ler_barra(GERBER_V1)
    furo_v1 = next(f for f in f_v1 if f[2] > 2 and f[0] > 0)
    y_furo_barra = Y_FUROS_BASE[1] + dist_furos
    y0_barra = y_furo_barra - furo_v1[1]
    z_topo_barra = Z_VARETA - gp.R_VARETA            # a vareta apoia em cima da barra
    s = {"base": placa(contorno, furos, ESP_BASE, 0.0)}
    s["barra_v1"] = placa(c_v1, f_v1, esp_barra, z_topo_barra, dy=y0_barra, d_min=1.0)
    y_fim = Y_TRAS_VARETA + COMP_VARETA
    for lado, nome in ((1, "dir"), (-1, "esq")):
        s[f"vareta_{nome}"] = cil_y(lado * gp.X_VARETA, Z_VARETA, Y_TRAS_VARETA, y_fim, gp.R_VARETA - 0.005)
        for i, yf in enumerate(Y_FUROS_BASE):
            s[f"presilha_{nome}_{i}"] = no_robo(stl("barilla_clamp.stl"), lado, yf - 2.25,
                                                inverter_z=lado < 0, comp=4.5)
        s[f"bloco_{nome}"] = bloco_transversal(lado, Y_TRANSVERSAL)
        p = patim_dir if lado > 0 else gp.espelhar(patim_dir)
        s[f"patim_{nome}"] = no_robo(p, lado, y_furo_barra - 3.0)
        s[f"parafuso_patim_{nome}"] = cil_z(lado * furo_v1[0], y_furo_barra, -8, 8, 0.99)
    s["vareta_transversal"] = cil_x(Y_TRANSVERSAL, Z_TRANSVERSAL, -(gp.X_VARETA - 1.5),
                                    gp.X_VARETA - 1.5, gp.R_VARETA - 0.005)
    # carcaca da ventoinha: pes em (+-15,56; +-15,56) -> STL girado 45 graus + k*90
    s["carcaca_ventoinha"] = stl("impeller_base_1.stl").rotate((0, 0, GIRO_CARCACA))
    j2 = comps["J2"]
    s["J2_barra_de_pinos"] = Manifold.cube((8 * 2.54, 2.54, 2.54)).translate((j2[0] - 4 * 2.54, j2[1] - 1.27, 0))
    # com o conector femea do cabo encaixado (corpo de 2,54 mm ate ~14 mm de altura)
    s["J2_com_cabo"] = Manifold.cube((8 * 2.54, 2.54, 14.0)).translate((j2[0] - 4 * 2.54, j2[1] - 1.27, 0))
    dados = dict(contorno=contorno, furos=furos, comps=comps, c_v1=c_v1, f_v1=f_v1, furo_v1=furo_v1,
                 y_furo_barra=y_furo_barra, y0_barra=y0_barra, z_topo_barra=z_topo_barra, y_fim=y_fim)
    return s, dados


# ----------------------------------------------------------------------------
# Conferencia numerica
# ----------------------------------------------------------------------------
def inter(a: Manifold, b: Manifold) -> float:
    return (a ^ b).volume()


def folga(a: Manifold, b: Manifold, busca=8.0) -> float:
    return a.min_gap(b, busca)


def relatorio(s, d, esp_barra):
    print("\nInterferencias (volume em mm3; 0 = nao encosta) e folgas (mm):")
    pares = []
    for lado in ("dir", "esq"):
        pares += [(f"presilha_{lado}_0", "base"), (f"presilha_{lado}_1", "base"),
                  (f"patim_{lado}", "barra_v1"), (f"patim_{lado}", f"vareta_{lado}"),
                  (f"vareta_{lado}", "barra_v1"), (f"vareta_{lado}", "base"),
                  (f"parafuso_patim_{lado}", "barra_v1"), (f"bloco_{lado}", "base"),
                  (f"bloco_{lado}", f"presilha_{lado}_1")]
    pares += [("vareta_transversal", "carcaca_ventoinha"), ("vareta_transversal", "J2_barra_de_pinos"),
              ("vareta_transversal", "J2_com_cabo"),
              ("vareta_transversal", "base"), ("barra_v1", "base"), ("barra_v1", "bloco_dir"),
              ("barra_v1", "bloco_esq")]
    pior = 0.0
    for a, b in pares:
        v = inter(s[a], s[b])
        g = folga(s[a], s[b]) if v < 1e-6 else 0.0
        pior = max(pior, v)
        print(f"  {a:22s} x {b:20s} interferencia {v:7.3f}   folga {g:6.3f}")
    # parafuso do patim: tem de passar livre pelos dois bracos
    print("  (a transversal encosta na base e nas orelhas dos pes da frente da carcaca: folga ~0 e o esperado)")
    for lado in ("dir", "esq"):
        v = inter(s[f"parafuso_patim_{lado}"], s[f"patim_{lado}"])
        print(f"  parafuso_patim_{lado:5s}   x patim_{lado:14s} interferencia {v:7.3f}   (furo alinhado se 0)")
        pior = max(pior, v)
    L = d["y0_barra"] + 6.957733 + 22.5877
    print(f"\nFuro da barra em y = {d['y_furo_barra']:.3f}; origem da V1 em y = {d['y0_barra']:.3f}; "
          f"L (eixo das rodas -> sensores centrais) = {L:.2f} mm")
    print(f"Face de cima da barra {d['z_topo_barra']:+.2f} mm em relacao a face de cima da base; "
          f"fundo do patim {Z_VARETA - 6.5:+.2f}; face de baixo da barra {d['z_topo_barra'] - esp_barra:+.2f} "
          f"-> barra {d['z_topo_barra'] - esp_barra - (Z_VARETA - 6.5):.2f} mm acima da pista")
    return pior


# ----------------------------------------------------------------------------
# Figuras
# ----------------------------------------------------------------------------
CORES = {"base": "#2f6b3a", "barra_v1": "#2f6b3a", "vareta": "#222222", "presilha": "#d98324",
         "bloco": "#8a5fbf", "patim": "#1f77b4", "carcaca": "#bbbbbb", "J2": "#b03030"}


def cor(nome):
    return next((c for k, c in CORES.items() if nome.startswith(k)), "#888888")


def proj(m: Manifold, eixo="z"):
    """Poligonos da projecao ao longo de um eixo."""
    if eixo == "x":      # ve (y, z)
        m = m.transform([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0]])
    return m.project().to_polygons()


def corte(m: Manifold, eixo, valor):
    """Secao por um plano: eixo 'y' -> devolve (x, z); 'x' -> (y, z)."""
    if eixo == "y":
        m = m.transform([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, valor]])
    else:
        m = m.transform([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, -valor]])
    return m.slice(0.0).to_polygons()


def pintar(ax, pols, c, alpha=0.85, z=1, borda="k", lw=0.5):
    # furos sao desenhados com a cor do fundo (os poligonos vem com o sentido certo)
    for p in pols:
        p = np.asarray(p)
        area = 0.5 * np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])
        ax.fill(p[:, 0], p[:, 1], facecolor=c if area > 0 else "white", edgecolor=borda,
                lw=lw, alpha=alpha if area > 0 else 1.0, zorder=z + (0 if area > 0 else 0.5))


def cota(ax, p0, p1, texto, desl=(0, 0), cor_="#c00000", fs=9, ha="center", va="center"):
    ax.annotate("", p0, p1, arrowprops=dict(arrowstyle="<->", color=cor_, lw=1.0), zorder=20)
    m = ((p0[0] + p1[0]) / 2 + desl[0], (p0[1] + p1[1]) / 2 + desl[1])
    ax.text(*m, texto, color=cor_, fontsize=fs, ha=ha, va=va, zorder=21,
            bbox=dict(fc="white", ec="none", alpha=0.85, pad=1))


def fig_planta(s, d, dist_furos, arq):
    fig, ax = plt.subplots(figsize=(11, 10.5))
    ordem = ["base", "barra_v1", "carcaca_ventoinha", "J2_barra_de_pinos", "vareta_transversal"]
    ordem += [n for n in s if n.startswith(("presilha", "bloco", "patim_", "vareta_d", "vareta_e"))]
    for i, n in enumerate(ordem):
        pintar(ax, proj(s[n]), cor(n), alpha=0.55 if n in ("carcaca_ventoinha",) else 0.9, z=2 + i * 0.01)
    for x, y, dd in d["furos"]:
        ax.add_patch(plt.Circle((x, y), dd / 2, fc="white", ec="k", lw=0.5, zorder=3))
    xr = gp.X_VARETA
    yb, yf = d["y_furo_barra"], Y_FUROS_BASE[1]
    ax.plot([d["furo_v1"][0], gp.X_FURO_BASE], [yb, yf], "o", color="#c00000", ms=3, zorder=22)
    cota(ax, (57, yf), (57, yb), f"{dist_furos:.2f} entre furos", desl=(1.5, 0), ha="left")
    ax.plot([gp.X_FURO_BASE, 58], [yf, yf], color="#c00000", lw=0.5, zorder=19)
    ax.plot([d["furo_v1"][0], 58], [yb, yb], color="#c00000", lw=0.5, zorder=19)
    cota(ax, (-xr, 52), (xr, 52), f"varetas paralelas em x = ±{xr:.2f}  ({2 * xr:.1f} entre eixos)", desl=(-18, 0))
    cota(ax, (-(xr - 1.5), Y_TRANSVERSAL + 9), (xr - 1.5, Y_TRANSVERSAL + 9),
         f"vareta transversal {2 * (xr - 1.5):.0f} mm, eixo em y = {Y_TRANSVERSAL:.2f}", fs=8, desl=(-18, 0))
    ax.annotate("J2 (barra de pinos)", (d["comps"]["J2"][0] + 6, d["comps"]["J2"][1]), (16, 33), fontsize=8,
                color=CORES["J2"], arrowprops=dict(arrowstyle="-", color=CORES["J2"], lw=0.6), zorder=25)
    cota(ax, (-58, Y_TRAS_VARETA), (-58, d["y_fim"]), f"vareta {COMP_VARETA:.0f} mm", desl=(-1.5, 0), ha="right")
    L = d["y0_barra"] + 6.957733 + 22.5877
    cota(ax, (0, -22.5877), (0, d["y0_barra"] + 6.957733), f"L = {L:.1f}", desl=(1.5, 30), ha="left", cor_="#0050a0")
    ax.axhline(-22.5877, color="#0050a0", lw=0.6, ls="--", zorder=1)
    ax.text(-30, -21.3, "eixo das rodas", color="#0050a0", fontsize=8)
    ax.text(0, d["y0_barra"] + 14.5, "barra V1 (12× QRE1113)", ha="center", fontsize=9)
    ax.text(-22, -29, "base SATURN v3", ha="center", fontsize=9, color="white", zorder=30)
    ax.text(62, 9.5, "presilhas\n(originais)", fontsize=8, color=CORES["presilha"], ha="left")
    ax.text(52.5, d["y_furo_barra"] + 6, "patim V1\n(novo)", fontsize=8, color=CORES["patim"], ha="left")
    ax.text(52.5, Y_TRANSVERSAL + 1, "bloco da\ntransversal", fontsize=8, color=CORES["bloco"], ha="left", va="center")
    ax.annotate("carcaça da ventoinha:\npés com orelha na frente,\nsegurando a transversal", (-15.5, 18.6), (-44, 31),
                fontsize=8, color="#444444", arrowprops=dict(arrowstyle="-", color="#444444", lw=0.6), zorder=25)
    ax.set_aspect("equal")
    ax.set_xlim(-80, 80)
    ax.set_ylim(-36, 98)
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm), frente para cima")
    ax.grid(alpha=0.25)
    ax.set_title(f"Montagem do suporte da barra V1 — vista de cima ({dist_furos:.2f} mm entre furos)")
    fig.tight_layout()
    fig.savefig(arq, dpi=110)
    plt.close(fig)


def fig_corte_patim(esp_barra, arq):
    """Corte pelo parafuso do patim (olhando de tras para a frente, lado direito)."""
    c_v1, f_v1 = ler_barra(GERBER_V1)
    c_vi, f_vi = ler_barra(GERBER_VISION)
    casos = [
        ("EVA-RT: barra VISION + sensor_sledge original", c_vi, f_vi, 1.0, stl("sensor_sledge.stl"),
         gp.X_FURO_VISION + gp.DESL_PATIM_EVA),
        ("Barra V1 + sensor_sledge original (sem adaptar)", c_v1, f_v1, 1.0, stl("sensor_sledge.stl"),
         gp.X_FURO_V1 + gp.DESL_PATIM_EVA),
        (f"Barra V1 ({esp_barra:.1f} mm) + patim V1 novo", c_v1, f_v1, esp_barra, gp.patim(esp_barra), gp.X_VARETA),
    ]
    fig, axs = plt.subplots(1, 3, figsize=(17, 6.2), sharey=True)
    for ax, (tit, cont, furos, esp, pat, x_var) in zip(axs, casos):
        furo = next(f for f in furos if f[2] > 2 and f[0] > 0)
        pcb = placa(cont, furos, esp, -gp.R_VARETA, d_min=1.0)
        pat_r = pat.transform([[-1, 0, 0, x_var], [0, 0, 1, furo[1] - 3.0], [0, 1, 0, 0]])
        vareta = cil_y(x_var, 0, furo[1] - 6, furo[1] + 8, gp.R_VARETA)
        novo = "novo" in tit
        folga_r = 0.1 if novo else 0.0
        y_baixo = -gp.R_VARETA - esp - folga_r - 1.0          # face de baixo do braco de baixo
        y_cima = 2.0 if novo else -0.5                        # onde a porca/cabeca apoia em cima
        pintar(ax, corte(pcb, "y", furo[1]), CORES["base"], z=3)
        pintar(ax, corte(pat_r, "y", furo[1]), CORES["patim"], z=2)
        pintar(ax, corte(vareta, "y", furo[1]), "#333333", z=4)
        # parafuso M2: cabeca O3,8 x 1,6 e porca de 4,0 entre faces x 1,6.
        # No EVA-RT (fotos) a cabeca fica em cima; no patim novo, cabeca por baixo e porca em cima.
        r_cima, r_baixo = (2.0, 1.9) if novo else (1.9, 2.0)
        for (xa, xb, ya, yb) in ((furo[0] - 1.0, furo[0] + 1.0, y_baixo - (0 if novo else 1.9), y_cima + (1.9 if novo else 0)),
                                 (furo[0] - r_baixo, furo[0] + r_baixo, y_baixo - 1.6, y_baixo),
                                 (furo[0] - r_cima, furo[0] + r_cima, y_cima, y_cima + 1.6)):
            ax.fill([xa, xb, xb, xa], [ya, ya, yb, yb], fc="#c9c9c9", ec="k", lw=0.5, alpha=0.95, zorder=5)
        ax.text(furo[0], y_cima + 2.2, "porca M2" if novo else "cabeça M2", fontsize=7, ha="center", color="#444444")
        ax.text(furo[0], y_baixo - 2.25, "cabeça M2" if novo else "porca M2", fontsize=7, ha="center", color="#444444")
        ax.axvline(gp.X_VARETA, color="#c00000", lw=1.0, ls="--", zorder=10)
        ax.text(gp.X_VARETA + 0.1, 4.9, f"linha das presilhas\nda base  x = {gp.X_VARETA:.2f}", color="#c00000",
                fontsize=8, va="top", ha="left")
        ax.axvline(furo[0], color="#555555", lw=0.6, ls=":", zorder=10)
        ax.text(furo[0], -7.6, f"furo {furo[0]:.2f}", fontsize=8, ha="center", color="#555555")
        ax.axhline(-6.5, color="k", lw=1.2, zorder=1)
        ax.text(39.2, -6.85, "pista", fontsize=8)
        desvio = x_var - gp.X_VARETA
        ax.set_title(f"{tit}\nvareta em x = {x_var:.2f}  (desvio {desvio:+.2f} mm)", fontsize=10)
        ax.set_aspect("equal")
        ax.set_xlim(39, 52.5)
        ax.set_ylim(-8, 5)
        ax.grid(alpha=0.25)
        ax.set_xlabel("x (mm) — lado direito do robô, visto de trás")
    axs[0].set_ylabel("altura em relação ao eixo da vareta (mm)")
    fig.tight_layout()
    fig.savefig(arq, dpi=110)
    plt.close(fig)


def fig_lateral(s, d, esp_barra, arq):
    """Corte longitudinal pelo eixo da vareta direita (plano x = 48,45)."""
    fig, ax = plt.subplots(figsize=(15, 3.6))
    x0 = gp.X_VARETA - 0.4      # um pouco para dentro: pega placa, bracos e vareta
    for n in ("base", "barra_v1", "presilha_dir_0", "presilha_dir_1", "bloco_dir", "patim_dir", "vareta_dir"):
        pintar(ax, corte(s[n], "x", x0), cor(n), z=3 if n.startswith("vareta") else 2)
    z_piso = Z_VARETA - 6.5
    ax.axhline(z_piso, color="k", lw=1.2)
    ax.text(30, z_piso - 0.9, "pista (fundo do patim)", fontsize=8)
    cota(ax, (Y_FUROS_BASE[1], 6.6), (d["y_furo_barra"], 6.6), f"{d['y_furo_barra'] - Y_FUROS_BASE[1]:.2f} entre furos")
    for y in (Y_FUROS_BASE[0], Y_FUROS_BASE[1], d["y_furo_barra"]):
        ax.plot([y, y], [-3, 7], color="#c00000", lw=0.5, ls=":")
    ax.text(4.5, -2.6, "base 1,0 mm", fontsize=8, ha="center")
    ax.text(d["y0_barra"] + 2, d["z_topo_barra"] - esp_barra - 1.2, f"barra V1 {esp_barra:.1f} mm", fontsize=8)
    ax.set_aspect("equal")
    ax.set_xlim(-8, 96)
    ax.set_ylim(z_piso - 1.6, 8)
    ax.set_xlabel("y (mm)")
    ax.set_ylabel("z (mm), 0 = face de cima da base")
    ax.set_title(f"Corte longitudinal 0,4 mm para dentro do eixo da vareta direita (x = {x0:.2f})")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(arq, dpi=110)
    plt.close(fig)


def fig_patim_3d(esp_barra, arq):
    """Patim original do EVA-RT ao lado do patim novo (mesma orientacao de impressao)."""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    pecas = [("sensor_sledge.stl (EVA-RT, barra VISION)", stl("sensor_sledge.stl"), "#9a9a9a"),
             (f"patim_v1_direito_pcb{esp_barra:.1f}.stl (novo)", gp.patim(esp_barra), CORES["patim"])]
    fig = plt.figure(figsize=(13, 9.5))
    luz = np.array([0.35, -0.5, 0.8]) / np.linalg.norm([0.35, -0.5, 0.8])
    for j, (el, az) in enumerate(((22, -58), (24, 32))):
        for i, (tit, m, c) in enumerate(pecas):
            ax = fig.add_subplot(2, 2, 2 * j + i + 1, projection="3d")
            v, f = gp.malha(m)
            tri = v[f]
            n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
            n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
            sombra = 0.5 + 0.5 * np.abs(n @ luz)
            base = np.array(matplotlib.colors.to_rgb(c))
            ax.add_collection3d(Poly3DCollection(tri, facecolors=np.clip(sombra[:, None] * base, 0, 1),
                                                 edgecolors=(0, 0, 0, 0.08), linewidths=0.15))
            ax.set_xlim(-3, 8)
            ax.set_ylim(-8, 3)
            ax.set_zlim(-1, 10)
            ax.set_box_aspect((1, 1, 1))
            ax.view_init(elev=el, azim=az)
            ax.set_proj_type("ortho")
            ax.set_xlabel("x")
            ax.set_ylabel("y")
            ax.set_zlabel("z (impressão)")
            if j == 0:
                ax.set_title(tit, fontsize=10)
    fig.tight_layout()
    fig.savefig(arq, dpi=100)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--furos", type=float, default=63.14, help="distancia entre furos base-barra (mm)")
    ap.add_argument("--esp-barra", type=float, default=1.0, help="espessura da barra V1 (mm)")
    ap.add_argument("--sem-figuras", action="store_true")
    a = ap.parse_args()
    s, d = montar(a.furos, a.esp_barra, gp.patim(a.esp_barra), gp.DESL_PATIM_V1)
    print(f"Montagem: {a.furos:.2f} mm entre furos, barra de {a.esp_barra:.1f} mm, base de {ESP_BASE:.1f} mm")
    pior = relatorio(s, d, a.esp_barra)
    if not a.sem_figuras:
        FIG.mkdir(parents=True, exist_ok=True)
        fig_planta(s, d, a.furos, FIG / "montagem_vista_de_cima.png")
        fig_corte_patim(a.esp_barra, FIG / "corte_patim.png")
        fig_lateral(s, d, a.esp_barra, FIG / "corte_longitudinal.png")
        fig_patim_3d(a.esp_barra, FIG / "patim_original_x_novo.png")
        print(f"Figuras em {FIG.relative_to(RAIZ)}/")
    print(f"\nMaior interferencia: {pior:.3f} mm3")


if __name__ == "__main__":
    main()
