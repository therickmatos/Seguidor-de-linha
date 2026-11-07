import json, csv, os, re, shutil, zipfile
from collections import OrderedDict
out = 'pacote/seguidor_base'
if os.path.isdir('pacote'): shutil.rmtree('pacote')
os.makedirs(out)
sch = open('seguidor_base.kicad_sch').read()
# --- biblioteca local com os 2 simbolos proprios
def block(txt, start):
    d = 0
    for i in range(start, len(txt)):
        if txt[i] == '(': d += 1
        elif txt[i] == ')':
            d -= 1
            if d == 0: return txt[start:i + 1]
syms = []
for name in ('DRV8874PWP', 'VBAT'):
    i = sch.index(f'(symbol "seguidor:{name}"')
    syms.append(block(sch, i).replace(f'"seguidor:{name}"', f'"{name}"'))
open(f'{out}/seguidor.kicad_sym', 'w').write('(kicad_symbol_lib (version 20220914) (generator kicad_symbol_editor)\n  ' + '\n  '.join(syms) + '\n)\n')
open(f'{out}/sym-lib-table', 'w').write('(sym_lib_table\n  (version 7)\n  (lib (name "seguidor")(type "KiCad")(uri "${KIPRJMOD}/seguidor.kicad_sym")(options "")(descr "DRV8874PWP e simbolo de alimentacao VBAT"))\n)\n')
json.dump({"meta": {"filename": "seguidor_base.kicad_pro", "version": 1}, "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
           "sheets": [], "text_variables": {}}, open(f'{out}/seguidor_base.kicad_pro', 'w'), indent=2)
shutil.copy('seguidor_base.kicad_sch', out)
shutil.copy('seguidor_base.pdf', out)
# --- BOM
bom = json.load(open('intent.json'))['bom']
opt = {'R2': 'opcional (bateria)', 'R3': 'opcional (bateria)', 'C6': 'opcional (bateria)'}
# designador do EVA-RT para as pecas que mudaram (numeracao por bloco de 07/11 aqui; a do EVA-RT entre aspas)
eva = {'J1': 'VIN', 'J2': 'FPC1 (FPC 10 vias)', 'U3': 'IFX_A1 (IFX9201)', 'U4': 'IFX_B1 (IFX9201)', 'J3': 'Converter Conn Master',
       'J5': 'USB to ASP Conn Master', 'Q1': 'Q1 (outro MOSFET)', 'X1': 'X1 (ressonador 3 pinos)', 'R10': 'R3 (1k)'}
new = {'R12', 'C14', 'R3', 'R13', 'C9', 'C10', 'D1', 'R11', 'R22', 'R14', 'C15', 'R21', 'R15', 'R2', 'C11', 'R20', 'C12', 'C6', 'C18', 'J4'}
def key(r):
    m = re.match(r'([A-Z]+)(\d+)', r); return (m.group(1), int(m.group(2)))
groups = OrderedDict()
for r in sorted(bom, key=key):
    v = bom[r]; mont = 'nao montar (DNP)' if v['dnp'] else opt.get(r, 'sim')
    k = (v['value'], v['pkg'], v['lcsc'], mont)
    groups.setdefault(k, dict(refs=[], notes=[], eva=[]))
    g = groups[k]; g['refs'].append(r)
    if v['note'] and v['note'] not in g['notes']: g['notes'].append(v['note'])
    e = 'novo' if r in new else eva.get(r, 'igual')
    if e not in g['eva']: g['eva'].append(e)
rows = [['Qtd', 'Referencias', 'Valor', 'Encapsulamento', 'LCSC', 'Montagem', 'EVA-RT', 'Observacao']]
for (val, pkg, lcsc, mont), g in sorted(groups.items(), key=lambda kv: (kv[0][3] != 'sim', key(kv[1]['refs'][0]))):
    rows.append([len(g['refs']), ' '.join(g['refs']), val, pkg, lcsc, mont, '; '.join(g['eva']), '; '.join(g['notes'])])
with open(f'{out}/BOM_seguidor_base.csv', 'w', newline='', encoding='utf-8-sig') as f:
    csv.writer(f, delimiter=';').writerows(rows)
print(len(rows) - 1, 'linhas na BOM,', sum(r[0] for r in rows[1:]), 'pecas')
json.dump(rows, open('bom_rows.json', 'w'))
