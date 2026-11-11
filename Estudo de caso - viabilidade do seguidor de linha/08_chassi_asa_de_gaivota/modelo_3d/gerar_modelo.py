"""Modelo 3D simplificado do robô v4 (asa de gaivota) com a barra V1 e as varetas.

Baseado no EVA-RT, (c) EXOTIC TEAM MX, AGPL-3.0. Blocos e cilindros nas medidas
do projeto: placa e componentes lidos do .epro da v4, barra V1 do Gerber, e
volumes das peças impressas com as dimensões dos STL do EVA-RT (posição
aproximada). Não serve para conferir interferências finas.

Saídas: robo_v4.glb (cores) e robo_v4.stl (uma malha só).
Referencial: mm, origem no centro da ventoinha, x para a direita, y para a frente, z para cima (chão em z = 0).
"""
from pathlib import Path
import json, math, sys, zipfile, collections
import numpy as np
import trimesh
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'codigo'))
sys.path.insert(0, str(HERE.parent / 'codigo' / 'v4_epro'))
import contorno as C
import check
REPO = HERE.parents[2]
EPRO = REPO / 'ProPrj_RUSH - SATURN - v4_asa_gaivota_2026-11-11.epro'
M = 0.0254

# --- alturas (mm) -----------------------------------------------------------
AXLE_Y = -22.587743818986525
TIRE_R = 11.5                    # pneu ~Ø23 (aro Ø16,5 do STL + borracha)
AXLE_Z = TIRE_R
PCB_T = 1.6
PCB_TOP = AXLE_Z - 7.0           # eixo 7 mm acima do topo da placa (STL do EVA-RT)
PCB_BOT = PCB_TOP - PCB_T        # 2,9 mm do chão → QRE (1,7 mm) a ~1,2 mm do chão
HOLES = 63.141                   # furo da frente da base → furo da barra V1
L = 10.75 + math.sqrt(HOLES ** 2 - (44.62624 - 43.75) ** 2) + 3.68496 + 6.9577325 - AXLE_Y
BAR_DY = L + AXLE_Y - 6.9577325  # translação da barra (referencial local do Gerber → robô)

COL = dict(pcb=(28, 30, 33), pcb_edge=(60, 64, 70), comp=(52, 56, 62), ic=(24, 24, 26), qre=(20, 20, 22),
           qre_lens=(150, 40, 40), led=(60, 200, 90), res=(40, 40, 44), cap=(170, 140, 90), elco=(40, 60, 140),
           conn=(235, 235, 230), xt30=(230, 200, 40), tire=(35, 35, 35), rim=(235, 235, 235),
           print=(225, 110, 40), print2=(200, 200, 205), motor=(180, 185, 190), rod=(25, 25, 25),
           battery=(40, 90, 170), metal=(170, 170, 175))

parts = []   # (nome, malha, cor)
def add(name, mesh, col):
    parts.append((name, mesh, col))
def box(c, size, name, col, rot=0.0):
    m = trimesh.creation.box(extents=size)
    if rot: m.apply_transform(trimesh.transformations.rotation_matrix(math.radians(rot), [0, 0, 1]))
    m.apply_translation(c); add(name, m, col); return m
def cyl(c, r, h, axis, name, col, sections=48):
    m = trimesh.creation.cylinder(radius=r, height=h, sections=sections)
    if axis == 'x': m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
    if axis == 'y': m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
    m.apply_translation(c); add(name, m, col); return m
def extrude(poly, z0, h, name, col):
    m = trimesh.creation.extrude_polygon(poly, h); m.apply_translation([0, 0, z0]); add(name, m, col); return m

# --- placa base v4 ----------------------------------------------------------
v3, outer, board, cuts, sensors, edge = C.build()
extrude(board, PCB_BOT, PCB_T, 'placa base v4', COL['pcb'])

# --- componentes (do .epro da v4) --------------------------------------------
z = zipfile.ZipFile(EPRO)
def load(n): return [json.loads(l) for l in z.read(n).decode('utf-8-sig').splitlines() if l.strip()]
rows = load([n for n in z.namelist() if n.endswith('.epcb')][0])
fps = {n.split('/')[1][:-5]: load(n) for n in z.namelist() if n.endswith('.efoo')}
des = {r[3]: r[8] for r in rows if r[0] == 'ATTR' and r[7] == 'Designator'}
comp = {r[1]: r for r in rows if r[0] == 'COMPONENT'}
pads = collections.defaultdict(list)
for Ly, net, g, i in check.pad_geoms(rows, fps): pads[i.split(':')[0]].append(g)
def kind(d, name):
    d = d or ''; name = (name or '').lower()
    if d.startswith('S'): return 'qre'
    if d.startswith('LED'): return 'led'
    if d.startswith('R'): return 'res'
    if d.startswith('C') and 'uf' in name: return 'elco'
    if d.startswith('C'): return 'cap'
    if d.startswith('U'): return 'ic'
    if d.startswith('J1'): return 'xt30'
    if d.startswith('J'): return 'conn'
    if d.startswith('SW'): return 'sw'
    if d.startswith('M'): return 'motorpad'
    return 'comp'
H = dict(qre=1.7, led=0.8, res=0.5, cap=0.8, ic=1.2, conn=2.5, sw=1.5, comp=1.0, xt30=5.0)
for cid, r in comp.items():
    if cid not in pads: continue
    k = kind(des.get(cid), r[7].get('Name'))
    if k == 'motorpad': continue
    g = unary_union(pads[cid]).convex_hull
    mrr = g.minimum_rotated_rectangle
    xs, ys = mrr.exterior.coords.xy
    p = np.array(list(zip(xs, ys))[:4]); e1 = p[1] - p[0]; e2 = p[2] - p[1]
    w, d = np.linalg.norm(e1) + 0.3, np.linalg.norm(e2) + 0.3
    ang = math.degrees(math.atan2(e1[1], e1[0]))
    cx, cy = g.centroid.x, g.centroid.y
    top = r[3] == 1
    name = f"{des.get(cid, cid)} {r[7].get('Name') or ''}".strip()
    if k == 'elco':
        h = 7.7; zc = PCB_TOP + h / 2 if top else PCB_BOT - h / 2
        cyl([cx, cy, zc], 3.15, h, 'z', name, COL['elco']); continue
    h = H.get(k, 1.0)
    if k == 'conn': h = 2.5 if top else 1.0
    zc = PCB_TOP + h / 2 if top else PCB_BOT - h / 2
    col = COL.get(k, COL['comp']) if k not in ('sw',) else COL['metal']
    box([cx, cy, zc], [w, d, h], name, col, rot=ang)
    if k == 'qre':   # lente do sensor (face de baixo)
        box([cx, cy, PCB_BOT - h - 0.05], [w * 0.5, d * 0.35, 0.1], name + ' (janela)', COL['qre_lens'], rot=ang)

# --- rodas, gearboxes, ventoinha, bateria (volumes dos STL do EVA-RT) ---------
for s in (-1, 1):
    cyl([s * 45.5, AXLE_Y, AXLE_Z], TIRE_R, 9.0, 'x', 'pneu', COL['tire'])
    cyl([s * 45.5 + s * 0.2, AXLE_Y, AXLE_Z], 8.25, 9.6, 'x', 'aro', COL['rim'])
    box([s * 35.25, -17.65, PCB_TOP + 7.15], [9.5, 26.7, 14.3], 'gearbox + motor 1020', COL['print2'])
    cyl([s * 40.75, AXLE_Y, AXLE_Z], 1.5, 2.2, 'x', 'eixo', COL['metal'])
cyl([0, 0, PCB_TOP + 14.15 / 2], 25.0, 14.15, 'z', 'carcaça da ventoinha (impeller_base)', COL['print'])
cyl([0, 0, PCB_TOP + 14.15 + 1.0], 9.8, 2.0, 'z', 'motor da ventoinha', COL['motor'])
box([0, 0, PCB_TOP + 14.15 + 2.0 + 6.0], [45.0, 20.5, 12.0], 'bateria 2S 350 mAh', COL['battery'])
cyl([0, 0, PCB_BOT - 0.3], 23.0, 0.6, 'z', 'saia de sucção (suction_base)', COL['print2'])

# --- presilhas, varetas e barra V1 --------------------------------------------
ROD_Z = PCB_TOP + 2.6
BAR_HOLE_Y = -3.68496 + BAR_DY
for s in (-1, 1):
    for y in (-1.75, 10.75):
        box([s * 43.75, y, PCB_TOP + 2.25], [6.0, 7.0, 4.5], 'presilha da vareta (barilla_clamp)', COL['print'])
    x0, x1 = 43.75, 44.62624
    p0 = np.array([s * x0, -4.5, ROD_Z]); p1 = np.array([s * x1, BAR_HOLE_Y, ROD_Z])
    rod = trimesh.creation.cylinder(radius=1.5, segment=[p0, p1], sections=24); add('vareta Ø3', rod, COL['rod'])
    box([s * x1, BAR_HOLE_Y, PCB_TOP + 7.95 / 2], [6.0, 7.0, 7.95], 'conexão da vareta (barilla_connection)', COL['print'])

BAR = [(48.25, 3.38), (28.7, 7.65), (19.5, 8.95), (10.0, 9.89), (0.0, 10.1), (-10.0, 9.89), (-19.5, 8.95), (-28.7, 7.65),
       (-48.25, 3.38), (-48.22, -6.5), (-43.0, -6.5), (-41.0, -4.5), (-41.0, -1.0), (-27.45, 1.34), (-12.66, 2.15),
       (-9.25, -1.26), (-6.75, -1.26), (-5.25, -2.76), (5.25, -2.76), (6.75, -1.26), (9.25, -1.26), (12.66, 2.15),
       (27.45, 1.34), (41.0, -1.0), (41.0, -4.5), (43.0, -6.5), (48.22, -6.5)]
bar = Polygon([(x, y + BAR_DY) for x, y in BAR])
for x, y, d in ((44.62624, -3.68496, 2.05), (-44.62624, -3.68496, 2.05), (9.2, 0.55, 1.6), (-9.2, 0.55, 1.6)):
    bar = bar.difference(Point(x, y + BAR_DY).buffer(d / 2, quad_segs=16))
extrude(bar, PCB_BOT, PCB_T, 'barra de sensores V1', COL['pcb'])
centres = json.loads((REPO / 'Estudo de caso - viabilidade do seguidor de linha/02_referencias/parametros_mecanicos_EVA.json')
                     .read_text(encoding='utf8'))['front_sensor_centres']
for i, (x, y) in enumerate(centres):
    ang = math.degrees(math.atan2(x, 120.0))      # a barra é curva: QRE alinhados à curvatura
    box([x, y + BAR_DY, PCB_BOT - 0.85], [2.9, 3.6, 1.7], f'QRE da barra {i + 1}', COL['qre'], rot=-ang)
box([0, 4.6 + BAR_DY, PCB_TOP + 0.6], [5.2, 6.6, 1.2], '74HC4067', COL['ic'])
for s in (-1, 1):
    box([s * 9.2 + s * 2.5, 0.55 + BAR_DY - 2.0, PCB_TOP + 4.25], [10.0, 9.0, 8.5], 'patim (sensor_sledge)', COL['print'])

# --- exportação ---------------------------------------------------------------
Y_UP = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], float)   # glTF: y para cima
scene = trimesh.Scene()
for k, (name, m, col) in enumerate(parts):
    m = m.copy(); m.apply_transform(Y_UP)
    mat = trimesh.visual.material.PBRMaterial(baseColorFactor=[*col, 255], metallicFactor=0.05, roughnessFactor=0.75, name=name)
    m.visual = trimesh.visual.TextureVisuals(material=mat)
    scene.add_geometry(m, node_name=f'{k:03d} {name}', geom_name=f'{k:03d} {name}')
scene.export(HERE / 'robo_v4.glb')
trimesh.util.concatenate([p[1] for p in parts]).export(HERE / 'robo_v4.stl')
allb = trimesh.util.concatenate([p[1] for p in parts]).bounds
print(f'L = {L:.2f} mm · peças: {len(parts)} · caixa: {np.round(allb[1] - allb[0], 1)} mm')
print('arquivos:', (HERE / 'robo_v4.glb').stat().st_size, (HERE / 'robo_v4.stl').stat().st_size)
