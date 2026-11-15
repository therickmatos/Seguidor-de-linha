"""Emula Marks.ino (EVA-RT 1.2.2) com cada par de QRE ligado em A5 (esquerdo) e A6 (direito).

Baseado no EVA-RT, (c) EXOTIC TEAM MX, AGPL-3.0. Usa a emulação do estudo 07
(analise.white_events / firmware_verdict) com os sensores da asa de gaivota.
Pergunta: qual par deve ir nas entradas analógicas para o firmware 1.2.2, sem
mudanças, parar na chegada e não parar em outro lugar?
"""
from pathlib import Path
import json
import numpy as np

import margens as M
from margens import A
import contorno as C

OUT = Path(__file__).resolve().parent.parent / 'dados'
PAIRS = {'externos E2/D2': C.SENSOR_OUT, 'internos E1/D1': C.SENSOR_IN}
SCEN = [('fixo', 0.0), ('fixo', -3.0), ('fixo', 3.0), ('abre', 10.0), ('abre', 20.0), ('abre', 30.0)]
WINDOWS = (10.0, 30.0, 60.0)     # velocidade × MARK_TIMER_MS (30 ms): ~0,3 / 1 / 2 m/s


def run(T, L, xy, kind, val):
    track, arc = M.scenario_track(T, kind, val)
    alpha = A.pose(track, L, arc)
    s = track[:, 0]
    x, y = xy
    left = A.sensor_path(track, alpha, L, x, y)
    right = A.sensor_path(track, alpha, L, -x, y)
    meta = T['meta']
    lo, hi = np.searchsorted(s, meta['start']), np.searchsorted(s, meta['end'])
    ev_left, _ = A.white_events(T, left, s, lo, hi, 3.0)
    ev_right, _ = A.white_events(T, right, s, lo, hi, 3.0)
    rises = np.array([e['s0'] for e in ev_left])
    res = dict(right_events=[dict(**e, left_edge_gap_mm=float(np.abs(rises - e['s0']).min()) if len(rises) else 1e9)
                             for e in ev_right])
    return {f'{w:g}': A.firmware_verdict(res, w) for w in WINDOWS}


def main():
    tracks = A.load_tracks(0.5)
    rows = []
    for holes in (63.141, 65.0):
        L = A.L_from_holes(holes)
        for pair, xy in PAIRS.items():
            for name, T in tracks.items():
                for kind, val in SCEN:
                    v = run(T, L, xy, kind, val)
                    row = dict(furos=holes, par=pair, pista=name, cenario=f'{kind} {val:g}',
                               **{f'janela_{w}': dict(ok=r['ok'], primeira_parada=r['first_stop'],
                                                       falsas=[e['what'] for e in r['false_stops']])
                                  for w, r in v.items()})
                    rows.append(row)
                    print(holes, pair, name, kind, val,
                          ' '.join(f"{w}:{'ok' if r['ok'] and not r['false_stops'] else 'FALHA(' + str(r['first_stop']) + ',' + str(len(r['false_stops'])) + ')'}"
                                   for w, r in v.items()), flush=True)
    (OUT / 'firmware_pares.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding='utf8', newline='\n')


if __name__ == '__main__':
    main()
