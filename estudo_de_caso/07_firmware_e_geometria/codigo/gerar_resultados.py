"""Gera dados/resultados.json e as tabelas (Markdown) usadas no README desta pasta.

Baseado no EVA-RT, (c) EXOTIC TEAM MX, AGPL-3.0. Conferência geométrica apenas.
Uso: cd codigo && python3 gerar_resultados.py
"""
from pathlib import Path
import json
import math

import numpy as np
from scipy.spatial import cKDTree

import analise as A

OUT = Path(__file__).resolve().parent.parent / 'dados'
STEP = 0.25
X, Y = 69.5, 4.5                      # sensores laterais da v3 (iguais aos do EVA-RT)
L_V3 = A.L_from_holes(63.141)         # 107,1 mm: barra a 63,14 mm (furo da frente)
CONFIGS = [
    ('v3 · 63,14 mm entre furos', L_V3),
    ('EVA-RT original (L 100)', 100.0),
    ('v3 · L 85', 85.0),
    ('v3 · L 80', 80.0),
    ('v3 · L 70', 70.0),
]
WINDOWS = (10.0, 30.0, 60.0)          # janela = velocidade × MARK_TIMER_MS (mm)


def synth(pieces, ds=0.25):
    """Pista aberta: lista de (comprimento, curvatura)."""
    data = [[0., 0., 0., 0.]]
    for length, k in pieces:
        s0, x0, y0, p0 = data[-1]
        n = math.ceil(length / ds)
        for t in np.linspace(0, length, n + 1)[1:]:
            p = p0 + k * t
            x = x0 + (math.sin(p) - math.sin(p0)) / k if k else x0 + t * math.cos(p0)
            y = y0 + (-math.cos(p) + math.cos(p0)) / k if k else y0 + t * math.sin(p0)
            data.append([s0 + t, x, y, p])
    return np.array(data)


def hairpin_clearance(R, angle_deg, L, x=X, y=Y):
    """Curva à ESQUERDA entre duas retas: menor distância do sensor DIREITO à borda da linha."""
    track = synth([(600, 0), (math.radians(angle_deg) * R, 1 / R), (600, 0)])
    tree = cKDTree(track[:, 1:3])
    alpha = A.pose(track, L)
    path = A.sensor_path(track, alpha, L, -x, y)
    sel = (track[:, 0] > 300) & (track[:, 0] < track[-1, 0] - 200)
    d, _ = tree.query(path[sel])
    return float(d.min() - A.LINE_HALF)


def config_rows(tracks):
    rows = []
    for name, T in tracks.items():
        for label, L in CONFIGS:
            res = A.evaluate(T, L, (X,), (X,), Y)
            verdicts = {f'{w:g}': A.firmware_verdict(res, w) for w in WINDOWS}
            shifted = [A.evaluate(T, L, (X + d,), (X - d,), Y) for d in (-5.0, 5.0)]
            rows.append(dict(track=name, config=label, L=L, holes_front=A.holes_from_L(L),
                             left=f"{res['left_nominal']}/{res['left_total']}",
                             left_common=f"{res['left_common']}/{res['left_total']}",
                             left_shift5=min(r['left_nominal'] for r in shifted),
                             right=f"{res['right_nominal']}/2", missed=res['missed'],
                             min_margin_left=res['min_margin_left'],
                             start_read=res['start_read'], finish_read=res['finish_read'],
                             crossings=sum(e['what'] == 'cruzamento' for e in res['right_events']),
                             max_crossing_gap=verdicts['30']['max_crossing_gap'],
                             first_stop={k: v['first_stop'] for k, v in verdicts.items()},
                             false_stops={k: [(e['what'], round(e['s0'] - res['start_s']))
                                              for e in v['false_stops']] for k, v in verdicts.items()},
                             right_events=[(e['what'], e['mark'], round(e['s0'] - res['start_s']),
                                            round(e['left_edge_gap_mm'], 1)) for e in res['right_events']]))
    return rows


def sweep(tracks, Ls, Ys):
    grid = {}
    for L in Ls:
        alphas = {n: A.pose(T['track'], L) for n, T in tracks.items()}
        for y in Ys:
            cell = {}
            for n, T in tracks.items():
                r = A.evaluate(T, L, (X,), (X,), y, alpha=alphas[n])
                cell[n] = dict(nominal=r['left_nominal'], common=r['left_common'], total=r['left_total'],
                               right=r['right_nominal'], min_margin=r['min_margin_left'])
            grid[f'{L:g}|{y:g}'] = cell
    return grid


def drift(tracks, Ls, Es):
    """Sensibilidade a "abrir na curva": marcas de curva lidas e parada do firmware."""
    out = {}
    for n, T in tracks.items():
        for L in Ls:
            for e in Es:
                r = A.evaluate(T, L, (X,), (X,), Y, e100=e)
                v = A.firmware_verdict(r, 30.0)
                out[f'{n}|{L:g}|{e:g}'] = dict(nominal=r['left_nominal'], common=r['left_common'],
                                              total=r['left_total'], right=r['right_nominal'],
                                              stop_ok=bool(v['ok'] and not v['false_stops']),
                                              false_stops=len(v['false_stops']))
    return out


def main():
    tracks = A.load_tracks(STEP)
    names = list(tracks)
    rows = config_rows(tracks)
    tracks = A.load_tracks(0.5)          # varreduras em passo maior (só contagens)
    Ld, Es = [107.1, 100, 85, 70], [0, 10, 20, 30]
    dr = drift(tracks, Ld, Es)
    Ls = [60, 65, 70, 75, 80, 85, 90, 95, 100, 107.1]
    Ys = [4.5, 10, 15, 20, 25]
    grid = sweep(tracks, Ls, Ys)
    radii, angles = [100, 110, 120, 150], [90, 180]
    Lh = [70, 80, 85, 90, 95, 100, 107.1]
    hair = {f'{R}|{a}': {f'{L:g}': hairpin_clearance(R, a, L) for L in Lh} for R in radii for a in angles}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'resultados.json').write_text(json.dumps(dict(
        step_mm=STEP, sensor_x=X, sensor_y=Y, axle_y=A.AXLE, tracks=names,
        note='Conferência geométrica; não modela PID, óptica, derrapagem nem tempo.',
        configs=rows, sweep_L_Y=grid, drift_sensitivity=dr, hairpin_right_sensor_clearance_mm=hair),
        ensure_ascii=False, indent=1), encoding='utf8', newline='\n')

    md = []
    md.append('### Configurações × pistas (um QRE por lado em X = ±69,5; Y = 4,5)\n')
    md.append('| Pista | Configuração | L | Furos* | Curva (esq.) | Região comum | Com ±5 mm de erro | Partida/chegada | Cruzamentos vetados | Parada do firmware |')
    md.append('|---|---|---:|---:|---:|---:|---:|---:|---:|---|')
    for r in rows:
        stop = r['first_stop']['30']
        falses = r['false_stops']['30']
        verdict = 'na chegada' if stop == 'chegada' and not falses else (
            f"FALSA ({len(falses)}×; a 1ª sobre «{falses[0][0]}» a {falses[0][1] / 1000:.1f} m da partida)")
        md.append(f"| {r['track']} | {r['config']} | {r['L']:.1f} | {r['holes_front']:.1f} | {r['left']} | "
                  f"{r['left_common']} | {r['left_shift5']}/{r['left'].split('/')[1]} | {r['right']} | "
                  f"{r['crossings']} (defasagem ≤ {r['max_crossing_gap']:.1f} mm) | {verdict} |")
    md.append('\n\\* distância entre o furo da frente da base (y = 10,75) e o furo da barra V1.\n')
    for n in names:
        md.append(f'### Varredura, {n}: marcas de curva lidas (nominal / região comum) de {grid[f"{Ls[0]:g}|{Ys[0]:g}"][n]["total"]}\n')
        md.append('| L \\ Y do sensor | ' + ' | '.join(f'{y:g}' for y in Ys) + ' |')
        md.append('|---:|' + '---:|' * len(Ys))
        for L in Ls:
            md.append(f'| {L:g} | ' + ' | '.join(
                f"{grid[f'{L:g}|{y:g}'][n]['nominal']} / {grid[f'{L:g}|{y:g}'][n]['common']}" for y in Ys) + ' |')
        md.append('')
    md.append('### Sensibilidade a "abrir na curva" (centro da barra e mm para fora numa curva de raio 100)\n')
    md.append('Célula: marcas de curva lidas (nominal) · parada do firmware com janela de 30 mm.\n')
    md.append('| Pista | L | ' + ' | '.join(f'abre {e} mm' for e in Es) + ' |')
    md.append('|---|---:|' + '---|' * len(Es))
    for n in names:
        for L in Ld:
            cells = []
            for e in Es:
                c = dr[f'{n}|{L:g}|{e:g}']
                cells.append(f"{c['nominal']}/{c['total']} · " + ('chegada' if c['stop_ok'] else f"FALSA ({c['false_stops']}×)"))
            md.append(f'| {n} | {L:g} | ' + ' | '.join(cells) + ' |')
    md.append('')
    md.append('### Curva à esquerda: folga do sensor direito até a borda da linha (mm)\n')
    md.append('| Raio | Ângulo | ' + ' | '.join(f'L {L:g}' for L in Lh) + ' |')
    md.append('|---:|---:|' + '---:|' * len(Lh))
    for R in radii:
        for a in angles:
            md.append(f'| {R} | {a}° | ' + ' | '.join(f"{hair[f'{R}|{a}'][f'{L:g}']:.1f}" for L in Lh) + ' |')
    text = '\n'.join(md) + '\n'
    (OUT / 'tabelas.md').write_text(text, encoding='utf8', newline='\n')
    print(text)


if __name__ == '__main__':
    main()
