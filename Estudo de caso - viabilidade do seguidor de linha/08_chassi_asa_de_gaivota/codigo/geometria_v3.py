"""Lê o contorno e os recortes da placa base v3 (RUSH/SATURN) do arquivo .epro.

Baseado no EVA-RT, (c) EXOTIC TEAM MX, AGPL-3.0. Unidades em mm; origem no centro
da ventoinha, +y para a frente (mesmo referencial do .epro).
"""
from pathlib import Path
import json
import zipfile

from shapely import affinity
from shapely.geometry import LineString, Point
from shapely.ops import polygonize

CASE = Path(__file__).resolve().parents[2]
EPRO = CASE / '01_projeto' / 'ProPrj_RUSH - SATURN - v3_2026-11-09.epro'
MIL = 0.0254


def _rows():
    with zipfile.ZipFile(EPRO) as z:
        pcb = next(n for n in z.namelist() if n.endswith('.epcb'))
        return [json.loads(l) for l in z.read(pcb).decode('utf-8-sig').splitlines() if l.strip()]


def load():
    """(contorno externo, [recortes]) da v3 como polígonos shapely."""
    rows = _rows()
    segs = [r[6] for r in rows if r[0] == 'POLY' and r[4] == 11]
    polys = list(polygonize([LineString([(s[0] * MIL, s[1] * MIL), (s[3] * MIL, s[4] * MIL)]) for s in segs]))
    assert len(polys) == 1, 'a v3 deve ter um único contorno externo'
    cuts = []
    for r in rows:
        if r[0] == 'FILL' and r[4] == 12:
            for shape in r[7]:
                if shape[0] == 'CIRCLE':
                    _, x, y, rad = shape
                    cuts.append(Point(x * MIL, y * MIL).buffer(rad * MIL, quad_segs=32))
        elif r[0] == 'PAD' and r[9][0] == 'SLOT':
            x, y, ang = r[6] * MIL, r[7] * MIL, r[8]
            length, width = r[9][1] * MIL, r[9][2] * MIL
            slot = LineString([(0, -(length - width) / 2), (0, (length - width) / 2)]).buffer(width / 2, quad_segs=16)
            cuts.append(affinity.translate(affinity.rotate(slot, ang, origin=(0, 0)), x, y))
    return polys[0], cuts
