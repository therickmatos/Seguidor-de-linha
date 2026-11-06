"""Etapa 2 da placa KiCad: monta seguidor_base.kicad_pcb com a API do KiCad 7 (pcbnew).

Rodar com o python do sistema (o do KiCad):  python3 kicad_montar.py
Le v2/kicad_dados.json (gerado por kicad_exportar.py, no venv) e grava em hardware/seguidor_base/:
seguidor_base.kicad_pcb, seguidor_base.kicad_pro (com as regras de projeto), a biblioteca
seguidor_alpha.pretty, fp-lib-table e drc_kicad.rpt (DRC do proprio KiCad, com as areas de GND
preenchidas). Origem da grade e auxiliar no centro da ventoinha; no KiCad o eixo Y aponta para
baixo, entao y do seguidor = -Y.

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
import json
import math
import os
import shutil
import sys
import tempfile

import pcbnew

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, '..', '..'))
DADOS = os.path.join(AQUI, 'v2', 'kicad_dados.json')
DEST = os.path.join(RAIZ, 'hardware', 'seguidor_base')
NOME = 'seguidor_base'
LIB = 'seguidor_alpha'
OX, OY = 148.5, 100.0          # centro da ventoinha na folha A4 (mm)
mm = pcbnew.FromMM


def P(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY - y))


def edge_seg(board, a, b):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(P(*a)); s.SetEnd(P(*b))
    s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
    board.Add(s)


def edge_arc(board, a, m, b):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_ARC)
    s.SetArcGeometry(P(*a), P(*m), P(*b))
    s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
    board.Add(s)


def contorno(board, d):
    pts = d['contorno']
    for i in range(len(pts)):
        edge_seg(board, pts[i], pts[(i + 1) % len(pts)])
    for h in d['furos']:
        if h['tipo'] == 'furo':
            s = pcbnew.PCB_SHAPE(board)
            s.SetShape(pcbnew.SHAPE_T_CIRCLE)
            s.SetStart(P(h['x'], h['y'])); s.SetEnd(P(h['x'] + h['d'] / 2, h['y']))
            s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
            board.Add(s)
        else:   # rasgo do velcro: oblongo w (x) por h (y)
            x, y, w, hh = h['x'], h['y'], h['w'], h['h']
            r = hh / 2
            x0, x1 = x - w / 2 + r, x + w / 2 - r
            edge_seg(board, (x0, y + r), (x1, y + r))
            edge_seg(board, (x0, y - r), (x1, y - r))
            edge_arc(board, (x1, y + r), (x1 + r, y), (x1, y - r))
            edge_arc(board, (x0, y - r), (x0 - r, y), (x0, y + r))


def fab_rect(fp, cx, cy, w, h, layer):
    xs, ys = (cx - w / 2, cx + w / 2), (cy - h / 2, cy + h / 2)
    cantos = [(xs[0], ys[0]), (xs[1], ys[0]), (xs[1], ys[1]), (xs[0], ys[1])]
    for i in range(4):
        a, b = cantos[i], cantos[(i + 1) % 4]
        s = pcbnew.FP_SHAPE(fp, pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(layer); s.SetWidth(mm(0.1))
        s.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(-a[1]))); s.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(-b[1])))
        s.SetLocalCoord()
        fp.Add(s)


def novo_footprint(board, c):
    """Footprint na origem, orientacao 0, face de cima (coordenadas locais com Y para baixo)."""
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPID(pcbnew.LIB_ID(LIB, c['footprint']))
    fp.SetReference(c['ref']); fp.SetValue(c['valor'] or c['footprint'])
    tht = False
    pads = []
    for p in c['pads']:
        pad = pcbnew.PAD(fp)
        pad.SetNumber(p['numero'])
        forma = {'rect': pcbnew.PAD_SHAPE_RECT, 'round': pcbnew.PAD_SHAPE_CIRCLE,
                 'oval': pcbnew.PAD_SHAPE_OVAL}[p['forma']]
        if p['forma'] == 'round' and abs(p['w'] - p['h']) > 1e-6:
            forma = pcbnew.PAD_SHAPE_OVAL
        pad.SetShape(forma)
        pad.SetSize(pcbnew.VECTOR2I(mm(p['w']), mm(p['h'])))
        pad.SetPos0(pcbnew.VECTOR2I(mm(p['x']), mm(-p['y'])))
        pad.SetPosition(pcbnew.VECTOR2I(mm(p['x']), mm(-p['y'])))
        if p['furo']:
            tht = True
            pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
            pad.SetDrillSize(pcbnew.VECTOR2I(mm(p['furo']), mm(p['furo'])))
            pad.SetLayerSet(pad.PTHMask())
        else:
            pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
            pad.SetLayerSet(pad.SMDMask())
        fp.Add(pad)
        pads.append(pad)
    w, h = c['corpo']
    if w > 0 and h > 0:
        fab_rect(fp, c['corpo_xy'][0], c['corpo_xy'][1], w, h, pcbnew.F_Fab)
    fp.SetAttributes(pcbnew.FP_THROUGH_HOLE if tht else pcbnew.FP_SMD)
    ref = fp.Reference()
    ref.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8))); ref.SetTextThickness(mm(0.12))
    topo = max([p['y'] + p['h'] / 2 for p in c['pads']] + ([c['corpo_xy'][1] + h / 2] if h > 0 else []))
    ref.SetPos0(pcbnew.VECTOR2I(0, mm(-(topo + 0.7))))
    ref.SetDrawCoord()
    val = fp.Value()
    val.SetLayer(pcbnew.F_Fab); val.SetVisible(False)
    return fp, pads   # fp.Pads() vem em ordem invertida; usar esta lista


def pad_pos(pad):
    q = pad.GetPosition()
    return (pcbnew.ToMM(q.x) - OX, OY - pcbnew.ToMM(q.y))


def posicionar(fp, pads, c):
    fp.SetPosition(P(c['x'], c['y']))
    fp.SetOrientationDegrees(c['rot'])
    if c['face'] == 'BOTTOM':
        fp.Flip(fp.GetPosition(), True)
    def erro():
        e = 0.0
        for pad, p in zip(pads, c['pads']):
            x, y = pad_pos(pad)
            e = max(e, math.hypot(x - p['abs'][0], y - p['abs'][1]))
        return e
    if erro() > 0.01:
        base = fp.GetOrientationDegrees()
        for cand in (c['rot'], -c['rot'], 180 - c['rot'], 180 + c['rot'], base + 180):
            fp.SetOrientationDegrees(cand)
            if erro() <= 0.01:
                break
    return erro()


def dentro(poly, x, y):
    ins = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            ins = not ins
    return ins


def caixa(item, folga=0.0):
    bb = item.GetBoundingBox()
    return (pcbnew.ToMM(bb.GetX()) - OX - folga, OY - pcbnew.ToMM(bb.GetBottom()) - folga,
            pcbnew.ToMM(bb.GetRight()) - OX + folga, OY - pcbnew.ToMM(bb.GetY()) + folga)


def cruza(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def posicionar_referencias(board, d):
    """Referencia na serigrafia, horizontal, sem cobrir pad, sem sair da placa nem cair em furo e sem
    encostar em outra referencia da mesma face. Se nao couber, vai para a camada Fab (fica no relatorio)."""
    contorno = [tuple(p) for p in d['contorno']]
    furos = [(h['x'], h['y'], (h['d'] or max(h['w'], h['h'])) / 2) for h in d['furos']]
    pads = {pcbnew.F_Cu: [], pcbnew.B_Cu: []}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            for L in (pcbnew.F_Cu, pcbnew.B_Cu):
                if pad.IsOnLayer(L):
                    pads[L].append(caixa(pad, 0.2))
    usados = {pcbnew.F_Cu: [], pcbnew.B_Cu: []}

    def livre(r, L):
        x0, y0, x1, y1 = r
        cantos = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), ((x0 + x1) / 2, (y0 + y1) / 2)]
        if not all(dentro(contorno, x, y) for x, y in cantos):
            return False
        # 0,3 mm da borda: testa os cantos afastados
        if not all(dentro(contorno, x + dx, y + dy) for x, y in cantos[:4] for dx, dy in
                   ((0.3, 0), (-0.3, 0), (0, 0.3), (0, -0.3))):
            return False
        for fx, fy, fr in furos:
            nx, ny = min(max(fx, x0), x1), min(max(fy, y0), y1)
            if math.hypot(fx - nx, fy - ny) < fr + 0.3:
                return False
        return not any(cruza(r, q) for q in pads[L] + usados[L])

    fora = []
    for fp in sorted(board.GetFootprints(), key=lambda f: -len(f.Pads())):
        ref = fp.Reference()
        L = pcbnew.B_Cu if fp.IsFlipped() else pcbnew.F_Cu
        cu = [caixa(p) for p in fp.Pads()]
        bx0, by0 = min(c[0] for c in cu), min(c[1] for c in cu)
        bx1, by1 = max(c[2] for c in cu), max(c[3] for c in cu)
        cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
        feito = False
        for alt in (1.0, 0.8):
            ref.SetTextSize(pcbnew.VECTOR2I(mm(alt), mm(alt))); ref.SetTextThickness(mm(0.15))
            ref.SetTextAngleDegrees(0)
            ref.SetPosition(P(cx, cy))
            w = pcbnew.ToMM(ref.GetBoundingBox().GetWidth()); h = pcbnew.ToMM(ref.GetBoundingBox().GetHeight())
            g = 0.25
            cands = [(cx, by1 + g + h / 2), (cx, by0 - g - h / 2), (bx1 + g + w / 2, cy), (bx0 - g - w / 2, cy)]
            for k in (0.5, 1.0, 1.5, 2.0, 3.0):
                cands += [(cx, by1 + g + h / 2 + k), (cx, by0 - g - h / 2 - k), (bx1 + g + w / 2 + k, cy),
                          (bx0 - g - w / 2 - k, cy), (bx1 + g + w / 2, by1 + g + h / 2 + k - 0.5),
                          (bx0 - g - w / 2, by1 + g + h / 2 + k - 0.5), (bx1 + g + w / 2, by0 - g - h / 2 - k + 0.5),
                          (bx0 - g - w / 2, by0 - g - h / 2 - k + 0.5)]
            for x, y in cands:
                r = (x - w / 2, y - h / 2, x + w / 2, y + h / 2)
                if livre(r, L):
                    ref.SetPosition(P(x, y))
                    usados[L].append((r[0] - 0.15, r[1] - 0.15, r[2] + 0.15, r[3] + 0.15))
                    feito = True
                    break
            if feito:
                break
        if not feito:
            ref.SetLayer(pcbnew.B_Fab if fp.IsFlipped() else pcbnew.F_Fab)
            fora.append(fp.GetReference())
    return fora


def paridade(board, tmp):
    """Placa x esquematico, pelo netlist que o proprio KiCad exporta do .kicad_sch publicado:
    UUID de cada footprint e rede de cada pad (numero do pad = pino do simbolo)."""
    import re
    import subprocess
    sch = os.path.join(DEST, NOME + '.kicad_sch')
    netf = os.path.join(tmp, NOME + '.net')
    subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', netf, sch],
                   check=True, capture_output=True)
    txt = open(netf, encoding='utf8').read()
    os.remove(netf)
    uu = dict(re.findall(r'\(comp \(ref "([^"]+)"\).*?\(tstamps "([0-9a-f-]{36})"\)\)', txt, re.S))
    pino = {}
    rede = None
    for linha in txt.splitlines():
        m = re.match(r'\s*\(net \(code "?\d+"?\) \(name "([^"]*)"\)', linha)
        if m:
            rede = m.group(1).lstrip('/')
        m = re.match(r'\s*\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', linha)
        if m and rede is not None:
            pino[(m.group(1), m.group(2))] = rede
    erros, n = [], 0
    placa = set()
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if uu.get(ref) != fp.GetPath().AsString().strip('/'):
            erros.append('%s: UUID diferente do esquematico' % ref)
        for pad in fp.Pads():
            num, pn = pad.GetNumber(), pad.GetNetname()
            placa.add((ref, num))
            if not num:
                if pn:
                    erros.append('%s: pad sem numero na rede %s' % (ref, pn))
                continue
            n += 1
            s = pino.get((ref, num))
            nomeada = s is not None and not s.startswith(('unconnected-', 'Net-('))
            if (nomeada and s != pn) or (not nomeada and pn and not pn.startswith('Net-(')):
                erros.append('%s.%s: placa %s, esquematico %s' % (ref, num, pn or '-', s))
            elif not nomeada and pn.startswith('Net-(') and s != pn:
                erros.append('%s.%s: placa %s, esquematico %s' % (ref, num, pn, s))
    fora = sorted('%s.%s' % k for k, v in pino.items() if not v.startswith('unconnected-') and k not in placa)
    return n, erros, fora


def main():
    d = json.load(open(DADOS, encoding='utf8'))
    tmp = tempfile.mkdtemp()
    caminho = os.path.join(tmp, NOME + '.kicad_pcb')
    board = pcbnew.NewBoard(caminho)
    ds = board.GetDesignSettings()
    ds.m_CopperEdgeClearance = mm(d['regras']['borda'])
    ds.m_MinClearance = mm(d['regras']['folga'])
    ds.m_TrackMinWidth = mm(0.2)
    ds.m_ViasMinSize = mm(0.5)
    ds.m_MinThroughDrill = mm(0.3)
    ds.m_HoleToHoleMin = mm(0.25)
    ds.SetAuxOrigin(P(0, 0)); ds.SetGridOrigin(P(0, 0))
    try:
        nc = ds.m_NetSettings.m_DefaultNetClass
        nc.SetClearance(mm(0.2)); nc.SetTrackWidth(mm(0.25)); nc.SetViaDiameter(mm(0.6)); nc.SetViaDrill(mm(0.3))
    except Exception as e:  # noqa
        print('aviso: classe de rede padrao nao ajustada:', e)

    tb = board.GetTitleBlock()
    tb.SetTitle('Seguidor de linha - placa base (versao alpha)')
    tb.SetRevision('alpha')
    tb.SetDate('2026-11-06')
    tb.SetComment(0, 'Baseado no EVA-RT (c) EXOTIC TEAM MX - AGPL-3.0')
    tb.SetComment(1, 'Origem (aux e grade) no centro da ventoinha; +y do seguidor = para cima na tela')
    tb.SetComment(2, 'Footprints aproximados (biblioteca seguidor_alpha): trocar pelos da LCSC no EasyEDA')
    nota = pcbnew.PCB_TEXT(board)
    nota.SetText('Baseado no EVA-RT (c) EXOTIC TEAM MX - AGPL-3.0\n'
                 'Origem no centro da ventoinha (0; 0), +y = frente do robo, mm\n'
                 'Versao alpha 06/11/2026 - footprints aproximados: conferir com os da LCSC')
    nota.SetLayer(pcbnew.Cmts_User)
    nota.SetTextSize(pcbnew.VECTOR2I(mm(1.5), mm(1.5))); nota.SetTextThickness(mm(0.2))
    nota.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    nota.SetPosition(P(-74, 50))
    board.Add(nota)

    redes = {}
    for nome in d['redes']:
        ni = pcbnew.NETINFO_ITEM(board, nome)
        board.Add(ni)
        redes[nome] = ni

    contorno(board, d)

    libdir = os.path.join(tmp, LIB + '.pretty')
    os.makedirs(libdir, exist_ok=True)
    salvos = set()
    piores = []
    for c in d['componentes']:
        fp, pads = novo_footprint(board, c)
        if c['footprint'] not in salvos:
            pcbnew.FootprintSave(libdir, fp)
            salvos.add(c['footprint'])
        for pad, p in zip(pads, c['pads']):
            if p['rede']:
                pad.SetNet(redes[p['rede']])
        if c['uuid']:
            fp.SetPath(pcbnew.KIID_PATH('/' + c['uuid']))
        board.Add(fp)
        e = posicionar(fp, pads, c)
        piores.append((e, c['ref']))
    pior = max(piores)
    print('pads: maior diferenca para o modelo = %.4f mm (%s)' % pior)
    if pior[0] > 0.01:
        sys.exit('ERRO: pads fora da posicao do modelo')

    for t in d['trilhas']:
        L = pcbnew.F_Cu if t['camada'] == 1 else pcbnew.B_Cu
        xy = t['xy']
        for a, b in zip(xy, xy[1:]):
            tr = pcbnew.PCB_TRACK(board)
            tr.SetStart(P(*a)); tr.SetEnd(P(*b)); tr.SetWidth(mm(t['largura']))
            tr.SetLayer(L); tr.SetNet(redes[t['rede']])
            board.Add(tr)
    for v in d['vias']:
        via = pcbnew.PCB_VIA(board)
        via.SetPosition(P(*v['xy'])); via.SetWidth(mm(v['d'])); via.SetDrill(mm(v['furo']))
        via.SetViaType(pcbnew.VIATYPE_THROUGH); via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        via.SetNet(redes[v['rede']])
        board.Add(via)

    fora = posicionar_referencias(board, d)
    print('referencias fora da serigrafia (sem lugar livre, ficaram na camada Fab):', fora)

    for L in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(L); z.SetNet(redes['GND'])
        ol = z.Outline(); ol.NewOutline()
        for x, y in d['contorno']:
            q = P(x, y); ol.Append(q.x, q.y)
        z.SetLocalClearance(mm(0.25)); z.SetMinThickness(mm(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)
        z.SetThermalReliefGap(mm(0.3)); z.SetThermalReliefSpokeWidth(mm(0.4))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        z.SetZoneName('GND_' + ('cima' if L == pcbnew.F_Cu else 'baixo'))
        board.Add(z)

    tabela = ('(fp_lib_table\n  (version 7)\n  (lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/%s.pretty")'
              '(options "")(descr "Footprints da previa alpha (aproximados; trocar pelos da LCSC)"))\n)\n' % (LIB, LIB))
    with open(os.path.join(tmp, 'fp-lib-table'), 'w') as fh:
        fh.write(tabela)
    pcbnew.SaveBoard(caminho, board)
    b = pcbnew.LoadBoard(caminho)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(caminho, b)
    rpt = os.path.join(tmp, 'drc_kicad.rpt')
    pcbnew.WriteDRCReport(b, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
    txt = open(rpt, encoding='utf8').read().replace(caminho, 'hardware/seguidor_base/' + NOME + '.kicad_pcb')
    open(rpt, 'w', encoding='utf8').write(txt)
    print('conexoes nao roteadas (KiCad):', b.GetConnectivity().GetUnconnectedCount(True))
    n, erros, fora = paridade(b, tmp)
    print('paridade com o esquematico: %d pads conferidos, %d diferencas %s' % (n, len(erros), erros[:8]))
    print('pinos do esquematico sem pad na placa:', fora)

    for f in os.listdir(tmp):
        src = os.path.join(tmp, f)
        dst = os.path.join(DEST, f)
        if os.path.isdir(src):
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(src, dst)
        elif f.endswith('.kicad_pro') and os.path.exists(dst):
            # mantem o que o esquematico gravou (folhas, variaveis) e acrescenta as regras da placa
            pro = json.load(open(dst, encoding='utf8'))
            novo = json.load(open(src, encoding='utf8'))
            for k in ('board', 'boards', 'net_settings', 'pcbnew', 'libraries', 'cvpcb'):
                if k in novo:
                    pro[k] = novo[k]
            with open(dst, 'w', encoding='utf8') as fh:
                json.dump(pro, fh, indent=2)
                fh.write('\n')
        elif f.endswith(('.kicad_pcb', '.kicad_pro', '.rpt')) or f == 'fp-lib-table':
            shutil.copy(src, dst)
    print('gravado em', DEST)


if __name__ == '__main__':
    main()
