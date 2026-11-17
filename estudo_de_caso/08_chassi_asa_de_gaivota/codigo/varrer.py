"""Varredura: margens de todas as marcas para uma grade de (x, y) de sensor, em vários cenários.
Grava ../dados/grade_margens.npz (reutilizado por escolher.py)."""
from pathlib import Path
import numpy as np
import margens as M
from margens import A

OUT = Path(__file__).resolve().parent.parent / 'dados'
XS = np.arange(44.0, 92.01, 0.5)
YS = np.arange(-4.0, 26.01, 1.0)
HOLES = (61.0, 63.141, 65.0)
SCEN = [('fixo', e) for e in (-5.0, -3.0, 0.0, 3.0, 5.0)] + [('abre', e) for e in (10.0, 20.0, 30.0)]


def main():
    tracks = A.load_tracks(0.5)
    data = {}
    for name, T in tracks.items():
        side = np.array([m['side'] for m in T['marks']])
        data[f'side|{name}'] = side
        for h in HOLES:
            L = A.L_from_holes(h)
            for kind, val in SCEN:
                for bname, box in (('nom', A.MARK), ('com', A.COMMON)):
                    g = M.margin_grid(T, L, XS, YS, kind, val, box)
                    data[f'{bname}|{name}|{h:g}|{kind}|{val:g}'] = g.astype(np.float32)
                print(name, h, kind, val, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / 'grade_margens.npz', xs=XS, ys=YS, **data)


if __name__ == '__main__':
    main()
