#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Monta a pasta mecânica/stl/: patim da barra V1, presilha de reserva e os STL do
EVA-RT que sao impressos como estao (mais a caixa de reducao espelhada).

Baseado nas pecas `sensor_sledge.stl` e `barilla_clamp.stl` do EVA-RT
(c) EXOTIC TEAM MX, AGPL-3.0 - https://github.com/EXOTIC-TEAM-MX/EVA-RT
As medidas foram tiradas dos STL originais (referencias/eva-rt/3d_models/).

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
import struct
from pathlib import Path

import numpy as np
from manifold3d import CrossSection, Manifold, set_circular_segments

RAIZ = Path(__file__).resolve().parents[2]
MECANICA = RAIZ / "mecânica"
SAIDA = MECANICA / "stl"
RESERVA = SAIDA / "se_a_placa_tiver_1.6mm"
ORIGINAIS = RAIZ / "referencias" / "eva-rt" / "3d_models"

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

EVA_COMO_ESTAO = ["gearbox.stl", "wheel_rim.stl", "impeller_base_1.stl", "impeller_base_2.stl",
                  "impeller_fan.stl", "suction_base.stl", "battery_holder.stl", "bead.stl",
                  "barilla_clamp.stl", "barilla_connection.stl"]

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
def presilha(esp_pcb=1.0, folga_rasgo=0.0, desl=DESL_PRESILHA, x_fim=7.0) -> Manifold:
    comp = 4.5
    y_topo_pcb = -2.5                            # eixo da vareta 2,5 mm acima da base
    y_base_pcb = y_topo_pcb - esp_pcb - folga_rasgo
    y_base = y_base_pcb - 1.0
    corpo = (circ(2.5) ^ ret(-2.5, 2.5, 0, 2.5)) + ret(-2.5, 2.5, y_topo_pcb, 0)   # ressalto em U
    corpo += ret(1.5, x_fim, y_topo_pcb, y_topo_pcb + 1.0)   # braco de cima
    corpo += ret(-2.5, -1.5, y_base, 0)                      # parede externa
    corpo += ret(-2.5, x_fim, y_base, y_base_pcb)            # braco de baixo
    corpo -= circ(R_VARETA)
    corpo -= ret(-R_VARETA, R_VARETA, y_base_pcb, 0)
    return extr_z(corpo, 0, comp) - furo_y(desl, comp / 2)


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


def conferir():
    """Reconstroi as pecas originais com os mesmos parametros e compara."""
    import trimesh
    from manifold3d import Mesh

    def carregar(nome):
        t = trimesh.load(ORIGINAIS / nome)
        return Manifold(Mesh(vert_properties=np.asarray(t.vertices, dtype=np.float32),
                             tri_verts=np.asarray(t.faces, dtype=np.uint32)))

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
    RESERVA.mkdir(parents=True, exist_ok=True)
    print(f"STL em {SAIDA.relative_to(RAIZ)}/:")
    for esp, pasta in ((1.0, SAIDA), (1.6, RESERVA)):
        p = patim(esp)
        gravar_stl(p, pasta / f"patim_v1_direito_pcb{esp:.1f}.stl", f"patim V1 direito pcb {esp:.1f}")
        gravar_stl(espelhar(p), pasta / f"patim_v1_esquerdo_pcb{esp:.1f}.stl", f"patim V1 esquerdo pcb {esp:.1f}")
    gravar_stl(presilha(1.6, folga_rasgo=0.1), RESERVA / "presilha_vareta_pcb1.6.stl",
               "presilha da vareta pcb 1.6")
    # pecas do EVA-RT usadas como estao (o sensor_sledge fica de fora: substituido pelo patim V1)
    import shutil
    for nome in EVA_COMO_ESTAO:
        shutil.copyfile(ORIGINAIS / nome, SAIDA / nome)
    print(f"  copiados sem alteracao de {ORIGINAIS.relative_to(RAIZ)}/: {', '.join(EVA_COMO_ESTAO)}")
    # o gearbox.stl e o do lado direito (pinhao para fora em +x); o esquerdo e o espelho dele
    import trimesh
    from manifold3d import Mesh
    t = trimesh.load(ORIGINAIS / "gearbox.stl")
    cx = Manifold(Mesh(vert_properties=np.asarray(t.vertices, dtype=np.float32),
                       tri_verts=np.asarray(t.faces, dtype=np.uint32)))
    gravar_stl(espelhar(cx), SAIDA / "gearbox_esquerdo_espelhado.stl", "gearbox espelhado (lado esquerdo)")


if __name__ == "__main__":
    main()
