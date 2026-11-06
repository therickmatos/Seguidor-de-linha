# Minimal KiCad 7 schematic writer (raw S-expressions) with pin-geometry helpers.
import re, uuid, math, random
LIBDIR='/usr/share/kicad/symbols/'
_libcache={}
# UUIDs reprodutiveis: a mesma geracao da o mesmo arquivo, e o UUID de cada simbolo depende so da
# referencia (a placa .kicad_pcb se liga ao esquematico por esses UUIDs)
_rng=random.Random(20261106)
def U(): return str(uuid.UUID(int=_rng.getrandbits(128), version=4))
def U_ref(project, ref): return str(uuid.uuid5(uuid.NAMESPACE_URL, f'seguidor-de-linha/{project}/{ref}'))

def _blocks(text):
    """yield (name, block_text) for top-level symbols in a .kicad_sym"""
    i=0; out={}
    for m in re.finditer(r'\n\s\s\(symbol "([^"]+)"', text):
        start=m.start()+1
        # find balanced end
        depth=0; j=start
        while True:
            c=text[j]
            if c=='(': depth+=1
            elif c==')':
                depth-=1
                if depth==0: break
            elif c=='"':
                j+=1
                while text[j]!='"':
                    if text[j]=='\\': j+=1
                    j+=1
            j+=1
        out[m.group(1)]=text[start:j+1]
    return out

def libsym(lib, name, extra_text=None):
    if lib not in _libcache:
        txt=extra_text if extra_text else open(LIBDIR+lib+'.kicad_sym').read()
        _libcache[lib]=_blocks(txt)
    blocks=_libcache[lib]
    b=blocks[name]
    m=re.search(r'\(extends "([^"]+)"\)', b)
    if m:
        parent=m.group(1); pb=blocks[parent]
        # flatten: parent geometry, child's properties
        child_props=re.findall(r'\(property "[^"]+".*?\n\s{4}\)', b, re.S)
        flat=pb.replace(f'(symbol "{parent}"', f'(symbol "{name}"',1)
        flat=flat.replace(f'"{parent}_', f'"{name}_')
        # replace parent's property blocks with child's
        flat=re.sub(r'\(property "[^"]+".*?\n\s{4}\)', '', flat, flags=re.S)
        idx=flat.index('\n',0)  # after first line
        flat=flat[:idx]+'\n    '+'\n    '.join(child_props)+flat[idx:]
        b=flat
    return b

def pins_of(block):
    pins={}
    for m in re.finditer(r'\(pin (\w+) \w+ \(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\) \(length ([-\d.]+)\)(.*?)\(name "([^"]*)".*?\(number "([^"]+)"', block, re.S):
        typ, x,y,a,l, mid, nm, num = m.groups()
        pins.setdefault(num, (float(x),float(y),float(a),nm,typ))
    return pins

def rot(vx,vy,r):
    r=r%360
    if r==0: return vx,vy
    if r==90: return vy,-vx
    if r==180: return -vx,-vy
    if r==270: return -vy,vx
    raise ValueError

class Sch:
    def __init__(self, title='', paper='A3', project='seguidor'):
        self.uuid=U_ref(project, '/'); self.paper=paper; self.project=project; self.title=title
        self.libs={}; self.items=[]; self.pwr=0; self.flg=0
        self.syms={}   # ref -> dict
        self.tb={}
        self.intent=[]; self.links=[]; self.ncs=[]
    def uselib(self, libid, block):
        if libid in self.libs: return
        name=libid.split(':',1)[1]
        self.libs[libid]=block.replace(f'(symbol "{name}"', f'(symbol "{libid}"',1)
    def place(self, lib, name, ref, value, x, y, r=0, fields=None, footprint='', block=None, hide_ref=False, hide_val=False, dnp=False, ref_off=None, val_off=None):
        libid=f'{lib}:{name}'
        blk=block if block else libsym(lib,name)
        self.uselib(libid, blk)
        pins=pins_of(blk)
        s=dict(ref=ref,value=value,x=x,y=y,r=r,libid=libid,pins=pins,fields=fields or {},footprint=footprint,
               hide_ref=hide_ref,hide_val=hide_val,dnp=dnp,uuid=U_ref(self.project, ref),ref_off=ref_off,val_off=val_off)
        self.syms[ref]=s; self.items.append(('sym',s)); return s
    def pinpos(self, ref, num):
        s=self.syms[ref]; px,py,a,nm,typ=s['pins'][num]
        dx,dy=rot(px,-py,s['r'])
        # outward direction (screen)
        ox,oy=math.cos(math.radians(a+180)), -math.sin(math.radians(a+180))
        ox,oy=rot(round(ox),round(oy),s['r'])
        return round(s['x']+dx,3), round(s['y']+dy,3), ox, oy
    def wire(self, x1,y1,x2,y2):
        self.items.append(('wire',(x1,y1,x2,y2)))
    def label(self, net, x, y, ox, oy, kind='label'):
        ang={ (1,0):0, (0,-1):90, (-1,0):180, (0,1):270 }[(ox,oy)]
        self.items.append((kind,(net,x,y,ang)))
    def power(self, net, x, y, d=None):
        self.pwr+=1
        if d is None: d=(0,1) if net=='GND' else (0,-1)
        if net=='VBAT':
            blk=libsym('power','VCC').replace('"VCC"','"VBAT"').replace('VCC_','VBAT_').replace('name \\"VCC\\"','name \\"VBAT\\"')
            libid='seguidor:VBAT'
        else:
            blk=libsym('power',net); libid=f'power:{net}'
        self.uselib(libid, blk)
        if net=='GND': ang={(0,1):0,(1,0):90,(0,-1):180,(-1,0):270}[d]
        else: ang={(0,-1):0,(-1,0):90,(0,1):180,(1,0):270}[d]
        self.items.append(('pwr',(libid, net, x, y, f'#PWR{self.pwr:03d}', ang, d)))
    def flag(self, x, y):
        self.flg+=1
        blk=libsym('power','PWR_FLAG'); self.uselib('power:PWR_FLAG', blk)
        self.items.append(('flag',(x,y,f'#FLG{self.flg:02d}')))
    def nc(self, x, y): self.items.append(('nc',(x,y)))
    def junction(self, x, y): self.items.append(('junc',(x,y)))
    def conn(self, ref, num, net, stub=2.54, bend=None, blen=2.54):
        """connect pin to net with a stub: net may be 'GND','+5V','VBAT' (power symbol), None (no-connect) or label"""
        x,y,ox,oy=self.pinpos(ref,num)
        if net is None: self.nc(x,y); self.ncs.append((ref,num)); return
        self.intent.append((ref,num,net))
        ex,ey=round(x+ox*stub,3), round(y+oy*stub,3)
        if stub: self.wire(x,y,ex,ey)
        if bend:
            bx,by={'left':(-1,0),'right':(1,0),'up':(0,-1),'down':(0,1)}[bend]
            fx,fy=round(ex+bx*blen,3), round(ey+by*blen,3)
            self.wire(ex,ey,fx,fy); ex,ey,ox,oy=fx,fy,bx,by
        if net in ('GND','+5V','VBAT'):
            self.power(net, ex, ey, (ox,oy))
        else:
            self.label(net, ex, ey, ox, oy)
    def link(self, ra, pa, rb, pb, vfirst=False):
        self.links.append((ra,pa,rb,pb))
        x1,y1,_,_=self.pinpos(ra,pa); x2,y2,_,_=self.pinpos(rb,pb)
        if x1==x2 and y1==y2: return
        if x1==x2 or y1==y2: self.wire(x1,y1,x2,y2); return
        if vfirst: self.wire(x1,y1,x1,y2); self.wire(x1,y2,x2,y2)
        else: self.wire(x1,y1,x2,y1); self.wire(x2,y1,x2,y2)
    def text(self, t, x, y, size=1.27, bold=False):
        self.items.append(('text',(t,x,y,size,bold)))
    def rect(self, x1,y1,x2,y2):
        self.items.append(('rect',(x1,y1,x2,y2)))

    def render(self):
        o=[]
        o.append(f'(kicad_sch (version 20230121) (generator eeschema)\n\n  (uuid {self.uuid})\n\n  (paper "{self.paper}")\n')
        if self.tb:
            tb='  (title_block\n'
            for k in ('title','date','rev','company'):
                if k in self.tb: tb+=f'    ({k} "{self.tb[k]}")\n'
            for i,c in enumerate(self.tb.get('comments',[]),1): tb+=f'    (comment {i} "{c}")\n'
            o.append(tb+'  )\n')
        o.append('  (lib_symbols\n')
        for libid,b in self.libs.items():
            o.append('    '+b.replace('\n','\n  ')+'\n')
        o.append('  )\n')
        inst=lambda ref: f'    (instances\n      (project "{self.project}"\n        (path "/{self.uuid}" (reference "{ref}") (unit 1))\n      )\n    )\n'
        F='(effects (font (size 1.27 1.27))'
        for kind,d in self.items:
            if kind=='sym':
                s=d; x,y,r=s['x'],s['y'],s['r']
                vert = (r%180==0)
                # field positions
                ro=s['ref_off'] or (2.54,-1.27) ; vo=s['val_off'] or (2.54,1.27)
                o.append(f'  (symbol (lib_id "{s["libid"]}") (at {x} {y} {r}) (unit 1)\n    (in_bom yes) (on_board yes) (dnp {"yes" if s["dnp"] else "no"})\n    (uuid {s["uuid"]})\n')
                fa = 90 if r % 180 == 90 else 0
                fj = 'right' if (r + fa) % 360 == 180 else 'left'
                o.append(f'    (property "Reference" "{s["ref"]}" (at {x+ro[0]} {y+ro[1]} {fa})\n      {F} (justify {fj}){" hide" if s["hide_ref"] else ""})\n    )\n')
                o.append(f'    (property "Value" "{s["value"]}" (at {x+vo[0]} {y+vo[1]} {fa})\n      {F} (justify {fj}){" hide" if s["hide_val"] else ""})\n    )\n')
                o.append(f'    (property "Footprint" "{s["footprint"]}" (at {x} {y} 0)\n      {F} hide)\n    )\n')
                o.append(f'    (property "Datasheet" "~" (at {x} {y} 0)\n      {F} hide)\n    )\n')
                for k,v in s['fields'].items():
                    o.append(f'    (property "{k}" "{v}" (at {x} {y} 0)\n      {F} hide)\n    )\n')
                for num in s['pins']:
                    o.append(f'    (pin "{num}" (uuid {U()}))\n')
                o.append(inst(s['ref'])+'  )\n')
            elif kind=='wire':
                x1,y1,x2,y2=d
                o.append(f'  (wire (pts (xy {x1} {y1}) (xy {x2} {y2}))\n    (stroke (width 0) (type default))\n    (uuid {U()})\n  )\n')
            elif kind=='label':
                net,x,y,a=d; j='left' if a in (0,90) else 'right'
                o.append(f'  (label "{net}" (at {x} {y} {a}) (fields_autoplaced)\n    {F} (justify {j} bottom))\n    (uuid {U()})\n  )\n')
            elif kind=='pwr':
                libid,net,x,y,ref,ang,dd=d
                vx,vy=x+dd[0]*(4.2 if dd[0] else 0), y+dd[1]*(3.81 if dd[1] else 0)
                vj='left' if dd[0]>0 else ('right' if dd[0]<0 else 'center')
                if dd[1]: vy = y+dd[1]*(4.5 if net!='GND' else 4.2)
                o.append(f'  (symbol (lib_id "{libid}") (at {x} {y} {ang}) (unit 1)\n    (in_bom yes) (on_board yes) (dnp no)\n    (uuid {U()})\n')
                o.append(f'    (property "Reference" "{ref}" (at {x} {y} 0)\n      {F} hide)\n    )\n')
                pfa = 90 if ang % 180 == 90 else 0
                if (ang + pfa) % 360 == 180 and vj in ('left', 'right'): vj = 'right' if vj == 'left' else 'left'
                o.append(f'    (property "Value" "{net}" (at {vx} {vy} {pfa})\n      {F}{" (justify "+vj+")" if vj!="center" else ""})\n    )\n')
                o.append(f'    (property "Footprint" "" (at {x} {y} 0)\n      {F} hide)\n    )\n    (property "Datasheet" "" (at {x} {y} 0)\n      {F} hide)\n    )\n')
                o.append(f'    (pin "1" (uuid {U()}))\n'+inst(ref)+'  )\n')
            elif kind=='flag':
                x,y,ref=d
                o.append(f'  (symbol (lib_id "power:PWR_FLAG") (at {x} {y} 0) (unit 1)\n    (in_bom yes) (on_board yes) (dnp no)\n    (uuid {U()})\n')
                o.append(f'    (property "Reference" "{ref}" (at {x} {y} 0)\n      {F} hide)\n    )\n')
                o.append(f'    (property "Value" "PWR_FLAG" (at {x} {y-3.81} 0)\n      {F} hide)\n    )\n')
                o.append(f'    (property "Footprint" "" (at {x} {y} 0)\n      {F} hide)\n    )\n    (property "Datasheet" "~" (at {x} {y} 0)\n      {F} hide)\n    )\n')
                o.append(f'    (pin "1" (uuid {U()}))\n'+inst(ref)+'  )\n')
            elif kind=='junc':
                x,y=d; o.append(f'  (junction (at {x} {y}) (diameter 0) (color 0 0 0 0)\n    (uuid {U()})\n  )\n')
            elif kind=='nc':
                x,y=d; o.append(f'  (no_connect (at {x} {y}) (uuid {U()}))\n')
            elif kind=='text':
                t,x,y,sz,b=d
                t=t.replace('"','\\"')
                o.append(f'  (text "{t}" (at {x} {y} 0)\n    (effects (font (size {sz} {sz}){" bold" if b else ""}) (justify left bottom))\n    (uuid {U()})\n  )\n')
            elif kind=='rect':
                x1,y1,x2,y2=d
                o.append(f'  (rectangle (start {x1} {y1}) (end {x2} {y2})\n    (stroke (width 0.254) (type dash) (color 120 120 120 1))\n    (fill (type none))\n    (uuid {U()})\n  )\n')
        o.append('\n  (sheet_instances\n    (path "/" (page "1"))\n  )\n)\n')
        return ''.join(o)
