"""Geometria auxiliar do preview (sem shapely): poligonos convexos, SAT, contorno, areas."""
import os
import json, math
import numpy as np
import footprints as F

P = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(P + "/geometria.json"))
CONTORNO = np.array(G["contorno"], dtype=float)

MARGEM = 0.25  # cortesia
SO_PADS = {"M1", "M2", "M3"}  # coordenador: motores so com pads nas checagens e no desenho

def rot_pts(pts, rot):
    t = math.radians(rot)
    c, s = round(math.cos(t), 12), round(math.sin(t), 12)
    pts = np.asarray(pts, dtype=float)
    return np.stack([pts[:, 0] * c - pts[:, 1] * s, pts[:, 0] * s + pts[:, 1] * c], axis=1)

def _to_board(pts, _unused, x, y, rot, lado):
    """pontos locais (footprint, TOP) -> pontos da placa, com espelho em x se BOTTOM."""
    pts = np.asarray(pts, dtype=float).copy()
    if lado == "BOTTOM":
        pts[:, 0] = -pts[:, 0]
    pts = rot_pts(pts, rot)
    pts[:, 0] += x
    pts[:, 1] += y
    return pts

def pad_quads(ref, x, y, rot, lado=None):
    """Lista de (pino, rede_str, quad 4x2 ou circulo (cx,cy,r)) para cada pad."""
    lado = F._lado_efetivo(ref, lado)
    fp = F.FOOTPRINTS[F.REF_FOOTPRINT[ref]]
    out = []
    for p in fp["pads"]:
        if p["forma"] in ("round", "oval") and p["w"] == p["h"]:
            cx, cy = _to_board([[p["x"], p["y"]]], None, x, y, rot, lado)[0]
            out.append((p["pino"], p["rede_pino"], ("circ", cx, cy, p["w"] / 2.0), p))
            continue
        hw, hh = p["w"] / 2.0, p["h"] / 2.0
        loc = [[p["x"] - hw, p["y"] - hh], [p["x"] + hw, p["y"] - hh],
               [p["x"] + hw, p["y"] + hh], [p["x"] - hw, p["y"] + hh]]
        q = _to_board(loc, None, x, y, rot, lado)
        out.append((p["pino"], p["rede_pino"], q, p))
    return out

def corpo_quad(ref, x, y, rot, lado=None, chave="corpo"):
    lado = F._lado_efetivo(ref, lado)
    fp = F.FOOTPRINTS[F.REF_FOOTPRINT[ref]]
    w, h = fp[chave]
    if w <= 0 or h <= 0:
        return None
    cxy = fp["corpo_xy"] if chave == "corpo" else fp["cortesia_xy"]
    loc = [[cxy[0] - w / 2, cxy[1] - h / 2], [cxy[0] + w / 2, cxy[1] - h / 2],
           [cxy[0] + w / 2, cxy[1] + h / 2], [cxy[0] - w / 2, cxy[1] + h / 2]]
    return _to_board(loc, None, x, y, rot, lado)

def convex_hull(pts):
    pts = sorted(set(map(tuple, np.round(np.asarray(pts, float), 9))))
    if len(pts) <= 2:
        return np.array(pts)
    def cross(o, a, b):
        return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    return np.array(lo[:-1] + up[:-1])

def courtyard(ref, x, y, rot, lado=None):
    """Cortesia convexa: pads (+ corpo, se houver) + MARGEM. Motores: so pads (coordenador)."""
    pts = []
    for pino, rede, q, p in pad_quads(ref, x, y, rot, lado):
        if isinstance(q, tuple):  # circulo: 4 pontos do quadrado circunscrito
            _, cx, cy, r = q
            pts += [[cx - r, cy - r], [cx + r, cy - r], [cx + r, cy + r], [cx - r, cy + r]]
        else:
            pts += list(q)
    if ref not in SO_PADS:
        cq = corpo_quad(ref, x, y, rot, lado, "corpo")
        if cq is not None:
            pts += list(cq)
    hull = convex_hull(pts)
    # margem de 0,25 mm em cada lado: soma de Minkowski com quadrado (+-MARGEM em x e y)
    ex = [(v[0] + dx, v[1] + dy) for v in hull for dx in (-MARGEM, MARGEM) for dy in (-MARGEM, MARGEM)]
    return convex_hull(ex)

def sat_overlap(A, B, tol=1e-9):
    """True se os convexos A e B se sobrepoem (area > 0, tolerancia tol)."""
    for poly in (A, B):
        n = len(poly)
        for i in range(n):
            e = poly[(i + 1) % n] - poly[i]
            axis = np.array([-e[1], e[0]])
            L = math.hypot(*axis)
            if L == 0: continue
            axis = axis / L
            pa = A @ axis; pb = B @ axis
            if pa.max() <= pb.min() + tol or pb.max() <= pa.min() + tol:
                return False
    return True

def sat_gap(A, B):
    """Distancia minima entre convexos (0 se sobrepostos) via separacao por eixos + vertices."""
    best = None
    def seg_dist(p, a, b):
        ab = b - a; t = np.clip(np.dot(p - a, ab) / max(np.dot(ab, ab), 1e-12), 0, 1)
        return np.linalg.norm(p - (a + t * ab))
    if sat_overlap(A, B):
        return 0.0
    d = min(min(seg_dist(p, B[i], B[(i+1) % len(B)]) for i in range(len(B))) for p in A)
    d2 = min(min(seg_dist(p, A[i], A[(i+1) % len(A)]) for i in range(len(A))) for p in B)
    return min(d, d2)

def point_in_poly(pt, poly):
    x, y = pt; inside = False; n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xi: inside = not inside
    return inside

def seg_point_dist(p, a, b):
    ab = b - a; t = max(0.0, min(1.0, float(np.dot(p - a, ab) / max(np.dot(ab, ab), 1e-12))))
    return float(np.linalg.norm(p - (a + t * ab)))

def dist_to_boundary(pt, poly):
    return min(seg_point_dist(np.asarray(pt), np.asarray(poly[i]), np.asarray(poly[(i+1) % len(poly)])) for i in range(len(poly)))

def quad_inside_contorno(quad, min_gap):
    """Quad (4 pontos) dentro do contorno com folga >= min_gap. Retorna (ok, folga_min)."""
    folga = 1e9
    quad = np.asarray(quad, float)
    for v in quad:
        if not point_in_poly(v, CONTORNO):
            return False, -dist_to_boundary(v, CONTORNO)
        folga = min(folga, dist_to_boundary(v, CONTORNO))
    # vertices dentro e distancia de cada aresta do contorno aos vertices do quad (aprox. suficiente para retangulos pequenos)
    for i in range(len(quad)):
        a = np.asarray(quad[i], float); b = np.asarray(quad[(i + 1) % len(quad)], float)
        for k in range(0, 11):
            pt = a + (b - a) * k / 10.0
            folga = min(folga, dist_to_boundary(pt, CONTORNO))
    return folga >= min_gap - 1e-9, folga

def area_contains(area, pt):
    """Ponto dentro de uma area (regra par-impar sobre todos os poligonos da area)."""
    n = 0
    for poly in area["poligonos"]:
        if point_in_poly(pt, np.array(poly, dtype=float)):
            n += 1
    return n % 2 == 1

def areas(face=None, tipo=None):
    for a in G["areas"]:
        if (face is None or a["face"] == face) and (tipo is None or a["tipo"] == tipo):
            yield a

def area_overlap_pts(area, poly_pts, step=0.1):
    """Amostra o interior do poligono (convexo) em grade e conta amostras dentro da area (par-impar)."""
    poly_pts = np.asarray(poly_pts, float)
    xs = poly_pts[:, 0]; ys = poly_pts[:, 1]
    cnt = 0
    for gx in np.arange(xs.min(), xs.max() + 1e-9, step):
        for gy in np.arange(ys.min(), ys.max() + 1e-9, step):
            if point_in_poly((gx, gy), poly_pts) and area_contains(area, (gx, gy)):
                cnt += 1
    return cnt

def hole_gap(quad_or_circ, hole):
    """Distancia (borda do cobre -> borda do furo). hole: dict com x,y,d (ou w,h para rasgo)."""
    if hole["tipo"] == "furo":
        hx, hy, r = hole["x"], hole["y"], hole["d"] / 2.0
        if isinstance(quad_or_circ, tuple):
            _, cx, cy, rr = quad_or_circ
            return math.hypot(cx - hx, cy - hy) - rr - r
        q = np.asarray(quad_or_circ)
        dmin = min(seg_point_dist(np.array([hx, hy]), q[i], q[(i+1) % len(q)]) for i in range(len(q)))
        inside = point_in_poly((hx, hy), q)
        return (-dmin if inside else dmin) - r
    else:  # rasgo retangular w x h (w no eixo x)
        hx, hy, w, h = hole["x"], hole["y"], hole["w"], hole["h"]
        rect = np.array([[hx - w/2, hy - h/2], [hx + w/2, hy - h/2], [hx + w/2, hy + h/2], [hx - w/2, hy + h/2]])
        if isinstance(quad_or_circ, tuple):
            _, cx, cy, rr = quad_or_circ
            q = np.array([[cx - rr, cy - rr], [cx + rr, cy - rr], [cx + rr, cy + rr], [cx - rr, cy + rr]])
        else:
            q = np.asarray(quad_or_circ)
        if sat_overlap(q, rect): return -1.0
        return sat_gap(q, rect)

HOLES = G["furos"]

# Apenas uma alternativa pendente: nunca deslocar silenciosamente os furos reais.
# As rotinas que ilustrarem esta alternativa devem fazer uma copia explicita de HOLES.
PROPOSTA_VELCRO_DX = 2.2
