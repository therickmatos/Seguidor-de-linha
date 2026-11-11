"""Contorno "asa de gaivota" da placa base, derivado da v3 (RUSH/SATURN).

Baseado no EVA-RT, (c) EXOTIC TEAM MX, AGPL-3.0 (github.com/EXOTIC-TEAM-MX/EVA-RT).
Unidades em mm; origem no centro da ventoinha, +y para a frente (referencial do .epro).

O que muda em relação à v3: só as abas laterais. O corpo (|x| <= 50), a frente
(nariz e degraus), a traseira e os 15 recortes (furo Ø17, 12 furos de fixação e
2 rasgos) ficam idênticos.

Aba: nasce no canto dianteiro do corpo, sobe em ângulo suave e termina numa
ponta horizontal, como a da v3 (centro do QRE a 4,6 mm da ponta, cantos r 1,45).
Largura 6,1 mm na parte externa (igual à v3), alargando até 8 mm na raiz.

Uso:  python3 contorno.py   → gera ../saida/*.dxf, *.png e contorno.json
"""
from pathlib import Path
import json
import math

import numpy as np
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

import geometria_v3

OUT = Path(__file__).resolve().parent.parent / 'saida'

# --- Parâmetros (lado direito; o esquerdo é espelhado) -------------------------
SENSOR_IN = (50.5, 14.0)     # E1/D1: sensor interno
SENSOR_OUT = (82.0, 20.0)    # E2/D2: sensor externo
W_TIP = 6.1                  # largura da aba na parte externa (v3 = 6,1)
W_ROOT = 8.0                 # largura na raiz
TIP = 4.6                    # centro do QRE externo até a ponta (v3 = 4,6)
TIP_R = 1.45                 # raio dos cantos da ponta (v3 = 1,45)
ROOT = (44.0, 7.0)           # início da linha de centro (dentro do corpo)
KNEE = (52.0, 14.6)          # joelho: a raiz sobe mais inclinada até aqui
KNEE_R = 14.0                # raio do joelho
BEND_X = 70.0                # onde a subida termina e a ponta horizontal começa
BEND_R = 30.0                # raio da curva da linha de centro (suaviza a dobra)
ROOT_R = 4.0                 # raio dos cantos côncavos entre aba e corpo
QRE = (2.7, 3.4)             # corpo do QRE1113GR no footprint da v3 (x × y, rotação 180°)
X_MIN_TOP = 45.0             # o arredondamento da raiz não entra em |x| < 45 (corpo da v3 intacto)


def _fillet_polyline(pts, radius, n=48):
    """Polilinha com cantos arredondados (arco tangente de raio `radius`)."""
    pts = [np.asarray(p, float) for p in pts]
    out = [pts[0]]
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        u = (a - b) / np.linalg.norm(a - b)
        v = (c - b) / np.linalg.norm(c - b)
        ang = math.acos(np.clip(u @ v, -1, 1))
        t = radius / math.tan(ang / 2)
        t = min(t, 0.45 * np.linalg.norm(a - b), 0.45 * np.linalg.norm(c - b))
        r = t * math.tan(ang / 2)
        p1, p2 = b + u * t, b + v * t
        bis = (u + v) / np.linalg.norm(u + v)
        centre = b + bis * (r / math.sin(ang / 2))
        a1 = math.atan2(*(p1 - centre)[::-1])
        a2 = math.atan2(*(p2 - centre)[::-1])
        d = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        for k in range(n + 1):
            th = a1 + d * k / n
            out.append(centre + r * np.array([math.cos(th), math.sin(th)]))
    out.append(pts[-1])
    return np.array(out)


def centerline():
    """Linha de centro da aba direita: raiz dentro do corpo → joelho (sobe mais) → subida suave → ponta horizontal."""
    x_out, y_out = SENSOR_OUT
    tip = (x_out + TIP, y_out)
    c = np.vstack((_fillet_polyline([ROOT, KNEE, (BEND_X, y_out)], KNEE_R)[:-1],
                   _fillet_polyline([KNEE, (BEND_X, y_out), tip], BEND_R)[1:]))
    # junta as duas metades no ponto de tangência comum (trecho reto entre as curvas)
    keep = np.r_[True, np.hypot(*np.diff(c, axis=0).T) > 1e-9]
    c = c[keep]
    order = np.r_[True, np.diff(c[:, 0]) > 0]
    return c[order]


def arm_polygon():
    c = centerline()
    seg = np.diff(c, axis=0)
    s = np.r_[0, np.cumsum(np.hypot(*seg.T))]
    tang = np.gradient(c, axis=0)
    tang /= np.linalg.norm(tang, axis=1)[:, None]
    normal = np.column_stack((-tang[:, 1], tang[:, 0]))
    # largura: W_ROOT até o sensor interno, afunila até W_TIP no início da ponta horizontal
    s_in = s[np.argmin(np.linalg.norm(c - SENSOR_IN, axis=1))]
    s_bend = s[np.argmin(np.abs(c[:, 0] - BEND_X))]
    frac = np.clip((s - s_in) / (s_bend - s_in), 0, 1)
    frac = 0.5 - 0.5 * np.cos(math.pi * frac)          # transição suave
    half = (W_ROOT + (W_TIP - W_ROOT) * frac) / 2
    left = c + normal * half[:, None]
    right = c - normal * half[:, None]
    poly = Polygon(np.vstack((left, right[::-1])))
    poly = poly.buffer(0)
    # cantos da ponta com r = TIP_R (abertura morfológica só na região da ponta)
    tipzone = box(SENSOR_OUT[0], -50, 200, 100)
    rounded = poly.buffer(-TIP_R, join_style='round').buffer(TIP_R, join_style='round', quad_segs=16)
    return unary_union([poly.difference(tipzone), rounded.intersection(tipzone)]).buffer(0)


def build():
    v3, cuts = geometria_v3.load()
    core = v3.intersection(box(-50, -100, 50, 100))          # corpo da v3 sem as abas
    arm_r = arm_polygon()
    arm_l = affinity.scale(arm_r, xfact=-1, yfact=1, origin=(0, 0))
    raw = unary_union([core, arm_r, arm_l])
    # cantos côncavos entre aba e corpo: fechamento morfológico só perto da raiz
    closed = raw.buffer(ROOT_R, quad_segs=24).buffer(-ROOT_R, quad_segs=24)
    roots = []
    for sx in (1, -1):
        lo, hi = sorted((sx * X_MIN_TOP, sx * 62.0))
        zone = box(lo, 0.0, hi, 30.0)
        roots.append(closed.difference(raw).intersection(zone))
    outer = unary_union([raw] + roots).buffer(0.001).buffer(-0.001)
    outer = Polygon(outer.exterior).simplify(0.0005)
    board = outer.difference(unary_union(cuts))

    # --- conferências -------------------------------------------------------
    assert outer.is_valid and outer.geom_type == 'Polygon'
    assert board.is_valid and board.geom_type == 'Polygon' and len(board.interiors) == 15
    assert all(outer.covers(c) for c in cuts), 'algum recorte da v3 ficou fora da placa'
    keep = box(-45, -100, 45, 100).union(box(-200, -100, 200, 0.0))
    assert outer.symmetric_difference(v3).intersection(keep).area < 1e-2, 'corpo/traseira da v3 alterados'
    sensors = [(sx * x, y) for sx in (1, -1) for x, y in (SENSOR_IN, SENSOR_OUT)]
    edge = {f'{p}': outer.exterior.distance(Point(p)) for p in sensors}
    assert all(outer.contains(Point(p)) for p in sensors)
    assert min(edge.values()) >= 2.5, f'sensor perto demais da borda: {edge}'
    assert outer.bounds[3] <= v3.bounds[3] + 1e-6, 'aba passa da frente do nariz'
    return v3, outer, board, cuts, sensors, edge


def write_dxf(path, outer, cuts=None, extras=None):
    import ezdxf
    doc = ezdxf.new('R2000')
    doc.units = ezdxf.units.MM
    msp = doc.modelspace()
    for name, color in (('BOARD_OUTLINE', 7), ('FUROS_V3', 3), ('SENSORES_REF', 1), ('V3_REF', 8)):
        doc.layers.add(name, color=color)
    msp.add_lwpolyline([tuple(p) for p in np.asarray(outer.exterior.coords)[:-1]], close=True,
                       dxfattribs={'layer': 'BOARD_OUTLINE'})
    msp.add_circle((0, 0), 8.5, dxfattribs={'layer': 'BOARD_OUTLINE'})   # furo da ventoinha Ø17
    if cuts:
        for c in cuts:
            if c.area > 200:          # o Ø17 já está no contorno
                continue
            msp.add_lwpolyline([tuple(p) for p in np.asarray(c.exterior.coords)[:-1]], close=True,
                               dxfattribs={'layer': 'FUROS_V3'})
    for e in extras or []:
        e(msp)
    doc.saveas(path)


def figure(path, v3, outer, board, cuts, sensors, low=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as Patch

    fig, ax = plt.subplots(figsize=(13, 5.2), dpi=150)
    if low is not None:
        ax.plot(*np.asarray(low.exterior.coords).T, color='#c9a227', lw=1, ls=':', label='esboço atual (chassi baixo)')
    ax.add_patch(Patch(np.asarray(board.exterior.coords), closed=True, fc='#24303a', ec='#24303a'))
    for hole in board.interiors:
        ax.add_patch(Patch(np.asarray(hole.coords), closed=True, fc='white', ec='#24303a', lw=0.6))
    ax.plot(*np.asarray(v3.exterior.coords).T, color='#4aa3df', lw=1, ls='--', label='v3 atual')
    for i, (x, y) in enumerate(sensors):
        name = ('D' if x > 0 else 'E') + ('1' if abs(x) < 60 else '2')
        ax.add_patch(plt.Rectangle((x - QRE[0] / 2, y - QRE[1] / 2), *QRE, fc='#f2c14e', ec='black', lw=0.5, zorder=5))
        dy = 12 if abs(x) < 60 else -24
        ax.annotate(f'{name}\n({x:+.1f}; {y:.1f})', (x, y), xytext=(0, dy), textcoords='offset points',
                    ha='center', fontsize=7.5, color='#b03a2e', zorder=6)
    ax.plot(0, -22.59, 'k+', ms=8)
    ax.annotate('eixo das rodas (y = −22,6)', (0, -22.59), xytext=(6, -10), textcoords='offset points', fontsize=7)
    xmin, ymin, xmax, ymax = outer.bounds
    ax.annotate('', (xmin, ymin - 6), (xmax, ymin - 6), arrowprops=dict(arrowstyle='<->', lw=0.7))
    ax.text(0, ymin - 9.5, f'{xmax - xmin:.1f} mm', ha='center', fontsize=8)
    ax.set_aspect('equal')
    ax.set_xlim(xmin - 6, xmax + 6)
    ax.set_ylim(ymin - 13, ymax + 8)
    ax.grid(True, lw=0.3, alpha=0.5)
    ax.set_xlabel('x (mm)')
    ax.set_ylabel('y (mm) — frente para cima')
    ax.legend(loc='center left', fontsize=8, frameon=False)
    ax.set_title('Placa base "asa de gaivota" (contorno derivado da v3; baseado no EVA-RT, AGPL-3.0)', fontsize=10)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def low_chassis():
    """Contorno do esboço anterior (chassi baixo, 06_estudo_consolidado), para comparação."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / '06_estudo_consolidado' / 'codigo'))
    from chassi_dois_sensores import build_geometry
    return Polygon(build_geometry()['outline'])


def main():
    v3, outer, board, cuts, sensors, edge = build()
    OUT.mkdir(parents=True, exist_ok=True)

    write_dxf(OUT / 'asa_gaivota_contorno.dxf', outer)

    def sensor_marks(msp):
        for x, y in sensors:
            msp.add_circle((x, y), 0.5, dxfattribs={'layer': 'SENSORES_REF'})
            hx, hy = QRE[0] / 2, QRE[1] / 2
            msp.add_lwpolyline([(x - hx, y - hy), (x + hx, y - hy), (x + hx, y + hy), (x - hx, y + hy)],
                               close=True, dxfattribs={'layer': 'SENSORES_REF'})
        msp.add_lwpolyline([tuple(p) for p in np.asarray(v3.exterior.coords)[:-1]], close=True,
                           dxfattribs={'layer': 'V3_REF'})
    write_dxf(OUT / 'asa_gaivota_referencia.dxf', outer, cuts, [sensor_marks])

    try:
        low = low_chassis()
    except Exception:          # o esboço anterior é só comparação
        low = None
    figure(OUT / 'asa_gaivota.png', v3, outer, board, cuts, sensors, low)

    xmin, ymin, xmax, ymax = outer.bounds
    info = dict(
        nome='Placa base asa de gaivota (derivada da v3)',
        creditos='Baseado no EVA-RT, (c) EXOTIC TEAM MX, AGPL-3.0',
        referencial='mm; origem no centro da ventoinha; +y para a frente (o mesmo do .epro da v3)',
        sensores={'E1': [-SENSOR_IN[0], SENSOR_IN[1]], 'D1': list(SENSOR_IN),
                  'E2': [-SENSOR_OUT[0], SENSOR_OUT[1]], 'D2': list(SENSOR_OUT)},
        distancia_sensor_borda_min_mm=round(min(edge.values()), 2),
        largura_mm=round(xmax - xmin, 2), comprimento_mm=round(ymax - ymin, 2),
        frente_aba_y_mm=round(max(y for x, y in outer.exterior.coords if abs(x) > 50), 2),
        nariz_y_mm=round(ymax, 2),
        largura_aba_ponta_mm=W_TIP, largura_aba_raiz_mm=W_ROOT,
        angulo_subida_graus=round(math.degrees(math.atan2(SENSOR_OUT[1] - SENSOR_IN[1], BEND_X - SENSOR_IN[0])), 1),
        area_placa_mm2=round(board.area, 1), area_v3_mm2=round(v3.difference(unary_union(cuts)).area, 1),
        recortes_v3_preservados=len(board.interiors),
        outline=[[round(x, 4), round(y, 4)] for x, y in outer.exterior.coords],
        cutouts=[[[round(x, 4), round(y, 4)] for x, y in c.exterior.coords] for c in cuts],
    )
    (OUT / 'contorno.json').write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding='utf8', newline='\n')
    print({k: v for k, v in info.items() if k not in ('outline', 'cutouts')})


if __name__ == '__main__':
    main()
