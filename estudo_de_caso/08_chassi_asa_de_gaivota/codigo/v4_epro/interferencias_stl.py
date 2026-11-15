"""Componentes da placa × peças do EVA-RT (STL e camada Document do .eprj original).

Posições: carcaça e hélice no centro (carcaça girada 45°); caixa de redução pelos dois furos
(±35,25; −3,73/−26,55), que batem com os furos da base do gearbox.stl (22,81 mm); motor 1020
deitado como na camada Document do EVA-RT (x ±18…38, y −16,26…−6,26); presilhas e varetas
aproximadas; pneus Ø23 no eixo y = −22,59. Alturas dos componentes estimadas pelo tipo.
Uso: python3 interferencias_stl.py <placa.epro>
Baseado no EVA-RT, (c) EXOTIC TEAM MX, AGPL-3.0.
"""
import sys, os, pickle
from shapely.geometry import Point, box
from shapely.ops import unary_union
from shapely import affinity
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verifica_placa as V, check
M = 0.0254
rows, fps, outer = V.board(sys.argv[1])
comp = {r[1]: r for r in rows if r[0] == 'COMPONENT'}
des = {r[3]: r[8] for r in rows if r[0] == 'ATTR' and r[3] in comp and r[7] == 'Designator'}
casing = pickle.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'carcaca_ate_8mm.pkl'), 'rb'))
pads = {}
for L, n, g, i in check.pad_geoms(rows, fps): pads.setdefault(i.split(':')[0], []).append(g)
def height(d):
    if d in ('C1', 'C2'): return 7.7
    if d == 'J1': return 5.0          # XT30 de placa
    if d == 'J4': return 8.5          # fêmea 1×6 do Bluetooth
    if d == 'J3': return 2.5          # barra 90°
    if d.startswith('SW'): return 3.5
    if d.startswith('M'): return 1.5  # pad do fio + solda
    if d.startswith('S'): return 1.7
    if d.startswith('U') or d.startswith('Q'): return 1.2
    if d.startswith('J'): return 2.5
    return 0.9
def body(cid, d):
    r = comp[cid]
    if d in ('C1', 'C2'): return affinity.translate(box(-3.3, -3.3, 3.3, 3.3), r[4] * M, r[5] * M)
    return unary_union(pads[cid]).convex_hull.buffer(0.15)
def bx(xa, xb, y0, y1): return box(min(xa, xb), y0, max(xa, xb), y1)
Z = []   # (nome, região 2D, face, altura mínima que colide)
Z.append(('hélice Ø34', Point(0, 0).buffer(18.0), 1, 1.3))          # 1 mm além da ponta (r 17); só peças altas (U2 tem só os pads em r 17,3, como no EVA-RT)
for s in (-1, 1):
    Z.append(('caixa de redução', bx(s * 30.5, s * 40.0, -28.49, -1.77), 1, 0.0))
    Z.append(('motor 1020 deitado', bx(s * 18.0, s * 38.0, -16.26, -6.26), 1, 2.4))   # o IFX9201 (DSO-12) do EVA-RT fica embaixo
    for y in (-1.75, 10.75):
        Z.append(('presilha da vareta', bx(s * 41.25, s * 50.75, y - 3.5, y + 3.5), 1, 0.0))
    Z.append(('vareta Ø3', bx(s * 42.2, s * 46.2, -4.5, 40), 1, 1.1))
    Z.append(('pneu Ø23', bx(s * 41.0, s * 50.0, -34.1, -11.1), 1, 0.0))
# carcaça: compara a altura do componente com o ponto mais baixo da carcaça acima dele
import numpy as np, trimesh
from shapely.geometry import Polygon
_m = trimesh.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../referencias/eva-rt/3d_models/impeller_base_1.stl'))
_m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(45), [0, 0, 1]))
TRI = [(p, t[:, 2].min()) for p, t in ((Polygon(t[:, :2]).buffer(0), t) for t in _m.triangles) if p.area > 1e-8]
Z.append(('placa de sucção (embaixo)', Polygon([(0, 21), (23.08, 16.81), (23.08, -27.5), (-23.08, -27.5), (-23.08, 16.81)]), 2, 0.0))
found = []
for cid, d in sorted(des.items(), key=lambda x: x[1]):
    if cid not in pads: continue
    b = body(cid, d); h = height(d); face = comp[cid][3]
    if face == 1:
        zs = [zz for p, zz in TRI if p.intersects(b)]
        if zs and min(zs) < h + 0.3: found.append((d, 'carcaça', round(min(zs), 2), h))
    for nome, g, f, hmin in Z:
        if face == f and h > hmin and b.intersects(g):
            found.append((d, nome, round(b.intersection(g).area, 2), h))
for f in found: print(f)
print('total:', len(found))
