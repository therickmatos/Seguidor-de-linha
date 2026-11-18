#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Monta a pasta mecânica/stl/ do seguidor RUSH - SATURN v12 (base e barra V1 de
1,6 mm): patim da barra V1, presilhas da vareta, placa de succao com folga para as
cabecas dos parafusos e os STL do EVA-RT que sao impressos como estao (mais a caixa
de reducao espelhada).

Baseado nas pecas `sensor_sledge.stl` e `barilla_clamp.stl` do EVA-RT
(c) EXOTIC TEAM MX, AGPL-3.0 - https://github.com/EXOTIC-TEAM-MX/EVA-RT
As medidas foram tiradas dos STL originais (referencias/eva-rt/3d_models/).
A presilha sem o braco de baixo veio do perseguidor RUSH - Dreamcast
(therickmatos/Perseguidor-de-linha). No Saturn a presilha da frente fica sobre a
raiz da asa, onde a placa nao acaba em x = +-50, e por isso nao tem a parede que
desce pela borda (ver presilha()).

Referencial LOCAL das pecas (o mesmo dos STL originais, que e o de impressao):
    origem = eixo da vareta, na face de tras da peca
    +x = do eixo da vareta para o parafuso (para dentro do robo)
    +y = para cima
    +z = ao longo da vareta, para a frente (a peca e impressa com z para cima)

Uso:  python3 gerar_pecas.py            # grava em mecânica/stl/
      python3 gerar_pecas.py --conferir # so reconstroi os originais e compara
Requer: numpy, manifold3d e trimesh (ver requisitos.txt).
"""
from __future__ import annotations

import argparse
import json
import struct
import zipfile
from pathlib import Path

import numpy as np
from manifold3d import CrossSection, Manifold, set_circular_segments

RAIZ = Path(__file__).resolve().parents[2]
MECANICA = RAIZ / "mecânica"
SAIDA = MECANICA / "stl"   # uma subpasta por filamento: stl/PETG/ e stl/PLA/
ORIGINAIS = RAIZ / "referencias" / "eva-rt" / "3d_models"
EPRO = RAIZ / "hardware" / "placa_base" / "ProPrj_RUSH - SATURN - v12_2026-11-15.epro"
MIL = 0.0254               # unidade do .epro
ESP_BASE = 1.6             # base RUSH - SATURN v12 (pedido na JLC: FR-4 1,6 mm)
ESP_BARRA = 1.6            # barra V1 (medida pelo Erick em 17/11/2026)

set_circular_segments(96)

# ----------------------------------------------------------------------------
# Cotas do projeto (mm). Referencial do robo: origem no centro da ventoinha.
# ----------------------------------------------------------------------------
X_FURO_BASE = 43.75        # furos das presilhas na base (iguais aos do EVA-RT)
X_FURO_V1 = 44.62624       # furos O2,05 da barra V1 (Drill_PTH_Through.DRL)
X_BORDA_V1 = 48.2521       # borda lateral da V1 (Gerber_BoardOutlineLayer.GKO)
X_FURO_VISION = 44.0       # barra VISION do EVA-RT, para comparar
DESL_PRESILHA = 4.7        # eixo da vareta -> parafuso, barilla_clamp.stl
DESL_PATIM_EVA = 4.4       # eixo da vareta -> parafuso, sensor_sledge.stl
X_VARETA = X_FURO_BASE + DESL_PRESILHA          # 48,45: onde a presilha poe a vareta
# Para a vareta sair reta (paralela ao eixo y) o patim tem de alcancar o furo da
# V1 a partir desse mesmo x:
DESL_PATIM_V1 = X_VARETA - X_FURO_V1            # 3,824
BORDA_V1_LOCAL = X_VARETA - X_BORDA_V1          # +0,198: a borda da V1 fica sob a vareta
Z_VARETA = 2.5             # eixo da vareta acima da face de cima da base
Y_TRANSVERSAL = 19.745     # eixo da vareta transversal (presa sob as orelhas da carcaca)
FOLGA_BLOCO = 0.3          # folga do rebaixo do bloco da transversal ate a placa

# Ficam de fora: barilla_clamp (rasgo de 1,0 mm, ver presilha()), sensor_sledge (barra
# VISION, ver patim()) e suction_base (substituida por placa_succao(), mesma peca com um
# rebaixo para a cabeca do parafuso em cada pe).
# barilla_connection tambem fica de fora: substituido por bloco_transversal(), a mesma
# peca com um rebaixo para a raiz da asa.
EVA_COMO_ESTAO = ["gearbox.stl", "wheel_rim.stl", "impeller_base_1.stl", "impeller_base_2.stl",
                  "impeller_fan.stl", "battery_holder.stl", "bead.stl"]

# Placa de succao (suction_base.stl, 0,6 mm): pes da carcaca da ventoinha em
# (+-15,556; +-15,556) no robo = (+-15,556; 11,944 e 43,056) no STL (y do STL = y + 27,5).
PES_SUCCAO_STL = [(sx * 15.556, 27.5 + sy * 15.556) for sx in (-1, 1) for sy in (-1, 1)]
D_REBAIXO = 4.4            # cabeca M2 de O3,8 + folga
FUNDO_REBAIXO = 0.2        # plastico que fica entre a cabeca e a base (isola as vias)

# Filamento de cada peca (so PLA e PETG; ver mecânica/README.md, "Material").
# PETG: sob aperto de parafuso ou perto de motor. PLA: aro (alojamento do
# rolamento mais preciso) e pecas sem esforco.
PLA = {"wheel_rim.stl", "battery_holder.stl", "bead.stl", "gabarito_base_teste.stl"}

# Pecas do EVA-RT que nao vem na posicao de impressao (matrizes 3x3, det = +1):
#   carcaca: de cabeca para baixo (o topo e plano; nos pes ela apoiaria 66 mm2
#            e teria ~490 mm2 em balanco);
#   caixas de reducao: deitadas sobre a face do pinhao, com os furos do motor e
#            do eixo na vertical (redondos, e o aperto do motor fica no plano
#            das camadas).
GIRO_IMPRESSAO = {
    "impeller_base_1.stl": [[1, 0, 0], [0, -1, 0], [0, 0, -1]],
    "gearbox.stl": [[0, 1, 0], [0, 0, 1], [1, 0, 0]],
    "gearbox_esquerdo_espelhado.stl": [[0, -1, 0], [0, 0, 1], [-1, 0, 0]],
}
CABECA_PARA_BAIXO = [[1, 0, 0], [0, -1, 0], [0, 0, -1]]


# engrenagens: as 3 versoes de VERSOES_ENGRENAGEM (nome_engrenagem)
RESINA = {f"engrenagem_64T_m0.3_{n}_{v}.stl" for n, v in ((1, "justa"), (2, "media"), (3, "folgada"))}


def destino(nome: str) -> Path:
    pasta = SAIDA / ("RESINA" if nome in RESINA else "PLA" if nome in PLA else "PETG")
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta / nome


R_VARETA = 1.5             # vareta de carbono O3
R_FURO = 1.0               # parafuso M2 (O2,0 como nos originais)

# Curva da ponta do esqui, (z, y), lida do sensor_sledge.stl no plano x = -0,5.
ESQUI_FRENTE = [
    (4.500, -6.500), (4.736, -6.496), (4.954, -6.483), (5.164, -6.462),
    (5.366, -6.433), (5.561, -6.396), (5.749, -6.352), (5.930, -6.299),
    (6.105, -6.238), (6.274, -6.169), (6.437, -6.094), (6.592, -6.011),
    (6.741, -5.921), (6.951, -5.775), (7.022, -5.723), (7.281, -5.500),
    (7.432, -5.349), (7.573, -5.195), (7.702, -5.039), (7.761, -4.960),
    (7.929, -4.727), (8.028, -4.574), (8.117, -4.426), (8.268, -4.149),
    (8.329, -4.022), (8.424, -3.799), (8.481, -3.623), (8.500, -3.500),
]


# ----------------------------------------------------------------------------
# Auxiliares de geometria
# ----------------------------------------------------------------------------
def poligono(pts) -> CrossSection:
    """Poligono simples; corrige o sentido para anti-horario (area positiva)."""
    p = np.asarray(pts, dtype=float)
    area = 0.5 * np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])
    assert abs(area) > 1e-9, "poligono degenerado"
    return CrossSection([p if area > 0 else p[::-1]])


def ret(x0, x1, y0, y1):
    return poligono([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def circ(r, cx=0.0, cy=0.0):
    return CrossSection.circle(r).translate((cx, cy))


def extr_z(perfil_xy: CrossSection, z0, z1) -> Manifold:
    return perfil_xy.extrude(z1 - z0).translate((0, 0, z0))


def extr_x(perfil_yz: CrossSection, x0, x1) -> Manifold:
    """Perfil dado em (y, z), extrudado ao longo de x."""
    m = perfil_yz.extrude(x1 - x0)                       # (u, v, w) = (y, z, x)
    return m.transform([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]])


def extr_y(perfil_zx: CrossSection, y0, y1) -> Manifold:
    """Perfil dado em (z, x), extrudado ao longo de y."""
    m = perfil_zx.extrude(y1 - y0)                       # (u, v, w) = (z, x, y)
    return m.transform([[0, 1, 0, 0], [0, 0, 1, y0], [1, 0, 0, 0]])


def furo_y(x, z, r=R_FURO) -> Manifold:
    return extr_y(circ(r, z, x), -20, 20)


def chanfro_pontas(x_fim, comp_z, c=1.5) -> Manifold:
    """Prisma que deixa as pontas dos bracos chanfradas a 45 graus (plano x-z)."""
    pts_zx = [(0, -10), (0, x_fim - c), (c, x_fim), (comp_z - c, x_fim),
              (comp_z, x_fim - c), (comp_z, -10)]
    return extr_y(poligono(pts_zx), -20, 20)


# ----------------------------------------------------------------------------
# Patim da barra (sensor_sledge)
# ----------------------------------------------------------------------------
def patim(esp_pcb=1.0, desl=DESL_PATIM_V1, borda_pcb=BORDA_V1_LOCAL,
          folga_rasgo=0.1, folga_borda=0.3, topo_reto=2.0, x_fim=7.5,
          assento=True) -> Manifold:
    """Patim da barra de sensores.

    esp_pcb      espessura da placa da barra
    desl         distancia do eixo da vareta ao parafuso
    borda_pcb    x local da borda da placa (a placa ocupa x >= borda_pcb)
    folga_rasgo  folga somada a espessura no rasgo da placa
    folga_borda  folga entre a borda da placa e o assento da vareta
    topo_reto    None = braco de cima de 1 mm, como no original;
                 valor = bloco de cima com topo plano nessa cota y, para a
                 porca M2 (4 mm entre faces) nao bater no ressalto da vareta
    assento      preenche o rasgo sob a vareta onde a placa nao chega
    """
    comp_braco, comp_bloco = 6.0, 8.5
    y_topo_pcb = -R_VARETA                       # a vareta apoia na face de cima da placa
    y_base_pcb = y_topo_pcb - esp_pcb - folga_rasgo
    y_base_braco = y_base_pcb - 1.0
    y_piso = -6.5                                # fundo do esqui (toca a pista)

    # --- secao dos bracos (plano x-y), extrudada em z = 0..6 -----------------
    corpo = (circ(2.5) ^ ret(-2.5, 2.5, 0, 2.5)) + ret(-2.5, 2.5, -0.5, 0)   # ressalto em U
    if topo_reto is None:
        corpo += ret(1.5, x_fim, y_topo_pcb, y_topo_pcb + 1.0)       # braco de cima fino
    else:
        corpo += ret(0, x_fim, y_topo_pcb, topo_reto)        # bloco de cima
    x_assento = borda_pcb - folga_borda if assento else -1.5
    corpo += ret(-2.5, x_assento, y_base_pcb, 0)             # parede externa + assento
    corpo += ret(-2.5, x_fim, y_base_braco, y_base_pcb)      # braco de baixo
    corpo -= circ(R_VARETA)                                  # vareta
    corpo -= ret(-R_VARETA, R_VARETA, y_topo_pcb, 0)         # canal em U ate a placa
    bracos = extr_z(corpo, 0, comp_braco) ^ chanfro_pontas(x_fim, comp_braco)

    # --- bloco do esqui -------------------------------------------------------
    # perfil lateral (y, z): chanfro de 30 graus atras, fundo reto, ponta curva
    perfil = [(y_base_pcb, 0.0), (-5.5, 0.0), (y_piso, 1.0 / np.tan(np.radians(30)))]
    perfil += [(y, z) for z, y in ESQUI_FRENTE if y < y_base_braco - 1e-6]
    z_ponta = float(np.interp(y_base_braco, [y for _, y in ESQUI_FRENTE],
                              [z for z, _ in ESQUI_FRENTE]))
    perfil += [(y_base_braco, z_ponta), (y_base_braco, comp_braco + 1.0),
               (y_base_pcb, comp_braco)]
    lateral = extr_x(poligono(perfil), -2.5, 1.5)
    # fundo arredondado (plano x-y): arco R2,5 com centro em (-0,5; -4)
    fundo = (circ(2.5, -0.5, -4.0) + ret(-2.5, 1.5, -4.0, 5)) ^ ret(-2.5, 1.5, -10, 5)
    esqui = lateral ^ extr_z(fundo, 0, comp_bloco)

    return (bracos + esqui) - furo_y(desl, comp_braco / 2)


# ----------------------------------------------------------------------------
# Presilha da vareta na base (barilla_clamp)
# ----------------------------------------------------------------------------
def presilha(esp_pcb=1.0, folga_rasgo=0.0, desl=DESL_PRESILHA, x_fim=7.0,
             braco_baixo=True, parede_na_borda=True, assento=False) -> Manifold:
    """Presilha da vareta na base.

    braco_baixo  True = como o barilla_clamp do EVA-RT (rasgo que abraca a placa).
                 False = sem o braco de baixo: o parafuso aperta o braco de cima
                 direto na placa, com a cabeca embaixo da placa. Para a base de
                 1,6 mm: com o braco de baixo, a cabeca do parafuso ficaria na
                 altura da pista (solucao do perseguidor RUSH - Dreamcast).
    parede_na_borda  (so sem braco de baixo) True = a parede externa desce ate a
                 face de baixo da placa e encosta na borda em x = +-50 (nao deixa a
                 peca girar). False = a parede acaba na face de cima: a peca apoia
                 inteira em cima da placa. E a presilha da frente do Saturn, que
                 fica sobre a raiz da asa (ali a placa vai alem de x = +-50).
    assento      False = canal em U aberto para a placa, como no original: sob a
                 vareta sobra 1 mm de vao e a altura dela depende so do aperto do
                 canal (e de cola). True = canal fechado embaixo (furo O3 inteiro):
                 a vareta fica presa para cima e para baixo. Para PLA/PETG, que
                 seguram por aperto bem menos que filamento com fibra de carbono,
                 e o PETG cola mal com cianoacrilato. A vareta entra pela ponta.
    """
    comp = 4.5
    y_topo_pcb = -2.5                            # eixo da vareta 2,5 mm acima da base
    y_base_pcb = y_topo_pcb - esp_pcb - folga_rasgo
    if braco_baixo:
        y_base = y_base_pcb - 1.0
    else:
        y_base = y_base_pcb if parede_na_borda else y_topo_pcb
    corpo = (circ(2.5) ^ ret(-2.5, 2.5, 0, 2.5)) + ret(-2.5, 2.5, y_topo_pcb, 0)   # ressalto em U
    corpo += ret(1.5, x_fim, y_topo_pcb, y_topo_pcb + 1.0)   # braco de cima
    corpo += ret(-2.5, -1.5, y_base, 0)                      # parede externa
    if braco_baixo:
        corpo += ret(-2.5, x_fim, y_base, y_base_pcb)        # braco de baixo
    corpo -= circ(R_VARETA)
    if not assento:
        corpo -= ret(-R_VARETA, R_VARETA, y_base_pcb, 0)
    return extr_z(corpo, 0, comp) - furo_y(desl, comp / 2)


def presilha_tras():
    """Presilhas de tras (y = -1,75): borda reta em x = +-50, parede encostada nela.
    E a presilha do perseguidor RUSH - Dreamcast (base de 1,6 mm) com o assento."""
    return presilha(ESP_BASE, folga_rasgo=0.1, braco_baixo=False, assento=True)


def presilha_frente():
    """Presilhas da frente (y = 10,75): sobre a raiz da asa, apoiada so em cima."""
    return presilha(ESP_BASE, folga_rasgo=0.1, braco_baixo=False, parede_na_borda=False, assento=True)


# ----------------------------------------------------------------------------
# Placa base (.epro) e bloco da transversal (barilla_connection)
# ----------------------------------------------------------------------------
def ler_epro(caminho: Path = EPRO):
    """Contorno (shapely Polygon), furos [(x, y, d)] e componentes
    {ref: (x, y, face, rotacao)} da placa base, em mm."""
    from shapely.geometry import LineString, Polygon
    from shapely.ops import polygonize, unary_union
    with zipfile.ZipFile(caminho) as z:
        nome = next(n for n in z.namelist() if n.endswith(".epcb"))
        linhas = [json.loads(l) for l in z.read(nome).decode().splitlines() if l.strip()]
    # Contorno (camada 11). No v12 sao so segmentos ("L"); se aparecer arco
    # (ARC: x0, y0, "ARC", angulo, x1, y1), entra como corda.
    segs = []
    for r in linhas:
        if r[0] == "POLY" and r[4] == 11:
            s = r[6]
            fim = (s[3], s[4]) if s[2] == "L" else (s[4], s[5])
            segs.append(LineString([(s[0] * MIL, s[1] * MIL), (fim[0] * MIL, fim[1] * MIL)]))
    contorno = Polygon(max(polygonize(unary_union(segs)), key=lambda p: p.area).exterior)
    furos = [(r[7][0][1] * MIL, r[7][0][2] * MIL, 2 * r[7][0][3] * MIL)
             for r in linhas if r[0] == "FILL" and r[7][0][0] == "CIRCLE"]
    ref = {r[3]: r[8] for r in linhas if r[0] == "ATTR" and r[7] == "Designator"}
    comps = {ref[r[1]]: (r[4] * MIL, r[5] * MIL, r[3], r[6]) for r in linhas
             if r[0] == "COMPONENT" and r[1] in ref}
    return contorno, furos, comps


def pose_bloco(lado: int):
    """Matriz 3x4 que leva o barilla_connection.stl para o robo. Furo cego (y local)
    virado para dentro e 1 mm ABAIXO do eixo da vareta longitudinal (x local = -1
    -> z = 1,5), como nas fotos do EVA-RT: a transversal deita sobre a base e fica
    sob as orelhas da carcaca da ventoinha. Os dois lados usam a mesma peca, girada
    180 graus em torno da vertical."""
    if lado > 0:
        return [[0, -1, 0, X_VARETA], [0, 0, -1, Y_TRANSVERSAL + 3.5], [1, 0, 0, Z_VARETA]]
    return [[0, 1, 0, -X_VARETA], [0, 0, 1, Y_TRANSVERSAL - 3.5], [1, 0, 0, Z_VARETA]]


def inversa(t):
    r = np.asarray(t, dtype=float)[:, :3]
    v = np.asarray(t, dtype=float)[:, 3]
    return np.hstack([r.T, (-r.T @ v)[:, None]]).tolist()


def bloco_transversal(folga=FOLGA_BLOCO) -> Manifold:
    """barilla_connection.stl com um rebaixo onde a raiz da asa passa por baixo.

    O bloco desce 1 mm abaixo da face de cima da base. No EVA-RT ele fica a frente
    da placa; no Saturn v12 a raiz da asa passa sob ele (x de 47,5 a 51, y de 15,3
    a 18,1). O rebaixo e o contorno da placa com `folga` em volta, de 0,2 mm acima
    da face de cima para baixo, calculado para os dois lados e somado: a mesma peca
    serve na direita e na esquerda. Nao toca no furo da transversal."""
    contorno = ler_epro()[0].buffer(folga, join_style=2)
    placa = poligono(np.array(contorno.exterior.coords)[:-1]).extrude(4.0).translate((0, 0, -3.8))
    b = carregar_original("barilla_connection.stl")
    for lado in (1, -1):
        b -= placa.transform(inversa(pose_bloco(lado)))
    return b


# ----------------------------------------------------------------------------
# Placa de succao (suction_base)
# ----------------------------------------------------------------------------
def carregar_original(nome) -> Manifold:
    import trimesh
    from manifold3d import Mesh
    t = trimesh.load(ORIGINAIS / nome)
    return Manifold(Mesh(vert_properties=np.asarray(t.vertices, dtype=np.float32),
                         tri_verts=np.asarray(t.faces, dtype=np.uint32)))


def placa_succao(d=D_REBAIXO, fundo=FUNDO_REBAIXO) -> Manifold:
    """suction_base.stl com um rebaixo de O4,4 na face de baixo em cada pe.

    No EVA-RT a cabeca do parafuso que prende os pes da carcaca aperta a placa de
    succao (0,6 mm) contra a base. Com a base de 1,6 mm a cabeca ficaria a ~0,2 mm
    da pista. Com o rebaixo ela entra na placa e fica a 0,6 mm da pista; o fundo
    de 0,2 mm continua isolando a cabeca das vias que ha embaixo dela (PWMA_D5,
    PWMB_D6 e GND nos pes de tras). No STL, z = 0,6 e a face que encosta na base;
    o rebaixo abre na face z = 0 (virada para a pista)."""
    m = carregar_original("suction_base.stl")
    esp = m.bounding_box()[5]
    for x, y in PES_SUCCAO_STL:
        m -= Manifold.cylinder(1.0 + esp - fundo, d / 2).translate((x, y, -1.0))
    return m


# ----------------------------------------------------------------------------
# Engrenagem de 64 dentes (resina) que encaixa no aro do EVA-RT
# ----------------------------------------------------------------------------
# O wheel_rim.stl tem, na ponta de dentro, uma aba de O16,5 x 1,4 mm e 6 pinos de
# O3,09 x 2,0 mm num circulo de raio 5,45 mm (0, 60, ..., 300 graus). A engrenagem
# do EVA-RT (64 dentes, modulo 0,3, comprada) apoia na aba, travada pelos pinos.
# O rolamento fica rente a aba; a bucha (bead.stl) entra pelo furo central.
#
# A distancia entre eixos da gearbox.stl (11,35 mm) e exatamente a de engrenamento sem
# folga de um pinhao 11T com deslocamento de perfil +0,33 e uma 64T sem deslocamento
# (a nominal, com x = 0, e 11,25). Nao se sabe antes de montar: o deslocamento do pinhao
# comprado (0 ou +0,33), a distancia real na caixa de PETG (o PETG encolhe) e quanto a
# resina engorda o dente. Por isso saem 3 versoes, para imprimir juntas na mesma leva (a
# resina cura a camada inteira de uma vez: 9 pecas levam o mesmo tempo que 1). A versao
# fica marcada por 1, 2 ou 3 furos de O1,0 entre os pinos.
#   folga_dente: tirado da espessura do dente no primitivo (folga entre flancos)
#   fundo_extra: fundo do dente mais fundo que 1,25 m (folga para a ponta do pinhao)
#   corte_ponta: ponta do dente mais curta (folga para o fundo do pinhao; baixa a razao
#                de contato, por isso so nas versoes mais folgadas)
ENGRENAGEM = dict(z=64, m=0.3, alfa=20.0, largura=2.0, r_pinos=5.45, d_furo_pino=3.25,
                  n_pinos=6, d_furo_central=6.6, r_marca=8.1, d_marca=1.0)
VERSOES_ENGRENAGEM = {
    1: dict(nome="justa", folga_dente=0.06, fundo_extra=0.06, corte_ponta=0.0),
    2: dict(nome="media", folga_dente=0.10, fundo_extra=0.06, corte_ponta=0.03),
    3: dict(nome="folgada", folga_dente=0.14, fundo_extra=0.08, corte_ponta=0.06),
}


def nome_engrenagem(n):
    return f"engrenagem_64T_m0.3_{n}_{VERSOES_ENGRENAGEM[n]['nome']}.stl"


def perfil_engrenagem(z, m, alfa=20.0, x=0.0, folga_dente=0.0, n_flanco=24, n_arco=6,
                      fundo_extra=0.0, corte_ponta=0.0):
    """Contorno (anti-horario) de uma engrenagem de dentes retos com flanco evolvente.

    x = deslocamento de perfil; folga_dente = quanto tirar da espessura do dente no
    circulo primitivo (folga entre dentes); fundo_extra = quanto aprofundar o fundo do
    dente alem de 1,25 m; corte_ponta = quanto encurtar a ponta. Abaixo do circulo de
    base o flanco vira radial (sem modelar o rebaixo de corte)."""
    a = np.radians(alfa)
    inv = lambda t: np.tan(t) - t
    rp = m * z / 2
    rb = rp * np.cos(a)
    ra = rp + m * (1 + x) - corte_ponta
    rf = rp - m * (1.25 - x) - fundo_extra
    s = m * (np.pi / 2 + 2 * x * np.tan(a)) - folga_dente
    psi_p = s / (2 * rp)
    r0 = max(rb, rf)
    rs = np.linspace(r0, ra, n_flanco)
    psi = psi_p + inv(a) - inv(np.arccos(np.clip(rb / rs, -1, 1)))
    assert psi[-1] > 0, "dente em ponta: diminua x ou a folga"
    pts = []
    for k in range(z):
        th = 2 * np.pi * k / z
        if rf < r0:
            pts.append((rf, th - psi[0]))
        pts += [(r, th - q) for r, q in zip(rs, psi)]
        pts += [(ra, t) for t in np.linspace(th - psi[-1], th + psi[-1], n_arco)[1:-1]]
        pts += [(r, th + q) for r, q in zip(rs[::-1], psi[::-1])]
        if rf < r0:
            pts.append((rf, th + psi[0]))
        th1 = 2 * np.pi * (k + 1) / z
        pts += [(rf, t) for t in np.linspace(th + psi[0], th1 - psi[0], n_arco)[1:-1]]
    return np.array([(r * np.cos(t), r * np.sin(t)) for r, t in pts])


def perfil_versao(n, e=ENGRENAGEM):
    v = VERSOES_ENGRENAGEM[n]
    return perfil_engrenagem(e["z"], e["m"], e["alfa"], 0.0, v["folga_dente"],
                             fundo_extra=v["fundo_extra"], corte_ponta=v["corte_ponta"])


def engrenagem_aro(n, e=ENGRENAGEM) -> Manifold:
    """Engrenagem de 64 dentes para resina (versao n), com os 6 furos dos pinos do aro
    e n furos de marca entre os pinos (30, 150 e 270 graus: ficam equilibrados)."""
    g = poligono(perfil_versao(n, e)).extrude(e["largura"])
    furos = [(e["r_pinos"], 2 * np.pi * k / e["n_pinos"], e["d_furo_pino"]) for k in range(e["n_pinos"])]
    furos += [(e["r_marca"], np.radians(30 + 360 * k / n), e["d_marca"]) for k in range(n)]
    furos += [(0.0, 0.0, e["d_furo_central"])]
    for r, t, d in furos:
        g -= Manifold.cylinder(e["largura"] + 2, d / 2).translate(
            (r * np.cos(t), r * np.sin(t), -1))
    return g


# ----------------------------------------------------------------------------
# Saida
# ----------------------------------------------------------------------------
def malha(m: Manifold):
    msh = m.to_mesh()
    return np.asarray(msh.vert_properties)[:, :3].astype(np.float64), np.asarray(msh.tri_verts)


def gravar_stl(m: Manifold, caminho: Path, nome: str):
    v, f = malha(m)
    tri = v[f]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    cab = (nome + " - baseado no EVA-RT (EXOTIC TEAM MX), AGPL-3.0").encode("ascii")[:80]
    with open(caminho, "wb") as fh:
        fh.write(cab.ljust(80, b" "))
        fh.write(struct.pack("<I", len(tri)))
        reg = np.zeros(len(tri), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
        reg["n"], reg["v"] = n, tri
        fh.write(reg.tobytes())
    bb = np.round([v.min(0), v.max(0)], 3).tolist()
    print(f"  {caminho.name:38s} {len(tri):5d} tri  vol {m.volume():7.2f} mm3  caixa {bb}")


def espelhar(m: Manifold) -> Manifold:
    return m.mirror((1, 0, 0))


def para_impressao(m: Manifold, giro) -> Manifold:
    """Gira a peca (matriz 3x3) e apoia o ponto mais baixo em z = 0."""
    m = m.transform([list(l) + [0] for l in giro])
    return m.translate((0, 0, -m.bounding_box()[2]))


def gabarito_base(x_max=56.0, d_furo=2.2) -> Manifold:
    """Base de teste em PLA com o contorno e os furos do Saturn v12, 1,6 mm.

    So para montar a carcaca da ventoinha, as caixas de reducao e as presilhas
    antes de a placa chegar (videos, conferencia de encaixe e de parafuso). As
    asas sao cortadas em |x| = 56: fica so a raiz delas, onde apoiam as
    presilhas da frente. Furos de O2,2 para o M2 passar sem broca."""
    from shapely.geometry import box
    contorno, furos, _ = ler_epro()
    contorno = contorno.intersection(box(-x_max, -100, x_max, 100))
    m = poligono(np.array(contorno.exterior.coords)[:-1]).extrude(ESP_BASE)
    for x, y, d in furos:
        m -= Manifold.cylinder(ESP_BASE + 2, (d if d > 5 else d_furo) / 2).translate((x, y, -1))
    return m


def conferir():
    """Reconstroi as pecas originais com os mesmos parametros e compara."""
    carregar = carregar_original
    casos = [
        ("sensor_sledge.stl", patim(1.0, DESL_PATIM_EVA, folga_rasgo=0.0,
                                    topo_reto=None, assento=False)),
        ("barilla_clamp.stl", presilha(1.0)),
    ]
    ok = True
    for nome, recon in casos:
        orig = carregar(nome)
        falta, sobra = (orig - recon).volume(), (recon - orig).volume()
        print(f"  {nome:20s} original {orig.volume():7.2f} mm3  reconstruida "
              f"{recon.volume():7.2f} mm3  falta {falta:.3f}  sobra {sobra:.3f}")
        ok &= recon.volume() > 0 and (falta + sobra) < 0.02 * orig.volume()
    print("  reconstrucao confere" if ok else "  DIFERENCA ACIMA DE 2 %")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--conferir", action="store_true",
                    help="so compara a reconstrucao com os STL originais")
    args = ap.parse_args()
    print(f"vareta em x = +/-{X_VARETA:.3f}; patim V1: parafuso a {DESL_PATIM_V1:.3f} mm "
          f"do eixo da vareta (EVA-RT/VISION: {DESL_PATIM_EVA}); borda da V1 em x local "
          f"{BORDA_V1_LOCAL:+.3f}")
    print("Conferencia contra os originais:")
    ok = conferir()
    if args.conferir:
        raise SystemExit(0 if ok else 1)
    print(f"STL em {SAIDA.relative_to(RAIZ)}/PETG/ e PLA/:")
    # o patim depende da espessura da barra V1; a presilha, da base
    p = patim(ESP_BARRA)
    gravar_stl(p, destino(f"patim_v1_direito_barra{ESP_BARRA:.1f}.stl"), f"patim V1 direito barra {ESP_BARRA:.1f}")
    gravar_stl(espelhar(p), destino(f"patim_v1_esquerdo_barra{ESP_BARRA:.1f}.stl"),
               f"patim V1 esquerdo barra {ESP_BARRA:.1f}")
    gravar_stl(presilha_tras(), destino("presilha_vareta_tras_base1.6.stl"), "presilha da vareta tras base 1.6")
    gravar_stl(presilha_frente(), destino("presilha_vareta_frente_asa.stl"), "presilha da vareta frente (asa)")
    # placa de succao com os rebaixos para cima: o fundo de 0,2 mm sai na 1a camada
    gravar_stl(para_impressao(placa_succao(), CABECA_PARA_BAIXO), destino("placa_succao_rebaixo.stl"),
               "placa de succao com rebaixo")
    gravar_stl(bloco_transversal(), destino("bloco_transversal_asa.stl"), "bloco da transversal (asa)")
    gravar_stl(gabarito_base(), destino("gabarito_base_teste.stl"), "gabarito da base (teste, PLA)")
    for n, v in VERSOES_ENGRENAGEM.items():
        gravar_stl(engrenagem_aro(n), destino(nome_engrenagem(n)), f"engrenagem 64T m0.3 versao {n} {v['nome']} (resina)")
    # pecas do EVA-RT usadas como estao (as de GIRO_IMPRESSAO so giradas para imprimir)
    import shutil
    for nome in EVA_COMO_ESTAO:
        if nome in GIRO_IMPRESSAO:
            gravar_stl(para_impressao(carregar_original(nome), GIRO_IMPRESSAO[nome]), destino(nome),
                       f"{nome[:-4]} (EVA-RT, girado para imprimir)")
        else:
            shutil.copyfile(ORIGINAIS / nome, destino(nome))
    print(f"  copiados de {ORIGINAIS.relative_to(RAIZ)}/: {', '.join(EVA_COMO_ESTAO)}")
    # o gearbox.stl e o do lado direito (pinhao para fora em +x); o esquerdo e o espelho dele
    nome = "gearbox_esquerdo_espelhado.stl"
    gravar_stl(para_impressao(espelhar(carregar_original("gearbox.stl")), GIRO_IMPRESSAO[nome]), destino(nome),
               "gearbox espelhado (lado esquerdo)")


if __name__ == "__main__":
    main()
