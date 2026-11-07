"""Sensores de marca (QRE nos bracos) x marcas laterais do TRIF, em retas e curvas.

Robo diferencial sem escorregamento: o centro do eixo das rodas anda na direcao do robo e a
barra de sensores fica L mm a frente dele. Tres modos de seguir a linha:
  ideal  - centro da barra sempre sobre a linha (robo como reboque);
  P      - giro proporcional ao erro lateral da barra (dpsi/ds = -k*e). O ganho e dado pelo erro
           que sobra numa curva R100 longa (5 mm = firme, 12 mm = solto/rapido): nas curvas a barra
           atrasa para fora e o robo entra "aberto", como num robo real;
  desvio - barra sempre 10 mm para um lado da linha (os dois lados).
Marca (regra do TRIF, Figuras 2 e 4 do regulamento RoboCore): 40 x 19 mm, a 40 mm da borda da
linha de 19 mm, ou seja de 49,5 a 89,5 mm do centro da linha, meio em 69,5. Curvatura: lado
esquerdo, em cada troca de curvatura; partida/chegada: lado direito, em reta. Como a posicao da
marca ao longo da pista em relacao ao ponto de troca nao e cotada, cada marca e testada centrada no
ponto de troca, terminando nele e comecando nele.

Saidas: v2/marcas_sim.json (todos os casos) e, com --figura, hardware/preview/marcas_trif_sim.jpg.
Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import json
import math
import sys

import numpy as np
import shapely
from shapely.geometry import LineString

import layout_placa as M

EIXO_Y = -22.59                 # eixo das rodas (medido no gearbox.stl / EVA_RT.eprj)
QRE = (69.5, 4.5)               # |x|, y dos QRE de marca (S0 esq. = curva, S1 dir. = partida/chegada)
LINHA = 19.0
M_IN, M_OUT, M_LEN = 49.5, 89.5, 19.0   # marca: de 49,5 a 89,5 do centro da linha, 19 ao longo
MEIO = (M_IN + M_OUT) / 2
DS = 0.5                        # passo (mm)
RETA_IN, RETA_OUT = 350.0, 350.0


# ------------------------------------------------------------------------------- pista
def pista(segs):
    """segs: ('reta', comp) | ('arco', R, graus, +1 esq./-1 dir.). Devolve pontos, angulo, curvatura
    e as abscissas das trocas de curvatura."""
    xs, ys, ph, ka = [0.0], [0.0], [math.pi / 2], [0.0]
    trocas = []
    k_ant = None
    for s in segs:
        if s[0] == 'reta':
            n, k = int(round(s[1] / DS)), 0.0
        else:
            _, R, ang, lado = s
            n, k = int(round(R * math.radians(ang) / DS)), lado / R
        if k_ant is not None and abs(k - k_ant) > 1e-12:
            trocas.append((len(xs) - 1) * DS)
        k_ant = k
        for _ in range(n):
            a = ph[-1] + k * DS / 2
            xs.append(xs[-1] + DS * math.cos(a)); ys.append(ys[-1] + DS * math.sin(a))
            ph.append(ph[-1] + k * DS); ka.append(k)
    return np.array(xs), np.array(ys), np.array(ph), np.array(ka), trocas


# ------------------------------------------------------------------------------- robo
def simular(P, ph, L, modo, e100=None, desvio=0.0):
    """Trajetoria do eixo (A), direcao (psi) e erro da barra, amostrada a cada DS ao longo da pista."""
    xs, ys = P
    n = len(xs)
    a_q = QRE[1] - EIXO_Y
    if modo == 'P':
        Ra = math.sqrt(100.0 ** 2 - L ** 2)
        k = 1.0 / (e100 * Ra)
    A = np.array([xs[0], ys[0]]) - L * np.array([math.cos(ph[0]), math.sin(ph[0])])
    psi = ph[0]
    out_A, out_psi, out_e = [], [], []
    i_ref = 0
    if modo in ('ideal', 'desvio'):
        for i in range(n):
            nrm = np.array([-math.sin(ph[i]), math.cos(ph[i])])
            B = np.array([xs[i], ys[i]]) + desvio * nrm
            d = B - A
            A = B - L * d / np.linalg.norm(d)
            psi = math.atan2(d[1], d[0])
            out_A.append(A.copy()); out_psi.append(psi); out_e.append(desvio)
    else:
        for i in range(n):
            f = np.array([math.cos(psi), math.sin(psi)])
            B = A + L * f
            j0, j1 = max(0, i_ref - 200), min(n, i_ref + 400)
            d2 = (xs[j0:j1] - B[0]) ** 2 + (ys[j0:j1] - B[1]) ** 2
            i_ref = j0 + int(np.argmin(d2))
            nrm = np.array([-math.sin(ph[i_ref]), math.cos(ph[i_ref])])
            e = float((B - np.array([xs[i_ref], ys[i_ref]])) @ nrm)
            out_A.append(A.copy()); out_psi.append(psi); out_e.append(e)
            psi += -k * e * DS
            A = A + DS * np.array([math.cos(psi), math.sin(psi)])
    A = np.array(out_A); psi = np.array(out_psi)
    f = np.stack([np.cos(psi), np.sin(psi)], 1)
    l = np.stack([-np.sin(psi), np.cos(psi)], 1)
    q_esq = A + a_q * f + QRE[0] * l
    q_dir = A + a_q * f - QRE[0] * l
    return A, psi, np.array(out_e), q_esq, q_dir


def cruzamento(Q, P, ph, s_m, lado, deslocamento, L):
    """Lateral do QRE (distancia ao centro da linha, do lado da marca) ao passar pelo meio da marca,
    a faixa lateral enquanto esta dentro dos 19 mm da marca e o trecho lido. So vale a passagem
    em que o robo esta de fato sobre a marca (a barra L mm a frente do eixo passa por ela antes)."""
    xs, ys = P
    s_c = s_m + deslocamento
    ic = int(round(s_c / DS))
    M0 = np.array([xs[ic], ys[ic]])
    t = np.array([math.cos(ph[ic]), math.sin(ph[ic])])
    n = np.array([-math.sin(ph[ic]), math.cos(ph[ic])]) * lado
    rel = Q - M0
    u, v = rel @ t, rel @ n
    esperado = ic + (L - (QRE[1] - EIXO_Y)) / DS       # passo em que o QRE chega a marca na reta
    cand = np.where(np.sign(u[:-1]) != np.sign(u[1:]))[0]
    cand = cand[np.abs(cand - esperado) < 150 / DS]
    if len(cand) == 0:
        return None
    k = int(cand[np.argmin(np.abs(cand - esperado))])
    w = u[k] / (u[k] - u[k + 1])
    v0 = float(v[k] + w * (v[k + 1] - v[k]))
    a = k
    while a > 0 and abs(u[a - 1]) <= M_LEN / 2:
        a -= 1
    b = k + 1
    while b < len(u) - 1 and abs(u[b + 1]) <= M_LEN / 2:
        b += 1
    vv = v[a:b + 1]
    lido = float(np.sum((vv >= M_IN) & (vv <= M_OUT)) * DS)
    return {'v0': round(v0, 2), 'vmin': round(float(vv.min()), 2), 'vmax': round(float(vv.max()), 2),
            'lido_mm': round(lido, 1)}


def casos():
    out = []
    for R in (100, 150, 200, 300, 400, 500):
        for ang in (45, 90, 180):
            for lado in (1, -1):
                out.append((f'R{R} {ang}° {"esq" if lado > 0 else "dir"}',
                            [('reta', RETA_IN), ('arco', R, ang, lado), ('reta', RETA_OUT)]))
    for R1, R2 in ((100, 300), (300, 100), (150, 500), (500, 150), (200, 400), (400, 200)):
        for lado in (1, -1):
            out.append((f'R{R1}→R{R2} {"esq" if lado > 0 else "dir"}',
                        [('reta', RETA_IN), ('arco', R1, 90, lado), ('arco', R2, 90, lado), ('reta', RETA_OUT)]))
    for R1, R2 in ((100, 100), (150, 150), (200, 200), (300, 300), (100, 300), (300, 100)):
        for lado in (1, -1):
            out.append((f'S R{R1}/R{R2} {"esq" if lado > 0 else "dir"}→',
                        [('reta', RETA_IN), ('arco', R1, 90, lado), ('arco', R2, 90, -lado), ('reta', RETA_OUT)]))
    return out


MODOS = [('ideal', dict(modo='ideal')),
         ('P firme (5 mm na R100)', dict(modo='P', e100=5.0)),
         ('P solto (12 mm na R100)', dict(modo='P', e100=12.0)),
         ('barra 10 mm à esq.', dict(modo='desvio', desvio=10.0)),
         ('barra 10 mm à dir.', dict(modo='desvio', desvio=-10.0))]


def rodar(Ls=(67.0, 70.0)):
    res = []
    for nome, segs in casos():
        xs, ys, ph, ka, trocas = pista(segs)
        linha = LineString(np.stack([xs, ys], 1))
        for L in Ls:
            for mnome, kw in MODOS:
                A, psi, e, qe, qd = simular((xs, ys), ph, L, **kw)
                # o QRE nunca pode ler a propria linha (fora as marcas)
                dmin = float(min(shapely.distance(shapely.points(qe[::4]), linha).min(),
                                 shapely.distance(shapely.points(qd[::4]), linha).min()))
                for s_m in trocas:
                    for desl, dnome in ((0.0, 'centrada'), (-M_LEN / 2, 'antes'), (M_LEN / 2, 'depois')):
                        c = cruzamento(qe, (xs, ys), ph, s_m, +1, desl, L)
                        if c:
                            c.update(pista=nome, L=L, modo=mnome, marca=dnome, s=round(s_m, 1),
                                     dist_linha_min=round(dmin, 1), erro_barra_max=round(float(np.abs(e).max()), 1))
                            res.append(c)
    # partida/chegada: reta logo depois de curvas fechadas (o robo ainda acomodando)
    for nome, segs, d in (('chegada 150 mm após R100 180°', [('reta', RETA_IN), ('arco', 100, 180, 1), ('reta', 600)], 150),
                          ('chegada 150 mm após R100 180° dir', [('reta', RETA_IN), ('arco', 100, 180, -1), ('reta', 600)], 150),
                          ('chegada 250 mm após S R100', [('reta', RETA_IN), ('arco', 100, 90, 1), ('arco', 100, 90, -1),
                                                           ('reta', 600)], 250)):
        xs, ys, ph, ka, trocas = pista(segs)
        for L in Ls:
            for mnome, kw in MODOS:
                A, psi, e, qe, qd = simular((xs, ys), ph, L, **kw)
                c = cruzamento(qd, (xs, ys), ph, trocas[-1] + d, -1, 0.0, L)
                if c:
                    c.update(pista=nome, L=L, modo=mnome, marca='partida/chegada', s=trocas[-1] + d)
                    res.append(c)
    return res


def resumo(res):
    out = {}
    for r in res:
        if r['marca'] == 'partida/chegada':
            chave = (r['L'], r['modo'], 'pc')
        else:
            chave = (r['L'], r['modo'], 'curva')
        o = out.setdefault(chave, {'n': 0, 'lidas': 0, 'folga4': 0, 'v0': [], 'faixa': [9e9, -9e9],
                                   'pior_meio': 0.0, 'dist_linha_min': 9e9})
        o['n'] += 1
        ok = M_IN <= r['v0'] <= M_OUT
        o['lidas'] += ok
        o['folga4'] += (M_IN + 4 <= r['vmin']) and (r['vmax'] <= M_OUT - 4)
        o['v0'].append(r['v0'])
        o['faixa'] = [min(o['faixa'][0], r['vmin']), max(o['faixa'][1], r['vmax'])]
        o['pior_meio'] = max(o['pior_meio'], abs(r['v0'] - MEIO))
        o['dist_linha_min'] = min(o['dist_linha_min'], r.get('dist_linha_min', 9e9))
    for o in out.values():
        v = np.array(o.pop('v0'))
        o['v0_min'], o['v0_max'], o['v0_med'] = round(float(v.min()), 1), round(float(v.max()), 1), round(float(v.mean()), 1)
    return out


if __name__ == '__main__' and '--figura' not in sys.argv:
    res = rodar()
    (M.HERE / 'v2' / 'marcas_sim.json').write_text(json.dumps(res, ensure_ascii=False), encoding='utf8')
    for k, o in sorted(resumo(res).items(), key=lambda kv: (kv[0][2], kv[0][0], kv[0][1])):
        print(k, o)


# ------------------------------------------------------------------------------- figura
def sensibilidade_y(ys=(-5.0, 0.0, 4.5, 10.0, 15.0), L=70.0):
    global QRE, MODOS
    guarda, gm = QRE, MODOS
    MODOS = [m for m in gm if m[0] in ('ideal', 'P firme (5 mm na R100)')]
    out = []
    try:
        for y in ys:
            QRE = (guarda[0], y)
            rs = [r for r in rodar(Ls=(L,)) if r['marca'] != 'partida/chegada']
            for m, _ in MODOS:
                v = [r['v0'] for r in rs if r['modo'] == m]
                out.append({'y': y, 'modo': m, 'min': min(v), 'max': max(v)})
    finally:
        QRE, MODOS = guarda, gm
    return out


def figura(res, sens):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as PPoly, Rectangle
    import matplotlib.patheffects as fx

    BG, PANEL, WHITE, MUTED, GRID = '#0f1317', '#151b20', '#f3f5ee', '#9aa7a0', '#2b3a35'
    LINE, MARK, OKC, WARN, BAD, BOARD = '#e9e6dc', '#d9d4c3', '#7ed6a0', '#f0c987', '#ff7b72', '#1f4a38'
    plt.rcParams.update({'font.size': 9, 'text.color': WHITE, 'axes.labelcolor': MUTED,
                         'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.edgecolor': GRID})
    fig = plt.figure(figsize=(16, 10.4), dpi=150, facecolor=BG)
    fig.text(0.035, 0.955, 'SENSORES DE MARCA × MARCAS DO TRIF — simulação em curvas', fontsize=17,
             fontweight='bold', color=WHITE)
    fig.text(0.035, 0.928, (f'QRE nos braços em (±{QRE[0]:.1f}; {QRE[1]:.1f}), eixo das rodas em y = {EIXO_Y:.2f} '
             f'({QRE[1] - EIXO_Y:.1f} mm à frente do eixo); barra L = 67 e 70 mm à frente do eixo; marca 40 × 19 mm de '
             f'{M_IN} a {M_OUT} mm do centro da linha (meio em {MEIO})').replace('.', ',') + '.', fontsize=9.5, color=MUTED)
    fig.text(0.035, 0.908, 'Pistas: curvas R100–R500 de 45°, 90° e 180°, curvas encadeadas (troca de raio) e em S, '
             'para os dois lados; cada marca testada centrada no ponto de troca, terminando nele e começando nele.',
             fontsize=9.5, color=MUTED)

    # ---- painel A: pista exemplo
    ax = fig.add_axes([0.035, 0.07, 0.40, 0.76], facecolor=BG)
    segs = [('reta', 220), ('arco', 150, 90, 1), ('reta', 300), ('arco', 100, 90, -1), ('reta', 260)]
    xs, ys, ph, ka, trocas = pista(segs)
    L = 70.0
    A, psi, e, qe, qd = simular((xs, ys), ph, L, modo='P', e100=5.0)
    linha = LineString(np.stack([xs, ys], 1))
    lp = linha.buffer(LINHA / 2, cap_style=2)
    ax.add_patch(PPoly(np.array(lp.exterior.coords), closed=True, fc=LINE, ec='none', zorder=2))
    contorno = np.array(M.OUTLINE.exterior.coords)
    for s_m in trocas:
        i = int(round(s_m / DS))
        t = np.array([math.cos(ph[i]), math.sin(ph[i])]); n = np.array([-t[1], t[0]])
        c0 = np.array([xs[i], ys[i]])
        q = [c0 + u * t + v * n for u, v in ((-9.5, M_IN), (9.5, M_IN), (9.5, M_OUT), (-9.5, M_OUT))]
        ax.add_patch(PPoly(np.array(q), closed=True, fc=MARK, ec='none', alpha=0.9, zorder=2))
        ax.plot(*np.array([c0 + 9.5 * n, c0 + 100 * n]).T, color=MUTED, lw=0.5, ls=':', zorder=1)
        # robo no instante em que o QRE esq. passa pelo meio da marca
        c = cruzamento(qe, (xs, ys), ph, s_m, +1, 0.0, L)
        rel = (qe - c0) @ t
        k = int(np.argmin(np.abs(rel) + 1e6 * (np.abs(np.arange(len(rel)) - (i + (L - QRE[1] + EIXO_Y) / DS)) > 300)))
        f = np.array([math.cos(psi[k]), math.sin(psi[k])]); l = np.array([-f[1], f[0]])
        W = A[k] + np.outer(contorno[:, 1] - EIXO_Y, f) - np.outer(contorno[:, 0], l)
        ax.add_patch(PPoly(W, closed=True, fc=BOARD, ec=WHITE, lw=0.7, alpha=0.6, zorder=4))
        bar = np.array([A[k] + L * f - 50 * l, A[k] + L * f + 50 * l])
        ax.plot(*bar.T, color='#6fb6ff', lw=2.4, solid_capstyle='butt', zorder=5)
        ax.plot(*qe[k], 'o', ms=5, color=OKC if M_IN + 4 <= c['v0'] <= M_OUT - 4 else WARN, zorder=6,
                mec=BG, mew=0.8)
        ax.plot(*qd[k], 'o', ms=4, color=MUTED, zorder=6, mec=BG, mew=0.8)
        tx = c0 + 112 * n
        t_ = ax.text(*tx, f"{c['v0']:.0f}".replace('.', ','), color=WHITE, fontsize=9, ha='center', va='center',
                     zorder=8, fontweight='bold')
        t_.set_path_effects([fx.withStroke(linewidth=2.5, foreground=BG)])
    ax.plot(qe[:, 0], qe[:, 1], color=OKC, lw=0.6, alpha=0.6, zorder=3)
    ax.plot(A[:, 0], A[:, 1], color=MUTED, lw=0.5, ls='--', alpha=0.6, zorder=3)
    ax.set_aspect('equal'); ax.axis('off')
    ax.text(0.0, 1.0, 'EXEMPLO (L = 70, controle P firme), da direita para a esquerda: R150 à esquerda, reta,\n'
            'R100 à direita. Robô no instante em que o QRE esquerdo passa pelo meio de cada marca de curvatura;\n'
            'número = distância do QRE ao centro da linha (mm). Verde = trajetória do QRE, tracejado = eixo das\n'
            'rodas, azul = barra de sensores.', transform=ax.transAxes, fontsize=8.5, color=MUTED, va='bottom')

    # ---- painel B: faixas por modo
    bx = fig.add_axes([0.63, 0.43, 0.27, 0.42], facecolor=PANEL)
    linhas = []
    for L in (67.0, 70.0):
        for m, _ in MODOS:
            rs = [r for r in res if r['L'] == L and r['modo'] == m and r['marca'] != 'partida/chegada']
            v = np.array([r['v0'] for r in rs])
            lidas = int(np.sum((v >= M_IN) & (v <= M_OUT)))
            folga = sum(1 for r in rs if r['vmin'] >= M_IN + 4 and r['vmax'] <= M_OUT - 4)
            linhas.append((f'L = {L:.0f} · {m}', v, lidas, folga, len(rs)))
    pcs = [r['v0'] for r in res if r['marca'] == 'partida/chegada' and r['modo'] in ('ideal', 'P firme (5 mm na R100)',
                                                                                        'P solto (12 mm na R100)')]
    linhas.append(('partida/chegada (reta após R100)', np.array(pcs), len(pcs), len(pcs), len(pcs)))
    n = len(linhas)
    bx.axvspan(M_IN, M_OUT, color=MARK, alpha=0.10)
    bx.axvspan(M_IN + 4, M_OUT - 4, color=OKC, alpha=0.07)
    bx.axvline(MEIO, color=WARN, lw=1)
    for j, (nome, v, lidas, folga, tot) in enumerate(linhas):
        yy = n - 1 - j
        cor = OKC if lidas == tot and folga >= 0.97 * tot else (WARN if lidas == tot else BAD)
        bx.plot([v.min(), v.max()], [yy, yy], color=cor, lw=7, solid_capstyle='round', alpha=0.9)
        bx.plot(np.percentile(v, [5, 95]), [yy, yy], color=BG, lw=1.2, alpha=0.6)
        bx.plot([np.median(v)], [yy], '|', color=BG, ms=9, mew=2)
        bx.text(-0.02, (yy + 0.8) / (n + 0.8), nome, ha='right', va='center', fontsize=8.5, color=WHITE,
                transform=bx.transAxes)
        bx.text(1.03, (yy + 0.8) / (n + 0.8), f'{lidas}/{tot}', ha='left', va='center', fontsize=8.5, color=WHITE,
                transform=bx.transAxes)
        bx.text(1.17, (yy + 0.8) / (n + 0.8), f'{folga}/{tot}', ha='left', va='center', fontsize=8.5, color=MUTED,
                transform=bx.transAxes)
    bx.text(1.03, 1.01, 'lidas', fontsize=8, color=MUTED, transform=bx.transAxes, va='bottom')
    bx.text(1.17, 1.01, 'folga 4 mm', fontsize=8, color=MUTED, transform=bx.transAxes, va='bottom')
    bx.text(M_IN, n - 0.35, 'borda', fontsize=8, color=MUTED, ha='center')
    bx.text(M_OUT, n - 0.35, 'borda', fontsize=8, color=MUTED, ha='center')
    bx.text(MEIO, n - 0.35, 'meio', fontsize=8, color=WARN, ha='center')
    bx.set_xlim(32, 100); bx.set_ylim(-0.8, n)
    bx.set_yticks([]); bx.set_xlabel('distância do QRE ao centro da linha ao passar pelo meio da marca (mm)')
    for s in bx.spines.values():
        s.set_color(GRID)
    fig.text(0.47, 0.875, f'Onde o QRE passa nas {len([r for r in res if r["L"] == 70 and r["modo"] == "ideal" and r["marca"] != "partida/chegada"])} '
             'passagens por marca de curvatura (barra = mín…máx, traço = mediana)', fontsize=10.5,
             color=WHITE, fontweight='bold')

    # ---- painel C: sensibilidade a posicao do QRE no braco
    cx = fig.add_axes([0.63, 0.115, 0.27, 0.2], facecolor=PANEL)
    cx.axvspan(0.8, 8.2, color=WHITE, alpha=0.06)
    cx.text(0.8 + 0.2, 45.5, 'largura do braço', fontsize=7.5, color=MUTED)
    for m, cor in (('ideal', WARN), ('P firme (5 mm na R100)', OKC)):
        ss = [s for s in sens if s['modo'] == m]
        yv = [s['y'] for s in ss]
        cx.fill_between(yv, [s['min'] for s in ss], [s['max'] for s in ss], color=cor, alpha=0.25, lw=0)
        cx.plot(yv, [s['min'] for s in ss], color=cor, lw=1.2, label=m)
        cx.plot(yv, [s['max'] for s in ss], color=cor, lw=1.2)
    cx.axhline(MEIO, color=WARN, lw=0.8, ls=':'); cx.axhline(M_IN, color=MARK, lw=0.8); cx.axhline(M_OUT, color=MARK, lw=0.8)
    cx.axvline(QRE[1], color=WHITE, lw=0.8, ls='--')
    cx.text(QRE[1] + 0.3, M_OUT - 2, 'atual', fontsize=8, color=WHITE, va='top')
    cx.set_xlabel('y do centro do QRE (mm)'); cx.set_ylabel('mín…máx (mm)')
    cx.set_ylim(44, 94)
    cx.legend(loc='upper left', bbox_to_anchor=(1.01, 1.0), fontsize=7.5, frameon=False)
    fig.text(0.47, 0.335, 'E se o QRE estivesse em outro y? (L = 70; o braço só deixa ±1,5 mm)', fontsize=10.5,
             color=WHITE, fontweight='bold')
    fig.text(0.035, 0.03, 'Modelo cinemático (sem escorregamento). "P" = giro proporcional ao erro da barra; o ganho é dado '
             'pelo erro que sobra numa R100 longa (firme 5 mm, solto 12 mm: mais rápido). "Barra 10 mm" = desvio fixo '
             'para um lado em toda a pista (caso pessimista). Código: ferramentas/preview/marcas_sim.py.   '
             'Baseado no EVA-RT © EXOTIC TEAM MX — AGPL-3.0.', fontsize=7.8, color=MUTED)
    out = M.OUTPUT / 'marcas_trif_sim.jpg'
    fig.savefig(out, facecolor=BG, pil_kwargs={'quality': 90})
    print(out)


if __name__ == '__main__' and '--figura' in sys.argv:
    res = json.loads((M.HERE / 'v2' / 'marcas_sim.json').read_text(encoding='utf8'))
    figura(res, sensibilidade_y())
