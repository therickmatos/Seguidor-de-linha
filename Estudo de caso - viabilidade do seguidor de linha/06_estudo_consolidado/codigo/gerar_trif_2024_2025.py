"""Gera o simulador local autocontido com somente os modelos TRIF 2025/2024."""
import json
import math
import re
from pathlib import Path
import numpy as np
import simular_comparar as model
import pista_trif2025 as track25
import pista_c_regulamentar as track24

HERE=Path(__file__).resolve().parent
CASE=model.CASE
STEP=.5


def build_data():
    b,bcycle,bmarks,bmeta=track25.build(STEP)
    c,ccycle,cmarks,cmeta=track24.build(STEP)
    specs=[
        (f'TRIF 2025 · modelo inspirado nas fotos · {len(bmarks)} marcas',b,bcycle,bmarks,bmeta,False),
        (f'TRIF 2024 · modelo espelhado · {len(cmarks)} marcas',c,ccycle,cmarks,cmeta,True),
    ]
    tracks=[]
    for name,track,cycle,marks,meta,is24 in specs:
        extra=dict(crossing=meta['crossing'],crossing_s=meta['crossing_s'],
                   crossing_second_s=meta['crossing_second_s'],photo=True,rule_based=True,
                   display_rotate=False,estimated=meta['estimated'])
        if is24:extra['mat']=meta['mat']
        points=np.vstack([cycle[::3,1:3],cycle[-1,1:3]])
        tracks.append(dict(name=name,track=track.round(5).tolist(),cycle=points.round(3).tolist(),
                           marks=sorted(marks,key=lambda m:m['s']),start=meta['start'],end=meta['end'],**extra))
    raw=json.loads((CASE/'03_simulacoes/02_ajuste_8mm_1mm/comparacao_animacao.json').read_text(encoding='utf8'))
    geo=raw['geometry']
    return dict(tracks=tracks,outline=[[round(a,3),round(b,3)] for a,b,_,_ in geo['outline_segments']],
                front=geo['front_sensor_centres'],wheels=geo['wheel_hulls'],axle=model.AXLE,
                Lholes=model.L_HOLE,Lgap=model.L_GAP)


def static_svg(t,rotate=False):
    def project(x,y):
        if rotate:x,y=-y,x
        return x,-y
    p=[project(*q) for q in t['cycle']];xs=[q[0] for q in p];ys=[q[1] for q in p]
    pad=300 if t.get('mat') else 180
    x0=min(xs)-pad;y0=min(ys)-pad;w=max(xs)-min(xs)+2*pad;h=max(ys)-min(ys)+2*pad
    stride=max(1,math.ceil(len(p)/1400));points=' '.join(f'{x:.1f},{y:.1f}' for x,y in (p[::stride]+[p[-1],p[0]]))
    out=[f'<svg role="img" aria-label="{t["name"]}" viewBox="{x0:.1f} {y0:.1f} {w:.1f} {h:.1f}" xmlns="http://www.w3.org/2000/svg">',
         f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{h:.1f}" fill="#111822"/>']
    if t.get('mat'):
        xa,ya,xb,yb=t['mat'];corners=[project(xa,ya),project(xb,ya),project(xb,yb),project(xa,yb)]
        poly=' '.join(f'{x:.1f},{y:.1f}' for x,y in corners)
        out.append(f'<polygon points="{poly}" fill="#17222c" stroke="#526473" stroke-width="4"/>')
    out.append(f'<polyline points="{points}" fill="none" stroke="#f4f6f3" stroke-width="19" stroke-linecap="round" stroke-linejoin="round"/>')
    for m in t['marks']:
        c,s=math.cos(m['phi']),math.sin(m['phi']);side=m['side'];half=m.get('halfWidth',9.5)
        inner=m.get('inner',49.5);outer=m.get('outer',89.5);corners=[]
        for u,v in [(-half,inner),(half,inner),(half,outer),(-half,outer)]:
            x,y=project(m['x']+u*c-v*side*s,m['y']+u*s+v*side*c);corners.append(f'{x:.1f},{y:.1f}')
        out.append(f'<polygon points="{" ".join(corners)}" fill="{"#f474ad" if side<0 else "#8dbde3"}"/>')
    for segment in t.get('estimated',[]):
        q=' '.join(f'{x:.1f},{y:.1f}' for x,y in (project(*r) for r in segment[::2]))
        out.append(f'<polyline points="{q}" fill="none" stroke="#f9bf5d" stroke-width="8" stroke-dasharray="22 15"/>')
    x,y=project(*t['crossing']);out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="28" fill="none" stroke="#6dceff" stroke-width="8"/>')
    return ''.join(out)+'</svg>'


def render(data):
    template=(HERE/'painel_template.html').read_text(encoding='utf8')
    template=template.replace('Duas pistas de teste, incluindo uma inspirada nas fotos do TRIF 2025. O ponto virtual central da barra permanece sobre a linha; ajuste as medidas e inspecione as marcas.',
        'Dois modelos inspirados em fotografias e no rascunho do TRIF 2025. Um sensor de marca por lado; as pistas não são plantas oficiais.')
    template=template.replace('Pista A · 19 marcas','TRIF 2025 · modelo inspirado nas fotos')
    template=template.replace('Pista B · inspirada no TRIF 2025','TRIF 2024 · modelo espelhado')
    template=template.replace('A pista B é uma aproximação das fotos; o traçado e as medidas exatas não foram fornecidos.',
        'Ambas as pistas são aproximações: dimensões, trechos ocultos e marcas não reproduzem uma planta oficial.')
    template=template.replace('<strong>Pista C:</strong>','<strong>TRIF 2024:</strong>')
    allowed={'holes','one_asym68','one_out1','one_out2','one_sym1','one_sym2','one_60','one_60_68','one_60_685','wide','custom'}
    def keep_options(match):
        return re.sub(r'<option value="([^"]+)">.*?</option>',lambda o:o.group(0) if o.group(1) in allowed else '',match.group(0))
    template=re.sub(r'<select id="preset">.*?</select>',keep_options,template,count=1,flags=re.S)
    details='''<details class="panel"><summary>Premissas, limites e como interpretar</summary>
    <ul>
      <li>TRIF 2025: modelo revisado conforme o rascunho aéreo e as fotografias fornecidas. TRIF 2024: modelo espelhado a pedido do usuário. Nenhuma é planta oficial; a escala e as posições das marcas são estimadas.</li>
      <li>Em ambos, faixa de 19 mm e marcas de 19 × 40 mm a 40 mm da borda; na esquerda ao mudar a curvatura, na direita para partida e chegada. A conferência é geométrica; portas, aderência, desníveis e montagem real não foram certificados.</li>
      <li>Fitas nominais intersectadas conta o centro pontual do QRE ao atravessar o retângulo. A região comum é uma faixa mais conservadora, não uma probabilidade e não prova sinal óptico. Passagens curtas são destacadas.</li>
      <li>Um QRE esquerdo e um direito; posição original X = ±69,5 mm e Y = 4,5 mm. A distância entre furos não é L: L vai do eixo ao ponto central virtual da barra.</li>
      <li>A barra segue a linha ou uma trajetória com desvio lateral fixo. O corpo é rígido e sem derrapagem; o caminho no cruzamento é imposto. Não são modelados PID, motores, tempo, óptica, ADC nem falsos sinais.</li>
      <li>O destaque amarelo representa trecho fora da foto, desenhado por hipótese. As marcas de curva ficam à esquerda e as de partida e chegada à direita no sentido do robô; suas posições são nominais, não medições das fotos.</li>
    </ul>
    <p>Fontes: <a href="https://ifsp.edu.br/index.php/trif/83-pesquisa/6044-trif2026">IFSP · TRIF 2026</a>; <a href="https://github.com/EXOTIC-TEAM-MX/EVA-RT">EVA-RT · projeto original</a>.</p></details>'''
    template=re.sub(r'<details class="panel">.*?</details>',details,template,count=1,flags=re.S)
    template=template.replace('rightOverride=null, barOffset=0, zoomed=true,','rightOverride=null, barOffset=0, zoomed=false,')
    template=template.replace('selected=7, timer=null,viewCross=false;','selected=0, timer=null,viewCross=false;')
    template=template.replace('<button id="zoom">Ver pista inteira</button>','<button id="zoom">Ver detalhe</button>')
    template=template.replace("$('course').append(o)});", "$('course').append(o)});$('course').value=String(course);")
    old="$('course').addEventListener('change',()=>{course=Number($('course').value);selected=course===0?7:(DATA.tracks[course].photo?0:2);zoomed=course===0;$('zoom').textContent=zoomed?'Ver pista inteira':'Ver detalhe';playing=false;$('play').textContent='Simular percurso';compute();if(DATA.tracks[course].photo){tick=nearest(DATA.tracks[course].start);$('progress').value=0;draw()}});"
    new="$('course').addEventListener('change',()=>{course=Number($('course').value);selected=DATA.tracks[course].photo?0:2;zoomed=false;$('zoom').textContent='Ver detalhe';playing=false;$('play').textContent='Simular percurso';compute();tick=nearest(DATA.tracks[course].start);$('progress').value=0;draw()});"
    if old not in template:raise ValueError('Controle de troca de pista não encontrado no painel.')
    template=template.replace(old,new)
    template=template.replace("changePreset();resize();document.body.classList.replace('initializing','ready');",
        "changePreset();tick=nearest(DATA.tracks[course].start);$('progress').value=0;resize();document.body.classList.replace('initializing','ready');")
    return (template.replace('/*__DADOS_DA_PISTA__*/',json.dumps(data,ensure_ascii=False,separators=(',',':')))
        .replace('<!--__PREVIA_PISTA_A__-->',static_svg(data['tracks'][0]))
        .replace('<!--__PREVIA_PISTA_B__-->',static_svg(data['tracks'][1]))
        .replace('<!--__PREVIA_PISTA_C_FIGURE__-->',''))


def main():
    data=build_data();assert len(data['tracks'])==2
    html=render(data)
    target=(HERE.parent/'simulador.html') if HERE.name=='codigo' else (HERE/'simulador_pista_foto.html')
    target.write_text(html,encoding='utf8',newline='\n')
    print(f'Simulador: {target} ({len(html.encode("utf8"))} bytes); somente TRIF 2025 e 2024.')


if __name__=='__main__':main()
