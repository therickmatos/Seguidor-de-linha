"""Gera REDES.md (lista de redes legível) a partir da netlist exportada pelo KiCad (kicadsexpr).

Uso (nesta pasta): python3 redes.py [seguidor_base.net] [../../hardware/seguidor_base/REDES.md]
"""
import re, sys

src = sys.argv[1] if len(sys.argv) > 1 else "seguidor_base.net"
out = sys.argv[2] if len(sys.argv) > 2 else "../../hardware/seguidor_base/REDES.md"
txt = open(src, encoding="utf-8").read()

def parse(s):
    toks = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', s)
    stack = [[]]
    for t in toks:
        if t == "(":
            stack.append([])
        elif t == ")":
            x = stack.pop(); stack[-1].append(x)
        else:
            stack[-1].append(t[1:-1] if t.startswith('"') else t)
    return stack[0][0]

root = parse(txt)
def child(node, name):
    return [c for c in node if isinstance(c, list) and c and c[0] == name]
def val(node, name):
    c = child(node, name)
    return c[0][1] if c and len(c[0]) > 1 else None

comps = {}
for c in child(child(root, "components")[0], "comp"):
    comps[val(c, "ref")] = val(c, "value")

def natkey(s):
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", s)]

nets, ncs = [], []
for n in child(child(root, "nets")[0], "net"):
    name = val(n, "name").lstrip("/")
    nodes = []
    for nd in child(n, "node"):
        ref, pin, fn = val(nd, "ref"), val(nd, "pin"), val(nd, "pinfunction")
        nodes.append((ref, pin, fn))
    nodes.sort(key=lambda t: (natkey(t[0]), natkey(t[1])))
    if name.startswith("unconnected-"):
        ncs.extend(nodes)
    else:
        nets.append((name, nodes))

order = {"VBAT": 0, "+5V": 1, "GND": 2}
nets.sort(key=lambda t: (order.get(t[0], 3), natkey(t[0])))

def fmt(ref, pin, fn):
    s = f"{ref}.{pin}"
    if fn and fn != pin and not fn.startswith("Pin_"):
        s += f" ({fn})"
    return s

L = []
L.append("# Redes da placa base (conferência da importação KiCad → EasyEDA)")
L.append("")
L.append("_Gerado por `ferramentas/esquematico/redes.py` a partir da netlist do `seguidor_base.kicad_sch` (rev 1.0). "
         "Depois de importar o esquemático no EasyEDA Pro, conferir rede por rede. "
         "Formato: `REF.pino (nome do pino)`. Valores e encapsulamentos em `BOM_seguidor_base.csv`._")
L.append("")
L.append(f"**{len(nets)} redes**, **{len(ncs)} pinos sem ligação**.")
L.append("")
L.append("**Atenção na importação:**")
L.append("- No símbolo do ATmega (U1), os pinos 5 e 21 (GND) e 6 (VCC) estão escondidos e empilhados sobre os pinos 3 e 4; "
         "no KiCad eles se ligam pela posição. Conferir no EasyEDA se U1.5 e U1.21 estão no GND e U1.6 no +5V.")
L.append("- `VBAT`, `+5V` e `GND` vêm de símbolos de alimentação (ligação pelo nome): conferir que chegaram com esses nomes.")
L.append("")
L.append("| Rede | Pinos | Qtd |")
L.append("|---|---|---|")
for name, nodes in nets:
    L.append(f"| `{name}` | {', '.join(fmt(*t) for t in nodes)} | {len(nodes)} |")
L.append("")
L.append("## Pinos sem ligação (marcados com X)")
L.append("")
for t in ncs:
    L.append(f"- {fmt(*t)} — {comps.get(t[0], '')}")
L.append("")
open(out, "w", encoding="utf-8").write("\n".join(L))
print(len(nets), "redes;", len(ncs), "NC;", sum(len(n) for _, n in nets), "nós")
