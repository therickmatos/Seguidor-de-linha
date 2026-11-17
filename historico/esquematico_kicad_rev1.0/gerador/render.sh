set -e
python3 gen.py && kicad-cli sch export pdf -o seguidor_base.pdf seguidor_base.kicad_sch >/dev/null && pdftoppm -r 250 -png seguidor_base.pdf hi
python3 - <<'P'
from PIL import Image
import glob
im=Image.open(sorted(glob.glob('hi*.png'))[0]); W,H=im.size; s=W/420
for n,b in dict(z1=(10,12,146,120),z2=(10,120,146,224),z3=(146,12,278,162),z4=(278,12,412,172),z5=(146,162,412,250),z6=(10,226,302,288)).items():
    im.crop(tuple(int(v*s) for v in b)).save(n+'.png')
P
