"""Monta hardware/placa_base_alpha.zip: projeto KiCad (esquematico + placa + biblioteca), pacote para o
EasyEDA (placa_alpha/) e a previa 3D. Rodar depois do kicad_montar.py:  python3 empacotar.py

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
import datetime
import os
import zipfile

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
HW = os.path.join(RAIZ, 'hardware')
SAIDA = os.path.join(HW, 'placa_base_alpha.zip')

LEIA = """Placa base do seguidor de linha - versao alpha ({data})
Baseado no EVA-RT (c) EXOTIC TEAM MX - AGPL-3.0.

seguidor_base/   projeto KiCad 7: abra seguidor_base.kicad_pro (esquematico + placa ligados).
                 seguidor_alpha.pretty = footprints da previa (aproximados: troque pelos da LCSC).
                 drc_kicad.rpt = DRC do proprio KiCad. BOM e REDES.md para conferir a importacao.
placa_alpha/     pacote para o EasyEDA Pro (README com o passo a passo, imagens, CSV, DXF).
placa_3d.html    previa 3D (abre no navegador; precisa de internet para carregar o three.js).

Origem no centro da ventoinha, +y = frente, mm. Repositorio: github.com/therickmatos/Seguidor-de-linha
"""


def main():
    itens = []
    for pasta in ('seguidor_base', 'placa_alpha'):
        base = os.path.join(HW, pasta)
        for raiz, _, arquivos in os.walk(base):
            for a in sorted(arquivos):
                if a.endswith(('.lck', '-bak', '.kicad_prl')) or a == 'fp-info-cache':
                    continue
                cam = os.path.join(raiz, a)
                itens.append((cam, os.path.relpath(cam, HW)))
    itens.append((os.path.join(HW, 'preview', 'placa_3d.html'), 'placa_3d.html'))
    with zipfile.ZipFile(SAIDA, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('LEIA-ME.txt', LEIA.format(data=datetime.date.today().strftime('%d/%m/%Y')))
        for cam, nome in itens:
            z.write(cam, nome)
    print(SAIDA, len(itens) + 1, 'arquivos, %.1f MB' % (os.path.getsize(SAIDA) / 1e6))


if __name__ == '__main__':
    main()
