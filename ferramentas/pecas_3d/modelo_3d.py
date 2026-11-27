#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Modelo 3D completo do RUSH - SATURN v12 (GLB), para o preview em mecânica/preview_3d/.

Junta numa cena so:
- a base v12 e a barra V1 com a textura tirada do Gerber (cobre, mascara, serigrafia);
- as pecas impressas e as ferragens, nas posicoes de conferir_montagem.py;
- caixas de reducao, motores 1020, pinhoes, rodas (aro + engrenagem 64T + pneu), carcaca,
  hélice e suporte do motor da ventoinha, vareta traseira, apoios e bateria;
- os componentes das duas placas com os modelos 3D da biblioteca oficial do KiCad
  (kicad-packages3D, STEP, baixados na primeira vez para modelos_kicad/). QRE1113GR,
  botoes e XT30 nao existem la e sao desenhados aqui.

Cada componente e encaixado nos pads: o script testa os 4 giros de 90 graus e pequenos
deslocamentos e fica com o que poe os terminais do modelo dentro das aberturas da
mascara (Gerber). Assim nao depende da convencao de giro de cada biblioteca.

Referencial do robo: origem no centro da ventoinha, +x direita, +y frente, z = 0 na face
de cima da base, em mm. O GLB sai em metros, com +y para cima (padrao glTF).

STL do EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0. Modelos do KiCad: CC-BY-SA 4.0 com a
excecao de uso em projetos (https://www.kicad.org/libraries/license/).

Uso (na raiz do repositorio): python3 ferramentas/pecas_3d/modelo_3d.py
Dependencias: requisitos.txt (inclui gerbonara, cairosvg e cascadio para este script).
"""
from __future__ import annotations

import io
import json
import math
import urllib.request
import warnings
import zipfile
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import Manifold
from PIL import Image, ImageDraw

import conferir_montagem as cm
import gerar_pecas as gp

warnings.filterwarnings("ignore")

RAIZ = gp.RAIZ
SAIDA = RAIZ / "mecânica" / "preview_3d"
CACHE = Path(__file__).resolve().parent / "modelos_kicad"
GERBER_BASE = RAIZ / "hardware/placa_base/gerber/Gerber_Final_Saturn_v12_2026-11-15.zip"
URL_KICAD = "https://gitlab.com/kicad/libraries/kicad-packages3D/-/raw/master/{lib}.3dshapes/{nome}.step"
PX = 20                    # resolucao da textura das placas (px/mm)
DIST_FUROS = 63.14         # barra a 63,14 mm entre furos (L = 107,1), como no conferir_montagem

# ----------------------------------------------------------------------------
# Materiais (PBR). As cores das pecas impressas sao ilustrativas.
# ----------------------------------------------------------------------------
def _mat(nome, cor, metal=0.0, rug=0.6, alfa=1.0):
    return trimesh.visual.material.PBRMaterial(
        name=nome, baseColorFactor=[*cor, alfa], metallicFactor=metal, roughnessFactor=rug,
        alphaMode="BLEND" if alfa < 1 else "OPAQUE", doubleSided=False)


MAT = {
    "petg": _mat("PETG grafite", (0.13, 0.135, 0.15), 0.0, 0.62),
    "petg_branco": _mat("PETG branco", (0.74, 0.745, 0.74), 0.0, 0.6),
    "pla": _mat("PLA branco", (0.78, 0.78, 0.77), 0.0, 0.55),
    "resina": _mat("Resina", (0.95, 0.55, 0.12), 0.0, 0.3, 0.92),
    "carbono": _mat("Fibra de carbono", (0.035, 0.035, 0.04), 0.2, 0.3),
    "aco": _mat("Aco", (0.78, 0.78, 0.8), 1.0, 0.28),
    "aco_escuro": _mat("Aco escuro", (0.35, 0.35, 0.37), 1.0, 0.35),
    "latao": _mat("Latao", (0.86, 0.70, 0.38), 1.0, 0.3),
    "motor": _mat("Carcaca do motor", (0.82, 0.83, 0.85), 1.0, 0.22),
    "motor_tampa": _mat("Tampa do motor", (0.42, 0.43, 0.45), 0.0, 0.5),
    "pneu": _mat("Silicone", (0.06, 0.06, 0.065), 0.0, 0.85),
    "bateria": _mat("Bateria", (0.10, 0.22, 0.52), 0.0, 0.35),
    "bateria_faixa": _mat("Bateria faixa", (0.92, 0.92, 0.9), 0.0, 0.4),
    "xt30": _mat("XT30", (0.98, 0.78, 0.10), 0.0, 0.45),
    "ouro": _mat("Ouro", (1.0, 0.78, 0.34), 1.0, 0.25),
    "preto": _mat("Plastico preto", (0.03, 0.03, 0.035), 0.0, 0.45),
    "fio_vermelho": _mat("Fio vermelho", (0.75, 0.05, 0.04), 0.0, 0.45),
    "fio_preto": _mat("Fio preto", (0.04, 0.04, 0.045), 0.0, 0.45),
    "fio_azul": _mat("Fio azul", (0.05, 0.22, 0.75), 0.0, 0.45),
    "fr4": _mat("Borda FR-4", (0.62, 0.60, 0.42), 0.0, 0.7),
    "qre_lente": _mat("Lente", (0.25, 0.05, 0.05), 0.0, 0.15),
    "botao": _mat("Botao", (0.08, 0.08, 0.09), 0.0, 0.5),
}

# ----------------------------------------------------------------------------
# Textura das placas a partir do Gerber
# ----------------------------------------------------------------------------
def _raster(layer, b):
    import cairosvg
    svg = str(layer.to_svg(force_bounds=b, fg="white", bg="black"))
    (x0, y0), (x1, y1) = b
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=int(round((x1 - x0) * PX)),
                           output_height=int(round((y1 - y0) * PX)))
    return np.asarray(Image.open(io.BytesIO(png)).convert("L"), dtype=np.float32) / 255


def _furos_raster(stack, b, so_pth=True):
    (x0, y0), (x1, y1) = b
    w, h = int(round((x1 - x0) * PX)), int(round((y1 - y0) * PX))
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    for dl in stack.drill_layers:
        for o in dl.objects:
            try:
                x, y, r = o.x, o.y, o.tool.diameter / 2
            except AttributeError:
                continue
            if so_pth and r < 0.3:      # vias (tented) ficam so com o anel de cobre
                continue
            cx, cy = (x - x0) * PX, (y1 - y) * PX
            d.ellipse((cx - r * PX, cy - r * PX, cx + r * PX, cy + r * PX), fill=255)
    return np.asarray(im, dtype=np.float32) / 255


class Placa:
    """Camadas de uma placa (Gerber zipado), em coordenadas do Gerber."""

    def __init__(self, zip_gerber: Path):
        import tempfile
        from gerbonara import LayerStack
        self.tmp = tempfile.TemporaryDirectory()
        with zipfile.ZipFile(zip_gerber) as z:
            z.extractall(self.tmp.name)
            self.sonda = json.loads(z.read("FlyingProbeTesting.json"))
        st = LayerStack.open(self.tmp.name)
        self.b = st.board_bounds()
        self.cam = {}
        for lado in ("top", "bottom"):
            for uso in ("copper", "mask", "silk"):
                self.cam[lado, uso] = _raster(st[f"{lado} {uso}"], self.b)
        self.furos = _furos_raster(st, self.b)

    def componentes(self):
        """{ref: (x, y, face 1 = cima / 2 = baixo, giro)} lidos do FlyingProbeTesting.json."""
        out = {}
        for _, ref, face, x, y, ang in self.sonda["components"]["rows"]:
            if not ref.startswith("PAD"):
                out[ref] = (x * cm.MIL, y * cm.MIL, 1 if face == "T" else 2, ang)
        return out

    def textura(self, lado):
        """Cor (RGB) e metal/rugosidade (glTF: G = rugosidade, B = metal)."""
        cu, ab, sk = self.cam[lado, "copper"], self.cam[lado, "mask"], self.cam[lado, "silk"]
        cu, ab = cu[..., None], ab[..., None]
        sk = (sk * (1 - self.cam[lado, "mask"]))[..., None]       # serigrafia nao vai no pad
        furo = self.furos[..., None]
        mask_fr4 = np.array([0.035, 0.20, 0.09])       # verde JLC sobre o FR-4
        mask_cu = np.array([0.09, 0.33, 0.15])        # verde sobre o cobre (mais claro)
        hasl = np.array([0.80, 0.80, 0.78])
        fr4 = np.array([0.72, 0.64, 0.42])
        seda = np.array([0.96, 0.96, 0.94])
        c = mask_fr4 * (1 - cu) + mask_cu * cu
        c = c * (1 - ab) + (hasl * cu + fr4 * (1 - cu)) * ab
        c = c * (1 - sk) + seda * sk
        c = c * (1 - furo) + np.array([0.02, 0.02, 0.02]) * furo
        rgb = Image.fromarray((np.clip(c, 0, 1) ** (1 / 1.0) * 255).astype(np.uint8))
        metal = (cu * ab)[..., 0]
        rug = 0.42 * (1 - metal) + 0.25 * metal
        rug = rug * (1 - sk[..., 0]) + 0.8 * sk[..., 0]
        mr = np.dstack([np.zeros_like(metal), rug, metal])
        mr = Image.fromarray((mr * 255).astype(np.uint8))
        return rgb, mr

    def amostrar(self, lado, xy):
        """Abertura da mascara (0..1) nos pontos xy (coordenadas do Gerber)."""
        (x0, y0), (x1, y1) = self.b
        m = self.cam[lado, "mask"]
        i = np.round((y1 - xy[:, 1]) * PX).astype(int)
        j = np.round((xy[:, 0] - x0) * PX).astype(int)
        ok = (i >= 0) & (i < m.shape[0]) & (j >= 0) & (j < m.shape[1])
        v = np.zeros(len(xy))
        v[ok] = m[i[ok], j[ok]]
        return v


def malha_placa(solido: Manifold, placa: Placa, dy: float, esp: float, z_topo: float):
    """Separa as faces de cima, de baixo e a borda e poe UV planar (textura do Gerber)."""
    v, f = gp.malha(solido)
    t = trimesh.Trimesh(v, f, process=False)
    n = t.face_normals
    (x0, y0), (x1, y1) = placa.b
    out = []
    for nome, sel, lado in (("cima", n[:, 2] > 0.99, "top"), ("baixo", n[:, 2] < -0.99, "bottom"),
                            ("borda", np.abs(n[:, 2]) <= 0.99, None)):
        p = t.submesh([np.nonzero(sel)[0]], append=True)
        if lado is None:
            out.append((nome, suavizar(p), MAT["fr4"]))
            continue
        uv = np.column_stack([(p.vertices[:, 0] - x0) / (x1 - x0),
                              (p.vertices[:, 1] - dy - y0) / (y1 - y0)])
        cor, mr = placa.textura(lado)
        mat = trimesh.visual.material.PBRMaterial(
            name=f"PCB {lado}", baseColorTexture=cor, metallicRoughnessTexture=mr,
            metallicFactor=1.0, roughnessFactor=1.0)
        p.visual = trimesh.visual.TextureVisuals(uv=uv, material=mat)
        out.append((nome, p, None))
    return out


# ----------------------------------------------------------------------------
# Malhas
# ----------------------------------------------------------------------------
def suavizar(t: trimesh.Trimesh, ang=32):
    """Sombreamento liso nas superficies curvas e quinas vivas nas arestas."""
    t = t.copy()
    t.merge_vertices()
    return trimesh.graph.smooth_shade(t, angle=math.radians(ang))


def tm(m: Manifold) -> trimesh.Trimesh:
    v, f = gp.malha(m)
    return suavizar(trimesh.Trimesh(v, f, process=False))


def caixa(c, l, h, centro=(0, 0, 0)):
    return Manifold.cube((c, l, h), center=True).translate(centro)


def cil_eixo(eixo, p0, comp, r, n=48):
    """Cilindro de raio r e comprimento comp a partir de p0 ao longo de 'x', 'y' ou 'z'."""
    m = Manifold.cylinder(comp, r, r, n)
    if eixo == "x":
        m = m.transform([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0]])
    elif eixo == "y":
        m = m.transform([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0]])
    return m.translate(p0)


def tubo(pts, r, n_lados=12, n=60):
    """Tubo (fio) passando por uma curva suave (Catmull-Rom) pelos pontos dados."""
    p = np.asarray(pts, dtype=float)
    p = np.vstack([p[0], p, p[-1]])
    curva = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1:i + 3]
        for t in np.linspace(0, 1, n // (len(p) - 3), endpoint=False):
            t2, t3 = t * t, t * t * t
            curva.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                                + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    curva.append(p[-2])
    c = np.array(curva)
    tg = np.gradient(c, axis=0)
    tg /= np.linalg.norm(tg, axis=1, keepdims=True)
    nrm = np.cross(tg[0], [0, 0, 1] if abs(tg[0][2]) < 0.9 else [1, 0, 0])
    nrm /= np.linalg.norm(nrm)
    verts = []
    for k in range(len(c)):
        nrm = nrm - tg[k] * np.dot(nrm, tg[k])
        nrm /= np.linalg.norm(nrm)
        b = np.cross(tg[k], nrm)
        for a in np.linspace(0, 2 * np.pi, n_lados, endpoint=False):
            verts.append(c[k] + r * (np.cos(a) * nrm + np.sin(a) * b))
    verts = np.array(verts)
    faces = []
    for k in range(len(c) - 1):
        for j in range(n_lados):
            a, b2 = k * n_lados + j, k * n_lados + (j + 1) % n_lados
            faces += [[a, b2, a + n_lados], [b2, b2 + n_lados, a + n_lados]]
    t = trimesh.Trimesh(verts, faces, process=False)
    tampa0 = trimesh.creation.icosphere(1, r).apply_translation(c[0])
    tampa1 = trimesh.creation.icosphere(1, r).apply_translation(c[-1])
    t = trimesh.util.concatenate([t, tampa0, tampa1])
    t.fix_normals()
    return trimesh.graph.smooth_shade(t, angle=math.radians(60))


# ----------------------------------------------------------------------------
# Modelos de componentes
# ----------------------------------------------------------------------------
KICAD = {
    "TQFP32": ("Package_QFP", "TQFP-32_7x7mm_P0.8mm"),
    "HTSSOP16": ("Package_SO", "HTSSOP-16-1EP_4.4x5mm_P0.65mm_EP3.4x5mm"),
    "SSOP24": ("Package_SO", "SSOP-24_5.3x8.2mm_P0.65mm"),
    "TO252": ("Package_TO_SOT_SMD", "TO-252-2"),
    "SOT23": ("Package_TO_SOT_SMD", "SOT-23"),
    "CP63": ("Capacitor_SMD", "CP_Elec_6.3x7.7"),
    "C0603": ("Capacitor_SMD", "C_0603_1608Metric"),
    "C1210": ("Capacitor_SMD", "C_1210_3225Metric"),
    "R0603": ("Resistor_SMD", "R_0603_1608Metric"),
    "LED0603": ("LED_SMD", "LED_0603_1608Metric"),
    "XTAL": ("Crystal", "Crystal_SMD_5032-2Pin_5.0x3.2mm"),
    "SOD123": ("Diode_SMD", "D_SOD-123"),
    "HDR8": ("Connector_PinHeader_2.54mm", "PinHeader_1x08_P2.54mm_Vertical"),
    "SKT6": ("Connector_PinSocket_2.54mm", "PinSocket_1x06_P2.54mm_Vertical"),
}

_METAL_KEYS = ("aco", "ouro", "latao")


def _classificar(cor):
    """Material para uma cor de STEP: metal (cinza claro ou dourado) ou plastico."""
    r, g, b = cor[:3] / 255.0
    lum = 0.3 * r + 0.59 * g + 0.11 * b
    if r > 0.6 and g > 0.45 and b < 0.45 and r - b > 0.3:
        return "ouro", None
    if lum > 0.5 and max(r, g, b) - min(r, g, b) < 0.15:
        return "aco", None
    return None, _mat(f"kicad {cor[0]} {cor[1]} {cor[2]}", (r, g, b), 0.0, 0.45)


def modelo_kicad(chave):
    """[(malha em mm, material)] de um modelo STEP do KiCad (baixa e converte uma vez)."""
    import cascadio
    lib, nome = KICAD[chave]
    CACHE.mkdir(exist_ok=True)
    step, glb = CACHE / f"{nome}.step", CACHE / f"{nome}.glb"
    if not glb.exists():
        if not step.exists():
            print(f"  baixando {nome}.step")
            urllib.request.urlretrieve(URL_KICAD.format(lib=lib, nome=nome), step)
        cascadio.step_to_glb(str(step), str(glb), 0.005, 0.35)
    cena = trimesh.load(glb)
    partes = []
    for nome_no in cena.graph.nodes_geometry:
        mtx, g = cena.graph[nome_no]
        m = cena.geometry[g].copy()
        m.apply_transform(mtx)
        m.apply_scale(1000.0)        # o STEP sai em metros
        cor = np.asarray(m.visual.material.baseColorFactor)
        chave_mat, mat = _classificar(cor)
        partes.append((suavizar(trimesh.Trimesh(m.vertices, m.faces, process=False)),
                       MAT[chave_mat] if chave_mat else mat))
    return partes


def _pinos(partes, z_max=0.4):
    """Pontos xy dos terminais (partes metalicas perto da placa)."""
    pts = []
    for t, mat in partes:
        if mat.name in (MAT[k].name for k in _METAL_KEYS):
            v = t.vertices[t.vertices[:, 2] < z_max]
            pts.append(v[:, :2])
    p = np.vstack(pts) if pts else np.zeros((0, 2))
    if len(p) > 600:
        p = p[np.random.default_rng(0).choice(len(p), 600, replace=False)]
    return p


def qre1113():
    """QRE1113GR: 3,6 x 2,9 x 1,7 mm, 4 terminais nas pontas, duas lentes na face."""
    corpo = caixa(2.9, 3.6, 1.7, (0, 0, 0.85))
    lentes = [cil_eixo("z", (0, sy * 0.8, 1.68), 0.04, 0.45) for sy in (-1, 1)]
    pernas = [caixa(0.5, 0.8, 0.25, (sx * 1.3, sy * 2.0, 0.125)) for sx in (-1, 1) for sy in (-1, 1)]
    partes = [(tm(corpo), MAT["preto"]), (tm(sum(lentes[1:], lentes[0])), MAT["qre_lente"]),
              (tm(sum(pernas[1:], pernas[0])), MAT["aco"])]
    return partes


def botao():
    """Botao SMD 6,1 x 3,7 mm (KEY-SMD_L6.1-W3.7-LS8.0) com 2 terminais."""
    corpo = caixa(6.1, 3.7, 1.6, (0, 0, 0.8))
    tampa = caixa(5.4, 3.2, 0.25, (0, 0, 1.72))
    atuador = cil_eixo("z", (0, 0, 1.6), 0.9, 1.05, 32)
    pernas = [caixa(1.2, 1.0, 0.2, (sx * 3.6, 0, 0.1)) for sx in (-1, 1)]
    return [(tm(corpo), MAT["preto"]), (tm(tampa), MAT["aco"]), (tm(atuador), MAT["botao"]),
            (tm(pernas[0] + pernas[1]), MAT["aco"])]


def xt30_macho():
    """XT30 vertical (macho) com os dois pinos a 5,0 mm."""
    perfil = gp.poligono([(-2.7, -5.1), (2.7, -5.1), (2.7, 3.4), (1.0, 5.1), (-1.0, 5.1), (-2.7, 3.4)])
    corpo = perfil.extrude(8.3)
    for sy in (-2.5, 2.5):
        corpo -= cil_eixo("z", (0, sy, 2.5), 7, 1.25)
    pinos = cil_eixo("z", (0, -2.5, -1.5), 9.0, 0.5) + cil_eixo("z", (0, 2.5, -1.5), 9.0, 0.5)
    return [(tm(corpo), MAT["xt30"]), (tm(pinos), MAT["ouro"])]


def xt30_femea():
    """XT30 femea (cabo da bateria) encaixada por cima do macho."""
    perfil = gp.poligono([(-3.0, -5.4), (3.0, -5.4), (3.0, 3.6), (1.2, 5.4), (-1.2, 5.4), (-3.0, 3.6)])
    corpo = perfil.extrude(9.0).translate((0, 0, 8.3))
    return [(tm(corpo), MAT["xt30"])]


MODELO_PROC = {"QRE": (qre1113, [(sx * 1.3, sy * 2.0) for sx in (-1, 1) for sy in (-1, 1)]),
               "BOTAO": (botao, [(sx * 3.6, 0) for sx in (-1, 1)]),
               "XT30": (xt30_macho, [(0, -2.5), (0, 2.5)])}


def chave_base(ref):
    if ref in ("U1",):
        return "TO252"
    if ref == "U2":
        return "TQFP32"
    if ref in ("U3", "U4"):
        return "HTSSOP16"
    if ref == "Q1":
        return "SOT23"
    if ref in ("C1", "C2"):
        return "CP63"
    if ref == "C5":
        return "C1210"
    if ref == "X1":
        return "XTAL"
    if ref == "D1":
        return "SOD123"
    if ref == "J2":
        return "HDR8"
    if ref == "J4":
        return "SKT6"
    if ref == "J1":
        return "XT30"
    if ref.startswith("SW"):
        return "BOTAO"
    if ref.startswith("S"):
        return "QRE"
    if ref.startswith("LED"):
        return "LED0603"
    if ref.startswith("R"):
        return "R0603"
    if ref.startswith("C"):
        return "C0603"
    return None


def chave_v1(ref):
    if ref.startswith("U"):
        return "SSOP24"
    if ref.startswith("S"):
        return "QRE"
    if ref.startswith("R"):
        return "R0603"
    if ref.startswith("C"):
        return "C0603"
    return None


def _rot_z(a):
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return np.array([[c, -s], [s, c]])


def encaixar(placa: Placa, ref, x, y, face, ang, pinos):
    """Matriz 4x4 (coordenadas do Gerber, z = 0 na face do componente) que poe os
    terminais do modelo dentro das aberturas da mascara. Testa giro + k*90 e
    deslocamentos de ate 1,2 mm em volta do centro dos terminais."""
    lado = "top" if face == 1 else "bottom"
    esp = np.diag([1.0, 1.0]) if face == 1 else np.diag([-1.0, 1.0])     # baixo: espelhado em x
    p = pinos @ esp.T
    centro = (p.min(0) + p.max(0)) / 2 if len(p) else np.zeros(2)
    melhor = None
    grade = np.arange(-1.2, 1.2001, 0.1)
    for k in range(4):
        a = ang + 90 * k
        r = _rot_z(a)
        base = (p - centro) @ r.T + (x, y)
        for dx in grade:
            for dy in grade:
                s = placa.amostrar(lado, base + (dx, dy)).mean() if len(p) else 1.0
                s -= 0.002 * (k != 0) + 0.004 * math.hypot(dx, dy)
                if melhor is None or s > melhor[0]:
                    melhor = (s, a, dx, dy)
    s, a, dx, dy = melhor
    r2 = _rot_z(a)
    t = np.eye(4)
    m3 = np.eye(3)
    if face == 2:
        m3 = np.diag([-1.0, 1.0, -1.0])           # vira para a face de baixo
    rz = np.eye(3)
    rz[:2, :2] = r2
    t[:3, :3] = rz @ m3
    desl = -(r2 @ centro)
    t[:3, 3] = (x + desl[0] + dx, y + desl[1] + dy, 0.0)
    return t, s


# ----------------------------------------------------------------------------
# Cena
# ----------------------------------------------------------------------------
class Cena:
    """Cena glTF: cada peca e um no 'grupo/nome' sob o no 'robo' (mm, z para cima)."""

    def __init__(self):
        self.s = trimesh.Scene()
        raiz = np.eye(4)
        raiz[:3, :3] = [[1, 0, 0], [0, 0, 1], [0, -1, 0]]     # z do robo -> y do glTF
        raiz[:3, :3] *= 0.001                                 # mm -> m
        self.s.graph.update(frame_from=self.s.graph.base_frame, frame_to="robo", matrix=raiz)
        self.geo = {}
        self.n = 0
        self.nos = []

    def _geo(self, chave, malha, mat):
        if chave not in self.geo:
            g = malha.copy()
            if mat is not None:
                g.visual = trimesh.visual.TextureVisuals(material=mat)
            nome = f"g{len(self.geo)}"
            self.s.geometry[nome] = g
            self.geo[chave] = nome
        return self.geo[chave]

    def peca(self, no, partes, matriz=None, chave=None):
        """partes = [(malha, material)]; chave reaproveita a geometria (instancias)."""
        self.s.graph.update(frame_from="robo", frame_to=no,
                            matrix=np.eye(4) if matriz is None else matriz)
        self.nos.append(no)
        for i, (m, mat) in enumerate(partes):
            g = self._geo((chave, i) if chave else (no, i), m, mat)
            self.n += 1
            self.s.graph.update(frame_from=no, frame_to=f"{no}#{i}", geometry=g)

    def gravar(self, caminho):
        self.s.export(caminho)
        info = {no: descrever(no) for no in self.nos}
        (caminho.parent / "pecas.json").write_text(json.dumps(info, ensure_ascii=False, indent=0))


# ----------------------------------------------------------------------------
# Nome, material e deslocamento da vista explodida de cada peca (pecas.json)
# ----------------------------------------------------------------------------
def _bom():
    import csv
    out = {}
    with open(RAIZ / "hardware/placa_base/BOM_v12.csv", encoding="utf-8") as fh:
        for l in csv.DictReader(fh):
            for ref in l["Designadores"].split(","):
                out[ref.strip()] = (l["Valor"], l["Encapsulamento"] or l["Footprint"])
    return out


BOM = None
PECAS = [  # (prefixo do no, nome, material, explodida [dx, dy, dz] em mm; dx aponta para fora)
    ("pcb/", "Placa base RUSH - SATURN v12", "PCB", (0, 0, 0)),
    ("barra/pcb", "Barra de sensores V1", "PCB", (0, 30, 6)),
    ("impresso/presilha_dir_0", "Presilha da vareta (trás)", "PETG", (6, 0, 14)),
    ("impresso/presilha_esq_0", "Presilha da vareta (trás)", "PETG", (6, 0, 14)),
    ("impresso/presilha", "Presilha da vareta (frente, sobre a asa)", "PETG", (6, 0, 14)),
    ("impresso/bloco", "Bloco da vareta transversal", "PETG", (6, 0, 22)),
    ("impresso/patim", "Patim da barra V1 (esqui)", "PETG", (14, 30, 6)),
    ("impresso/placa_succao", "Placa de sucção com rebaixo", "PETG", (0, 0, -16)),
    ("impresso/apoio_bateria", "Apoio da bateria (battery_holder, EVA-RT)", "PLA", (0, -14, 30)),
    ("vareta/vareta_transversal", "Vareta transversal Ø3", "Comprado", (0, 0, 30)),
    ("vareta/vareta_traseira", "Vareta traseira Ø3 (segura o apoio da bateria)", "Comprado", (0, -14, 24)),
    ("vareta/", "Vareta longitudinal Ø3 (fibra de carbono)", "Comprado", (6, 12, 20)),
    ("ferragem/parafuso_patim", "Parafuso M2 × 8 do patim", "Comprado", (14, 30, 18)),
    ("ferragem/cabeca_patim", "Cabeça do parafuso M2 do patim", "Comprado", (14, 30, -6)),
    ("ferragem/cabeca_pe", "Parafuso M2 × 6 dos pés da carcaça", "Comprado", (0, 0, -24)),
    ("ferragem/cabeca", "Parafuso M2 (cabeça por baixo da base)", "Comprado", (0, 0, -16)),
    ("ferragem/porca", "Porca M2", "Comprado", (6, 0, 26)),
    ("ferragem/eixo_roda", "Eixo da roda: parafuso M2 × 30 com porca", "Comprado", (56, 0, 0)),
    ("ventoinha/carcaca", "Carcaça da ventoinha (impeller_base_1, EVA-RT)", "PETG", (0, 0, 46)),
    ("ventoinha/suporte_motor", "Suporte do motor da ventoinha (impeller_base_2, EVA-RT)", "PETG", (0, 0, 70)),
    ("ventoinha/helice", "Hélice centrífuga Ø34 (impeller_fan, EVA-RT)", "PETG", (0, 0, 22)),
    ("ventoinha/motor", "Motor coreless 1020 da ventoinha (M3)", "Comprado", (0, 0, 96)),
    ("tracao/caixa", "Caixa de redução (gearbox, EVA-RT)", "PETG", (10, 0, 0)),
    ("tracao/pinhao", "Pinhão 11T, módulo 0,3", "Comprado", (22, 0, 0)),
    ("tracao/motor", "Motor coreless 1020 (tração)", "Comprado", (-6, 0, 26)),
    ("tracao/buchas", "Buchas do eixo (bead, EVA-RT)", "PLA", (28, 0, 0)),
    ("tracao/engrenagem", "Engrenagem 64T m0,3 (resina, versão 2)", "Resina", (34, 0, 0)),
    ("tracao/aro", "Aro da roda (wheel_rim, EVA-RT)", "PLA", (44, 0, 0)),
    ("tracao/pneu", "Pneu StickyMAX Ø22 × 15 (RoboCore)", "Comprado", (50, 0, 0)),
    ("bateria/bateria", "Bateria LiPo 2S 350 mAh (GNB), posição ilustrativa", "Comprado", (0, -14, 44)),
    ("bateria/", "XT30 e cabo da bateria", "Comprado", (0, -14, 44)),
    ("fios/", "Fio do motor", "Comprado", (0, 0, 0)),
    ("baixo/J3", "J3 · gravação (barra de pinos deitada, 5 vias)", "Comprado", (0, 0, -10)),
]
V1 = {"S": ("QRE1113 (sensor de linha)", "QRE1113"), "U": ("74HC4067 (multiplexador de 16 canais)", "SSOP-24"),
      "R": ("Resistor", "0603"), "C": ("Capacitor 100 nF", "0603")}


def descrever(no):
    global BOM
    BOM = BOM or _bom()
    grp, nome = no.split("/", 1)
    if grp in ("cima", "baixo") and nome in BOM:
        val, enc = BOM[nome]
        return {"nome": f"{nome} · {val}", "info": enc, "material": "Componente",
                "explode": [0, 0, 8 if grp == "cima" else -10], "grupo": grp}
    if grp == "barra" and not nome.startswith("pcb"):
        t, enc = V1[nome[0]]
        return {"nome": f"{nome} · {t}", "info": f"barra V1, {enc}", "material": "Componente",
                "explode": [0, 30, 14 if nome[0] in "UR" and nome not in ("R20", "R21", "R22", "R23", "R24", "R25")
                            else -2], "grupo": "barra"}
    for pre, t, mat, ex in PECAS:
        if no.startswith(pre):
            lado = -1 if ("_esq" in no) else 1
            return {"nome": t, "info": "", "material": mat, "explode": [lado * ex[0], ex[1], ex[2]], "grupo": grp}
    return {"nome": nome, "info": "", "material": "Comprado", "explode": [0, 0, 0], "grupo": grp}


def montar_cena():
    print("Lendo placas, Gerber e montagem...")
    s, d = cm.montar(DIST_FUROS, gp.ESP_BARRA, gp.patim(gp.ESP_BARRA), gp.DESL_PATIM_V1)
    base = Placa(GERBER_BASE)
    v1 = Placa(cm.GERBER_V1)
    cena = Cena()
    y0b, ztb, eb = d["y0_barra"], d["z_topo_barra"], gp.ESP_BARRA

    # placas
    for nome, malha, mat in malha_placa(s["base"], base, 0.0, gp.ESP_BASE, 0.0):
        cena.peca(f"pcb/base_{nome}", [(malha, mat)])
    for nome, malha, mat in malha_placa(s["barra_v1"], v1, y0b, eb, ztb):
        cena.peca(f"barra/pcb_{nome}", [(malha, mat)])

    # pecas da conferencia de montagem
    def grupo(nome):
        if nome.startswith(("presilha", "bloco", "patim", "placa_succao")):
            return "impresso"
        if nome.startswith(("vareta",)):
            return "vareta"
        if nome.startswith(("parafuso", "cabeca", "porca")):
            return "ferragem"
        return None

    for nome, m in s.items():
        g = grupo(nome)
        if g is None:
            continue
        mat = {"impresso": MAT["petg"], "vareta": MAT["carbono"], "ferragem": MAT["aco"]}[g]
        if nome.startswith("parafuso_presilha"):        # so a ponta que sobra acima da porca
            continue
        cena.peca(f"{g}/{nome}", [(tm(m), mat)])

    # ventoinha: carcaca, suporte do motor, helice e motor
    car = cm.stl("impeller_base_1.stl").rotate((0, 0, cm.GIRO_CARCACA))
    cena.peca("ventoinha/carcaca", [(tm(car), MAT["petg_branco"])])
    z_sup = 12.1                                 # aba do suporte no rebaixo de O20 da carcaca
    sup = cm.stl("impeller_base_2.stl").translate((0, 0, z_sup))
    cena.peca("ventoinha/suporte_motor", [(tm(sup), MAT["petg_branco"])])
    z_helice = 11.2                              # helice com o disco em cima e as pas para a placa
    hel = cm.stl("impeller_fan.stl").transform([[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, z_helice]])
    cena.peca("ventoinha/helice", [(tm(hel), MAT["petg_branco"])])
    z_mot = z_sup + 0.4
    cena.peca("ventoinha/motor", motor_1020(np.array([0, 0, z_mot]), np.array([0, 0, 1.0]), 6.0))

    # caixas de reducao, motores, pinhoes, rodas (lado direito; o esquerdo e espelhado)
    caixa_d = cm.stl("gearbox.stl").transform([[-1, 0, 0, 40.0], [0, -1, 0, -11.258], [0, 0, 1, 2.5]])
    y_roda, z_roda = -22.5877, 7.0
    pinhao = gp.poligono(gp.perfil_engrenagem(11, 0.3, 20.0, 0.33)).extrude(2.0)
    pinhao = (pinhao - Manifold.cylinder(4, 0.55).translate((0, 0, -1))).transform(
        [[0, 0, 1, 40.75], [1, 0, 0, -11.258], [0, 1, 0, 7.64]])
    z_aba = 18.45
    aro = cm.stl("wheel_rim.stl")
    eng = gp.engrenagem_aro(2).translate((0, 0, z_aba))
    pneu = pneu_silicone()
    rot_roda = [[0, 0, -1, 40.75 + 20.5], [1, 0, 0, y_roda], [0, -1, 0, z_roda]]
    bucha = cm.stl("bead.stl")
    bucha_in = bucha.transform([[0, 0, 1, 40.0], [1, 0, 0, y_roda], [0, 1, 0, z_roda]])
    bucha_out = bucha.transform([[0, 0, -1, 40.75 + 20.5 - 2.0 + 0.6], [1, 0, 0, y_roda], [0, -1, 0, z_roda]])
    eixo = cil_eixo("x", (29.0, y_roda, z_roda), 30.0, 1.0, 24)
    cab_eixo = cil_eixo("x", (59.0 + 0.3, y_roda, z_roda), 1.6, 1.9, 32)
    porca_eixo = Manifold.cylinder(1.6, 2.0 / math.cos(math.radians(30)), 2.0 / math.cos(math.radians(30)), 6
                                   ).transform([[0, 0, -1, 30.5], [1, 0, 0, y_roda], [0, 1, 0, z_roda]])
    for lado, sx in (("dir", 1), ("esq", -1)):
        esp = (lambda m: m) if sx > 0 else (lambda m: m.mirror((1, 0, 0)))
        cena.peca(f"tracao/caixa_{lado}", [(tm(esp(caixa_d)), MAT["petg"])])
        cena.peca(f"tracao/pinhao_{lado}", [(tm(esp(pinhao)), MAT["latao"])])
        mot = motor_1020(np.array([sx * 38.0, -11.258, 7.64]), np.array([-sx * 1.0, 0, 0]), 5.0)
        cena.peca(f"tracao/motor_{lado}", mot)
        cena.peca(f"tracao/aro_{lado}", [(tm(esp(aro.transform(rot_roda))), MAT["pla"])])
        cena.peca(f"tracao/engrenagem_{lado}", [(tm(esp(eng.transform(rot_roda))), MAT["resina"])])
        cena.peca(f"tracao/pneu_{lado}", [(tm(esp(pneu.transform(rot_roda))), MAT["pneu"])])
        cena.peca(f"tracao/buchas_{lado}", [(tm(esp(bucha_in + bucha_out)), MAT["pla"])])
        cena.peca(f"ferragem/eixo_roda_{lado}", [(tm(esp(eixo + cab_eixo + porca_eixo)), MAT["aco"])])

    # vareta traseira, apoios e bateria (posicao da bateria ilustrativa: em aberto no projeto)
    y_vt, z_vt = -11.258 - 8.244, 7.842 + 2.5
    cena.peca("vareta/vareta_traseira", [(tm(cil_eixo("x", (-37.5, y_vt, z_vt), 75.0, 1.5, 32)), MAT["carbono"])])
    apoio = cm.stl("battery_holder.stl")
    for k, xa in enumerate((-14.0, 14.0)):
        m = apoio.transform([[0, 0, 1, xa - 1.5], [0, 1, 0, y_vt], [-1, 0, 0, z_vt]])
        cena.peca(f"impresso/apoio_bateria_{k}", [(tm(m), MAT["pla"])])
    zb = z_vt + 2.5
    yb0 = -22.7
    yb_c = yb0 - 10.25
    cena.peca("bateria/bateria", [(tm(bateria_arredondada(45.0, 20.5, 12.0).translate((0, yb_c, zb))), MAT["bateria"]),
                                  (tm(caixa(6.0, 20.7, 12.2, (14.0, yb_c, zb + 6.0))), MAT["bateria_faixa"])])

    # componentes das placas
    print("Componentes (modelos do KiCad + desenhados aqui)...")
    cache = {}

    def partes_de(chave):
        if chave not in cache:
            if chave in MODELO_PROC:
                f, pinos = MODELO_PROC[chave]
                cache[chave] = (f(), np.array(pinos, dtype=float))
            else:
                p = modelo_kicad(chave)
                cache[chave] = (p, _pinos(p))
        return cache[chave]

    rel = []
    comps_base = base.componentes()
    for ref, (x, y, face, ang) in sorted(comps_base.items()):
        ch = chave_base(ref)
        if ch is None:
            continue
        partes, pinos = partes_de(ch)
        t, sc = encaixar(base, ref, x, y, face, ang, pinos)
        if face == 2:
            t[2, 3] = -gp.ESP_BASE
        rel.append((ref, ch, sc))
        grp = "cima" if face == 1 else "baixo"
        cena.peca(f"{grp}/{ref}", partes, t, chave=ch)
    for ref, (x, y, face, ang) in sorted(v1.componentes().items()):
        ch = chave_v1(ref)
        if ch is None:
            continue
        partes, pinos = partes_de(ch)
        t, sc = encaixar(v1, ref, x, y, face, ang, pinos)
        t[1, 3] += y0b
        t[2, 3] += ztb if face == 1 else ztb - eb
        rel.append((f"V1:{ref}", ch, sc))
        cena.peca(f"barra/{ref}", partes, t, chave=ch)
    ruins = [r for r in rel if r[2] < 0.5]
    print(f"  {len(rel)} componentes; encaixe nos pads (fracao dos terminais sobre pad): "
          f"min {min(r[2] for r in rel):.2f}" + (f"; conferir: {ruins}" if ruins else ""))

    # J3 deitada embaixo (5 pinos curtos e o corpo preto encostado na borda de tras)
    j3 = comps_base["J3"]
    zp = -gp.ESP_BASE - cm.J3_PINO / 2
    pinos = None
    for i in range(5):
        xp = j3[0] + (i - 2) * 2.54
        p = caixa(cm.J3_PINO, 11.0, cm.J3_PINO, (xp, j3[1] - 5.0, zp))
        pinos = p if pinos is None else pinos + p
    corpo = caixa(5 * 2.54, 2.54, 2.54, (j3[0], cm.J3_BORDA - 1.27, zp))
    cena.peca("baixo/J3", [(tm(corpo), MAT["preto"]), (tm(pinos), MAT["ouro"])])

    # XT30 femea da bateria encaixada na J1 e os fios
    j1 = comps_base["J1"]
    fem = xt30_femea()
    t = np.eye(4)
    t[:2, :2] = _rot_z(j1[3])
    t[:2, 3] = j1[:2]
    cena.peca("bateria/xt30_femea", fem, t)
    for k, (dy, mat) in enumerate(((-2.5, "fio_vermelho"), (2.5, "fio_preto"))):
        p0 = np.array([j1[0] + dy * 0, j1[1] + dy, 17.3])
        pts = [p0, p0 + (0, 0, 3), (-24.0, yb_c + 3 * np.sign(dy), zb + 6 + 0.5 * dy), (-22.0, yb_c + 2.2 * np.sign(dy), zb + 6)]
        cena.peca(f"bateria/fio_{k}", [(tubo(pts, 0.55), MAT[mat])])

    # fios dos motores (das tampas ate os pads M1, M2 e M3)
    pads = pads_motor(base)
    for lado, sx, ref in (("dir", 1, "M2"), ("esq", -1, "M1")):
        a, b = pads[ref]
        for k, (pad, mat) in enumerate(((a, "fio_vermelho"), (b, "fio_azul"))):
            ini = np.array([sx * 17.6, -11.258 + (1.6 if k == 0 else -1.6), 7.64 + 1.5])
            pts = [ini, ini + (-sx * 1.2, 0, 2.5), (sx * 22.0, pad[1] - 6, 9.0), (pad[0], pad[1], 3.5),
                   (pad[0], pad[1], 0.2)]
            cena.peca(f"fios/{ref}_{k}", [(tubo(pts, 0.32), MAT[mat])])
    a, b = pads["M3"]
    for k, (pad, mat) in enumerate(((a, "fio_vermelho"), (b, "fio_azul"))):
        ini = np.array([(1.6 if k == 0 else -1.6), 0.0, z_mot + 20.5])
        pts = [ini, ini + (0, 0, 2.5), (8.0, -1.0, z_mot + 22.0), (pad[0] - 3, pad[1], 14.0),
               (pad[0], pad[1], 3.5), (pad[0], pad[1], 0.2)]
        cena.peca(f"fios/M3_{k}", [(tubo(pts, 0.32), MAT[mat])])

    return cena, s, d


def pads_motor(placa: Placa):
    """Centros dos dois furos de cada pad de motor (M1, M2, M3), lidos da furacao."""
    comps = placa.componentes()
    out = {}
    with zipfile.ZipFile(GERBER_BASE) as z:
        texto = z.read("Drill_PTH_Through.DRL").decode()
    import re
    furos = [(float(m.group(1)), float(m.group(2))) for m in re.finditer(r"X(-?[\d.]+)Y(-?[\d.]+)", texto)]
    furos = np.array(furos)
    for ref in ("M1", "M2", "M3"):
        x, y = comps[ref][:2]
        dd = np.hypot(furos[:, 0] - x, furos[:, 1] - y)
        sel = furos[np.argsort(dd)[:2]]
        out[ref] = sorted(map(tuple, sel), key=lambda p: (p[1], p[0]))
    return out


def pneu_silicone(r_in=6.5, r_out=11.0, z0=2.0, z1=17.0, raio_borda=1.6):
    """Pneu StickyMAX (O22 x 15) sobre o aro, com as bordas arredondadas."""
    pts = [(r_in, z0)] + [(r_out - raio_borda + raio_borda * math.sin(a), z0 + raio_borda - raio_borda * math.cos(a))
                          for a in np.linspace(0, np.pi / 2, 10)]
    pts += [(r_out - raio_borda + raio_borda * math.cos(a), z1 - raio_borda + raio_borda * math.sin(a))
            for a in np.linspace(0, np.pi / 2, 10)]
    pts += [(r_in, z1)]
    from manifold3d import CrossSection
    return CrossSection([np.array(pts)]).revolve(96)


def bateria_arredondada(c, l, h, r=1.5):
    """Bateria LiPo (caixa com cantos arredondados), apoiada em z = 0, centrada em x e y."""
    pts = []
    for cx, cy, a0 in ((c / 2 - r, l / 2 - r, 0), (-c / 2 + r, l / 2 - r, 90), (-c / 2 + r, -l / 2 + r, 180),
                       (c / 2 - r, -l / 2 + r, 270)):
        pts += [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
                for a in np.linspace(a0, a0 + 90, 6)]
    return gp.poligono(pts).extrude(h)


def motor_1020(frente, direcao, comp_eixo):
    """Motor coreless 1020 (O10 x 20): 'frente' = centro da face do eixo; 'direcao' aponta
    da frente para a traseira. O eixo (O1) sai da frente por comp_eixo mm."""
    d = np.asarray(direcao, dtype=float)
    d /= np.linalg.norm(d)
    # base local: z ao longo do motor (da frente para tras)
    aux = np.array([0, 0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0, 0])
    ex = np.cross(aux, d)
    ex /= np.linalg.norm(ex)
    ey = np.cross(d, ex)
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = ex, ey, d, frente
    lata = Manifold.cylinder(18.5, 5.0, 5.0, 64).translate((0, 0, 0))
    lata -= Manifold.cylinder(0.6, 4.2, 4.2, 48).translate((0, 0, -0.1))
    boss = Manifold.cylinder(0.6, 2.4, 2.4, 32).translate((0, 0, -0.5))
    tampa = Manifold.cylinder(1.5, 5.0, 5.0, 64).translate((0, 0, 18.5))
    term = caixa(0.8, 0.3, 1.2, (1.6, 0, 20.4)) + caixa(0.8, 0.3, 1.2, (-1.6, 0, 20.4))
    eixo = Manifold.cylinder(comp_eixo, 0.5, 0.5, 16).translate((0, 0, -comp_eixo))
    pecas = [(lata + boss, MAT["motor"]), (tampa, MAT["motor_tampa"]), (term, MAT["latao"]), (eixo, MAT["aco"])]
    out = []
    for p, mat in pecas:
        out.append((tm(p.transform(m[:3].tolist())), mat))
    return out


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    cena, s, d = montar_cena()
    arq = SAIDA / "rush_saturn_v12.glb"
    cena.gravar(arq)
    print(f"GLB: {arq.relative_to(RAIZ)} ({arq.stat().st_size / 1e6:.1f} MB, {cena.n} malhas)")


if __name__ == "__main__":
    main()
