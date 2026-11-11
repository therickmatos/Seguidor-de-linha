"""Margem das marcas laterais × posição dos sensores (dois QRE por lado).

Baseado no EVA-RT, (c) EXOTIC TEAM MX, AGPL-3.0. Reutiliza as pistas do estudo 06
e a cinemática de ../../07_firmware_e_geometria/codigo/analise.py.

Margem de uma marca = quanto o centro do sensor entra no retângulo da marca, na
métrica do "pior lado" (L-infinito): min(9,5-|u|, v-49,5, 89,5-v), maximizada ao
longo da passagem. 3 mm de margem = o centro do QRE passa a pelo menos 3 mm de
qualquer borda da fita. Com dois sensores no mesmo lado vale o melhor dos dois.
"""
from pathlib import Path
import math
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / '07_firmware_e_geometria' / 'codigo'))
import analise as A  # noqa: E402

TRACKS = ('TRIF 2025', 'TRIF 2024', 'EVA-RT teste')


def offset_track(track, e):
    """Centro da barra deslocado e mm (+ = para a esquerda) em relação à linha, fixo."""
    if not e:
        return track, track[:, 0]
    phi = track[:, 3]
    out = track.copy()
    out[:, 1] = track[:, 1] - e * np.sin(phi)
    out[:, 2] = track[:, 2] + e * np.cos(phi)
    arc = np.r_[0.0, np.cumsum(np.hypot(np.diff(out[:, 1]), np.diff(out[:, 2])))]
    return out, arc


def scenario_track(T, kind, value):
    if kind == 'fixo':
        return offset_track(T['track'], value)
    return A.drift_track(T['track'], value)


def margin_grid(T, L, xs, ys, kind='fixo', value=0.0, box=A.MARK):
    """Margens [marca, x, y] para sensores no lado de cada marca (x absoluto)."""
    track, arc = scenario_track(T, kind, value)
    alpha = A.pose(track, L, arc)
    s = track[:, 0]
    xs = np.asarray(xs, float); ys = np.asarray(ys, float)
    half, inner, outer = box
    out = np.empty((len(T['marks']), len(xs), len(ys)))
    for i, m in enumerate(T['marks']):
        lo, hi = np.searchsorted(s, m['s'] - 200), np.searchsorted(s, m['s'] + 300)
        p = track[lo:hi, 1:3]; a = alpha[lo:hi]
        ex, ey = np.cos(a), np.sin(a)          # frente do robô
        nx, ny = -ey, ex                        # esquerda do robô
        co, si = math.cos(m['phi']), math.sin(m['phi'])
        side = m['side']
        # ponto = p + (y - AXLE - L) e + side*x n  (marca à esquerda → sensor esquerdo)
        lead = ys - A.AXLE - L
        bx = p[:, 0] - m['x']; by = p[:, 1] - m['y']
        u0 = bx * co + by * si; v0 = side * (-bx * si + by * co)
        eu = ex * co + ey * si; ev = side * (-ex * si + ey * co)
        nu = nx * co + ny * si; nv = side * (-nx * si + ny * co)
        u = (u0[:, None, None] + eu[:, None, None] * lead[None, None, :]
             + side * nu[:, None, None] * xs[None, :, None])
        v = (v0[:, None, None] + ev[:, None, None] * lead[None, None, :]
             + side * nv[:, None, None] * xs[None, :, None])
        mg = np.minimum(np.minimum(half - np.abs(u), v - inner), outer - v)
        out[i] = mg.max(axis=0)
    return out


def line_clearance(T, L, pts_xy, kind='fixo', value=0.0, exclude=120.0):
    """Menor distância (mm) de cada ponto do robô à borda da linha principal.

    Exclui trechos a menos de `exclude` mm de um cruzamento (lá a linha é cruzada
    de propósito). Positivo = o centro do sensor não passa sobre a linha.
    """
    track, arc = scenario_track(T, kind, value)
    alpha = A.pose(track, L, arc)
    s = track[:, 0]
    lo, hi = np.searchsorted(s, T['meta']['start']), np.searchsorted(s, T['meta']['end'])
    out = []
    for x, y in pts_xy:
        path = A.sensor_path(track[lo:hi], alpha[lo:hi], L, x, y)
        if len(T['crossings']):
            near = np.min(np.linalg.norm(path[:, None, :] - T['crossings'][None, :, :], axis=2), axis=1)
            path = path[near > exclude]
        d, _ = T['tree'].query(path)
        out.append(float(d.min() - A.LINE_HALF))
    return out
