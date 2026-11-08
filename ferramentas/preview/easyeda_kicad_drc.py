"""Conferencia independente de um .epro no KiCad 7: monta a placa (pads na forma exata do EasyEDA,
trilhas, vias, furos e contorno), poe planos de GND nas duas faces, preenche com o proprio KiCad e
roda o DRC.

  /usr/bin/python3 easyeda_kicad_drc.py placa.epro saida.kicad_pcb [folga_plano]

Precisa do modulo pcbnew (KiCad 7) e de shapely no mesmo Python (ou no PYTHONPATH).
Eixo y: o KiCad usa y para baixo; aqui (x, y) -> (x + 100, 100 - y) mm.

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
from __future__ import annotations

import collections
import os
import re
import sys

import pcbnew
from shapely.geometry import MultiPolygon, Polygon

import easyeda_cobre as C

OX, OY = 100.0, 100.0


def mm(v):
    return pcbnew.FromMM(float(v))


def P(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY - y))


def montar(caminho_epro, saida, folga_plano=0.25):
    placa = C.Placa(caminho_epro)
    board = pcbnew.NewBoard(saida)
    ds = board.GetDesignSettings()
    ds.m_CopperEdgeClearance = mm(0.3)
    ds.m_MinClearance = mm(0.2)
    ds.m_HoleClearance = mm(0.25)
    ds.m_TrackMinWidth = mm(0.2)
    ds.m_ViasMinSize = mm(0.5)
    ds.m_MinThroughDrill = mm(0.3)
    ds.m_HoleToHoleMin = mm(0.25)
    nc = ds.m_NetSettings.m_DefaultNetClass
    nc.SetClearance(mm(0.2))
    nc.SetTrackWidth(mm(0.25))
    tb = board.GetTitleBlock()
    tb.SetTitle('RUSH - placa base (conferencia do .epro)')
    tb.SetComment(0, 'Baseado no EVA-RT (c) EXOTIC TEAM MX - AGPL-3.0')
    redes = {}
    for nome in sorted({p['net'] for p in placa.pads if p['net']} | {t['net'] for t in placa.tracks if t['net']}):
        ni = pcbnew.NETINFO_ITEM(board, nome)
        board.Add(ni)
        redes[nome] = ni
    # contorno e furos
    def poligono_edge(coords):
        for a, b in zip(coords, coords[1:]):
            s = pcbnew.PCB_SHAPE(board)
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(P(*a))
            s.SetEnd(P(*b))
            s.SetLayer(pcbnew.Edge_Cuts)
            s.SetWidth(mm(0.05))
            board.Add(s)
    poligono_edge(list(placa.borda.exterior.coords))
    for i in placa.borda.interiors:
        poligono_edge(list(i.coords))
    for h in placa.npth:
        c = h.centroid
        r = (h.area / 3.14159265) ** 0.5
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_CIRCLE)
        s.SetCenter(P(c.x, c.y))
        s.SetEnd(P(c.x + r, c.y))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.05))
        board.Add(s)
    # componentes: um footprint por designador, pads customizados na posicao absoluta
    por_ref = collections.defaultdict(list)
    for p in placa.pads:
        por_ref[p['des']].append(p)
    for ref, pads in por_ref.items():
        fp = pcbnew.FOOTPRINT(board)
        fp.SetReference(ref.replace(':', '_'))
        cx = sum(p['centro'][0] for p in pads) / len(pads)
        cy = sum(p['centro'][1] for p in pads) / len(pads)
        fp.SetPosition(P(cx, cy))
        board.Add(fp)
        for p in pads:
            pad = pcbnew.PAD(fp)
            pad.SetNumber(p['num'])
            px, py = p['centro']
            g = p['geom']
            if isinstance(g, MultiPolygon):
                g = max(g.geoms, key=lambda q: q.area)
            tht = len(p['layers']) == 2
            pad.SetShape(pcbnew.PAD_SHAPE_CUSTOM)
            pad.SetAnchorPadShape(pcbnew.PAD_SHAPE_CIRCLE)
            pad.SetSize(pcbnew.VECTOR2I(mm(0.05), mm(0.05)))
            if tht:
                pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
                pad.SetLayerSet(pad.PTHMask())
                forma = p['forma']
                furo = p['furo']
                if p['des'].startswith('PAD:'):     # rasgo do velcro (furo oblongo 7 x 1 na horizontal)
                    pad.SetDrillShape(pcbnew.PAD_DRILL_SHAPE_OBLONG)
                    pad.SetDrillSize(pcbnew.VECTOR2I(mm(7.0), mm(1.0)))
                else:
                    pad.SetDrillSize(pcbnew.VECTOR2I(mm(round(furo, 3)), mm(round(furo, 3))))
            else:
                pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
                ls = pcbnew.LSET()
                if C.TOP in p['layers']:
                    ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.F_Mask)
                else:
                    ls.AddLayer(pcbnew.B_Cu); ls.AddLayer(pcbnew.B_Mask)
                pad.SetLayerSet(ls)
            pts = pcbnew.VECTOR_VECTOR2I()
            for x, y in list(g.simplify(0.002).exterior.coords)[:-1]:
                pts.append(pcbnew.VECTOR2I(mm(x - px), mm(-(y - py))))
            pad.AddPrimitivePoly(pts, 0, True)
            pad.SetPos0(pcbnew.VECTOR2I(mm(px - cx), mm(-(py - cy))))
            pad.SetPosition(P(px, py))
            fp.Add(pad)
            if p['net']:
                pad.SetNet(redes[p['net']])
    for t in placa.tracks:
        tr = pcbnew.PCB_TRACK(board)
        tr.SetStart(P(*t['a']))
        tr.SetEnd(P(*t['b']))
        tr.SetWidth(mm(t['w']))
        tr.SetLayer(pcbnew.F_Cu if t['layer'] == C.TOP else pcbnew.B_Cu)
        if t['net']:
            tr.SetNet(redes[t['net']])
        board.Add(tr)
    for v in placa.vias:
        via = pcbnew.PCB_VIA(board)
        via.SetPosition(P(v['x'], v['y']))
        via.SetWidth(mm(round(v['d'], 3)))
        via.SetDrill(mm(round(v['furo'], 3)))
        via.SetViaType(pcbnew.VIATYPE_THROUGH)
        via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        if v['net']:
            via.SetNet(redes[v['net']])
        board.Add(via)
    x0, y0, x1, y1 = placa.borda.bounds
    for L in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(L)
        z.SetNet(redes['GND'])
        ol = z.Outline()
        ol.NewOutline()
        for x, y in ((x0 - 1, y0 - 1), (x1 + 1, y0 - 1), (x1 + 1, y1 + 1), (x0 - 1, y1 + 1)):
            q = P(x, y)
            ol.Append(q.x, q.y)
        z.SetLocalClearance(mm(folga_plano))
        z.SetMinThickness(mm(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)   # ligacao solida (pads customizados nao recebem raios)
        z.SetThermalReliefGap(mm(0.3))
        z.SetThermalReliefSpokeWidth(mm(0.4))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        z.SetZoneName('GND_' + ('cima' if L == pcbnew.F_Cu else 'baixo'))
        board.Add(z)
    pcbnew.SaveBoard(saida, board)
    b = pcbnew.LoadBoard(saida)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(saida, b)
    rpt = saida.replace('.kicad_pcb', '_drc.rpt')
    pcbnew.WriteDRCReport(b, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
    txt = open(rpt, encoding='utf8').read()
    tipos = collections.Counter(re.findall(r'^\[(\w+)\]', txt, re.M))
    nao = b.GetConnectivity().GetUnconnectedCount(True)
    return b, rpt, tipos, nao


if __name__ == '__main__':
    folga = float(sys.argv[3]) if len(sys.argv) > 3 else 0.25
    b, rpt, tipos, nao = montar(sys.argv[1], sys.argv[2], folga)
    print('DRC do KiCad:', dict(tipos))
    print('ligacoes nao roteadas (KiCad):', nao)
    print('relatorio:', rpt)
