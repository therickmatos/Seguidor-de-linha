"""Resumo das larguras das redes de potência: trechos longos (> 2,2 mm) e trechos curtos estreitos (junto aos pinos).
Uso: python3 resumo_larguras.py <placa.epro>"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verifica_placa as V, corrente as C
M = 0.0254
rows, fps, outer = V.board(sys.argv[1])
def x(r): return ((r[5] * M + r[7] * M) / 2, (r[6] * M + r[8] * M) / 2)
for net in ('OUT_A1', 'OUT_A2', 'OUT_B1', 'OUT_B2', 'VBAT', 'OUT_C'):
    segs = [(math.hypot(r[7] - r[5], r[8] - r[6]) * M, r[9] * M, r) for r in rows if r[0] == 'LINE' and r[3] == net and r[9] * M >= 0.35]
    if net == 'VBAT':   # só o caminho de potência (fora do ramo da medição e do grupo C1/C3/78M05)
        segs = [s for s in segs if s[1] >= 2.0 or (s[0] <= 2.2 and abs(x(s[2])[0]) > 21 and x(s[2])[1] < -5)]
    longos = [s for s in segs if s[0] > 2.2]
    curtos = [s for s in segs if s[0] <= 2.2 and s[1] < 2.1]
    if not longos: continue
    wmin = min(s[1] for s in longos); tot = sum(s[0] for s in longos)
    print(f'{net:7s} trechos longos: {tot:5.1f} mm, menor largura {wmin:.2f} mm → {C.ipc_amp(wmin, 20):.1f} A (ΔT 20 °C) / {C.ipc_amp(wmin, 30):.1f} A (ΔT 30 °C)')
    if curtos:
        print(f'        trechos curtos < 2,1 mm: {len(curtos)}, até {max(s[0] for s in curtos):.1f} mm de comprimento, larguras {min(s[1] for s in curtos):.2f}–{max(s[1] for s in curtos):.2f} mm')
vb = [r for r in rows if r[0] == 'VIA' and r[3] == 'VBAT' and r[8] * M >= 1.5]
print('vias de VBAT ≥ 1,5 mm:', [(round(r[5] * M, 2), round(r[6] * M, 2)) for r in vb])
