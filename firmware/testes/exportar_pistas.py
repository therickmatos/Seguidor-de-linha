"""Exporta os modelos de pista TRIF 2025 e 2024 do estudo de caso para o
simulador do firmware (firmware/testes/sim.cpp).

Os modelos estao em "Estudo de caso - viabilidade do seguidor de linha/
06_estudo_consolidado/codigo" (pista_trif2025.py e pista_c_regulamentar.py).
Sao aproximacoes feitas a partir de fotos e rascunhos, nao plantas oficiais.

    pip install numpy scipy shapely matplotlib
    python3 exportar_pistas.py

Formato de pistas/*.txt (mm, uma volta):
    T comprimento curvatura     trecho (curvatura em 1/mm, + = esquerda)
    P s                         marca de partida (direita)
    C s                         marca de chegada (direita)
    X s cotangente              cruzamento (cotangente do angulo entre os ramos)
As marcas da esquerda ficam em toda mudanca de curvatura (regra 4.15).
"""
import math
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ESTUDO = AQUI.parents[1] / 'Estudo de caso - viabilidade do seguidor de linha'
sys.path.insert(0, str(ESTUDO / '06_estudo_consolidado' / 'codigo'))

import pista_trif2025 as trif2025          # noqa: E402
import pista_c_regulamentar as trif2024    # noqa: E402


def exportar(nome, modulo, titulo):
    _, _, marcas, meta = modulo.build(.5)
    blocos = meta['blocks']
    periodo = meta['period']
    inicio = [0.]
    for b in blocos:
        inicio.append(inicio[-1] + b['length'])
    assert abs(inicio[-1] - periodo) < 1e-6

    def rumo(s):
        s %= periodo
        for b, s0 in zip(blocos, inicio):
            if s0 <= s <= s0 + b['length']:
                return b['phi'] + b['k'] * (s - s0)
        raise ValueError(s)

    linhas = [f'# {titulo}',
              '# modelo aproximado do estudo de caso; gerado por exportar_pistas.py',
              f'# volta de {periodo / 1000:.3f} m, {len(blocos)} trechos']
    for b in blocos:
        linhas.append(f"T {b['length']:.4f} {b['k']:.9f}")
    for m in marcas:
        if m['kind'] == 'partida':
            linhas.append(f"P {m['s'] % periodo:.3f}")
        elif m['kind'] == 'chegada':
            linhas.append(f"C {m['s'] % periodo:.3f}")
    s1, s2 = meta['crossing_s'] % periodo, meta['crossing_second_s'] % periodo
    for a, b in ((s1, s2), (s2, s1)):
        alfa = rumo(b) - rumo(a)     # rumo do outro ramo visto deste
        linhas.append(f'X {a:.3f} {math.cos(alfa) / math.sin(alfa):.6f}')
    destino = AQUI / 'pistas' / f'{nome}.txt'
    destino.write_text('\n'.join(linhas) + '\n', encoding='utf8')
    curvas = sum(1 for m in marcas if m['kind'] == 'curva')
    raio = min(1 / abs(b['k']) for b in blocos if b['k'])
    print(f'{destino.name}: {periodo / 1000:.2f} m, {curvas} marcas de curva, raio minimo {raio:.0f} mm')


exportar('trif2025', trif2025, 'TRIF 2025 - modelo inspirado nas fotos')
exportar('trif2024', trif2024, 'TRIF 2024 - modelo espelhado')
