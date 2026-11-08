"""Roteador de grade (Dijkstra, 8 direcoes, duas faces) para fechar ligacoes que sobram do FreeRouting
e para ligar pads de GND ao GND principal (08/11/2026).

A folga e garantida por construcao: o cobre de outras redes e inflado de (folga + meia largura +
erro da grade) e o centro da via precisa ficar a (folga + raio da via + erro) de tudo. Com `macio`,
trilhas de sinal de outras redes viram obstaculos caros em vez de proibidos; o resultado diz quais
trilhas teriam de ser arrancadas.

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import heapq
import math

import numpy as np
import shapely
from shapely import contains_xy
from shapely.ops import unary_union

import easyeda_cobre as C

FOLGA = 0.2


def _mascara(geom, X, Y):
    if geom is None or geom.is_empty:
        return np.zeros(X.shape, bool)
    shapely.prepare(geom)
    return contains_xy(geom, X, Y)


def rotear(placa, objs, net, origem, alvo, largura, via=(0.6, 0.3), margem=4.0, passo=None,
           custo_camada=None, custo_via=60, macio=None, sem_via_em_pad=True, janela=None, pen=400.0):
    """origem/alvo: {camada: geometria} do cobre (da rede) de onde sai e aonde chega.
    custo_camada: {camada: fator}. macio: conjunto de redes cujas trilhas podem ser cruzadas (custo alto).
    Devolve dict(trilhas, vias, cruzadas) ou None."""
    custo_camada = custo_camada or {C.TOP: 1.0, C.BOT: 1.0}
    geoms = [g for g in list(origem.values()) + list(alvo.values()) if g is not None and not g.is_empty]
    if janela is None:
        x0, y0, x1, y1 = unary_union(geoms).bounds
        x0, y0, x1, y1 = x0 - margem, y0 - margem, x1 + margem, y1 + margem
    else:
        x0, y0, x1, y1 = janela
    if passo is None:
        passo = 0.05 if (x1 - x0) * (y1 - y0) < 500 else 0.1
    erro = passo * 0.75
    xs = np.arange(x0, x1 + passo / 2, passo)
    ys = np.arange(y0, y1 + passo / 2, passo)
    X, Y = np.meshgrid(xs, ys)
    win = shapely.box(x0 - 2, y0 - 2, x1 + 2, y1 + 2)
    rv = via[0] / 2
    infl = FOLGA + largura / 2 + erro
    area = placa.borda.buffer(-(C.FOLGA_BORDA + largura / 2 + erro))
    va = placa.borda.buffer(-(C.FOLGA_BORDA + rv + erro))
    if placa.npth:
        furos = unary_union(placa.npth)
        area = area.difference(furos.buffer(C.FOLGA_BORDA + largura / 2 + erro))
        va = va.difference(furos.buffer(C.FOLGA_BORDA + rv + erro))
    livre, caro, via_ok = {}, {}, None
    todos_pads = unary_union([o['geom'] for o in objs if o['tipo'] == 'pad' and o['geom'].intersects(win)] or [shapely.Point(1e6, 1e6)])
    mapa_macio = {}
    for lay in (C.TOP, C.BOT):
        duros = [o['geom'] for o in objs if lay in o['layers'] and o['net'] != net and o['geom'].intersects(win)
                 and not (macio and o['tipo'] == 'trilha' and o['net'] in macio)]
        moles = [o for o in objs if lay in o['layers'] and o['net'] != net and o['geom'].intersects(win)
                 and macio and o['tipo'] == 'trilha' and o['net'] in macio]
        g = area.intersection(win)
        if duros:
            g = g.difference(unary_union(duros).buffer(infl, quad_segs=6))
        livre[lay] = _mascara(g, X, Y)
        caro[lay] = np.zeros(X.shape, bool)
        if moles:
            gm = unary_union([o['geom'] for o in moles]).buffer(infl, quad_segs=6)
            caro[lay] = _mascara(gm, X, Y)
            mapa_macio[lay] = moles
        vg = va.intersection(win)
        if duros:
            vg = vg.difference(unary_union(duros).buffer(rv + FOLGA + erro, quad_segs=6))
        vm = _mascara(vg, X, Y)
        if moles:
            vm &= ~_mascara(unary_union([o['geom'] for o in moles]).buffer(rv + FOLGA + erro, quad_segs=6), X, Y)
        via_ok = vm if via_ok is None else (via_ok & vm)
    if sem_via_em_pad:
        # o EasyEDA acusa via encostada em pad SMD mesmo da mesma rede: borda da via a >= 0,2 de qualquer pad
        via_ok &= ~_mascara(todos_pads.buffer(rv + FOLGA + erro), X, Y)
    # furos: anel a >= 0,15 mm de qualquer via existente e furo a >= 0,35 mm de furo de pad passante
    furos = [o['geom'].buffer(rv + 0.15) for o in objs if o['tipo'] == 'via' and o['geom'].intersects(win)]
    furos += [shapely.Point(*o['obj']['centro']).buffer(o['obj']['furo'] / 2 + via[1] / 2 + 0.35)
              for o in objs if o['tipo'] == 'pad' and o['obj'].get('furo') and o['geom'].intersects(win)]
    if furos:
        via_ok &= ~_mascara(unary_union(furos), X, Y)
    ini, meta = {}, {}
    for lay in (C.TOP, C.BOT):
        o = origem.get(lay)
        a = alvo.get(lay)
        ini[lay] = _mascara(o, X, Y) & livre[lay] if o is not None else np.zeros(X.shape, bool)
        a = a.buffer(-0.02) if a is not None and not a.is_empty else None
        meta[lay] = _mascara(a, X, Y) & livre[lay] if a is not None else np.zeros(X.shape, bool)
    ny, nx = X.shape
    dist = {}
    fila = []
    for lay in (C.TOP, C.BOT):
        for iy, ix in zip(*np.nonzero(ini[lay])):
            dist[(lay, iy, ix)] = 0.0
            fila.append((0.0, lay, int(iy), int(ix)))
    heapq.heapify(fila)
    if not fila:
        return None
    viz = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
           (-1, -1, 1.4142), (-1, 1, 1.4142), (1, -1, 1.4142), (1, 1, 1.4142)]
    pai = {}
    fim = None
    PEN = pen
    while fila:
        d, lay, iy, ix = heapq.heappop(fila)
        if d > dist.get((lay, iy, ix), 1e18):
            continue
        if meta[lay][iy, ix]:
            fim = (lay, iy, ix)
            break
        L, CC, cl = livre[lay], caro[lay], custo_camada[lay]
        for dy, dx, c in viz:
            jy, jx = iy + dy, ix + dx
            if not (0 <= jy < ny and 0 <= jx < nx) or not L[jy, jx]:
                continue
            if dx and dy and not (L[iy, jx] and L[jy, ix]):
                continue
            nd = d + c * cl + (PEN if CC[jy, jx] and not CC[iy, ix] else 0.0)
            k = (lay, jy, jx)
            if nd < dist.get(k, 1e18):
                dist[k] = nd
                pai[k] = (lay, iy, ix)
                heapq.heappush(fila, (nd, lay, jy, jx))
        if via_ok[iy, ix]:
            o = C.BOT if lay == C.TOP else C.TOP
            if livre[o][iy, ix]:
                nd = d + custo_via
                k = (o, iy, ix)
                if nd < dist.get(k, 1e18):
                    dist[k] = nd
                    pai[k] = (lay, iy, ix)
                    heapq.heappush(fila, (nd, o, iy, ix))
    if fim is None:
        return None
    cam = [fim]
    while cam[-1] in pai:
        cam.append(pai[cam[-1]])
    cam.reverse()
    trechos, vias = [], []
    atual = [cam[0]]
    for a, b in zip(cam, cam[1:]):
        if a[0] != b[0]:
            trechos.append((a[0], atual))
            vias.append((float(xs[a[2]]), float(ys[a[1]])))
            atual = [b]
        else:
            atual.append(b)
    trechos.append((atual[0][0], atual))
    trilhas = []
    cruzadas = set()
    for lay, pts in trechos:
        for p in pts:
            if caro[lay][p[1], p[2]]:
                P = shapely.Point(xs[p[2]], ys[p[1]])
                for o in mapa_macio.get(lay, []):
                    if o['geom'].distance(P) < infl:
                        cruzadas.add(o['ref'])
        if len(pts) < 2:
            continue
        xy = [(float(xs[p[2]]), float(ys[p[1]])) for p in pts]
        simp = [xy[0]]
        for k in range(1, len(xy) - 1):
            ax, ay = simp[-1]
            bx, by = xy[k]
            cx, cy = xy[k + 1]
            if abs((bx - ax) * (cy - by) - (by - ay) * (cx - bx)) > 1e-9:
                simp.append(xy[k])
        simp.append(xy[-1])
        trilhas.append({'net': net, 'layer': lay, 'w': largura, 'pts': simp})
    return {'trilhas': trilhas,
            'vias': [{'net': net, 'x': x, 'y': y, 'd': via[0], 'furo': via[1]} for x, y in vias],
            'cruzadas': cruzadas}


def ilhas_da_rede(placa, objs, net):
    """Componentes conexos (por cobre) da rede, como listas de objetos."""
    return [g for g in C.ilhas(objs, net) if any(o['tipo'] == 'pad' for o in g)]


def por_camada(grupo):
    out = {}
    for lay in (C.TOP, C.BOT):
        gs = [o['geom'] for o in grupo if lay in o['layers']]
        if gs:
            out[lay] = unary_union(gs)
    return out
