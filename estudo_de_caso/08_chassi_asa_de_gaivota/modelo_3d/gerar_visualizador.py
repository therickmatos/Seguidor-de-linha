"""Embute robo_v4.glb no visualizador (HTML autocontido; three.js do jsDelivr)."""
from pathlib import Path
import base64, trimesh
HERE = Path(__file__).resolve().parent
glb = (HERE / 'robo_v4.glb').read_bytes()
b = trimesh.load(HERE / 'robo_v4.glb').bounds
comp = f"{b[1][2] - b[0][2]:.1f}".replace('.', ',')
html = (HERE / 'visualizador_template.html').read_text(encoding='utf8')
html = html.replace('__GLB__', base64.b64encode(glb).decode()).replace('__COMP__', comp)
(HERE / 'visualizador.html').write_text(html, encoding='utf8')
print('visualizador.html', len(html), 'bytes; comprimento', comp)
