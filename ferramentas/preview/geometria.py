#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Geometria mecanica da placa base do seguidor (clone do EVA-RT) para o preview de posicionamento.

Saidas nesta pasta: geometria.json e conf_geometria.png.
Referencial: mm, origem (0,0) = centro da ventoinha (furo D17), +x = direita, +y = frente.
Rodar: <venv>/bin/python -I geometria.py   (le so arquivos do repositorio; grava so aqui)
"""
import csv
import json
import math
import os
import re
import struct
import sys
import zipfile

import numpy as np
import ezdxf
import contourpy
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.path import Path as MPath  # noqa: E402
from matplotlib.patches import Polygon as MPolygon, Circle as MCircle  # noqa: E402

P = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
DXF = os.path.join(REPO, "hardware/contorno/EVA-RT_contorno_B_degraus.dxf")
STL_DIR = os.path.join(REPO, "referencias/eva-rt/3d_models")
ZIP_GERBER = os.path.join(REPO, "referencias/eva-rt/pcb_files/Gerber_EVA_RT_PCB_2025-02-02.zip")
GERBER_DIR = os.path.join(P, "gerber_eva_rt_zip")
EPRJ_PCB = os.path.join(P, "eprj", "eva_rt_pcb_b73a4a.txt")  # gerado por extrair_eprj.py
COMP_CSV = os.path.join(P, "eva_rt_componentes.csv")
MIL = 0.0254

STEP = 0.1                      # grade de trabalho (mm)
X0, X1, Y0, Y1 = -80.0, 80.0, -50.0, 90.0
NX = int(round((X1 - X0) / STEP))
NY = int(round((Y1 - Y0) / STEP))
XC = X0 + (np.arange(NX) + 0.5) * STEP
YC = Y0 + (np.arange(NY) + 0.5) * STEP

CONTACT_H = 1.0                 # triangulos ate 1,0 mm da face de apoio = contato
CHORD_MAX = 0.2                 # corda maxima na discretizacao dos arcos

LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    LOG.append(s)
    print(s)


# ----------------------------------------------------------------------------
# 1. Contorno (DXF)
# ----------------------------------------------------------------------------
def load_contour():
    doc = ezdxf.readfile(DXF)
    msp = doc.modelspace()
    units = doc.header.get("$INSUNITS")
    pls = [e for e in msp if e.dxftype() == "LWPOLYLINE"]
    circles = [e for e in msp if e.dxftype() == "CIRCLE"]
    assert len(pls) == 1 and pls[0].closed, "esperado 1 LWPOLYLINE fechada"
    pl = pls[0]
    raw = [(float(x), float(y), float(b)) for x, y, b in pl.get_points("xyb")]
    n = len(raw)
    out = []
    for i in range(n):
        x0, y0, b = raw[i]
        x1, y1, _ = raw[(i + 1) % n]
        out.append((x0, y0))
        if abs(b) > 1e-12:  # arco de bulge: discretiza com corda <= CHORD_MAX
            dx, dy = x1 - x0, y1 - y0
            c = math.hypot(dx, dy)
            theta = 4.0 * math.atan(b)
            r = c * (1.0 + b * b) / (4.0 * abs(b))
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            hc = (c / 2) * (1 - b * b) / (2 * b)
            cx, cy = mx + (-dy / c) * hc, my + (dx / c) * hc
            a0 = math.atan2(y0 - cy, x0 - cx)
            nseg = max(2, int(math.ceil(abs(theta) * r / CHORD_MAX)))
            for k in range(1, nseg):
                a = a0 + theta * k / nseg
                out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    pts = np.array(out)
    circ = circles[0]
    info = dict(unidades_dxf=units, n_vertices=len(pts),
                bbox=[pts[:, 0].min(), pts[:, 0].max(), pts[:, 1].min(), pts[:, 1].max()],
                area=0.5 * abs(np.sum(pts[:, 0] * np.roll(pts[:, 1], -1) - np.roll(pts[:, 0], -1) * pts[:, 1])),
                circulo=(float(circ.dxf.center.x), float(circ.dxf.center.y), float(circ.dxf.radius)))
    return pts, info


# ----------------------------------------------------------------------------
# 2. Furos (arquivo de furacao do Gerber do EVA-RT)
# ----------------------------------------------------------------------------
def ensure_gerber():
    need = ["Drill_NPTH_Through.DRL", "Drill_PTH_Through.DRL"]
    if all(os.path.exists(os.path.join(GERBER_DIR, f)) for f in need):
        return
    os.makedirs(GERBER_DIR, exist_ok=True)
    with zipfile.ZipFile(ZIP_GERBER) as z:
        for info in z.infolist():
            name = os.path.basename(info.filename)
            if name.lower().endswith((".drl", ".gko", ".gdd", ".txt")) and name:
                with z.open(info) as src, open(os.path.join(GERBER_DIR, name), "wb") as dst:
                    dst.write(src.read())


def parse_drill(path):
    tools, holes, slots = {}, [], []
    tool = None
    for raw in open(path, encoding="latin1"):
        line = raw.strip()
        m = re.match(r"^T(\d+)C([\d.]+)$", line)
        if m:
            tools[m.group(1)] = float(m.group(2))
            continue
        m = re.match(r"^T(\d+)$", line)
        if m:
            tool = m.group(1)
            continue
        m = re.match(r"^X(-?[\d.]+)Y(-?[\d.]+)G85X(-?[\d.]+)Y(-?[\d.]+)$", line)
        if m:
            x1, y1, x2, y2 = map(float, m.groups())
            slots.append((tool, x1, y1, x2, y2))
            continue
        m = re.match(r"^X(-?[\d.]+)Y(-?[\d.]+)$", line)
        if m and tool is not None:
            holes.append((tool, float(m.group(1)), float(m.group(2))))
    return tools, holes, slots


def load_holes():
    ensure_gerber()
    tn, hn, _ = parse_drill(os.path.join(GERBER_DIR, "Drill_NPTH_Through.DRL"))
    tp, hp, sp = parse_drill(os.path.join(GERBER_DIR, "Drill_PTH_Through.DRL"))
    npth = [(x, y, tn[t]) for t, x, y in hn]
    slots = []
    for t, x1, y1, x2, y2 in sp:
        d = tp[t]
        length = math.hypot(x2 - x1, y2 - y1) + d
        slots.append(dict(xc=(x1 + x2) / 2, yc=(y1 + y2) / 2, w=length, h=d, dx=(x2 - x1), dy=(y2 - y1)))
    return npth, slots, tn, tp


def nome_furo(x, y):
    sx = "D" if x > 0 else "E"
    if abs(abs(x) - 15.556) < 0.1 and abs(abs(y) - 15.556) < 0.1:
        return "carcaca_" + ("N" if y > 0 else "S") + ("E" if x > 0 else "O")
    if abs(abs(x) - 35.25) < 0.1:
        return f"suporte_motor_{sx}_{'frente' if y > -10 else 'tras'}"
    if abs(abs(x) - 43.75) < 0.1:
        return f"presilha_{sx}_{'frente' if y > 4.5 else 'tras'}"
    return f"furo_{x:.2f}_{y:.2f}".replace(".", "p")


# ----------------------------------------------------------------------------
# 3. STL (binario) e deteccao de furos verticais
# ----------------------------------------------------------------------------
STL_DT = np.dtype([("n", "<f4", (3,)), ("v", "<f4", (3, 3)), ("a", "<u2")])


def read_stl(name):
    b = open(os.path.join(STL_DIR, name + ".stl"), "rb").read()
    n = struct.unpack("<I", b[80:84])[0]
    if 84 + 50 * n != len(b):
        raise ValueError(f"{name}: STL nao binario (ASCII nao tratado aqui)")
    T = np.frombuffer(b[84:84 + 50 * n], dtype=STL_DT)
    return T["v"].astype(np.float64)  # (N,3,3)


def _key(p):
    return (round(float(p[0]), 4), round(float(p[1]), 4), round(float(p[2]), 4))


def vertical_walls(V, nz_max=0.25, min_tris=8):
    """Paredes verticais (|nz|<0.25) agrupadas por arestas compartilhadas; ajusta circulo em XY."""
    E1 = V[:, 1] - V[:, 0]
    E2 = V[:, 2] - V[:, 0]
    C = np.cross(E1, E2)
    L = np.linalg.norm(C, axis=1)
    L[L == 0] = 1.0
    N = C / L[:, None]
    idx = np.where(np.abs(N[:, 2]) < nz_max)[0]
    emap = {}
    for t in idx:
        vs = [_key(V[t, k]) for k in range(3)]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            emap.setdefault(tuple(sorted((vs[a], vs[b]))), []).append(t)
    parent = {int(t): int(t) for t in idx}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for ts in emap.values():
        for u in ts[1:]:
            ra, rb = find(int(ts[0])), find(int(u))
            if ra != rb:
                parent[ra] = rb
    comps = {}
    for t in idx:
        comps.setdefault(find(int(t)), []).append(int(t))
    res = []
    for comp in comps.values():
        if len(comp) < min_tris:
            continue
        pts = V[comp].reshape(-1, 3)
        xy = np.unique(np.round(pts[:, :2], 4), axis=0)
        if len(xy) < 6:
            continue
        x, y = xy[:, 0], xy[:, 1]
        A = np.c_[2 * x, 2 * y, np.ones(len(x))]
        sol = np.linalg.lstsq(A, x * x + y * y, rcond=None)[0]
        cx, cy = sol[0], sol[1]
        r = math.sqrt(max(sol[2] + cx * cx + cy * cy, 0.0))
        err = float(np.max(np.abs(np.hypot(x - cx, y - cy) - r)))
        ang = np.sort(np.arctan2(y - cy, x - cx))
        gap = np.degrees(np.max(np.diff(np.r_[ang, ang[0] + 2 * np.pi])))
        mid = V[comp].mean(axis=1)[:, :2]
        toward = np.sum(N[comp][:, :2] * (np.array([cx, cy]) - mid), axis=1)
        if err < 0.05 and gap < 120:
            res.append(dict(cx=float(cx), cy=float(cy), r=float(r), zmin=float(pts[:, 2].min()),
                            zmax=float(pts[:, 2].max()), furo=bool(np.mean(toward > 0) > 0.5)))
    return res


# ----------------------------------------------------------------------------
# 4. Transformacao das pecas e rasterizacao (alturas acima da face de apoio)
# ----------------------------------------------------------------------------
def part_tris(V, zc, sign, mirror=False, rot=0.0, t=(0.0, 0.0)):
    """h = sign*(z - zc): altura acima da face de apoio (TOP: sign=+1; BOTTOM: sign=-1)."""
    W = V.copy()
    W[:, :, 2] = sign * (W[:, :, 2] - zc)
    if mirror:
        W[:, :, 0] = -W[:, :, 0]
    if rot:
        c, s = math.cos(rot), math.sin(rot)
        x, y = W[:, :, 0].copy(), W[:, :, 1].copy()
        W[:, :, 0] = c * x - s * y
        W[:, :, 1] = s * x + c * y
    W[:, :, 0] += t[0]
    W[:, :, 1] += t[1]
    return W[:, :, :2].copy(), W[:, :, 2].copy()


def rasterize(tris, hs):
    """Cobertura XY, mascara de contato (todos os vertices h<=1) e altura minima por celula."""
    cov = np.zeros((NY, NX), bool)
    cont = np.zeros((NY, NX), bool)
    hmin = np.full((NY, NX), np.inf)
    for t in range(len(tris)):
        a, b, c = tris[t]
        ha, hb, hc = hs[t]
        den = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(den) < 1e-12:
            continue
        ix0 = max(0, int(math.floor((min(a[0], b[0], c[0]) - X0) / STEP)))
        ix1 = min(NX, int(math.ceil((max(a[0], b[0], c[0]) - X0) / STEP)) + 1)
        iy0 = max(0, int(math.floor((min(a[1], b[1], c[1]) - Y0) / STEP)))
        iy1 = min(NY, int(math.ceil((max(a[1], b[1], c[1]) - Y0) / STEP)) + 1)
        if ix1 <= ix0 or iy1 <= iy0:
            continue
        X = XC[ix0:ix1][None, :]
        Y = YC[iy0:iy1][:, None]
        wb = ((X - a[0]) * (c[1] - a[1]) - (Y - a[1]) * (c[0] - a[0])) / den
        wc = ((b[0] - a[0]) * (Y - a[1]) - (b[1] - a[1]) * (X - a[0])) / den
        wa = 1.0 - wb - wc
        ins = (wa >= -1e-9) & (wb >= -1e-9) & (wc >= -1e-9)
        if not ins.any():
            continue
        hp = wa * ha + wb * hb + wc * hc
        sub = (slice(iy0, iy1), slice(ix0, ix1))
        cov[sub] |= ins
        cur = hmin[sub]
        hmin[sub] = np.where(ins, np.minimum(cur, hp), cur)
        if max(ha, hb, hc) <= CONTACT_H:
            cont[sub] |= ins
    return cov, cont, hmin


def fill_mask_polygons(mask, tol=0.03):
    """Poligonos sem furos (furos internos fechados) a partir de uma mascara booleana."""
    if not mask.any():
        return []
    gen = contourpy.contour_generator(XC, YC, mask.astype(float), line_type="Separate")
    loops = [np.asarray(l) for l in gen.lines(0.5) if len(l) >= 4]
    paths = [MPath(l) for l in loops]
    out = []
    for i, li in enumerate(loops):
        depth = 0
        for j, pj in enumerate(paths):
            if i != j and pj.contains_point(li[0]):
                depth += 1
        if depth % 2 == 0:  # contorno externo: interior (inclusive furos) fica preenchido
            if depth == 0:
                out.append(dp_simplify(li, tol))
    return out


def _dp_open(pts, tol):
    """Douglas-Peucker em polilinha aberta (extremos mantidos)."""
    n = len(pts)
    if n <= 2:
        return pts
    keep = np.zeros(n, bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = pts[i], pts[j]
        seg = b - a
        L = math.hypot(seg[0], seg[1])
        if L < 1e-12:
            d = np.hypot(pts[i + 1:j, 0] - a[0], pts[i + 1:j, 1] - a[1])
        else:
            d = np.abs((pts[i + 1:j, 0] - a[0]) * seg[1] - (pts[i + 1:j, 1] - a[1]) * seg[0]) / L
        k = int(np.argmax(d))
        if d[k] > tol:
            m = i + 1 + k
            keep[m] = True
            stack.append((i, m))
            stack.append((m, j))
    return pts[keep]


def dp_simplify(pts, tol):
    """Simplifica anel fechado (primeiro ponto nao repetido no fim)."""
    pts = np.asarray(pts, dtype=float)
    if len(pts) < 4:
        return pts
    if np.allclose(pts[0], pts[-1]):
        P = pts[:-1]
        m = int(np.argmax(np.hypot(P[:, 0] - P[0, 0], P[:, 1] - P[0, 1])))
        a = _dp_open(P[:m + 1], tol)
        b = _dp_open(np.vstack([P[m:], P[:1]]), tol)
        return np.vstack([a[:-1], b[:-1]])
    return _dp_open(pts, tol)


def area_of(poly):
    x, y = poly[:, 0], poly[:, 1]
    return 0.5 * abs(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def pts_list(poly):
    return [[round(float(x), 3), round(float(y), 3)] for x, y in poly]


# ----------------------------------------------------------------------------
# 5. Pads do EVA-RT (projeto EasyEDA decodificado) e componentes originais
# ----------------------------------------------------------------------------
def eva_top_items():
    lines = open(EPRJ_PCB, encoding="utf-8").read().splitlines()
    i0 = next(i for i, l in enumerate(lines) if l.startswith('["DOCTYPE","PCB"'))
    items = []
    for l in lines[i0:]:
        o = json.loads(l)
        if o[0] == "PAD" and o[4] in (1, 12):
            shp = o[10] if isinstance(o[10], list) else o[9]
            r = 0.6
            if isinstance(shp, list) and len(shp) >= 3 and isinstance(shp[1], (int, float)):
                r = max(shp[1], shp[2]) / 2 * MIL
            items.append(("pad_" + str(o[5]), o[6] * MIL, o[7] * MIL, r))
        elif o[0] == "VIA":
            items.append(("via_" + str(o[1]), o[5] * MIL, o[6] * MIL, o[8] / 2 * MIL))
    return items


def load_components():
    rows = []
    with open(COMP_CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            rows.append(dict(ref=r["ref"], lado=r["lado"], x=float(r["x_mm"]), y=float(r["y_mm"]),
                             rot=float(r["rot"]), valor=r["valor"]))
    return rows


def disk_hits_mask(mask, x, y, r):
    """True se algum centro de celula dentro do disco (x,y,r) estiver marcado na mascara."""
    ix = int(round((x - X0) / STEP - 0.5))
    iy = int(round((y - Y0) / STEP - 0.5))
    k = int(math.ceil(r / STEP)) + 1
    jx0, jx1 = max(0, ix - k), min(NX, ix + k + 1)
    jy0, jy1 = max(0, iy - k), min(NY, iy + k + 1)
    if jx1 <= jx0 or jy1 <= jy0:
        return False
    XX, YY = np.meshgrid(XC[jx0:jx1], YC[jy0:jy1])
    inside = (XX - x) ** 2 + (YY - y) ** 2 <= r * r
    return bool(np.any(mask[jy0:jy1, jx0:jx1] & inside))


# ----------------------------------------------------------------------------
# 6. Principal
# ----------------------------------------------------------------------------
def main():
    log("== 1. Contorno (DXF)")
    cont_pts, cinfo = load_contour()
    bb = cinfo["bbox"]
    log(f"  unidades DXF INSUNITS={cinfo['unidades_dxf']} (4 = mm); vertices discretizados={cinfo['n_vertices']}")
    log(f"  bbox x [{bb[0]:.3f}, {bb[1]:.3f}]  y [{bb[2]:.3f}, {bb[3]:.3f}]  (esperado x +-74,1; y -32..25,6)")
    log(f"  area={cinfo['area']:.2f} mm2; CIRCLE centro=({cinfo['circulo'][0]:.3f},{cinfo['circulo'][1]:.3f}) r={cinfo['circulo'][2]:.3f}")
    cpath = MPath(cont_pts)

    log("== 2. Furos (furacao do Gerber do EVA-RT, unidades mm)")
    npth, slots, tn, tp = load_holes()
    log(f"  NPTH: {len(npth)} furos, diametros {sorted(set(round(d, 3) for _, _, d in npth))}")
    for s in slots:
        log(f"  rasgo: centro=({s['xc']:.3f},{s['yc']:.3f}) comprimento total={s['w']:.3f} largura={s['h']:.3f} dir=({s['dx']:.3f},{s['dy']:.3f})")
    furos = []
    dentro = []
    for x, y, d in sorted(npth, key=lambda t: (t[0], t[1])):
        dentro.append(cpath.contains_point((x, y)))
        furos.append(dict(nome=nome_furo(x, y), x=round(x, 3), y=round(y, 3), d=round(d, 3), tipo="furo"))
    fan = cinfo["circulo"]
    furos.insert(0, dict(nome="ventoinha", x=round(fan[0], 3), y=round(fan[1], 3), d=round(2 * fan[2], 3), tipo="furo"))
    for s, nm in zip(sorted(slots, key=lambda s: s["xc"]), ["velcro_E", "velcro_D"]):
        furos.append(dict(nome=nm, x=round(s["xc"], 3), y=round(s["yc"], 3), w=round(s["w"], 3), h=round(s["h"], 3), tipo="rasgo"))
    dentro += [cpath.contains_point((s["xc"], s["yc"])) for s in slots]
    dentro.append(cpath.contains_point((0.0, 0.0)))
    log(f"  furos dentro do contorno B: {sum(dentro)}/{len(dentro)}")

    log("== 3. Pecas STL (referencial da placa)")
    V = {n: read_stl(n) for n in ["impeller_base_1", "impeller_fan", "impeller_base_2", "suction_base",
                                   "gearbox", "battery_holder", "barilla_clamp"]}
    for n in V:
        mn = V[n].reshape(-1, 3).min(0)
        mx = V[n].reshape(-1, 3).max(0)
        log(f"  {n}: {len(V[n])} tri; bbox x[{mn[0]:.2f},{mx[0]:.2f}] y[{mn[1]:.2f},{mx[1]:.2f}] z[{mn[2]:.2f},{mx[2]:.2f}]")
    return dict(cont_pts=cont_pts, cinfo=cinfo, furos=furos, npth=npth, slots=slots, V=V,
                cpath=cpath, dentro=dentro)


def _loops_depth(mask):
    """Anéis do contorno da mascara com a profundidade de aninhamento (0 = externo, 1 = furo...)."""
    if not mask.any():
        return []
    gen = contourpy.contour_generator(XC, YC, mask.astype(float), line_type="Separate")
    loops = [np.asarray(l) for l in gen.lines(0.5) if len(l) >= 4]
    paths = [MPath(l) for l in loops]
    res = []
    for i, li in enumerate(loops):
        depth = sum(1 for j, pj in enumerate(paths) if i != j and pj.contains_point(li[0]))
        res.append((li, depth, abs(poly_area(li))))
    return res


def poly_area(p):
    x, y = p[:, 0], p[:, 1]
    return 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)


def loops_all(mask):
    """Anéis da mascara (externo + furos). Falhas de malha menores que 1 mm2 sao descartadas."""
    out = []
    for li, depth, ar in _loops_depth(mask):
        if depth % 2 == 0 and ar < 0.5:
            continue  # ilhota de ruido
        if depth % 2 == 1 and ar < 1.0:
            continue  # falha de cobertura da malha: trata como preenchido
        out.append(dp_simplify(li, 0.03))
    return out


def rings_fill(mask):
    """Pegada preenchida: so anéis externos (furos internos ficam preenchidos)."""
    return [dp_simplify(li, 0.03) for li, depth, ar in _loops_depth(mask) if depth == 0 and ar >= 0.5]


def conflitos_rotacao(Vh, items, comps):
    """Para cada rotacao candidata da carcaca, conta pads/vias/componentes TOP do EVA-RT sob o contato."""
    rows = []
    for deg in (45, 135, 225, 315):
        tris, hs = part_tris(Vh, 0.0, 1.0, rot=math.radians(deg))
        cov, cont, hmin = rasterize(tris, hs)
        hits = [nm for nm, x, y, r in items if disk_hits_mask(cont, x, y, r)]
        hits += ["comp_" + c["ref"] for c in comps if c["lado"] == "TOP" and disk_hits_mask(cont, c["x"], c["y"], 1.0)]
        rows.append(dict(deg=deg, n=len(hits), hits=hits, area=float(np.count_nonzero(cont)) * STEP * STEP))
    return rows


def hole_match(centros_pe, furos_placa):
    """Erro maximo (mm) entre centros de furos transformados e o furo de placa mais proximo."""
    erros = []
    for (x, y) in centros_pe:
        dmin = min(math.hypot(x - fx, y - fy) for fx, fy in furos_placa)
        erros.append(dmin)
    return max(erros) if erros else None


def altura_apoio_bateria(Vb):
    """Altura (acima da face de apoio) das faces superiores do anel do suporte da bateria (|xy| <= 2,6)."""
    E1 = Vb[:, 1] - Vb[:, 0]
    E2 = Vb[:, 2] - Vb[:, 0]
    C = np.cross(E1, E2)
    L = np.linalg.norm(C, axis=1)
    L[L == 0] = 1.0
    N = C / L[:, None]
    up = N[:, 2] > 0.97
    cen = Vb.mean(axis=1)
    anel = up & (np.hypot(cen[:, 0], cen[:, 1]) <= 2.6)
    return round(float(cen[anel, 2].max()), 1)


def transforma_pt(x, y, mirror=False, rot=0.0, t=(0.0, 0.0)):
    if mirror:
        x = -x
    c, s = math.cos(rot), math.sin(rot)
    return (c * x - s * y + t[0], s * x + c * y + t[1])


def run():
    d = main()
    cont_pts, cinfo, furos, V = d["cont_pts"], d["cinfo"], d["furos"], d["V"]
    npth = d["npth"]
    furos_placa = [(x, y) for x, y, _ in npth]
    carc_pl = [(x, y) for x, y in furos_placa if abs(abs(x) - 15.556) < 0.1 and abs(abs(y) - 15.556) < 0.1]
    gear_pl = [(x, y) for x, y in furos_placa if abs(abs(x) - 35.25) < 0.1]
    pres_pl = [(x, y) for x, y in furos_placa if abs(abs(x) - 43.75) < 0.1]

    log("== 3b. Furos verticais detectados nos STL (r entre 0,5 e 3 mm = furos de parafuso)")
    holes_stl = {}
    for nm in ["impeller_base_1", "suction_base", "gearbox", "battery_holder", "barilla_clamp"]:
        w = vertical_walls(V[nm])
        pequenos = [h for h in w if 0.5 <= h["r"] <= 3.0 and h["furo"]]
        holes_stl[nm] = pequenos
        log(f"  {nm}: " + "; ".join(f"({h['cx']:.3f},{h['cy']:.3f}) d={2*h['r']:.2f}" for h in pequenos)
            + ("  [sem furo vertical de parafuso]" if not pequenos else ""))
        for h in w:
            if h["r"] > 3.0:
                log(f"     (parede circular grande: ({h['cx']:.3f},{h['cy']:.3f}) d={2*h['r']:.2f} z[{h['zmin']:.2f},{h['zmax']:.2f}])")

    log("== 4. Rotacao da carcaca (4 candidatas a 45 graus) - conflito com pads TOP e componentes do EVA-RT")
    items = eva_top_items()
    comps = load_components()
    rows = conflitos_rotacao(V["impeller_base_1"], items, comps)
    for r in rows:
        log(f"  giro {r['deg']:3d} deg: contato={r['area']:.2f} mm2; conflitos={r['n']} {r['hits'][:12]}")
    deg_escolhido = min(rows, key=lambda r: (r["n"], r["deg"]))["deg"]
    log(f"  escolhido: {deg_escolhido} deg")

    # verificacao: rotor/hub e carcaca nao devem tocar pads do EVA-RT dentro de r<=17 (rotor)
    tris, hs = part_tris(V["impeller_fan"], 0.0, 1.0)
    cov_f, cont_f, _ = rasterize(tris, hs)
    tris2, hs2 = part_tris(V["impeller_base_2"], 0.0, 1.0)
    cov_h, cont_h, _ = rasterize(tris2, hs2)
    cont_fan = cont_f | cont_h
    hits_fan = [nm for nm, x, y, r in items if disk_hits_mask(cont_fan, x, y, r)]
    log(f"  rotor+hub: contato={float(np.count_nonzero(cont_fan))*STEP*STEP:.1f} mm2; pads TOP sob o contato do rotor: {len(hits_fan)}")

    # ------------------------------------------------------------------
    # instancias das pecas (vname, zc, sinal, espelho, rotacao, translacao)
    # ------------------------------------------------------------------
    rot = math.radians(deg_escolhido)
    INST = [
        dict(nome="carcaca", vname="impeller_base_1", zc=0.0, sign=1.0, mirror=False, rot=rot, t=(0.0, 0.0),
             face="TOP", fonte="stl", conf="media",
             obs="Carcaca da ventoinha (impeller_base_1). Pes (4) em (+-15,556; +-15,556) = furos NPTH D2,0 (STL D1,85), erro 0,000 mm. Giro de 45 graus: os 4 giros de 45 graus casam os furos e nenhum conflita com pads do EVA-RT; escolhido 45 graus (linguetas traseiras). Confianca media so pela orientacao das linguetas (~2 mm2 de pe)."),
        dict(nome="ventoinha_base", vname="impeller_fan", zc=0.0, sign=1.0, mirror=False, rot=0.0, t=(0.0, 0.0),
             face="TOP", fonte="stl", conf="media", extra=True,
             obs="Rotor da ventoinha (impeller_fan, D34 x 9 mm, base em z=0) + hub (impeller_base_2, D19,6): centro da placa, sobre a placa. Nao esta na lista do briefing; incluido porque toca a placa."),
        dict(nome="succao", vname="suction_base", zc=0.6, sign=-1.0, mirror=False, rot=0.0, t=(0.0, -27.5),
             face="BOTTOM", fonte="stl", conf="alta",
             obs="Placa de succao (suction_base), face de baixo. Deslocamento y -27,5 (furo D17 do STL em (0,27,5) = centro da ventoinha; furos D2 em (+-15,557; -15,556/+15,556)). Furos internos preenchidos."),
        dict(nome="motor_sup_D", vname="gearbox", zc=-2.5, sign=1.0, mirror=False, rot=0.0, t=(30.5, -19.027),
             face="TOP", fonte="stl", conf="alta",
             obs="Suporte do motor direito (gearbox): flange de 2,5 mm apoiada em z=-2,5 (STL). Furos D2 do flange casam com (35,25; -3,733) e (35,25; -26,55)."),
        dict(nome="motor_sup_E", vname="gearbox", zc=-2.5, sign=1.0, mirror=True, rot=0.0, t=(-30.5, -19.027),
             face="TOP", fonte="stl", conf="alta",
             obs="Suporte do motor esquerdo: mesma peca espelhada em x (copia do direito)."),
        dict(nome="suporte_bateria", vname="battery_holder", zc=0.0, sign=1.0, mirror=False, rot=0.0, t=(0.0, -24.6),
             face="TOP", fonte="stl", conf="baixa",
             obs="Suporte da bateria (battery_holder): anel D5 (apoio em z=3,0 mm) + lingueta de 2 mm. Sem furo de placa para casar; posicao por hipotese (centro do anel na frente da bateria, x=0)."),
        dict(nome="presilha_D_tras", vname="barilla_clamp", zc=0.0, sign=1.0, mirror=False, rot=0.0, t=(43.0, -0.75),
             face="TOP", fonte="stl", conf="baixa",
             obs="Presilha da vareta (barilla_clamp), lado direito, furo NPTH (43,75; -1,75). STL sem furo vertical: posicao pelo contorno da presilha desenhado no EasyEDA do EVA-RT (x 43,75..50; centro em y do furo)."),
        dict(nome="presilha_D_frente", vname="barilla_clamp", zc=0.0, sign=1.0, mirror=False, rot=0.0, t=(43.0, 11.75),
             face="TOP", fonte="stl", conf="baixa",
             obs="Presilha da vareta, lado direito, furo NPTH (43,75; 10,75). Mesma hipotese da presilha de frente."),
        dict(nome="presilha_E_tras", vname="barilla_clamp", zc=0.0, sign=1.0, mirror=True, rot=0.0, t=(-43.0, -0.75),
             face="TOP", fonte="stl", conf="baixa",
             obs="Presilha da vareta, lado esquerdo (espelho), furo NPTH (-43,75; -1,75). Hipotese como no lado direito."),
        dict(nome="presilha_E_frente", vname="barilla_clamp", zc=0.0, sign=1.0, mirror=True, rot=0.0, t=(-43.0, 11.75),
             face="TOP", fonte="stl", conf="baixa",
             obs="Presilha da vareta, lado esquerdo (espelho), furo NPTH (-43,75; 10,75). Hipotese como no lado direito."),
    ]

    areas = []
    resumo = []
    for ins in INST:
        tris, hs = part_tris(V[ins["vname"]], ins["zc"], ins["sign"], ins["mirror"], ins["rot"], ins["t"])
        cov, cont, hmin = rasterize(tris, hs)
        cont_polys = rings_fill(cont)
        band = cov & ~cont
        faixas = []
        if band.any():
            bins = np.floor(hmin)
            grupos = [band & (bins == b) for b in np.unique(bins[band])]
            alts = [(math.floor(float(np.min(hmin[m])) * 10) / 10, m) for m in grupos]
            alts.sort(key=lambda t: t[0])
            fundidas = []  # faixas com altura quase igual (<= 0,25 mm) viram uma so; altura = a menor
            for alt, m in alts:
                if fundidas and alt - fundidas[-1][0] <= 0.25:
                    fundidas[-1] = (fundidas[-1][0], fundidas[-1][1] | m)
                else:
                    fundidas.append((alt, m))
            for alt, m in fundidas:
                alt = math.floor(float(np.min(hmin[m])) * 10) / 10
                if float(np.count_nonzero(m)) * STEP * STEP < 0.2:
                    continue
                faixas.append((alt, loops_all(m), float(np.count_nonzero(m)) * STEP * STEP))
        resumo.append((ins["nome"], float(np.count_nonzero(cont)) * STEP * STEP,
                       [(a, round(ar, 1)) for a, _, ar in faixas]))
        base_obs = ins["obs"]
        areas.append(dict(nome=ins["nome"] + "_contato", face=ins["face"], tipo="contato", altura_min_mm=0.0,
                          poligonos=[pts_list(p) for p in cont_polys], fonte=ins["fonte"], confianca=ins["conf"],
                          obs=base_obs + " Contato = triangulos ate 1,0 mm da face de apoio."))
        for alt, rings, ar in faixas:
            areas.append(dict(nome=f"{ins['nome']}_sombra_{alt:.1f}mm".replace(".", "p"), face=ins["face"],
                              tipo="sombra", altura_min_mm=alt, poligonos=[pts_list(p) for p in rings],
                              fonte=ins["fonte"], confianca=("media" if ins["conf"] != "baixa" else "baixa"),
                              obs=f"Faixa de sombra da peca {ins['nome']}: altura minima do corpo nesta faixa = {alt:.1f} mm acima da placa; "
                                  f"area {ar:.0f} mm2. Anel interno = vazio (regra par-impar). Componente com altura <= {alt:.1f} mm cabe por baixo."))
    # bateria: retangulo do briefing, apoio medido no suporte (anel em z=3,0)
    altura_bateria = altura_apoio_bateria(V["battery_holder"])
    rect = [[-22.5, -42.6], [22.5, -42.6], [22.5, -22.1], [-22.5, -22.1]]  # 45 mm em x, 20,5 mm em y
    areas.append(dict(nome="bateria", face="TOP", tipo="sombra", altura_min_mm=altura_bateria,
                      poligonos=[rect], fonte="briefing", confianca="media",
                      obs="Bateria GNB 350 mAh 2S deitada: 45 mm em x (x +-22,5), 20,5 mm em y (frente em y=-22,1, passa 12,6 mm da borda y=-30), 12 mm de altura. Altura de apoio 3,0 mm medida no anel do suporte (battery_holder, topo z=3,0; a lingueta tem 2,0). Embaixo so componentes com altura <= 2,5 mm. As tiras de velcro passam pelos rasgos (x +-16,7) ao longo de y."))
    log(f"  bateria (retangulo do briefing): area={45 * 20.5:.1f} mm2; altura de apoio={altura_bateria} mm (medida no suporte)")

    # ---------------- JSON
    out = dict(unidade="mm", contorno=pts_list(cont_pts), furos=furos, areas=areas)
    with open(os.path.join(P, "geometria.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    log(f"== JSON: {len(areas)} areas, {len(furos)} furos -> {os.path.join(P, 'geometria.json')}")
    for nm, ar, fx in resumo:
        log(f"  {nm}: contato={ar:.1f} mm2; faixas (altura, area mm2)={fx}")

    # ---------------- verificacao dos furos casados
    log("== 5. Casamento dos furos (erro maximo em mm)")
    cen = [transforma_pt(h["cx"], h["cy"], rot=rot) for h in holes_stl["impeller_base_1"]]
    log(f"  carcaca (giro {deg_escolhido}): furos do STL -> {[ (round(x,2), round(y,2)) for x,y in cen]}; erro max = {hole_match(cen, carc_pl):.3f} mm")
    log(f"  succao: erro max = {hole_match([transforma_pt(h['cx'], h['cy'], t=(0,-27.5)) for h in holes_stl['suction_base'] if h['r']<1.2], carc_pl):.3f} mm (4 furos D2)")
    cen = [transforma_pt(h["cx"], h["cy"], t=(30.5, -19.027)) for h in holes_stl["gearbox"]]
    log(f"  motor direito: erro max = {hole_match(cen, gear_pl):.3f} mm (2 furos); esquerdo: espelhado")
    figura(d, areas, comps, os.path.join(P, "conf_geometria.png"))
    return d, areas, comps, rows, deg_escolhido


CORES = {"carcaca": "#4fc3f7", "ventoinha": "#ce93d8", "succao": "#ffb74d", "motor": "#81c784",
         "suporte": "#f06292", "bateria": "#fff176", "presilha": "#4db6ac"}


def cor_da_area(nome):
    for k, c in CORES.items():
        if nome.startswith(k):
            return c
    return "#ffffff"


def figura(d, areas, comps, caminho):
    """Figura de conferencia: 1:1, grade de 5 mm, areas (contato preenchido / sombra tracejada), componentes do EVA-RT."""
    from matplotlib.patches import PathPatch, FancyBboxPatch as FBP, Patch
    from matplotlib.lines import Line2D
    from matplotlib.path import Path as P_
    BG, AX, TX, GRID = "#0f1216", "#161b22", "#d0d7de", "#2b333d"
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig, ax = plt.subplots(figsize=(24, 13.2), dpi=100)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(AX)
    ax.set_aspect("equal")
    ax.set_xlim(-80, 80)
    ax.set_ylim(-48, 40)
    ax.set_xticks(np.arange(-80, 81, 5))
    ax.set_yticks(np.arange(-45, 41, 5))
    ax.tick_params(colors=TX, labelsize=8)
    ax.grid(True, color=GRID, lw=0.6)
    ax.axhline(0, color="#5c6672", lw=0.9)
    ax.axvline(0, color="#5c6672", lw=0.9)
    for s in ax.spines.values():
        s.set_color("#5c6672")
    ax.set_xlabel("x (mm): +x = direita do robo", color=TX, fontsize=11)
    ax.set_ylabel("y (mm): +y = frente do robo", color=TX, fontsize=11)
    ax.set_title("Geometria mecanica da placa base do seguidor (clone EVA-RT) - origem no centro da ventoinha",
                 color=TX, fontsize=15, pad=14)
    # contorno B
    cont = np.array(d["cont_pts"])
    ax.add_patch(MPolygon(cont, closed=True, fill=False, ec="#eceff1", lw=1.8, zorder=5))
    # furos e rasgos
    for f in d["furos"]:
        if f["tipo"] == "furo":
            ls = "--" if f["nome"] == "ventoinha" else "-"
            ax.add_patch(MCircle((f["x"], f["y"]), f["d"] / 2, fill=False, ec="#eceff1", lw=0.9, ls=ls, zorder=6))
        else:
            ax.add_patch(FBP((f["x"] - f["w"] / 2, f["y"] - f["h"] / 2), f["w"], f["h"],
                             boxstyle="round,pad=0,rounding_size=0.5", fill=False, ec="#eceff1", lw=0.9, zorder=6))
    # areas
    for a in areas:
        c = cor_da_area(a["nome"])
        if a["tipo"] == "contato":
            for ring in a["poligonos"]:
                ax.add_patch(MPolygon(np.array(ring), closed=True, fc=c, alpha=0.38, ec=c, lw=1.2, zorder=3))
        else:
            paths = [P_(np.vstack([np.array(r), np.array(r)[:1]]), closed=True) for r in a["poligonos"]]
            if paths:
                ax.add_patch(PathPatch(P_.make_compound_path(*paths), fill=False, ec=c, lw=1.1, ls=(0, (4, 2)), zorder=4))
    # componentes originais do EVA-RT
    for c in comps:
        col = "#ffffff" if c["lado"] == "TOP" else "#ff8a65"
        ax.plot(c["x"], c["y"], "o", ms=3.2, color=col, zorder=7)
        ax.text(c["x"] + 0.5, c["y"] + 0.5, c["ref"], fontsize=6.2, color=col, zorder=8)
    # legenda
    h = [Patch(fc="#9e9e9e", alpha=0.45, ec="#9e9e9e", label="contato (apoio na placa): preenchido")]
    h += [Line2D([0], [0], color="#9e9e9e", lw=1.2, ls=(0, (4, 2)), label="sombra (faixa de altura): tracejado")]
    h += [Line2D([0], [0], color="#eceff1", lw=1.8, label="contorno B (DXF)")]
    h += [Line2D([0], [0], marker="o", color="#eceff1", ls="none", mfc="none", ms=7, label="furo (NPTH / ventoinha)")]
    h += [Patch(fc="none", ec="#eceff1", label="rasgo do velcro 7 x 1 mm")]
    h += [Patch(fc=CORES[k], alpha=0.6, ec=CORES[k], label=t) for k, t in
          [("carcaca", "carcaca da ventoinha"), ("ventoinha", "rotor + hub"), ("succao", "placa de succao (embaixo)"),
           ("motor", "suporte do motor"), ("suporte", "suporte da bateria"), ("bateria", "bateria (retangulo)"),
           ("presilha", "presilha da vareta")]]
    h += [Line2D([0], [0], marker="o", color="#ffffff", ls="none", ms=5, label="componente EVA-RT (TOP)"),
          Line2D([0], [0], marker="o", color="#ff8a65", ls="none", ms=5, label="componente EVA-RT (BOT)")]
    leg = ax.legend(handles=h, loc="upper left", fontsize=9, facecolor="#1b2028", edgecolor="#5c6672",
                    labelcolor=TX, framealpha=0.95, ncol=2)
    leg.set_zorder(20)
    fig.subplots_adjust(left=0.05, right=0.985, top=0.93, bottom=0.07)
    fig.savefig(caminho, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)
    log(f"== figura: {caminho}")


if __name__ == "__main__":
    run()
