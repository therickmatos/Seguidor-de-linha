"""Testes da biblioteca de footprints (footprints.py).

Confere:
1. Toda referencia da BOM tem footprint e o footprint existe.
2. Todo REF.pino do REDES.md existe como rede_pino no footprint do REF.
3. Nenhum pad (nem furo) sobrepoe outro dentro do mesmo footprint.
4. Campos obrigatorios, cortesia >= corpo, pino unico por footprint.
5. Posicoes conferidas com os pads reais do EVA-RT (ICSP, asas, motores, TQFP).
Le a BOM e o REDES.md do repositorio em modo somente leitura.
"""

import os as _os
_REPO = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))
import csv
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import footprints as F  # noqa: E402

BOM = _REPO + "/hardware/seguidor_base/BOM_seguidor_base.csv"
REDES = _REPO + "/hardware/seguidor_base/REDES.md"

falhas = []
avisos = []
n_ok = 0


def ok(msg):
    global n_ok
    n_ok += 1


def falha(msg):
    falhas.append(msg)


def aviso(msg):
    avisos.append(msg)


# ------------------------------------------------------------------ 1. BOM
refs_bom = []
with open(BOM, encoding="utf-8-sig", newline="") as f:
    for linha in csv.DictReader(f, delimiter=";"):
        refs_bom += linha["Referencias"].split()
refs_bom = sorted(set(refs_bom))
print(f"BOM: {len(refs_bom)} referencias")
for r in refs_bom:
    if r not in F.REF_FOOTPRINT:
        falha(f"BOM: {r} sem footprint em REF_FOOTPRINT")
    elif F.REF_FOOTPRINT[r] not in F.FOOTPRINTS:
        falha(f"BOM: {r} aponta para footprint inexistente {F.REF_FOOTPRINT[r]}")
    else:
        ok("bom")
extras = sorted(set(F.REF_FOOTPRINT) - set(refs_bom))
if extras:
    aviso(f"REF_FOOTPRINT tem referencias fora da BOM: {extras}")
for nome, alts in F.ALTERNATIVAS.items():
    for a in alts:
        if a not in F.FOOTPRINTS:
            falha(f"alternativa {a} de {nome} nao existe")
for nome in F.FOOTPRINTS:
    if nome not in F.REF_FOOTPRINT.values() and not any(nome in v for v in F.ALTERNATIVAS.values()):
        aviso(f"footprint {nome} nao usado por nenhuma referencia nem alternativa")

# ------------------------------------------------------------------ 2. campos e geometria basica
CHAVES = {"pads", "corpo", "cortesia", "altura_mm", "tht", "obs"}
for nome, fp in F.FOOTPRINTS.items():
    if not CHAVES <= set(fp):
        falha(f"{nome}: faltam campos {CHAVES - set(fp)}")
        continue
    ok("campos")
    if not fp["obs"].strip():
        falha(f"{nome}: obs vazio")
    if fp["corpo"][0] > 0 and fp["corpo"][1] > 0:
        if not (fp["cortesia"][0] >= fp["corpo"][0] and fp["cortesia"][1] >= fp["corpo"][1]):
            falha(f"{nome}: cortesia menor que corpo")
        else:
            ok("cortesia")
    pinos = [p["pino"] for p in fp["pads"]]
    if len(pinos) != len(set(pinos)):
        falha(f"{nome}: pinos repetidos {sorted(set(p for p in pinos if pinos.count(p) > 1))}")
    else:
        ok("pino unico")
    for p in fp["pads"]:
        if p["forma"] not in ("rect", "oval", "round"):
            falha(f"{nome}: forma invalida {p['forma']}")
        if p["w"] <= 0 or p["h"] <= 0:
            falha(f"{nome}: pad {p['pino']} sem tamanho")
        if p["furo"] is not None and p["furo"] >= min(p["w"], p["h"]):
            falha(f"{nome}: furo {p['furo']} maior que o pad {p['pino']} ({p['w']}x{p['h']})")
        else:
            ok("pad")


# ------------------------------------------------------------------ 3. REDES.md
texto = open(REDES, encoding="utf-8").read()
pares = set(re.findall(r"(?<![\w-])([A-Z]{1,3}\d{1,2})\.(\d{1,2})(?!\d)", texto))
print(f"REDES.md: {len(pares)} pares REF.pino distintos")
mapa = {}
for ref, pino in pares:
    if ref not in F.REF_FOOTPRINT:
        falha(f"REDES cita {ref}.{pino} mas {ref} nao esta na BOM/REF_FOOTPRINT")
        continue
    fp = F.FOOTPRINTS[F.REF_FOOTPRINT[ref]]
    rede_pads = {p["rede_pino"] for p in fp["pads"] if p["rede_pino"] is not None}
    if pino in rede_pads:
        ok("redes")
    else:
        falha(f"REDES {ref}.{pino} sem pad com rede_pino={pino} em {F.REF_FOOTPRINT[ref]}")
    mapa.setdefault(ref, set()).add(pino)

# reverso: pad com rede_pino que nao aparece no REDES
for ref, nome in F.REF_FOOTPRINT.items():
    if ref not in refs_bom:
        continue
    fp = F.FOOTPRINTS[nome]
    for p in fp["pads"]:
        if p["rede_pino"] is not None and p["rede_pino"] not in mapa.get(ref, set()):
            aviso(f"{ref}: pad {p['pino']} com rede_pino={p['rede_pino']} nao aparece no REDES.md")


# ------------------------------------------------------------------ 4. sobreposicao
def _meia(p):
    return p["w"] / 2.0, p["h"] / 2.0


def _sobrepoe_copper(a, b, tol=0.01):
    if a["forma"] == "round" and b["forma"] == "round":
        d = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
        return (a["w"] + b["w"]) / 2.0 - d > tol
    if a["forma"] == "round" or b["forma"] == "round":
        c, r = (a, b) if a["forma"] == "round" else (b, a)
        hw, hh = _meia(r)
        dx = max(abs(c["x"] - r["x"]) - hw, 0.0)
        dy = max(abs(c["y"] - r["y"]) - hh, 0.0)
        return math.hypot(dx, dy) < c["w"] / 2.0 - tol
    ha, hb = _meia(a), _meia(b)
    return (abs(a["x"] - b["x"]) < ha[0] + hb[0] - tol) and (abs(a["y"] - b["y"]) < ha[1] + hb[1] - tol)


def _sobrepoe_furo(furo, pad):
    # furo circular centrado no pad; testa contra o cobre de outro pad
    r = furo["furo"] / 2.0
    if pad["forma"] == "round":
        return math.hypot(furo["x"] - pad["x"], furo["y"] - pad["y"]) < r + pad["w"] / 2.0 - 0.01
    hw, hh = _meia(pad)
    dx = max(abs(furo["x"] - pad["x"]) - hw, 0.0)
    dy = max(abs(furo["y"] - pad["y"]) - hh, 0.0)
    return math.hypot(dx, dy) < r - 0.01


for nome, fp in F.FOOTPRINTS.items():
    pads = fp["pads"]
    for i in range(len(pads)):
        for j in range(i + 1, len(pads)):
            a, b = pads[i], pads[j]
            if _sobrepoe_copper(a, b):
                falha(f"{nome}: pad {a['pino']} sobrepoe pad {b['pino']}")
            else:
                ok("sobreposicao")
    for i, a in enumerate(pads):
        if a["furo"] is None:
            continue
        for j, b in enumerate(pads):
            if i == j:
                continue
            if _sobrepoe_furo(a, b):
                falha(f"{nome}: furo do pad {a['pino']} invade o cobre do pad {b['pino']}")
            elif b["furo"] is not None and j > i:
                d = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
                if d < (a["furo"] + b["furo"]) / 2.0 + 0.1:
                    falha(f"{nome}: furos {a['pino']} e {b['pino']} muito proximos")
                else:
                    ok("furo")


# ------------------------------------------------------------------ 5. conferencia com o EVA-RT
def _ref_pos(ref, x, y, rot, lado):
    return {p["pino"]: (p["x"], p["y"], p["rede_pino"]) for p in F.pads_absolutos(ref, x, y, rot, lado)}


def _confere(titulo, pos, esperado, tol=0.005):
    for pino, (ex, ey) in esperado.items():
        if pino not in pos:
            falha(f"{titulo}: pad {pino} nao existe")
            continue
        x, y, _ = pos[pino]
        if abs(x - ex) > tol or abs(y - ey) > tol:
            falha(f"{titulo}: pad {pino} em ({x:.3f},{y:.3f}), EVA-RT ({ex:.3f},{ey:.3f})")
        else:
            ok("eva-rt")


# ICSP (J5) no EVA-RT, face BOTTOM: centro (35,244; -10,901)
_confere("J5 ICSP", _ref_pos("J5", 35.244, -10.901, 0, "BOTTOM"), {
    "1": (36.514, -8.361), "2": (33.974, -8.361), "3": (36.514, -10.901),
    "4": (33.974, -10.901), "5": (36.514, -13.441), "6": (33.974, -13.441)})
# nets reais do PCB do EVA-RT: pino 1 MISO (D12) 36,51/-8,36 ; pino 2 +5V ; pino 4 MOSI ; pino 6 GND
_pos_j5 = _ref_pos("J5", 35.244, -10.901, 0, "BOTTOM")
if _pos_j5["6"][2] != "6":
    falha("J5 pino 6 deveria ser GND")
# asas: J8 (esq.) e J9 (dir.), centro y 4,5085
_confere("J8 asa esq.", _ref_pos("J8", -45.044, 4.5085, 0, "TOP"), {
    "1": (-45.044, 5.08), "2": (-45.044, 6.223), "3": (-45.044, 3.937), "4": (-45.044, 2.794)})
_confere("J9 asa dir.", _ref_pos("J9", 45.044, 4.5085, 0, "TOP"), {
    "1": (45.044, 3.937), "2": (45.044, 2.794), "3": (45.044, 5.08), "4": (45.044, 6.223)})
# motores: M1 (esq.), M2 (dir.) e M3 (ventoinha)
_confere("M1", _ref_pos("M1", -36.576, 1.27, 0, "TOP"), {"1": (-36.576, 0.0), "2": (-36.576, 2.54)})
_confere("M2", _ref_pos("M2", 36.576, 1.27, 0, "TOP"), {"1": (36.576, 0.0), "2": (36.576, 2.54)})
_confere("M3", _ref_pos("M3", 29.718, 3.048, 0, "TOP"), {"1": (29.718, 1.778), "2": (29.718, 4.318)})
# TQFP-32 (U1): medidas do EasyEDA (mil convertidas)
_confere("U1 TQFP", _ref_pos("U1", 0, 0, 0, "TOP"), {
    "1": (-2.8, -4.269), "8": (2.8, -4.269), "9": (4.282, -2.8), "16": (4.282, 2.8),
    "17": (2.8, 4.269), "24": (-2.8, 4.269), "25": (-4.281, 2.8), "32": (-4.281, -2.8)})
# HTSSOP-16 (U2): pino 1 canto superior-esquerdo, 9 inferior-direito
_confere("U2 HTSSOP", _ref_pos("U2", 0, 0, 0, "TOP"), {
    "1": (-2.775, 2.275), "8": (-2.775, -2.275), "9": (2.775, -2.275), "16": (2.775, 2.275)})
# Rotacao: pad (1,0) girado 90 graus vai para (0,1); lado BOTTOM espelha x
_teste_rot = F.pads_absolutos("R1", 0, 0, 90, "TOP")
_p1 = [p for p in F.pads_absolutos("R1", 0, 0, 0, "TOP") if p["pino"] == "2"][0]
_p1r = [p for p in _teste_rot if p["pino"] == "2"][0]
if abs(_p1r["x"] - 0.0) > 1e-9 or abs(_p1r["y"] - _p1["x"]) > 1e-9:
    falha("rotacao de 90 graus incorreta em pads_absolutos")
else:
    ok("rotacao")
_p_bot = [p for p in F.pads_absolutos("R1", 0, 0, 0, "BOTTOM") if p["pino"] == "2"][0]
if abs(_p_bot["x"] + _p1["x"]) > 1e-9:
    falha("espelhamento BOTTOM incorreto em pads_absolutos")
else:
    ok("espelho")

# ------------------------------------------------------------------ resultado
print(f"verificacoes OK: {n_ok}")
for a in avisos:
    print("AVISO:", a)
for f_ in falhas:
    print("FALHA:", f_)
if falhas:
    print(f"RESULTADO: {len(falhas)} falha(s)")
    sys.exit(1)
print("RESULTADO: OK (todas as verificacoes passaram)")
