import struct, os, numpy as np
def load(fn):
    b=open(fn,'rb').read()
    n=struct.unpack('<I',b[80:84])[0]
    if 84+n*50==len(b):
        a=np.frombuffer(b[84:84+n*50],dtype=np.dtype([('n','<3f4'),('v','<9f4'),('a','<u2')]))
        return a['v'].reshape(-1,3,3).astype(float)
    v=[list(map(float,l.split()[1:4])) for l in b.decode().splitlines() if l.strip().startswith('vertex')]
    return np.array(v).reshape(-1,3,3)
