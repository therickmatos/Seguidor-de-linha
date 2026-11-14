"""Serigrafia de baixo (v8.8): símbolo do IF + "IFSP" e "Projetado por / Erick Matos".

O símbolo é desenhado em polígonos (FILL) na camada 4 (Bottom Silkscreen), já espelhado em x
para ser lido olhando a placa por baixo; os textos são STRING na camada 4 (o EasyEDA espelha sozinho).
Lugar: espaço livre à esquerda da placa de sucção, entre ela e os pads do motor esquerdo.
Uso: python3 serigrafia_v88.py <entrada.epro> <saida.epro>
Baseado no EVA-RT, (c) EXOTIC TEAM MX, AGPL-3.0.
"""
import sys, os, json, zipfile, re
from shapely.geometry import box, Point, Polygon
from shapely.ops import unary_union
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check, verifica_placa as V
M = 0.0254
mil = lambda v: round(v / M, 4)
SRC, DST = sys.argv[1], sys.argv[2]
z = zipfile.ZipFile(SRC)
PCBN = [n for n in z.namelist() if n.endswith('.epcb')][0]
rows = [json.loads(l) for l in z.read(PCBN).decode('utf-8-sig').splitlines() if l.strip()]
rows_chk, fps, outer = V.board(SRC)
n_id = max(int(r[1][1:]) for r in rows if len(r) > 1 and isinstance(r[1], str) and re.fullmatch(r'e\d+', r[1]))
def nid():
    global n_id
    n_id += 1; return f'e{n_id}'
LAYER = 4
shapes = []
def rect(x0, y0, x1, y1):
    rows.append(['FILL', nid(), 0, '', LAYER, 0.1, 0, [[mil(x0), mil(y0), 'L', mil(x1), mil(y0), mil(x1), mil(y1), mil(x0), mil(y1), mil(x0), mil(y0)]], 0])
    shapes.append(box(x0, y0, x1, y1))
def circle(cx, cy, r):
    rows.append(['FILL', nid(), 0, '', LAYER, 0.1, 0, [['CIRCLE', mil(cx), mil(cy), mil(r)]], 0])
    shapes.append(Point(cx, cy).buffer(r))
def text(x, y, s, h=1.2, w=0.18):
    rows.append(['STRING', nid(), 0, LAYER, mil(x), mil(y), s, 'default', mil(h), mil(w), 0, 0, 3, 0, 0, 0, 0, 0])
    shapes.append(box(x - 0.45 * h * len(s), y - h / 2, x + 0.45 * h * len(s), y + h / 2))   # tamanho aproximado

# símbolo do IF (visto por baixo): linha 1 círculo, ■, ■; linha 2 ■, ■; linha 3 ■, ■, ■; linha 4 ■, ■
CX, TOP, S, G = -29.0, 4.5, 1.35, 0.30
grid = ['o##', '##.', '###', '##.']
for r, linha in enumerate(grid):
    for c, ch in enumerate(linha):
        u = (c - 1) * (S + G)                 # coordenada vista por baixo
        x = CX - u                            # espelhada para o referencial da placa (vista de cima)
        y = TOP - r * (S + G) - S / 2
        if ch == '#': rect(x - S / 2, y - S / 2, x + S / 2, y + S / 2)
        if ch == 'o': circle(x, y, S / 2)
ybase = TOP - 4 * (S + G) + G
text(CX, ybase - 0.3 - 0.6, 'IFSP', 1.2, 0.18)
text(-33.3, 8.25, 'Projetado por', 1.2, 0.18)
text(-33.3, 6.75, 'Erick Matos', 1.2, 0.18)

# conferência: nada encosta em pad, via ou furo, e fica dentro da placa e fora da placa de sucção
hard = unary_union([g for l, n, g, i in check.pad_geoms(rows_chk, fps) if l == 2] + check.holes(rows_chk) +
                   [Point(r[5] * M, r[6] * M).buffer(r[8] * M / 2) for r in rows_chk if r[0] == 'VIA'])
plate = Polygon([(0, 21), (23.08, 16.81), (23.08, -27.5), (-23.08, -27.5), (-23.08, 16.81)])
u = unary_union(shapes)
print('distância a pads/vias/furos (mm):', round(u.distance(hard), 2), '| dentro da placa:', outer.buffer(-0.5).contains(u), '| fora da sucção:', not u.intersects(plate))
print('caixa total:', [round(v, 2) for v in u.bounds])
with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zo:
    for info in z.infolist():
        if info.is_dir(): zo.writestr(info, b''); continue
        data = z.read(info.filename)
        if info.filename == PCBN:
            data = ''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n' for r in rows).encode('utf-8')
        zo.writestr(info, data)
print('arquivo:', DST)
