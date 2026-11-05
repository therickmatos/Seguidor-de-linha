"""Decodifica o projeto EasyEDA Pro do EVA-RT (EVA_RT.eprj, SQLite) para texto e tabela.

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.

Saidas (nesta pasta):
- eprj/<titulo>_<uuid6>.txt : cada documento do projeto, uma primitiva JSON por linha
  (coordenadas em mil; 1 mil = 0,0254 mm). O da placa e eprj/eva_rt_pcb_b73a4a.txt:
  blocos ["DOCTYPE","FOOTPRINT"] com os footprints embutidos e depois o bloco ["DOCTYPE","PCB"].
- eva_rt_componentes.csv : ref;footprint;lado;x_mm;y_mm;rot;valor de cada COMPONENT da placa,
  ja no referencial do seguidor (origem no centro da ventoinha, +y = frente).

Formatos uteis no bloco PCB (EasyEDA Pro 2.2):
  ["COMPONENT", id, ?, camada(1=TOP, 2=BOTTOM), x, y, rot, {atributos}, travado]
  ["ATTR", id, ?, id_do_componente, camada, x, y, chave, valor, ...]   (Designator, Footprint, ...)
  ["PAD", id, ?, rede, camada, numero, x, y, rot, [furo], [forma, w, h, ...], ...]
  ["LINE", ...], ["VIA", ...], ["POLY", ...], ["FILL", ...]  -> trilhas, vias, cobre (com a rede)

Uso: python3 extrair_eprj.py
"""
import base64
import csv
import gzip
import json
import os
import sqlite3

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(AQUI, "..", ".."))
EPRJ = os.path.join(REPO, "referencias", "eva-rt", "pcb_files", "EVA_RT.eprj")
SAIDA = os.path.join(AQUI, "eprj")
MIL = 0.0254


def decodificar():
    os.makedirs(SAIDA, exist_ok=True)
    con = sqlite3.connect(f"file:{EPRJ}?mode=ro", uri=True)
    caminhos = {}
    for uuid, titulo, data in con.execute("select uuid, title, dataStr from documents"):
        assert data.startswith("base64")
        texto = gzip.decompress(base64.b64decode(data[6:])).decode("utf-8", "replace")
        caminho = os.path.join(SAIDA, f"{titulo}_{uuid[:6]}.txt")
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(texto)
        caminhos[(titulo, uuid[:6])] = caminho
        print(f"{titulo:24s} {len(texto):8d} caracteres -> {os.path.relpath(caminho, AQUI)}")
    return caminhos


def tabela_componentes(caminho_pcb):
    linhas = open(caminho_pcb, encoding="utf-8").read().splitlines()
    ini = next(k for k, l in enumerate(linhas) if l.startswith('["DOCTYPE","PCB"'))
    comps, attrs = {}, {}
    for l in linhas[ini:]:
        try:
            r = json.loads(l)
        except json.JSONDecodeError:
            continue
        if r[0] == "COMPONENT":
            comps[r[1]] = r
        elif r[0] == "ATTR" and r[3]:
            attrs.setdefault(r[3], {})[r[7]] = r[8]
    saida = os.path.join(AQUI, "eva_rt_componentes.csv")
    with open(saida, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\n")
        w.writerow(["ref", "footprint", "lado", "x_mm", "y_mm", "rot", "valor"])
        for cid, r in comps.items():
            a = attrs.get(cid, {})
            lado = {1: "TOP", 2: "BOT"}.get(r[3], r[3])
            w.writerow([a.get("Designator", "?"), a.get("Footprint", "?"), lado,
                        f"{r[4] * MIL:.2f}", f"{r[5] * MIL:.2f}", r[6], r[7].get("Value", "")])
    print(f"{len(comps)} componentes -> {os.path.relpath(saida, AQUI)}")


if __name__ == "__main__":
    docs = decodificar()
    tabela_componentes(docs[("eva_rt_pcb", "b73a4a")])
