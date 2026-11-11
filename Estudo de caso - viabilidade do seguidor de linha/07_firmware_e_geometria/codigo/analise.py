"""Geometria das marcas × lógica de marcas do firmware EVA-RT 1.2.2.

Baseado no EVA-RT, (c) EXOTIC TEAM MX, AGPL-3.0 (github.com/EXOTIC-TEAM-MX/EVA-RT).
Reutiliza as pistas de ../06_estudo_consolidado/codigo (modelos aproximados,
não plantas oficiais).

Modelo cinemático (o mesmo do estudo 06): o centro da barra de sensores fica
sobre a linha, o eixo das rodas não escorrega de lado, corpo rígido:
    d(alpha)/ds = sin(phi - alpha) / L
com L = distância do eixo ao centro da barra. Não há PID, motor, óptica real,
derrapagem nem tempo: é uma conferência geométrica.

O que este módulo acrescenta:
1. "Branco" visto por cada sensor lateral ao longo da volta: qualquer marca
   (dos dois lados) e a própria linha, inclusive os cruzamentos.
2. Emulação de Marks.ino (EVA-RT 1.2.2) no domínio da distância:
   - borda de subida no sensor direito arma a parada;
   - se o sensor esquerdo tiver borda de subida a menos de `janela` (= velocidade
     × MARK_TIMER_MS) da borda do direito, a parada é cancelada (cruzamento);
   - senão o robô desliga (chegada... ou parada falsa).
3. Varredura de L e da posição do sensor lateral (um por lado).
"""
from pathlib import Path
import json
import math
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
CODE06 = Path(os.environ.get('ESTUDO06', HERE.parents[1] / '06_estudo_consolidado' / 'codigo'))
sys.path.insert(0, str(CODE06))

AXLE = -22.587743818986525   # y do eixo das rodas (origem = centro da ventoinha)
LINE_HALF = 9.5              # meia largura da linha de 19 mm
MARK = (9.5, 49.5, 89.5)     # meia largura, início e fim da marca (do centro da linha)
COMMON = (9.0, 53.0, 83.0)   # região comum às tolerâncias do regulamento (±1, ±3 mm)

# Distância entre furos (base ↔ barra V1) → L, como no estudo 06.
_Y_HOLE_BASE, _X_HOLE_BASE = 10.75, 43.75
_X_HOLE_V1, _Y_HOLE_V1, _Y_SENSOR_V1 = 44.62624, -3.68496, 6.9577325


def L_from_holes(mm):
    return (_Y_HOLE_BASE + math.sqrt(mm ** 2 - (_X_HOLE_V1 - _X_HOLE_BASE) ** 2)
            - _Y_HOLE_V1 + _Y_SENSOR_V1 - AXLE)


def holes_from_L(L):
    dy = L + AXLE - _Y_SENSOR_V1 + _Y_HOLE_V1 - _Y_HOLE_BASE
    return math.hypot(dy, _X_HOLE_V1 - _X_HOLE_BASE)


def load_tracks(step=0.5, names=None):
    """Devolve {nome: dict(track, cycle, marks, meta)} das pistas disponíveis."""
    import importlib
    wanted = [('TRIF 2025', 'pista_trif2025'), ('TRIF 2024', 'pista_c_regulamentar'),
              ('EVA-RT teste', 'pista_eva_rt_teste')]
    out = {}
    for name, module in wanted:
        if names and name not in names:
            continue
        if not (CODE06 / f'{module}.py').exists():
            continue
        mod = importlib.import_module(module)
        track, cycle, marks, meta = mod.build(step)
        crossings = meta.get('crossings')
        if crossings is None:
            crossings = [meta['crossing']]
        crossings = [c['xy'] if isinstance(c, dict) else c for c in crossings]
        out[name] = dict(track=np.asarray(track), cycle=np.asarray(cycle), marks=marks, meta=meta,
                         crossings=np.asarray(crossings, dtype=float).reshape(-1, 2),
                         tree=cKDTree(np.asarray(cycle)[:, 1:3]))
    return out


def pose(track, L):
    """Orientação do robô (RK4) com o centro da barra sobre a linha."""
    s, phi = track[:, 0], np.unwrap(track[:, 3])
    alpha = np.empty(len(track))
    alpha[0] = phi[0]
    a = float(phi[0])
    sin = math.sin
    for i in range(1, len(track)):
        h = s[i] - s[i - 1]
        p = phi[i - 1]
        dp = phi[i] - p
        k1 = sin(p - a) / L
        k2 = sin(p + dp / 2 - a - h * k1 / 2) / L
        k3 = sin(p + dp / 2 - a - h * k2 / 2) / L
        k4 = sin(p + dp - a - h * k3) / L
        a += h * (k1 + 2 * k2 + 2 * k3 + k4) / 6
        alpha[i] = a
    return alpha


def sensor_path(track, alpha, L, x, y):
    """Trajetória de um ponto do robô: x lateral (+ = esquerda), y no referencial da placa."""
    e = np.column_stack((np.cos(alpha), np.sin(alpha)))
    n = np.column_stack((-np.sin(alpha), np.cos(alpha)))
    return track[:, 1:3] + (y - AXLE - L) * e + x * n


def _mark_uv(points, m):
    co, si = math.cos(m['phi']), math.sin(m['phi'])
    dx, dy = points[:, 0] - m['x'], points[:, 1] - m['y']
    return dx * co + dy * si, m['side'] * (-dx * si + dy * co)


def _runs(mask):
    """Índices [início, fim) dos trechos contíguos em que mask é verdadeira."""
    d = np.diff(np.r_[0, mask.astype(np.int8), 0])
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)))


def white_events(T, points, s, lo, hi, r=0.0):
    """Trechos em que o ponto vê branco (marca ou linha) entre os índices lo..hi.

    r > 0 aumenta as áreas brancas (campo óptico do sensor); r < 0 encolhe.
    """
    pts, ss = points[lo:hi], s[lo:hi]
    label = np.full(len(pts), -2, dtype=int)          # -2 = preto
    dist, _ = T['tree'].query(pts)
    label[dist <= LINE_HALF + r] = -1                  # -1 = linha
    for i, m in enumerate(T['marks']):
        u, v = _mark_uv(pts, m)
        inside = (np.abs(u) <= MARK[0] + r) & (v >= MARK[1] - r) & (v <= MARK[2] + r)
        label[inside] = i
    events = []
    for a, b in _runs(label != -2):
        kinds = set(label[a:b].tolist())
        mid = pts[(a + b) // 2]
        if kinds == {-1}:
            near = np.linalg.norm(T['crossings'] - mid, axis=1).min() if len(T['crossings']) else 1e9
            what = 'cruzamento' if near < 120 else 'linha'
            mark = None
        else:
            i = max(k for k in kinds if k >= 0)
            mark = T['marks'][i]
            what = mark['kind']
        events.append(dict(s0=float(ss[a]), s1=float(ss[b - 1]), what=what,
                           mark=None if mark is None else mark['label'],
                           mark_side=None if mark is None else mark['side'],
                           min_line_dist=float(dist[a:b].min())))
    return events, float(dist.min())


def marks_read(T, points_by_side, s, box=MARK):
    """Para cada marca: algum sensor do lado certo cruza o retângulo? (contagem do estudo 06)."""
    out = []
    for m in T['marks']:
        lo, hi = np.searchsorted(s, m['s'] - 200), np.searchsorted(s, m['s'] + 300)
        hit, margin = False, -1e9
        for pts in points_by_side[m['side']]:
            u, v = _mark_uv(pts[lo:hi], m)
            mg = np.minimum(np.minimum(box[0] - np.abs(u), v - box[1]), box[2] - v)
            margin = max(margin, float(mg.max()))
            hit = hit or margin > 0
        out.append(dict(label=m['label'], kind=m['kind'], side=m['side'], hit=hit, margin=margin))
    return out


def evaluate(T, L, left=(69.5,), right=(69.5,), y=4.5, r_false=3.0, alpha=None):
    """Contagem de marcas + emulação do firmware para uma configuração."""
    track = T['track']
    s = track[:, 0]
    if alpha is None:
        alpha = pose(track, L)
    paths = {1: [sensor_path(track, alpha, L, x, y) for x in left],
             -1: [sensor_path(track, alpha, L, -x, y) for x in right]}
    nominal = marks_read(T, paths, s, MARK)
    common = marks_read(T, paths, s, COMMON)
    meta = T['meta']
    lo, hi = np.searchsorted(s, meta['start']), np.searchsorted(s, meta['end'])
    # Firmware: usa só um sensor por lado (A5 esquerda, A6 direita) → o primeiro de cada lista.
    ev_left, _ = white_events(T, paths[1][0], s, lo, hi, r_false)
    ev_right, clearance_right = white_events(T, paths[-1][0], s, lo, hi, r_false)
    ev_right_centre, _ = white_events(T, paths[-1][0], s, lo, hi, 0.0)
    rises_left = np.array([e['s0'] for e in ev_left])
    start_s = next(m['s'] for m in T['marks'] if m['kind'] == 'partida')
    finish_s = start_s + meta['period'] - next(
        (m2['s'] - m1['s']) % meta['period'] for m1 in T['marks'] if m1['kind'] == 'chegada'
        for m2 in T['marks'] if m2['kind'] == 'partida')
    right_report = []
    for e in ev_right:
        gap = float(np.abs(rises_left - e['s0']).min()) if len(rises_left) else float('inf')
        right_report.append(dict(**e, left_edge_gap_mm=gap))
    read_centre = {e['what'] for e in ev_right_centre}
    return dict(L=L, left=list(left), right=list(right), y=y,
                d_bar_to_sensor=L - (y - AXLE),
                total=len(nominal), nominal=sum(m['hit'] for m in nominal), common=sum(m['hit'] for m in common),
                left_total=sum(m['side'] > 0 for m in nominal),
                left_nominal=sum(m['hit'] and m['side'] > 0 for m in nominal),
                left_common=sum(m['hit'] and m['side'] > 0 for m in common),
                right_nominal=sum(m['hit'] and m['side'] < 0 for m in nominal),
                right_common=sum(m['hit'] and m['side'] < 0 for m in common),
                missed=[m['label'] for m in nominal if not m['hit']],
                min_margin_left=min(m['margin'] for m in nominal if m['side'] > 0),
                right_events=right_report, left_events=ev_left,
                right_min_line_distance=clearance_right,
                start_read='partida' in read_centre, finish_read='chegada' in read_centre,
                start_s=start_s, finish_s=finish_s)


def firmware_verdict(res, window_mm):
    """Resultado de Marks.ino para uma janela (= velocidade × MARK_TIMER_MS) em mm.

    Supõe o robô largando perto da marca de partida (a partida cai no 1º segundo,
    em que o firmware ignora a parada).
    """
    stops, cancelled = [], []
    for e in res['right_events']:
        if e['what'] == 'partida':
            continue
        if e['left_edge_gap_mm'] < window_mm:
            cancelled.append(e)
        else:
            stops.append(e)
    first = stops[0] if stops else None
    ok = bool(first and first['what'] == 'chegada')
    return dict(ok=ok, first_stop=None if first is None else first['what'],
                first_stop_s=None if first is None else first['s0'],
                false_stops=[e for e in stops if e['what'] != 'chegada'],
                crossings_cancelled=sum(e['what'] == 'cruzamento' for e in cancelled),
                max_crossing_gap=max([e['left_edge_gap_mm'] for e in res['right_events']
                                      if e['what'] == 'cruzamento'], default=None))


def strip(res):
    """Remove listas longas para gravar em JSON."""
    out = {k: v for k, v in res.items() if k not in ('left_events',)}
    return out


if __name__ == '__main__':
    tracks = load_tracks(0.5)
    for name, T in tracks.items():
        for label, L in [('EVA-RT L=100', 100.0), ('v3 63,14 mm', L_from_holes(63.141))]:
            res = evaluate(T, L)
            v = firmware_verdict(res, 30.0)
            print(f"{name:14s} {label:13s} L={L:6.1f} marcas {res['nominal']}/{res['total']} "
                  f"(esq {res['left_nominal']}/{res['left_total']}, dir {res['right_nominal']}/2) "
                  f"parada: {v['first_stop']} falsas={len(v['false_stops'])} "
                  f"dir-linha min={res['right_min_line_distance']:.1f} mm")
