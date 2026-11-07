"""Renumeracao dos designadores por bloco (07/11/2026), na ordem dos blocos do esquematico:
1 Alimentacao, 2 Barra de sensores, 3 Sensores de marca, 4 Microcontrolador, 5 Pontes H,
6 Ventoinha, 7 Interface, 8 Gravacao/Bluetooth/ICSP. Dentro de cada bloco, na ordem de leitura.

ANTIGO_NOVO vale para o repositorio (KiCad, previa, kit do EasyEDA). No esquematico do Erick
(EasyEDA, projeto RUSH) o cristal estava como U4; ali ele vira X1 (EPRO_EXTRA).
Saem da referencia: LED7/R2 (LED de RX, nao montado desde 06/11) e J8/J9 (conectores das asas,
que nao existem com os bracos integrados).

Uso como biblioteca (mapa e funcao de troca) ou como script:
  python designadores.py tabela   -> imprime a tabela em Markdown

Baseado no EVA-RT (c) EXOTIC TEAM MX, AGPL-3.0.
"""
import re
import sys

BLOCOS = [
    ('1 - Alimentação', ['J1', 'C1', 'C2', 'C3', 'U5', 'C4', 'C5', 'R10', 'LED5', 'R23', 'R24', 'C18']),
    ('2 - Barra de sensores', ['J2']),
    ('3 - Sensores de marca', ['R20', 'S0', 'R30', 'R6', 'LED1', 'R21', 'S1', 'R31', 'R7', 'LED2']),
    ('4 - Microcontrolador', ['U1', 'R3', 'C9', 'C10', 'SW0', 'X1', 'C11', 'C12']),
    ('5 - Pontes H', ['U2', 'C13', 'C14', 'C6', 'R13', 'R14', 'R15', 'R11', 'M1',
                      'U3', 'C15', 'C16', 'C7', 'R12', 'M2']),
    ('6 - Ventoinha', ['M3', 'R9', 'R8', 'Q1', 'C8', 'D1']),
    ('7 - Interface', ['SW1', 'SW2', 'R5', 'LED4', 'R1', 'LED6']),
    ('8 - Gravação, Bluetooth e ICSP', ['J3', 'C17', 'R16', 'R17', 'R18', 'J4', 'J5']),
]
REMOVIDOS = ['LED7', 'R2', 'J8', 'J9']
EPRO_EXTRA = {'U4': 'X1'}      # no projeto do EasyEDA o cristal era U4


def _prefixo(ref):
    return re.match(r'[A-Z]+', ref).group(0)


def _montar():
    cont = {}
    mapa = {}
    for _, refs in BLOCOS:
        for r in refs:
            p = _prefixo(r)
            n = cont.get(p, 0) + 1
            cont[p] = n
            mapa[r] = f'{p}{n}'
    return mapa


ANTIGO_NOVO = _montar()
NOVO_ANTIGO = {v: k for k, v in ANTIGO_NOVO.items()}
assert len(NOVO_ANTIGO) == len(ANTIGO_NOVO)

_TOKEN = re.compile(r'\b(LED\d+|SW\d+|[RCUJSMQDX]\d+)\b')


def trocar(texto, mapa=ANTIGO_NOVO):
    """Troca, numa passada so, cada designador inteiro (R10, U2.11, LED5...) pelo novo."""
    return _TOKEN.sub(lambda m: mapa.get(m.group(1), m.group(1)), texto)


def tabela_md():
    linhas = ['| Bloco | Antigo → novo |', '|---|---|']
    for nome, refs in BLOCOS:
        pares = ', '.join(f'{r} → **{ANTIGO_NOVO[r]}**' if r != ANTIGO_NOVO[r] else f'{r}' for r in refs)
        linhas.append(f'| {nome} | {pares} |')
    return '\n'.join(linhas)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'tabela':
        print(tabela_md())
    else:
        for k, v in ANTIGO_NOVO.items():
            print(k, '->', v)
