"""Verificação final das posições escolhidas (passo 0,25 mm) e comparação com v3 e chassi baixo.

Baseado no EVA-RT, (c) EXOTIC TEAM MX, AGPL-3.0. Conferência geométrica: não modela
PID, óptica, derrapagem nem tempo. Gera ../dados/resultados.json e ../dados/tabelas.md.
"""
from pathlib import Path
import json
import math
import sys

import numpy as np
from scipy.spatial import cKDTree

import margens as M
from margens import A
import contorno as C

sys.path.insert(0, str(Path(A.__file__).resolve().parent))
import gerar_resultados as GR  # noqa: E402  (pista sintética do estudo 07)

OUT = Path(__file__).resolve().parent.parent / 'dados'
STEP = 0.25

GULL = [C.SENSOR_IN, C.SENSOR_OUT]
CONFIGS = [  # nome, furos (base → barra), sensores [(x, y), ...] por lado (espelhados)
    ('Asa de gaivota · 63,14 mm', 63.141, GULL),
    ('Asa de gaivota · 65 mm', 65.0, GULL),
    ('Asa de gaivota · 61 mm (referência)', 61.0, GULL),
    ('Chassi baixo (esboço) · 63,14 mm', 63.141, [(52.25, 20.0), (77.75, 20.0)]),
    ('v3 atual · 63,14 mm', 63.141, [(69.5, 4.5)]),
]
SCENARIOS = [('fixo', 0.0), ('fixo', -3.0), ('fixo', 3.0), ('fixo', -5.0), ('fixo', 5.0),
             ('abre', 10.0), ('abre', 20.0), ('abre', 30.0)]


def scen_label(kind, v):
    return 'ideal' if (kind, v) == ('fixo', 0.0) else (f'desvio {v:+g} mm' if kind == 'fixo' else f'abre {v:g} mm')


def run_config(T, holes, sensors, kind, val):
    L = A.L_from_holes(holes)
    track, arc = M.scenario_track(T, kind, val)
    alpha = A.pose(track, L, arc)
    s = track[:, 0]
    paths = {1: [A.sensor_path(track, alpha, L, x, y) for x, y in sensors],
             -1: [A.sensor_path(track, alpha, L, -x, y) for x, y in sensors]}
    nom = A.marks_read(T, paths, s, A.MARK)
    com = A.marks_read(T, paths, s, A.COMMON)
    # folga até a linha (fora dos cruzamentos), por sensor (interno/externo), pior dos dois lados
    lo, hi = np.searchsorted(s, T['meta']['start']), np.searchsorted(s, T['meta']['end'])
    clear = []
    for k in range(len(sensors)):
        worst = 1e9
        for side in (1, -1):
            p = paths[side][k][lo:hi]
            if len(T['crossings']):
                near = np.min(np.linalg.norm(p[:, None, :] - T['crossings'][None], axis=2), axis=1)
                p = p[near > 120.0]
            worst = min(worst, float(T['tree'].query(p)[0].min() - A.LINE_HALF))
        clear.append(worst)
    left = [m for m in nom if m['side'] > 0]
    right = [m for m in nom if m['side'] < 0]
    return dict(L=L, total=len(nom), nominal=sum(m['hit'] for m in nom), common=sum(m['hit'] for m in com),
                left=f"{sum(m['hit'] for m in left)}/{len(left)}", right=f"{sum(m['hit'] for m in right)}/{len(right)}",
                missed=[m['label'] for m in nom if not m['hit']],
                min_margin=min(m['margin'] for m in nom), min_margin_common=min(m['margin'] for m in com),
                worst_mark=min(nom, key=lambda m: m['margin'])['label'],
                line_clearance=clear)


def hairpin(R, deg, L, sensors):
    """Curva entre retas: menor folga de cada sensor (dos dois lados) até a borda da linha."""
    track = GR.synth([(600, 0), (math.radians(deg) * R, 1 / R), (600, 0)])
    tree = cKDTree(track[:, 1:3])
    alpha = A.pose(track, L)
    sel = (track[:, 0] > 300) & (track[:, 0] < track[-1, 0] - 200)
    out = []
    for x, y in sensors:
        out.append(min(float(tree.query(A.sensor_path(track, alpha, L, sx * x, y)[sel])[0].min() - A.LINE_HALF)
                       for sx in (1, -1)))
    return out


def main():
    tracks = A.load_tracks(STEP)
    rows = []
    for name, T in tracks.items():
        for label, holes, sensors in CONFIGS:
            for kind, val in SCENARIOS:
                r = run_config(T, holes, sensors, kind, val)
                rows.append(dict(track=name, config=label, holes=holes, sensors=sensors,
                                 scenario=scen_label(kind, val), **r))
                print(f"{name:12s} {label:36s} {scen_label(kind, val):15s} {r['nominal']}/{r['total']} "
                      f"comum {r['common']} margem {r['min_margin']:5.1f} ({r['worst_mark']}) "
                      f"linha {' '.join(f'{c:5.1f}' for c in r['line_clearance'])}", flush=True)
    hp = {}
    for label, holes, sensors in CONFIGS:
        L = A.L_from_holes(holes)
        hp[label] = {f'R{R} {d}°': hairpin(R, d, L, sensors) for R in (100, 120, 150) for d in (90, 180)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'resultados.json').write_text(json.dumps(dict(
        step_mm=STEP, axle_y=A.AXLE, sensores_asa=dict(interno=C.SENSOR_IN, externo=C.SENSOR_OUT),
        nota='Conferência geométrica: centro do QRE × retângulo da marca. Não modela PID, óptica, derrapagem nem tempo.',
        resultados=rows, grampos_folga_linha_mm=hp), ensure_ascii=False, indent=1), encoding='utf8', newline='\n')
    write_tables(rows, hp, list(tracks))


def write_tables(rows, hp, names):
    md = ['# Tabelas geradas por `codigo/verificar.py`', '',
          'Margem = quanto o centro do QRE entra na fita, na pior marca (mm; negativo = não passa). '
          '"Comum" = mesma conta na região que vale para qualquer fita dentro da tolerância do regulamento (±1 mm na linha, ±3 mm na marca).', '']
    for name in names:
        md += [f'## {name}', '', '| Configuração | Cenário | Marcas (esq. / dir.) | Região comum | Margem mín. | Margem comum | Pior marca | Folga até a linha (int. / ext.) |',
               '|---|---|---:|---:|---:|---:|---|---|']
        for r in rows:
            if r['track'] != name:
                continue
            clear = ' / '.join(f'{c:.1f}' for c in r['line_clearance'])
            md.append(f"| {r['config']} | {r['scenario']} | {r['nominal']}/{r['total']} ({r['left']} · {r['right']}) | "
                      f"{r['common']}/{r['total']} | {r['min_margin']:.1f} | {r['min_margin_common']:.1f} | {r['worst_mark']} | {clear} |")
        md.append('')
    md += ['## Curvas isoladas entre retas: folga até a borda da linha (mm), pior dos dois lados', '',
           'Sensores na ordem interno / externo. Negativo = o centro do sensor passa sobre a linha principal.', '',
           '| Configuração | ' + ' | '.join(next(iter(hp.values())).keys()) + ' |',
           '|---|' + '---:|' * len(next(iter(hp.values())))]
    for label, cells in hp.items():
        md.append(f'| {label} | ' + ' | '.join(' / '.join(f'{c:.1f}' for c in v) for v in cells.values()) + ' |')
    (OUT / 'tabelas.md').write_text('\n'.join(md) + '\n', encoding='utf8', newline='\n')


if __name__ == '__main__':
    main()
