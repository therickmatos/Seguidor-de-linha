"""Contorno experimental baixo com dois QRE por lado.

Baseado no RUSH/SATURN v3 / EVA-RT, EXOTIC TEAM MX, AGPL-3.0.
Preserva recortes do arquivo original; não é uma PCB roteada para fabricação.
"""
import json
import math
import zipfile
from hashlib import sha256
from shapely import affinity
from shapely.geometry import LineString, Point, box
from shapely.ops import polygonize, unary_union
import simular_comparar as model

SENSOR_X=(52.25,77.75)
SENSOR_Y=20.
HOLE_DISTANCE=60.
PRESET_ID='chassi_baixo_2'


def length_from_holes(mm):
    return (model.Y_HOLE_BASE+math.sqrt(mm**2-(model.X_HOLE_V1-model.X_HOLE_BASE)**2)
            -model.Y_HOLE_V1+model.Y_SENSOR_V1-model.AXLE)


def build_geometry():
    source=model.CASE/'01_projeto/ProPrj_RUSH - SATURN - v3_2026-11-09.epro'
    with zipfile.ZipFile(source) as z:
        pcb=next(n for n in z.namelist() if n.endswith('.epcb'))
        rows=[json.loads(line) for line in z.read(pcb).decode('utf-8-sig').splitlines() if line.strip()]
    segments=[r[6] for r in rows if r[0]=='POLY' and r[4]==11]
    polys=list(polygonize([LineString([(s[0]*.0254,s[1]*.0254),(s[3]*.0254,s[4]*.0254)]) for s in segments]))
    assert len(polys)==1,'O v3 deve ter um único contorno externo.'
    original=polys[0];cuts=[]
    for row in rows:
        if row[0]=='FILL' and row[4]==12:
            for shape in row[7]:
                if shape[0]=='CIRCLE':
                    _,x,y,r=shape
                    cuts.append(Point(x*.0254,y*.0254).buffer(r*.0254,quad_segs=24))
        elif row[0]=='PAD' and row[9][0]=='SLOT':
            x,y,angle=row[6]*.0254,row[7]*.0254,row[8]
            length,width=row[9][1]*.0254,row[9][2]*.0254
            slot=LineString([(0,-(length-width)/2),(0,(length-width)/2)]).buffer(width/2,quad_segs=16)
            cuts.append(affinity.translate(affinity.rotate(slot,angle,origin=(0,0)),x,y))
    core=original.intersection(box(-50,-100,50,100))
    right=LineString([(48.,4.6),(SENSOR_X[0],SENSOR_Y),(SENSOR_X[1],SENSOR_Y)]).buffer(4.6,quad_segs=48)
    outer=unary_union([core,right,affinity.scale(right,xfact=-1,yfact=1,origin=(0,0))])
    board=outer.difference(unary_union(cuts))
    assert board.is_valid and board.geom_type=='Polygon' and len(board.interiors)==15
    assert outer.symmetric_difference(original).intersection(box(-45,-100,45,100)).area<1e-8
    assert outer.symmetric_difference(original).intersection(box(-150,-100,150,0)).area<1e-8
    assert all(outer.covers(cut) for cut in cuts)
    assert all(board.contains(Point(sign*x,SENSOR_Y)) for sign in [-1,1] for x in SENSOR_X)
    def points(ring):return [[round(x,5),round(y,5)] for x,y in ring.coords]
    return dict(id=PRESET_ID,name='Chassi baixo · 2 sensores por lado',
                outline=points(outer.exterior),cutouts=[points(cut.exterior) for cut in cuts],
                sensor_x=list(SENSOR_X),sensor_y=SENSOR_Y,hole_distance=HOLE_DISTANCE,
                L=length_from_holes(HOLE_DISTANCE),width=outer.bounds[2]-outer.bounds[0],
                length=outer.bounds[3]-outer.bounds[1],source_sha256=sha256(source.read_bytes()).hexdigest())
