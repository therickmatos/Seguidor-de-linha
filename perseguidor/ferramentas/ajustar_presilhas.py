"""Ajusta o "RUSH - Dreamcast 2026-11-14 (Erick).epro" (edição do Erick no
EasyEDA) para não bater nas presilhas da vareta (barilla_clamp do EVA-RT).

Uso (a partir da raiz do repositório):
    python3 perseguidor/ferramentas/ajustar_presilhas.py

Presilha (vista de cima): o parafuso vai no furo (+-43,75; -1,75 / 10,75), o
olhal segura a vareta 4,6 mm para fora (x = +-48,35); cada presilha ocupa
x de +-41,35 até +-50,85 e y = furo +- 2,25, com 7 mm de altura. O braço de
baixo apoia na placa: nada de componente em cima nessa área.

O que muda:
  - J6 vai para x = -39,8 (corpo de -41,05 a -38,55: 0,3 mm das presilhas);
  - +5V do J6 refeito por cima, contornando o J6 pela esquerda (x = -41,75);
  - A5 entra no pino 1 vindo de baixo, em x = -39,8;
  - LED2/R6 e LED3/R9 em cima, no vão entre as presilhas (y 0,5 a 8,5):
    LED em x = +-45,0 e resistor em x = +-43,0, y = 5,6, ligados sem vias;
  - as áreas de cobre de GND (POUR, em cima e embaixo) do Saturn voltam;
    o arquivo de entrada não tinha nenhuma. Refazer os pours no EasyEDA.
"""
import copy, glob, json, os, shutil, sys, tempfile, zipfile
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from gerar_dreamcast import (MIL, mm, read_rows, write_rows, max_id, Ids, pad_geoms,  # noqa: E402
                             copper, drc, ilhas, seg_ends, near, outline)
from shapely.geometry import LineString, Point, box, Polygon  # noqa: E402
from shapely import affinity  # noqa: E402

RAIZ = os.path.dirname(AQUI)
ENTRADA = os.path.join(RAIZ, 'origem', 'RUSH - Dreamcast 2026-11-14 (Erick).epro')
SATURN = os.path.join(RAIZ, 'origem', 'RUSH - Saturn - Final.epro')
SAIDA = os.path.join(RAIZ, 'RUSH - Dreamcast.epro')

J6_POS = (-39.8, 4.5)
TOPO = {'LED2': (-45.0, 5.6), 'R6': (-43.0, 5.6), 'LED3': (45.0, 5.6), 'R9': (43.0, 5.6)}
W5V, WSIG = 19.685, 9.8425           # 0,5 mm e 0,25 mm em mil


def presilhas():
    out = []
    for sx in (-1, 1):
        for hy in (-1.75, 10.75):
            xa, xb = sorted((sx * 41.35, sx * 50.85))
            out.append(box(mm(xa), mm(hy - 2.25), mm(xb), mm(hy + 2.25)))
    return out


def corpos(d, rows):
    """contorno do corpo (camada 48 do footprint) ou dos pads, por componente, só os de cima."""
    comp = {r[1]: r for r in rows if r[0] == 'COMPONENT'}
    fp = {r[3]: r[8] for r in rows if r[0] == 'ATTR' and r[7] == 'Footprint' and r[8]}
    res = {}
    padsby = defaultdict(list)
    for cid, num, ly, g, net in pad_geoms(d, rows):
        padsby[cid].append(g)
    for cid, c in comp.items():
        if c[3] != 1 or cid not in fp:
            continue
        g = None
        for l in open(f'{d}/FOOTPRINT/{fp[cid]}.efoo', encoding='utf-8'):
            p = json.loads(l)
            if p[0] == 'POLY' and p[4] == 48:
                from epcb import pathpts
                try:
                    g = Polygon(pathpts(p[6]))
                except Exception:
                    g = None
        if g is not None and g.is_valid and g.area > 0:
            g = affinity.rotate(g, c[6], origin=(0, 0))
            g = affinity.translate(g, c[4], c[5])
        else:
            from shapely.ops import unary_union
            g = unary_union(padsby[cid]) if padsby[cid] else None
        if g is not None:
            res[cid] = g
    return res


def main():
    tmp = tempfile.mkdtemp()
    d, ds = f'{tmp}/in', f'{tmp}/sat'
    zipfile.ZipFile(ENTRADA).extractall(d)
    zipfile.ZipFile(SATURN).extractall(ds)
    pcb = glob.glob(f'{d}/PCB/*.epcb')[0]
    rows = [r for r in read_rows(pcb) if r is not None]
    srows = [r for r in read_rows(glob.glob(f'{ds}/PCB/*.epcb')[0]) if r is not None]
    new = Ids(max(max_id(rows), 20000) + 1000)
    log = defaultdict(list)
    base_drc = drc(copper(rows, pad_geoms(d, rows)))
    base_keys = {(a, b) for a, b, _ in base_drc}

    des = {r[3]: r[8] for r in rows if r[0] == 'ATTR' and r[7] == 'Designator' and r[8]}
    inv = {v: k for k, v in des.items()}
    comp = {r[1]: r for r in rows if r[0] == 'COMPONENT'}

    def mover(nome, x, y, camada=None, rot=None):
        c = comp[inv[nome]]
        dx, dy = mm(x) - c[4], mm(y) - c[5]
        c[4], c[5] = round(mm(x), 4), round(mm(y), 4)
        if rot is not None:
            c[6] = rot
        for r in rows:
            if r[0] == 'ATTR' and r[3] == c[1]:
                if r[5] is not None:
                    r[5] = round(r[5] + dx, 4); r[6] = round(r[6] + dy, 4)
                if camada == 1 and r[4] == 4:
                    r[4] = 3                       # serigrafia de baixo -> de cima
        if camada:
            c[3] = camada
        log['componentes movidos'].append((nome, x, y, 'cima' if c[3] == 1 else 'baixo', c[6]))

    def achar(net, a, b, tol=0.05):
        a, b = (mm(a[0]), mm(a[1])), (mm(b[0]), mm(b[1]))
        for r in rows:
            if r[0] == 'LINE' and r[3] == net:
                p, q = seg_ends(r)
                if (near(p, a, mm(tol)) and near(q, b, mm(tol))) or (near(p, b, mm(tol)) and near(q, a, mm(tol))):
                    return r
        raise KeyError((net, a, b))

    # ---- apagar o que vai ser refeito
    apagar = []
    for r in rows:
        if r[0] not in ('LINE', 'VIA'):
            continue
        if r[3] in ('$1N2289', '$1N2298'):
            apagar.append(r)
        elif r[3] in ('LEDA_D2', 'LEDB_D7'):
            pts = seg_ends(r) if r[0] == 'LINE' else [(r[5], r[6])]
            if all(abs(p[0]) > mm(40) for p in pts):
                comprimento = LineString(pts).length if r[0] == 'LINE' else 0
                if r[0] == 'VIA' or r[4] == 2 or comprimento < mm(0.5):
                    apagar.append(r)
    apagar += [achar('+5V', (-39.37, 12.446), (-39.37, 4.854)),
               achar('+5V', (-39.37, 4.854), (-39.724, 4.5)),
               achar('+5V', (-39.724, 4.5), (-40.7, 4.5)),
               achar('IR_A5', (-40.7, -1.083), (-40.7, 1.96))]
    ids = {id(r) for r in apagar}
    rows = [r for r in rows if id(r) not in ids]
    for r in apagar:
        log['trilhas/vias apagadas'].append((r[1], r[3]))

    # ---- mover componentes
    mover('J6', *J6_POS)
    for nome, (x, y) in TOPO.items():
        mover(nome, x, y, camada=1, rot=90)

    def pc(nome, n):
        return next(g.centroid.coords[0] for cid, num, _, g, _ in pad_geoms(d, rows)
                    if cid == inv[nome] and num == n)
    # pino 1 do resistor (sinal) embaixo e pino 2 do LED (lado do resistor) em cima
    for led, res in (('LED2', 'R6'), ('LED3', 'R9')):
        if pc(res, '1')[1] > pc(res, '2')[1]:
            comp[inv[res]][6] = 270
        if pc(led, '2')[1] < pc(led, '1')[1]:
            comp[inv[led]][6] = 270

    # ---- trilhas novas (todas em cima)
    j1, j2 = pc('J6', '1'), pc('J6', '2')
    novas = [
        ('+5V', W5V, [(mm(-39.37), mm(12.446)), (mm(-39.37), mm(9.35)), (mm(-41.75), mm(9.35)),
                      (mm(-41.75), j2[1]), j2]),
        ('IR_A5', WSIG, [(mm(-40.7), mm(-1.083)), (j1[0], mm(-1.083) + (j1[0] - mm(-40.7))), j1]),
    ]
    pa = (mm(-45.484), mm(2.558))      # fim da diagonal do D2
    pb = (mm(45.738), mm(-2.852))      # fim da diagonal do D7
    for led, res, mid, sig, p in (('LED2', 'R6', '$1N2289', 'LEDA_D2', pa),
                                  ('LED3', 'R9', '$1N2298', 'LEDB_D7', pb)):
        r1, r2, l2 = pc(res, '1'), pc(res, '2'), pc(led, '2')
        if sig == 'LEDA_D2':           # sobe a 45 graus para a direita
            pts = [p, (p[0] + (r1[1] - p[1]), r1[1]), r1]
        else:                          # sobe reto e entra a 45 graus para a esquerda
            pts = [p, (p[0], r1[1] - (p[0] - r1[0])), r1]
        novas += [(sig, WSIG, pts), (mid, WSIG, [l2, r2])]
    k = next(i for i, r in enumerate(rows) if r[0] == 'LINE')
    for net, w, pts in novas:
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if abs(x0 - x1) < 0.01 and abs(y0 - y1) < 0.01:
                continue
            rows.insert(k, ['LINE', new(), 0, net, 1, round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4), w, 0])
            k += 1
            log['trilhas novas (cima)'].append((net, round(x0 * MIL, 2), round(y0 * MIL, 2),
                                                round(x1 * MIL, 2), round(y1 * MIL, 2)))

    # ---- áreas de cobre de GND do Saturn
    if not any(r[0] == 'POUR' for r in rows):
        k = max(i for i, r in enumerate(rows) if r[0] in ('LINE', 'VIA')) + 1
        for r in srows:
            if r[0] == 'POUR':
                r = copy.deepcopy(r); r[1] = new()
                rows.insert(k, r); k += 1
                log['áreas de cobre restauradas'].append((r[3], 'camada', r[4], r[6]))
    rows = [r for r in rows if r[0] != 'POURED']

    # ---- conferências
    pads = pad_geoms(d, rows)
    novo = drc(copper(rows, pads))
    log['folga < 0,15 mm (novos)'] = sorted(x for x in novo if (x[0], x[1]) not in base_keys)
    for net, grupos in sorted(ilhas(rows, pads).items()):
        com_pad = [g for g in grupos if any(it[4] for it in g)]
        sem_pad = [g for g in grupos if not any(it[4] for it in g)]
        if net != 'GND' and (len(com_pad) > 1 or sem_pad):
            log['redes partidas (fora o GND)'].append((net, len(com_pad), len(sem_pad)))
    pres = presilhas()
    des = {r[3]: r[8] for r in rows if r[0] == 'ATTR' and r[7] == 'Designator' and r[8]}
    for cid, g in corpos(d, rows).items():
        dist = min(g.distance(p) for p in pres) * MIL
        if dist < 0.3:
            log['componentes de cima a menos de 0,3 mm das presilhas'].append((des.get(cid), round(dist, 2)))
    gb = [box(mm(-40), mm(-28.5), mm(-30.5), mm(-1.78)), box(mm(30.5), mm(-28.5), mm(40), mm(-1.78))]
    j6 = corpos(d, rows)[inv['J6']]
    log['folgas do corpo do J6 (mm)'] = [('presilhas', round(min(j6.distance(p) for p in pres) * MIL, 2)),
                                        ('gearbox', round(min(j6.distance(p) for p in gb) * MIL, 2)),
                                        ('aba do U1', round(j6.distance(next(g for c, n, _, g, _ in pads
                                                                          if c == inv['U1'] and n == '2')) * MIL, 2))]
    # folga mínima dos itens novos/movidos
    items = copper(rows, pads)
    novos_ids = {r[1] for r in rows if r[0] == 'LINE' and int(r[1][1:]) > 20000}
    movidos = {inv[n] for n in list(TOPO) + ['J6']}
    piores = []
    for it in items:
        if it[0] in novos_ids or it[0].split('.')[0] in movidos:
            o = min(((it[2].distance(x[2]) * MIL, x[0], x[3]) for x in items
                     if x[1] == it[1] and x[3] != it[3] and x[0] != it[0]), default=None)
            if o:
                nome = des.get(it[0].split('.')[0], it[0]) + ('.' + it[0].split('.')[1] if '.' in it[0] else '')
                outro = des.get(o[1].split('.')[0], o[1]) + ('.' + o[1].split('.')[1] if '.' in o[1] else '')
                piores.append((round(o[0], 2), nome, it[3], outro, o[2]))
    log['menores folgas dos itens novos/movidos'] = sorted(piores)[:5]
    borda = outline(rows)[0].exterior
    log['menor distância à borda (itens novos/movidos, mm)'] = [round(min(
        borda.distance(it[2]) for it in items if it[0] in novos_ids or it[0].split('.')[0] in movidos) * MIL, 2)]

    write_rows(pcb, rows)
    names = zipfile.ZipFile(ENTRADA).namelist()
    with zipfile.ZipFile(SAIDA, 'w', zipfile.ZIP_DEFLATED) as z:
        for n in names:
            if n.endswith('/'):
                z.writestr(zipfile.ZipInfo(n), '')
            else:
                z.write(f'{d}/{n}', n)
    shutil.rmtree(tmp)
    print('Gerado:', os.path.relpath(SAIDA))
    for k, v in log.items():
        print(f'{k}: {len(v)}')
        for x in v:
            print('   ', x)


if __name__ == '__main__':
    main()
