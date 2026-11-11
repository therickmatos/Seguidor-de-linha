# Ferramentas do perseguidor (`.epro` do EasyEDA Pro)

Usadas na revisão de `Perseguidor de linha/`. Trabalham sobre o `.epro` **descompactado** (é um zip).
Requer `pip install shapely numpy matplotlib pillow`.

- `epro.py` – lê projeto, componentes, pads (com o espelhamento da face de baixo do EasyEDA), trilhas, vias, polígonos e contorno.
- `drc.py <pasta>` – redes abertas, curtos, folga < 0,2 mm, cobre perto da borda/furos (usa o preenchimento `POURED` salvo).
- `poursim.py <pasta>` – o mesmo, mas recalcula os polígonos de GND (para quando o preenchimento foi apagado).
- `render.py <pasta> <png> [camadas] [xmin,xmax,ymin,ymax]` – figura das camadas.
- `router.py` – roteador A* em grade de 0,1 mm, 2 camadas.
- `j6.py`, `build.py <origem> <destino>` – geram o J6 (KY-022) e as rotas a partir da placa original.
- `stl.py` – lê os STL do EVA-RT (conferência mecânica).
