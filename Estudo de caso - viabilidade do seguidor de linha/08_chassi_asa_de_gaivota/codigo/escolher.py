"""Escolhe (x interno, x externo, y) dos dois QRE de cada lado a partir de ../dados/grade_margens.npz."""
from pathlib import Path
import itertools
import json
import sys
import numpy as np

DADOS = Path(__file__).resolve().parent.parent / 'dados'
Z = np.load(DADOS / 'grade_margens.npz')
XS, YS = Z['xs'], Z['ys']
TRIF = ('TRIF 2025', 'TRIF 2024')
ALL = TRIF + ('EVA-RT teste',)
HOLES = ('61', '63.141', '65')
FIXED = ('-5', '-3', '0', '3', '5')
OPEN = ('10', '20', '30')


def keys(box, tracks, holes=HOLES, fixed=FIXED, opened=OPEN):
    out = []
    for t, h in itertools.product(tracks, holes):
        out += [f'{box}|{t}|{h}|fixo|{e}' for e in fixed]
        out += [f'{box}|{t}|{h}|abre|{e}' for e in opened]
    return out


def stack(ks, yi):
    return np.concatenate([Z[k][:, :, yi] for k in ks], axis=0)   # (marcas×cenários, nx)


def pair_worst(G):
    """Pior margem (sobre linhas de G) do melhor dos dois sensores, para todo par (i, j)."""
    best = np.full((G.shape[1], G.shape[1]), np.inf, dtype=np.float32)
    for row in G:
        np.minimum(best, np.maximum(row[:, None], row[None, :]), out=best)
    return best


def evaluate(x1, x2, y, tracks=TRIF, holes=HOLES, fixed=FIXED, opened=OPEN):
    i1, i2, yi = (int(np.argmin(abs(XS - x1))), int(np.argmin(abs(XS - x2))), int(np.argmin(abs(YS - y))))
    res = {}
    for box in ('nom', 'com'):
        G = stack(keys(box, tracks, holes, fixed, opened), yi)
        res[box] = float(np.maximum(G[:, i1], G[:, i2]).min())
    return res


def table(tracks, x2max, gapmin=10.0, x1min=50.0):
    rows = []
    ii = np.arange(len(XS))
    ok = (XS[None, :] - XS[:, None] >= gapmin) & (XS[:, None] >= x1min) & (XS[None, :] <= x2max)
    for yi, y in enumerate(YS):
        Gn = stack(keys('nom', tracks), yi)
        Gc = stack(keys('com', tracks), yi)
        wn, wc = pair_worst(Gn), pair_worst(Gc)
        score = np.where(ok, np.minimum(wn, wc + 3.5), -np.inf)   # região comum é 3,5 mm mais estreita por dentro
        i, j = np.unravel_index(np.argmax(score), score.shape)
        rows.append(dict(y=float(y), x1=float(XS[i]), x2=float(XS[j]), nom=float(wn[i, j]), com=float(wc[i, j])))
    return rows


def margin(x1, y1, x2, y2, fixed, opened, box='nom', tracks=TRIF, holes=('63.141', '65')):
    """Pior margem (marcas × cenários) com o sensor interno em (x1, y1) e o externo em (x2, y2)."""
    i1, i2 = int(np.argmin(abs(XS - x1))), int(np.argmin(abs(XS - x2)))
    A = stack(keys(box, tracks, holes, fixed, opened), int(np.argmin(abs(YS - y1))))[:, i1]
    B = stack(keys(box, tracks, holes, fixed, opened), int(np.argmin(abs(YS - y2))))[:, i2]
    return float(np.maximum(A, B).min())


def main():
    """Tabela da escolha (../dados/escolha.md): TRIF 2024 + 2025, 63,14 e 65 mm entre furos."""
    S1 = (('0',), ('10', '20', '30'))            # ideal + abre na curva
    S2 = (('-3', '0', '3'), ('10', '20', '30'))   # idem + desvio fixo de ±3 mm
    md = ['# Escolha das posições (gerado por `codigo/escolher.py`)', '',
          'Pior margem (mm) sobre as marcas do TRIF 2024 e 2025, 63,14 e 65 mm entre furos.',
          'Célula: ideal+abre / com ±3 mm / região comum (ideal+abre). Linhas: sensor interno; colunas: externo.', '']
    outs = [(80.0, 14.0), (80.0, 20.0), (82.0, 14.0), (82.0, 20.0)]
    md.append('| Interno (x; y) | ' + ' | '.join(f'externo ({x:g}; {y:g})' for x, y in outs) + ' |')
    md.append('|---|' + '---|' * len(outs))
    for x1 in (50.0, 50.5, 52.0, 55.0):
        for y1 in (4.0, 8.0, 12.0, 14.0, 16.0, 20.0):
            cells = []
            for x2, y2 in outs:
                a = margin(x1, y1, x2, y2, *S1)
                b = margin(x1, y1, x2, y2, *S2)
                c = margin(x1, y1, x2, y2, *S1, box='com')
                cells.append(f'{a:.1f} / {b:.1f} / {c:.1f}')
            md.append(f'| ({x1:g}; {y1:g}) | ' + ' | '.join(cells) + ' |')
            print(md[-1], flush=True)
    (DADOS / 'escolha.md').write_text('\n'.join(md) + '\n', encoding='utf8', newline='\n')


if __name__ == '__main__':
    main()
