import json, math, os, sys
MIL = 0.0254
MIRROR = os.environ.get('MIRROR', 'y')
def load_lines(path):
    out = []
    for l in open(path, encoding='utf-8'):
        l = l.strip()
        if l: out.append(json.loads(l))
    return out

class Proj:
    def __init__(self, root):
        self.root = root
        self.pj = json.load(open(os.path.join(root, 'project.json')))
        pcbf = [f for f in os.listdir(os.path.join(root, 'PCB'))][0]
        self.pcbpath = os.path.join(root, 'PCB', pcbf)
        self.pcb = load_lines(self.pcbpath)
        self.fps = {}
        for f in os.listdir(os.path.join(root, 'FOOTPRINT')):
            self.fps[f.split('.')[0]] = load_lines(os.path.join(root, 'FOOTPRINT', f))
        self.parse()
    def parse(self):
        self.comps = {}
        self.attrs = {}
        for r in self.pcb:
            if r[0] == 'COMPONENT':
                self.comps[r[1]] = dict(id=r[1], layer=r[3], x=r[4], y=r[5], rot=r[6], a=r[7], raw=r, attrs={})
        for r in self.pcb:
            if r[0] == 'ATTR' and r[3] in self.comps:
                self.comps[r[3]]['attrs'][r[7]] = r[8]
        self.padnet = {}
        for r in self.pcb:
            if r[0] == 'PAD_NET' and r[2] != '':
                self.padnet[(r[1], r[2])] = r[3]
        self.byref = {c['attrs'].get('Designator'): c for c in self.comps.values()}
    def fp_pads(self, fpid):
        return [r for r in self.fps[fpid] if r[0] == 'PAD']
    def comp_pads(self, c):
        """absolute pads: list of dict(num, x, y, layer, shape, hole, rot, net) in mil"""
        fpid = c['attrs'].get('Footprint')
        res = []
        if not fpid or fpid not in self.fps: return res
        th = math.radians(c['rot'])
        bot = c['layer'] == 2
        for p in self.fp_pads(fpid):
            px, py = p[6], p[7]
            prot = p[8]
            lay = p[4]
            if bot:
                if MIRROR == 'x': px = -px; prot = 180 - prot
                elif MIRROR == 'y': py = -py; prot = -prot
                elif MIRROR == 'yneg': py = -py; prot = -prot; th = -math.radians(c['rot'])
                if lay == 1: lay = 2
                elif lay == 2: lay = 1
            x = c['x'] + px*math.cos(th) - py*math.sin(th)
            y = c['y'] + px*math.sin(th) + py*math.cos(th)
            res.append(dict(num=p[5], x=x, y=y, layer=lay, hole=p[9], shape=p[10], rot=(prot + c['rot']) % 360,
                            net=self.padnet.get((c['id'], p[5]), ''), ref=c['attrs'].get('Designator')))
        return res
    def all_pads(self):
        out = []
        for c in self.comps.values(): out += self.comp_pads(c)
        return out

# ---------- geometry ----------
from shapely.geometry import Polygon, Point, LineString, box, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity

def path_to_coords(path, x0=None, y0=None, seg=16):
    """EasyEDA path list -> list of (x,y)"""
    pts = []
    i = 0
    mode = 'L'
    if not isinstance(path[0], str):
        pts.append((path[0], path[1])); i = 2
    while i < len(path):
        t = path[i]
        if isinstance(t, str):
            mode = t; i += 1; continue
        if mode == 'L':
            pts.append((path[i], path[i+1])); i += 2
        elif mode == 'ARC':
            ang, ex, ey = path[i], path[i+1], path[i+2]; i += 3
            sx, sy = pts[-1]
            pts += arc_points(sx, sy, ex, ey, ang, seg)[1:]
        elif mode == 'CARC':
            ang, ex, ey = path[i], path[i+1], path[i+2]; i += 3
            sx, sy = pts[-1]
            pts += arc_points(sx, sy, ex, ey, ang, seg)[1:]
        else:
            raise ValueError(mode)
    return pts

def arc_points(sx, sy, ex, ey, ang, seg=16):
    # arc from s to e with sweep angle ang (deg); positive = CCW
    a = math.radians(ang)
    if abs(a) < 1e-9: return [(sx, sy), (ex, ey)]
    dx, dy = ex - sx, ey - sy
    d = math.hypot(dx, dy)
    r = d / 2 / math.sin(abs(a) / 2)
    mx, my = (sx + ex) / 2, (sy + ey) / 2
    h = math.sqrt(max(r*r - (d/2)**2, 0))
    # center on the left of s->e for ccw with |a|<pi
    nx, ny = -dy / d, dx / d
    sgn = 1 if a > 0 else -1
    if abs(a) > math.pi: sgn = -sgn
    cx, cy = mx + sgn*nx*h, my + sgn*ny*h
    a0 = math.atan2(sy - cy, sx - cx)
    n = max(4, int(abs(ang) / 360 * seg * 4))
    return [(cx + r*math.cos(a0 + a*k/n), cy + r*math.sin(a0 + a*k/n)) for k in range(n+1)]

def pad_shape(p):
    """pad dict -> shapely polygon (mil), absolute"""
    sh = p['shape']; t = sh[0]
    if t == 'RECT':
        w, h = sh[1], sh[2]; r = sh[3] if len(sh) > 3 else 0
        g = box(-w/2, -h/2, w/2, h/2)
        if r: 
            rr = min(w, h) * r / 100 / 2 if r <= 100 else 0
            if rr > 0: g = box(-w/2+rr, -h/2+rr, w/2-rr, h/2-rr).buffer(rr, 8)
    elif t in ('ELLIPSE',):
        w, h = sh[1], sh[2]
        g = affinity.scale(Point(0, 0).buffer(1, 16), w/2, h/2)
    elif t == 'OVAL':
        w, h = sh[1], sh[2]
        if w >= h: g = LineString([(-(w-h)/2, 0), ((w-h)/2, 0)]).buffer(h/2, 8)
        else: g = LineString([(0, -(h-w)/2), (0, (h-w)/2)]).buffer(w/2, 8)
    elif t == 'POLY' or t == 'POLYGON':
        g = Polygon(path_to_coords(sh[1]))
    else:
        raise ValueError(t)
    g = affinity.rotate(g, p['rot'], origin=(0, 0))
    return affinity.translate(g, p['x'], p['y'])

def outline_polygon(proj):
    segs = []
    for r in proj.pcb:
        if r[0] == 'POLY' and r[4] == 11:
            pts = [(round(a,2),round(b,2)) for a,b in path_to_coords(r[6])]
            segs.append(pts)
    # chain
    from shapely.ops import polygonize, linemerge
    lines = [LineString(s) for s in segs]
    polys = list(polygonize(unary_union(lines)))
    polys.sort(key=lambda g: -g.area)
    return polys[0], segs

def copper(proj, extra=None):
    """returns dict layer-> list of (net, geom, kind, ref)"""
    items = []
    for q in proj.all_pads():
        g = pad_shape(q)
        lays = [1, 2] if q['layer'] == 12 else [q['layer']]
        for L in lays: items.append((L, q['net'], g, 'pad', f"{q['ref']}.{q['num']}"))
    for r in proj.pcb:
        if r[0] == 'LINE' and r[4] in (1, 2):
            g = LineString([(r[5], r[6]), (r[7], r[8])]).buffer(r[9]/2, 8)
            items.append((r[4], r[3], g, 'track', r[1]))
        elif r[0] == 'ARC' and r[4] in (1, 2):
            pts = arc_points(r[5], r[6], r[7], r[8], r[9])
            g = LineString(pts).buffer(r[10]/2, 8)
            items.append((r[4], r[3], g, 'track', r[1]))
        elif r[0] == 'VIA':
            g = Point(r[5], r[6]).buffer(r[8]/2, 12)
            for L in (1, 2): items.append((L, r[3], g, 'via', r[1]))
        elif r[0] == 'POURED':
            pour = [x for x in proj.pcb if x[0] == 'POUR' and x[1] == r[2]][0]
            polys = r[5]
            # first = outer, rest = holes? each poly is path
            rings = [[(a*10, b*10) for a, b in path_to_coords(pp)] for pp in polys]
            rings = [rg for rg in rings if len(rg) >= 4]
            if not rings: continue
            try:
                g = Polygon(rings[0], rings[1:]).buffer(0)
            except Exception:
                g = Polygon(rings[0]).buffer(0)
            items.append((pour[4], pour[3], g, 'pour', r[1]))
        elif r[0] == 'FILL' and r[4] in (1, 2):
            pass
    return items
