#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Monta em 3D a base RUSH - SATURN v12 (placa encomendada, 1,6 mm), as varetas, as
presilhas, a barra V1, o patim, os parafusos, a placa de succao e os componentes de
baixo (QRE de marca, J3), mede interferencias, folgas e a altura ate a pista e
desenha as figuras de conferencia.

Le direto do repositorio: o .epro da placa, o Gerber da V1 e da VISION e os STL
do EVA-RT ((c) EXOTIC TEAM MX, AGPL-3.0). Referencial do robo: origem no centro
da ventoinha, +x direita, +y frente, z = 0 na face de cima da base.
Parafusos, porcas, placa de succao, J3 e altura ate a pista vieram da conferencia do
perseguidor RUSH - Dreamcast (therickmatos/Perseguidor-de-linha).

Uso: python3 conferir_montagem.py [--furos 63.14] [--esp-barra 1.6]
"""
from __future__ import annotations

import argparse
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
EPRO = RAIZ / "hardware/placa_base/ProPrj_RUSH - SATURN - v12_2026-11-15.epro"
GERBER_V1 = RAIZ / "hardware/barra_v1/V1_Barra_de_sensores_PCB_2026-03.zip"
GERBER_VISION = RAIZ / "referencias/eva-rt/pcb_files/Gerber_VISION_2_X12_4S_PCB_2025-02-02.zip"
STL = RAIZ / "referencias/eva-rt/3d_models"
FIG = gp.MECANICA / "conferencia"
MIL = 0.0254

# Cotas da montagem
ESP_BASE = gp.ESP_BASE          # 1,6 mm (o barilla_clamp do EVA-RT e para 1,0 mm)
ESP_SUCCAO = 0.6                # suction_base.stl
Y_FUROS_BASE = (-1.75, 10.75)   # furos das presilhas
Z_VARETA = gp.Z_VARETA          # 2,5: eixo da vareta acima da face de cima da base
Y_TRANSVERSAL = gp.Y_TRANSVERSAL  # 19,745: eixo da vareta transversal no desenho do EVA-RT
Z_TRANSVERSAL = Z_VARETA - 1.0  # deitada sobre a base (o furo do bloco fica 1 mm abaixo do eixo)
GIRO_CARCACA = 225              # pes com orelha na frente: as orelhas seguram a transversal
COMP_VARETA = 94.0              # o EVA-RT usa 3 varetas de 94 mm
Y_TRAS_VARETA = -4.0            # a vareta comeca na face de tras da presilha traseira
# Pista: o esqui do patim fica 6,5 mm abaixo do eixo da vareta. Com a vareta
# paralela a pista (pneu de ~22 mm: eixo da roda 7,0 mm acima da base, pela
# caixa de reducao), a pista fica 4,0 mm abaixo da face de cima da base.
Z_PISTA = Z_VARETA - 6.5
# Parafuso M2 de cabeca cilindrica ou abaulada (O3,8 x 1,6) e porca M2 (4,0 entre faces x 1,6)
CABECA_M2 = (1.9, 1.6)
PORCA_M2 = (2.0, 1.6)
FUROS_CAIXA = ((-35.25, -26.55), (-35.25, -3.733), (35.25, -26.55), (35.25, -3.733))
PES_CARCACA = [(sx * 15.556, sy * 15.556) for sx in (-1, 1) for sy in (-1, 1)]
# Componentes da face de baixo (envelopes: corpo + pads; altura maxima do datasheet).
# QRE1113GR: 3,6 x 2,9 x 1,7 mm. SOD-123: 3,7 (com os terminais) x 1,6 x 1,35.
# 0603: 2,4 (pads) x 0,95, resistor 0,55 e capacitor 0,9 de altura.
ENVELOPE_BAIXO = {"S": (3.6, 2.9, 1.7), "D": (3.7, 1.6, 1.35), "R": (2.4, 0.95, 0.55), "C": (2.4, 0.95, 0.9)}
# J3 (gravacao): barra de pinos reta deitada embaixo, pinos curtos soldados nos pads e
# a parte preta (2,54 x 2,54) encostada na borda de tras da base, em y = -30,0
J3_PINO = 0.64
J3_BORDA = -30.0


# ----------------------------------------------------------------------------
# Leitura dos arquivos de placa
# ----------------------------------------------------------------------------
ler_epro = gp.ler_epro


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


def porca(x, y, z) -> Manifold:
    """Porca M2 sextavada (4,0 entre faces), deitada em z."""
    r = PORCA_M2[0] / math.cos(math.radians(30))
    m = Manifold.cylinder(PORCA_M2[1], r, r, 6).rotate((0, 0, 30))
    return m.translate((x, y, z))


def bloco_transversal(lado: int, peca: Manifold) -> Manifold:
    """Bloco da transversal (ver gp.pose_bloco e gp.bloco_transversal)."""
    return peca.transform(gp.pose_bloco(lado))


def componente_baixo(ref, x, y, rot) -> Manifold | None:
    """Envelope de um componente da face de baixo (pendurado sob a base)."""
    env = ENVELOPE_BAIXO.get(ref[0])
    if env is None:
        return None
    c, l, h = env
    m = Manifold.cube((c, l, h), center=True).rotate((0, 0, rot))
    return m.translate((x, y, -ESP_BASE - h / 2))


def montar(dist_furos: float, esp_barra: float, patim_dir: Manifold, desl_patim: float, x_vareta_barra=None):
    """Devolve dict nome -> Manifold e dados da montagem."""
    contorno, furos, comps = ler_epro(EPRO)
    c_v1, f_v1 = ler_barra(GERBER_V1)
    presilhas = (gp.presilha_tras(), gp.presilha_frente())       # y = -1,75 e 10,75
    bloco = gp.bloco_transversal()
    z_porca = Z_VARETA - 2.5 + 1.0          # face de cima do braco de cima da presilha
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
            s[f"presilha_{nome}_{i}"] = no_robo(presilhas[i], lado, yf - 2.25, inverter_z=lado < 0, comp=4.5)
            xf = lado * gp.X_FURO_BASE
            s[f"parafuso_presilha_{nome}_{i}"] = cil_z(xf, yf, -ESP_BASE - 0.01, z_porca + PORCA_M2[1] + 1.0, 0.99)
            s[f"cabeca_presilha_{nome}_{i}"] = cil_z(xf, yf, -ESP_BASE - CABECA_M2[1], -ESP_BASE, CABECA_M2[0])
            s[f"porca_presilha_{nome}_{i}"] = porca(xf, yf, z_porca)
        s[f"bloco_{nome}"] = bloco_transversal(lado, bloco)
        p = patim_dir if lado > 0 else gp.espelhar(patim_dir)
        s[f"patim_{nome}"] = no_robo(p, lado, y_furo_barra - 3.0)
        s[f"parafuso_patim_{nome}"] = cil_z(lado * furo_v1[0], y_furo_barra, -8, 8, 0.99)
        # cabeca por baixo do braco de baixo do patim
        z_braco = Z_VARETA - gp.R_VARETA - esp_barra - 0.1 - 1.0
        s[f"cabeca_patim_{nome}"] = cil_z(lado * furo_v1[0], y_furo_barra, z_braco - CABECA_M2[1], z_braco,
                                          CABECA_M2[0])
    s["vareta_transversal"] = cil_x(Y_TRANSVERSAL, Z_TRANSVERSAL, -(gp.X_VARETA - 1.5),
                                    gp.X_VARETA - 1.5, gp.R_VARETA - 0.005)
    # caixas de reducao: so os parafusos (cabeca por baixo da base; a caixa fica em cima)
    for k, (xc, yc) in enumerate(FUROS_CAIXA):
        s[f"cabeca_caixa_{k}"] = cil_z(xc, yc, -ESP_BASE - CABECA_M2[1], -ESP_BASE, CABECA_M2[0])
    # placa de succao por baixo da base, centrada na ventoinha (furos nos pes da carcaca),
    # com rebaixo: a cabeca do parafuso dos pes apoia no fundo de 0,2 mm
    s["placa_succao"] = gp.placa_succao().translate((0, -27.5, -ESP_BASE - ESP_SUCCAO))
    z_cab = -ESP_BASE - gp.FUNDO_REBAIXO
    for k, (xp, yp) in enumerate(PES_CARCACA):
        s[f"cabeca_pe_{k}"] = cil_z(xp, yp, z_cab - CABECA_M2[1], z_cab, CABECA_M2[0])
    # componentes da face de baixo
    for ref, (xc, yc, face, rot) in comps.items():
        if face == 2 and (m := componente_baixo(ref, xc, yc, rot)) is not None:
            s[f"baixo_{ref}"] = m
    # J3 deitado: pinos sob os pads, corpo atras da borda, centrado no pino
    j3 = comps["J3"]
    zp = -ESP_BASE - J3_PINO / 2
    s["J3_pinos"] = Manifold.cube((5 * 2.54, J3_BORDA - (j3[1] - 0.95) + 2.54 + 6, J3_PINO)).translate(
        (j3[0] - 2.5 * 2.54, J3_BORDA - 2.54 - 6, -ESP_BASE - J3_PINO))
    s["J3_corpo"] = Manifold.cube((5 * 2.54, 2.54, 2.54)).translate((j3[0] - 2.5 * 2.54, J3_BORDA - 2.54, zp - 1.27))
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
    for lado in ("dir", "esq"):
        for i in (0, 1):
            pares += [(f"parafuso_presilha_{lado}_{i}", f"presilha_{lado}_{i}"),
                      (f"porca_presilha_{lado}_{i}", f"vareta_{lado}")]
    pares += [("vareta_transversal", "carcaca_ventoinha"), ("vareta_transversal", "J2_barra_de_pinos"),
              ("vareta_transversal", "J2_com_cabo"),
              ("vareta_transversal", "base"), ("barra_v1", "base"), ("barra_v1", "bloco_dir"),
              ("barra_v1", "bloco_esq"), ("placa_succao", "base"),
              ("J3_corpo", "base"), ("J3_corpo", "placa_succao")]
    pares += [(f"cabeca_pe_{k}", "placa_succao") for k in range(4)]
    pior = 0.0
    for a, b in pares:
        v = inter(s[a], s[b])
        g = folga(s[a], s[b]) if v < 1e-6 else 0.0
        pior = max(pior, v)
        print(f"  {a:22s} x {b:20s} interferencia {v:7.3f}   folga {g:6.3f}")
    # cabecas de parafuso x componentes da face de baixo (so os que ficam a menos de 2 mm)
    cabecas = [n for n in s if n.startswith("cabeca_")]
    for c in cabecas:
        for n in (n for n in s if n.startswith("baixo_")):
            v = inter(s[c], s[n])
            g = folga(s[c], s[n], 2.0) if v < 1e-6 else 0.0
            if g < 2.0:
                pior = max(pior, v)
                print(f"  {c:22s} x {n:20s} interferencia {v:7.3f}   folga {g:6.3f}")
    # parafuso do patim: tem de passar livre pelos dois bracos
    print("  (a transversal encosta na base e nas orelhas dos pes da frente da carcaca: folga ~0 e o esperado)")
    # a porca apoia no braco de cima da presilha; o que importa e a folga ate o ressalto da vareta
    acima = Manifold.cube((200, 200, 10)).translate((-100, -100, Z_VARETA - 1.5 + 0.02))
    for lado in ("dir", "esq"):
        for i in (0, 1):
            pres = s[f"presilha_{lado}_{i}"] ^ acima
            v = inter(s[f"porca_presilha_{lado}_{i}"], pres)
            g = folga(s[f"porca_presilha_{lado}_{i}"], pres) if v < 1e-6 else 0.0
            pior = max(pior, v)
            print(f"  porca_presilha_{lado}_{i:<2d}     x ressalto da presilha interferencia {v:7.3f}   folga {g:6.3f}")
    for lado in ("dir", "esq"):
        v = inter(s[f"parafuso_patim_{lado}"], s[f"patim_{lado}"])
        print(f"  parafuso_patim_{lado:5s}   x patim_{lado:14s} interferencia {v:7.3f}   (furo alinhado se 0)")
        pior = max(pior, v)
    print(f"\nAltura ate a pista (pista em z = {Z_PISTA:+.1f}, vareta nivelada; base de {ESP_BASE:.1f} mm):")
    grupos = [("base (face de baixo)", ["base"]), ("placa de succao", ["placa_succao"]),
              ("cabeca do parafuso dos pes da carcaca", [n for n in s if n.startswith("cabeca_pe")]),
              ("presilhas", [n for n in s if n.startswith("presilha_")]),
              ("cabeca do parafuso das presilhas", [n for n in s if n.startswith("cabeca_presilha")]),
              ("cabeca do parafuso das caixas", [n for n in s if n.startswith("cabeca_caixa")]),
              ("bloco da transversal", ["bloco_dir", "bloco_esq"]),
              ("barra V1 (face de baixo)", ["barra_v1"]),
              ("cabeca do parafuso dos patins", [n for n in s if n.startswith("cabeca_patim")]),
              ("J3 deitado (parte preta)", ["J3_corpo"]),
              ("QRE de marca S1 a S4 (face do sensor)", [n for n in s if n.startswith("baixo_S")]),
              ("D1 (SOD-123)", ["baixo_D1"]),
              ("resistores e capacitores 0603 de baixo", [n for n in s if n.startswith(("baixo_R", "baixo_C"))]),
              ("esqui do patim", ["patim_dir", "patim_esq"])]
    alturas = {}
    for rot, nomes in grupos:
        zmin = min(s[n].bounding_box()[2] for n in nomes)
        alturas[rot] = zmin - Z_PISTA
        print(f"  {rot:34s} {zmin - Z_PISTA:5.2f} mm")
    d["alturas"] = alturas
    z_orig = -ESP_BASE - ESP_SUCCAO - CABECA_M2[1]
    print(f"  (com a suction_base original a cabeca dos pes ficaria em cima da placa: {z_orig - Z_PISTA:.2f} mm;"
          f" sem o fundo do rebaixo, direto na base: {-ESP_BASE - CABECA_M2[1] - Z_PISTA:.2f} mm)")
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
         "bloco": "#8a5fbf", "patim": "#1f77b4", "carcaca": "#bbbbbb", "J2": "#b03030",
         "parafuso": "#c9c9c9", "cabeca": "#c9c9c9", "porca": "#c9c9c9", "baixo_S": "#3060b0"}


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
    fig, ax = plt.subplots(figsize=(12.5, 10.5))
    ordem = ["base", "barra_v1", "carcaca_ventoinha", "J2_barra_de_pinos", "vareta_transversal"]
    ordem += [n for n in s if n.startswith(("presilha", "bloco", "patim_", "vareta_d", "vareta_e", "porca_"))]
    for i, n in enumerate(ordem):
        pintar(ax, proj(s[n]), cor(n), alpha=0.55 if n == "carcaca_ventoinha" else 0.9, z=2 + i * 0.01)
    # QRE de marca (face de baixo), so o contorno
    for n in (n for n in s if n.startswith("baixo_S")):
        for p in proj(s[n]):
            p = np.asarray(p)
            ax.fill(p[:, 0], p[:, 1], fc="none", ec=CORES["baixo_S"], lw=0.9, ls="--", zorder=26)
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
    ax.text(-22, -29, "base SATURN v12", ha="center", fontsize=9, color="white", zorder=30)
    ax.annotate("presilha da frente\n(sobre a raiz da asa)", (50.5, 11.5), (58, 1.5), fontsize=8,
                color=CORES["presilha"], ha="left", arrowprops=dict(arrowstyle="-", color=CORES["presilha"], lw=0.6),
                zorder=25)
    ax.annotate("presilha de trás\n(parede na borda x = 50)", (50.5, -1.5), (58, -9), fontsize=8,
                color=CORES["presilha"], ha="left", arrowprops=dict(arrowstyle="-", color=CORES["presilha"], lw=0.6),
                zorder=25)
    ax.text(-81.5, 9.5, "QRE de marca\n(embaixo)", fontsize=8, color=CORES["baixo_S"], ha="center", va="top")
    ax.text(52.5, d["y_furo_barra"] + 6, "patim V1\n(novo)", fontsize=8, color=CORES["patim"], ha="left")
    ax.annotate("bloco da transversal\n(rebaixo para a asa)", (50.5, Y_TRANSVERSAL + 2), (58.5, Y_TRANSVERSAL + 9),
                fontsize=8, color=CORES["bloco"], ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=CORES["bloco"], lw=0.6), zorder=25)
    ax.annotate("carcaça da ventoinha:\npés com orelha na frente,\nsegurando a transversal", (-15.5, 18.6), (-44, 31),
                fontsize=8, color="#444444", arrowprops=dict(arrowstyle="-", color="#444444", lw=0.6), zorder=25)
    ax.set_aspect("equal")
    ax.set_xlim(-90, 90)
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
    ax.text(4.5, -3.2, f"base {ESP_BASE:.1f} mm".replace(".", ","), fontsize=8, ha="center")
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


def fig_corte_presilha(s, arq):
    """Corte pelo parafuso das presilhas do lado direito (tras e frente), com a pista."""
    casos = [(Y_FUROS_BASE[0], "presilha_dir_0", "Presilha de trás: parede encostada na borda x = 50"),
             (Y_FUROS_BASE[1], "presilha_dir_1", "Presilha da frente: apoiada sobre a raiz da asa")]
    fig, axs = plt.subplots(1, 2, figsize=(14, 5.6), sharey=True)
    for ax, (yf, nome, tit) in zip(axs, casos):
        pintar(ax, corte(s["base"], "y", yf), CORES["base"], z=3)
        pintar(ax, corte(s[nome], "y", yf), CORES["presilha"], z=2)
        pintar(ax, corte(s["vareta_dir"], "y", yf), "#333333", z=4)
        for n in (n for n in s if n.startswith("baixo_")):
            pols = corte(s[n], "y", yf)
            if pols:
                pintar(ax, pols, "#3060b0", z=4)
                x0 = min(np.asarray(p)[:, 0].min() for p in pols)
                ax.text(x0 + 0.5, -ESP_BASE - 1.2, n[6:], fontsize=7, color="#3060b0", ha="center", va="top")
        z_baixo = -ESP_BASE
        z_cima = Z_VARETA - 2.5 + 1.0
        xf = gp.X_FURO_BASE
        rc, hc = CABECA_M2
        rp, hp = PORCA_M2
        for (xa, xb, za, zb) in ((xf - 1.0, xf + 1.0, z_baixo, z_cima + hp + 0.4),
                                 (xf - rc, xf + rc, z_baixo - hc, z_baixo),
                                 (xf - rp, xf + rp, z_cima, z_cima + hp)):
            ax.fill([xa, xb, xb, xa], [za, za, zb, zb], fc="#c9c9c9", ec="k", lw=0.5, alpha=0.95, zorder=5)
        ax.text(xf, z_cima + hp + 0.6, "porca M2", fontsize=7, ha="center", color="#444444")
        ax.axhline(Z_PISTA, color="k", lw=1.2, zorder=1)
        ax.text(38.3, Z_PISTA - 0.45, "pista (vareta nivelada)", fontsize=8)
        folga_ = z_baixo - hc - Z_PISTA
        cota(ax, (xf - 2.6, Z_PISTA), (xf - 2.6, z_baixo - hc), f"{folga_:+.1f} mm".replace(".", ","),
             desl=(-0.4, 0), ha="right", cor_="#0050a0")
        ax.text(xf, z_baixo - hc - 0.35, "cabeça M2 (1,6 mm)", fontsize=7, ha="center", va="top", color="#444444",
                zorder=21)
        ax.set_title(f"{tit}\nbase {ESP_BASE:.1f} mm, corte em y = {yf}".replace(".", ","), fontsize=10)
        ax.set_aspect("equal")
        ax.set_xlim(37, 54)
        ax.set_ylim(Z_PISTA - 1.2, 5.5)
        ax.grid(alpha=0.25)
        ax.set_xlabel("x (mm) — lado direito, visto de trás")
    axs[0].set_ylabel("z (mm), 0 = face de cima da base")
    fig.tight_layout()
    fig.savefig(arq, dpi=110)
    plt.close(fig)


def distancia_eixos_caixa():
    """Distancia entre o eixo do motor (furo O10,18) e o eixo da roda (furo O2,0),
    lida do gearbox.stl (os dois furos sao paralelos a x)."""
    g = stl("gearbox.stl").transform([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0]])
    centros = {}
    for p in g.slice(6.0).to_polygons():
        p = np.asarray(p)
        if 0.5 * np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1]) < 0:
            d = 2 * np.hypot(*(p - p.mean(0)).T).mean()
            for nome, alvo in (("motor", 10.18), ("eixo", 2.0)):
                if abs(d - alvo) < 0.1:
                    centros[nome] = p.mean(0)
    return float(np.hypot(*(centros["motor"] - centros["eixo"])))


def menor_folga(g0, p0, a, z_eng, z_pin=11, n_fase=40, n_phi=8):
    """Gira a engrenagem (contorno g0, z_eng dentes) e o pinhao (p0) juntos por um passo e
    devolve a menor distancia entre os contornos na pior posicao (flanco ou ponta x fundo).
    Negativa = interferencia (area sobreposta, em mm2)."""
    from shapely import affinity
    from shapely.geometry import box
    janela = box(a - 4, -4, a + 4, 4)
    piores = []
    for fase in np.linspace(0, 2 * np.pi / z_pin, n_fase + 1)[:-1]:
        w = np.inf
        for phi in np.linspace(0, 2 * np.pi / z_eng, n_phi + 1)[:-1]:
            g = affinity.rotate(g0, phi, origin=(0, 0), use_radians=True).intersection(janela)
            p = affinity.translate(affinity.rotate(p0, fase - phi * z_eng / z_pin, origin=(0, 0),
                                                   use_radians=True), a, 0)
            i = g.intersection(p).area
            w = min(w, -i if i > 1e-9 else g.distance(p))
        piores.append((w, fase))
    return max(piores)


def razao_contato(a, z1, x1, z2, m, alfa, corte_ponta2=0.0):
    al = np.radians(alfa)
    rb1, rb2 = m * z1 / 2 * np.cos(al), m * z2 / 2 * np.cos(al)
    ra1, ra2 = m * z1 / 2 + m * (1 + x1), m * z2 / 2 + m - corte_ponta2
    aw = np.arccos((rb1 + rb2) / a)
    return (np.sqrt(ra1 ** 2 - rb1 ** 2) + np.sqrt(ra2 ** 2 - rb2 ** 2) - a * np.sin(aw)) / (np.pi * m * np.cos(al))


def engrenagem_no_aro():
    """Poe cada versao da engrenagem sobre a aba do wheel_rim.stl do EVA-RT, com os furos
    alinhados aos pinos, e mede a interferencia em 3D. Devolve (topo da aba, altura dos
    pinos, diametro e angulos dos pinos, {versao: interferencia em mm3})."""
    aro = stl("wheel_rim.stl")
    z_max = aro.bounding_box()[5]
    baixo, cima = z_max - 4.0, z_max - 0.01          # acha o topo da aba (onde so sobram os pinos)
    for _ in range(30):                              # a aba tem O16,5; os pinos chegam a r ~7
        z = (baixo + cima) / 2
        if max(np.hypot(*np.asarray(p).T).max() for p in aro.slice(z).to_polygons()) > 7.5:
            baixo = z
        else:
            cima = z
    z_aba = (baixo + cima) / 2
    pinos = [np.asarray(p) for p in aro.slice(z_max - 0.5).to_polygons()]
    d_pino = float(np.mean([2 * np.sqrt(abs(0.5 * np.sum(p[:, 0] * np.roll(p[:, 1], -1)
                                                         - np.roll(p[:, 0], -1) * p[:, 1])) / np.pi) for p in pinos]))
    ang = sorted(float(np.degrees(np.arctan2(*p.mean(0)[::-1])) % 360) for p in pinos)
    res = {}
    for n in gp.VERSOES_ENGRENAGEM:
        g = gp.engrenagem_aro(n).rotate((0, 0, ang[0])).translate((0, 0, z_aba))
        res[n] = inter(g, aro)
    return z_aba, z_max - z_aba, d_pino, ang, res


def conferir_engrenamento(arq=None):
    """Engrenagem de 64 dentes (as 3 versoes de gp.VERSOES_ENGRENAGEM) x pinhao 11T m0,3.
    Testa o pinhao sem deslocamento de perfil e com +0,33, na distancia entre eixos lida da
    caixa e com ela 0,10/0,05 mm mais curta ou 0,10 mm mais longa (PETG encolhe; motor e
    eixo podem assentar fora de centro). Confere tambem o encaixe no aro em 3D."""
    from shapely.geometry import Polygon
    e = gp.ENGRENAGEM
    a = distancia_eixos_caixa()
    nominal = e["m"] * (e["z"] + 11) / 2
    print(f"\nEngrenamento: distancia entre eixos na caixa {a:.3f} mm (nominal 64T + 11T: {nominal:.3f}; "
          f"sem folga com pinhao +0,33: {gp_sem_folga(e, 0.33):.3f})")
    print("  menor distancia entre contornos (mm; negativo = interfere), pior posicao numa volta:")
    desvios = (-0.10, -0.05, 0.0, +0.10)
    print("    versao       pinhao   " + "  ".join(f"a{d:+.2f}".replace("+0.00", " caixa") for d in desvios)
          + "   razao de contato (caixa)")
    pin = {x: Polygon(gp.perfil_engrenagem(11, e["m"], e["alfa"], x, 0.0)).buffer(0) for x in (0.0, 0.33)}
    figs = {}
    for n, v in gp.VERSOES_ENGRENAGEM.items():
        g0 = Polygon(gp.perfil_versao(n)).buffer(0)
        for x, p0 in pin.items():
            r = [menor_folga(g0, p0, a + d, e["z"]) for d in desvios]
            eps = razao_contato(a, 11, x, e["z"], e["m"], e["alfa"], v["corte_ponta"])
            print(f"    {n} {v['nome']:8s}  x={x:+.2f}  " + "  ".join(f"{w:+.3f}" for w, _ in r)
                  + f"   {eps:.2f}" + ("   INTERFERE NA CAIXA" if r[2][0] < 0 else ""))
            if n == 2:
                figs[x] = (r[2][1], r[2][0], g0, p0)
    z_aba, h_pino, d_pino, ang, res = engrenagem_no_aro()
    print(f"  aro do EVA-RT: aba em z = {z_aba:.2f}, 6 pinos de O{d_pino:.3f} x {h_pino:.2f} mm "
          f"(a {', '.join(f'{t:.0f}' for t in ang)} graus); engrenagem de {e['largura']:.1f} mm")
    print(f"  furo dos pinos O{e['d_furo_pino']} x pino O{d_pino:.3f}: folga radial {(e['d_furo_pino'] - d_pino) / 2:.3f}; "
          f"furo central O{e['d_furo_central']} x bucha O6,0: folga radial {(e['d_furo_central'] - 6.0) / 2:.2f}")
    print("  engrenagem x aro (3D): " + ", ".join(f"versao {n} {w:.3f} mm3" for n, w in res.items()))
    for n, v in gp.VERSOES_ENGRENAGEM.items():
        rf = e["m"] * e["z"] / 2 - 1.25 * e["m"] - v["fundo_extra"]
        print(f"  versao {n}: {n} furo(s) de marca O{e['d_marca']} a r {e['r_marca']}; parede ate o fundo do dente "
              f"{rf - e['r_marca'] - e['d_marca'] / 2:.2f} mm")
    for nome, d_pneu in (("pneu de O22", 22.0), ("StickyMAX esticado no aro (~O22,5)", 22.5)):
        print(f"  ponta dos dentes a {(d_pneu / 2 - e['m'] * (e['z'] / 2 + 1)):.2f} mm da pista com {nome}")
    if arq:
        from shapely import affinity
        fig, axs = plt.subplots(1, 2, figsize=(12, 5.4))
        for ax, (x, (fase, f, g0, p0)) in zip(axs, figs.items()):
            p = affinity.translate(affinity.rotate(p0, fase, origin=(0, 0), use_radians=True), a, 0)
            for poly, c in ((g0, CORES["patim"]), (p, "#c9a227")):
                xs, ys = poly.exterior.xy
                ax.fill(xs, ys, fc=c, ec="k", lw=0.4, alpha=0.85)
            ax.set_xlim(a - 4.2, a + 2.6)
            ax.set_ylim(-3.2, 3.2)
            ax.set_aspect("equal")
            ax.grid(alpha=0.25)
            ax.set_title(f"64T versão 2 (média) x pinhão 11T, deslocamento {x:+.2f}\n"
                         f"entre eixos {a:.2f} mm, menor folga {f:.3f} mm".replace(".", ","), fontsize=10)
        fig.tight_layout()
        fig.savefig(arq, dpi=110)
        plt.close(fig)


def gp_sem_folga(e, x_pinhao):
    """Distancia entre eixos de engrenamento sem folga (x da 64T = 0)."""
    al = np.radians(e["alfa"])
    inv = lambda t: np.tan(t) - t
    alvo = inv(al) + 2 * np.tan(al) * x_pinhao / (e["z"] + 11)
    lo, hi = al, al + 0.3
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if inv(mid) < alvo else (lo, mid)
    return e["m"] * (e["z"] + 11) / 2 * np.cos(al) / np.cos(lo)


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


ROTULO_MESA = {"gearbox": "caixa D", "gearbox_esquerdo_espelhado": "caixa E", "impeller_base_1": "carcaça",
               "impeller_base_2": "tampa\nmotor", "impeller_fan": "hélice", "placa_succao_rebaixo": "placa de sucção",
               "gabarito_base_teste": "gabarito", "wheel_rim": "aro", "bead": "B", "battery_holder": "bat",
               "presilha_vareta_tras_base1.6": "PT", "presilha_vareta_frente_asa": "PF",
               "patim_v1_direito_barra1.6": "pD", "patim_v1_esquerdo_barra1.6": "pE", "bloco_transversal_asa": "bl"}


def fig_mesas(arq):
    """Vista de cima das mesas de mecânica/mesas/ (o mesmo arranjo do gerar_pecas.py)."""
    import trimesh
    paineis = [(n, gp.arranjar(p)) for n, p in gp.MESAS_FDM.items()]
    for nome_r in ("resina_9_engrenagens", "resina_2_engrenagens_v2_media"):
        r = trimesh.load(gp.MESAS / f"{nome_r}.stl")
        paineis.append((nome_r, [("engrenagem", np.asarray(r.vertices), np.asarray(r.faces))]))
    ncol = 4
    nlin = -(-len(paineis) // ncol)
    fig, axs = plt.subplots(nlin, ncol, figsize=(4.75 * ncol, 5.4 * nlin + 0.4))
    axs = axs.ravel()
    for ax in axs[len(paineis):]:
        ax.set_axis_off()
    for ax, (nome, itens) in zip(axs, paineis):
        ax.add_patch(matplotlib.patches.Rectangle((0, 0), 180, 180, fc="#f4f4f4", ec="#999", lw=1))
        for peca, v, f in itens:
            m = Manifold(Mesh(vert_properties=np.asarray(v, np.float32), tri_verts=np.asarray(f, np.uint32)))
            base = re.sub(r"_\d+$", "", peca)
            c = "#c9a227" if nome.startswith("resina") else CORES["patim"]
            for pol in m.project().to_polygons():
                pol = np.asarray(pol)
                ax.fill(*np.r_[pol, pol[:1]].T, fc=c, ec="k", lw=0.3, alpha=0.8)
            if base in ROTULO_MESA:
                cx, cy = (v[:, 0].max() + v[:, 0].min()) / 2, (v[:, 1].max() + v[:, 1].min()) / 2
                ax.text(cx, cy, ROTULO_MESA[base], ha="center", va="center", fontsize=7, color="#222")
        ax.set_xlim(-2, 182)
        ax.set_ylim(-2, 182)
        ax.set_aspect("equal")
        ax.set_xticks(range(0, 181, 30))
        ax.set_yticks(range(0, 181, 30))
        ax.tick_params(labelsize=7)
        n = len(itens) if not nome.startswith("resina") else int(nome.split("_")[1])
        if nome.startswith("resina_2"):
            nome = "resina_2_engrenagens_v1, v2 ou v3"
        ax.set_title(f"{nome}\n{n} peças, mesa de 180 × 180 mm", fontsize=10)
    fig.text(0.5, 0.01, "PT/PF = presilha de trás/da frente, pD/pE = patim direito/esquerdo, bl = bloco da transversal, "
             "B = bucha (bead), bat = apoio da bateria. Resina: fileira de cima versão 1, do meio 2, de baixo 3.",
             ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(arq, dpi=100)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--furos", type=float, default=63.14, help="distancia entre furos base-barra (mm)")
    ap.add_argument("--esp-barra", type=float, default=gp.ESP_BARRA, help="espessura da barra V1 (mm)")
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
        fig_corte_presilha(s, FIG / "corte_presilha.png")
        conferir_engrenamento(FIG / "engrenamento.png")
        fig_mesas(FIG / "mesas.png")
        print(f"Figuras em {FIG.relative_to(RAIZ)}/")
    if a.sem_figuras:
        conferir_engrenamento()
    print(f"\nMaior interferencia: {pior:.3f} mm3")


if __name__ == "__main__":
    main()
