"""Retifica o quadro de vídeo do EVA-RT e sobrepõe o modelo de pista_eva_rt_teste.py.

Usa só numpy, scipy e PIL. Os parâmetros da câmera (distância focal em pixels e
pose do plano da placa, centro óptico suposto no centro da imagem) foram
ajustados fora deste script, de modo que as 27 marcas da foto fiquem retangulares
e congruentes; aqui só se aplica o resultado.
Saída: imagens/pista_eva_rt_sobreposicao.png (placa retificada, 0,75 px/mm,
linha do modelo em vermelho, retângulos das marcas geradas em ciano).
"""
from pathlib import Path
import math
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import map_coordinates
from scipy.spatial.transform import Rotation
import pista_eva_rt_teste as pista

HERE=Path(__file__).resolve().parent
IMG=HERE.parent/'imagens'/'referencia_pista_teste_eva_rt.png'
OUT=HERE.parent/'imagens'/'pista_eva_rt_sobreposicao.png'
CAM=[1507.9898743710241,-0.5491089967448822,0.1425937001961081,0.15930814302956953,5334.6410097139815,1039.515447461086,510.8222938228023]
YAW_DEG=2.38; ORIGIN_RECT=np.array([-7024.3,-250.2]); DELTA_DEG=-0.7731599055549377
SCALE=pista.SCALE_FACTOR; ORG=np.array([88.51504225378767,-18.762044987804302])


def homography():
    f,rx,ry,rz,tx,ty,tz=CAM
    K=np.array([[f,0,960],[0,f,540],[0,0,1.]])
    R=Rotation.from_rotvec([rx,ry,rz]).as_matrix()@np.diag([1,-1,-1.])
    return K@np.column_stack((R[:,0],R[:,1],[tx,ty,tz]))


def rot(deg):
    a=math.radians(deg);return np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])


def image_to_model(px):
    h=np.c_[np.asarray(px,float),np.ones(len(px))]@np.linalg.inv(homography()).T
    plane=h[:,:2]/h[:,2:3]
    return SCALE*((plane@rot(YAW_DEG).T-ORIGIN_RECT)@rot(DELTA_DEG).T)-ORG


def model_to_image(mm):
    plane=((((np.asarray(mm,float)+ORG)/SCALE)@rot(DELTA_DEG))+ORIGIN_RECT)@rot(YAW_DEG)
    h=np.c_[plane,np.ones(len(plane))]@homography().T
    return h[:,:2]/h[:,2:3]


def main(px_per_mm=.75):
    test=np.array([[300.,400.],[1500.,800.]])
    assert np.allclose(model_to_image(image_to_model(test)),test,atol=1e-6)
    W,H=int(pista.BOARD[0]*px_per_mm),int(pista.BOARD[1]*px_per_mm)
    xs,ys=np.meshgrid((np.arange(W)+.5)/px_per_mm,(H-np.arange(H)-.5)/px_per_mm)
    ip=model_to_image(np.column_stack((xs.ravel(),ys.ravel())))
    photo=np.array(Image.open(IMG).convert('RGB')).astype(float)
    warped=np.stack([map_coordinates(photo[...,k],[ip[:,1]-.5,ip[:,0]-.5],order=1,cval=0).reshape(H,W) for k in range(3)],axis=2)
    im=Image.fromarray(np.clip(warped,0,255).astype(np.uint8));d=ImageDraw.Draw(im)
    P=lambda pts:[(float(x)*px_per_mm,H-float(y)*px_per_mm) for x,y in pts]
    track,cycle,marks,meta=pista.build(1.)
    d.line(P(cycle[:,1:3]),fill=(255,50,50),width=1)
    for seg in meta['estimated']:d.line(P(seg),fill=(255,200,0),width=2)
    for m in marks:
        c,s=math.cos(m['phi']),math.sin(m['phi'])
        q=[(m['x']+u*c-v*m['side']*s,m['y']+u*s+v*m['side']*c) for u,v in [(-9.5,49.5),(9.5,49.5),(9.5,89.5),(-9.5,89.5)]]
        d.polygon(P(q),outline=(0,255,255) if m['side']>0 else (255,0,255))
    for x,y in meta['crossings'] and [(c['x'],c['y']) for c in meta['crossings']]:
        r=25*px_per_mm;cx,cy=x*px_per_mm,H-y*px_per_mm;d.ellipse([cx-r,cy-r,cx+r,cy+r],outline=(80,200,255))
    im.save(OUT);print('Sobreposição:',OUT,im.size)


if __name__=='__main__':main()
