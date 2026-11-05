import io, contextlib, collections, numpy as np
import build_pos as B, fixos, place_lib as L
with contextlib.redirect_stdout(io.StringIO()):
    fixos.primeiro(B.PLACED, B.colocar)
    B.satelite('SW2', 26.9, -20.5, 2.5, [90, 0]); B.satelite('SW0', -26.9, -20.5, 0.0, [90])
    B.satelite('J1', -28.6, 0.0, 3.0, [90, 0])
    B.satelite('C8', *B.pad_xy('M3', 1), 4.0, [0, 90, 180, 270], alvo=[B.pad_xy('M3', 1)], modo='min')
    B.satelite('Q1', *B.pad_xy('M3', 2), 6.0, [0, 90, 180, 270], lado='BOTTOM', alvo=[B.pad_xy('M3', 2)], modo='min')
    B.satelite('D1', 27.0, 3.0, 4.0, [0, 90, 180, 270])
    B.satelite('X1', -7.0, -27.9, 0.0, [0, 90])
P = B.PLACED
cu = P['U1']['court']; print('U1 cortesia x[%.2f,%.2f] y[%.2f,%.2f]' % (cu[:,0].min(), cu[:,0].max(), cu[:,1].min(), cu[:,1].max()))
print('X1 pos', round(P['X1']['x'],2), round(P['X1']['y'],2), P['X1']['rot'])
cnt = collections.Counter(); ok = []
for rot in (0, 45, 90, 135, 180, 225, 270, 315):
    for x in np.arange(-6.5, -1.0, 0.25):
        for y in np.arange(-29.5, -24.0, 0.25):
            c = L.comp('C9', round(float(x),2), round(float(y),2), rot)
            e, a = L.avaliar(c, P)
            if not e: ok.append((round(float(x),2), round(float(y),2), rot))
            for m in e: cnt[m[:45]] += 1
print('C9 validos:', len(ok), ok[:8])
print('motivos:', cnt.most_common(6))
